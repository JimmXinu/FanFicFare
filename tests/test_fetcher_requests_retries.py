"""Exercise retry policy through RequestsFetcher without external traffic."""
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from unittest.mock import patch

from fanficfare.exceptions import HTTPErrorFFF
from fanficfare.fetchers.fetcher_requests import RequestsFetcher


class RequestsFetcherRetryTest(unittest.TestCase):
    def make_fetcher(self, config=None):
        config = config or {}
        fetcher = RequestsFetcher(lambda key, default=None: config.get(key, default),
                                 lambda key: [])
        # Ignore environment proxies and netrc credentials for local tests.
        fetcher.get_requests_session().trust_env = False
        self.addCleanup(fetcher.requests_session.close)
        return fetcher

    def serve(self, statuses):
        requests_seen = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length)
                index = min(len(requests_seen), len(statuses) - 1)
                requests_seen.append((self.command, body))
                self.send_response(statuses[index])
                self.end_headers()
                self.wfile.write(b'test response')

            do_POST = do_GET

            def log_message(self, *args):
                pass

        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop():
            server.shutdown()
            thread.join()
            server.server_close()

        self.addCleanup(stop)
        return 'http://127.0.0.1:%s/' % server.server_port, requests_seen

    def test_525_recovers_for_get_and_post(self):
        for method in ('GET', 'POST'):
            with self.subTest(method=method):
                url, seen = self.serve([525, 525, 200])
                fetcher = self.make_fetcher()
                with patch('urllib3.util.retry.time.sleep') as sleep:
                    response = fetcher.request(method, url, parameters={'test': 'value'})
                self.assertEqual(response.content, b'test response')
                self.assertEqual(len(seen), 3)
                self.assertEqual([entry[0] for entry in seen], [method] * 3)
                if method == 'POST':
                    self.assertEqual([entry[1] for entry in seen], [b'test=value'] * 3)
                sleep.assert_called_once_with(4.0)

    def test_exhaustion_preserves_http_error(self):
        for config, attempts, delays in [({}, 5, [4.0, 8.0, 16.0]),
                                         ({'max_request_retries': '0'}, 1, []),
                                         ({'max_request_retries': '2'}, 3, [4.0])]:
            with self.subTest(config=config):
                url, seen = self.serve([525])
                fetcher = self.make_fetcher(config)
                with patch('urllib3.util.retry.time.sleep') as sleep:
                    with self.assertRaises(HTTPErrorFFF) as error:
                        fetcher.request('GET', url)
                self.assertEqual(error.exception.status_code, 525)
                self.assertEqual(len(seen), attempts)
                self.assertEqual([call.args[0] for call in sleep.call_args_list], delays)

    def test_other_cloudflare_errors_are_not_retried(self):
        fetcher = self.make_fetcher()
        for status in (520, 521, 522, 523, 524, 526):
            with self.subTest(status=status):
                url, seen = self.serve([status, 200])
                with patch('urllib3.util.retry.time.sleep') as sleep:
                    with self.assertRaises(HTTPErrorFFF) as error:
                        fetcher.request('POST', url)
                self.assertEqual(error.exception.status_code, status)
                self.assertEqual(len(seen), 1)
                sleep.assert_not_called()

    def test_invalid_retry_counts_fall_back(self):
        for value in ('-1', 'invalid', '1.5', '', None):
            with self.subTest(value=value):
                with self.assertLogs('fanficfare.fetchers.fetcher_requests', level='ERROR'):
                    fetcher = self.make_fetcher({'max_request_retries': value})
                self.assertEqual(fetcher.retries.total, 4)

    def test_existing_policy_and_tls_verification_are_preserved(self):
        fetcher = self.make_fetcher()
        self.assertEqual(fetcher.retries.status_forcelist,
                         {413, 429, 500, 502, 503, 504, 525})
        self.assertEqual(fetcher.retries.other, 0)
        self.assertFalse(fetcher.retries.raise_on_status)
        self.assertTrue(fetcher.use_verify())


if __name__ == '__main__':
    unittest.main()
