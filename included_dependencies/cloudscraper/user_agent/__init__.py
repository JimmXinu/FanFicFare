import json
import os
import random
import re
import sys
import ssl

from collections import OrderedDict

# ------------------------------------------------------------------------------- #


class User_Agent():

    # ------------------------------------------------------------------------------- #

    def __init__(self, *args, **kwargs):
        self.headers = None
        self.cipherSuite = []
        self.loadUserAgent(*args, **kwargs)

    # ------------------------------------------------------------------------------- #

    def filterAgents(self, user_agents):
        filtered = {}

        if self.mobile:
            if self.platform in user_agents['mobile'] and user_agents['mobile'][self.platform]:
                filtered.update(user_agents['mobile'][self.platform])

        if self.desktop:
            if self.platform in user_agents['desktop'] and user_agents['desktop'][self.platform]:
                filtered.update(user_agents['desktop'][self.platform])

        return filtered

    # ------------------------------------------------------------------------------- #

    def tryMatchCustom(self, user_agents):
        for device_type in user_agents['user_agents']:
            for platform in user_agents['user_agents'][device_type]:
                for browser in user_agents['user_agents'][device_type][platform]:
                    if re.search(re.escape(self.custom), ' '.join(user_agents['user_agents'][device_type][platform][browser])):
                        self.headers = user_agents['headers'][browser]
                        self.headers['User-Agent'] = self.custom
                        self.cipherSuite = user_agents['cipherSuite'][browser]
                        return True
        return False

    # ------------------------------------------------------------------------------- #

    def loadUserAgent(self, *args, **kwargs):
        self.browser = kwargs.pop('browser', None)

        self.platforms = ['linux', 'windows', 'darwin', 'android', 'ios']
        self.browsers = ['chrome', 'firefox']

        if isinstance(self.browser, dict):
            self.custom = self.browser.get('custom', None)
            self.platform = self.browser.get('platform', None)
            self.desktop = self.browser.get('desktop', True)
            self.mobile = self.browser.get('mobile', True)
            self.browser = self.browser.get('browser', None)
        else:
            self.custom = kwargs.pop('custom', None)
            self.platform = kwargs.pop('platform', None)
            self.desktop = kwargs.pop('desktop', True)
            self.mobile = kwargs.pop('mobile', True)

        if not self.desktop and not self.mobile:
            sys.tracebacklimit = 0
            raise RuntimeError("Sorry you can't have mobile and desktop disabled at the same time.")

        #with open(os.path.join(os.path.dirname(__file__), 'browsers.json'), 'r') as fp:
        user_agents = json.load(self.get_user_agents(),
                                object_pairs_hook=OrderedDict
                                )

        if self.custom:
            if not self.tryMatchCustom(user_agents):
                self.cipherSuite = [
                    ssl._DEFAULT_CIPHERS,
                    '!AES128-SHA',
                    '!ECDHE-RSA-AES256-SHA',
                ]
                self.headers = OrderedDict([
                    ('User-Agent', self.custom),
                    ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'),
                    ('Accept-Language', 'en-US,en;q=0.9'),
                    ('Accept-Encoding', 'gzip, deflate, br')
                ])
        else:
            if self.browser and self.browser not in self.browsers:
                sys.tracebacklimit = 0
                raise RuntimeError('Sorry "{}" browser is not valid, valid browsers are [{}].'.format(self.browser, ', '.join(self.browsers)))

            if not self.platform:
                self.platform = random.SystemRandom().choice(self.platforms)

            if self.platform not in self.platforms:
                sys.tracebacklimit = 0
                raise RuntimeError('Sorry the platform "{}" is not valid, valid platforms are [{}]'.format(self.platform, ', '.join(self.platforms)))

            filteredAgents = self.filterAgents(user_agents['user_agents'])

            if not self.browser:
                # has to be at least one in there...
                while not filteredAgents.get(self.browser):
                    self.browser = random.SystemRandom().choice(list(filteredAgents.keys()))

            if not filteredAgents[self.browser]:
                sys.tracebacklimit = 0
                raise RuntimeError('Sorry "{}" browser was not found with a platform of "{}".'.format(self.browser, self.platform))

            self.cipherSuite = user_agents['cipherSuite'][self.browser]
            self.headers = user_agents['headers'][self.browser]

            self.headers['User-Agent'] = random.SystemRandom().choice(filteredAgents[self.browser])

        if not kwargs.get('allow_brotli', False) and 'br' in self.headers['Accept-Encoding']:
            self.headers['Accept-Encoding'] = ','.join([
                encoding for encoding in self.headers['Accept-Encoding'].split(',') if encoding.strip() != 'br'
            ]).strip()

    def get_user_agents(self):
        from io import StringIO
        return StringIO(self.get_user_agents_resources())
        # return self.get_user_agents_stringio()

    def get_user_agents_stringio(self):
        return '''
{
    "headers": {
        "chrome": {
            "User-Agent": null,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br"
        },
        "firefox": {
            "User-Agent": null,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br"
        }
    },
    "cipherSuite": {
        "chrome": [
            "TLS_AES_128_GCM_SHA256",
            "TLS_AES_256_GCM_SHA384",
            "TLS_CHACHA20_POLY1305_SHA256",
            "ECDHE-ECDSA-AES128-GCM-SHA256",
            "ECDHE-RSA-AES128-GCM-SHA256",
            "ECDHE-ECDSA-AES256-GCM-SHA384",
            "ECDHE-RSA-AES256-GCM-SHA384",
            "ECDHE-ECDSA-CHACHA20-POLY1305",
            "ECDHE-RSA-CHACHA20-POLY1305",
            "ECDHE-RSA-AES128-SHA",
            "ECDHE-RSA-AES256-SHA",
            "AES128-GCM-SHA256",
            "AES256-GCM-SHA384",
            "AES128-SHA",
            "AES256-SHA",
            "DES-CBC3-SHA"
        ],
        "firefox": [
            "TLS_AES_128_GCM_SHA256",
            "TLS_CHACHA20_POLY1305_SHA256",
            "TLS_AES_256_GCM_SHA384",
            "ECDHE-ECDSA-AES128-GCM-SHA256",
            "ECDHE-RSA-AES128-GCM-SHA256",
            "ECDHE-ECDSA-CHACHA20-POLY1305",
            "ECDHE-RSA-CHACHA20-POLY1305",
            "ECDHE-ECDSA-AES256-GCM-SHA384",
            "ECDHE-RSA-AES256-GCM-SHA384",
            "ECDHE-ECDSA-AES256-SHA",
            "ECDHE-ECDSA-AES128-SHA",
            "ECDHE-RSA-AES128-SHA",
            "ECDHE-RSA-AES256-SHA",
            "DHE-RSA-AES128-SHA",
            "DHE-RSA-AES256-SHA",
            "AES128-SHA",
            "AES256-SHA",
            "DES-CBC3-SHA"
        ]
    },
    "user_agents": {
        "desktop": {
            "windows": {
                "chrome": [
                    "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.1331.54 Safari/537.36-1",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3788.1 Safari/537.36-2"
                ],
                "firefox": [
                    "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Dragon/52.15.25.665 Chrome/52.0.2743.82 Safari/537.36-3",
                    "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:67.0) Gecko/20100101 Firefox/67.0-4"
                ]
            },
            "linux": {
                "chrome": [
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36",
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
                ],
                "firefox": [
                    "Mozilla/5.0 (X11; Linux i686 on x86_64; rv:50.0) Gecko/20100101 Firefox/50.0",
                    "Mozilla/5.0 (X11; Linux x86_64; rv:67.0) Gecko/20100101 Firefox/67.0"
                ]
            },
            "darwin": {
                "chrome": [
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3783.0 Safari/537.36"
                ],
                "firefox": [
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:50.0) Gecko/20100101 Firefox/50.0",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:67.0) Gecko/20100101 Firefox/67.0"
                ]
            }
        },
        "mobile": {
            "android": {
                "chrome": [
                    "Mozilla/5.0 (Linux; U; Android 5.1; zh-cn; Build/LMY47D ) AppleWebKit/534.30 (KHTML,like Gecko) Version/4.0 Chrome/50.0.0.0 Mobile Safari/534.30 GIONEE-GN9010/GN9010 RV/5.0.16",
                    "Mozilla/5.0 (Linux; Android 8.1.0; QS5509A) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.28 Mobile Safari/537.36"
                ],
                "firefox": [
                    "Mozilla/5.0 (Android 3.0; Tablet; rv:50.0) Gecko/50.0 Firefox/50.0",
                    "Mozilla/5.0 (Android 7.1.1; Tablet; rv:68.0) Gecko/68.0 Firefox/68.0"
                ]
            },
            "ios": {
                "chrome": [
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.5277.764 Mobile Safari/537.36",
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.1502.79 Mobile Safari/537.36"
                ],
                "firefox": []
            }
        }
    }
}
'''

    def get_user_agents_resources(self):
        return browsers_json

browsers_json = None
