# -*- coding: utf-8 -*-

# Copyright 2021 FanFicFare team
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

import base64
import binascii
import time
import logging

logger = logging.getLogger(__name__)

from .. import exceptions
from .log import make_log
from .base_fetcher import FetcherResponse
from .fetcher_requests import RequestsFetcher

import socket

## proxy reply is '<size>||<type>$END_OF_HEADER$<payload>'
END_OF_HEADER = b'$END_OF_HEADER$'
MAX_HEADER_SIZE = 1024

class NSAPA_ProxyFetcher(RequestsFetcher):

    def __init__(self, getConfig_fn, getConfigList_fn):
        super(NSAPA_ProxyFetcher, self).__init__(getConfig_fn,
                                                 getConfigList_fn)

    def get_header_timeout(self):
        ## The proxy only sends the header after the browser has
        ## loaded the page, so wait as long as for a normal request.
        timeout = 60.0
        try:
            timeout = float(self.getConfig("connect_timeout",timeout))
        except Exception as e:
            logger.error("connect_timeout setting failed: %s -- Using default value(%s)"%(e,timeout))
        return timeout

    def proxy_request(self, url, timeout=5):
        address = (self.getConfig("nsapa_proxy_address", "127.0.0.1"),
                   int(self.getConfig("nsapa_proxy_port", 8888)))
        try:
            s = socket.create_connection(address,
                                         timeout=self.get_header_timeout())
        except socket.error as e:
            logger.error("proxy unavailable, socket error: %s", str(e))
            raise ConnectionError(
                "nsapa_proxy: proxy %s:%i unavailable" % address)

        with s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            s.sendall(url.encode('utf-8'))
            (header, pre_data) = self.recv_header(s)
            (size_expected, type_expected) = self.parse_header(header)
            logger.debug('expecting %i bytes of %s', size_expected, type_expected)
            data = self.recv_payload(s, pre_data, size_expected, timeout)

        if type_expected == 'text':
            content = data.decode("utf-8")
        elif type_expected == 'text-b64':
            try:
                content = base64.standard_b64decode(data.decode("utf-8"))
            except (binascii.Error, UnicodeDecodeError):
                raise exceptions.FailedToDownload(
                    'nsapa_proxy: base64 decoding failed')
        elif type_expected == 'image':
            content = data
            #logger.debug('Got %i bytes of image', len(content))
        else:
            ## 'binary' or unknown.  Not FailedToDownload, retrying
            ## won't help.
            raise NotImplementedError("nsapa_proxy: type %s unimplemented" %
                                      type_expected)

        return (type_expected, content)

    def recv_header(self, s):
        '''
        Returns (header, pre_data).  The header can arrive in several
        pieces, and the first piece can include the start of the
        payload (pre_data).
        '''
        header_raw = b''
        try:
            while END_OF_HEADER not in header_raw:
                if len(header_raw) > MAX_HEADER_SIZE:
                    raise exceptions.FailedToDownload(
                        'nsapa_proxy: proxy protocol violation; header too long')
                chunk = s.recv(1024)
                if not chunk:
                    raise exceptions.FailedToDownload(
                        'nsapa_proxy: proxy closed connection before header')
                header_raw += chunk
        except socket.timeout:
            raise exceptions.FailedToDownload(
                'nsapa_proxy: timeout waiting for proxy header')
        (header, pre_data) = header_raw.split(END_OF_HEADER, 1)
        return (header.decode('utf-8'), pre_data)

    def parse_header(self, header):
        header_splited = header.split('||')
        if len(header_splited) < 2:
            raise exceptions.FailedToDownload(
                'nsapa_proxy: proxy protocol violation; only %d headers' %
                len(header_splited))

        size_expected = 0
        if header_splited[0].isnumeric():
            size_expected = int(header_splited[0])
        else:
            raise exceptions.FailedToDownload(
                'nsapa_proxy: proxy protocol violation; invalid size')

        if size_expected == 0:
            raise exceptions.FailedToDownload(
                'nsapa_proxy: proxy sent empty content')

        type_expected = header_splited[1]
        if not type_expected.strip():
            raise exceptions.FailedToDownload(
                'nsapa_proxy: proxy protocol violation; invalid type')

        return (size_expected, type_expected)

    def recv_payload(self, s, pre_data, size_expected, timeout):
        ## Wait up to timeout*2 for the first data, then up to timeout
        ## for each further piece.
        total_data = []
        bytes_recd = 0
        if pre_data:
            total_data.append(pre_data)
            bytes_recd += len(pre_data)
            logger.debug("injecting %i bytes from the header recv()",
                         bytes_recd)
        s.settimeout(timeout if total_data else timeout * 2)
        try:
            while bytes_recd < size_expected:
                data = s.recv(8192)
                if not data:
                    logger.debug("proxy closed connection")
                    break
                total_data.append(data)
                bytes_recd += len(data)
                s.settimeout(timeout)
        except socket.timeout:
            logger.debug("timeout while receiving data")
        logger.debug('leaving receive loop after %i bytes', bytes_recd)

        if bytes_recd != size_expected:
            # Truncated reply, log the issue
            logger.error(
                'truncated reply from proxy! Expected %i bytes, received %i!' %
                (size_expected, bytes_recd))
            raise exceptions.FailedToDownload(
                'nsapa_proxy: truncated reply from proxy')
        return b''.join(total_data)

    def request(self, method, url, headers=None, parameters=None):
        if method != 'GET':
            raise NotImplementedError

        logger.debug(
            make_log('NSAPA_ProxyFetcher', method, url, hit='REQ', bar='-'))
        tries = 5  #FIXME: make the retry counter configurable
        timeout = 5
        for retry_count in range(tries):
            timeout = timeout + retry_count * 5
            logger.debug("setting timeout to %i seconds", timeout)
            try:
                (type_expected, content) = self.proxy_request(url, timeout)
                return FetcherResponse(content, url, False)
            except exceptions.FailedToDownload as e:
                last_error = e
                logger.debug("nsapa_proxy request failed: %s", e)

            if retry_count < tries - 1:
                logger.debug('resetting the browser state')
                try:
                    # Loading a very simple website seem to 'fix' this
                    self.proxy_request('chrome://version')
                except exceptions.FailedToDownload as e:
                    logger.debug("resetting the browser state failed: %s", e)
                logger.debug('waiting 5 seconds to let the browser settle')
                time.sleep(5)

        # We exited the retry loop without any valid content,
        raise exceptions.FailedToDownload(
            'nsapa_proxy: failed after %i tries: %s' % (tries, last_error))
