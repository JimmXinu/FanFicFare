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

from contextlib import closing
import logging
logger = logging.getLogger(__name__)

from .. import exceptions

from .log import make_log
from .base_fetcher import FetcherResponse, Fetcher

class CamoufoxFetcher(Fetcher):
    def __init__(self,getConfig_fn,getConfigList_fn):
        super(CamoufoxFetcher,self).__init__(getConfig_fn,getConfigList_fn)
        self.browser = None


    # def set_cookiejar(self,cookiejar):
    #     super(CamoufoxFetcher,self).set_cookiejar(cookiejar)
    #     ## in case where cookiejar is set second
    #     if  self.requests_session:
    #         self.requests_session.cookies = self.cookiejar

    def get_browser(self):
        if self.browser is None:
            from calibre.web.automate.recipes import Browser as CamoufoxBrowser
            self.browser = CamoufoxBrowser(
                warmup=False,
                # user_agent=kwargs['user_agent'],
                # verify_ssl_certificates=kwargs.get('verify_ssl_certificates', False),
                # # A tab per download thread, so that the images of an article
                # # are taken from the tab that rendered it
                # max_tabs=self.simultaneous_downloads,
                # warmup_excluded_domains=self.warmup_excluded_domains(),
                )
        return self.browser

    def request(self,method,url,headers=None,parameters=None,json=None):
        '''Returns a FetcherResponse regardless of mechanism'''
        if method not in ('GET','POST'):
            raise NotImplementedError()
        try:
            logger.debug(make_log('CamoufoxFetcher',method,url,hit='REQ',bar='-'))
            ## resp = requests Response object
            timeout = 60.0
            try:
                timeout = float(self.getConfig("connect_timeout",timeout))
            except Exception as e:
                logger.error("connect_timeout setting failed: %s -- Using default value(%s)"%(e,timeout))

            ## XXX headers, json
            ## data is None == GET, has data == POST
            resp = None
            resp2 = None
            try:
                resp = self.get_browser().open(url,
                                               data=parameters,
                                               timeout=timeout)
                logger.debug(resp)
                logger.debug("response code:%s"%resp.status)
                # resp.raise_for_status() # raises RequestsHTTPError if error code.
                # consider 'cached' if from file.
                fromcache = resp.url.startswith('file:')
                ## currently only saving response json if there input was json.
                ## for flaresolverr_proxy
                resp_json = None
                data = resp.read().decode()
                if "<title>Making sure you\'re not a bot!</title>" in data:
                    logger.debug("Anubis detected, sleep then open_novisit()")
                    import time
                    time.sleep(15)
                    resp2 = self.get_browser().open_novisit(url,
                                                            data=parameters,
                                                            timeout=timeout)
                    logger.debug("resp2 code:%s"%resp.status)
                    logger.debug(resp2)
                    return FetcherResponse(resp2.read().decode(),
                                           resp2.url,
                                           fromcache,
                                           resp_json)

                # if json:
                #     try:
                #         resp_json = resp.json()
                #     except:
                #         pass
                # logger.debug(resp_json)
                return FetcherResponse(data,
                                       resp.url,
                                       fromcache,
                                       resp_json)
            finally:
                if resp is not None:
                    resp.close()
                if resp2 is not None:
                    resp2.close()
        except Exception as e:
            raise
            ## not RequestsHTTPError(requests.exceptions.HTTPError) or
            ## urllib.error import HTTPError because we want code
            ## *and* content for that one trekfanfiction catch.
            # raise exceptions.HTTPErrorFFF(
            #     url,
            #     e.response.status_code,
            #     e.args[0],# error_msg
            #     e.response.content # data
            #     )

    def __del__(self):
        if self.browser is not None:
            ## for when it will be shared
            # self.browser.release()
            if self.browser is not None:
                self.browser.shutdown()
