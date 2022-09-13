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
import sys
import re
import random

import time
import logging
logger = logging.getLogger(__name__)

# py2 vs py3 transition
from .six.moves.urllib.parse import quote_plus
from .six.moves.http_cookiejar import LWPCookieJar, MozillaCookieJar
from .six import text_type as unicode
from .six import ensure_binary, ensure_text

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
                           referer=None,
                           usecache=True):
        ## can use fetcher.getConfig()/getConfigList().
        fetchresp = chainfn(
            method,
            url,
            parameters=parameters,
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
                           referer=None,
                           usecache=True):
        # logger.debug("ProgressBarDecorator fetcher_do_request")
        fetchresp = chainfn(
            method,
            url,
            parameters=parameters,
            referer=referer,
            usecache=usecache)
        ## added ages ago for CLI to give a line of dots showing it's
        ## doing something.
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
        # logger.debug("\n===========\n set sleep time %s\n==========="%val)
        self.sleep_override = val

    def fetcher_do_request(self,
                           fetcher,
                           chainfn,
                           method,
                           url,
                           parameters=None,
                           referer=None,
                           usecache=True):
        # logger.debug("SleepDecorator fetcher_do_request")
        fetchresp = chainfn(
            method,
            url,
            parameters=parameters,
            referer=referer,
            usecache=usecache)

        # don't sleep cached results.  Usually MemCache results will
        # be before sleep, but check fetchresp.fromcache for file://
        # and other intermediate caches.
        if not fetchresp.fromcache:
            t = None
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

        return fetchresp

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
                           usecache=True):
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
            usecache=usecache)

        data = fetchresp.content

        ## don't re-cache, which includes file://, marked fromcache
        ## down in RequestsFetcher.  I can foresee using the dev CLI
        ## saved-cache and wondering why file changes aren't showing
        ## up.
        if not fetchresp.fromcache:
            self.cache.set_to_cache(cachekey,data,fetchresp.redirecturl)
        return fetchresp

class BrowserCacheDecorator(FetcherDecorator):
    def __init__(self,cache):
        super(BrowserCacheDecorator,self).__init__()
        self.cache = cache

    def fetcher_do_request(self,
                           fetcher,
                           chainfn,
                           method,
                           url,
                           parameters=None,
                           referer=None,
                           usecache=True):
        # logger.debug("BrowserCacheDecorator fetcher_do_request")
        if usecache:
            d = self.cache.get_data(url)
            logger.debug(make_log('BrowserCache',method,url,d is not None))
            if d:
                return FetcherResponse(d,redirecturl=url,fromcache=True)
        ## make use_browser_cache true/false/only?
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

class FetcherResponse(object):
    def __init__(self,content,redirecturl=None,fromcache=False,json=None):
        self.content = content
        self.redirecturl = redirecturl
        self.fromcache = fromcache
        self.json = json

