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

class BrowserCacheException(Exception):
    pass

from ..six import ensure_binary, ensure_text

class BaseBrowserCache:
    """Base class to read various formats of web browser cache file"""

    def __init__(self, cache_dir=None):
        """Constructor for BaseBrowserCache"""
        if cache_dir is None:
            raise BrowserCacheException("BrowserCache must be initialized with a valid browser cache directory path")
        self.cache_dir = os.path.realpath(os.path.expanduser(cache_dir))
        if not os.path.isdir(self.cache_dir):
            raise BrowserCacheException("BrowserCache cache_dir does not exist: '%s (%s)'" %
                                        (cache_dir, self.cache_dir))

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

    def get_data(self, url):
        """ Return decoded data for specified key (a URL string) or None """
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

