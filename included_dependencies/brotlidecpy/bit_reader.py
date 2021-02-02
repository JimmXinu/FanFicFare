# Copyright 2021 Sidney Markowitz All Rights Reserved.
# Distributed under MIT license.
# See file LICENSE for detail or copy at https://opensource.org/licenses/MIT

BROTLI_READ_SIZE = 4096
BROTLI_IBUF_SIZE = (2 * BROTLI_READ_SIZE + 32)
BROTLI_IBUF_MASK = (2 * BROTLI_READ_SIZE - 1)
kBitMask = [
    0, 1, 3, 7, 15, 31, 63, 127, 255, 511, 1023, 2047, 4095, 8191, 16383, 32767,
    65535, 131071, 262143, 524287, 1048575, 2097151, 4194303, 8388607, 16777215
]


class BrotliBitReader:
    def __init__(self, input_stream):
        self.buf_ = bytearray([0] * BROTLI_IBUF_SIZE)
        self.input_ = input_stream    # input stream
        self.buf_ptr_ = 0      # next input will write here
        self.val_ = 0          # pre-fetched bits
        self.pos_ = 0          # byte position in stream
        self.bit_pos_ = 0      # current bit-reading position in val_
        self.bit_end_pos_ = 0  # bit-reading end position from LSB of val_
        self.eos_ = 0          # input stream is finished
        self.reset()

    READ_SIZE = BROTLI_READ_SIZE
    IBUF_MASK = BROTLI_IBUF_MASK

    def reset(self):
        self.buf_ptr_ = 0      # next input will write here
        self.val_ = 0          # pre-fetched bits
        self.pos_ = 0          # byte position in stream
        self.bit_pos_ = 0      # current bit-reading position in val_
        self.bit_end_pos_ = 0  # bit-reading end position from LSB of val_
        self.eos_ = 0          # input stream is finished

        self.read_more_input()
        for i in range(0, 4):
            self.val_ |= self.buf_[self.pos_] << (8 * i)
            self.pos_ += 1
        return self.bit_end_pos_ > 0

    def read_more_input(self):
        """ Fills up the input ringbuffer by calling the input callback.

       Does nothing if there are at least 32 bytes present after current position.

       Returns 0 if either:
        - the input callback returned an error, or
        - there is no more input and the position is past the end of the stream.

       After encountering the end of the input stream, 32 additional zero bytes are
       copied to the ringbuffer, therefore it is safe to call this function after
       every 32 bytes of input is read"""
        if self.bit_end_pos_ > 256:
            return
        elif self.eos_:
            if self.bit_pos_ > self.bit_end_pos_:
                raise Exception('Unexpected end of input %s %s' % (self.bit_pos_, self.bit_end_pos_))
        else:
            dst = self.buf_ptr_
            bytes_read = self.input_.readinto(memoryview(self.buf_)[dst:dst+BROTLI_READ_SIZE])
            if bytes_read < 0:
                raise Exception('Unexpected end of input')

            if bytes_read < BROTLI_READ_SIZE:
                self.eos_ = 1
                # Store 32 bytes of zero after the stream end
                for p in range(0, 32):
                    self.buf_[dst + bytes_read + p] = 0

            if dst == 0:
                # Copy the head of the ringbuffer to the slack region
                for p in range(0, 32):
                    self.buf_[(BROTLI_READ_SIZE << 1) + p] = self.buf_[p]
                self.buf_ptr_ = BROTLI_READ_SIZE
            else:
                self.buf_ptr_ = 0

            self.bit_end_pos_ += bytes_read << 3

    def fill_bit_window(self):
        """Guarantees that there are at least 24 bits in the buffer"""
        while self.bit_pos_ >= 8:
            self.val_ >>= 8
            self.val_ |= self.buf_[self.pos_ & BROTLI_IBUF_MASK] << 24
            self.pos_ += 1
            self.bit_pos_ -= 8
            self.bit_end_pos_ -= 8

    def read_bits(self, n_bits):
        if 32 - self.bit_pos_ < n_bits:
            self.fill_bit_window()
        val = ((self.val_ >> self.bit_pos_) & kBitMask[n_bits])
        self.bit_pos_ += n_bits
        return val
