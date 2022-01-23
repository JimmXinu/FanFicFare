# -*- coding: utf-8 -*-

# Copyright 2022 FanFicFare team
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
from .base_efiction_adapter import BaseEfictionAdapter

class MerengoHuAdapter(BaseEfictionAdapter):

    @classmethod
    def getProtocol(self):
        return "https"

    @staticmethod
    def getSiteDomain():
        return 'merengo.hu'

    @classmethod
    def getSiteAbbrev(self):
        return 'merengo'

    @classmethod
    def getDateFormat(self):
        return "%Y.%m.%d"

    def extractChapterUrlsAndMetadata(self):
        ## merengo.hu has a custom 18 consent click through
        self.get_request(self.getUrlForPhp('tizennyolc.php')+'?consent=true')

        ## Call super of extractChapterUrlsAndMetadata().
        ## base_efiction leaves the soup in self.html.
        return super(MerengoHuAdapter, self).extractChapterUrlsAndMetadata()

def getClass():
    return MerengoHuAdapter

