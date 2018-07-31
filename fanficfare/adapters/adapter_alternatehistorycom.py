#  -*- coding: utf-8 -*-

# Copyright 2018 FanFicFare team
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
from .adapter_forumquestionablequestingcom import QuestionablequestingComAdapter

def getClass():
    return WWWAlternatehistoryComAdapter

class WWWAlternatehistoryComAdapter(QuestionablequestingComAdapter):

    def __init__(self, config, url):
        QuestionablequestingComAdapter.__init__(self, config, url)

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','ah')

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.alternatehistory.com'

    @classmethod
    def getURLPrefix(cls):
        # in case it needs more than just site/
        return 'https://' + cls.getSiteDomain() + '/forum'

