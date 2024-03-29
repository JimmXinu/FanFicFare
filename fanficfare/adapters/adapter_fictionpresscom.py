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
import re

# py2 vs py3 transition

## They're from the same people and pretty much identical.
from .adapter_fanfictionnet import FanFictionNetSiteAdapter

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

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://www.fictionpress.com/s/1234/1/ https://www.fictionpress.com/s/1234/12/ http://www.fictionpress.com/s/1234/1/Story_Title http://m.fictionpress.com/s/1234/1/"

    @classmethod
    def _get_site_url_pattern(cls):
        return r"https?://(www|m)?\.fictionpress\.com/s/(?P<id>\d+)(/\d+)?(/(?P<title>[^/]+))?/?$"

    ## normalized chapter URLs DO contain the story title now, but
    ## normalized to current urltitle in case of title changes.
    def normalize_chapterurl(self,url):
        return re.sub(r"https?://(www|m)\.(?P<keep>fictionpress\.com/s/\d+/\d+/).*",
                      r"https://www.\g<keep>",url)+self.urltitle

def getClass():
    return FictionPressComSiteAdapter

