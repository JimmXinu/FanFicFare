"""Cache-miss diagnostics must be read-only and preserve fetch behaviour."""
import logging
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from fanficfare.browsercache import BrowserCache
from fanficfare.browsercache.base_browsercache import BaseBrowserCache
from fanficfare.browsercache.browsercache_firefox2 import FirefoxCache2
from fanficfare.exceptions import HTTPErrorFFF
from fanficfare.fetchers.base_fetcher import FetcherResponse
from fanficfare.fetchers.cache_browser import BrowserCacheDecorator, domain_open_tries


class BrowserCacheDiagnosticsTest(unittest.TestCase):
    url = 'https://www.fanfiction.net/s/13447216/1/The-Propriety-Correction'
    cache_miss_message = ('Page not found or expired in Browser Cache '
                          '(see FFF setting browser_cache_age_limit)')
    logger_name = 'fanficfare.browsercache.browsercache_firefox2'

    def setUp(self):
        self.logger = logging.getLogger(self.logger_name)
        self.addCleanup(self.logger.setLevel, self.logger.level)
        self.logger.setLevel(logging.DEBUG)
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        self.cache_dir = Path(tempdir.name).resolve()
        self.entries = self.cache_dir / 'entries'
        self.entries.mkdir()
        config = {'browser_cache_path': str(self.cache_dir)}
        self.impl = FirefoxCache2('fanfiction.net', config.get, lambda key: [])
        # Bypass format detection so size-only fixtures need no binary headers.
        self.cache = BrowserCache.__new__(BrowserCache)
        self.cache.browser_cache_impl = self.impl
        self.decorator = BrowserCacheDecorator(self.cache)
        self.chain = Mock(return_value=FetcherResponse(b'network response'))
        tries = patch.dict(domain_open_tries, clear=True)
        tries.start()
        self.addCleanup(tries.stop)

    def request(self, config=None, url=None):
        settings = {'use_browser_cache_only': True}
        settings.update(config or {})
        fetcher = Mock()
        fetcher.getConfig = settings.get
        return self.decorator.fetcher_do_request(
            fetcher, self.chain, 'GET', url or self.url)

    def get_diagnostic(self):
        with self.assertLogs(self.logger_name, level='DEBUG') as logs:
            message = self.cache.get_cache_miss_message()
        self.assertEqual(message, self.cache_miss_message)
        return '\n'.join(logs.output)

    def assert_firefox_hint(self, message):
        self.assertIn(str(self.cache_dir), message)
        self.assertIn('about:cache', message)
        self.assertIn('Storage in use', message)
        self.assertIn('Maximum storage size', message)
        self.assertIn('105%', message)
        self.assertIn('keeping cookies and site data', message)

    def test_usage_rounds_each_file_to_kib_and_ignores_directories(self):
        for name, size in [('A' * 40, 1024), ('B' * 40, 1025), ('C' * 40, 0)]:
            (self.entries / name).write_bytes(b'x' * size)
        (self.entries / 'subdirectory').mkdir()
        # The index and doomed entries are not part of active entry usage.
        (self.cache_dir / 'index').write_bytes(b'x' * 4096)
        doomed = self.cache_dir / 'doomed'
        doomed.mkdir()
        (doomed / ('D' * 40)).write_bytes(b'x' * 4096)
        before = {path: path.read_bytes() for path in self.cache_dir.rglob('*')
                  if path.is_file()}

        message = self.get_diagnostic()

        self.assert_firefox_hint(message)
        self.assertIn('Approximate usage: 3 KiB. Entry count: 3.', message)
        self.assertEqual(before, {path: path.read_bytes()
                                 for path in self.cache_dir.rglob('*')
                                 if path.is_file()})

    def test_empty_cache_does_not_claim_to_be_full(self):
        message = self.get_diagnostic()
        self.assertIn('Approximate usage: 0 KiB. Entry count: 0.', message)
        self.assertNotIn('cache is full', message.lower())

    def test_large_cache_does_not_assume_a_capacity_limit(self):
        # A sparse file reproduces the reported usage without allocating it.
        with (self.entries / ('A' * 40)).open('wb') as entry:
            entry.truncate(216528 * 1024)
        message = self.get_diagnostic()
        self.assertIn('Approximate usage: 216528 KiB. Entry count: 1.', message)
        self.assertNotIn('cache is full', message.lower())
        self.assertNotIn('204800', message)

    def test_unavailable_directory_preserves_troubleshooting_hint(self):
        self.entries.rmdir()
        message = self.get_diagnostic()
        self.assert_firefox_hint(message)
        self.assertNotIn('Approximate usage', message)

    def test_permission_error_preserves_cache_miss(self):
        with patch('fanficfare.browsercache.browsercache_firefox2.os.scandir',
                   side_effect=PermissionError('not readable')), \
             self.assertLogs(self.logger_name, level='DEBUG') as logs:
            with self.assertRaises(HTTPErrorFFF) as error:
                self.request()
        self.assertEqual(error.exception.status_code, 428)
        self.assertEqual(error.exception.url, self.url)
        self.assertEqual(error.exception.error_msg, self.cache_miss_message)
        diagnostic = '\n'.join(logs.output)
        self.assert_firefox_hint(diagnostic)
        self.assertNotIn('Approximate usage', diagnostic)
        self.chain.assert_not_called()

    def test_entry_evicted_during_scan_is_skipped(self):
        evicted = Mock()
        evicted.is_file.return_value = True
        evicted.stat.side_effect = FileNotFoundError('evicted')
        present = Mock()
        present.is_file.return_value = True
        present.stat.return_value.st_size = 2048
        scan = MagicMock()
        scan.__enter__.return_value = iter([evicted, present])
        with patch('fanficfare.browsercache.browsercache_firefox2.os.scandir',
                   return_value=scan):
            message = self.get_diagnostic()
        self.assertIn('Approximate usage: 2 KiB. Entry count: 1.', message)
        scan.__exit__.assert_called_once()

    def test_normal_miss_does_not_scan_or_log_diagnostics(self):
        self.logger.setLevel(logging.WARNING)
        with patch('fanficfare.browsercache.browsercache_firefox2.os.scandir') as scan, \
             patch.object(self.impl, '_log_cache_miss_diagnostics') as diagnostic:
            with self.assertRaises(HTTPErrorFFF) as error:
                self.request()
        self.assertEqual(error.exception.status_code, 428)
        self.assertEqual(error.exception.error_msg, self.cache_miss_message)
        scan.assert_not_called()
        diagnostic.assert_not_called()
        self.chain.assert_not_called()

    def test_debug_miss_logs_diagnostic_but_preserves_error(self):
        with self.assertLogs(self.logger_name, level='DEBUG') as logs:
            with self.assertRaises(HTTPErrorFFF) as error:
                self.request()
        self.assertEqual(error.exception.status_code, 428)
        self.assertEqual(error.exception.error_msg, self.cache_miss_message)
        self.assert_firefox_hint('\n'.join(logs.output))
        self.assertNotIn('about:cache', str(error.exception))
        self.chain.assert_not_called()

    def test_expired_entry_keeps_brief_error_and_logs_debug_hint(self):
        old_entry = ('', time.time() - 10 * 3600, '', b'expired page')
        with patch.object(self.impl, 'get_data_key_impl', return_value=old_entry), \
             self.assertLogs(self.logger_name, level='DEBUG') as logs:
            with self.assertRaises(HTTPErrorFFF) as error:
                self.request()
        self.assertEqual(error.exception.error_msg, self.cache_miss_message)
        self.assert_firefox_hint('\n'.join(logs.output))

    def test_cache_hit_does_not_scan(self):
        with patch.object(self.cache, 'get_data', return_value=b'cached page'), \
             patch('fanficfare.browsercache.browsercache_firefox2.os.scandir') as scan:
            response = self.request()
        self.assertEqual(response.content, b'cached page')
        self.assertTrue(response.fromcache)
        scan.assert_not_called()
        self.chain.assert_not_called()

    def test_network_fallback_and_file_requests_do_not_scan(self):
        for config, url in [({'use_browser_cache_only': False}, self.url),
                            ({}, 'file:///missing-page.html')]:
            with self.subTest(config=config, url=url):
                self.chain.reset_mock()
                with patch('fanficfare.browsercache.browsercache_firefox2.os.scandir') as scan:
                    response = self.request(config, url)
                self.assertEqual(response.content, b'network response')
                self.chain.assert_called_once()
                scan.assert_not_called()

    def test_successful_browser_retry_does_not_scan(self):
        with patch.object(self.cache, 'get_data', side_effect=[None, b'loaded page']), \
             patch('fanficfare.fetchers.cache_browser.open_url') as open_url, \
             patch('fanficfare.fetchers.cache_browser.time.sleep'), \
             patch('fanficfare.browsercache.browsercache_firefox2.os.scandir') as scan:
            response = self.request({'open_pages_in_browser': True})
        self.assertEqual(response.content, b'loaded page')
        self.assertFalse(response.fromcache)
        open_url.assert_called_once_with(self.url)
        scan.assert_not_called()

    def test_exhausted_browser_retries_scan_only_once(self):
        with patch('fanficfare.fetchers.cache_browser.open_url'), \
             patch('fanficfare.fetchers.cache_browser.time.sleep'), \
             patch('fanficfare.browsercache.browsercache_firefox2.os.scandir',
                   wraps=os.scandir) as scan:
            with self.assertRaises(HTTPErrorFFF):
                self.request({'open_pages_in_browser': True})
        scan.assert_called_once_with(str(self.entries))

    def test_other_browser_caches_keep_existing_message(self):
        self.cache.browser_cache_impl = BaseBrowserCache(
            'fanfiction.net', {'browser_cache_path': str(self.cache_dir)}.get,
            lambda key: [])
        with patch.object(self.cache, 'get_data', return_value=None):
            with self.assertRaises(HTTPErrorFFF) as error:
                self.request()
        self.assertEqual(error.exception.error_msg, self.cache_miss_message)


if __name__ == '__main__':
    unittest.main()
