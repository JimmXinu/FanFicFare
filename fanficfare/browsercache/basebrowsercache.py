import sys
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

import pickle
if sys.version_info < (2, 7):
    sys.exit('This program requires Python 2.7 or newer.')
elif sys.version_info < (3, 0):
    reload(sys)  # Reload restores 'hidden' setdefaultencoding method
    sys.setdefaultencoding("utf-8")
    def pickle_load(f):
        return pickle.load(f)
else: # > 3.0
    def pickle_load(f):
        return pickle.load(f,encoding="bytes")

import logging
logger = logging.getLogger(__name__)
from ..six import ensure_text

class BrowserCacheException(Exception):
    pass

from ..six import ensure_binary, ensure_text

import datetime
def make_datetime(i):
    return datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=i)

class BaseBrowserCache(object):
    """Base class to read various formats of web browser cache file"""

    def __init__(self, cache_dir):
        """Constructor for BaseBrowserCache"""
        ## only ever
        if cache_dir is None:
            raise BrowserCacheException("BrowserCache must be initialized with a valid browser cache directory path")
        self.cache_dir = os.path.realpath(os.path.expanduser(cache_dir))
        if not os.path.isdir(self.cache_dir):
            raise BrowserCacheException("BrowserCache cache_dir does not exist: '%s (%s)'" %
                                        (cache_dir, self.cache_dir))

        # switched from namedtuple or class to primitives because it's
        # dirt simple and I want to pickle it.
        # map of urls -> (cache_key, cache_time)
        self.key_mapping = {}

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

    def map_cache_keys(self):
        """Scan index file and cache entries to save entries in this cache"""
        raise NotImplementedError()

    ## should priority be given to keeping any particular domain cache?
    def minimal_url(self,url):
        '''
        ONLY tested with fanfiction.net so far.
        '''
        url=ensure_text(url)
        # examples seen so far:
        # _dk_https://fanfiction.net https://fanfiction.net https://www.fanfiction.net/s/13278343/1/The-Timeless-Vault-HP-travel
        # _dk_chrome-extension://akiljllkbielkidmammnifcnibaigelm chrome-extension://akiljllkbielkidmammnifcnibaigelm https://www.fanfiction.net/s/13278343/3/The-Timeless-Vault-HP-travel
        # 1610476847265546/_dk_https://fanfiction.net https://fanfiction.net https://www.fanfiction.net/s/13791057/1/A-Yule-Ball-Changes?__cf_chl_jschl_tk__=c80be......
        url = url.split(' ')[-1]
        url = url.split('?')[0]
        if 'www.fanfiction.net/s/' in url:
            # remove title too.
            url = '/'.join(url.split('/')[:6])+'/'
        return url

    def add_key_mapping(self,url,key,time=None):
        '''
        ONLY used with fanfiction.net so far.
        '''
        if 'fanfiction.net/' in url:
            minurl = self.minimal_url(url)
            # logger.debug("add:\n%s\n%s\n%s\n%s"%(url,minurl,key,make_datetime(time)))
            (existing_key,existing_time) = self.key_mapping.get(minurl,(None,None))
            if( existing_key is None
                or existing_time is None
                or existing_time < time ):
                # logger.debug("replacing existing:%s < %s"%(existing_key and make_datetime(existing_time),make_datetime(time)))
                self.key_mapping[minurl]=(key,time)

    def get_key_mapping(self,url):
        # logger.debug("get_key_mapping:%s"%url)
        return self.key_mapping.get(self.minimal_url(url),(None,None))[0]

    def get_data(self, url):
        # logger.debug("\n\n===================================================\n\nurl:%s\n%s"%(url,self.minimal_url(url)))
        key = self.get_key_mapping(self.minimal_url(url))
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

    def load_cache(self,filename=None):
        logger.debug("load browser cache mappings(%s)"%(filename or self.filename))
        with open(filename or self.filename,'rb') as jin:
            self.key_mapping = pickle_load(jin)
            # logger.debug(self.basic_cache.keys())

    def save_cache(self,filename=None):
        with open(filename or self.filename,'wb') as jout:
            pickle.dump(self.key_mapping,jout,protocol=2)
            logger.debug("save browser cache mappings(%s)"%(filename or self.filename))

    def decompress(self, encoding, data):
        encoding = ensure_text(encoding)
        if encoding == 'gzip':
            return gzip.decompress(data)
        elif encoding == 'br':
            return brotli.decompress(data)
        elif encoding == 'deflate':
            return zlib.decompress(data)
        return data
