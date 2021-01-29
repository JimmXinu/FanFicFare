# Copyright 2021 Sidney Markowitz All Rights Reserved.
# Distributed under MIT license.
# See file LICENSE for detail or copy at https://opensource.org/licenses/MIT

from .dictionary import BrotliDictionary
"""
Transformations on dictionary words

"""


class Transform:
    def __init__(self, prefix, transform, suffix):
        self.prefix = bytearray(prefix)
        self.transform = transform
        self.suffix = bytearray(suffix)

    @staticmethod
    def transformDictionaryWord(dst, idx, word, length, transform):
        prefix = kTransforms[transform].prefix
        suffix = kTransforms[transform].suffix
        t = kTransforms[transform].transform
        skip = t < (0 if kOmitFirst1 else (t - (kOmitFirst1 - 1)))
        start_idx = idx
        if skip > length:
            skip = length

        prefix_pos = 0
        while prefix_pos < len(prefix):
            dst[idx] = prefix[prefix_pos]
            idx += 1
            prefix_pos += 1

        word += skip
        length -= skip

        if t <= kOmitLast9:
            length -= t

        for i in range(0, length):
            dst[idx] = BrotliDictionary.dictionary[word + i]
            idx += 1

        uppercase = idx - length

        if t == kUppercaseFirst:
            _to_upper_case(dst, uppercase)
        elif t == kUppercaseAll:
            while length > 0:
                step = _to_upper_case(dst, uppercase)
                uppercase += step
                length -= step

        suffix_pos = 0
        while suffix_pos < len(suffix):
            dst[idx] = suffix[suffix_pos]
            idx += 1
            suffix_pos += 1

        return idx - start_idx


kIdentity = 0
kOmitLast1 = 1
kOmitLast2 = 2
kOmitLast3 = 3
kOmitLast4 = 4
kOmitLast5 = 5
kOmitLast6 = 6
kOmitLast7 = 7
kOmitLast8 = 8
kOmitLast9 = 9
kUppercaseFirst = 10
kUppercaseAll = 11
kOmitFirst1 = 12
kOmitFirst2 = 13
kOmitFirst3 = 14
kOmitFirst4 = 15
kOmitFirst5 = 16
kOmitFirst6 = 17
kOmitFirst7 = 18
kOmitFirst8 = 19
kOmitFirst9 = 20

