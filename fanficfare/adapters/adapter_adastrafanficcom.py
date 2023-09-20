# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2018 FanFicFare team
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

from .base_otw_adapter import BaseOTWAdapter

def getClass():
    return SquidgeWorldOrgAdapter

class SquidgeWorldOrgAdapter(BaseOTWAdapter):

    def __init__(self, config, url):
        BaseOTWAdapter.__init__(self, config, url)
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','aaff')

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.adastrafanfic.com'
