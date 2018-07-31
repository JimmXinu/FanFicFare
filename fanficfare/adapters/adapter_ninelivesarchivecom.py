# -*- coding: utf-8 -*-

# Copyright 2015 Fanficdownloader team, 2018 FanFicFare team
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

# Software: eFiction
from __future__ import absolute_import
import re
from .base_efiction_adapter import BaseEfictionAdapter

class NineLivesAdapter(BaseEfictionAdapter):

    @staticmethod
    def getSiteDomain():
        return 'ninelivesarchive.com'

    @classmethod
    def getAcceptDomains(cls):
        return ['ninelivesarchive.com','ninelives.dark-solace.org']

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/viewstory.php?sid=1234"

    @classmethod
    def getSiteURLPattern(self):
        return "http://("+self.getSiteDomain()+"|ninelives.dark-solace.org)"+re.escape("/viewstory.php?sid=")+r"(?P<storyId>\d+)$"

    @classmethod
    def getConfigSections(cls):
        "Only needs to be overriden if has additional ini sections."
        return ['base_efiction','ninelives.dark-solace.org',cls.getSiteDomain()]

    @classmethod
    def getSiteAbbrev(self):
        return '9lvs'

    @classmethod
    def getDateFormat(self):
        return "%B %d, %Y"

def getClass():
    return NineLivesAdapter

