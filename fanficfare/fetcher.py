# -*- coding: utf-8 -*-

# Copyright 2021 FanFicFare team
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
import re
import random

# py2 vs py3 transition
from .six.moves.urllib.parse import quote_plus
from .six.moves.http_cookiejar import LWPCookieJar
from .six import text_type as unicode
from .six import ensure_binary, ensure_text

import time
import logging
import sys
import pickle
from functools import wraps

## isn't found in plugin when only imported down below inside
## get_requests_session()
import requests
from requests_file import FileAdapter
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import cloudscraper
from cloudscraper.exceptions import CloudflareException

from . import exceptions
from requests.exceptions import HTTPError as RequestsHTTPError

logger = logging.getLogger(__name__)

## makes requests/cloudscraper dump req/resp headers.
# import http.client as http_client
# http_client.HTTPConnection.debuglevel = 5

class Cache(object):
    def __init__(self):
        self.pagecache = self.get_empty_pagecache()
        self.save_cache_file = None

    def get_empty_pagecache(self):
        return {}

    def _get_pagecache(self):
        return self.pagecache

    def set_pagecache(self,d,save_cache_file=None):
        self.save_cache_file = save_cache_file
        self.pagecache=d

    def make_cachekey(self, url, parameters=None):
        keylist=[url]
        if parameters != None:
            keylist.append('&'.join('{0}={1}'.format(key, val) for key, val in sorted(parameters.items())))
        return unicode('?'.join(keylist))

    def has_cachekey(self,cachekey):
        return self.use_pagecache and cachekey in self._get_pagecache()

    def get_from_cache(self,cachekey):
        if self.use_pagecache:
            return self._get_pagecache().get(cachekey)
        else:
            return None

    def set_to_cache(self,cachekey,data,redirectedurl):
        if self.use_pagecache:
            self._get_pagecache()[cachekey] = (data,ensure_text(redirectedurl))
            if self.save_cache_file:
                with open(self.save_cache_file,'wb') as jout:
                    pickle.dump(self._get_pagecache(),jout,protocol=2)

class FetcherResponse(object):
    def __init__(self,content,redirecturl=None,fromcache=False):
        self.content = content
        self.redirecturl = redirecturl
        self.fromcache = fromcache

