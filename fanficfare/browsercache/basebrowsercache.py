import sys
import os
import time
import traceback

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


# import cProfile
# def do_cprofile(func):
#     def profiled_func(*args, **kwargs):
#         profile = cProfile.Profile()
#         try:
#             profile.enable()
#             result = func(*args, **kwargs)
#             profile.disable()
#             return result
#         finally:
#             profile.print_stats(sort='time')
#     return profiled_func

def do_cprofile(func):
    def profiled_func(*args, **kwargs):
        t=0
        try:
            t = time.time()
            result = func(*args, **kwargs)
            t = time.time() - t
            return result
        finally:
            logger.debug("do_cprofile time:%s"%t)
    return profiled_func



class BrowserCacheException(Exception):
    pass

## difference in seconds between Jan 1 1601 and Jan 1 1970.  Chrome
## caches (so far) have kept time stamps as microseconds since
## 1-1-1601 a Windows/Cobol thing.
EPOCH_DIFFERENCE = 11644473600
import datetime

class BaseBrowserCache(object):
    """Base class to read various formats of web browser cache file"""

    def __init__(self, cache_dir, age_limit=-1):
        """Constructor for BaseBrowserCache"""
        ## only ever
        if cache_dir is None:
            raise BrowserCacheException("BrowserCache must be initialized with a valid browser cache directory path")
        self.cache_dir = os.path.realpath(os.path.expanduser(cache_dir))
        if not os.path.isdir(self.cache_dir):
            raise BrowserCacheException("BrowserCache cache_dir does not exist: '%s (%s)'" %
                                        (cache_dir, self.cache_dir))
        self.age_comp_time = 0
        if age_limit is None or age_limit == '':
            self.age_limit = -1
        else:
            self.age_limit = float(age_limit)
        self.set_age_comp_time()
        # switched from namedtuple or class to primitives because it's
        # dirt simple and I want to pickle it.
        # map of urls -> (cache_key, cache_time)
        self.key_mapping = {}

        self.mapping_loaded = False

    @classmethod
    def new_browser_cache(cls, cache_dir, age_limit=-1):
        """Return new instance of this BrowserCache class, or None if supplied directory not the correct cache type"""
        cache_dir = os.path.realpath(os.path.expanduser(cache_dir))
        if cls.is_cache_dir(cache_dir):
            try:
                return cls(cache_dir,age_limit=age_limit)
            except BrowserCacheException:
                return None
        return None

    # Chromium uses 1601 epoch for... reasons?
    def set_age_comp_time(self):
        if self.age_limit > 0.0:
            ## now - age_limit as microseconds since Jan 1, 1601
            ## for direct comparison with cache values.
            self.age_comp_time = int(time.time() - (self.age_limit*3600) + EPOCH_DIFFERENCE)*1000000
            ## By doing this once, we save a lot of comparisons
            ## and extra saved data at the risk of using pages
            ## that would have expired during long download
            ## sessions.

    ## just here for ease of applying @do_cprofile
    @do_cprofile
    def do_map_cache_keys(self):
        logger.debug("do_map_cache_keys()")
        self.map_cache_keys()
        self.mapping_loaded = True
        logger.debug("Cached %s entries"%len(self.key_mapping))

    def map_cache_keys(self):
        """Scan index file and cache entries to save entries in this cache"""
        raise NotImplementedError()

    def cache_key_to_url(self,key):
        '''
        Modern browsers partition cache by domain to avoid leaking information.
        '''
        key=ensure_text(key)
        # chromium examples seen so far:
        # _dk_https://fanfiction.net https://fanfiction.net https://www.fanfiction.net/s/13278343/1/The-Timeless-Vault-HP-travel
        # _dk_chrome-extension://akiljllkbielkidmammnifcnibaigelm chrome-extension://akiljllkbielkidmammnifcnibaigelm https://www.fanfiction.net/s/13278343/3/The-Timeless-Vault-HP-travel
        # 1610476847265546/_dk_https://fanfiction.net https://fanfiction.net https://www.fanfiction.net/s/13791057/1/A-Yule-Ball-Changes?__cf_chl_jschl_tk__=c80be......
        return key.split(' ')[-1]

    ## should priority be given to keeping any particular domain cache?
    def minimal_url(self,url):
        '''
        ONLY tested with fanfiction.net & ficbook.net so far.

        Will need to split into separate functions for add and
        get--FireFox domain keys different.
        '''
        url=ensure_text(url)
        url = url.split('?')[0]
        if 'www.fanfiction.net/s/' in url or 'www.fictionpress.com/s/' in url:
            # remove title too.
            url = '/'.join(url.split('/')[:6])+'/'
        if 'ficbook.net/readfic/' in url:
            # remove #content_part
            url = url.split('#')[0]
        return url

    def add_key_mapping(self,cache_url,key,cached_time=None):
        '''
        ONLY used with fanfiction.net & ficbook.net so far.
        '''
        if self.age_comp_time > cached_time:
            return
        if (
                'fanfiction.net/' in cache_url
                or 'fictionpress.com/' in cache_url
                or 'ficbook.net/' in cache_url
                or 'patreon.com/' in cache_url
            ):
            minurl = self.minimal_url(self.cache_key_to_url(cache_url))
            # logger.debug("%s -> %s"%(minurl,key))
            (existing_key,existing_time) = self.key_mapping.get(minurl,(None,None))
            if( existing_key is None
                or existing_time is None
                or existing_time < cached_time ):
                # logger.debug("replacing existing:%s < %s"%(existing_key and self.make_datetime(existing_time),self.make_datetime(cached_time)))
                self.key_mapping[minurl]=(key,cached_time)

    def get_key_mapping(self,url):
        # logger.debug("get_key_mapping:%s"%url)
        ## on demand map loading now.
        ## browser_cache is shared between configurations
        ## XXX Needs some locking if multi-threading implemented.
        if not self.mapping_loaded:
            try:
                self.do_map_cache_keys()
            except Exception as e:
                logger.debug(traceback.format_exc())
                raise BrowserCacheException("Browser Cache Failed to Load with error '%s'"%e)
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

    def make_datetime(self,i):
        return datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=i)

    def load_cache(self,filename=None):
        logger.debug("load browser cache mappings(%s)"%(filename or self.filename))
        with open(filename or self.filename,'rb') as jin:
            self.key_mapping = pickle_load(jin)
            # logger.debug(self.basic_cache.keys())
        self.mapping_loaded = True

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
