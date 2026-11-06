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

"""The subset of Calibre's recipe Browser used by the sequential FFF CLI.

One browser context shares cookies between clones, each with its own tab.
The browser and its temporary profile live only for this CLI invocation.

Calibre also tracks and retrieves a document's loaded image/resource responses.
This initial CLI wrapper does not implement that resource handling; use the
existing use_camoufox:directimages option to fetch images through requests.
Images requiring browser cookies or other browser state may therefore fail.
"""

import atexit
import base64
from io import BytesIO
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit

logger = logging.getLogger(__name__)


class Response(BytesIO):
    def __init__(self, content, url, status):
        super().__init__(content)
        self.url = url
        self.status = status


class Browser:
    def __init__(self, warmup=False):
        try:
            from camoufox.sync_api import Camoufox
            from playwright.sync_api import Error, TimeoutError
        except ImportError as e:
            raise RuntimeError(
                'CLI Camoufox requires Python 3.10+ and the optional dependencies. '
                'Install "FanFicFare[camoufox]". The browser is downloaded '
                'automatically on first use.') from e
        self._error = Error
        self._timeout_error = TimeoutError
        self._manager = Camoufox(headless=True)
        self._closed = False
        try:
            # Camoufox installs its browser and fingerprint data on first use.
            logger.debug('Starting Camoufox; first use may download browser and fingerprint data')
            self._browser = self._manager.__enter__()
        except Exception as e:
            raise RuntimeError(
                'Could not start Camoufox (first use may need to download the '
                'browser and fingerprint data). Original error: %s' % e) from e
        try:
            self._context = self._browser.new_context()
        except BaseException:
            self._manager.__exit__(None, None, None)
            raise
        atexit.register(self.close)
        if warmup:
            logger.warning('do_camoufox_warmup is only supported in Calibre; '
                           'the CLI starts with an empty temporary profile.')

    def clone_browser(self):
        return BrowserTab(self)

    def close(self):
        if not self._closed:
            self._closed = True
            atexit.unregister(self.close)
            self._manager.__exit__(None, None, None)


# POSTs use the page's own fetch, as in Calibre, so browser cookies and the
# document origin apply. Binary response bodies are returned without decoding.
PAGE_FETCH = """async ({url, data, timeout}) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    try {
        const options = {credentials: 'include', redirect: 'follow',
                         signal: controller.signal};
        if (data !== null) {
            options.method = 'POST';
            options.headers = {'Content-Type': 'application/x-www-form-urlencoded'};
            options.body = Uint8Array.from(atob(data), c => c.charCodeAt(0));
        }
        const response = await fetch(url, options);
        const blob = await response.blob();
        const encoded = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = () => reject(reader.error);
            reader.readAsDataURL(blob);
        });
        return {url: response.url, status: response.status,
                reason: response.statusText, data: encoded.split(',')[1]};
    } finally {
        clearTimeout(timer);
    }
}"""


class BrowserTab:
    def __init__(self, owner):
        self._owner = owner
        self._page = owner._context.new_page()

    def cookies(self):
        return self._owner._context.cookies()

    def set_cookie(self, name, value, domain, path):
        self._owner._context.add_cookies([
            {'name': name, 'value': value, 'domain': domain, 'path': path or '/'}])

    def open(self, url, data=None, timeout=60, as_document=True):
        try:
            if data is not None or not as_document:
                return self._fetch(url, data, timeout)
            responses = []

            def remember_response(response):
                if (response.request.is_navigation_request() and
                        response.frame == self._page.main_frame):
                    responses.append(response)

            self._page.on('response', remember_response)
            try:
                try:
                    response = self._page.goto(url, wait_until='load', timeout=timeout * 1000)
                except self._owner._timeout_error:
                    # A failed document may never fire load. Keep its actual
                    # HTTP status rather than treating a timed-out page as 200.
                    response = responses[-1] if responses else None
                    if response is None:
                        raise
                    if response.status < 400:
                        # Like Calibre, allow a usable DOM when ads prevent load.
                        self._page.wait_for_load_state('domcontentloaded', timeout=10000)
            finally:
                self._page.remove_listener('response', remember_response)
            status = response.status if response else 200
            if status == 304:
                status = 200
            final_url = self._page.url
            if not 200 <= status < 300:
                raise HTTPError(final_url, status, response.status_text, {}, None)
            content_type = response.headers.get('content-type', '') if response else 'text/html'
            if 'html' in content_type:
                # The adapter receives UTF-8, irrespective of the server's original
                # encoding. Replace declarations to agree with our serialization.
                content = self._page.evaluate("""() => {
                    document.querySelectorAll('meta[charset], meta[http-equiv="Content-Type" i]')
                        .forEach(node => node.remove());
                    const meta = document.createElement('meta');
                    meta.setAttribute('charset', 'utf-8');
                    (document.head || document.documentElement).prepend(meta);
                    return document.documentElement.outerHTML;
                }""").encode('utf-8')
            else:
                content = response.body()
            return Response(content, final_url, status)
        except self._owner._error as e:
            raise URLError(str(e)) from e

    def _fetch(self, url, data, timeout):
        if self._page.url == 'about:blank':
            parts = urlsplit(url)
            self._page.goto('%s://%s/' % (parts.scheme, parts.netloc),
                            wait_until='domcontentloaded', timeout=timeout * 1000)
        if isinstance(data, dict):
            data = urlencode(data)
        if isinstance(data, str):
            data = data.encode('utf-8')
        result = self._page.evaluate(PAGE_FETCH, {
            'url': url,
            'data': base64.b64encode(data).decode('ascii') if data is not None else None,
            'timeout': timeout * 1000})
        content = base64.b64decode(result['data'])
        if result['status'] >= 400:
            raise HTTPError(result['url'], result['status'], result['reason'], {}, BytesIO(content))
        return Response(content, result['url'], result['status'])

    def open_novisit(self, url, data=None, timeout=60):
        return self.open(url, data=data, timeout=timeout, as_document=False)

    def release(self):
        if not self._owner._closed and not self._page.is_closed():
            self._page.close()
