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

import threading
import traceback
import time
import webbrowser
from ..six.moves.urllib.parse import urlparse

from .. import exceptions

from .base_fetcher import FetcherResponse
from .decorators import FetcherDecorator
from .log import make_log

domain_open_tries = dict()

class BrowserCacheDecorator(FetcherDecorator):
    def __init__(self,cache):
        super(BrowserCacheDecorator,self).__init__()
        self.cache = cache
        self.cache_lock = threading.RLock()

    def fetcher_do_request(self,
                           fetcher,
                           chainfn,
                           method,
                           url,
                           parameters=None,
                           referer=None,
                           usecache=True):
        with self.cache_lock:
            # logger.debug("BrowserCacheDecorator fetcher_do_request")
            fromcache=True
            if usecache:
                try:
                    d = self.cache.get_data(url)

                    ## XXX - should there be a fail counter / limit for
                    ##       cases of pointing to wrong cache/etc?

                    parsedUrl = urlparse(url)

                    sleeptries = [ 2, 5 ]
                    while( fetcher.getConfig("use_browser_cache_only") and
                           fetcher.getConfig("open_pages_in_browser",False) and
                           not d and sleeptries
                           and domain_open_tries.get(parsedUrl.netloc,0) < fetcher.getConfig("open_browser_pages_tries_limit",6) ):
                        logger.debug("\n\nopen page in browser: %s\ntries:%s\n"%(url,domain_open_tries.get(parsedUrl.netloc,0)))
                        webbrowser.open(url)
                        domain_open_tries[parsedUrl.netloc] = domain_open_tries.get(parsedUrl.netloc,0) + 1
                        fromcache=False
                        if parsedUrl.netloc not in domain_open_tries:
                            logger.debug("First time for (%s) extra sleep"%parsedUrl.netloc)
                            time.sleep(5)
                        time.sleep(sleeptries.pop(0))
                        d = self.cache.get_data(url)
                        # logger.debug(d)
                except Exception as e:
                    logger.debug(traceback.format_exc())
                    raise exceptions.BrowserCacheException("Browser Cache Failed to Load with error '%s'"%e)

                # had a d = b'' which showed HIT, but failed.
                logger.debug(make_log('BrowserCache',method,url,True if d else False))
                # logger.debug(d)
                if d:
                    domain_open_tries[parsedUrl.netloc] = 0
                    logger.debug("fromcache:%s"%fromcache)
                    return FetcherResponse(d,redirecturl=url,fromcache=fromcache)

            if fetcher.getConfig("use_browser_cache_only"):
                raise exceptions.HTTPErrorFFF(
                    url,
                    428, # 404 & 410 trip StoryDoesNotExist
                         # 428 ('Precondition Required') gets the
                         # error_msg through to the user.
                    "Page not found or expired in Browser Cache (see FFF setting browser_cache_age_limit)",# error_msg
                    None # data
                    )
            return chainfn(
                method,
                url,
                parameters=parameters,
                referer=referer,
                usecache=usecache)

