# -*- coding: utf-8 -*-

# Copyright 2014 Fanficdownloader team, 2015 FanFicFare team
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

class FHSArchiveComAdapter(BaseEfictionAdapter):

    @staticmethod
    def getSiteDomain():
        return 'fhsarchive.com'

    @classmethod
    def getPathToArchive(self):
        return '/autoarchive'

    @classmethod
    def getSiteAbbrev(self):
        return 'fhsa'

    @classmethod
    def getDateFormat(self):
        return "%m/%d/%y"

    def handleMetadataPair(self, key, value):
        if key == 'Warnings':
            for val in re.split("\s*,\s*", value):
                if value == 'None':
                    return
                else:
                    # toss numbers only.
                    self.story.addToList('warnings', filter(lambda x : not x.isdigit() , val))

    #     elif 'Categories' in key:
    #         for val in re.split("\s*>\s*", value):
    #             self.story.addToList('category', val)
        else:
            super(FHSArchiveComAdapter, self).handleMetadataPair(key, value)

def getClass():
    return FHSArchiveComAdapter

