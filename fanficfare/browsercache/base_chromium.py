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

from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

from ..exceptions import BrowserCacheException

from . import BaseBrowserCache

## difference in seconds between Jan 1 1601 and Jan 1 1970.  Chrome
## caches (so far) have kept time stamps as microseconds since
## 1-1-1601 a Windows/Cobol thing.
EPOCH_DIFFERENCE = 11644473600

class BaseChromiumCache(BaseBrowserCache):
    def __init__(self, *args, **kargs):
        """Constructor for BaseChromiumCache"""
        super(BaseChromiumCache,self).__init__(*args, **kargs)
#        logger.debug("Using BaseChromiumCache")

    # WebToEpub: akiljllkbielkidmammnifcnibaigelm appears to be a UID.
    # 1/0/_dk_chrome-extension://akiljllkbielkidmammnifcnibaigelm chrome-extension://akiljllkbielkidmammnifcnibaigelm https://www.fanfiction.net/s/11377932/2/Guilt
    # 1/0/_dk_chrome-extension://akiljllkbielkidmammnifcnibaigelm chrome-extension://akiljllkbielkidmammnifcnibaigelm https://www.fanfiction.net/s/14161667/10/That-Time-I-Was-Reincarnated-In-Brockton-Bay
    def make_keys(self,url):
        (scheme, domain, url) = self.make_key_parts(url)
        return [ '1/0/_dk_'+scheme+'://'+domain+' '+scheme+'://'+domain+' '+url,
                 '1/0/_dk_chrome-extension://akiljllkbielkidmammnifcnibaigelm chrome-extension://akiljllkbielkidmammnifcnibaigelm '+url
                 ]

    def make_age(self,response_time):
        return int(response_time/1000000)-EPOCH_DIFFERENCE
