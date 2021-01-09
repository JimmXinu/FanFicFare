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
Parse the Chrome Visited Links
Reverse engineered from
  chrome/common/visitedlink_common.*
  chrome/browser/visitedlink/visitedlink_*
"""

from __future__ import absolute_import
import md5
import struct
import sys
from six.moves import range

VISITED_LINKS_MAGIC = 0x6b6e4c56;

def isVisited(path, urls):
    """
    Return the list of urls given in parameter with a boolean information
    about its presence in the given visited links file
    """
    output = []

    f = open(path, 'rb')

    # Checking file type
    magic = struct.unpack('I', f.read(4))[0]
    if magic != VISITED_LINKS_MAGIC:
        raise Exception("Invalid file")

    # Reading header values
    version = struct.unpack('I', f.read(4))[0]
    length = struct.unpack('I', f.read(4))[0]
    usedItems = struct.unpack('I', f.read(4))[0]

    # Reading salt
    salt = ""
    for dummy in range(8):
        salt += struct.unpack('c', f.read(1))[0]

    for url in urls:
        fingerprint = md5.new()
        fingerprint.update(salt)
        fingerprint.update(url)
        digest = fingerprint.hexdigest()

        # Inverting the result
        # Why Chrome MD5 computation gives a reverse digest ?
        fingerprint = 0
        for i in range(0, 16, 2):
            fingerprint += int(digest[i:i+2], 16) << (i/2)*8
        key = fingerprint % length

        # The hash table uses open addressing
        f.seek(key*8 + 24, 0)
        while True:
            finger = struct.unpack('q', f.read(8))[0]
            if finger == 0:
                output.append((url, False))
                break
            if finger == fingerprint:
                output.append((url, True))
                break
            if f.tell() >= length*8 + 24:
                f.seek(24)
            if f.tell() == key*8 + 24:
                output.append((url, False))
                break
    f.close()
    return output
