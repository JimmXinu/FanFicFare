"""Offline tests for FlareSolverr/Camoufox fetcher cookie and error
handling, and the FlareSolverr include_images override."""
import time
import unittest
from http.cookiejar import CookieJar
from unittest.mock import MagicMock

import requests

from fanficfare.configurable import Configuration
from fanficfare.exceptions import HTTPErrorFFF
from fanficfare.fetchers.fetcher_camoufox import CamoufoxFetcher
from fanficfare.fetchers.fetcher_flaresolverr_proxy import (
    FlareSolverr_ProxyFetcher, cookiejson_to_jarable, filter_cookies)


def default_config(key, default=None):
    return default


def default_config_list(key, default=None):
    return []


def fs_cookie(name, domain, **kwargs):
    cookie = {'name': name, 'value': 'v', 'domain': domain, 'path': '/',
              'secure': True}
    cookie.update(kwargs)
    return cookie


def cookie_header(cookies, url):
    jar = CookieJar()
    for cookie in cookies:
        jar.set_cookie(cookie)
    request = requests.Request('GET', url).prepare()
    return requests.cookies.get_cookie_header(jar, request) or ''


class FlareSolverrCookieTest(unittest.TestCase):
    def test_filter_cookies_matches_host_and_parent_domains(self):
        jar = CookieJar()
        for cookie in cookiejson_to_jarable([
                fs_cookie('dot', '.archiveofourown.org', expires=2000000000),
                fs_cookie('host', 'archiveofourown.org', expires=2000000000),
                fs_cookie('other', 'example.com', expires=2000000000)]):
            jar.set_cookie(cookie)

        def names(url):
            return sorted(c.name for c in filter_cookies(jar, url))

        self.assertEqual(names('https://archiveofourown.org/works/1'),
                         ['dot', 'host'])
        self.assertEqual(names('https://www.archiveofourown.org/works/1'),
                         ['dot', 'host'])
        # Cookie domain only in the query or as the end of another
        # domain name must not send the cookie there.
        self.assertEqual(
            names('https://evil.example/?ref=archiveofourown.org'), [])
        self.assertEqual(names('https://notarchiveofourown.org/'), [])

    def test_session_cookies_are_kept(self):
        now = time.time()
        cookies = cookiejson_to_jarable([
            fs_cookie('session', '.example.com', expires=-1),
            fs_cookie('noexpiry', 'example.com'),
            fs_cookie('persistent', 'example.com', expires=now + 3600),
            fs_cookie('far', 'example.com', expires=253402300799)])
        byname = {c.name: c for c in cookies}

        for cookie in cookies:
            self.assertFalse(cookie.is_expired(now), cookie.name)
        self.assertIsNone(byname['session'].expires)
        self.assertTrue(byname['session'].discard)
        self.assertFalse(byname['persistent'].discard)
        self.assertEqual(byname['far'].expires, 30000000000)
        self.assertTrue(byname['persistent'].path_specified)

        header = cookie_header(cookies, 'https://www.example.com/')
        for name in ('session', 'noexpiry', 'persistent', 'far'):
            self.assertIn('%s=v' % name, header)


class FlareSolverrErrorTest(unittest.TestCase):
    def make_fetcher(self, data):
        fetcher = FlareSolverr_ProxyFetcher(default_config,
                                            default_config_list)

        def fs_error(*args, **kwargs):
            raise HTTPErrorFFF('http://localhost:8191/v1', 500,
                               'Server Error', data)
        fetcher.super_request = fs_error
        return fetcher

    def test_flaresolverr_json_error_message(self):
        fetcher = self.make_fetcher(
            b'{"status": "error", "message": "Timeout after 59.0 seconds."}')
        with self.assertRaises(HTTPErrorFFF) as cm:
            fetcher.request('GET', 'https://example.com/')
        self.assertEqual(cm.exception.error_msg,
                         'Flaresolverr says: Timeout after 59.0 seconds.')

    def test_non_json_error_passes_http_error_on(self):
        fetcher = self.make_fetcher(b'<html>502 Bad Gateway</html>')
        with self.assertRaises(HTTPErrorFFF) as cm:
            fetcher.request('GET', 'https://example.com/')
        self.assertEqual(cm.exception.status_code, 500)
        self.assertEqual(cm.exception.error_msg, 'Server Error')


class FlareSolverrIncludeImagesTest(unittest.TestCase):
    def make_configuration(self, use_flaresolverr_proxy):
        configuration = Configuration(['test1.com'], 'EPUB')
        configuration.read_string(
            '[defaults]\ninclude_images:true\n'
            '[overrides]\nuse_flaresolverr_proxy:%s\n' % use_flaresolverr_proxy)
        configuration.get_fetcher()
        return configuration

    def test_include_images_turned_off(self):
        configuration = self.make_configuration('true')
        self.assertFalse(configuration.getConfig('include_images'))

    def test_include_images_kept_withimages(self):
        configuration = self.make_configuration('withimages')
        self.assertEqual(configuration.getConfig('include_images'), 'true')


class CamoufoxCookieTest(unittest.TestCase):
    def test_session_cookies_are_kept(self):
        now = time.time()
        fetcher = CamoufoxFetcher(default_config, default_config_list)
        fetcher.browser = MagicMock()
        fetcher.browser.cookies.return_value = [
            {'name': 'session', 'value': 'v', 'domain': '.example.com',
             'path': '/', 'secure': True, 'expires': -1, 'httpOnly': True},
            {'name': 'persistent', 'value': 'v', 'domain': '.example.com',
             'path': '/', 'secure': True, 'expires': now + 3600,
             'httpOnly': True}]

        cookies = list(fetcher.get_cookiejar())
        for cookie in cookies:
            self.assertFalse(cookie.is_expired(now), cookie.name)

        header = cookie_header(cookies, 'https://www.example.com/')
        self.assertIn('session=v', header)
        self.assertIn('persistent=v', header)


if __name__ == '__main__':
    unittest.main()
