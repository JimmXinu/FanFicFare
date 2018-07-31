# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2018 FanFicFare team
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

from __future__ import absolute_import
from ..htmlcleanup import stripHTML

# Software: eFiction
from .base_efiction_adapter import BaseEfictionAdapter

class DarkSolaceOrgAdapter(BaseEfictionAdapter):

    @classmethod
    def getProtocol(self):
        """
        Some, but not all site now require https.
        """
        return "https"

    @staticmethod
    def getSiteDomain():
        return 'dark-solace.org'

    @classmethod
    def getPathToArchive(self):
        return '/elysian'

    @classmethod
    def getSiteAbbrev(self):
        return 'dksl'

    @classmethod
    def getDateFormat(self):
        return "%B %d, %Y"

    def extractChapterUrlsAndMetadata(self):
        ## Call super of extractChapterUrlsAndMetadata().
        ## base_efiction leaves the soup in self.html.
        super(DarkSolaceOrgAdapter, self).extractChapterUrlsAndMetadata()

        ## attempt to fetch rating from title line:
        ## "Do You Think This Is Love? by Supernatural Beings [PG]"
        r = stripHTML(self.html.find("div", {"id": "pagetitle"}))
        if '[' in r and ']' in r:
            self.story.setMetadata('rating',
                                   r[r.index('[')+1:r.index(']')])

def getClass():
    return DarkSolaceOrgAdapter

