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

from functools import partial
import threading

from urllib3.util.retry import Retry
import requests
from requests.exceptions import HTTPError as RequestsHTTPError
from requests.adapters import HTTPAdapter
from requests_file import FileAdapter

import cloudscraper
from cloudscraper.exceptions import CloudflareException

from . import exceptions

logger = logging.getLogger(__name__)

## makes requests/cloudscraper dump req/resp headers.
# import http.client as http_client
# http_client.HTTPConnection.debuglevel = 5

class FetcherDecorator(object):
    def __init__(self):
        pass

    def decorate_fetcher(self,fetcher):
        # replace fetcher's do_request with a func that wraps it.
        # can be chained.
        fetcher.do_request = partial(self.fetcher_do_request,
                                     fetcher,
                                     fetcher.do_request)

    def fetcher_do_request(self,
                           fetcher,
                           chainfn,
                           method,
                           url,
                           parameters=None,
                           extrasleep=None,
                           referer=None,
                           usecache=True):
        ## can use fetcher.getConfig()/getConfigList().
        fetchresp = chainfn(
            method,
            url,
            parameters=parameters,
            extrasleep=extrasleep,
            referer=referer,
            usecache=usecache)

        return fetchresp

class ProgressBarDecorator(FetcherDecorator):
    def fetcher_do_request(self,
                           fetcher,
                           chainfn,
                           method,
                           url,
                           parameters=None,
                           extrasleep=None,
                           referer=None,
                           usecache=True):
        logger.debug("ProgressBarDecorator fetcher_do_request")
        fetchresp = chainfn(
            method,
            url,
            parameters=parameters,
            extrasleep=extrasleep,
            referer=referer,
            usecache=usecache)
        ## added ages ago for CLI to give a line of dots showing it's
        ## doing something.
        logger.debug("..")
        sys.stdout.write('.')
        sys.stdout.flush()
        return fetchresp

class SleepDecorator(FetcherDecorator):
    def __init__(self):
        super(SleepDecorator,self).__init__()
        self.sleep_override = None

    def decorate_fetcher(self,fetcher):
        super(SleepDecorator,self).decorate_fetcher(fetcher)

    ## used by plugin for ffnet variable timing
    def set_sleep_override(self,val):
        logger.debug("\n===========\n set sleep time %s\n==========="%val)
        self.sleep_override = val

    def fetcher_do_request(self,
                           fetcher,
                           chainfn,
                           method,
                           url,
                           parameters=None,
                           extrasleep=None,
                           referer=None,
                           usecache=True):
        logger.debug("SleepDecorator fetcher_do_request")
        fetchresp = chainfn(
            method,
            url,
            parameters=parameters,
            extrasleep=extrasleep,
            referer=referer,
            usecache=usecache)

        # don't sleep cached results.  Usually MemCache results will
        # be before sleep, but check fetchresp.fromcache for file://
        # and other intermediate caches.
        if not fetchresp.fromcache:
            t = None
            if extrasleep:
                logger.debug("extra sleep:%s"%extrasleep)
                time.sleep(float(extrasleep))
            if self.sleep_override:
                t = float(self.sleep_override)
            elif fetcher.getConfig('slow_down_sleep_time'):
                t = float(fetcher.getConfig('slow_down_sleep_time'))
            ## sleep randomly between 0.5 time and 1.5 time.
            ## So 8 would be between 4 and 12.
            if t:
                rt = random.uniform(t*0.5, t*1.5)
                logger.debug("random sleep(%0.2f-%0.2f):%0.2f"%(t*0.5, t*1.5,rt))
                time.sleep(rt)
        else:
            logger.debug("Skip sleeps")

        return fetchresp

