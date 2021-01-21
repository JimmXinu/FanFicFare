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
Stores the data fetched in the cache.
Parse the HTTP header if asked.
"""

from __future__ import absolute_import
import re
import shutil
import struct
import os

from . import cacheAddress
from six.moves import range

class CacheData():
    """
    Retrieve data at the given address
    Can save it to a separate file for export
    """

    HTTP_HEADER = 0
    UNKNOWN = 1

    def __init__(self, address, size, isHTTPHeader=False):
        """
        It is a lazy evaluation object : the file is open only if it is
        needed. It can parse the HTTP header if asked to do so.
        See net/http/http_util.cc LocateStartOfStatusLine and
        LocateEndOfHeaders for details.
        """
        self.size = size
        self.address = address
        self.type = CacheData.UNKNOWN

        if isHTTPHeader and\
           self.address.blockType != cacheAddress.CacheAddress.SEPARATE_FILE:
            # Getting raw data
            string = b""
            block = open(os.path.join(self.address.path,self.address.fileSelector), 'rb')
            block.seek(8192 + self.address.blockNumber*self.address.entrySize)
            for _ in range(self.size):
                string += struct.unpack('c', block.read(1))[0]
            block.close()

            # Finding the beginning of the request
            start = re.search(b"HTTP", string)
            if start == None:
                return
            else:
                string = string[start.start():]

            # Finding the end (some null characters : verified by experience)
            end = re.search(b"\x00\x00", string)
            if end == None:
                return
            else:
                string = string[:end.end()-2]

            # Creating the dictionary of headers
            self.headers = {}
            for line in string.split(b'\0'):
                stripped = line.split(b':')
                self.headers[stripped[0].lower()] = \
                    b':'.join(stripped[1:]).strip()
            self.type = CacheData.HTTP_HEADER

    def save(self, filename=None):
        """Save the data to the specified filename"""
        if self.address.blockType == cacheAddress.CacheAddress.SEPARATE_FILE:
            shutil.copy(os.path.join(self.address.path,self.address.fileSelector),
                        filename)
        else:
            output = open(filename, 'wb')
            block = open(os.path.join(self.address.path,self.address.fileSelector), 'rb')
            block.seek(8192 + self.address.blockNumber*self.address.entrySize)
            output.write(block.read(self.size))
            block.close()
            output.close()

    def data(self):
        """Returns a string representing the data"""
        if self.address.blockType == cacheAddress.CacheAddress.SEPARATE_FILE:
            with open(os.path.join(self.address.path,self.address.fileSelector), 'rb') as infile:
                data = infile.read()
        else:
            block = open(os.path.join(self.address.path,self.address.fileSelector), 'rb')
            block.seek(8192 + self.address.blockNumber*self.address.entrySize)
            data = block.read(self.size)#.decode('utf-8',errors='ignore')
            block.close()
        return data

    def __str__(self):
        """
        Display the type of cacheData
        """
        if self.type == CacheData.HTTP_HEADER:
            if 'content-type' in self.headers:
                return "HTTP Header %s" % self.headers['content-type']
            else:
                return "HTTP Header"
        else:
            return "Data"
