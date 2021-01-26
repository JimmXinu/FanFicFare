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
from .six.moves import http_cookiejar as cl
from .six import text_type as unicode
from .six import ensure_binary, ensure_text

import time
import logging
import sys
import pickle

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
from .six.moves.urllib.error import HTTPError

logger = logging.getLogger(__name__)

## makes requests/cloudscraper dump req/resp headers.
# import http.client as http_client
# http_client.HTTPConnection.debuglevel = 5

class Fetcher(object):
    def __init__(self,getConfig_fn,getConfigList_fn):
        self.getConfig = getConfig_fn
        self.getConfigList = getConfigList_fn

        self.use_pagecache = False # default to false for old adapters.

        self.override_sleep = None
        self.cookiejar = self.get_empty_cookiejar()
        self.requests_session = None

        self.pagecache = self.get_empty_pagecache()
        self.save_cache_file = None
        self.save_cookiejar_file = None


    def get_empty_cookiejar(self):
        return cl.LWPCookieJar()

    def get_cookiejar(self):
        return self.cookiejar

    def set_cookiejar(self,cj,save_cookiejar_file=None):
        self.cookiejar = cj
        self.save_cookiejar_file = save_cookiejar_file

    def load_cookiejar(self,filename):
        '''
        Needs to be called after adapter create, but before any fetchs
        are done.  Takes file *name*.
        '''
        self.get_cookiejar().load(filename, ignore_discard=True, ignore_expires=True)

    def get_empty_pagecache(self):
        return {}

    def get_pagecache(self):
        return self.pagecache

    def set_pagecache(self,d,save_cache_file=None):
        self.save_cache_file = save_cache_file
        self.pagecache=d

    def _get_cachekey(self, url, parameters=None, headers=None):
        keylist=[url]
        if parameters != None:
            keylist.append('&'.join('{0}={1}'.format(key, val) for key, val in sorted(parameters.items())))
        if headers != None:
            keylist.append('&'.join('{0}={1}'.format(key, val) for key, val in sorted(headers.items())))
        return unicode('?'.join(keylist))

    def _has_cachekey(self,cachekey):
        return self.use_pagecache and cachekey in self.get_pagecache()

    def _get_from_pagecache(self,cachekey):
        if self.use_pagecache:
            return self.get_pagecache().get(cachekey)
        else:
            return None

    def _set_to_pagecache(self,cachekey,data,redirectedurl):
        if self.use_pagecache:
            self.get_pagecache()[cachekey] = (data,ensure_text(redirectedurl))
            if self.save_cache_file:
                with open(self.save_cache_file,'wb') as jout:
                    pickle.dump(self.get_pagecache(),jout,protocol=2)
            if self.save_cookiejar_file:
                self.get_cookiejar().save(self.save_cookiejar_file)

    def _progressbar(self):
        if self.getConfig('progressbar'):
            sys.stdout.write('.')
            sys.stdout.flush()

    def get_requests_session(self):
        if not self.requests_session:

            ## set up retries.
            retries = Retry(total=4,
                            other=0, # rather fail SSL errors/etc quick
                            backoff_factor=2,# factor 2=4,8,16sec
                            allowed_methods={'GET','POST'},
                            status_forcelist={413, 429, 500, 502, 503, 504},
                            raise_on_status=False) # to match w/o retries behavior
            if self.getConfig('use_cloudscraper',False):
                ## ffnet adapter can't parse mobile output, so we only
                ## want desktop browser.  But cloudscraper then insists on
                ## a browser and platform, too.
                logger.debug("initializing cloudscraper")
                self.requests_session = cloudscraper.CloudScraper(browser={
                        'browser': 'chrome',
                        'platform': 'windows',
                        'mobile': False,
                        'desktop': True,
                        })
                ## CipherSuiteAdapter adapter replaced by HTTPAdapter
                ## if done as below.
                self.requests_session.mount('https://',
                                            cloudscraper.CipherSuiteAdapter(
                        cipherSuite=self.requests_session.cipherSuite,
                        ssl_context=self.requests_session.ssl_context,
                        source_address=self.requests_session.source_address,
                        max_retries=retries))
            else:
                ## CloudScraper is subclass of requests.Session.
                ## Hopefully everything one can do will work with the
                ## other.
                self.requests_session = requests.Session()
                self.requests_session.mount('https://', HTTPAdapter(max_retries=retries))
            self.requests_session.mount('http://', HTTPAdapter(max_retries=retries))
            self.requests_session.mount('file://', FileAdapter())

            self.requests_session.cookies = self.cookiejar

        return self.requests_session

    def __del__(self):
        if self.requests_session is not None:
            self.requests_session.close()

    # used by plugin for ffnet variable timing
    def set_sleep(self,val):
        logger.debug("\n===========\n set sleep time %s\n==========="%val)
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

    # Assumes application/x-www-form-urlencoded.  parameters, headers are dict()s
    def post_request(self, url,
                     parameters={},
                     headers={},
                     extrasleep=None,
                     usecache=True):
        '''
        When should cache be cleared or not used? logins...

        extrasleep is primarily for ffnet adapter which has extra
        sleeps.  Passed into fetchs so it can be bypassed when
        cache hits.
        '''
        url = quote_plus(ensure_binary(url),safe=';/?:@&=+$,%&#')

        if self.getConfig('force_https'): ## For developer testing only.
            url = url.replace("http:","https:")
        cachekey=self._get_cachekey(url, parameters, headers)
        if usecache and self._has_cachekey(cachekey) and not cachekey.startswith('file:'):
            logger.debug("#####################################\npagecache(POST) HIT: %s"%safe_url(cachekey))
            data,redirecturl = self._get_from_pagecache(cachekey)
            return data

        logger.debug("#####################################\npagecache(POST) MISS: %s"%safe_url(cachekey))
        if not cachekey.startswith('file:'): # don't sleep for file: URLs.
            self.do_sleep(extrasleep)

        if 'User-Agent' not in headers:
            headers['User-Agent']=self.getConfig('user_agent')

        if self.getConfig('use_cloudscraper',False):
            ## let cloudscraper do its thing with UA.
            if 'User-Agent' in headers:
                del headers['User-Agent']
        # logger.debug("POST http login for SB xf2test %s"%url)
        # if "xf2test" in url:
        #     import base64
        #     base64string = base64.encodestring(b"sbreview2019:Fs2PwuVE9").replace(b'\n', b'')
        #     headers['Authorization']=b"Basic %s" % base64string
        #     logger.debug("http login for SB xf2test")

        try:
            # logger.debug("requests_session.cookies:%s"%self.get_requests_session().cookies)
            resp = self.get_requests_session().post(url,
                                                    headers=dict(headers),
                                                    data=parameters,
                                                    verify=not self.getConfig('use_ssl_unverified_context',False))
            logger.debug("response code:%s"%resp.status_code)

            resp.raise_for_status() # raises RequestsHTTPError if error code.
            data = resp.content
        except CloudflareException as e:
            msg = unicode(e).replace(' in the opensource (free) version','...')
            raise exceptions.FailedToDownload('cloudscraper reports: "%s"'%msg)
        self._progressbar()
        self._set_to_pagecache(cachekey,data,url)
        return data

    def get_request_raw_redirected(self, url,
                        extrasleep=None,
                        usecache=True,
                        referer=None):
        '''
        When should cache be cleared or not used? logins...

        extrasleep is primarily for ffnet adapter which has extra
        sleeps.  Passed into fetchs so it can be bypassed when
        cache hits.
        '''
        method='GET'

        if not url.startswith('file:'): # file fetches fail on + for space
            url = quote_plus(ensure_binary(url),safe=';/?:@&=+$,%&#')

        if self.getConfig('force_https'): ## For developer testing only.
            url = url.replace("http:","https:")
        cachekey=self._get_cachekey(url)
        if usecache and self._has_cachekey(cachekey) and not cachekey.startswith('file:'):
            logger.debug("#####################################\npagecache(%s) HIT: %s"%(method,safe_url(cachekey)))
            data,redirecturl = self._get_from_pagecache(cachekey)
            return (data,redirecturl)

        logger.debug("#####################################\npagecache(%s) MISS: %s"%(method,safe_url(cachekey)))
        # print(self.get_pagecache().keys())
        if not cachekey.startswith('file:'): # don't sleep for file: URLs.
            self.do_sleep(extrasleep)

        ## Specific UA because too many sites are blocking the default python UA.
        headers = [('User-Agent', self.getConfig('user_agent')),
                   ## starslibrary.net throws a "HTTP Error 403: Bad
                   ## Behavior" over the X-Clacks-Overhead.  Which
                   ## both against standard and rather a dick-move.
                   #('X-Clacks-Overhead','GNU Terry Pratchett'),
                   ]
        if referer:
            ## hpfanficarchive.com complains about Referer: None.
            ## Could have defaulted to "" instead, but this way it's
            ## not present at all
            headers.append(('Referer',referer))

        # logger.debug("GET http login for SB xf2test %s"%url)
        # if "xf2test" in url:
        #     import base64
        #     base64string = base64.encodestring(b"sbreview2019:Fs2PwuVE9").replace(b'\n', b'')
        #     headers.append(('Authorization',b"Basic %s" % base64string))
        #     logger.debug("http login for SB xf2test")

        ## requests/cloudscraper wants a dict() for headers, not
        ## list of tuples.
        headers = dict(headers)
        if self.getConfig('use_cloudscraper',False):
            ## let cloudscraper do its thing with UA.
            if 'User-Agent' in headers:
                del headers['User-Agent']
        # logger.debug("requests_session.cookies:%s"%self.get_requests_session().cookies)
        resp = self.get_requests_session().get(url,
                                               headers=headers,
                                               verify=not self.getConfig('use_ssl_unverified_context',False))
        logger.debug("response code:%s"%resp.status_code)
        try:
            resp.raise_for_status() # raises HTTPError if error code.
        except RequestsHTTPError as e:
            ## trekfanfiction.net has started returning the page,
            ## but with a 500 code.
            if resp.status_code == 500 and 'trekfanfiction.net' in url:
                ## Jan2012 -- Still happens at:
                ## https://trekfanfiction.net/maestros1/star-trek-greatest-generation/
                # logger.debug("!!!!!!!!!!!!!!!!! 500 trekfanfiction.net tripped !!!!!!!!!!!!")
                # resp.content is still there, even with 500.
                pass
            else:
                raise HTTPError(url,
                                e.response.status_code,
                                e.args[0],#msg,
                                None,#hdrs,
                                None #fp
                                )
        except CloudflareException as cfe:
            ## cloudscraper exception messages can appear to
            ## come from FFF and cause confusion.
            msg = unicode(cfe).replace(' in the opensource (free) version','...')
            raise exceptions.FailedToDownload('cloudscraper reports: "%s"'%msg)

        data = resp.content
        self._progressbar()
        self._set_to_pagecache(cachekey,data,resp.url)

        return (data,resp.url)

# .? for AO3's ']' in param names.
safe_url_re = re.compile(r'(?P<attr>(pass(word)?|name|login).?=)[^&]*(?P<amp>&|$)',flags=re.MULTILINE)
def safe_url(url):
    # return url with password attr (if present) obscured.
    return re.sub(safe_url_re,r'\g<attr>XXXXXXXX\g<amp>',url)
