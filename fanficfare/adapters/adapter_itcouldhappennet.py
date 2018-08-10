# -*- coding: utf-8 -*-

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

# Software: eFiction
from __future__ import absolute_import
import re
from .base_efiction_adapter import BaseEfictionAdapter

class ItCouldHappenNetSiteAdapter(BaseEfictionAdapter):

    @staticmethod
    def getSiteDomain():
        return 'it-could-happen.net'

    @classmethod
    def getSiteAbbrev(seluuf):
        return 'ich'

    @classmethod
    def getDateFormat(self):
        return "%B %d, %Y"

    def handleMetadataPair(self, key, value):
        # This site is all one 'category' as it's usually defined and
        # uses Category for what is usually genre.
        if key == 'Categories':
            for val in re.split("\s*,\s*", value):
                self.story.addToList('genre', val)
        else:
            super(ItCouldHappenNetSiteAdapter, self).handleMetadataPair(key, value)

def getClass():
    return ItCouldHappenNetSiteAdapter
