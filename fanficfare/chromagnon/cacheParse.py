#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2012, Jean-Rémy Bancel <jean-remy.bancel@telecom-paristech.org>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Chromagon Project nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Jean-Rémy Bancel BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Parse the Chrome Cache File
See http://www.chromium.org/developers/design-documents/network-stack/disk-cache
for design details
"""

from __future__ import absolute_import
from __future__ import print_function
import gzip
import zlib
import os
import struct
import sys


try:
    from brotli import decompress
    def brotli_decompress(inbuf):
        return decompress(inbuf)
except:
    # Calibre doesn't include brotli, so use packaged brotlipython
    # which is waaaay slower, but pure python.
    from brotlipython import brotlidec
    def brotli_decompress(inbuf):
        # wants the output, too, but returns it
        return brotlidec(inbuf,[])

from . import SuperFastHash

from .cacheAddress import CacheAddress
from .cacheBlock import CacheBlock
from .cacheData import CacheData
from .cacheEntry import CacheEntry
from six.moves import range

class ChromeCache(object):
    def __init__(self,path):
        self.path = os.path.abspath(path)
        self.cacheBlock = CacheBlock(os.path.join(path, "index"))

        # Checking type
        if self.cacheBlock.type != CacheBlock.INDEX:
            raise Exception("Invalid Index File")
        self.get_cache_keys()

    def get_cache_keys(self):
        """Scan index file and cache entries to set self.cache_keys to set of the keys (as strings) in this cache"""
        with open(os.path.join(self.path, "index"), 'rb') as index:
            # Skipping Header
            index.seek(92*4)
            self.cache_keys = set()
            for key in range(self.cacheBlock.tableSize):
                raw = struct.unpack('I', index.read(4))[0]
                if raw != 0:
                    entry = CacheEntry(CacheAddress(raw, path=self.path))
                    # Checking if there is a next item in the bucket because
                    # such entries are not stored in the Index File so they will
                    # be ignored during iterative lookup in the hash table
                    while entry.next != 0:
                        self.cache_keys.add(entry.keyToStr())
                        entry = CacheEntry(CacheAddress(entry.next, path=self.path))
                    self.cache_keys.add(entry.keyToStr())

    def get_cache_entry(self,url):
        url = bytes(url,'utf8')
        # Compute the key and seeking to it
        # print("url:%s"%url)
        hash = SuperFastHash.superFastHash(url)
        # print("superFastHash:%s"%hash)
        key = hash & (self.cacheBlock.tableSize - 1)
        with open(os.path.join(self.path, "index"), 'rb') as index:
            index.seek(92*4 + key*4)

            addr = struct.unpack('I', index.read(4))[0]
            # Checking if the address is initialized (i.e. used)
            if addr & 0x80000000 == 0:
                print("%s is not in the cache" % url, file=sys.stderr)

            # Follow the chained list in the bucket
            else:
                entry = CacheEntry(CacheAddress(addr, path=self.path))
                while entry.hash != hash and entry.next != 0:
                    entry = CacheEntry(CacheAddress(entry.next, path=self.path))
                if entry.hash == hash:
                    return entry

    def get_cached_file(self,url):
        entry = self.get_cache_entry(url)
        if entry:
            # entry = self.hash_cache[url]
            for i in range(len(entry.data)):
                if entry.data[i].type == CacheData.UNKNOWN:
                    # Extracting data into a file
                    data = entry.data[i].data()

                    # print("content-encoding:%s"%entry.httpHeader.headers.get(b'content-encoding',''))
                    if entry.httpHeader != None and \
                       b'content-encoding' in entry.httpHeader.headers:
                        if entry.httpHeader.headers[b'content-encoding'] == b"gzip":
                            data = gzip.decompress(data)
                        elif entry.httpHeader.headers[b'content-encoding'] == b"br":
                            data = brotli_decompress(data)
                        elif entry.httpHeader.headers[b'content-encoding'] == b"deflate":
                            data = zlib.decompress(data)
                    return data
        return None
