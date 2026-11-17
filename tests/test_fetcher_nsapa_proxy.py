"""Exercise NSAPA_ProxyFetcher against a local fake proxy, without
external traffic."""
import base64
import socket
import socketserver
import threading
import time
import unittest
from unittest.mock import patch

from fanficfare.exceptions import FailedToDownload
from fanficfare.fetchers.fetcher_nsapa_proxy import NSAPA_ProxyFetcher

URL = 'https://www.fanfiction.net/s/1234/1/'


def reply(payload, type_='text'):
    return b'%d||%s$END_OF_HEADER$%s' % (len(payload), type_.encode(), payload)


class NSAPAProxyFetcherTest(unittest.TestCase):
    def serve(self, respond):
        """respond(url, socket) is called for each proxy request."""
        seen = []

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                url = self.request.recv(4096).decode('utf-8')
                seen.append(url)
                respond(url, self.request)

        server = socketserver.ThreadingTCPServer(('127.0.0.1', 0), Handler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop():
            server.shutdown()
            server.server_close()
            thread.join()

        self.addCleanup(stop)
        return server.server_address[1], seen

    def make_fetcher(self, port, config=None):
        config = dict({'nsapa_proxy_address': '127.0.0.1',
                       'nsapa_proxy_port': port}, **(config or {}))
        return NSAPA_ProxyFetcher(lambda key, default=None: config.get(key, default),
                                  lambda key, default=None: [])

    def test_text_reply(self):
        port, seen = self.serve(
            lambda url, s: s.sendall(reply('Grüße'.encode('utf-8'))))
        response = self.make_fetcher(port).request('GET', URL)
        self.assertEqual(response.content, 'Grüße')
        self.assertEqual(seen, [URL])

    def test_header_and_payload_in_pieces(self):
        def respond(url, s):
            for piece in (b'11||te', b'xt$END_OF', b'_HEADER$hel', b'lo world'):
                s.sendall(piece)
                time.sleep(0.05)

        port, seen = self.serve(respond)
        response = self.make_fetcher(port).request('GET', URL)
        self.assertEqual(response.content, 'hello world')

    def test_text_b64_reply(self):
        data = b'\x89PNG\r\n\x1a\nimage'
        port, seen = self.serve(
            lambda url, s: s.sendall(reply(base64.b64encode(data), 'text-b64')))
        response = self.make_fetcher(port).request('GET', URL)
        self.assertEqual(response.content, data)

    def test_invalid_base64_fails_download(self):
        port, seen = self.serve(
            lambda url, s: s.sendall(reply(b'not base64!', 'text-b64')))
        with self.assertRaises(FailedToDownload):
            self.make_fetcher(port).proxy_request(URL)

    def test_unknown_type_is_not_retried(self):
        port, seen = self.serve(lambda url, s: s.sendall(reply(b'abc', 'weird')))
        with self.assertRaises(NotImplementedError):
            self.make_fetcher(port).request('GET', URL)
        self.assertEqual(seen, [URL])

    def test_truncated_reply_retries_with_browser_reset(self):
        def respond(url, s):
            if url == 'chrome://version':
                s.sendall(reply(b'version'))
            else:
                # announce 100 bytes, send 10 and close.
                s.sendall(b'100||text$END_OF_HEADER$0123456789')

        port, seen = self.serve(respond)
        start = time.monotonic()
        with patch('fanficfare.fetchers.fetcher_nsapa_proxy.time.sleep') as sleep:
            with self.assertRaises(FailedToDownload) as error:
                self.make_fetcher(port).request('GET', URL)
        self.assertIn('truncated', str(error.exception))
        self.assertEqual(seen, [URL, 'chrome://version'] * 4 + [URL])
        self.assertEqual(sleep.call_count, 4)
        # closed connection ends the wait right away, no timeouts.
        self.assertLess(time.monotonic() - start, 5)

    def test_missing_header_times_out(self):
        done = threading.Event()
        self.addCleanup(done.set)
        port, seen = self.serve(lambda url, s: done.wait(10))
        fetcher = self.make_fetcher(port, {'connect_timeout': '0.5'})
        start = time.monotonic()
        with self.assertRaises(FailedToDownload):
            fetcher.proxy_request(URL)
        self.assertLess(time.monotonic() - start, 5)

    def test_slow_payload_does_not_busy_wait(self):
        def respond(url, s):
            s.sendall(b'11||text$END_OF_HEADER$hello')
            time.sleep(1)
            s.sendall(b' world')

        port, seen = self.serve(respond)
        cpu_start = time.process_time()
        response = self.make_fetcher(port).request('GET', URL)
        self.assertEqual(response.content, 'hello world')
        self.assertLess(time.process_time() - cpu_start, 0.5)

    def test_proxy_down_raises_connection_error(self):
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]
        with self.assertRaises(ConnectionError):
            self.make_fetcher(port).request('GET', URL)


if __name__ == '__main__':
    unittest.main()
