# Copyright 2021 Sidney Markowitz All Rights Reserved.
# Distributed under MIT license.
# See file LICENSE for detail or copy at https://opensource.org/licenses/MIT

kBitMask = [
    0x000000, 0x000001, 0x000003, 0x000007, 0x00000f, 0x00001f, 0x00003f, 0x00007f,
    0x0000ff, 0x0001ff, 0x0003ff, 0x0007ff, 0x000fff, 0x001fff, 0x003fff, 0x007fff,
    0x00ffff, 0x01ffff, 0x03ffff, 0x07ffff, 0x0fffff, 0x1fffff, 0x3fffff, 0x7fffff,
    0xffffff
]


class BrotliBitReader:
    """Wrap a bytes buffer to enable reading 0 < n <=24 bits at a time, or transfer of arbitrary number of bytes"""
    def __init__(self, input_buffer):
        self.buf_ = bytearray(input_buffer)
        self.buf_len_ = len(input_buffer)
        self.pos_ = 0          # byte position in stream
        self.bit_pos_ = 0      # current bit-reading position in current byte (number bits already read from byte, 0-7)

    def reset(self):
        """Reset an initialized BrotliBitReader to start of input buffer"""
        self.pos_ = 0
        self.bit_pos_ = 0

    def peek_bits(self, n_bits):
        """Get value a n_bits unsigned integer treating input as little-endian byte stream, without advancing pointer"""
        val = 0
        bytes_shift = 0
        buf_pos = self.pos_
        bit_pos_when_done = n_bits + self.bit_pos_
        while bytes_shift < bit_pos_when_done:
            if buf_pos >= self.buf_len_:
                break  # if hit end of buffer, this simulates zero padding after end, which is correct
            val |= self.buf_[buf_pos] << bytes_shift
            bytes_shift += 8
            buf_pos += 1
        return (val >> self.bit_pos_) & kBitMask[n_bits]

    def skip_bits(self, n_bits):
        next_in_bits = self.bit_pos_ + n_bits
        self.bit_pos_ = next_in_bits & 7
        self.pos_ += next_in_bits >> 3

    def read_bits(self, n_bits):
        val = self.peek_bits(n_bits)
        self.skip_bits(n_bits)
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
