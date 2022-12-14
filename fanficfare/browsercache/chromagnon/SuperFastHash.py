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
Python implementation of SuperFastHash algorithm
Maybe it is better to use c_uint32 to limit the size of variables to 32bits
instead of using 0xFFFFFFFF mask.
"""

import binascii
import sys

def get16bits(data):
    """Returns the first 16bits of a string"""
    return int(binascii.hexlify(data[1::-1]), 16)

def superFastHash(data):
    hash = length = len(data)
    if length == 0:
        return 0

    rem = length & 3
    length >>= 2

    while length > 0:
        hash += get16bits(data) & 0xFFFFFFFF
        tmp = (get16bits(data[2:])<< 11) ^ hash
        hash = ((hash << 16) & 0xFFFFFFFF) ^ tmp
        data = data[4:]
        hash += hash >> 11
        hash = hash & 0xFFFFFFFF
        length -= 1

    if rem == 3:
        hash += get16bits (data)
        hash ^= (hash << 16) & 0xFFFFFFFF
        hash ^= (int(binascii.hexlify(data[2]), 16) << 18) & 0xFFFFFFFF
        hash += hash >> 11
    elif rem == 2:
        hash += get16bits (data)
        hash ^= (hash << 11) & 0xFFFFFFFF
        hash += hash >> 17
    elif rem == 1:
        hash += int(binascii.hexlify(data[0]), 16)
        hash ^= (hash << 10) & 0xFFFFFFFF
        hash += hash >> 1

    hash = hash & 0xFFFFFFFF
    hash ^= (hash << 3) & 0xFFFFFFFF
    hash += hash >> 5
    hash = hash & 0xFFFFFFFF
    hash ^= (hash << 4) & 0xFFFFFFFF
    hash += hash >> 17
    hash = hash & 0xFFFFFFFF
    hash ^= (hash << 25) & 0xFFFFFFFF
    hash += hash >> 6
    hash = hash & 0xFFFFFFFF

    return hash

if __name__ == "__main__":
    print("%08x"%superFastHash(sys.argv[1]))
