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

import logging
logger = logging.getLogger(__name__)

from .configurable import Configurable

class Requestable(Configurable):
    def __init__(self, configuration):
        Configurable.__init__(self,configuration)

        ## use_pagecache() is on adapters--not all have been updated
        ## to deal with caching correctly
        if hasattr(self, 'use_pagecache'):
            self.configuration.cache.use_pagecache = self.use_pagecache()

## website encoding(s)--in theory, each website reports the character
## encoding they use for each page.  In practice, some sites report it
## incorrectly.  Each adapter has a default list, usually "utf8,
## Windows-1252" or "Windows-1252, utf8".  The special value 'auto'
## will call chardet and use the encoding it reports if it has +90%
## confidence.  'auto' is not reliable.  1252 is a superset of
## iso-8859-1.  Most sites that claim to be iso-8859-1 (and some that
## claim to be utf8) are really windows-1252.
    def do_decode(self,data):
        if not hasattr(data,'decode'):
            ## py3 str() from pickle doesn't have .decode and is
            ## already decoded.  Should always be bytes now(Jan2021),
            ## but keeping this just in case.
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
        logger.info("Could not decode story, tried:%s Stripping non-ASCII."%decode)
        try:
            # python2
            return "".join([x for x in data if ord(x) < 128])
        except TypeError:
            # python3
            return "".join([chr(x) for x in data if x < 128])

    def do_reduce_zalgo(self,data):
        max_zalgo = int(self.getConfig('max_zalgo',-1))
        if max_zalgo > -1:
            logger.debug("Applying max_zalgo:%s"%max_zalgo)
            try:
                return reduce_zalgo(data,max_zalgo)
            except Exception as e:
                logger.warning("reduce_zalgo failed(%s), continuing."%e)
        return data

    def decode_data(self,data):
        return self.do_reduce_zalgo(self.do_decode(data))

    def post_request(self, url,
                     parameters=None,
                     usecache=True):
        data = self.configuration.get_fetcher().post_request(
            url,
            parameters=parameters,
            usecache=usecache)
        data = self.decode_data(data)
        return data

    def get_request_redirected(self, url,
                               usecache=True,
                               extrasleep=None):
        (data,rurl) = self.configuration.get_fetcher().get_request_redirected(
            url,
            usecache=usecache,
            extrasleep=extrasleep)[:2]
        data = self.decode_data(data)
        return (data,rurl)

    def get_request(self, url,
                  usecache=True,
                  extrasleep=None):
        return self.get_request_redirected(url,
                                           usecache,
                                           extrasleep)[0]

    def get_request_raw(self, url,
                        extrasleep=None,
                        referer=None,
                        usecache=True): ## referer is used with raw for images.
        return self.configuration.get_fetcher().get_request_redirected(
            url,
            extrasleep=extrasleep,
            referer=referer,
            usecache=usecache)[0]

