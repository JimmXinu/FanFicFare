# -*- coding: utf-8 -*-

# Copyright 2026 FanFicFare team
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

import logging
logger = logging.getLogger(__name__)

import urllib
from http import cookiejar as cj

from .. import exceptions

from .log import make_log
from .base_fetcher import FetcherResponse, Fetcher
from .camoufoxbrowser import CamoufoxBrowserSingleton

class CamoufoxFetcher(Fetcher):
    def __init__(self,getConfig_fn,getConfigList_fn):
        super(CamoufoxFetcher,self).__init__(getConfig_fn,getConfigList_fn)
        self.browser = None

    def get_cookiejar(self,filename=None,mozilla=False):
        self.cookiejar = super(CamoufoxFetcher,self).get_cookiejar(filename,mozilla)
        for c in self.get_browser().cookies():
            # logger.debug(f'{c=}')
            self.cookiejar.set_cookie(cj.Cookie(
                    version=0,
                    name=c['name'],
                    value=c['value'],
                    port=None,
                    port_specified=False,
                    domain=c['domain'],
                    domain_specified=False,
                    domain_initial_dot=False,
                    path=c['path'],
                    path_specified=True,
                    secure=c['secure'],
                    expires=c['expires'],
                    discard=False,
                    comment=None,
                    comment_url=None,
                    rest={'HttpOnly': c['httpOnly']},
                    rfc2109=False))
        return self.cookiejar

    def set_cookiejar(self,cookiejar):
        super(CamoufoxFetcher,self).set_cookiejar(cookiejar)
        # logger.debug("Camoufox set_cookiejar")
        for c in cookiejar:
            # logger.debug(f'{c=}')
            self.get_browser().set_cookie(c.name,c.value,c.domain,c.path)

    def get_browser(self):
        if self.browser is None:
            self.browser = CamoufoxBrowserSingleton().clone_browser()
        return self.browser

    def request(self,method,url,headers=None,parameters=None):
        '''Returns a FetcherResponse regardless of mechanism'''
        if method not in ('GET','POST'):
            raise NotImplementedError()
        resp = None
        resp2 = None
        try:
            logger.debug(make_log('CamoufoxFetcher',method,url,hit='REQ',bar='-'))
            timeout = 60.0
            try:
                timeout = float(self.getConfig("connect_timeout",timeout))
            except Exception as e:
                logger.error("connect_timeout setting failed: %s -- Using default value(%s)"%(e,timeout))

            ## Nothing done with base_fetcher.make_headers().  I don't
            ## think we need to.

            ## data is None == GET, has data == POST
            resp = self.get_browser().open(url,
                                           data=parameters,
                                           timeout=timeout)
            logger.debug("response code:%s"%resp.status)

            data = resp.read()
            # logger.debug(data)
            sleepsec = 10
            if b'<title>Making sure you\'re not a bot!</title>' in data:
                logger.debug(f"Anubis detected, sleep({sleepsec}) then open_novisit()")
                import time
                time.sleep(sleepsec)
                resp2 = self.get_browser().open_novisit(url,
                                                        data=parameters,
                                                        timeout=timeout)
                logger.debug("resp2 code:%s"%resp.status)
                return FetcherResponse(resp2.read(),
                                       resp2.url)
            return FetcherResponse(data,
                                   resp.url)

        except urllib.error.URLError as e:
            ## not RequestsHTTPError(requests.exceptions.HTTPError) or
            ## urllib.error import HTTPError because we want code
            ## *and* content for that one trekfanfiction catch.
            raise exceptions.HTTPErrorFFF(
                url,
                getattr(e,'code', 'No status code'),
                getattr(e,'reason', 'No given reason'),
                None # don't have data here.
                )
        finally:
            if resp is not None:
                resp.close()
            if resp2 is not None:
                resp2.close()

    def __del__(self):
        if self.browser is not None:
            logger.debug("browser clone released")
            self.browser.release()
