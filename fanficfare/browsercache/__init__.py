# -*- coding: utf-8 -*-

# Copyright 2022 FanFicFare team
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

import os
from .basebrowsercache import BrowserCacheException, BaseBrowserCache
## SimpleCache and BlockfileCache are both flavors of cache used by Chrome.
from .simplecache import SimpleCache
from .blockfilecache import BlockfileCache
from .firefoxcache2 import FirefoxCache2

import logging
logger = logging.getLogger(__name__)

class BrowserCache(object):
    """
    Class to read web browser cache
    This wrapper class contains the actual impl object.
    """
    def __init__(self, cache_dir, age_limit=-1):
        """Constructor for BrowserCache"""
        # import of child classes have to be inside the def to avoid circular import error
        for browser_cache_class in [SimpleCache, BlockfileCache, FirefoxCache2]:
            self.browser_cache_impl = browser_cache_class.new_browser_cache(cache_dir,age_limit=age_limit)
            if self.browser_cache_impl is not None:
                break
        if self.browser_cache_impl is None:
            raise BrowserCacheException("Directory does not contain a known browser cache type: '%s'"%
                                        os.path.abspath(cache_dir))

    def get_data(self, url):
        # logger.debug("get_data:%s"%url)
        d = self.browser_cache_impl.get_data(url)
        return d

    def load_cache(self,filename=None):
        self.browser_cache_impl.load_cache(filename)

    def save_cache(self,filename=None):
        self.browser_cache_impl.save_cache(filename)
