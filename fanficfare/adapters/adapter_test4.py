# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2019 FanFicFare team
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

from .adapter_test1 import TestSiteAdapter

class Test4SiteAdapter(TestSiteAdapter):

    def __init__(self, config, url):
        TestSiteAdapter.__init__(self, config, url)

    @staticmethod
    def getSiteDomain():
        return 'test4.com'

def getClass():
    return Test4SiteAdapter

