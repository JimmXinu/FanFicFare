# -*- coding: utf-8 -*-

# Copyright 2013 Fanficdownloader team, 2018 FanFicFare team
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
import logging
logger = logging.getLogger(__name__)

# py2 vs py3 transition
from ..six import text_type as unicode

from .adapter_storiesonlinenet import StoriesOnlineNetAdapter

def getClass():
    return FineStoriesComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class FineStoriesComAdapter(StoriesOnlineNetAdapter):

    @classmethod
    def getSiteAbbrev(cls):
        return 'fnst'

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'finestories.com'

    @classmethod
    def getTheme(cls):
        ## only one theme is supported.
        return "Modern"

    ## Login seems to be reasonably standard across eFiction sites.
    def needToLoginCheck(self, data):
        if 'Free Registration' in data \
                or "Log In" in data \
                or "Invalid Password!" in data \
                or "Invalid User Name!" in data:
            return True
        else:
            return False

    def getStoryMetadataFromAuthorPage(self):
        # surprisingly, the detailed page does not give enough details, so go to author's page
        story_row = self.findStoryRow('div')

        description_element = story_row.find('div', {'class' : 'sdesc'})

        self.parseDescriptionField(description_element)

        misc_element = story_row.find('div', {'class' : 'misc'})
        self.parseOtherAttributes(misc_element)
