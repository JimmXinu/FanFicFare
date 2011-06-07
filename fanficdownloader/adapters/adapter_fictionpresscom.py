# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team
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

import time
import logging
import re
import urllib2
import time

import fanficdownloader.BeautifulSoup as bs
import fanficdownloader.exceptions as exceptions

from base_adapter import BaseSiteAdapter, utf8FromSoup, makeDate

## They're from the same people and pretty much identical.
from adapter_fanfictionnet import FanFictionNetSiteAdapter

class FictionPressComSiteAdapter(FanFictionNetSiteAdapter):

    def __init__(self, config, url):
        FanFictionNetSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','fpcom')

    @staticmethod
    def getSiteDomain():
        return 'www.fictionpress.com'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.fictionpress.com','m.fictionpress.com']

    def getSiteExampleURLs(self):
        return "http://www.fictionpress.com/s/1234/1/ http://www.fictionpress.com/s/1234/12/ http://www.fictionpress.com/s/1234/1/Story_Title"

    def getSiteURLPattern(self):
        return r"http://(www|m)?\.fictionpress\.com/s/\d+(/\d+)?(/|/[a-zA-Z0-9_-]+)?/?$"

def getClass():
    return FictionPressComSiteAdapter

