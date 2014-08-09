# -*- coding: utf-8 -*-

# Copyright 2014 Fanficdownloader team
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
import re
from base_efiction_adapter import BaseEfictionAdapter

class FanNationAdapter(BaseEfictionAdapter):

    @staticmethod
    def getSiteDomain():
        return 'fannation.shades-of-moonlight.com'

    @classmethod
    def getPathToArchive(self):
        return '/archive'

    @classmethod
    def getSiteAbbrev(self):
        return 'fannation'

    def handleMetadataPair(self, key, value):
        if key == 'Romance':
            for val in re.split("\s*,\s*", value):
                self.story.addToList('romance', val)
        else:
            super(FanNationAdapter, self).handleMetadataPair(key, value)

def getClass():
    return FanNationAdapter
