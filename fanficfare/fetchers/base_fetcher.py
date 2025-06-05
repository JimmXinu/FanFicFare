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

# py2 vs py3 transition
from ..six.moves.urllib.parse import quote_plus
from ..six.moves.http_cookiejar import LWPCookieJar, MozillaCookieJar
from ..six import text_type as unicode
from ..six import ensure_binary

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

    def make_headers(self,url,referer=None,image=False):
        headers = {}
        headers['User-Agent']=self.getConfig('user_agent')
        if referer:
            headers['Referer']=referer
        if image is True:
            headers["Accept"] = "image/*"
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
                    usecache=True,
                    image=False):
        # logger.debug("fetcher do_request")
        # logger.debug(self.get_cookiejar())
        headers = self.make_headers(url,referer=referer,image=image)
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
                               usecache=True,
                               image=False):
        fetchresp = self.do_request('GET',
                                     self.condition_url(url),
                                     referer=referer,
                                     usecache=usecache,
                                     image=image)
        return (fetchresp.content,fetchresp.redirecturl)
