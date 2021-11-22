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

from grimoire_elk.raw.elastic import ElasticOcean
from grimoire_elk.enriched.utils import get_repository_filter
from grimoire_elk.elastic_mapping import Mapping as BaseMapping
from ..identities.surveyqq import SurveyqqIdentities
from grimoire_elk_surveyqq.enriched.surveyqq import GITEE
import json


class Mapping(BaseMapping):

    @staticmethod
    def get_elastic_mappings(es_major):
        """Get Elasticsearch mapping.
        :param es_major: major version of Elasticsearch, as string
        :returns:        dictionary with a key, 'items', with the mapping
        """

        mapping = '''
         {
            "dynamic":true,
                "properties": {
                    "data": {
                        "dynamic":false,
                        "properties": {}
                    }
                }
        }
        '''

        return {"items": mapping}


class SurveyqqOcean(ElasticOcean):
    """Gitee Ocean feeder"""

    mapping = Mapping
    identities = SurveyqqIdentities

    @classmethod
    def get_perceval_params_from_url(cls, url):
        """ Get the perceval params given a URL for the data source """

        params = []

        owner = url.split('/')[-2]
        repository = url.split('/')[-1]
        params.append(owner)
        params.append(repository)
        return params

    def _fix_item(self, item):
        category = item['category']

        if 'classified_fields_filtered' not in item or not item['classified_fields_filtered']:
            return

        item = item['data']
        comments_attr = None
        if category == "issue":
            identity_types = ['user', 'assignee']
            comments_attr = 'comments_data'
        elif category == "pull_request":
            identity_types = ['user', 'merged_by']
            comments_attr = 'review_comments_data'
        else:
            identity_types = []

        for identity in identity_types:
            if identity not in item:
                continue
            if not item[identity]:
                continue

            identity_attr = identity + "_data"

            item[identity_attr] = {
                'name': item[identity]['login'],
                'login': item[identity]['login'],
                'email': None,
                'company': None,
                'location': None,
            }

        comments = item.get(comments_attr, [])
        for comment in comments:
            comment['user_data'] = {
                'name': comment['user']['login'],
                'login': comment['user']['login'],
                'email': None,
                'company': None,
                'location': None,
            }
        
    def get_repository_filter_raw(self, term=False):
        """Returns the filter to be used in queries in a repository items"""

        perceval_backend_name = self.get_connector_name()
        self.perceval_backend.set_origin(GITEE + self.perceval_backend.owner +"/" + self.perceval_backend.owner)
        filter_ = get_repository_filter(self.perceval_backend, perceval_backend_name, term)
        return filter_

    # def get_elastic_items(self, elastic_scroll_id=None, _filter=None, ignore_incremental=False):
    #     """Get the items from the index related to the backend applying and
    #     optional _filter if provided

    #     :param elastic_scroll_id: If not None, it allows to continue scrolling the data
    #     :param _filter: if not None, it allows to define a terms filter (e.g., "uuid": ["hash1", "hash2, ...]
    #     :param ignore_incremental: if True, incremental collection is ignored
    #     """
    #     headers = {"Content-Type": "application/json"}

    #     if not self.elastic:
    #         return None
    #     url = self.elastic.index_url
    #     # 1 minute to process the results of size items
    #     # In gerrit enrich with 500 items per page we need >1 min
    #     # In Mozilla ES in Amazon we need 10m
    #     max_process_items_pack_time = "10m"  # 10 minutes
    #     url += "/_search?scroll=%s&size=%i" % (max_process_items_pack_time,
    #                                            self.scroll_size)

    #     if elastic_scroll_id:
    #         """ Just continue with the scrolling """
    #         url = self.elastic.url
    #         url += "/_search/scroll"
    #         scroll_data = {
    #             "scroll": max_process_items_pack_time,
    #             "scroll_id": elastic_scroll_id
    #         }
    #         query_data = json.dumps(scroll_data)
    #     else:
    #         # If using a perceval backends always filter by repository
    #         # to support multi repository indexes
    #         filters_dict = self.get_repository_filter_raw(term=True)
    #         if filters_dict:
    #             filters = json.dumps(filters_dict)
    #         else:
    #             filters = ''

    #         if self.filter_raw:
    #             for fltr in self.filter_raw_dict:
    #                 filters += '''
    #                     , {"match":
    #                         { "%s":"%s"  }
    #                     }
    #                 ''' % (fltr['name'], fltr['value'])

    #         if _filter:
    #             filter_str = '''
    #                 , {"match":
    #                     { "%s": %s }
    #                 }
    #             ''' % (_filter['name'], _filter['value'])
    #             # List to string conversion uses ' that are not allowed in JSON
    #             filter_str = filter_str.replace("'", "\"")
    #             filters += filter_str

    #         # The code below performs the incremental enrichment based on the last value of `metadata__timestamp`
    #         # in the enriched index, which is calculated in the TaskEnrich before enriching the single repos that
    #         # belong to a given data source. The old implementation of the incremental enrichment, which consisted in
    #         # collecting the last value of `metadata__timestamp` in the enriched index for each repo, didn't work
    #         # for global data source (which are collected globally and only partially enriched).
    #         if self.from_date and not ignore_incremental:
    #             date_field = self.get_incremental_date()
    #             from_date = self.from_date.isoformat()

    #         #     filters += '''
    #         #         , {"range":
    #         #             {"%s": {"gte": "%s"}}
    #         #         }
    #         #     ''' % (date_field, from_date)
    #         # elif self.offset and not ignore_incremental:
    #         #     filters += '''
    #         #         , {"range":
    #         #             {"offset": {"gte": %i}}
    #         #         }
    #         #     ''' % self.offset

    #         # Order the raw items from the old ones to the new so if the
    #         # enrich process fails, it could be resume incrementally
    #         order_query = ''
    #         order_field = None
    #         if self.perceval_backend:
    #             order_field = self.get_incremental_date()
    #         if order_field is not None:
    #             order_query = ', "sort": { "%s": { "order": "asc" }} ' % order_field

    #         # Fix the filters string if it starts with "," (empty first filter)
    #         filters = filters.lstrip()[1:] if filters.lstrip().startswith(',') else filters

    #         query = """
    #         {
    #             "query": {
    #                 "bool": {
    #                     "must": [%s]
    #                 }
    #             } %s
    #         }
    #         """ % (filters, order_query)

    #         logger.debug("Raw query to {}\n{}".format(anonymize_url(url),
    #                      json.dumps(json.loads(query), indent=4)))
    #         query_data = query

    #     rjson = None
    #     try:
    #         res = self.requests.post(url, data=query_data, headers=headers)
    #         if self.too_many_scrolls(res):
    #             return {'too_many_scrolls': True}
    #         res.raise_for_status()
    #         rjson = res.json()
    #     except Exception:
    #         # The index could not exists yet or it could be empty
    #         logger.debug("No results found from {}".format(anonymize_url(url)))

    #     return rjson