class BasicCache(object):
    def __init__(self,filename=None):
        self.cache_lock = threading.RLock()
        self.pagecache = {}
        self.filename = filename
        if self.filename:
            try:
                self.load_cache()
            except:
                raise
                logger.debug("Failed to load cache(%s), going on without."%filename)

    def load_cache(self,filename=None):
        logger.debug(filename or self.filename)
        with open(filename or self.filename,'rb') as jin:
            self.pagecache = pickle_load(jin)
            logger.debug(self.pagecache.keys())

    def save_cache(self,filename=None):
        logger.debug(filename or self.filename)
        with open(filename or self.filename,'wb') as jout:
            pickle.dump(self.pagecache,jout,protocol=2)
            logger.debug("wrote")

    def make_cachekey(self, url, parameters=None):
        with self.cache_lock:
            keylist=[url]
            if parameters != None:
                keylist.append('&'.join('{0}={1}'.format(key, val) for key, val in sorted(parameters.items())))
            return unicode('?'.join(keylist))

    def has_cachekey(self,cachekey):
        with self.cache_lock:
            return cachekey in self.pagecache

    def get_from_cache(self,cachekey):
        with self.cache_lock:
            return self.pagecache.get(cachekey,None)

    def set_to_cache(self,cachekey,data,redirectedurl):
        with self.cache_lock:
            self.pagecache[cachekey] = (data,ensure_text(redirectedurl))
            logger.debug("set_to_cache:%s"%self.filename)
            if self.filename:
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
                           extrasleep=None,
                           referer=None,
                           usecache=True):
        '''
        When should cache be cleared or not used? logins, primarily
        Note that usecache=False prevents lookup, but cache still saves
        result
        '''
        logger.debug("BasicCacheDecorator fetcher_do_request")
        cachekey=self.cache.make_cachekey(url, parameters)

        if usecache and self.cache.has_cachekey(cachekey) and not cachekey.startswith('file:'):
            logger.debug("\n>>>> pagecache(%s) HIT: %s"%(method,safe_url(cachekey)))
            data,redirecturl = self.cache.get_from_cache(cachekey)
            return FetcherResponse(data,redirecturl=redirecturl,fromcache=True)
        logger.debug("\n<<<< pagecache(%s) MISS: %s"%(method,safe_url(cachekey)))

        fetchresp = chainfn(
            method,
            url,
            parameters=parameters,
            extrasleep=extrasleep,
            referer=referer,
            usecache=usecache)

        data = fetchresp.content

        ## don't re-cache, which includes file://, marked fromcache
        ## down in RequestsFetcher.  I can foresee using the dev CLI
        ## saved-cache and wondering why file changes aren't showing
        ## up.
        if not fetchresp.fromcache:
            self.cache.set_to_cache(cachekey,data,fetchresp.redirecturl)
            if url != fetchresp.redirecturl: # cache both?
                self.cache.set_to_cache(cachekey,data,url)
        return fetchresp

class FetcherResponse(object):
    def __init__(self,content,redirecturl=None,fromcache=False):
        self.content = content
        self.redirecturl = redirecturl
        self.fromcache = fromcache

class Fetcher(object):
    def __init__(self,getConfig_fn,getConfigList_fn):
        self.getConfig = getConfig_fn
        self.getConfigList = getConfigList_fn

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

    def do_request(self, method, url,
                    parameters=None,
                    extrasleep=None,
                    referer=None,
                    usecache=True):
        '''
        extrasleep is primarily for ffnet adapter which has extra
        sleeps.  Passed into fetchs so it can be bypassed when
        cache hits.
        '''
        logger.debug("fetcher do_request")
        headers = self.make_headers(url,referer=referer)
        fetchresp = self.request(method,url,
                                 headers=headers,
                                 parameters=parameters)
        data = fetchresp.content
        self.save_cookiejar()
        return fetchresp

    def condition_url(self, url):
        if not url.startswith('file:'): # file fetches fail on + for space
            url = quote_plus(ensure_binary(url),safe=';/?:@&=+$,%&#')
        if self.getConfig('force_https'): ## For developer testing only.
            url = url.replace("http:","https:")
        return url

    def post_request(self, url,
                     parameters=None,
                     extrasleep=None,
                     usecache=True):
        fetchresp = self.do_request('POST',
                                     self.condition_url(url),
                                     parameters=parameters,
                                     extrasleep=extrasleep,
                                     usecache=usecache)
        return fetchresp.content

    def get_request_redirected(self, url,
                               extrasleep=None,
                               referer=None,
                               usecache=True):
        fetchresp = self.do_request('GET',
                                     self.condition_url(url),
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
            # consider 'cached' if from file.
            fromcache = resp.url.startswith('file:')
            return FetcherResponse(resp.content,
                                   resp.url,
                                   fromcache)
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
