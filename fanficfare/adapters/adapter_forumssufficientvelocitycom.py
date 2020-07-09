#  -*- coding: utf-8 -*-

# Copyright 2019 FanFicFare team
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
import re

from .base_xenforo2forum_adapter import BaseXenForo2ForumAdapter

def getClass():
    return ForumsSufficientVelocityComAdapter

class ForumsSufficientVelocityComAdapter(BaseXenForo2ForumAdapter):

    def __init__(self, config, url):
        BaseXenForo2ForumAdapter.__init__(self, config, url)

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','fsv')

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'forums.sufficientvelocity.com'

    @classmethod
    def getAcceptDomains(cls):
        return [cls.getSiteDomain(),
                cls.getSiteDomain().replace('forums.','forum.'),
                cls.getSiteDomain().replace('forums.','')]

    def getSiteURLPattern(self):
        ## SV accepts forums.sufficientvelocity.com, forum.sufficientvelocity.com and sufficientvelocity.com
        ## all of which redirect to forums.
        ## We will use forums. as canonical for all
        return super(ForumsSufficientVelocityComAdapter, self).getSiteURLPattern().replace(re.escape("forums."),r"(forums?\.)?")
