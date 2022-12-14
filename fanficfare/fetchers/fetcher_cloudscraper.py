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

import cloudscraper
from cloudscraper.exceptions import CloudflareException

# py2 vs py3 transition
from ..six import text_type as unicode
from .. import exceptions

from .fetcher_requests import RequestsFetcher

## makes requests/cloudscraper dump req/resp headers.
# import http.client as http_client
# http_client.HTTPConnection.debuglevel = 5

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

