import os
from .basebrowsercache import BrowserCacheException, BaseBrowserCache
## SimpleCache and BlockfileCache are both flavors of cache used by Chrome.
from .simplecache import SimpleCache
from .blockfilecache import BlockfileCache

import logging
logger = logging.getLogger(__name__)

import time
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


class BrowserCache(object):
    """Class to read web browser cache"""
    @do_cprofile
    def __init__(self, cache_dir=None):
        """Constructor for BrowserCache"""
        # import of child classes have to be inside the def to avoid circular import error
        for browser_cache_class in [SimpleCache, BlockfileCache]:
            self.browser_cache = browser_cache_class.new_browser_cache(cache_dir)
            if self.browser_cache is not None:
                break
        if self.browser_cache is None:
            raise BrowserCacheException("Directory does not contain a known browser cache type: '%s",
                                        os.path.abspath(cache_dir))

    def get_data(self, url):
        logger.debug("get_data:%s"%url)
        d = self.browser_cache.get_data(url)
        # if not d:
        #     ## newer browser caches separate by calling domain to not
        #     ## leak information about past visited pages by showing
        #     ## quick retrieval.

        #     ## There has to be a better way to do this...
        #     ## Or parse the whole cache for proper URLs.
        #     # protocol & domain only.
        #     # prefix = ('/'.join(url.split('/')[:3])).replace('www.','')
        #     # key = "_dk_"+prefix+" "+prefix+" "+url
        #     # logger.debug(key)
        #     # logger.debug("_dk_https://fanfiction.net https://fanfiction.net "+url)
        #     d = self.browser_cache.get_data(key)
        return d
