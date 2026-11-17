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

# Software: eFiction
import re
from .base_efiction_adapter import BaseEfictionAdapter

## thehookupzone.net/CriminalMinds moved to criminal-minds-fiction.com,
## same story IDs.
SITE_URL_RE = r"https?://(www\.)?(criminal-minds-fiction\.com|thehookupzone\.net/CriminalMinds)/"

class TheHookupZoneNetAdapter(BaseEfictionAdapter):

    @classmethod
    def getProtocol(self):
        return "https"

    @staticmethod
    def getSiteDomain():
        return 'criminal-minds-fiction.com'

    @classmethod
    def getAcceptDomains(cls):
        return [cls.getSiteDomain(),'thehookupzone.net']

    @classmethod
    def getConfigSections(cls):
        "Only needs to be overriden if has additional ini sections."
        return ['base_efiction','thehookupzone.net',cls.getConfigSection()]

    def getSiteURLPattern(self):
        return SITE_URL_RE+r"viewstory\.php\?sid=(?P<storyId>\d+)"

    def normalize_chapterurl(self,url):
        url = re.sub(SITE_URL_RE,'https://'+self.getSiteDomain()+'/',url)
        return super(TheHookupZoneNetAdapter, self).normalize_chapterurl(url)

    @classmethod
    def get_url_search(cls,url):
        ## Also find books saved with the old thehookupzone.net URLs.
        regexp = super(TheHookupZoneNetAdapter, cls).get_url_search(url)
        return re.sub(r'://.*?/viewstory',
                      r'://(www\\.)?(criminal-minds-fiction\\.com|thehookupzone\\.net/CriminalMinds)/viewstory',
                      regexp, count=1)

    @classmethod
    def getSiteAbbrev(seluuf):
        return 'thupz'

    @classmethod
    def getDateFormat(self):
        return "%b %d, %Y"

def getClass():
    return TheHookupZoneNetAdapter