class Fetcher(object):
    def __init__(self,getConfig_fn,getConfigList_fn):
        self.getConfig = getConfig_fn
        self.getConfigList = getConfigList_fn

        self.override_sleep = None

        self.cache = Cache()

        self.cookiejar = None

    def get_cookiejar(self,filename=None):
        if self.cookiejar is None:
            self.cookiejar = LWPCookieJar(filename=filename)
            if filename:
                try:
                    self.cookiejar.load(ignore_discard=True, ignore_expires=True)
                except:
                    logger.debug("Failed to load cookiejar(%s), going on without."%filename)
        return self.cookiejar

    def set_cookiejar(self,cookiejar):
        self.cookiejar = cookiejar

    def load_cookiejar(self,filename):
        '''
        Needs to be called after adapter create, but before any fetchs
        are done.  Takes file *name*.
        '''
        # get_cookiejar() creates an empty jar if not already.
        self.get_cookiejar().load(filename, ignore_discard=True, ignore_expires=True)

    def save_cookiejar(self,filename=None):
        if filename or self.get_cookiejar().filename:
            ## raises exception on save w/o filename
            self.get_cookiejar().save(filename or self.get_cookiejar().filename,
                                      ignore_discard=True,
                                      ignore_expires=True)

    def _progressbar(self):
        if self.getConfig('progressbar'):
            sys.stdout.write('.')
            sys.stdout.flush()

    # used by plugin for ffnet variable timing
    def set_sleep(self,val):
        # logger.debug("\n===========\n set sleep time %s\n==========="%val)
        self.override_sleep = val

    def do_sleep(self,extrasleep=None):
        if extrasleep:
            logger.debug("extra sleep:%s"%extrasleep)
            time.sleep(float(extrasleep))
        t = None
        if self.override_sleep:
            t = float(self.override_sleep)
        elif self.getConfig('slow_down_sleep_time'):
            t = float(self.getConfig('slow_down_sleep_time'))
        ## sleep randomly between 0.5 time and 1.5 time.
        ## So 8 would be between 4 and 12.
        if t:
            rt = random.uniform(t*0.5, t*1.5)
            logger.debug("random sleep(%0.2f-%0.2f):%0.2f"%(t*0.5, t*1.5,rt))
            time.sleep(rt)

    def make_headers(self,url,referer=None):
        headers = {}
        headers['User-Agent']=self.getConfig('user_agent')
        if referer:
            headers['Referer']=referer
        # if "xf2test" in url:
        #     import base64
        #     base64string = base64.encodestring(b"sbreview2019:Fs2PwuVE9").replace(b'\n', b'')
        #     headers['Authorization']="Basic %s" % base64string
        #     logger.debug("http login for SB xf2test")
        return headers

    def request(self,*args,**kargs):
        '''Returns a FetcherResponse regardless of mechanism'''
        raise NotImplementedError()

    def _do_request(self, method, url,
                    parameters=None,
                    extrasleep=None,
                    referer=None,
                    usecache=True):
        '''
        When should cache be cleared or not used? logins...

        extrasleep is primarily for ffnet adapter which has extra
        sleeps.  Passed into fetchs so it can be bypassed when
        cache hits.
        '''
        if not url.startswith('file:'): # file fetches fail on + for space
            url = quote_plus(ensure_binary(url),safe=';/?:@&=+$,%&#')

        if self.getConfig('force_https'): ## For developer testing only.
            url = url.replace("http:","https:")
        cachekey=self.cache.make_cachekey(url, parameters)
        if usecache and self.cache.has_cachekey(cachekey) and not cachekey.startswith('file:'):
            logger.debug("#####################################\npagecache(%s) HIT: %s"%(method,safe_url(cachekey)))
            data,redirecturl = self.cache.get_from_cache(cachekey)
            return FetcherResponse(data,redirecturl=redirecturl,fromcache=True)

        logger.debug("#####################################\npagecache(%s) MISS: %s"%(method,safe_url(cachekey)))
        if not cachekey.startswith('file:'): # don't sleep for file: URLs.
            self.do_sleep(extrasleep)

        headers = self.make_headers(url,referer=referer)
        fetchresp = self.request(method,url,
                                 headers=headers,
                                 parameters=parameters)
        data = fetchresp.content

        self.save_cookiejar()

        self._progressbar()
        self.cache.set_to_cache(cachekey,data,fetchresp.redirecturl)
        if url != fetchresp.redirecturl: # cache both?
            self.cache.set_to_cache(cachekey,data,url)
        return fetchresp

    def post_request(self, url,
                     parameters=None,
                     extrasleep=None,
                     usecache=True):
        fetchresp = self._do_request('POST',url,
                                     parameters=parameters,
                                     extrasleep=extrasleep,
                                     usecache=usecache)
        return fetchresp.content

    def get_request_redirected(self, url,
                               extrasleep=None,
                               referer=None,
                               usecache=True):
        fetchresp = self._do_request('GET',url,
                                     extrasleep=extrasleep,
                                     referer=referer,
                                     usecache=usecache)
        return (fetchresp.content,fetchresp.redirecturl)

