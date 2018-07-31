# -*- coding: utf-8 -*-

# Copyright 2018 FanFicFare team
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
##################################################################################
### Rewritten by: GComyn on November, 06, 2016
### Original was adapter_fannation.py
##################################################################################
from __future__ import absolute_import
from .base_efiction_adapter import BaseEfictionAdapter

class ValentChamberComAdapter(BaseEfictionAdapter):

    @staticmethod
    def getSiteDomain():
        return 'www.valentchamber.com'

    @classmethod
    def getSiteAbbrev(self):
        return 'vccom'

    @classmethod
    def getDateFormat(self):
        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        return "%B %d %Y"

##################################################################################
### The Efiction Base Adapter uses the Bulk story to retrieve the metadata, but
### on this site, the Rating is not present in the Bulk page... 
### so it is not retrieved.
##################################################################################
        
def getClass():
    return ValentChamberComAdapter
