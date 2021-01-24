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
from . import six
from .six.moves import urllib
from .six.moves.urllib.parse import (urlencode, quote_plus)
from .six.moves.urllib.request import (build_opener, HTTPCookieProcessor, Request)
from .six.moves import http_cookiejar as cl
from .six import text_type as unicode
from .six import string_types as basestring
from .six import ensure_binary, ensure_text

import time
import logging
import sys
import pickle

## isn't found in plugin when only imported down below inside
## get_scraper()
import cloudscraper
from cloudscraper.exceptions import CloudflareException

from . import exceptions
from requests.exceptions import HTTPError as RequestsHTTPError
from .six.moves.urllib.error import HTTPError

logger = logging.getLogger(__name__)

## makes requests based(like cloudscraper) dump req/resp headers.
## Does *not* work with older urllib code.
# import http.client as http_client
# http_client.HTTPConnection.debuglevel = 5

try:
    import chardet
except ImportError:
    chardet = None

from .gziphttp import GZipProcessor
from .htmlcleanup import reduce_zalgo

class Fetcher(object):
    def __init__(self,getConfig_fn,getConfigList_fn):
        self.getConfig = getConfig_fn
        self.getConfigList = getConfigList_fn

        self.use_pagecache = False # default to false for old adapters.

        self.override_sleep = None
        self.cookiejar = self.get_empty_cookiejar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookiejar),GZipProcessor())
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
        saveheaders = self.opener.addheaders
        self.opener = build_opener(HTTPCookieProcessor(self.cookiejar),GZipProcessor())
        self.opener.addheaders = saveheaders

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