class RequestsFetcher(Fetcher):
    def __init__(self,getConfig_fn,getConfigList_fn):
        super(RequestsFetcher,self).__init__(getConfig_fn,getConfigList_fn)
        self.requests_session = None
        self.retries = self.make_retries()

    def set_cookiejar(self,cookiejar):
        super(RequestsFetcher,self).set_cookiejar(cookiejar)
        ## in case where cookiejar is set second
        if  self.requests_session:
            self.requests_session.cookies = self.cookiejar

    def make_retries(self):
        return Retry(total=4,
                            other=0, # rather fail SSL errors/etc quick
                            backoff_factor=2,# factor 2=4,8,16sec
                            allowed_methods={'GET','POST'},
                            status_forcelist={413, 429, 500, 502, 503, 504},
                            raise_on_status=False) # to match w/o retries behavior

    def make_sesssion(self):
        return requests.Session()

    def do_mounts(self,session):
        session.mount('https://', HTTPAdapter(max_retries=self.retries))
        session.mount('http://', HTTPAdapter(max_retries=self.retries))
        session.mount('file://', FileAdapter())

    def get_requests_session(self):
        if not self.requests_session:
            self.requests_session = self.make_sesssion()
            self.do_mounts(self.requests_session)
            ## in case where cookiejar is set first
            if self.cookiejar is not None: # present but *empty* jar==False
                self.requests_session.cookies = self.cookiejar
        return self.requests_session

    def request(self,method,url,headers=None,parameters=None):
        '''Returns a FetcherResponse regardless of mechanism'''
        if method not in ('GET','POST'):
            raise NotImplementedError()
        try:
            ## resp = requests Response object
            verify = not self.getConfig('use_ssl_unverified_context',False)
            resp = self.get_requests_session().request(method, url,
                                                       headers=headers,
                                                       data=parameters,
                                                       verify=verify)
            logger.debug("response code:%s"%resp.status_code)
            resp.raise_for_status() # raises RequestsHTTPError if error code.
            return FetcherResponse(resp.content,
                                   resp.url)
        except RequestsHTTPError as e:
            ## not RequestsHTTPError(requests.exceptions.HTTPError) or
            ## .six.moves.urllib.error import HTTPError because we
            ## want code *and* content for that one trekfanfiction
            ## catch.
            raise exceptions.HTTPErrorFFF(
                url,
                e.response.status_code,
                e.args[0],# error_msg
                e.response.content # data
                )

    def __del__(self):
        if self.requests_session is not None:
            self.requests_session.close()


class CloudScraperFetcher(RequestsFetcher):
    def __init__(self,getConfig_fn,getConfigList_fn):
        super(CloudScraperFetcher,self).__init__(getConfig_fn,getConfigList_fn)

    def make_sesssion(self):
        logger.debug("initializing cloudscraper")
        return cloudscraper.CloudScraper(browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False,
                'desktop': True,
                })

    def do_mounts(self,session):
        super(CloudScraperFetcher,self).do_mounts(session)
        ## CipherSuiteAdapter adapter replaces HTTPAdapter
        session.mount('https://',cloudscraper.CipherSuiteAdapter(
                cipherSuite=session.cipherSuite,
                ssl_context=session.ssl_context,
                source_address=session.source_address,
                max_retries=self.retries))

    def make_headers(self,url,referer=None):
        headers = super(CloudScraperFetcher,self).make_headers(url,
                                                               referer=referer)
        ## let cloudscraper do its thing with UA.
        if 'User-Agent' in headers:
            del headers['User-Agent']
        return headers

    def request(self,method,url,headers=None,parameters=None):
        try:
            return super(CloudScraperFetcher,self).request(method,url,headers,parameters)
        except CloudflareException as cfe:
            ## cloudscraper exception messages can appear to
            ## come from FFF and cause confusion.
            msg = unicode(cfe).replace(' in the opensource (free) version','...')
            raise exceptions.FailedToDownload('cloudscraper reports: "%s"'%msg)

# .? for AO3's ']' in param names.
safe_url_re = re.compile(r'(?P<attr>(pass(word)?|name|login).?=)[^&]*(?P<amp>&|$)',flags=re.MULTILINE)
def safe_url(url):
    # return url with password attr (if present) obscured.
    return re.sub(safe_url_re,r'\g<attr>XXXXXXXX\g<amp>',url)
