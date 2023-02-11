#  -*- coding: utf-8 -*-

# Copyright 2020 FanFicFare team
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

# py2 vs py3 transition
from ..six import text_type as unicode

from .base_xenforo2forum_adapter import BaseXenForo2ForumAdapter

def getClass():
    return TheSietchComAdapter

class TheSietchComAdapter(BaseXenForo2ForumAdapter):

    def __init__(self, config, url):
        BaseXenForo2ForumAdapter.__init__(self, config, url)

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','sietch')

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.the-sietch.com'

    @classmethod
    def getPathPrefix(cls):
        # in case it needs more than just site/
        return '/index.php?'

    def make_reader_url(self,tmcat_num,reader_page_num):
        # https://www.the-sietch.com/index.php?threads/shattered-sphere-the-arcadian-free-march.3243/reader/page-2
        # discard tmcat_num -- the-sietch.com doesn't have multiple
        # threadmark categories yet.
        return self.story.getMetadata('storyUrl')+'reader/page-'+unicode(reader_page_num)

# XXX different threadmarks categories
