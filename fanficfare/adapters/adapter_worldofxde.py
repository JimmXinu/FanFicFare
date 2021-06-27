# -*- coding: utf-8 -*-

# Copyright 2021 FanFicFare team
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
from .base_efiction_adapter import BaseEfictionAdapter
import re
import logging
logger = logging.getLogger(__name__)

class WorldOfXDeAdapter(BaseEfictionAdapter):

    @staticmethod
    def getSiteDomain():
        return 'worldofx.de'

    @classmethod
    def getSiteAbbrev(self):
        return 'wox'

    @classmethod
    def getDateFormat(self):
        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        return "%d.%m.%y"

    def handleMetadataPair(self, key, value):
        # This site is there isn't a label for other tags and they get
        # accidentally lumped with characters.
        # logger.debug("%s->%s"%(key,value))
        if key == 'Characters':
            (value,othertags) = value.split("\n\n")
            # let characters values fall through to super.
            # logger.debug("%s || %s"%(value,othertags))
            for val in re.split(r"\s*,\s*", othertags):
                if val == 'Deutsch':
                    ## German instead of Deutsch for benefit of
                    ## Calibre.
                    self.story.setMetadata('language','German')
                else:
                    self.story.addToList('genre', val)
        super(WorldOfXDeAdapter, self).handleMetadataPair(key, value)

def getClass():
    return WorldOfXDeAdapter
