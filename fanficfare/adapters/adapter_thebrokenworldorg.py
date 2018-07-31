# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2017 FanFicFare team
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

class TheBrokenWorldOrgSiteAdapter(BaseEfictionAdapter):

    @staticmethod
    def getSiteDomain():
        return 'www.fiction.thebrokenworld.org'

    @classmethod
    def getSiteAbbrev(self):
        return 'tbwo'

    @classmethod
    def getDateFormat(self):
        return "%B %d, %Y"

    def extractChapterUrlsAndMetadata(self):
        ## Call super of extractChapterUrlsAndMetadata().
        ## base_efiction leaves the soup in self.html.
        super(TheBrokenWorldOrgSiteAdapter, self).extractChapterUrlsAndMetadata()

        if len(self.story.getMetadata('rating')) == 0:
            # as with most eFiction bulk sites, the Rating is not retrieved.
            # So I'm going to retrieve it here
            toc = self.url + "&index=1"
            soup = self.make_soup(self._fetchUrl(toc))
            for label in soup.find_all('span', {'class':'label'}):
                if 'Rated:' in label:
                    self.story.setMetadata('rating',stripHTML(label.next_sibling))
                    break
        
def getClass():
    return TheBrokenWorldOrgSiteAdapter
