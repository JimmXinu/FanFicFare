import os

import gzip
import zlib

try:
    # py3 only, calls C libraries. CLI
    import brotli
except ImportError:
    # Calibre doesn't include brotli, so use plugin packaged
    # brotlidecpy, which is slower, but pure python
    from calibre_plugins.fanficfare_plugin import brotlidecpy as brotli

import logging
logger = logging.getLogger(__name__)
from ..six import ensure_text

class BrowserCacheException(Exception):
    pass

from ..six import ensure_binary, ensure_text

class BaseBrowserCache(object):
    """Base class to read various formats of web browser cache file"""

    def __init__(self, cache_dir=None):
        """Constructor for BaseBrowserCache"""
        if cache_dir is None:
            raise BrowserCacheException("BrowserCache must be initialized with a valid browser cache directory path")
        self.cache_dir = os.path.realpath(os.path.expanduser(cache_dir))
        if not os.path.isdir(self.cache_dir):
            raise BrowserCacheException("BrowserCache cache_dir does not exist: '%s (%s)'" %
                                        (cache_dir, self.cache_dir))

        self.key_mapping = {}

    ## should priority be given to keeping any particular domain cache?
    def minimal_url(self,url):
        url=ensure_text(url)
        if '_dk_' in url:
            url = url.split(' ')[-1].split('?')[0]
        return url

    def add_key_mapping(self,url,key):
        if 'fanfiction.net/' in url:
            # logger.debug("add:\n%s\n%s\n%s"%(url,self.minimal_url(url),key))
            self.key_mapping[self.minimal_url(url)]=key

    def get_key_mapping(self,url):
        # logger.debug("get_key_mapping:%s"%url)
        return self.key_mapping.get(self.minimal_url(url),None)

    def get_data(self, url):
        # logger.debug("\n\n===================================================\n\nurl:%s"%url)
        key = self.get_key_mapping(url)
        # logger.debug("key:%s"%key)
        if key:
            return self.get_data_key(key)
        else:
            return None

    def get_data_key(self,url):
        """ Return decoded data for specified key (a URL string) or None """
        return None

    @staticmethod
    def is_cache_dir(cache_dir):
        return os.path.isdir(cache_dir)  # This method only makes sense when overridden

    @classmethod
    def new_browser_cache(cls, cache_dir):
        """Return new instance of this BrowserCache class, or None if supplied directory not the correct cache type"""
        cache_dir = os.path.realpath(os.path.expanduser(cache_dir))
        if cls.is_cache_dir(cache_dir):
            try:
                return cls(cache_dir)
            except BrowserCacheException:
                return None
        return None

    def get_keys(self):
        """ Return all keys for existing entries in underlying cache as set of strings"""
        return None  # must be overridden

    def decompress(self, encoding, data):
        encoding = ensure_text(encoding)
        if encoding == 'gzip':
            return gzip.decompress(data)
        elif encoding == 'br':
            return brotli.decompress(data)
        elif encoding == 'deflate':
            return zlib.decompress(data)
        return data

