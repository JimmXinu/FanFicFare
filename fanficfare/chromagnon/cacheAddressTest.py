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

from __future__ import absolute_import
import unittest

from . import cacheAddress

class CacheAddressTest(unittest.TestCase):

    def testFileType(self):
        """Parse Block Type From Address"""
        address = cacheAddress.CacheAddress(0x8000002A)
        self.assertEqual(address.blockType,
                         cacheAddress.CacheAddress.SEPARATE_FILE)
        address = cacheAddress.CacheAddress(0x9DFF0000)
        self.assertEqual(address.blockType,
                         cacheAddress.CacheAddress.RANKING_BLOCK)
        address = cacheAddress.CacheAddress(0xA0010003)
        self.assertEqual(address.blockType,
                         cacheAddress.CacheAddress.BLOCK_256)
        address = cacheAddress.CacheAddress(0xBDFF0108)
        self.assertEqual(address.blockType,
                         cacheAddress.CacheAddress.BLOCK_1024)
        address = cacheAddress.CacheAddress(0xCDFF0108)
        self.assertEqual(address.blockType,
                         cacheAddress.CacheAddress.BLOCK_4096)

    def testFilename(self):
        """Parse Filename from Address"""
        address = cacheAddress.CacheAddress(0x8000002A)
        self.assertEqual(address.fileSelector,
                         "f_0002A")
        address = cacheAddress.CacheAddress(0xA001135C)
        self.assertEqual(address.fileSelector,
                         "data_1")

if __name__ == "__main__":
    unittest.main()
