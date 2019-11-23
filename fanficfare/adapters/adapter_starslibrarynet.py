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

def getClass():
    return StarsLibraryNetAdapter
