import os
from .basebrowsercache import BrowserCacheException, BaseBrowserCache
from .simplecache import SimpleCache
from .chromediskcache import ChromeDiskCache


class BrowserCache:
    """Class to read web browser cache"""
    def __init__(self, cache_dir=None):
        """Constructor for BrowserCache"""
        # import of child classes have to be inside the def to avoid circular import error
        browser_cache_class: BaseBrowserCache
        for browser_cache_class in [SimpleCache, ChromeDiskCache]:
            self.browser_cache = browser_cache_class.new_browser_cache(cache_dir)
            if self.browser_cache is not None:
                break
        if self.browser_cache is None:
            raise BrowserCacheException("Directory does not contain a known browser cache type: '%s",
                                        os.path.abspath(cache_dir))

    def get_data(self, url):
        return self.browser_cache.get_data(url)
