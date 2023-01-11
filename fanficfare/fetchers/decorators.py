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
import sys
import random
import time
from functools import partial

from .log import make_log

import logging
logger = logging.getLogger(__name__)

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
        logger.debug("fromcache:%s"%fetchresp.fromcache)
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
