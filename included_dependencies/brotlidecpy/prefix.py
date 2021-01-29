# Copyright 2021 Sidney Markowitz All Rights Reserved.
# Distributed under MIT license.
# See file LICENSE for detail or copy at https://opensource.org/licenses/MIT

class Prefix:
    """Represents the range of values belonging to a prefix code: [offset, offset + 2^nbits)"""
    def __init__(self, offset, nbits):
        self.offset = offset
        self.nbits = nbits

    kInsertRangeLut = [0, 0, 8, 8, 0, 16, 8, 16, 16]

    kCopyRangeLut = [0, 8, 0, 8, 16, 0, 16, 8, 16]


kBlockLengthPrefixCode = [
   Prefix(1, 2), Prefix(5, 2), Prefix(9, 2), Prefix(13, 2),
   Prefix(17, 3), Prefix(25, 3), Prefix(33, 3), Prefix(41, 3),
   Prefix(49, 4), Prefix(65, 4), Prefix(81, 4), Prefix(97, 4),
   Prefix(113, 5), Prefix(145, 5), Prefix(177, 5), Prefix(209, 5),
   Prefix(241, 6), Prefix(305, 6), Prefix(369, 7), Prefix(497, 8),
   Prefix(753, 9), Prefix(1265, 10), Prefix(2289, 11), Prefix(4337, 12),
   Prefix(8433, 13), Prefix(16625, 24)]

kInsertLengthPrefixCode = [
   Prefix(0, 0), Prefix(1, 0), Prefix(2, 0), Prefix(3, 0),
   Prefix(4, 0), Prefix(5, 0), Prefix(6, 1), Prefix(8, 1),
   Prefix(10, 2), Prefix(14, 2), Prefix(18, 3), Prefix(26, 3),
   Prefix(34, 4), Prefix(50, 4), Prefix(66, 5), Prefix(98, 5),
   Prefix(130, 6), Prefix(194, 7), Prefix(322, 8), Prefix(578, 9),
   Prefix(1090, 10), Prefix(2114, 12), Prefix(6210, 14), Prefix(22594, 24)]

kCopyLengthPrefixCode = [
   Prefix(2, 0), Prefix(3, 0), Prefix(4, 0), Prefix(5, 0),
   Prefix(6, 0), Prefix(7, 0), Prefix(8, 0), Prefix(9, 0),
   Prefix(10, 1), Prefix(12, 1), Prefix(14, 2), Prefix(18, 2),
   Prefix(22, 3), Prefix(30, 3), Prefix(38, 4), Prefix(54, 4),
   Prefix(70, 5), Prefix(102, 5), Prefix(134, 6), Prefix(198, 7),
   Prefix(326, 8), Prefix(582, 9), Prefix(1094, 10), Prefix(2118, 24)]
