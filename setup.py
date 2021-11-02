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
#     Yehui Wang <yehui.wang.mdh@gmail.com>
#

import codecs
import os
import re

# Always prefer setuptools over distutils
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
readme_md = os.path.join(here, 'README.md')

# Get the package description from the README.md file
with codecs.open(readme_md, encoding='utf-8') as f:
    long_description = f.read()

setup(name="grimoire-elk-surveyqq",
      description="GrimoireLab library to produce surveyqq indexes for ElasticSearch",
      long_description=long_description,
      long_description_content_type='text/markdown',
      url="https://github.com/grimoirelab-gitee/grimoirelab-elk-surveyqq",
      version="0.1.0",
      author="Yehui Wang",
      author_email="yehui.wang.mdh@gmail.com",
      license="GPLv3",
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'Topic :: Software Development',
          'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5'],
      keywords="development repositories analytics for surveyqq",
      packages=['grimoire_elk_surveyqq', 'grimoire_elk_surveyqq.enriched', 'grimoire_elk_surveyqq.raw', 'grimoire_elk_surveyqq.identities'],
      entry_points={"grimoire_elk": "surveyqq = grimoire_elk_surveyqq.utils:get_connectors"},
      package_dir={'grimoire_elk_surveyqq.enriched': 'grimoire_elk_surveyqq/enriched'},
      package_data={'grimoire_elk_surveyqq.enriched': ['mappings/*.json']},
      python_requires='>=3.4',
      setup_requires=['wheel'],
      extras_require={'sortinghat': ['sortinghat'],
                      'mysql': ['PyMySQL']},
      tests_require=['httpretty==0.8.6'],
      test_suite='tests',
      install_requires=[
          'grimoire-elk>=0.72.0',
          'perceval>=0.9.6',
          'perceval-surveyqq>=0.1.0',
          'cereslib>=0.1.0',
          'grimoirelab-toolkit>=0.1.4',
          'sortinghat>=0.6.2',
          'graal>=0.2.2',
          'elasticsearch==6.3.1',
          'elasticsearch-dsl==6.3.1',
          'requests==2.21.0',
          'urllib3==1.24.3',
          'PyMySQL>=0.7.0',
          'pandas>=0.22.0,<=0.25.3',
          'geopy>=1.20.0',
          'statsmodels >= 0.9.0'
      ],
      zip_safe=False
      )
