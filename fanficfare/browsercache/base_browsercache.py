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

import os
import time, datetime
import gzip
import zlib
import re
try:
    # py3 only, calls C libraries. CLI
    import brotli
except ImportError:
    try:
        # Calibre doesn't include brotli, so use plugin packaged
        # brotlidecpy, which is slower, but pure python
        from calibre_plugins.fanficfare_plugin import brotlidecpy as brotli
    except ImportError:
        # Included for benefit of A-Shell for iOS users.  They need to
        # install brotlidecpy themselves and override pip to install
        # FFF without brotli
        # See:
        # https://github.com/JimmXinu/FanFicFare/issues/919
        # https://github.com/sidney/brotlidecpy
        import brotlidecpy as brotli

import logging
logger = logging.getLogger(__name__)

from ..six.moves.urllib.parse import urlparse, urlunparse
from ..six import ensure_text

from ..exceptions import BrowserCacheException

CACHE_DIR_CONFIG="browser_cache_path"
AGE_LIMIT_CONFIG="browser_cache_age_limit"

class BaseBrowserCache(object):
    """Base class to read various formats of web browser cache file"""

    def __init__(self, site, getConfig_fn, getConfigList_fn):
        """Constructor for BaseBrowserCache"""
        ## only ever called by class method new_browser_cache()
        self.site = site
        self.getConfig = getConfig_fn
        self.getConfigList = getConfigList_fn

        self.cache_dir = self.expand_cache_dir(getConfig_fn(CACHE_DIR_CONFIG))
        age_limit=self.getConfig(AGE_LIMIT_CONFIG)
        if age_limit is None or age_limit == '' or float(age_limit) < 0.0:
            self.age_limit = None
        else:
            # set in hours, recorded in seconds
            self.age_limit = float(age_limit) * 3600

    @classmethod
    def new_browser_cache(cls, site, getConfig_fn, getConfigList_fn):
        """Return new instance of this BrowserCache class, or None if supplied directory not the correct cache type"""
        if cls.is_cache_dir(cls.expand_cache_dir(getConfig_fn(CACHE_DIR_CONFIG))):
            try:
                return cls(site,
                           getConfig_fn,
                           getConfigList_fn)
            except BrowserCacheException:
                return None
        return None

    @staticmethod
    def expand_cache_dir(cache_dir):
        return os.path.realpath(os.path.expanduser(cache_dir))

    @staticmethod
    def is_cache_dir(cache_dir):
        """Check given dir is a valid cache."""
        raise NotImplementedError()

    def get_data(self, url):
        """Return cached value for URL if found."""
        # logger.debug("get_data:%s"%url)

        ## allow for a list of keys specifically for finding WebToEpub
        ## cached entries.
        rettuple = None
        for key in self.make_keys(url):
            logger.debug("Cache Key:%s"%key)
            entrytuple = self.get_data_key_impl(url, key)
            # use newest
            if entrytuple and (not rettuple or rettuple[1] < entrytuple[1]):
                rettuple = entrytuple

        if rettuple is None:
            return None

        (location,
         age,
         encoding,
         rawdata) = rettuple

        # age check
        logger.debug("age:%s"%datetime.datetime.fromtimestamp(age))
        logger.debug("now:%s"%datetime.datetime.fromtimestamp(time.time()))
        if not (self.age_limit is None or age > time.time()-self.age_limit):
            logger.debug("Cache entry found, rejected, past age limit")
            return None

        # recurse on location redirects
        if location:
            logger.debug("Do Redirect(%s)"%location)
            return self.get_data(self.make_redirect_url(location,url))

        # decompress
        return self.decompress(encoding,rawdata)

    def get_data_key_impl(self, url, key):
        """
        returns location, entry age, content-encoding and
        raw(compressed) data
        """
        raise NotImplementedError()

    def make_keys(self, url):
        """
        Returns a list of keys to try--list for WebToEpub and normal
        Hashing done inside get_data_key_impl
        """
        raise NotImplementedError()

    def make_key_parts(self, url, site=False):
        """
        Modern browser all also key their cache with the domain to
        reduce info leaking, but differently.  However, some parts
        are common.

        Now returns a list of domains, one for the story URL site and
        one for the URLs own domain.  Cache partitioning of images is
        done based on the parent page (ie, the story site), but if
        it's not found/expired/etc and called directly instead, then
        it will be partitioned by the image URL instead.  This way we
        have both.
        """
        parsedUrl = urlparse(url)
        scheme = parsedUrl.scheme
        domains = [self.site, parsedUrl.netloc]


        ## only keep the first domain.TLD, more general than
        ## discarding www.
        domains = [ re.sub(r'.*?([^\.]+\.[^\.]+)$',r'\1',d) for d in domains ]
        ## don't need both if they are the same.  Could use a set() to
        ## dedup, but want to preserve order.
        if domains[0] == domains[1]:
            domains.pop()

        # discard any #anchor part
        url = url.split('#')[0]

        return (scheme, domains, url) # URL still contains domain, params, etc

    def make_redirect_url(self,location,origurl):
        """
        Most redirects are relative, but not all.
        """
        pLoc = urlparse(location)
        pUrl = urlparse(origurl)
        # logger.debug(pLoc)
        # logger.debug(pUrl)
        return urlunparse((pLoc.scheme or pUrl.scheme,
                           pLoc.netloc or pUrl.netloc,
                           location.strip(),
                           '','',''))

    def decompress(self, encoding, data):
        encoding = ensure_text(encoding)
        if encoding == 'gzip':
            ## XXX py2 doesn't have gzip.decompress() and
            ## zlib.decompress() isn't compatible.  Ran into once, but
            ## it's the site that choses the encoding and on reload,
            ## got brotli instead.
            return gzip.decompress(data)
        elif encoding == 'br':
            return brotli.decompress(data)
        elif encoding == 'deflate':
            return zlib.decompress(data)
        return data