## website encoding(s)--in theory, each website reports the character
## encoding they use for each page.  In practice, some sites report it
## incorrectly.  Each adapter has a default list, usually "utf8,
## Windows-1252" or "Windows-1252, utf8".  The special value 'auto'
## will call chardet and use the encoding it reports if it has +90%
## confidence.  'auto' is not reliable.  1252 is a superset of
## iso-8859-1.  Most sites that claim to be iso-8859-1 (and some that
## claim to be utf8) are really windows-1252.
    def _decode(self,data):
        if not hasattr(data,'decode'):
            ## py3 str() from pickle doesn't have .decode and is
            ## already decoded.
            return data
        decode = self.getConfigList('website_encodings',
                                    default=["utf8",
                                             "Windows-1252",
                                             "iso-8859-1"])
        for code in decode:
            try:
                logger.debug("Encoding:%s"%code)
                errors=None
                if ':' in code:
                    (code,errors)=code.split(':')
                if code == "auto":
                    if not chardet:
                        logger.info("chardet not available, skipping 'auto' encoding")
                        continue
                    detected = chardet.detect(data)
                    #print(detected)
                    if detected['confidence'] > float(self.getConfig("chardet_confidence_limit",0.9)):
                        logger.debug("using chardet detected encoding:%s(%s)"%(detected['encoding'],detected['confidence']))
                        code=detected['encoding']
                    else:
                        logger.debug("chardet confidence too low:%s(%s)"%(detected['encoding'],detected['confidence']))
                        continue
                if errors == 'ignore': # only allow ignore.
                    return data.decode(code,errors='ignore')
                else:
                    return data.decode(code)
            except Exception as e:
                logger.debug("code failed:"+code)
                logger.debug(e)
                pass
        logger.info("Could not decode story, tried:%s Stripping non-ASCII."%decode)
        try:
            # python2
            return "".join([x for x in data if ord(x) < 128])
        except TypeError:
            # python3
            return "".join([chr(x) for x in data if x < 128])

    def _progressbar(self):
        if self.getConfig('progressbar'):
            sys.stdout.write('.')
            sys.stdout.flush()

    def _do_reduce_zalgo(self,data):
        max_zalgo = int(self.getConfig('max_zalgo',-1))
        if max_zalgo > -1:
            logger.debug("Applying max_zalgo:%s"%max_zalgo)
            try:
                return reduce_zalgo(data,max_zalgo)
            except Exception as e:
                logger.warning("reduce_zalgo failed(%s), continuing."%e)
        return data

    def get_requests_session(self):
        if not self.requests_session:
            if self.getConfig('use_cloudscraper',False):
                ## ffnet adapter can't parse mobile output, so we only
                ## want desktop browser.  But cloudscraper then insists on
                ## a browser and platform, too.
                self.requests_session = cloudscraper.CloudScraper(browser={
                        'browser': 'chrome',
                        'platform': 'windows',
                        'mobile': False,
                        'desktop': True,
                        })
            else:
            ## CloudScraper is subclass of requests.Session.
            ## probably need import higher up if ever used.
                import requests
                self.requests_session = requests.Session()
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

        ## Request assumes POST when data!=None.  Also assumes data
        ## is application/x-www-form-urlencoded.
        if 'Content-type' not in headers:
            headers['Content-type']='application/x-www-form-urlencoded'
        if 'Accept' not in headers:
            headers['Accept']="text/html,*/*"

        # logger.debug("POST http login for SB xf2test %s"%url)
        # if "xf2test" in url:
        #     import base64
        #     base64string = base64.encodestring(b"sbreview2019:Fs2PwuVE9").replace(b'\n', b'')
        #     headers['Authorization']=b"Basic %s" % base64string
        #     logger.debug("http login for SB xf2test")

        try:
            resp = self.get_requests_session().post(url,
                                           headers=dict(headers),
                                           data=parameters)
            logger.debug("response code:%s"%resp.status_code)
            resp.raise_for_status() # raises HTTPError if error code.
            data = resp.content
        except CloudflareException as e:
            msg = unicode(e).replace(' in the opensource (free) version','...')
            raise exceptions.FailedToDownload('cloudscraper reports: "%s"'%msg)
        data = self._do_reduce_zalgo(self._decode(data))
        self._progressbar()
        ## postURL saves data to the pagecache *after* _decode() while
        ## fetchRaw saves it *before* _decode()--because raw.
        self._set_to_pagecache(cachekey,data,url)
        return data

    def get_request(self, url,
                    usecache=True,
                    extrasleep=None):
        return self.get_request_redirected(url,
                                           parameters,
                                           usecache,
                                           extrasleep)[0]

    # parameters is a dict()
    def get_request_redirected(self, url,
                               usecache=True,
                               extrasleep=None):

        excpt=None
        if url.startswith("file://"):
            # only one try for file:s.
            sleeptimes = [0]
        else:
            sleeptimes = [0, 2, 7, 12]
        for sleeptime in sleeptimes:
            if sleeptime:
                logger.debug("retry sleep:%s"%sleeptime)
            time.sleep(sleeptime)
            try:
                (data,rurl)=self.get_request_raw(url,
                                                 usecache=usecache,
                                                 extrasleep=extrasleep)
                return (self._do_reduce_zalgo(self._decode(data)),rurl)
            except HTTPError as he:
                excpt=he
                if he.code in (403,404,410):
                    logger.debug("Caught an exception reading URL: %s  Exception %s."%(unicode(safe_url(url)),unicode(he)))
                    break # break out on 404
                ## trekfanfiction.net has started returning the page,
                ## but with a 500 code.  We can get the url from the
                ## HTTPError in such case.
                if he.code == 500 and 'trekfanfiction.net' in url:
                    data = he.read()
                    return (self._do_reduce_zalgo(self._decode(data)),he.geturl())
            except Exception as e:
                excpt=e
                logger.debug("Caught an exception reading URL: %s sleeptime(%s) Exception %s."%(unicode(safe_url(url)),sleeptime,unicode(e)))
                if isinstance(e,CloudflareException):
                    ## cloudscraper exception messages can appear to
                    ## come from FFF and cause confusion.
                    msg = unicode(e).replace(' in the opensource (free) version','...')
                    raise exceptions.FailedToDownload('cloudscraper reports: "%s"'%msg)
                else:
                    raise

        logger.debug("Giving up on %s" %safe_url(url))
        logger.debug(excpt, exc_info=True)
        raise(excpt)

    def get_request_raw(self, url,
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

        self.opener.addheaders = headers

        ## requests/cloudscraper wants a dict() for headers, not
        ## list of tuples.
        headers = dict(headers)
        if self.getConfig('use_cloudscraper',False):
            ## let cloudscraper do its thing with UA.
            if 'User-Agent' in headers:
                del headers['User-Agent']
        resp = self.get_requests_session().get(url,headers=headers)
        logger.debug("response code:%s"%resp.status_code)
        try:
            resp.raise_for_status() # raises HTTPError if error code.
        except RequestsHTTPError as e:
            raise HTTPError(url,
                            e.response.status_code,
                            e.args[0],#msg,
                            None,#hdrs,
                            None #fp
                            )
        data = resp.content

        self._progressbar()
        ## postURL saves data to the pagecache *after* _decode() while
        ## fetchRaw saves it *before* _decode()--because raw.
        self._set_to_pagecache(cachekey,data,resp.url)

        return (data,resp.url)


class UrllibFetcher(Fetcher):
    pass


# .? for AO3's ']' in param names.
safe_url_re = re.compile(r'(?P<attr>(pass(word)?|name|login).?=)[^&]*(?P<amp>&|$)',flags=re.MULTILINE)
def safe_url(url):
    # return url with password attr (if present) obscured.
    return re.sub(safe_url_re,r'\g<attr>XXXXXXXX\g<amp>',url)
