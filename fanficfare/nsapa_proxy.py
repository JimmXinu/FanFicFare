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
import time
import logging

logger = logging.getLogger(__name__)

from . import exceptions
from .fetcher import RequestsFetcher, FetcherResponse, make_log

import socket


class NSAPA_ProxyFetcher(RequestsFetcher):

    def __init__(self, getConfig_fn, getConfigList_fn):
        super(NSAPA_ProxyFetcher, self).__init__(getConfig_fn,
                                                 getConfigList_fn)

    def proxy_request(self, url, timeout=5):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setblocking(True)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        try:
            s.connect((self.getConfig("nsapa_proxy_address", "127.0.0.1"),
                       int(self.getConfig("nsapa_proxy_port", 8888))))

        except socket.error as e:
            logger.error("proxy unavailable, socket error: %s", str(e))
            raise ConnectionError(
                "nsapa_proxy: proxy %s:%i unavailable" %
                (self.getConfig("nsapa_proxy_address", "127.0.0.1"),
                 int(self.getConfig("nsapa_proxy_port", 8888))))

        sent = s.sendall(url.encode('utf-8'))
        if sent == 0:
            logger.debug('connection lost while sending command')

        header_raw = s.recv(1024)
        header = header_raw.split(b'$END_OF_HEADER$')[0].decode('utf-8')

        # If we received a part of the payload here, save it
        # so we can inject it before the payload receive loop
        pre_data = None
        if len(header_raw.split(b'$END_OF_HEADER$')) > 1:
            pre_data = header_raw.split(b'$END_OF_HEADER$')[1]

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

        logger.debug('expecting %i bytes of %s', size_expected, type_expected)

        # Payload receive loop
        bytes_recd = 0

        #Based on code from https://code.activestate.com/recipes/408859/
        #Licenced under PSF by John Nielsen
        s.setblocking(False)
        total_data = []
        data = ''
        begin = time.time()

        if pre_data is not None:
            if len(pre_data) > 0:
                total_data.append(pre_data)
                bytes_recd += len(pre_data)
                logger.debug("injecting %i bytes from the first recv()",
                             bytes_recd)

        while True:
            # We received everything we expected
            if bytes_recd == size_expected:
                logger.debug('exiting receive loop after %i bytes', bytes_recd)
                break
            #if you got some data, then break after wait sec
            if total_data and time.time() - begin > timeout:
                logger.debug("timeout while receiving data")
                break
            #if you got no data at all, wait a little longer
            elif time.time() - begin > timeout * 2:
                logger.debug("socket timeout (%i seconds)", timeout)
                break
            try:
                data = s.recv(8192)
                if data:
                    total_data.append(data)
                    bytes_recd += len(data)
                    begin = time.time()
                else:
                    time.sleep(0.1)
            except:
                pass
        #End of Code from https://code.activestate.com/recipes/408859/
        logger.debug('leaving receive loop after %i bytes', bytes_recd)

        s.close()

        if bytes_recd != size_expected:
            # Truncated reply, log the issue
            logger.error(
                'truncated reply from proxy! Expected %i bytes, received %i!' %
                (size_expected, bytes_recd))
            raise exceptions.FailedToDownload(
                'nsapa_proxy: truncated reply from proxy')

        if type_expected == 'text':
            content = b''.join(total_data).decode("utf-8")

        if type_expected == 'text-b64':
            content = b''.join(total_data).decode("utf-8")
            try:
                content = base64.standard_b64decode(content)
            except binascii.Error:
                raise exceptions.FailedToDownload(
                    'nsapa_proxy: base64 decoding failed')

        if type_expected == 'image':
            content = b''.join(total_data)
            #logger.debug('Got %i bytes of image', len(content))

        if type_expected == 'binary':
            raise NotImplementedError("nsapa_proxy: type %s unimplemented" %
                                      type_expected)

        return (type_expected, content)

    def request(self, method, url, headers=None, parameters=None):
        if method != 'GET':
            raise NotImplementedError

        logger.debug(
            make_log('NSAPA_ProxyFetcher', method, url, hit='REQ', bar='-'))
        content = b'initial_data'
        retry_count = 0
        timeout = 5
        while (retry_count < 5):  #FIXME: make the retry counter configurable
            try:
                timeout = timeout + retry_count * 5
                logger.debug("setting timeout to %i seconds", timeout)

                (type_expected, content) = self.proxy_request(url, timeout)
                # Everything is fine, escape the retry loop
                retry_count = 6
                break

            except exceptions.FailedToDownload:
                logger.debug('resetting the browser state')
                self.proxy_request(
                    'chrome://version'
                )  # Loading a very simple website seem to 'fix' this
                logger.debug('waiting 5 seconds to let the browser settle')
                time.sleep(5)

            finally:
                retry_count += 1
                #Needed to catch the raise

                ## continue from finally: not valid in Python2
                ## (Calibre < v5).  Also, continue here seems
                ## unnecessary--we're at the end of the loop. --JM
                # continue

        if retry_count == 5:
            # We exited the retry loop without any valid content,
            raise exceptions.FailedToDownload(
                'nsapa_proxy: reply still truncated after %i retry' %
                retry_count)

        return FetcherResponse(content, url, False)
