import os
from .basebrowsercache import BrowserCacheException, BaseBrowserCache
## SimpleCache and BlockfileCache are both flavors of cache used by Chrome.
from .simplecache import SimpleCache
from .blockfilecache import BlockfileCache

import logging
logger = logging.getLogger(__name__)


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
#             profile.print_stats()
#     return profiled_func

# import time
# def do_cprofile(func):
#     def profiled_func(*args, **kwargs):
#         t=0
#         try:
#             t = time.time()
#             result = func(*args, **kwargs)
#             t = time.time() - t
#             return result
#         finally:
#             logger.debug("do_cprofile time:%s"%t)
#     return profiled_func


class BrowserCache(object):
    """
    Class to read web browser cache
    This wrapper class contains the actual impl object.
    """
    def __init__(self, cache_dir, autoload=True):
        """Constructor for BrowserCache"""
        # import of child classes have to be inside the def to avoid circular import error
        for browser_cache_class in [SimpleCache, BlockfileCache]:
            self.browser_cache = browser_cache_class.new_browser_cache(cache_dir)
            if self.browser_cache is not None:
                break
        if self.browser_cache is None:
            raise BrowserCacheException("Directory does not contain a known browser cache type: '%s'"%
                                        os.path.abspath(cache_dir))

        if autoload:
            self.do_map_cache_keys()

    # @do_cprofile
    def do_map_cache_keys(self,autoload=True):
        logger.debug("do_map_cache_keys()")
        self.browser_cache.map_cache_keys()

    def get_data(self, url):
        # logger.debug("get_data:%s"%url)
        d = self.browser_cache.get_data(url)
        return d

    def load_cache(self,filename=None):
        self.browser_cache.load_cache(filename)

    def save_cache(self,filename=None):
        self.browser_cache.save_cache(filename)
