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
Chrome Cache Address
See /net/disk_cache/addr.h for design details
"""

class CacheAddressError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class CacheAddress():
    """
    Object representing a Chrome Cache Address
    """
    SEPARATE_FILE = 0
    RANKING_BLOCK = 1
    BLOCK_256 = 2
    BLOCK_1024 = 3
    BLOCK_4096 = 4

    typeArray = [("Separate file", 0),
                 ("Ranking block file", 36),
                 ("256 bytes block file", 256),
                 ("1k bytes block file", 1024),
                 ("4k bytes block file", 4096)]

    def __init__(self, uint_32, path):
        """
        Parse the 32 bits of the uint_32
        """
        if uint_32 == 0:
            raise CacheAddressError("Null Address")

        #XXX Is self.binary useful ??
        self.addr = uint_32
        self.path = path

        # Checking that the MSB is set
        self.binary = bin(uint_32)
        if len(self.binary) != 34:
            raise CacheAddressError("Uninitialized Address")

        self.blockType = int(self.binary[3:6], 2)

        # If it is an address of a separate file
        if self.blockType == CacheAddress.SEPARATE_FILE:
            self.fileSelector = "f_%06x" % int(self.binary[6:], 2)
        elif self.blockType == CacheAddress.RANKING_BLOCK:
            self.fileSelector = "data_" + str(int(self.binary[10:18], 2))
        else:
            self.entrySize = CacheAddress.typeArray[self.blockType][1]
            self.contiguousBlock = int(self.binary[8:10], 2)
            self.fileSelector = "data_" + str(int(self.binary[10:18], 2))
            self.blockNumber = int(self.binary[18:], 2)

    def __str__(self):
        string = hex(self.addr) + " ("
        if self.blockType >= CacheAddress.BLOCK_256:
            string += str(self.contiguousBlock) +\
                      " contiguous blocks in "
        string += CacheAddress.typeArray[self.blockType][0] +\
                  " : " + self.fileSelector + ")"
        return string
