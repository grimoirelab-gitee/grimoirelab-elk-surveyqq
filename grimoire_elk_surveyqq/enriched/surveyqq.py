# -*- coding: utf-8 -*-
#
# Copyright (C) 2021 Huawei
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#   Yehui Wang <yehui.wang.mdh@gmail.com>
#

import logging
import re
import json

import requests

from dateutil.relativedelta import relativedelta
from datetime import datetime

from grimoire_elk.elastic import ElasticSearch
from grimoirelab_toolkit.datetime import (datetime_utcnow,
                                          str_to_datetime)

from elasticsearch import Elasticsearch as ES, RequestsHttpConnection

from grimoire_elk.enriched.utils import get_time_diff_days


from grimoire_elk.enriched.enrich import Enrich, metadata
from grimoire_elk.elastic_mapping import Mapping as BaseMapping


GITEE = 'https://gitee.com/'
GITEE_ISSUES = "gitee_issues"
GITEE_MERGES = "gitee_pulls"

logger = logging.getLogger(__name__)


class Mapping(BaseMapping):

    @staticmethod
    def get_elastic_mappings(es_major):
        """Get Elasticsearch mapping.
        geopoints type is not created in dynamic mapping
        :param es_major: major version of Elasticsearch, as string
        :returns:        dictionary with a key, 'items', with the mapping
        """

        mapping = """
        {
            "properties": {
               "merge_author_geolocation": {
                   "type": "geo_point"
               },
               "assignee_geolocation": {
                   "type": "geo_point"
               },
               "state": {
                   "type": "keyword"
               },
               "user_geolocation": {
                   "type": "geo_point"
               },
               "title_analyzed": {
                 "type": "text",
                 "index": true
               }
            }
        }
        """

        return {"items": mapping}


class SurveyqqEnrich(Enrich):

    mapping = Mapping

    issue_roles = ['assignee_data', 'user_data']
    pr_roles = ['merged_by_data', 'user_data']
    roles = ['assignee_data', 'merged_by_data', 'user_data']

    def __init__(self, db_sortinghat=None, db_projects_map=None, json_projects_map=None,
                 db_user='', db_password='', db_host=''):
        super().__init__(db_sortinghat, db_projects_map, json_projects_map,
                         db_user, db_password, db_host)

        self.studies = []
        self.studies.append(self.enrich_onion)
        # self.studies.append(self.enrich_pull_requests)
        # self.studies.append(self.enrich_geolocation)
        # self.studies.append(self.enrich_extra_data)
        # self.studies.append(self.enrich_backlog_analysis)

    def set_elastic(self, elastic):
        self.elastic = elastic

    def get_field_author(self):
        return "user_data"

    def get_field_date(self):
        """ Field with the date in the JSON enriched items """
        return "grimoire_creation_date"

    def get_identities(self, item):
        """Return the identities from an item"""

        category = item['category']
        item = item['data']

        user = self.get_sh_identity(item["answer"])
        return user

        # if category == "issue":
        #     identity_types = ['user', 'assignee']
        # elif category == "pull_request":
        #     identity_types = ['user', 'merged_by']
        # else:
        #     identity_types = []

        # for identity in identity_types:
        #     identity_attr = identity + "_data"
        #     if item[identity] and identity_attr in item:
        #         # In user_data we have the full user data
        #         user = self.get_sh_identity(item[identity_attr])
        #         if user:
        #             yield user

    def get_sh_identity(self, item_answer, identity_field=None):
        identity = {}

        # by default a specific user dict is expected
        user_answer = item_answer[0]["questions"]
        identity['username'] = user_answer[0]["text"]
        identity['email'] = user_answer[1]["text"]
        identity['name'] = None
        return identity

    def get_project_repository(self, eitem):
        repo = eitem['origin']
        return repo

    @metadata
    def get_rich_item(self, item):

        rich_item = {}
        if item['category'] == 'issue':
            rich_item = self.__get_rich_survey(item)
        else:
            logger.error("[github] rich item not defined for GitHub category {}".format(
                         item['category']))

        self.add_repository_labels(rich_item)
        self.add_metadata_filter_raw(rich_item)
        return rich_item

    def __get_rich_survey(self, item):
        rich_survey = {}
        survey = item['data']["answer"][0]["questions"]
        rich_survey["user_login"] = survey[0]["text"]
        rich_survey["user_email"] = survey[1]["text"]
        rich_survey["issue_link"] = survey[2]["text"]
        rich_survey["survey_score"] = survey[3]["text"]
        rich_survey["participated_reason"] = [op["text"]
                                              for op in survey[4]["options"]]
        if rich_survey["survey_score"] in range(0, 7):
            rich_survey["issue_unsatisfied"] = [op["text"]
                                                for op in survey[5]["options"]]
        if rich_survey["survey_score"] in range(7, 9):
            rich_survey["issue_to_improve"] = [op["text"]
                                               for op in survey[5]["options"]]
        if rich_survey["survey_score"] in range(9, 11):
            rich_survey["issue_satisfied"] = [op["text"]
                                              for op in survey[5]["options"]]

        if item['data']['comment_data'] not in ["Invalid Issue Link", "Can't get message about Issue"]:
            rich_survey["survey_answer_role"] = self.__get_survey_answer_role(
                rich_survey["user_login"], item['data'])

        if self.prjs_map:
            rich_survey.update(self.get_item_project(rich_survey))

        if 'project' in item:
            rich_survey['project'] = item['project']

        rich_survey.update(self.get_grimoire_fields(
            item['data']["started_at"], "pull_request"))

        item[self.get_field_date()] = rich_survey[self.get_field_date()]
        rich_survey.update(self.get_item_sh(item, self.pr_roles))
        return rich_survey

    def __get_survey_answer_role(self, name, item):
        if name in [item["issue_data"]["user"]["login"], item["issue_data"]["user"]["name"]]:
            return "issue_owner"
        elif item["issue_data"]["assignee"] and name in item["issue_data"]["assignee"]:
            return "assignee"
        elif name in [user["user"]["login"] for user in item["comment_data"]]:
            return "commenter"

        return None

    def enrich_onion(self, ocean_backend, enrich_backend,
                     in_index, out_index, data_source=None, no_incremental=False,
                     contribs_field='uuid',
                     timeframe_field='grimoire_creation_date',
                     sort_on_field='metadata__timestamp',
                     seconds=Enrich.ONION_INTERVAL):

        if not data_source:
            raise ELKError(cause="Missing data_source attribute")

        if data_source not in [GITEE_ISSUES, GITEE_MERGES, ]:
            logger.warning("[gitee] data source value {} should be: {} or {}".format(
                data_source, GITEE_ISSUES, GITEE_MERGES))

        super().enrich_onion(enrich_backend=enrich_backend,
                             in_index=in_index,
                             out_index=out_index,
                             data_source=data_source,
                             contribs_field=contribs_field,
                             timeframe_field=timeframe_field,
                             sort_on_field=sort_on_field,
                             no_incremental=no_incremental,
                             seconds=seconds)
