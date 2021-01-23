import os
import struct

from ..chromagnon.cacheParse import ChromeCache
from . import BrowserCacheException, BaseBrowserCache


class ChromeDiskCacheException(BrowserCacheException):
    pass


INDEX_MAGIC_NUMBER = 0xC103CAC3
BLOCK_MAGIC_NUMBER = 0xC104CAC3


class ChromeDiskCache(BaseBrowserCache):
    """Class to access data stream in Chrome Disk Cache format cache files"""

    def __init__(self, cache_dir=None):
        """Constructor for ChromeDiskCache"""
        super().__init__(cache_dir)
        if not self.is_cache_dir(cache_dir):
            raise ChromeDiskCacheException("Directory does not contain a Chrome Disk Cache: '%s'" % cache_dir)
        self.chromagnon_cache = ChromeCache(cache_dir)

    @staticmethod
    def is_cache_dir(cache_dir):
        """Return True only if a directory is a valid Cache for this class"""
        if not os.path.isdir(cache_dir):
            return False
        index_path = os.path.join(cache_dir, "index")
        if not os.path.isfile(index_path):
            return False
        with open(index_path, 'rb') as index_file:
            if struct.unpack('I', index_file.read(4))[0] != INDEX_MAGIC_NUMBER:
                return False
        data0_path = os.path.join(cache_dir, "data_0")
        if not os.path.isfile(data0_path):
            return False
        with open(data0_path, 'rb') as data0_file:
            if struct.unpack('I', data0_file.read(4))[0] != BLOCK_MAGIC_NUMBER:
                return False
        return True

    def get_keys(self):
        """ Return all keys for existing entries in underlying cache as set of strings"""
        return self.chromagnon_cache.cache_keys

    def get_data(self, url):
        """ Return decoded data for specified key (a URL string) or None """
        return self.chromagnon_cache.get_cached_file(url)
