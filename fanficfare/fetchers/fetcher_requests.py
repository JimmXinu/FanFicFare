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
from ..six import text_type as unicode
from .. import exceptions

from urllib3.util.retry import Retry
import requests
from requests.exceptions import HTTPError as RequestsHTTPError
from requests.adapters import HTTPAdapter
from requests_file import FileAdapter

## makes requests/cloudscraper dump req/resp headers.
# import http.client as http_client
# http_client.HTTPConnection.debuglevel = 5

from .log import make_log
from .base_fetcher import FetcherResponse, Fetcher

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
