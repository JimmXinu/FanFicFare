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
import re

from .base_xenforoforum_adapter import BaseXenForoForumAdapter

def getClass():
    return ForumsSpacebattlesComAdapter

class ForumsSpacebattlesComAdapter(BaseXenForoForumAdapter):

    def __init__(self, config, url):
        BaseXenForoForumAdapter.__init__(self, config, url)

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','fsb')

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'forums.spacebattles.com'

    @classmethod
    def getAcceptDomains(cls):
        return [cls.getSiteDomain(),
                cls.getSiteDomain().replace('forums.','forum.')]

    def getSiteURLPattern(self):
        ## SB accepts forums.spacebattles.com and forum.spacebattles.com
        ## We will use forums. as canonical for all
        return super(ForumsSpacebattlesComAdapter, self).getSiteURLPattern().replace(re.escape("forums."),r"forums?\.")
