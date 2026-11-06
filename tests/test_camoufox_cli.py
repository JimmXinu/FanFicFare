"""Opt-in browser integration tests using only a local HTTP server.

Run with RUN_CAMOUFOX_TESTS=1 after installing FanFicFare[camoufox]. The first
run downloads the browser unless pre-installed with python -m camoufox fetch.
"""

import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs

import pytest

from fanficfare.fetchers.camoufoxbrowser_cli import Browser


pytestmark = pytest.mark.skipif(
    os.environ.get('RUN_CAMOUFOX_TESTS') != '1',
    reason='Requires the optional Camoufox browser installation')


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == '/slow':
            time.sleep(1)
            self.send_response(200)
            self.end_headers()
            return
        if self.path == '/redirect':
            self.send_response(302)
            self.send_header('Location', '/page')
            self.end_headers()
            return
        if self.path == '/missing':
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Set-Cookie', 'fromserver=yes; Path=/')
        self.end_headers()
        body = '<html><head><meta charset="iso-8859-1"></head><body>café'
        body += '<script>document.body.dataset.ready = "yes";</script>'
        body += self.headers.get('Cookie', '') + '</body></html>'
        self.wfile.write(body.encode('utf-8'))

    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        fields = parse_qs(body.decode('utf-8'))
        self.send_response(200)
        self.send_header('Content-Type', 'application/octet-stream')
        self.send_header('Set-Cookie', 'loggedin=yes; Path=/')
        self.end_headers()
        self.wfile.write(fields['value'][0].encode('utf-8') + b'\x00\xff')


@pytest.fixture(scope='module')
def server():
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield 'http://127.0.0.1:%d' % server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.fixture(scope='module')
def browser():
    browser = Browser()
    try:
        yield browser
    finally:
        browser.close()
        browser.close()  # Explicit cleanup and the exit hook are idempotent.


def test_navigation_runs_javascript_and_follows_redirects(browser, server):
    tab = browser.clone_browser()
    try:
        with tab.open(server + '/redirect') as response:
            assert response.status == 200
            assert response.url == server + '/page'
            content = response.read().decode('utf-8')
            assert 'café' in content
            assert 'data-ready="yes"' in content
            assert 'charset="utf-8"' in content
            assert 'iso-8859-1' not in content
    finally:
        tab.release()


def test_post_binary_response_and_shared_cookies(browser, server):
    first = browser.clone_browser()
    second = browser.clone_browser()
    try:
        first.set_cookie('imported', 'yes', '127.0.0.1', '/')
        with first.open(server + '/login', data={'value': 'a & café'}) as response:
            assert response.read() == 'a & café'.encode('utf-8') + b'\x00\xff'
        cookies = {cookie['name']: cookie['value'] for cookie in second.cookies()}
        assert cookies['imported'] == 'yes'
        assert cookies['loggedin'] == 'yes'
        with second.open(server + '/page') as response:
            assert b'loggedin=yes' in response.read()
        with second.open_novisit(server + '/page') as response:
            assert response.status == 200
            assert b'loggedin=yes' in response.read()
    finally:
        first.release()
        second.release()


def test_http_error_keeps_status(browser, server):
    tab = browser.clone_browser()
    try:
        with pytest.raises(HTTPError) as error:
            tab.open(server + '/missing', timeout=3)
        assert error.value.code == 404
    finally:
        tab.release()


def test_timeout_does_not_return_the_previous_document(browser, server):
    tab = browser.clone_browser()
    try:
        tab.open(server + '/page').close()
        with pytest.raises(URLError):
            tab.open(server + '/slow', timeout=0.1)
    finally:
        tab.release()
