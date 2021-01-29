# Copyright 2021 Sidney Markowitz All Rights Reserved.
# Distributed under MIT license.
# See file LICENSE for detail or copy at https://opensource.org/licenses/MIT

import pkgutil


class BrotliDictionary:
    def __init__(self):
        pass

    offsetsByLength = [
        0,     0,     0,     0,     0,  4096,  9216, 21504, 35840, 44032,
        53248, 63488, 74752, 87040, 93696, 100864, 104704, 106752, 108928, 113536,
        115968, 118528, 119872, 121280, 122016
    ]

    sizeBitsByLength = bytearray([
        0,  0,  0,  0, 10, 10, 11, 11, 10, 10,
        10, 10, 10,  9,  9,  8,  7,  7,  8,  7,
        7,  6,  6,  5,  5
    ])

    minDictionaryWordLength = 4
    maxDictionaryWordLength = 24

    dictionary = pkgutil.get_data('_brotlidecpy', 'brotli-dict')
