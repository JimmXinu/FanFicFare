# -*- coding: utf-8 -*-

# Copyright 2026 FanFicFare team
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

import logging
logger = logging.getLogger(__name__)

import threading

## Currently, only works in Calibre.

## Singleton code from:
## https://medium.com/analytics-vidhya/how-to-create-a-thread-safe-singleton-class-in-python-822e1170a7f6
class CamoufoxBrowserSingleton:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Another thread could have created the instance
                # before we acquired the lock. So check that the
                # instance is still nonexistent.
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # Only initialize once
        if not self._initialized:
            logger.debug("Initializing camoufox singlton browser")
            from calibre.web.automate.recipes import Browser as CamoufoxBrowser
            self.browser = CamoufoxBrowser(
                warmup=False,
                # user_agent=kwargs['user_agent'],
                # verify_ssl_certificates=kwargs.get('verify_ssl_certificates', False),
                # # A tab per download thread, so that the images of an article
                # # are taken from the tab that rendered it
                # max_tabs=self.simultaneous_downloads,
                # warmup_excluded_domains=self.warmup_excluded_domains(),
                )
            self._initialized = True

    def clone_browser(self):
        """A browser sharing this one's Camoufox instance but with a tab of its own."""
        logger.debug("cloning camoufox singlton browser")
        return self.browser.clone_browser()

