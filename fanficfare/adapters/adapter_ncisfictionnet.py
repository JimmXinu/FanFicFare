# -*- coding: utf-8 -*-

# Copyright 2012 Fanficdownloader team, 2016 FanFicFare team
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
from base_efiction_adapter import BaseEfictionAdapter

class NCISFictionNetAdapter(BaseEfictionAdapter):

    @staticmethod
    def getSiteDomain():
        return 'ncisfiction.net'

    @classmethod
    def getSiteAbbrev(self):
        return 'ncisfn'

    @classmethod
    def getDateFormat(self):
        return "%m/%d/%Y"

def getClass():
    return NCISFictionNetAdapter
