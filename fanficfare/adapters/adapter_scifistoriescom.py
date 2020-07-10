# -*- coding: utf-8 -*-

# Copyright 2013 Fanficdownloader team, 2020 FanFicFare team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from __future__ import absolute_import, division, unicode_literals, print_function
import logging
logger = logging.getLogger(__name__)

# py2 vs py3 transition
from ..six import text_type as unicode

from .adapter_finestoriescom import FineStoriesComAdapter

def getClass():
    return SciFiStoriesComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class SciFiStoriesComAdapter(FineStoriesComAdapter):

    @classmethod
    def getSiteAbbrev(cls):
        return 'sfst'

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'scifistories.com'
