# Copyright 2021 Sidney Markowitz All Rights Reserved.
# Distributed under MIT license.
# See file LICENSE for detail or copy at https://opensource.org/licenses/MIT


class BrotliBitReader:
    """Wrap a bytes buffer to enable reading 0 < n <=24 bits at a time, or transfer of arbitrary number of bytes"""

    kBitMask = [
        0x000000, 0x000001, 0x000003, 0x000007, 0x00000f, 0x00001f, 0x00003f, 0x00007f,
        0x0000ff, 0x0001ff, 0x0003ff, 0x0007ff, 0x000fff, 0x001fff, 0x003fff, 0x007fff,
        0x00ffff, 0x01ffff, 0x03ffff, 0x07ffff, 0x0fffff, 0x1fffff, 0x3fffff, 0x7fffff,
        0xffffff
    ]

    def __init__(self, input_buffer):
        self.buf_ = bytearray(input_buffer)
        self.buf_len_ = len(input_buffer)
        self.pos_ = 0          # byte position in stream
        self.bit_pos_ = 0      # current bit-reading position in current byte (number bits already read from byte, 0-7)

    def reset(self):
        """Reset an initialized BrotliBitReader to start of input buffer"""
        self.pos_ = 0
        self.bit_pos_ = 0

    def read_bits(self, n_bits, bits_to_skip=None):
        """Get n_bits unsigned integer treating input as little-endian byte stream, maybe advancing input buffer pointer
        n_bits: is number of bits to read from input buffer. Set to None or 0 to seek ahead ignoring the value
        bits_to_skip: number of bits to advance in input_buffer, defaults to n_bits if it is None
           pass in 0 to peek at the next n_bits of value without advancing
        It is ok to have n_bits and bits_to_skip be different non-zero values if that is what is wanted
        Returns: the next n_bits from the buffer as a little-endian integer, 0 if n_bits is None or 0
        """
        val = 0
        if bits_to_skip is None:
            bits_to_skip = n_bits
        if n_bits:
            bytes_shift = 0
            buf_pos = self.pos_
            bit_pos_when_done = n_bits + self.bit_pos_
            while bytes_shift < bit_pos_when_done:
                if buf_pos >= self.buf_len_:
                    break  # if hit end of buffer, this simulates zero padding after end, which is correct
                val |= self.buf_[buf_pos] << bytes_shift
                bytes_shift += 8
                buf_pos += 1
            val = (val >> self.bit_pos_) & self.kBitMask[n_bits]
        if bits_to_skip:
            next_in_bits = self.bit_pos_ + bits_to_skip
            self.bit_pos_ = next_in_bits & 7
            self.pos_ += next_in_bits >> 3
        return val

    def copy_bytes(self, dest_buffer, dest_pos, n_bytes):
        """Copy bytes from input buffer. This will first skip to next byte boundary if not already on one"""
        if self.bit_pos_ != 0:
            self.bit_pos_ = 0
            self.pos_ += 1
        if n_bytes > 0:  # call with n_bytes == 0 to just skip to next byte boundary
            new_pos = self.pos_ + n_bytes
            memoryview(dest_buffer)[dest_pos:dest_pos+n_bytes] = self.buf_[self.pos_:new_pos]
            self.pos_ = new_pos