kTransforms = [
    Transform(b"", kIdentity, b""),
    Transform(b"", kIdentity, b" "),
    Transform(b" ", kIdentity, b" "),
    Transform(b"", kOmitFirst1, b""),
    Transform(b"", kUppercaseFirst, b" "),
    Transform(b"", kIdentity, b" the "),
    Transform(b" ", kIdentity, b""),
    Transform(b"s ", kIdentity, b" "),
    Transform(b"", kIdentity, b" of "),
    Transform(b"", kUppercaseFirst, b""),
    Transform(b"", kIdentity, b" and "),
    Transform(b"", kOmitFirst2, b""),
    Transform(b"", kOmitLast1, b""),
    Transform(b", ", kIdentity, b" "),
    Transform(b"", kIdentity, b", "),
    Transform(b" ", kUppercaseFirst, b" "),
    Transform(b"", kIdentity, b" in "),
    Transform(b"", kIdentity, b" to "),
    Transform(b"e ", kIdentity, b" "),
    Transform(b"", kIdentity, b"\""),
    Transform(b"", kIdentity, b"."),
    Transform(b"", kIdentity, b"\">"),
    Transform(b"", kIdentity, b"\n"),
    Transform(b"", kOmitLast3, b""),
    Transform(b"", kIdentity, b"]"),
    Transform(b"", kIdentity, b" for "),
    Transform(b"", kOmitFirst3, b""),
    Transform(b"", kOmitLast2, b""),
    Transform(b"", kIdentity, b" a "),
    Transform(b"", kIdentity, b" that "),
    Transform(b" ", kUppercaseFirst, b""),
    Transform(b"", kIdentity, b". "),
    Transform(b".", kIdentity, b""),
    Transform(b" ", kIdentity, b", "),
    Transform(b"", kOmitFirst4, b""),
    Transform(b"", kIdentity, b" with "),
    Transform(b"", kIdentity, b"'"),
    Transform(b"", kIdentity, b" from "),
    Transform(b"", kIdentity, b" by "),
    Transform(b"", kOmitFirst5, b""),
    Transform(b"", kOmitFirst6, b""),
    Transform(b" the ", kIdentity, b""),
    Transform(b"", kOmitLast4, b""),
    Transform(b"", kIdentity, b". The "),
    Transform(b"", kUppercaseAll, b""),
    Transform(b"", kIdentity, b" on "),
    Transform(b"", kIdentity, b" as "),
    Transform(b"", kIdentity, b" is "),
    Transform(b"", kOmitLast7, b""),
    Transform(b"", kOmitLast1, b"ing "),
    Transform(b"", kIdentity, b"\n\t"),
    Transform(b"", kIdentity, b":"),
    Transform(b" ", kIdentity, b". "),
    Transform(b"", kIdentity, b"ed "),
    Transform(b"", kOmitFirst9, b""),
    Transform(b"", kOmitFirst7, b""),
    Transform(b"", kOmitLast6, b""),
    Transform(b"", kIdentity, b"("),
    Transform(b"", kUppercaseFirst, b", "),
    Transform(b"", kOmitLast8, b""),
    Transform(b"", kIdentity, b" at "),
    Transform(b"", kIdentity, b"ly "),
    Transform(b" the ", kIdentity, b" of "),
    Transform(b"", kOmitLast5, b""),
    Transform(b"", kOmitLast9, b""),
    Transform(b" ", kUppercaseFirst, b", "),
    Transform(b"", kUppercaseFirst, b"\""),
    Transform(b".", kIdentity, b"("),
    Transform(b"", kUppercaseAll, b" "),
    Transform(b"", kUppercaseFirst, b"\">"),
    Transform(b"", kIdentity, b"=\""),
    Transform(b" ", kIdentity, b"."),
    Transform(b".com/", kIdentity, b""),
    Transform(b" the ", kIdentity, b" of the "),
    Transform(b"", kUppercaseFirst, b"'"),
    Transform(b"", kIdentity, b". This "),
    Transform(b"", kIdentity, b","),
    Transform(b".", kIdentity, b" "),
    Transform(b"", kUppercaseFirst, b"("),
    Transform(b"", kUppercaseFirst, b"."),
    Transform(b"", kIdentity, b" not "),
    Transform(b" ", kIdentity, b"=\""),
    Transform(b"", kIdentity, b"er "),
    Transform(b" ", kUppercaseAll, b" "),
    Transform(b"", kIdentity, b"al "),
    Transform(b" ", kUppercaseAll, b""),
    Transform(b"", kIdentity, b"='"),
    Transform(b"", kUppercaseAll, b"\""),
    Transform(b"", kUppercaseFirst, b". "),
    Transform(b" ", kIdentity, b"("),
    Transform(b"", kIdentity, b"ful "),
    Transform(b" ", kUppercaseFirst, b". "),
    Transform(b"", kIdentity, b"ive "),
    Transform(b"", kIdentity, b"less "),
    Transform(b"", kUppercaseAll, b"'"),
    Transform(b"", kIdentity, b"est "),
    Transform(b" ", kUppercaseFirst, b"."),
    Transform(b"", kUppercaseAll, b"\">"),
    Transform(b" ", kIdentity, b"='"),
    Transform(b"", kUppercaseFirst, b","),
    Transform(b"", kIdentity, b"ize "),
    Transform(b"", kUppercaseAll, b"."),
    Transform(b"\xc2\xa0", kIdentity, b""),
    Transform(b" ", kIdentity, b","),
    Transform(b"", kUppercaseFirst, b"=\""),
    Transform(b"", kUppercaseAll, b"=\""),
    Transform(b"", kIdentity, b"ous "),
    Transform(b"", kUppercaseAll, b", "),
    Transform(b"", kUppercaseFirst, b"='"),
    Transform(b" ", kUppercaseFirst, b","),
    Transform(b" ", kUppercaseAll, b"=\""),
    Transform(b" ", kUppercaseAll, b", "),
    Transform(b"", kUppercaseAll, b","),
    Transform(b"", kUppercaseAll, b"("),
    Transform(b"", kUppercaseAll, b". "),
    Transform(b" ", kUppercaseAll, b"."),
    Transform(b"", kUppercaseAll, b"='"),
    Transform(b" ", kUppercaseAll, b". "),
    Transform(b" ", kUppercaseFirst, b"=\""),
    Transform(b" ", kUppercaseAll, b"='"),
    Transform(b" ", kUppercaseFirst, b"='")
]

kNumTransforms = len(kTransforms)


def _to_upper_case(p, i):
    """Overly simplified model of uppercase in utf-8, but what RFC7932 specifies to use"""
    if p[i] < 0xc0:
        if 97 <= p[i] <= 122:
            p[i] ^= 32
        return 1
    if p[i] < 0xe0:
        p[i + 1] ^= 32
        return 2
    p[i + 2] ^= 5
    return 3
