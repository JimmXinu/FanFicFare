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

class StarsLibraryNetAdapter(BaseEfictionAdapter):

    @staticmethod
    def getSiteDomain():
        return 'starslibrary.net'

    @classmethod
    def getProtocol(self):
        return "https"

    ## starslibrary.net is a replacement for pre-existing twcslibrary.net.
    @classmethod
    def getConfigSections(cls):
        "Only needs to be overriden if has additional ini sections."
        return super(StarsLibraryNetAdapter, cls).getConfigSections()+['www.'+cls.getConfigSection(),'www.twcslibrary.net']

    @classmethod
    def getAcceptDomains(cls):
        return [cls.getSiteDomain(),'www.' + cls.getSiteDomain(),
                'www.twcslibrary.net','twcslibrary.net']

    @classmethod
    def getSiteURLPattern(self):
        return r"https?://(%s)?%s/%s\?sid=(?P<storyId>\d+)" % ('|'.join(self.getAcceptDomains()), self.getPathToArchive(), self.getViewStoryPhpName())

    @classmethod
    def getSiteAbbrev(self):
        return 'stars'

    @classmethod
    def getDateFormat(self):
        return "%d %b %Y"


    def extractChapterUrlsAndMetadata(self):
        ## Call super of extractChapterUrlsAndMetadata().
        ## base_efiction leaves the soup in self.html.
        super(getClass(), self).extractChapterUrlsAndMetadata()

        if not self.story.getMetadata('rating'):
            # as with most eFiction bulk sites, the Rating is not retrieved.
            # fetch from index page.
            toc = self.url + "&index=1"
            soup = self.make_soup(self._fetchUrl(toc))
            for label in soup.find_all('span', {'class':'label'}):
                if 'Rated:' in label:
                    self.story.setMetadata('rating',stripHTML(label.next_sibling))
                    break

def getClass():
    return StarsLibraryNetAdapter
