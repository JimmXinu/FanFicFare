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
import sys
import threading
import logging
logger = logging.getLogger(__name__)

from ..six import text_type as unicode
from ..six import ensure_text

from .base_fetcher import FetcherResponse
from .decorators import FetcherDecorator
from .log import make_log

import pickle
if sys.version_info < (2, 7):
    sys.exit('This program requires Python 2.7 or newer.')
elif sys.version_info < (3, 0):
    reload(sys)  # Reload restores 'hidden' setdefaultencoding method
    sys.setdefaultencoding("utf-8")
    def pickle_load(f):
        return pickle.load(f)
else: # > 3.0
    def pickle_load(f):
        return pickle.load(f,encoding="bytes")

class BasicCache(object):
    def __init__(self):
        self.cache_lock = threading.RLock()
        self.basic_cache = {}
        self.filename = None
        self.autosave = False
        if self.filename:
            try:
                self.load_cache()
            except:
                raise
                logger.debug("Failed to load cache(%s), going on without."%filename)

    ## used by CLI --save-cache dev debugging feature
    def set_autosave(self,autosave=False,filename=None):
        self.autosave = autosave
        self.filename = filename

    def load_cache(self,filename=None):
        # logger.debug("load cache(%s)"%(filename or self.filename))
        with self.cache_lock, open(filename or self.filename,'rb') as jin:
            self.basic_cache = pickle_load(jin)
            # logger.debug(self.basic_cache.keys())

    def save_cache(self,filename=None):
        with self.cache_lock, open(filename or self.filename,'wb') as jout:
            pickle.dump(self.basic_cache,jout,protocol=2)
            # logger.debug("save cache(%s)"%(filename or self.filename))

    def make_cachekey(self, url, parameters=None):
        with self.cache_lock:
            keylist=[url]
            if parameters != None:
                keylist.append('&'.join('{0}={1}'.format(key, val) for key, val in sorted(parameters.items())))
            return unicode('?'.join(keylist))

    def has_cachekey(self,cachekey):
        with self.cache_lock:
            return cachekey in self.basic_cache

    def get_from_cache(self,cachekey):
        with self.cache_lock:
            return self.basic_cache.get(cachekey,None)

    def set_to_cache(self,cachekey,data,redirectedurl):
        with self.cache_lock:
            self.basic_cache[cachekey] = (data,ensure_text(redirectedurl))
            # logger.debug("set_to_cache %s->%s"%(cachekey,ensure_text(redirectedurl)))
            if self.autosave and self.filename:
                self.save_cache()

class BasicCacheDecorator(FetcherDecorator):
    def __init__(self,cache):
        super(BasicCacheDecorator,self).__init__()
        self.cache = cache

    def fetcher_do_request(self,
                           fetcher,
                           chainfn,
                           method,
                           url,
                           parameters=None,
                           referer=None,
                           usecache=True,
                           image=False):
        '''
        When should cache be cleared or not used? logins, primarily
        Note that usecache=False prevents lookup, but cache still saves
        result
        '''
        # logger.debug("BasicCacheDecorator fetcher_do_request")
        cachekey=self.cache.make_cachekey(url, parameters)

        hit = usecache and self.cache.has_cachekey(cachekey) and not cachekey.startswith('file:')
        logger.debug(make_log('BasicCache',method,url,hit=hit))
        if hit:
            data,redirecturl = self.cache.get_from_cache(cachekey)
            # logger.debug("from_cache %s->%s"%(cachekey,redirecturl))
            return FetcherResponse(data,redirecturl=redirecturl,fromcache=True)

        fetchresp = chainfn(
            method,
            url,
            parameters=parameters,
            referer=referer,
            usecache=usecache,
            image=image)

        data = fetchresp.content

        ## don't re-cache, which includes file://, marked fromcache
        ## down in RequestsFetcher.  I can foresee using the dev CLI
        ## saved-cache and wondering why file changes aren't showing
        ## up.
        if not fetchresp.fromcache:
            self.cache.set_to_cache(cachekey,data,fetchresp.redirecturl)
        return fetchresp