class Fetcher(object):
    def __init__(self,getConfig_fn,getConfigList_fn):
        self.getConfig = getConfig_fn
        self.getConfigList = getConfigList_fn

        self.cookiejar = None

    def get_cookiejar(self,filename=None,mozilla=False):

        if self.cookiejar is None:
            if mozilla:
                ParentCookieJar = MozillaCookieJar
            else:
                ParentCookieJar = LWPCookieJar

            class BasicCookieJar(ParentCookieJar,object):
                def __init__(self,*args,**kargs):
                    super(BasicCookieJar,self).__init__(*args,**kargs)
                    self.autosave = False
                    # self.filename from parent(s)

                ## used by CLI --save-cache dev debugging feature
                def set_autosave(self,autosave=False,filename=None):
                    self.autosave = autosave
                    self.filename = filename

                def load_cookiejar(self,filename=None):
                    self.load(self.filename or filename,
                              ignore_discard=True,
                              ignore_expires=True)

                def save_cookiejar(self,filename=None):
                    self.save(filename or self.filename,
                              ignore_discard=True,
                              ignore_expires=True)


            self.cookiejar = BasicCookieJar(filename=filename)
            if filename:
                try:
                    self.cookiejar.load(ignore_discard=True, ignore_expires=True)
                except:
                    logger.debug("Failed to load cookiejar(%s), going on without."%filename)
        return self.cookiejar

    def set_cookiejar(self,cookiejar):
        self.cookiejar = cookiejar

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
                    referer=None,
                    usecache=True):
        # logger.debug("fetcher do_request")
        # logger.debug(self.get_cookiejar())
        headers = self.make_headers(url,referer=referer)
        fetchresp = self.request(method,url,
                                 headers=headers,
                                 parameters=parameters)
        data = fetchresp.content
        if self.get_cookiejar().autosave and self.get_cookiejar().filename:
            self.get_cookiejar().save_cookiejar()
        return fetchresp

    def condition_url(self, url):
        if not url.startswith('file:'): # file fetches fail on + for space
            url = quote_plus(ensure_binary(url),safe=';/?:@&=+$,%&#')
        if self.getConfig('force_https'): ## For developer testing only.
            url = url.replace("http:","https:")
        return url

    def post_request(self, url,
                     parameters=None,
                     usecache=True):
        fetchresp = self.do_request('POST',
                                     self.condition_url(url),
                                     parameters=parameters,
                                     usecache=usecache)
        return fetchresp.content

    def get_request_redirected(self, url,
                               referer=None,
                               usecache=True):
        fetchresp = self.do_request('GET',
                                     self.condition_url(url),
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
        if self.getConfig('use_ssl_default_seclevelone',False):
            import ssl
            class TLSAdapter(HTTPAdapter):
                def init_poolmanager(self, *args, **kwargs):
                    ctx = ssl.create_default_context()
                    ctx.set_ciphers('DEFAULT@SECLEVEL=1')
                    kwargs['ssl_context'] = ctx
                    return super(TLSAdapter, self).init_poolmanager(*args, **kwargs)
            session.mount('https://', TLSAdapter(max_retries=self.retries))
        else:
            session.mount('https://', HTTPAdapter(max_retries=self.retries))
        session.mount('http://', HTTPAdapter(max_retries=self.retries))
        session.mount('file://', FileAdapter())
        # logger.debug("Session Proxies Before:%s"%session.proxies)
        ## try to get OS proxy settings via Calibre
        try:
            # logger.debug("Attempting to collect proxy settings through Calibre")
            from calibre import get_proxies
            try:
                proxies = get_proxies()
                if proxies:
                    logger.debug("Calibre Proxies:%s"%proxies)
                session.proxies.update(proxies)
            except Exception as e:
                logger.error("Failed during proxy collect/set %s"%e)
        except:
            pass
        if self.getConfig('http_proxy'):
            session.proxies['http'] = self.getConfig('http_proxy')
        if self.getConfig('https_proxy'):
            session.proxies['https'] = self.getConfig('https_proxy')
        if session.proxies:
            logger.debug("Session Proxies After INI:%s"%session.proxies)

    def get_requests_session(self):
        if not self.requests_session:
            self.requests_session = self.make_sesssion()
            self.do_mounts(self.requests_session)
            ## in case where cookiejar is set first
            if self.cookiejar is not None: # present but *empty* jar==False
                self.requests_session.cookies = self.cookiejar
        return self.requests_session

    def use_verify(self):
        return not self.getConfig('use_ssl_unverified_context',False)

    def request(self,method,url,headers=None,parameters=None,json=None):
        '''Returns a FetcherResponse regardless of mechanism'''
        if method not in ('GET','POST'):
            raise NotImplementedError()
        try:
            logger.debug(make_log('RequestsFetcher',method,url,hit='REQ',bar='-'))
            ## resp = requests Response object
            timeout = 60.0
            try:
                timeout = float(self.getConfig("connect_timeout",timeout))
            except Exception as e:
                logger.error("connect_timeout setting failed: %s -- Using default value(%s)"%(e,timeout))
            resp = self.get_requests_session().request(method, url,
                                                       headers=headers,
                                                       data=parameters,
                                                       json=json,
                                                       verify=self.use_verify(),
                                                       timeout=timeout)
            logger.debug("response code:%s"%resp.status_code)
            resp.raise_for_status() # raises RequestsHTTPError if error code.
            # consider 'cached' if from file.
            fromcache = resp.url.startswith('file:')
            ## currently only saving response json if there input was json.
            ## for flaresolverr_proxy
            resp_json = None
            if json:
                try:
                    resp_json = resp.json()
                except:
                    pass
            # logger.debug(resp_json)
            return FetcherResponse(resp.content,
                                   resp.url,
                                   fromcache,
                                   resp_json)
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

    def use_verify(self):
        ## cloudscraper doesn't work with verify=False, throws an
        ## error about "Cannot set verify_mode to CERT_NONE when
        ## check_hostname is enabled."
        if self.getConfig('use_ssl_unverified_context',False):
            logger.warning("use_ssl_unverified_context:true ignored when use_cloudscraper:true")
        return True

    def request(self,method,url,headers=None,parameters=None):
        try:
            return super(CloudScraperFetcher,self).request(method,url,headers,parameters)
        except CloudflareException as cfe:
            ## cloudscraper exception messages can appear to
            ## come from FFF and cause confusion.
            msg = unicode(cfe).replace(' in the opensource (free) version','...')
            raise exceptions.FailedToDownload('cloudscraper reports: (%s) \nSee https://github.com/JimmXinu/FanFicFare/wiki/BrowserCacheFeature for a possible workaround.'%msg)

# .? for AO3's ']' in param names.
safe_url_re = re.compile(r'(?P<attr>(pass(word)?|name|login).?=)[^&]*(?P<amp>&|$)',flags=re.MULTILINE)
def safe_url(url):
    # return url with password attr (if present) obscured.
    return re.sub(safe_url_re,r'\g<attr>XXXXXXXX\g<amp>',url)

## Yes, I care about this debug out more than I really should.  But I
## do watch it alot.
def make_log(where,method,url,hit=True,bar='=',barlen=10):
    return "\n%(bar)s %(hit)s (%(method)s) %(where)s\n%(url)s"%{
        'bar':bar*barlen,
        'where':where,
        'method':method,
        'url':safe_url(url),
        'hit':'HIT' if hit==True else 'MISS' if hit==False else hit}
