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
Parse the header of a Chrome Cache File
See http://www.chromium.org/developers/design-documents/network-stack/disk-cache
for design details
"""
from __future__ import absolute_import
import struct
from six.moves import range

class CacheBlock():
    """
    Object representing a block of the cache. It can be the index file or any
    other block type : 256B, 1024B, 4096B, Ranking Block.
    See /net/disk_cache/disk_format.h for details.
    """

    INDEX_MAGIC = 0xC103CAC3
    BLOCK_MAGIC = 0xC104CAC3
    INDEX = 0
    BLOCK = 1

    def __init__(self, filename):
        """
        Parse the header of a cache file
        """
        with open(filename, 'rb') as header:
            # Read Magic Number
            magic = struct.unpack('I', header.read(4))[0]
            # print("magic number:%s"%hex(magic))
            if magic == CacheBlock.BLOCK_MAGIC:
                self.type = CacheBlock.BLOCK
                header.seek(2, 1)
                self.version = struct.unpack('h', header.read(2))[0]
                self.header = struct.unpack('h', header.read(2))[0]
                self.nextFile = struct.unpack('h', header.read(2))[0]
                self.blockSize = struct.unpack('I', header.read(4))[0]
                self.entryCount = struct.unpack('I', header.read(4))[0]
                self.entryMax = struct.unpack('I', header.read(4))[0]
                self.empty = []
                for _ in range(4):
                    self.empty.append(struct.unpack('I', header.read(4))[0])
                self.position = []
                for _ in range(4):
                    self.position.append(struct.unpack('I', header.read(4))[0])
            elif magic == CacheBlock.INDEX_MAGIC:
                self.type = CacheBlock.INDEX
                header.seek(2, 1)
                self.version = struct.unpack('h', header.read(2))[0]
                self.entryCount = struct.unpack('I', header.read(4))[0]
                self.byteCount = struct.unpack('I', header.read(4))[0]
                self.lastFileCreated = "f_%06x" % \
                                           struct.unpack('I', header.read(4))[0]
                header.seek(4*2, 1)
                self.tableSize = struct.unpack('I', header.read(4))[0]
            else:
                raise Exception("Invalid Chrome Cache File")

