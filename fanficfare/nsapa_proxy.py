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

import logging
logger = logging.getLogger(__name__)


from .fetcher import RequestsFetcher, FetcherResponse, make_log

import socket
class NSAPA_ProxyFetcher(RequestsFetcher):
    def __init__(self,getConfig_fn,getConfigList_fn):
        super(NSAPA_ProxyFetcher,self).__init__(getConfig_fn,getConfigList_fn)

    def proxy_request(self,url):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setblocking(True)
        s.connect((self.getConfig("nsapa_proxy_address","127.0.0.1"),
                   int(self.getConfig("nsapa_proxy_port",8888))))
        #logger.debug('Sending URL to socket')
        sent = s.sendall(url.encode('utf-8'))
        if sent == 0:
            logging.debug('Connection lost during sending')

        header_raw = s.recv(4096)
        header = header_raw.split(b'$END_OF_HEADER$')[0].decode('utf-8')
        size_expected = int(header.split('||')[0])
        type_expected = header.split('||')[1]
        logger.debug('Expecting %i bytes of %s', size_expected, type_expected)

        chunks = []
        bytes_recd = 0

        while bytes_recd <= size_expected:
            chunk = s.recv(4096)
            #logger.debug('Receiving %i bytes from socket', bytes_recd)
            #if len(chunk.split(b'$END_OF_HEADER$')) > 1:
                # We have part of the header in our chunk!
                #chunk = chunk.split(b'$END_OF_HEADER$')[1]
            if chunk == b'':
                logging.debug('connection closed by remote host')
                break
            chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)
        logger.debug('closing connection after %i bytes', bytes_recd)

        s.close()

        if type_expected == 'text':
            content = b''.join(chunks).decode("utf-8")

        if type_expected == 'image':
            content = b''.join(chunks)
            #logger.debug('Got %i bytes of image', len(content))

        if type_expected == 'binary':
            raise NotImplementedError()

        # return (type,expected_size,received_size,content_as_bytes)
        return (type_expected,size_expected,bytes_recd,content)

    def request(self,method,url,headers=None,parameters=None):
        if method != 'GET':
            raise NotImplementedError()

        logger.debug(make_log('NSAPA_ProxyFetcher',method,url,hit='REQ',bar='-'))
        content = b'initial_data'
        retry_count = 0
        while (retry_count < 5): #FIXME: make the retry counter configurable
            (type_expected,size_expected,received_size,content) = self.proxy_request(url)

            if received_size == size_expected:
                # Everything normal
                retry_count = 0
                break

            # Truncated reply, log the issue
            logger.error('truncated reply from proxy! Expected %i bytes, received %i! ' % (size_expected, received_size))

            logger.debug('resetting the browser state')
            self.proxy_request('http://www.example.com') # Loading a very simple website seem to 'fix' this
            logger.debug('waiting 5 seconds to let the browser settle')
            time.sleep(5)

            retry_count += 1

        if retry_count == 5:
            # We exited the retry loop without any valid content,
            raise exceptions.FailedToDownload('fanfictionnet_ff_proxy: truncated reply from proxy')

        return FetcherResponse(content,
                                   url,
                                   False)
