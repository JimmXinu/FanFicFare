#  -*- coding: utf-8 -*-

# Copyright 2014 Fanficdownloader team, 2020 FanFicFare team
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
    return ArchiveOfOurOwnOrgAdapter

class ArchiveOfOurOwnOrgAdapter(BaseOTWAdapter):

    def __init__(self, config, url):
        BaseOTWAdapter.__init__(self, config, url)

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','ao3')

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'archiveofourown.org'

    # The certificate is only valid for the following names:
    # ao3.org,
    # archiveofourown.com,
    # archiveofourown.net,
    # archiveofourown.org,
    # www.ao3.org,

    @classmethod
    def getAcceptDomains(cls):
        return ['archiveofourown.org',
                'archiveofourown.com',
                'archiveofourown.net',
                'archiveofourown.gay',
                'download.archiveofourown.org',
                'download.archiveofourown.com',
                'download.archiveofourown.net',
                'ao3.org',
                ]

    def mod_url_request(self, url):
        return url

    def mod_url_request(self, url):
        ## add / to *not* replace media.archiveofourown.org
        if self.getConfig("use_archive_transformativeworks_org",False):
            return url.replace("/archiveofourown.org","/archive.transformativeworks.org")
        elif self.getConfig("use_archiveofourown_gay",False):
            return url.replace("/archiveofourown.org","/archiveofourown.gay")
        else:
            return url
