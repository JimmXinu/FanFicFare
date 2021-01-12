#!/usr/bin/env python3
# Copyright (C) 2016 Kai Lüke kailueke@riseup.net
# This program comes with ABSOLUTELY NO WARRANTY and is free software, you are welcome to redistribute it
# under certain conditions, see https://www.gnu.org/licenses/gpl-3.0.en.html

# super slow pure python brotli decoder, please ignore
#
# ported from brotli-rs to a minimal python subset and now back to standard python (but unpolished) as a side project
#
# usage:
#
#     from brotlipython import brotlidec
#     in = open('test.br', 'rb').read()
#     outbuf = []
#     dec = brotlidec(in, outbuf)  # also returns bytes(outbuf) again
#
# or see `./brotlipython.py --help`

# @TODO:
# look into brotlidump.py
# whole file is unpythonic (no for loops, mostly integers, global variables, no classes, no good exception model)
# is needlessly complicated comes becfrom a malloc/free world (transformations)

import sys, array, argparse, os
from requests.utils import extract_zipped_paths

BROTLI_DICTIONARY = ''

# alloc_pM = lambda length: array.array('B', [0 for x in range(0, length)])
# alloc_pH = lambda length: array.array('L', [0 for x in range(0, length)])
alloc_L = lambda length: [0 for x in range(0, length)]
alloc_pM = alloc_pH = alloc_L

input_buf_pos = 0
input_buf = []
NONE = None
gcmpbuf = []
cmpbuf_pos = 0
output_buf = []

def out(a):
  global cmpbuf_pos, output_buf
  if gcmpbuf is not None:
    expected = gcmpbuf[cmpbuf_pos]
    cmpbuf_pos += 1
    if a != expected:
      import ipdb; ipdb.set_trace()
  output_buf.append(a)

def read_b():
    global input_buf, input_buf_pos
    if input_buf_pos == len(input_buf):
        return NONE
    a = input_buf[input_buf_pos]
    input_buf_pos += 1
    return a

def error():
  raise Exception("error() invoked")


# /bitreader/mod.rs
bit_pos = 0
current_byte = NONE
global_bit_pos = 0

read_exact_result = 0
def read_exact(): # read only one as it's anyway not used for more
  global read_exact_result
  read_exact_result = read_b()
  if read_exact_result is None:
    return 1 # eos error()
  return 0

def read_u8():  # return NONE for eof
  global bit_pos, current_byte, global_bit_pos
  res = read_exact()
  buf = read_exact_result
  if bit_pos == 0 and current_byte is not None and res == 1:  # i.e. res == EOS
    tmp_ = current_byte
    current_byte = NONE
    global_bit_pos += 8
    return tmp_
  elif current_byte is None and res == 0:  # i.e. res == Ok()
    global_bit_pos += 8
    return buf
  elif current_byte is not None and res == 0:
    tmp_ = current_byte
    current_byte = buf
    global_bit_pos += 8
    return (tmp_ >> bit_pos) | (buf << (8 - bit_pos))
  else:
    return NONE

read_u8_from_nibble_result = 0
def read_u8_from_nibble():  # returns 0 for OK, 1 for Error
  global bit_pos, current_byte, global_bit_pos, read_u8_from_nibble_result
  if bit_pos == 0 and current_byte is None:
    res = read_exact()
    buf = read_exact_result
    if res == 0:  # i.e. Ok()
      global_bit_pos += 4
      bit_pos = 4
      current_byte = buf
      read_u8_from_nibble_result = buf & 0x0f
      return 0
    else:
      return res
  elif (bit_pos == 1 or bit_pos == 2 or bit_pos == 3) and current_byte is not None:
    global_bit_pos += 4
    bit_pos += 4
    read_u8_from_nibble_result = (current_byte >> (bit_pos - 4)) & 0x0f
    return 0
  elif bit_pos == 4 and current_byte is not None:
    global_bit_pos += 4
    bit_pos = 0
    tmp_ = current_byte
    current_byte = NONE
    read_u8_from_nibble_result = (tmp_ >> 4) & 0x0f
    return 0
  elif (bit_pos == 5 or bit_pos == 6 or bit_pos == 7) and current_byte is not None:
    res = read_exact()
    buf = read_exact_result
    if res == 0:
      global_bit_pos += 4
      bit_pos_prev = bit_pos
      bit_pos = bit_pos - 4
      tmp_ = current_byte
      current_byte = buf
      read_u8_from_nibble_result = ((tmp_ >> (bit_pos_prev)) | (buf << (8 - bit_pos_prev))) & 0x0f
      return 0
    else:
      return res
  else:
    return 1 # unreachable


read_bit_result = 0
def read_bit():  # returns 0 for OK, 1 for Error
  global bit_pos, current_byte, global_bit_pos, read_bit_result
  if current_byte is not None:
      tmp_ = bit_pos
      tmp_2 = current_byte
      bit_pos = (tmp_ + 1) % 8
      global_bit_pos = global_bit_pos + 1
      if bit_pos == 0:
          current_byte = NONE
      read_bit_result = tmp_2 >> tmp_ & 1
      return 0
  else:
      if read_exact():
        return 1
      else:
        current_byte = read_exact_result
        bit_pos = 1
        global_bit_pos = 1
        read_bit_result = read_exact_result & 1
        return 0


read_u32_from_n_bits_result = 0
# returns 0 for OK, 1 for Error
def read_u32_from_n_bits(n):  # does also serve as read_u8_from_n_bits, read_u16_from_n_bits
  global bit_pos, current_byte, global_bit_pos, read_u32_from_n_bits_result
  read_u32_from_n_bits_result = 0
  i = 0
  while i < n:
    if read_bit():
      return 1  # error
    elif read_bit_result == 1:
      read_u32_from_n_bits_result = read_u32_from_n_bits_result | (1 << i)
    i += 1
  return 0

def read_u8_from_byte_tail():  # return NONE for eof
  if bit_pos == 0:
    return 0
  else:
    if read_u32_from_n_bits(8 - bit_pos):
      return NONE
    return read_u32_from_n_bits_result

read_u32_from_n_nibbles_result = 0
# returns 0 for OK, 1 for Error
def read_u32_from_n_nibbles(n):
  global bit_pos, current_byte, global_bit_pos, read_u32_from_n_nibbles_result
  read_u32_from_n_nibbles_result = 0
  i = 0
  while i < n:
    if read_u8_from_nibble() == 0:
      read_u32_from_n_nibbles_result = read_u32_from_n_nibbles_result | (read_u8_from_nibble_result  << (4 * i))
    else:
      return 1
    i += 1
  return 0

def read_fixed_length_string(length):
    my_string =  alloc_pM(length)
    i = 0
    while i < length:
        t = read_u8()
        if t == NONE:
            return NONE
        my_string[i] = t
        i += 1
    return my_string


# /huffman/tree/mod.rs

# tree as [buf, len, last_symbol]
#   buf: tree[0]
#   len: tree[1]
#   last_symbol: tree[2]

def tree_from_raw_data(buf, len_, last_symbol):
  return [buf, len_, last_symbol]

def tree_with_max_depth(max_depth):
  len_ = (1 << (max_depth + 1)) - 1
  # u16 entries
  arr = alloc_L(len_)
  i = 0  # init all values with NONE
  while i < len_:
    arr[i] = NONE
    i += 1
  return tree_from_raw_data(arr, 0, NONE)

def insert(tree, code, symbol):  # code[0,1,0,1,0,1]
  # code is 32 bit array
  tree[1] = tree[1] + 1
  tree[2] = symbol
  insert_at_index = 0
  i = 0
  while i < len(code):
    insert_at_index = (insert_at_index << 1) + code[i]
    i += 1
  insert_at_index = (1 << len(code)) - 1 + insert_at_index
  if insert_at_index > len(tree[0]) - 1:
    error() # panic!()
  tr = tree[0]
  tr[insert_at_index] = symbol


def lookup(tree):
  pseudo_code = 1
  len_ = len(tree[0])
  while True:
    if read_bit():
      return NONE
    pseudo_code = (pseudo_code << 1) + read_bit_result
    lookup_index = pseudo_code - 1
    if lookup_index > len_ - 1:
      return NONE # None but anyway None is always leading to DecompressorError
    tr = tree[0]
    tmp_ = tr[lookup_index] # buf[lookup_index]
    if tmp_ != NONE:
      return tmp_

def lookup_symbol(tree):
  if tree[1] == 0: # len == 0
    return NONE  # None empty table
  if tree[1] == 1: # len == 1
    return tree[2] # last_symbol
  return lookup(tree)

# /huffman/mod.rs

def bit_string_from_code_and_length(code, len_): # nr, nr
  bits = alloc_pM(len_)
  i = 0
  while i < len_:  # all bits get set, no initialisation with zero needed
    if (code >> i) & 1 == 1:
      bits[len_ - i - 1] = 1
    else:
      bits[len_ - i - 1] = 0
    i += 1
  return bits

def codes_from_lengths_and_symbols(lengths, symbols): # [], [] -> tree
  # treat lengths as u8 in pM, symbols as u32 in pH
  max_length = 0
  i = 0
  while i < len(lengths):
    j = lengths[i]
    if j > max_length:
      max_length = j
    i += 1
  bl_count = alloc_pH(max_length + 1)
  i = 0
  while i < max_length + 1:
    bl_count[i] = 0  # init
    i += 1
  i = 0
  while i < len(lengths):
    j = lengths[i]
    bl_count[j] = bl_count[j] + 1
    i += 1
  code = 0
  next_code = alloc_pH(max_length + 1)
  next_code[0] = 0  # init, rest is in loop
  bits = 1
  while bits < max_length + 1:
    code = (code + bl_count[bits - 1]) << 1
    next_code[bits] = code
    bits += 1
  codes = tree_with_max_depth(max_length)
  i = 0
  while i < len(lengths):
    len_ = lengths[i]
    if len_ > 0 or max_length == 0:
      insert(codes, bit_string_from_code_and_length(next_code[len_], len_), symbols[i])
      next_code[len_] = next_code[len_] + 1
    i += 1
  return codes

def codes_from_lengths(lengths): # [] -> Tree
  # lengths is in pM
  symbols = alloc_pH(len(lengths))
  i = 0
  while i < len(lengths):
    symbols[i] = i
    i += 1
  ret = codes_from_lengths_and_symbols(lengths, symbols)
  return ret

# /transformation/mod.rs

def uppercase_all(base_word):
  l = len(base_word)
  v = alloc_pM(l)
  i = 0
  while i < l:
    b = base_word[i]
    if (b >= 0 and b <= 96) or (b >= 123 and b <= 191):
      v[i] = b
      i += 1
    elif b >= 97 and b <= 122:
      v[i] = b ^ 32
      i += 1
    elif b >= 192 and b <= 223:
      v[i] = b
      i += 1
      if i < l:
        v[i] = base_word[i] ^ 32
      i += 1
    elif b >= 224 and b <= 255:
      v[i] = b
      i += 1
      if i < l:
        v[i] = base_word[i]
      i += 1
      if i < l:
        v[i] = base_word[i] ^ 5
      i += 1
    else:
      error() # unreachable
  return v

def uppercase_first(base_word):
  l = len(base_word)
  if l == 0:
    return alloc_pM(0)
  v = alloc_pM(l)
  i = 0
  b = base_word[0]
  if (b >= 1 and b <= 96) or (b >= 123 and b <= 191):
    v[0] = b
    i = 1
  elif b >= 97 and b <= 122:
    v[0] = b ^ 32
    i = 1
  elif b >= 192 and b <= 223:
    v[0] = b
    if 1 < l:
      v[1] = base_word[1] ^ 32
    i = 2
  elif b >= 224 and b <= 255:
    v[0] = b
    if 1 < l:
      v[1] = base_word[1]
    if 2 < l:
      v[2] = base_word[2] ^ 5
    i = 3
  else:
    error() # unreachable
  while i < l:
    v[i] = base_word[i]
    i += 1
  return v

def transformation(id_, base_word):
  #print("t:", id_, str(bytearray(base_word)))
  # rewrite like: t1 = [0x22] t2= omit_first(2) t3=[0x22,0x21] tc=3
  l = len(base_word)
  i = 0
  if id_ == 0:
    return base_word
  elif id_ == 1 or id_ == 19 or id_ == 20 or id_ == 22 or id_ == 24 or id_ == 36 or id_ == 51 or id_ == 57 or id_ == 76:  # 1 hinten an
    v = alloc_pM(l+1)
    while i < l:
      v[i] = base_word[i]
      i += 1
    if id_ == 1:
      v[i] = 0x20
    elif id_ == 19:
      v[i] = 0x22
    elif id_ == 20:
      v[i] = 0x2e
    elif id_ == 22:
      v[i] = 0x0a
    elif id_ == 24:
      v[i] = 0x5d
    elif id_ == 36:
      v[i] = 0x27
    elif id_ == 51:
      v[i] = 0x3a
    elif id_ == 57:
      v[i] = 0x28
    elif id_ == 76:
      v[i] = 0x2c
  elif id_ == 2 or id_ == 67 or id_ == 71 or id_ == 77 or id_ == 89 or id_ == 103:  # 1 vorne 1 hinten an
    v = alloc_pM(l+2)
    if id_ == 2 or id_ == 71 or id_ == 89 or id_ == 103:
      v[i] = 0x20
    elif id_ == 67 or id_ == 77:
      v[i] = 0x2e
    i += 1
    while i <= l:
      v[i] = base_word[i-1]
      i += 1
    if id_ == 2 or id_ == 77:
      v[i] = 0x20
    elif id_ == 67 or id_ == 89:
      v[i] = 0x28
    elif id_ == 71:
      v[i] = 0x2e
    elif id_ == 103:
      v[i] = 0x2c
  elif id_ == 3 or id_ == 11 or id_ == 26 or id_ == 34 or id_ == 39 or id_ == 40 or id_ == 54 or id_ == 55:
    if id_ == 3:
      j = 1
    elif id_ == 11:
      j = 2
    elif id_ == 26:
      j = 3
    elif id_ == 34:
      j = 4
    elif id_ == 39:
      j = 5
    elif id_ == 40:
      j = 6
    elif id_ == 54:
      j = 9
    elif id_ == 55:
      j = 7
    if l-1 < j:
      j = l-1
    v = alloc_pM(l-j)
    while i < l-j:
      v[i] = base_word[i+j]
      i += 1
  elif id_ == 4 or id_ == 66 or id_ == 74 or id_ == 78 or id_ == 79 or id_ == 99:  # upper first 1 hinten an
    u = uppercase_first(base_word)
    j = len(u)
    v = alloc_pM(j+1)
    while i < j:
      v[i] = u[i]
      i += 1
    if id_ == 4:
      v[i] = 0x20
    elif id_ == 66:
      v[i] = 0x22
    elif id_ == 74:
      v[i] = 0x27
    elif id_ == 78:
      v[i] = 0x28
    elif id_ == 79:
      v[i] = 0x2e
    elif id_ == 99:
      v[i] = 0x2c
  elif id_ == 5 or id_ == 10 or id_ == 25 or id_ == 80 or id_ == 93:  # 5 hinten an
    v = alloc_pM(l+5)
    while i < l:
      v[i] = base_word[i]
      i += 1
    if id_ == 93:
      v[i] = 0x6c
    else:
      v[i] = 0x20
    i += 1
    if id_ == 5:
      v[i] = 0x74
    elif id_ == 10:
      v[i] = 0x61
    elif id_ == 25:
      v[i] = 0x66
    elif id_ == 80:
      v[i] = 0x6e
    elif id_ == 93:
      v[i] = 0x65
    i += 1
    if id_ == 5:
      v[i] = 0x68
    elif id_ == 10:
      v[i] = 0x6e
    elif id_ == 25 or id_ == 80:
      v[i] = 0x6f
    elif id_ == 93:
      v[i] = 0x73
    i += 1
    if id_ == 5:
      v[i] = 0x65
    elif id_ == 10:
      v[i] = 0x64
    elif id_ == 25:
      v[i] = 0x72
    elif id_ == 80:
      v[i] = 0x74
    elif id_ == 93:
      v[i] = 0x73
    i += 1
    v[i] = 0x20
  elif id_ == 6 or id_ == 32:  # 1 vorne an
    v = alloc_pM(l+1)
    if id_ == 6:
      v[i] = 0x20
    elif id_ == 32:
      v[i] = 0x2e
    i += 1
    while i <= l:
      v[i] = base_word[i-1]
      i += 1
  elif id_ == 7 or id_ == 13 or id_ == 18:  # 2 vorne an 1 hinten an
    v = alloc_pM(l+3)
    if id_ == 7:
      v[i] = 0x73
    elif id_ == 13:
      v[i] = 0x2c
    elif id_ == 18:
      v[i] = 0x65
    i += 1
    v[i] = 0x20
    i += 1
    l += 1
    while i <= l:
      v[i] = base_word[i-2]
      i += 1
    v[i] = 0x20
  elif id_ == 8 or id_ == 16 or id_ == 17 or id_ == 38 or id_ == 45 or id_ == 46 or id_ == 47 or id_ == 60 or id_ == 90 or id_ == 92 or id_ == 95 or id_ == 100 or id_ == 106:  # 4 hinten an
    v = alloc_pM(l+4)
    while i < l:
      v[i] = base_word[i]
      i += 1
    if id_ == 90:
      v[i] = 0x66
    elif id_ == 92 or id_ == 100:
      v[i] = 0x69
    elif id_ == 95:
      v[i] = 0x65
    elif id_ == 106:
      v[i] = 0x6f
    else:
      v[i] = 0x20
    i += 1
    if id_ == 8:
      v[i] = 0x6f
    elif id_ == 16:
      v[i] = 0x69
    elif id_ == 17:
      v[i] = 0x74
    elif id_ == 38:
      v[i] = 0x62
    elif id_ == 45:
      v[i] = 0x6f
    elif id_ == 46 or id_ == 60:
      v[i] = 0x61
    elif id_ == 47:
      v[i] = 0x69
    elif id_ == 90 or id_ == 106:
      v[i] = 0x75
    elif id_ == 92:
      v[i] = 0x76
    elif id_ == 95:
      v[i] = 0x73
    elif id_ == 100:
      v[i] = 0x7a
    i += 1
    if id_ == 8:
      v[i] = 0x66
    elif id_ == 16:
      v[i] = 0x6e
    elif id_ == 17:
      v[i] = 0x6f
    elif id_ == 38:
      v[i] = 0x79
    elif id_ == 45:
      v[i] = 0x6e
    elif id_ == 46 or id_ == 47 or id_ == 106:
      v[i] = 0x73
    elif id_ == 60 or id_ == 95:
      v[i] = 0x74
    elif id_ == 90:
      v[i] = 0x6c
    elif id_ == 92 or id_ == 100:
      v[i] = 0x65
    i += 1
    v[i] = 0x20
  elif id_ == 9:
    v = uppercase_first(base_word)
  elif id_ == 12 or id_ == 23 or id_ == 27 or id_ == 42 or id_ == 48 or id_ == 56 or id_ == 59 or id_ == 63 or id_ == 64:
    if id_ == 12:
      j = 1
    elif id_ == 23:
      j = 3
    elif id_ == 27:
      j = 2
    elif id_ == 42:
      j = 4
    elif id_ == 48:
      j = 7
    elif id_ == 56:
      j = 6
    elif id_ == 59:
      j = 8
    elif id_ == 63:
      j = 5
    elif id_ == 64:
      j = 9
    if l > j:
      j = l
    if id_ == 12:
      j -= 1
    elif id_ == 23:
      j -= 3
    elif id_ == 27:
      j -= 2
    elif id_ == 42:
      j -= 4
    elif id_ == 48:
      j -= 7
    elif id_ == 56:
      j -= 6
    elif id_ == 59:
      j -= 8
    elif id_ == 63:
      j -= 5
    elif id_ == 64:
      j -= 9
    v = alloc_pM(j)
    while i < j:
      v[i] = base_word[i]
      i += 1
  elif id_ == 14 or id_ == 21 or id_ == 31 or id_ == 50 or id_ == 70 or id_ == 86:  # 2 hinten an
    v = alloc_pM(l+2)
    while i < l:
      v[i] = base_word[i]
      i += 1
    if id_ == 14:
      v[i] = 0x2c
    elif id_ == 21:
      v[i] = 0x22
    elif id_ == 31:
      v[i] = 0x2e
    elif id_ == 50:
      v[i] = 0x0a
    elif id_ == 70 or id_ == 86:
      v[i] = 0x3d
    i += 1
    if id_ == 14 or id_ == 31:
      v[i] = 0x20
    elif id_ == 21:
      v[i] = 0x3e
    elif id_ == 50:
      v[i] = 0x09
    elif id_ == 70:
      v[i] = 0x22
    elif id_ == 86:
      v[i] = 0x27
  elif id_ == 15 or id_ == 96 or id_ == 109:  # upper first 1 vorne an 1 hinten an
    u = uppercase_first(base_word)
    j = len(u)
    v = alloc_pM(j+2)
    v[0] = 0x20
    while i < j:
      v[i+1] = u[i]
      i += 1
    i += 1
    if id_ == 96:
      v[i] = 0x2e
    elif id_ == 109:
      v[i] = 0x2c
    else:
      v[i] = 0x20
  elif id_ == 28 or id_ == 53 or id_ == 61 or id_ == 82 or id_ == 84:  # 3 hinten an
    v = alloc_pM(l+3)
    while i < l:
      v[i] = base_word[i]
      i += 1
    if id_ == 28:
      v[i] = 0x20
    elif id_ == 53 or id_ == 82:
      v[i] = 0x65
    elif id_ == 61:
      v[i] = 0x6c
    elif id_ == 84:
      v[i] = 0x61
    i += 1
    if id_ == 28:
      v[i] = 0x61
    elif id_ == 53:
      v[i] = 0x64
    elif id_ == 61:
      v[i] = 0x79
    elif id_ == 82:
      v[i] = 0x72
    elif id_ == 84:
      v[i] = 0x6c
    i += 1
    v[i] = 0x20
  elif id_ == 29 or id_ == 35 or id_ == 37 or id_ == 43:  # 6 hinten an
    v = alloc_pM(l+6)
    while i < l:
      v[i] = base_word[i]
      i += 1
    if id_ == 43:
      v[i] = 0x2e
    else:
      v[i] = 0x20
    i += 1
    if id_ == 29:
      v[i] = 0x74
    elif id_ == 35:
      v[i] = 0x77
    elif id_ == 37:
      v[i] = 0x66
    elif id_ == 43:
      v[i] = 0x20
    i += 1
    if id_ == 29:
      v[i] = 0x68
    elif id_ == 35:
      v[i] = 0x69
    elif id_ == 37:
      v[i] = 0x72
    elif id_ == 43:
      v[i] = 0x54
    i += 1
    if id_ == 29:
      v[i] = 0x61
    elif id_ == 35:
      v[i] = 0x74
    elif id_ == 37:
      v[i] = 0x6f
    elif id_ == 43:
      v[i] = 0x68
    i += 1
    if id_ == 29:
      v[i] = 0x74
    elif id_ == 35:
      v[i] = 0x68
    elif id_ == 37:
      v[i] = 0x6d
    elif id_ == 43:
      v[i] = 0x65
    i += 1
    v[i] = 0x20
  elif id_ == 30:  # upper first 1 vorne an
    u = uppercase_first(base_word)
    j = len(u)
    v = alloc_pM(j+1)
    v[0] = 0x20
    while i < j:
      v[i+1] = u[i]
      i += 1
  elif id_ == 33 or id_ == 52 or id_ == 81 or id_ == 98:  # 1 vorne 2 hinten an
    v = alloc_pM(l+3)
    v[i] = 0x20
    i += 1
    while i <= l:
      v[i] = base_word[i-1]
      i += 1
    if id_ == 33:
      v[i] = 0x2c
    elif id_ == 52:
      v[i] = 0x2e
    elif id_ == 81 or id_ == 98:
      v[i] = 0x3d
    i += 1
    if id_ == 81:
      v[i] = 0x22
    elif id_ == 98:
      v[i] = 0x27
    else:
      v[i] = 0x20
  elif id_ == 41 or id_ == 72:  # 5 vorne an
    v = alloc_pM(l+5)
    if id_ == 41:
      v[i] = 0x20
    elif id_ == 72:
      v[i] = 0x2e
    i += 1
    if id_ == 41:
      v[i] = 0x74
    elif id_ == 72:
      v[i] = 0x63
    i += 1
    if id_ == 41:
      v[i] = 0x68
    elif id_ == 72:
      v[i] = 0x6f
    i += 1
    if id_ == 41:
      v[i] = 0x65
    elif id_ == 72:
      v[i] = 0x6d
    i += 1
    if id_ == 41:
      v[i] = 0x20
    elif id_ == 72:
      v[i] = 0x2f
    i += 1
    while i-5 < l:
      v[i] = base_word[i-5]
      i += 1
  elif id_ == 44:
    v = uppercase_all(base_word)
  elif id_ == 49:
    j = 1
    if l > j:
      j = l
    j -= 1
    v = alloc_pM(j+4)
    while i < j:
      v[i] = base_word[i]
      i += 1
    v[i] = 0x69
    i += 1
    v[i] = 0x6e
    i += 1
    v[i] = 0x67
    i += 1
    v[i] = 0x20
  elif id_ == 58 or id_ == 69 or id_ == 88 or id_ == 104 or id_ == 108:  # upper first 2 hinten an
    u = uppercase_first(base_word)
    j = len(u)
    v = alloc_pM(j+2)
    while i < j:
      v[i] = u[i]
      i += 1
    if id_ == 58:
      v[i] = 0x2c
    elif id_ == 69:
      v[i] = 0x22
    elif id_ == 88:
      v[i] = 0x2e
    elif id_ == 104 or id_ == 108:
      v[i] = 0x3d
    i += 1
    if id_ == 58 or id_ == 88:
      v[i] = 0x20
    elif id_ == 69:
      v[i] = 0x3e
    elif id_ == 104:
      v[i] = 0x22
    elif id_ == 108:
      v[i] = 0x27
  elif id_ == 62:  # 5 vorne 4 hinten an
    v = alloc_pM(l+9)
    v[i] = 0x20
    i += 1
    v[i] = 0x74
    i += 1
    v[i] = 0x68
    i += 1
    v[i] = 0x65
    i += 1
    v[i] = 0x20
    i += 1
    while i-5 < l:
      v[i] = base_word[i-5]
      i += 1
    v[i] = 0x20
    i += 1
    v[i] = 0x6f
    i += 1
    v[i] = 0x66
    i += 1
    v[i] = 0x20
  elif id_ == 65 or id_ == 91 or id_ == 118 or id_ == 120:  # upper first 1 vorne 2 hinten an
    u = uppercase_first(base_word)
    j = len(u)
    v = alloc_pM(j+3)
    v[0] = 0x20
    while i < j:
      v[i+1] = u[i]
      i += 1
    i += 1
    if id_ == 65:
      v[i] = 0x2c
    elif id_ == 91:
      v[i] = 0x2e
    else:
      v[i] = 0x3d
    i += 1
    if id_ == 118:
      v[i] = 0x22
    elif id_ == 120:
      v[i] = 0x27
    else:
      v[i] = 0x20
  elif id_ == 68 or id_ == 87 or id_ == 94 or id_ == 101 or id_ == 112 or id_ == 113:  # upper all 1 hinten
    u = uppercase_all(base_word)
    j = len(u)
    v = alloc_pM(j+1)
    while i < j:
      v[i] = u[i]
      i += 1
    if id_ == 87:
      v[i] = 0x22
    elif id_ == 94:
      v[i] = 0x27
    elif id_ == 101:
      v[i] = 0x2e
    elif id_ == 112:
      v[i] = 0x2c
    elif id_ == 113:
      v[i] = 0x28
    else:
      v[i] = 0x20
  elif id_ == 73:  # 5 vorne 8 hinten an
    v = alloc_pM(l+13)
    v[i] = 0x20
    i += 1
    v[i] = 0x74
    i += 1
    v[i] = 0x68
    i += 1
    v[i] = 0x65
    i += 1
    v[i] = 0x20
    i += 1
    while i-5 < l:
      v[i] = base_word[i-5]
      i += 1
    v[i] = 0x20
    i += 1
    v[i] = 0x6f
    i += 1
    v[i] = 0x66
    i += 1
    v[i] = 0x20
    i += 1
    v[i] = 0x74
    i += 1
    v[i] = 0x68
    i += 1
    v[i] = 0x65
    i += 1
    v[i] = 0x20
  elif id_ == 75:  # 7 hinten an
    v = alloc_pM(l+7)
    while i < l:
      v[i] = base_word[i]
      i += 1
    v[i] = 0x2e
    i += 1
    v[i] = 0x20
    i += 1
    v[i] = 0x54
    i += 1
    v[i] = 0x68
    i += 1
    v[i] = 0x69
    i += 1
    v[i] = 0x73
    i += 1
    v[i] = 0x20
  elif id_ == 83 or id_ == 115:  # upper all 1 vorne 1 hinten
    u = uppercase_all(base_word)
    j = len(u)
    v = alloc_pM(j+2)
    v[0] = 0x20
    while i < j:
      v[i+1] = u[i]
      i += 1
    i += 1
    if id_ == 83:
      v[i] = 0x20
    elif id_ == 115:
      v[i] = 0x2e
  elif id_ == 85:  # upper all 1 vorne
    u = uppercase_all(base_word)
    j = len(u)
    v = alloc_pM(j+1)
    v[0] = 0x20
    while i < j:
      v[i+1] = u[i]
      i += 1
  elif id_ == 97 or id_ == 105 or id_ == 107 or id_ == 114 or id_ == 116:  # upper all 2 hinten
    u = uppercase_all(base_word)
    j = len(u)
    v = alloc_pM(j+2)
    while i < j:
      v[i] = u[i]
      i += 1
    if id_ == 97:
      v[i] = 0x22
    elif id_ == 105 or id_ == 116:
      v[i] = 0x3d
    elif id_ == 107:
      v[i] = 0x2c
    elif id_ == 114:
      v[i] = 0x2e
    i += 1
    if id_ == 97:
      v[i] = 0x3e
    elif id_ == 105:
      v[i] = 0x22
    elif id_ == 116:
      v[i] = 0x27
    elif id_ == 107 or id_ == 114:
      v[i] = 0x20
  elif id_ == 102: # 2 vorne
    v = alloc_pM(l+2)
    v[i] = 0xc2
    i += 1
    v[i] = 0xa0
    i += 1
    l += 1
    while i <= l:
      v[i] = base_word[i-2]
      i += 1
  elif id_ == 110 or id_ == 111 or id_ == 117 or id_ == 119:  # upper all 1 vorne 2 hinten
    u = uppercase_all(base_word)
    j = len(u)
    v = alloc_pM(j+3)
    v[0] = 0x20
    while i < j:
      v[i+1] = u[i]
      i += 1
    i += 1
    if id_ == 110 or id_ == 119:
      v[i] = 0x3d
    elif id_ == 111:
      v[i] = 0x2c
    elif id_ == 117:
      v[i] = 0x2e
    i += 1
    if id_ == 110:
      v[i] = 0x22
    elif id_ == 110:
      v[i] = 0x27
    else:
      v[i] = 0x20
  else:
    return NONE # unreachable
  return v

# /dictionary/mod.rs
BROTLI_DICTIONARY_OFFSETS_BY_LENGTH = [0,      0,      0,      0,      0,   4096,   9216,  21504,  35840,  44032, 53248,  63488 , 74752,  87040,  93696, 100864, 104704, 106752, 108928, 113536, 115968, 118528, 119872, 121280, 122016]
BROTLI_DICTIONARY_SIZE_BITS_BY_LENGTH = [0,  0,  0,  0, 10, 10, 11, 11, 10, 10, 10, 10, 10,  9,  9,  8,  7,  7,  8,  7, 7,  6,  6,  5,  5]

# /lookuptable/mod.rs

LUT_0 = [
	 0,  0,  0,  0,  0,  0,  0,  0,  0,  4,  4,  0,  0,  4,  0,  0,
	 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
	 8, 12, 16, 12, 12, 20, 12, 16, 24, 28, 12, 12, 32, 12, 36, 12,
	44, 44, 44, 44, 44, 44, 44, 44, 44, 44, 32, 32, 24, 40, 28, 12,
	12, 48, 52, 52, 52, 48, 52, 52, 52, 48, 52, 52, 52, 52, 52, 48,
	52, 52, 52, 52, 52, 48, 52, 52, 52, 52, 52, 24, 12, 28, 12, 12,
	12, 56, 60, 60, 60, 56, 60, 60, 60, 56, 60, 60, 60, 60, 60, 56,
	60, 60, 60, 60, 60, 56, 60, 60, 60, 60, 60, 24, 12, 28, 12,  0,
	 0,  1,  0,  1,  0,  1,  0,  1,  0,  1,  0,  1,  0,  1,  0,  1,
	 0,  1,  0,  1,  0,  1,  0,  1,  0,  1,  0,  1,  0,  1,  0,  1,
	 0,  1,  0,  1,  0,  1,  0,  1,  0,  1,  0,  1,  0,  1,  0,  1,
	 0,  1,  0,  1,  0,  1,  0,  1,  0,  1,  0,  1,  0,  1,  0,  1,
	 2,  3,  2,  3,  2,  3,  2,  3,  2,  3,  2,  3,  2,  3,  2,  3,
	 2,  3,  2,  3,  2,  3,  2,  3,  2,  3,  2,  3,  2,  3,  2,  3,
	 2,  3,  2,  3,  2,  3,  2,  3,  2,  3,  2,  3,  2,  3,  2,  3,
	 2,  3,  2,  3,  2,  3,  2,  3,  2,  3,  2,  3,  2,  3,  2,  3
]

LUT_1 = [
	0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
	0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
	0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
	2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1,
	1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
	2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1,
	1, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
	3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 1, 1, 1, 1, 0,
	0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
	0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
	0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
	0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
	0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
	0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
	2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
	2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2
]

LUT_2 = [
	0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
	2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
	2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
	2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
	3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
	3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
	3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
	3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
	4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
	4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
	4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
	4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
	5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
	5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
	5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
	6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 7
]

table = alloc_pH(704*4)
insert_and_copy_length = 0
while insert_and_copy_length < 704:
  if insert_and_copy_length >= 0 and insert_and_copy_length <= 63:
    insert_length_code = 0
    copy_length_code = 0
  elif insert_and_copy_length >= 64 and insert_and_copy_length <= 127:
    insert_length_code = 0
    copy_length_code = 8
  elif insert_and_copy_length >= 128 and insert_and_copy_length <= 191:
    insert_length_code = 0
    copy_length_code = 0
  elif insert_and_copy_length >= 192 and insert_and_copy_length <= 255:
    insert_length_code = 0
    copy_length_code = 8
  elif insert_and_copy_length >= 256 and insert_and_copy_length <= 319:
    insert_length_code = 8
    copy_length_code = 0
  elif insert_and_copy_length >= 320 and insert_and_copy_length <= 383:
    insert_length_code = 8
    copy_length_code = 8
  elif insert_and_copy_length >= 384 and insert_and_copy_length <= 447:
    insert_length_code = 0
    copy_length_code = 16
  elif insert_and_copy_length >= 448 and insert_and_copy_length <= 511:
    insert_length_code = 16
    copy_length_code = 0
  elif insert_and_copy_length >= 512 and insert_and_copy_length <= 575:
    insert_length_code = 8
    copy_length_code = 16
  elif insert_and_copy_length >= 576 and insert_and_copy_length <= 639:
    insert_length_code = 16
    copy_length_code = 8
  elif insert_and_copy_length >= 640 and insert_and_copy_length <= 703:
    insert_length_code = 16
    copy_length_code = 16
  else:
    error() # print('unreachable')
  insert_length_code += 0x07 & (insert_and_copy_length >> 3)
  copy_length_code += 0x07 & insert_and_copy_length
  if insert_length_code >= 0 and insert_length_code <= 5:
    insert_length = insert_length_code
    extra_bits_insert = 0
  elif insert_length_code == 6 or insert_length_code == 7:
    insert_length = 6 + 2 * (insert_length_code - 6)
    extra_bits_insert = 1
  elif insert_length_code == 8 or insert_length_code == 9:
    insert_length = 10 + 4 * (insert_length_code - 8)
    extra_bits_insert = 2
  elif insert_length_code == 10 or insert_length_code == 11:
    insert_length = 18 + 8 * (insert_length_code - 10)
    extra_bits_insert = 3
  elif insert_length_code == 12 or insert_length_code == 13:
    insert_length = 34 + 16 * (insert_length_code - 12)
    extra_bits_insert = 4
  elif insert_length_code == 14 or insert_length_code == 15:
    insert_length = 66 + 32 * (insert_length_code - 14)
    extra_bits_insert = 5
  elif insert_length_code == 16:
    insert_length = 130
    extra_bits_insert = 6
  elif insert_length_code == 17:
    insert_length = 194
    extra_bits_insert = 7
  elif insert_length_code == 18:
    insert_length = 322
    extra_bits_insert = 8
  elif insert_length_code == 19:
    insert_length = 578
    extra_bits_insert = 9
  elif insert_length_code == 20:
    insert_length = 1090
    extra_bits_insert = 10
  elif insert_length_code == 21:
    insert_length = 2114
    extra_bits_insert = 12
  elif insert_length_code == 22:
    insert_length = 6210
    extra_bits_insert = 14
  elif insert_length_code == 23:
    insert_length = 22594
    extra_bits_insert = 24
  else:
    error() # print('unreachable')
  if copy_length_code >= 0 and copy_length_code <= 7:
    copy_length = copy_length_code + 2
    extra_bits_copy = 0
  elif copy_length_code == 8 or copy_length_code == 9:
    copy_length = 10 + 2 * (copy_length_code - 8)
    extra_bits_copy = 1
  elif copy_length_code == 10 or copy_length_code == 11:
    copy_length = 14 + 4 * (copy_length_code - 10)
    extra_bits_copy = 2
  elif copy_length_code == 12 or copy_length_code == 13:
    copy_length = 22 + 8 * (copy_length_code - 12)
    extra_bits_copy = 3
  elif copy_length_code == 14 or copy_length_code == 15:
    copy_length = 38 + 16 * (copy_length_code - 14)
    extra_bits_copy = 4
  elif copy_length_code == 16 or copy_length_code == 17:
    copy_length = 70 + 32 * (copy_length_code - 16)
    extra_bits_copy = 5
  elif copy_length_code == 18:
    copy_length = 134
    extra_bits_copy = 6
  elif copy_length_code == 19:
    copy_length = 198
    extra_bits_copy = 7
  elif copy_length_code == 20:
    copy_length = 326
    extra_bits_copy = 8
  elif copy_length_code == 21:
    copy_length = 582
    extra_bits_copy = 9
  elif copy_length_code == 22:
    copy_length = 1094
    extra_bits_copy = 10
  elif copy_length_code == 23:
    copy_length = 2118
    extra_bits_copy = 24
  else:
    error() # print('unreachable')
  table[insert_and_copy_length*4] = insert_length
  table[insert_and_copy_length*4 + 1] = extra_bits_insert
  table[insert_and_copy_length*4 + 2] = copy_length
  table[insert_and_copy_length*4 + 3] = extra_bits_copy
  insert_and_copy_length += 1

INSERT_LENGTHS_AND_COPY_LENGTHS = table

# /lib.rs

PrefixCodeKind_Simple = 1
PrefixCodeKind_Complex = 2
PrefixCodeKind_Complex_data = NONE

StreamBegin = 1
HeaderBegin = 2
WBits = 3
WBits_data = 0
HeaderEnd = 4
HeaderMetaBlockBegin = 5
IsLast = 6
IsLast_data = 0
IsLastEmpty = 7
IsLastEmpty_data = 0
MNibbles = 8
MNibbles_data = 0
MSkipBytes = 9
MSkipBytes_data = 0
MSkipLen = 10
MSkipLen_data = 0
MLen = 11
MLen_data = 0
IsUncompressed = 12
IsUncompressed_data = 0
MLenLiterals = 13
MLenLiterals_data = 0 # []
NBltypesL = 14
NBltypesL_data = 0
PrefixCodeBlockTypesLiterals = 15
PrefixCodeBlockTypesLiterals_data = 0  # (HuffmanCodes)
PrefixCodeBlockCountsLiterals = 16
PrefixCodeBlockCountsLiterals_data = 0 # (HuffmanCodes)
FirstBlockCountLiterals = 17
FirstBlockCountLiterals_data = 0 # (BLen)
NBltypesI = 18
NBltypesI_data = 0
PrefixCodeBlockTypesInsertAndCopyLengths = 19
PrefixCodeBlockTypesInsertAndCopyLengths_data = 0 # (HuffmanCodes)
PrefixCodeBlockCountsInsertAndCopyLengths = 20
PrefixCodeBlockCountsInsertAndCopyLengths_data = 0 # (HuffmanCodes)
FirstBlockCountInsertAndCopyLengths = 21
FirstBlockCountInsertAndCopyLengths_data = 0
NBltypesD = 22
NBltypesD_data = 0 # (NBltypes)
PrefixCodeBlockTypesDistances = 23
PrefixCodeBlockTypesDistances_data = 0 # (HuffmanCodes)
PrefixCodeBlockCountsDistances = 24
PrefixCodeBlockCountsDistances_data = 0 # (HuffmanCodes)
FirstBlockCountDistances = 25
FirstBlockCountDistances_data = 0 #(BLen)
NPostfix = 26
NPostfix_data = 0
NDirect = 27
NDirect_data = 0
ContextModesLiterals = 28
ContextModesLiterals_data = 0 # (ContextModes)
NTreesL = 29
NTreesL_data = 0 # (NTrees)
NTreesD = 30
NTreesD_data = 0 #(NTrees)
ContextMapDistances = 31
ContextMapDistances_data = 0 # (ContextMap)
ContextMapLiterals = 32
ContextMapLiterals_data = 0 # (ContextMap)
PrefixCodesLiterals = 33
PrefixCodesLiterals_data = 0 # (Vec<HuffmanCodes>)
PrefixCodesInsertAndCopyLengths = 34
PrefixCodesInsertAndCopyLengths_data = 0 # (Vec<HuffmanCodes>)
PrefixCodesDistances = 35
PrefixCodesDistances_data = 0 # (Vec<HuffmanCodes>)
DataMetaBlockBegin = 36
InsertAndCopyLength = 37
InsertAndCopyLength_data = 0
InsertLengthAndCopyLength = 38
InsertLengthAndCopyLength_data_co_len = NONE
InsertLengthAndCopyLength_data_in_len = NONE
InsertLiterals = 39
InsertLiterals_data = 0 #(Literals)
DistanceCode = 40
DistanceCode_data = 0 #(DistanceCode)
Distance = 41
Distance_data = 0 # (Distance)
CopyLiterals = 42
CopyLiterals_data = 0 # (Literals)
DataMetaBlockEnd = 43
MetaBlockEnd = 44
StreamEnd = 45

t_array = alloc_pH(255)
i = 0
while i < 255:
  t_array[i] = NONE
  i += 1
t_array[1] = 16
t_array[24] = 21
t_array[25] = 19
t_array[26] = 23
t_array[27] = 18
t_array[28] = 22
t_array[29] = 20
t_array[30] = 24
t_array[191] = 17
t_array[192] = 12
t_array[193] = 10
t_array[194] = 14
t_array[196] = 13
t_array[197] = 11
t_array[198] = 15
header_wbits_codes = tree_from_raw_data(t_array, 15, 24)

t_array = alloc_pH(31)
i = 0
while i < 31:
  t_array[i] = NONE
  i += 1
t_array[3] = 0
t_array[4] = 3
t_array[5] = 4
t_array[13] = 2
t_array[29] = 1
t_array[30] = 5
header_bit_lengths_code = tree_from_raw_data(t_array, 6, 5)

t_array = alloc_pH(31)
i = 0
while i < 31:
  t_array[i] = NONE
  i += 1
t_array[1] = 1
t_array[23] = 2
t_array[24] = 17
t_array[25] = 5
t_array[26] = 65
t_array[27] = 3
t_array[28] = 33
t_array[29] = 9
t_array[30] = 129
header_bltype_codes = tree_from_raw_data(t_array, 9, 129)

header_wbits = NONE
header_window_size = NONE
output_window = NONE # RingBuffer []
output_window_pointer = 0
count_output = 0 # Decompressor.count_output
distance_buf = alloc_pH(4)
distance_buf[0] = 16  # reversed!
distance_buf[1] = 15
distance_buf[2] = 11
distance_buf[3] = 4
distance_buf_pointer = 3
literal_buf = alloc_pM(2)
literal_buf[0] = 0
literal_buf[1] = 0
literal_buf_pointer = 0
meta_block_header_is_last = NONE
meta_block_header_is_last_empty = NONE
meta_block_header_m_nibbles = NONE
meta_block_header_m_skip_bytes = NONE
meta_block_header_m_skip_len = NONE
meta_block_header_m_len = NONE
meta_block_header_is_uncompressed = NONE
meta_block_header_n_bltypes_l = NONE
meta_block_header_n_bltypes_i = NONE
meta_block_header_n_bltypes_d = NONE
meta_block_header_n_postfix = NONE
meta_block_header_n_direct = NONE
meta_block_header_n_trees_l = NONE
meta_block_header_n_trees_d = NONE
meta_block_header_c_map_l = NONE
meta_block_header_c_map_d = NONE
meta_block_prefix_tree_block_types_literals = NONE
meta_block_prefix_tree_block_counts_literals = NONE
meta_block_prefix_trees_literals = NONE
meta_block_count_output = 0
meta_block_btype_l = 0
meta_block_btype_l_prev = 1
meta_block_blen_l = NONE
meta_block_blen_i = NONE
meta_block_blen_d = NONE
meta_block_btype_i = 0
meta_block_btype_i_prev = 1
meta_block_btype_d = 0
meta_block_btype_d_prev = 1
meta_block_prefix_tree_block_types_insert_and_copy_lengths = NONE
meta_block_prefix_tree_block_counts_insert_and_copy_lengths = NONE
meta_block_prefix_tree_block_types_distances = NONE
meta_block_prefix_tree_block_counts_distances = NONE
meta_block_prefix_trees_insert_and_copy_lengths = NONE
meta_block_prefix_trees_distances = NONE
meta_block_context_modes_literals = NONE
meta_block_insert_and_copy_length = NONE
meta_block_copy_length = NONE
meta_block_insert_length = NONE
meta_block_distance = NONE
meta_block_distance_code = NONE


state = StreamBegin

def parse_wbits():
  return lookup_symbol(header_wbits_codes)

def parse_is_last():
  global IsLast_data
  if read_bit():
    error() # eof
  else:
    IsLast_data = read_bit_result
    return IsLast

def parse_is_last_empty():
  global IsLastEmpty_data
  if read_bit():
    error() # eof
  else:
    IsLastEmpty_data = read_bit_result
    return IsLastEmpty

def parse_m_nibbles():
  global MNibbles_data
  if read_u32_from_n_bits(2):
    error() # eof
  if read_u32_from_n_bits_result == 3:
    MNibbles_data = 0
    return MNibbles
  else:
    MNibbles_data = read_u32_from_n_bits_result + 4
    return MNibbles

def parse_m_skip_bytes():
  global MSkipBytes_data
  if read_u32_from_n_bits(2):
    error() # eof
  MSkipBytes_data = read_u32_from_n_bits_result
  return MSkipBytes

def parse_m_skip_len():
    global MSkipLen_data
    bytes_ = read_fixed_length_string(meta_block_header_m_skip_bytes)
    if bytes_ == NONE:
      error() # eof
    if meta_block_header_m_skip_bytes > 1 and bytes_[meta_block_header_m_skip_bytes - 1] == 0:
      error()
    MSkipLen_data = 0
    i = 0
    while i < meta_block_header_m_skip_bytes:
      MSkipLen_data = MSkipLen_data | (bytes_[i] << i)  # u32!
      i += 1
    return MSkipLen

def parse_m_len():
    global MLen_data
    if read_u32_from_n_nibbles(meta_block_header_m_nibbles):
      error()
    if meta_block_header_m_nibbles > 4 and (read_u32_from_n_nibbles_result >> ((meta_block_header_m_nibbles - 1)*4) == 0):
      error() # NonZeroTrailerNibble
    MLen_data = read_u32_from_n_nibbles_result + 1
    return MLen

def parse_is_uncompressed():
    global IsUncompressed_data
    if read_bit():
      error()
    IsUncompressed_data = read_bit_result
    return IsUncompressed

def parse_mlen_literals():
    global MLenLiterals_data
    MLenLiterals_data = read_fixed_length_string(meta_block_header_m_len)
    if MLenLiterals_data == NONE:
      error()
    return MLenLiterals

def parse_n_bltypes():
  value = lookup_symbol(header_bltype_codes)
  if value == 1 or value == 2:
    extra_bits = 0
  elif value == 3:
    extra_bits = 1
  elif value == 5:
    extra_bits = 2
  elif value == 9:
    extra_bits = 3
  elif value == 17:
    extra_bits = 4
  elif value == 33:
    extra_bits = 5
  elif value == 65:
    extra_bits = 6
  elif value == 129:
    extra_bits = 7
  if extra_bits > 0:
    if read_u32_from_n_bits(extra_bits):
      error()
    return value + read_u32_from_n_bits_result
  else:
    return value

def parse_n_bltypes_l():
  global NBltypesL_data
  NBltypesL_data = parse_n_bltypes()
  if NBltypesL_data == NONE:
    error()
  return NBltypesL

def parse_n_bltypes_i():
  global NBltypesI_data
  NBltypesI_data = parse_n_bltypes()
  if NBltypesI_data == NONE:
    error()
  return NBltypesI

def parse_n_bltypes_d():
  global NBltypesD_data
  NBltypesD_data = parse_n_bltypes()
  if NBltypesD_data == NONE:
    error()
  return NBltypesD

def parse_n_postfix():
  global NPostfix_data
  if read_u32_from_n_bits(2):
    error()
  NPostfix_data = read_u32_from_n_bits_result
  return NPostfix

def parse_n_direct():
  global NDirect_data
  if read_u32_from_n_bits(4):
    error()
  NDirect_data = read_u32_from_n_bits_result << meta_block_header_n_postfix
  return NDirect

def parse_context_modes_literals():
  global ContextModesLiterals_data
  ContextModesLiterals_data = alloc_pM(meta_block_header_n_bltypes_l)
  i = 0
  while i < meta_block_header_n_bltypes_l:
    if read_u32_from_n_bits(2):
      error()
    ContextModesLiterals_data[i] = read_u32_from_n_bits_result
    i += 1
  return ContextModesLiterals

def parse_n_trees_l():
  global NTreesL_data
  NTreesL_data = parse_n_bltypes()
  if NTreesL_data == NONE:
    error()
  return NTreesL

def parse_n_trees_d():
  global NTreesD_data
  NTreesD_data = parse_n_bltypes()
  if NTreesD_data == NONE:
    error()
  return NTreesD

def parse_prefix_code_kind():
  global PrefixCodeKind_Complex_data
  if read_u32_from_n_bits(2):
    error()
  if read_u32_from_n_bits_result == 1:
    return PrefixCodeKind_Simple
  PrefixCodeKind_Complex_data = read_u32_from_n_bits_result
  return PrefixCodeKind_Complex

def parse_simple_prefix_code(alphabet_size):
  #import ipdb; ipdb.set_trace()
  bit_width = alphabet_size - 1
  n = 0
  # count leading zeros
  if bit_width == 0:
    n = 16
  else:
    while True:
        if bit_width >= 32768:  # 2**15
          break
        n += 1
        bit_width <<= 1
  bit_width = 16 - n
  if read_u32_from_n_bits(2):
    error()
  n_sym = read_u32_from_n_bits_result + 1
  symbols = alloc_pH(n_sym)
  i = 0
  while i < n_sym:
    if read_u32_from_n_bits(bit_width):
      error()
    if read_u32_from_n_bits_result < alphabet_size:
      symbols[i] = read_u32_from_n_bits_result
    else:
      error()  # InvalidSymbol
    i += 1
  i = 0
  while i < n_sym - 1:
    j = i+1
    while j < n_sym:
      if symbols[i] == symbols[j]:
        error() # InvalidSymbol
      j += 1
    i += 1
  if n_sym == 4:
    if read_bit():
      error() # eof
    tree_select = read_bit_result
  else:
    tree_select = NONE
  if n_sym == 1 and tree_select == NONE:
    code_lengths = alloc_pM(1)
    code_lengths[0] = 0
  elif n_sym == 2 and tree_select == NONE:
    tmp_ = symbols[0]
    if tmp_ > symbols[1]:
      symbols[0] = symbols[1]
      symbols[1] = tmp_
    code_lengths = alloc_pM(2)
    code_lengths[0] = 1
    code_lengths[1] = 1
  elif n_sym == 3 and tree_select == NONE:
    # [1..3]rust  sort ind 1...2
    tmp_ = symbols[1]
    if tmp_ > symbols[2]:
      symbols[1] = symbols[2]
      symbols[2] = tmp_
    code_lengths = alloc_pM(3)
    code_lengths[0] = 1
    code_lengths[1] = 2
    code_lengths[2] = 2
  elif n_sym == 4 and tree_select == 0:
    # sort all in-place with insertion sort
    i = 1
    while i < n_sym:
      x = symbols[i]
      j = i - 1
      while j >= 0 and symbols[j] > x:
          symbols[j+1] = symbols[j]
          j = j - 1
      symbols[j+1] = x
      i += 1
    code_lengths = alloc_pM(4)
    code_lengths[0] = 2
    code_lengths[1] = 2
    code_lengths[2] = 2
    code_lengths[3] = 2
  elif n_sym == 4 and tree_select == 1:
    # [2..4]rust  sort ind 2...3
    tmp_ = symbols[2]
    if tmp_ > symbols[3]:
      symbols[2] = symbols[3]
      symbols[3] = tmp_
    code_lengths = alloc_pM(4)
    code_lengths[0] = 1
    code_lengths[1] = 2
    code_lengths[2] = 3
    code_lengths[3] = 3
  else:
    error()  # unreachable as len(symbols)<=4
  ret = codes_from_lengths_and_symbols(code_lengths, symbols)
  return ret

def parse_complex_prefix_code(h_skip, alphabet_size):
  #import ipdb; ipdb.set_trace()
  # symbols = [1, 2, 3, 4, 0, 5, 17, 6, 16, 7, 8, 9, 10, 11, 12, 13, 14, 15]
  bit_lengths_code = header_bit_lengths_code
  code_lengths = alloc_pM(18)
  i = 0
  while i < 18:
    code_lengths[i] = 0
    i += 1
  sum_ = 0
  len_non_zero_codelengths = 0
  i = h_skip
  while i < 18:
    code_length = lookup_symbol(bit_lengths_code)
    if code_length == NONE:
      error()
    code_lengths[i] = code_length
    if code_length > 0:
        sum_ = sum_ + (32 >> code_length)
        len_non_zero_codelengths += 1
        #
        # print("code length = ", code_lengths[i])
        # print("32 >> code length = ", 32 >> code_lengths[i])
        # print("sum = ", sum_)
        #
        if sum_ == 32:
          break
        if sum_ > 32:
          error() # CodeLengthsChecksum
    i += 1
  if len_non_zero_codelengths == 0:
    error()  # NoCodeLength
  if len_non_zero_codelengths >= 2 and sum_ < 32:
    error()  # CodeLengthsChecksum
  new_code_lengths = alloc_pM(18)
  new_code_lengths[0] = code_lengths[4]
  new_code_lengths[1] = code_lengths[0]
  new_code_lengths[2] = code_lengths[1]
  new_code_lengths[3] = code_lengths[2]
  new_code_lengths[4] = code_lengths[3]
  new_code_lengths[5] = code_lengths[5]
  new_code_lengths[6] = code_lengths[7]
  new_code_lengths[7] = code_lengths[9]
  new_code_lengths[8] = code_lengths[10]
  new_code_lengths[9] = code_lengths[11]
  new_code_lengths[10] = code_lengths[12]
  new_code_lengths[11] = code_lengths[13]
  new_code_lengths[12] = code_lengths[14]
  new_code_lengths[13] = code_lengths[15]
  new_code_lengths[14] = code_lengths[16]
  new_code_lengths[15] = code_lengths[17]
  new_code_lengths[16] = code_lengths[8]
  new_code_lengths[17] = code_lengths[6]
  code_lengths = new_code_lengths
  symbols = alloc_pH(18)
  i = 0
  while i < 18:
    symbols[i] = i
    i += 1
  prefix_code_code_lengths = codes_from_lengths_and_symbols(code_lengths, symbols)
  actual_code_lengths = alloc_pM(alphabet_size)
  i = 0
  while i < alphabet_size:
    actual_code_lengths[i] = 0
    i += 1
  sum_ = 0
  last_symbol = NONE
  last_repeat = NONE
  last_non_zero_codelength = 8
  i = 0
  while i < alphabet_size:
    code_length_code = lookup_symbol(prefix_code_code_lengths)
    if code_length_code == NONE:
      error()
    if code_length_code >= 0 and code_length_code <= 15:
      actual_code_lengths[i] = code_length_code
      i += 1
      last_symbol = code_length_code
      last_repeat = NONE
      if code_length_code > 0:
        last_non_zero_codelength = code_length_code
        sum_ += 32768 >> code_length_code
        if sum_ == 32768:
          break
        elif sum_ > 32768:
          error()  # CodeLengthsChecksum
    elif code_length_code == 16:
      if read_u32_from_n_bits(2):
        error()  # UnexpectedEOF
      extra_bits = read_u32_from_n_bits_result
      if last_symbol == 16 and last_repeat != NONE:
        new_repeat = 4 * (last_repeat - 2) + extra_bits + 3
        if i + new_repeat - last_repeat > alphabet_size:
          error()  # ParseErrorComplexPrefixCodeLengths
        j = 0
        while j < new_repeat - last_repeat:
          actual_code_lengths[i] = last_non_zero_codelength
          i += 1
          sum_ += 32768 >> last_non_zero_codelength
          j += 1
        if sum_ == 32768:
          break
        elif sum_ > 32768:
          error()  # CodeLengthsChecksum
        last_repeat = new_repeat
      else:
        repeat = 3 + extra_bits
        if i + repeat > alphabet_size:
          error()  # ParseErrorComplexPrefixCodeLengths
        j = 0
        while j < repeat:
          actual_code_lengths[i] = last_non_zero_codelength
          i += 1
          sum_ += 32768 >> last_non_zero_codelength
          j += 1
        if sum_ == 32768:
          break
        elif sum_ > 32768:
          error()  # CodeLengthsChecksum
        last_repeat = repeat
      last_symbol = 16
    elif code_length_code == 17:
      if read_u32_from_n_bits(3):
        error()  # UnexpectedEOF
      extra_bits = read_u32_from_n_bits_result
      if last_symbol == 17 and last_repeat != NONE:
        new_repeat = (8 * (last_repeat - 2)) + extra_bits + 3
        i += new_repeat - last_repeat
        last_repeat = new_repeat
      else:
        repeat = 3 + extra_bits
        i += repeat
        last_repeat = repeat
      if i > alphabet_size:
        error()  # ParseErrorComplexPrefixCodeLengths
      last_symbol = 17
    else:
      error()   # unreachable OR ParseErrorComplexPrefixCodeLengths
  tmp_ = 0
  i = 0
  while i < alphabet_size:
    if actual_code_lengths[i] > 0:
      tmp_ += 1
    i += 1
  if tmp_ < 2:
    error()  # LessThanTwoNonZeroCodeLengths
  ret = codes_from_lengths(actual_code_lengths)
  return ret

def parse_prefix_code(alphabet_size):
  prefix_code_kind = parse_prefix_code_kind()
  if prefix_code_kind == NONE:
    error()
  if prefix_code_kind == PrefixCodeKind_Complex:
    return parse_complex_prefix_code(PrefixCodeKind_Complex_data, alphabet_size)
  elif prefix_code_kind == PrefixCodeKind_Simple:
    return parse_simple_prefix_code(alphabet_size)
  else:
    return NONE # unreachable

def parse_prefix_code_block_types_literals():
  global PrefixCodeBlockTypesLiterals_data
  alphabet_size = meta_block_header_n_bltypes_l + 2
  tmp_ = parse_prefix_code(alphabet_size)
  if tmp_ == NONE:
    error()
  PrefixCodeBlockTypesLiterals_data = tmp_
  return PrefixCodeBlockTypesLiterals

def parse_prefix_code_block_counts_literals():
  global PrefixCodeBlockCountsLiterals_data
  tmp_ = parse_prefix_code(26)
  if tmp_ == NONE:
    error()
  PrefixCodeBlockCountsLiterals_data = tmp_
  return PrefixCodeBlockCountsLiterals

def parse_prefix_code_block_types_insert_and_copy_lengths():
  global PrefixCodeBlockTypesInsertAndCopyLengths_data
  alphabet_size = meta_block_header_n_bltypes_i + 2
  tmp_ = parse_prefix_code(alphabet_size)
  if tmp_ == NONE:
    error()
  PrefixCodeBlockTypesInsertAndCopyLengths_data = tmp_
  return PrefixCodeBlockTypesInsertAndCopyLengths

def parse_prefix_code_block_counts_insert_and_copy_lengths():
  global PrefixCodeBlockCountsInsertAndCopyLengths_data
  tmp_ = parse_prefix_code(26)
  if tmp_ == NONE:
    error()
  PrefixCodeBlockCountsInsertAndCopyLengths_data = tmp_
  return PrefixCodeBlockCountsInsertAndCopyLengths

def parse_prefix_code_block_types_distances():
  global PrefixCodeBlockTypesDistances_data
  alphabet_size = meta_block_header_n_bltypes_d + 2
  tmp_ = parse_prefix_code(alphabet_size)
  if tmp_ == NONE:
    error()
  PrefixCodeBlockTypesDistances_data = tmp_
  return PrefixCodeBlockTypesDistances

def parse_prefix_code_block_counts_distances():
  global PrefixCodeBlockCountsDistances_data
  tmp_ = parse_prefix_code(26)
  if tmp_ == NONE:
    error()
  PrefixCodeBlockCountsDistances_data = tmp_
  return PrefixCodeBlockCountsDistances

def parse_block_count(prefix_code):  # HuffmanCodes
  symbol = lookup_symbol(prefix_code)
  if symbol >= 0 and symbol <= 3:
    base_length = 1 + (symbol << 2)
    extra_bits = 2
  elif symbol >= 4 and symbol <= 7:
    base_length = 17 + ((symbol - 4) << 3)
    extra_bits = 3
  elif symbol >= 8 and symbol <= 11:
    base_length = 49 + ((symbol - 8) << 4)
    extra_bits = 4
  elif symbol >= 12 and symbol <= 15:
    base_length = 113 + ((symbol - 12) << 5)
    extra_bits = 5
  elif symbol >= 16 and symbol <= 17:
    base_length = 241 + ((symbol - 16) << 6)
    extra_bits = 6
  elif symbol == 18:
    base_length = 369
    extra_bits = 7
  elif symbol == 19:
    base_length = 497
    extra_bits = 8
  elif symbol == 20:
    base_length = 753
    extra_bits = 9
  elif symbol == 21:
    base_length = 1265
    extra_bits = 10
  elif symbol == 22:
    base_length = 2289
    extra_bits = 11
  elif symbol == 23:
    base_length = 4337
    extra_bits = 12
  elif symbol == 24:
    base_length = 8433
    extra_bits = 13
  elif symbol == 25:
    base_length = 16625
    extra_bits = 24
  else:
    error() # err EOF OR InvalidBlockCountCode
  if read_u32_from_n_bits(extra_bits):
    error() # err EOF
  return base_length + read_u32_from_n_bits_result

def parse_first_block_count_literals():
  global FirstBlockCountLiterals_data
  prefix_code = meta_block_prefix_tree_block_counts_literals
  FirstBlockCountLiterals_data = parse_block_count(prefix_code)
  if FirstBlockCountLiterals_data == NONE:
    error()
  return FirstBlockCountLiterals

def parse_first_block_count_insert_and_copy_lengths():
  global FirstBlockCountInsertAndCopyLengths_data
  prefix_code = meta_block_prefix_tree_block_counts_insert_and_copy_lengths
  FirstBlockCountInsertAndCopyLengths_data = parse_block_count(prefix_code)
  if FirstBlockCountInsertAndCopyLengths_data == NONE:
    error()
  return FirstBlockCountInsertAndCopyLengths

def parse_first_block_count_distances():
  global FirstBlockCountDistances_data
  prefix_code = meta_block_prefix_tree_block_counts_distances
  FirstBlockCountDistances_data = parse_block_count(prefix_code)
  if FirstBlockCountDistances_data == NONE:
    error()
  return FirstBlockCountDistances

def parse_prefix_codes_literals():
  global PrefixCodesLiterals_data
  n_trees_l = meta_block_header_n_trees_l
  prefix_codes = alloc_L(n_trees_l)
  alphabet_size = 256
  j = 0
  while j < n_trees_l:
    prefix_codes[j] = parse_prefix_code(alphabet_size)
    if prefix_codes[j] == NONE:
      error()
    j += 1
  PrefixCodesLiterals_data = prefix_codes
  return PrefixCodesLiterals

def parse_prefix_codes_insert_and_copy_lengths():
  global PrefixCodesInsertAndCopyLengths_data
  n_bltypes_i = meta_block_header_n_bltypes_i
  prefix_codes = alloc_L(n_bltypes_i)
  alphabet_size = 704
  j = 0
  while j < n_bltypes_i:
    prefix_codes[j] = parse_prefix_code(alphabet_size)
    if prefix_codes[j] == NONE:
      error()
    j += 1
  PrefixCodesInsertAndCopyLengths_data = prefix_codes
  return PrefixCodesInsertAndCopyLengths

def parse_prefix_codes_distances():
  global PrefixCodesDistances_data
  n_trees_d = meta_block_header_n_trees_d
  prefix_codes = alloc_L(n_trees_d)
  alphabet_size = 16 + meta_block_header_n_direct + (48 << meta_block_header_n_postfix)
  j = 0
  while j < n_trees_d:
    prefix_codes[j] = parse_prefix_code(alphabet_size)
    if prefix_codes[j] == NONE:
      error()
    j += 1
  PrefixCodesDistances_data = prefix_codes
  return PrefixCodesDistances

def parse_context_map(n_trees, len_):
  if read_bit():
    error() # err eof
  rlemax = read_bit_result
  if rlemax:
    if read_u32_from_n_bits(4):
      error() # err eof
    rlemax = read_u32_from_n_bits_result + 1
  alphabet_size = rlemax + n_trees
  prefix_tree = parse_prefix_code(alphabet_size)
  if prefix_tree == NONE:
    error()  # err
  c_map = alloc_pM(len_)
  c_pushed = 0
  while c_pushed < len_:
    run_length_code = lookup_symbol(prefix_tree)
    if run_length_code == NONE:
      error()  # err eof OR ParseErrorContextMap
    if run_length_code > 0 and run_length_code <= rlemax:
      if read_u32_from_n_bits(run_length_code):
        error() # err eof
      repeat = (1 << run_length_code) + read_u32_from_n_bits_result
      j = 0
      while j < repeat:
        c_map[c_pushed] = 0
        c_pushed += 1
        if c_pushed > len_:
          error()  # RunLengthExceededSizeOfContextMap
        j += 1
    else:
      if run_length_code == 0:
        c_map[c_pushed] = 0
      else:
        c_map[c_pushed] = run_length_code - rlemax
      c_pushed += 1
  if read_bit():
    error()  # err eof
  imtf_bit = read_bit_result
  if imtf_bit:
    inverse_move_to_front_transform(c_map) # mut c_map
  return c_map

def parse_context_map_literals():
  global ContextMapLiterals_data
  n_trees = meta_block_header_n_trees_l
  len_ = meta_block_header_n_bltypes_l * 64
  ContextMapLiterals_data = parse_context_map(n_trees, len_)
  if ContextMapLiterals_data == NONE:
    error() # err
  return ContextMapLiterals

def parse_context_map_distances():
  global ContextMapDistances_data
  n_trees = meta_block_header_n_trees_d
  len_ = meta_block_header_n_bltypes_d * 4
  ContextMapDistances_data = parse_context_map(n_trees, len_)
  if ContextMapDistances_data == NONE:
    error() # err
  return ContextMapDistances

def inverse_move_to_front_transform(v): # modifies v
  mtf = alloc_pM(256)
  i = 0
  while i < 256:
    mtf[i] = i
    i += 1
  i = 0
  while i < len(v):
    index = v[i]
    value = mtf[index]
    v[i] = value
    j = index
    while j > 0:
      mtf[j] = mtf[j - 1]
      j -= 1
    mtf[0] = value
    i += 1

def decode_insert_and_copy_length():
  global InsertLengthAndCopyLength_data_co_len, InsertLengthAndCopyLength_data_in_len
  insert_length = INSERT_LENGTHS_AND_COPY_LENGTHS[0 + meta_block_insert_and_copy_length*4]
  extra_bits_insert = INSERT_LENGTHS_AND_COPY_LENGTHS[1 + meta_block_insert_and_copy_length*4]
  copy_length = INSERT_LENGTHS_AND_COPY_LENGTHS[2 + meta_block_insert_and_copy_length*4]
  extra_bits_copy = INSERT_LENGTHS_AND_COPY_LENGTHS[3 + meta_block_insert_and_copy_length*4]
  if read_u32_from_n_bits(extra_bits_insert):
    error() # err eof
  insert_length += read_u32_from_n_bits_result
  if read_u32_from_n_bits(extra_bits_copy):
    error() # err eof
  copy_length += read_u32_from_n_bits_result
  InsertLengthAndCopyLength_data_co_len = copy_length
  InsertLengthAndCopyLength_data_in_len = insert_length
  return InsertLengthAndCopyLength


parse_block_switch_command_block_type = NONE
parse_block_switch_command_block_count = NONE
def parse_block_switch_command(prefix_tree_types, btype, btype_prev, n_bltypes, prefix_tree_counts): # 1:HuffmanCodes,2-4:nr,5:HuffmanCodes
  global parse_block_switch_command_block_type, parse_block_switch_command_block_count
  block_type_code = lookup_symbol(prefix_tree_types)
  if block_type_code == NONE:
    error() # decompr err
  if block_type_code == 0:
    block_type = btype_prev
  elif block_type_code == 1:
    block_type = (btype + 1) % n_bltypes
  elif block_type_code >= 2 and block_type_code <= 258:
    block_type = block_type_code - 2
  else:
    return NONE # unreachable
  block_count = parse_block_count(prefix_tree_counts)
  if block_count == NONE:
    error() # err
  parse_block_switch_command_block_type = block_type
  parse_block_switch_command_block_count = block_count
  return 0

parse_block_switch_command_literals_block_type = NONE
parse_block_switch_command_literals_block_count = NONE
def parse_block_switch_command_literals():
  global parse_block_switch_command_literals_block_type, parse_block_switch_command_literals_block_count
  prefix_tree_types = meta_block_prefix_tree_block_types_literals
  btype = meta_block_btype_l
  btype_prev = meta_block_btype_l_prev
  n_bltypes = meta_block_header_n_bltypes_l
  prefix_tree_counts = meta_block_prefix_tree_block_counts_literals
  if parse_block_switch_command(prefix_tree_types, btype, btype_prev, n_bltypes, prefix_tree_counts):
    error() # err
  parse_block_switch_command_literals_block_type = parse_block_switch_command_block_type
  parse_block_switch_command_literals_block_count = parse_block_switch_command_block_count
  return 0

parse_block_switch_command_insert_and_copy_lengths_block_type = NONE
parse_block_switch_command_insert_and_copy_lengths_block_count = NONE
def parse_block_switch_command_insert_and_copy_lengths():
  global parse_block_switch_command_insert_and_copy_lengths_block_type, parse_block_switch_command_insert_and_copy_lengths_block_count
  prefix_tree_types = meta_block_prefix_tree_block_types_insert_and_copy_lengths
  btype = meta_block_btype_i
  btype_prev = meta_block_btype_i_prev
  n_bltypes = meta_block_header_n_bltypes_i
  prefix_tree_counts = meta_block_prefix_tree_block_counts_insert_and_copy_lengths
  if parse_block_switch_command(prefix_tree_types, btype, btype_prev, n_bltypes, prefix_tree_counts):
    error() # err
  parse_block_switch_command_insert_and_copy_lengths_block_type = parse_block_switch_command_block_type
  parse_block_switch_command_insert_and_copy_lengths_block_count = parse_block_switch_command_block_count
  return 0

def parse_insert_and_copy_length():
  global meta_block_btype_i_prev, meta_block_blen_i, meta_block_btype_i, InsertAndCopyLength_data
  if meta_block_blen_i == NONE:
    pass
  elif meta_block_blen_i == 0:
    if parse_block_switch_command_insert_and_copy_lengths():
      error() # err
    meta_block_btype_i_prev = meta_block_btype_i
    meta_block_btype_i = parse_block_switch_command_insert_and_copy_lengths_block_type
    meta_block_blen_i = parse_block_switch_command_insert_and_copy_lengths_block_count - 1
  else:
    meta_block_blen_i -= 1
  btype = meta_block_btype_i
  InsertAndCopyLength_data = lookup_symbol(meta_block_prefix_trees_insert_and_copy_lengths[btype])
  if InsertAndCopyLength_data == NONE:
    error() # err eof OR ParseErrorInsertAndCopyLength
  return InsertAndCopyLength

parse_block_switch_command_distances_block_type = NONE
parse_block_switch_command_distances_block_count = NONE
def parse_block_switch_command_distances():
  global parse_block_switch_command_distances_block_type, parse_block_switch_command_distances_block_count
  prefix_tree_types = meta_block_prefix_tree_block_types_distances
  btype = meta_block_btype_d
  btype_prev = meta_block_btype_d_prev
  n_bltypes = meta_block_header_n_bltypes_d
  prefix_tree_counts = meta_block_prefix_tree_block_counts_distances
  if parse_block_switch_command(prefix_tree_types, btype, btype_prev, n_bltypes, prefix_tree_counts):
    error() # err
  parse_block_switch_command_distances_block_type = parse_block_switch_command_block_type
  parse_block_switch_command_distances_block_count = parse_block_switch_command_block_count
  return 0

def parse_insert_literals():
  global literal_buf_pointer, meta_block_btype_l_prev, meta_block_btype_l, meta_block_blen_l, InsertLiterals_data
  insert_length = meta_block_insert_length
  literals = alloc_pM(insert_length)
  j = 0
  while j < insert_length:
    if meta_block_blen_l == NONE:
      pass
    elif meta_block_blen_l == 0:
      if parse_block_switch_command_literals():
        error()
      meta_block_btype_l_prev = meta_block_btype_l
      meta_block_btype_l = parse_block_switch_command_literals_block_type
      meta_block_blen_l = parse_block_switch_command_literals_block_count - 1
    else:
      meta_block_blen_l -= 1
    btype = meta_block_btype_l
    context_mode = meta_block_context_modes_literals[btype]
    p1 = literal_buf[literal_buf_pointer]
    p2 = literal_buf[(literal_buf_pointer+1) % 2]
    if context_mode == 0:
      cid = p1 & 63
    elif context_mode == 1:
      cid = p1 >> 2
    elif context_mode == 2:
      cid = LUT_0[p1] | LUT_1[p2]
    elif context_mode == 3:
      cid = (LUT_2[p1] << 3) | LUT_2[p2]
    else:
      return NONE # unreachable
    index = meta_block_header_c_map_l[btype * 64 + cid]
    tmp_ = lookup_symbol(meta_block_prefix_trees_literals[index])
    if tmp_ == NONE:
      error() # err eof OR ParseErrorInsertLiterals
    literals[j] = tmp_
    literal_buf_pointer = (literal_buf_pointer+1) % 2
    literal_buf[literal_buf_pointer] = tmp_
    j += 1
  InsertLiterals_data = literals
  return InsertLiterals

def parse_distance_code():
  global meta_block_btype_d_prev, meta_block_btype_d, meta_block_blen_d, DistanceCode_data
  if meta_block_distance == 0:
    DistanceCode_data = 0
    return DistanceCode
  elif meta_block_distance == NONE:
    pass
  else:
    return NONE # unreachable
  if meta_block_blen_d == NONE:
    pass
  elif meta_block_blen_d == 0:
    if parse_block_switch_command_distances():
      error() # err
    meta_block_btype_d_prev = meta_block_btype_d
    meta_block_btype_d = parse_block_switch_command_distances_block_type
    meta_block_blen_d = parse_block_switch_command_distances_block_count - 1
  else:
    meta_block_blen_d -= 1
  if meta_block_copy_length == 0 or meta_block_copy_length == 1:
    error() # unreachable
  elif meta_block_copy_length == 2 or meta_block_copy_length == 3 or meta_block_copy_length == 4:
    cid = meta_block_copy_length - 2
  else:
    cid = 3
  index = meta_block_header_c_map_d[meta_block_btype_d * 4 + cid]
  DistanceCode_data = lookup_symbol(meta_block_prefix_trees_distances[index])
  if DistanceCode_data == NONE:
    error() # err decompr ParseErrorDistanceCode OR eof
  return DistanceCode

def decode_distance():
  global Distance_data, distance_buf_pointer
  if meta_block_distance_code == NONE:
    error() # unreachable
  elif meta_block_distance_code >= 0 and meta_block_distance_code <= 3:
    distance = distance_buf[(4 + distance_buf_pointer - meta_block_distance_code) % 4]
    #if distance == NONE:
    #  error() # RingBufferError
  elif meta_block_distance_code >= 4 and meta_block_distance_code <= 9:
    distance = distance_buf[distance_buf_pointer]
    sign = meta_block_distance_code % 2
    d = (meta_block_distance_code - 2) >> 1
    if sign:  # case +
      distance = distance + d
    else:  # case -
      if distance <= d:
        error() # InvalidNonPositiveDistance
      distance = distance - d
  elif meta_block_distance_code >= 10 and meta_block_distance_code <= 15:
    distance = distance_buf[(3 + distance_buf_pointer) % 4]
    sign = meta_block_distance_code % 2
    d = (meta_block_distance_code - 8) >> 1
    if sign:  # case +
      distance = distance + d
    else:  # case -
      if distance <= d:
        error() # InvalidNonPositiveDistance
      distance = distance - d
  elif meta_block_distance_code <= (15 + meta_block_header_n_direct):
    distance = meta_block_distance_code - 15
  else:
    n_direct = meta_block_header_n_direct
    n_postfix = meta_block_header_n_postfix
    ndistbits = 1 + ((meta_block_distance_code - n_direct - 16) >> (n_postfix + 1))
    if read_u32_from_n_bits(ndistbits):
      error() # eof err
    dextra = read_u32_from_n_bits_result
    hcode = (meta_block_distance_code - n_direct - 16) >> n_postfix
    postfix_mask = (1 << n_postfix) - 1
    lcode = (meta_block_distance_code - n_direct - 16) & postfix_mask
    offset = ((2 + (hcode & 1)) << ndistbits) - 4
    distance = ((offset + dextra) << n_postfix) + lcode + n_direct + 1
  if meta_block_distance_code > 0 and distance <= header_window_size and distance <= count_output:
    distance_buf_pointer = (distance_buf_pointer + 1) % 4
    distance_buf[distance_buf_pointer] = distance
  Distance_data = distance
  return Distance

def copy_literals():
  global CopyLiterals_data
  window_size = header_window_size
  copy_length = meta_block_copy_length
  distance = meta_block_distance
  max_allowed_distance = count_output
  if window_size < max_allowed_distance:
    max_allowed_distance = window_size
  if distance <= max_allowed_distance:
    window = alloc_pM(copy_length)
    l = distance
    if copy_length < l:
      l = copy_length
    # output_window.slice_tail(distance - 1, &mut window)
    n = distance - 1
    i = 0
    while i < copy_length:
      t = (output_window_pointer + len(output_window) - n + i) % len(output_window)
      window[i] = output_window[t]
      i += 1
    i = 0
    while i < copy_length:
      window[i] = window[i % l]
      i += 1
    CopyLiterals_data = window
    return CopyLiterals
  else:
    if copy_length < 4 or copy_length > 24:
      error()  # InvalidLengthInStaticDictionary
    word_id = distance - max_allowed_distance - 1
    if copy_length < 4:
      n_words_length = 0
    else:
      n_words_length = 1 << BROTLI_DICTIONARY_SIZE_BITS_BY_LENGTH[copy_length]
    index = word_id % n_words_length
    offset_from = BROTLI_DICTIONARY_OFFSETS_BY_LENGTH[copy_length] + index * copy_length
    offset_to = BROTLI_DICTIONARY_OFFSETS_BY_LENGTH[copy_length] + (index + 1) * copy_length
    base_word = alloc_pM(offset_to-offset_from)
    i = 0
    while i < offset_to-offset_from:
      base_word[i] = BROTLI_DICTIONARY[i + offset_from]
      i += 1
    transform_id = word_id >> BROTLI_DICTIONARY_SIZE_BITS_BY_LENGTH[copy_length]
    if transform_id > 120:
      error() # InvalidTransformId
    # print(bytes(eval('array.'+str(base_word))))  # remove
    CopyLiterals_data = transformation(transform_id, base_word)
    # print(transform_id, bytes(eval('array.'+str(CopyLiterals_data))))  # remove
    return CopyLiterals


def brotlidec(pinput, outb, cmpbuf=None):
  """pinput: input buffer, needs to support len() and []
     outb: output buffer, needs to support .append()
     returns bytes(outb)"""
  global count_output, header_wbits, header_window_size, literal_buf_pointer, meta_block_blen_d
  global meta_block_blen_i, meta_block_blen_l, meta_block_context_modes_literals, meta_block_copy_length
  global meta_block_count_output, meta_block_distance, meta_block_distance_code, meta_block_header_c_map_d
  global meta_block_btype_l_prev, meta_block_btype_l, meta_block_btype_i, meta_block_btype_i_prev
  global meta_block_btype_d, meta_block_btype_d_prev
  global meta_block_header_c_map_l, meta_block_header_is_last, meta_block_header_is_last_empty
  global meta_block_header_is_uncompressed, meta_block_header_m_len, meta_block_header_m_nibbles
  global meta_block_header_m_skip_bytes, meta_block_header_m_skip_len, meta_block_header_n_bltypes_d
  global meta_block_header_n_bltypes_i, meta_block_header_n_bltypes_l, meta_block_header_n_direct
  global meta_block_header_n_postfix, meta_block_header_n_trees_d, meta_block_header_n_trees_l
  global meta_block_insert_and_copy_length, meta_block_insert_length, meta_block_prefix_tree_block_counts_distances
  global meta_block_prefix_tree_block_counts_insert_and_copy_lengths, meta_block_prefix_tree_block_counts_literals
  global meta_block_prefix_tree_block_types_distances, meta_block_prefix_tree_block_types_insert_and_copy_lengths
  global meta_block_prefix_tree_block_types_literals, meta_block_prefix_trees_distances
  global meta_block_prefix_trees_insert_and_copy_lengths, meta_block_prefix_trees_literals
  global output_window, output_window_pointer, state, WBits_data, BROTLI_DICTIONARY
  global distance_buf, distance_buf_pointer, literal_buf
  global bit_pos, current_byte, global_bit_pos
  global input_buf, input_buf_pos, output_buf, gcmpbuf, cmpbuf_pos
  
  dir_path = os.path.dirname(os.path.abspath(__file__))
  fo = open(extract_zipped_paths(os.path.join(dir_path,'brotli-dict')),'rb')
  BROTLI_DICTIONARY = fo.read()
  fo.close()

  input_buf_pos = 0
  input_buf = pinput
  output_buf = outb
  gcmpbuf = cmpbuf
  if cmpbuf is not None:
    cmpbuf_pos = 0
  # import ipdb; ipdb.set_trace() # r
  state = StreamBegin
  while True:
    # print("state",state)
    # import ipdb; ipdb.set_trace() # c
    if state == StreamBegin:
      state = HeaderBegin
      distance_buf[0] = 16  # reversed!
      distance_buf[1] = 15
      distance_buf[2] = 11
      distance_buf[3] = 4
      distance_buf_pointer = 3
      literal_buf[0] = 0
      literal_buf[1] = 0
      literal_buf_pointer = 0
      count_output = 0
      bit_pos = 0
      current_byte = NONE
      global_bit_pos = 0
    elif state == NONE: # dec err
      error()
      return
    elif state == HeaderBegin:
      state = WBits
      WBits_data = parse_wbits()
    elif state == WBits:
      header_wbits = WBits_data
      header_window_size = (1 << WBits_data) - 16
      output_window = alloc_pM(header_window_size)
      output_window_pointer = 0
      state = HeaderEnd
    elif state == HeaderEnd:
      state = HeaderMetaBlockBegin
    elif state == HeaderMetaBlockBegin:
      meta_block_header_is_last = NONE
      meta_block_header_is_last_empty = NONE
      meta_block_header_m_nibbles = NONE
      meta_block_header_m_skip_bytes = NONE
      meta_block_header_m_skip_len = NONE
      meta_block_header_m_len = NONE
      meta_block_header_is_uncompressed = NONE
      meta_block_header_n_bltypes_l = NONE
      meta_block_header_n_bltypes_i = NONE
      meta_block_header_n_bltypes_d = NONE
      meta_block_header_n_postfix = NONE
      meta_block_header_n_direct = NONE
      meta_block_header_n_trees_l = NONE
      meta_block_header_n_trees_d = NONE
      meta_block_header_c_map_l = NONE
      meta_block_header_c_map_d = NONE
      meta_block_prefix_tree_block_types_literals = NONE
      meta_block_prefix_tree_block_counts_literals = NONE
      meta_block_prefix_trees_literals = NONE
      meta_block_count_output = 0
      meta_block_btype_l = 0
      meta_block_btype_l_prev = 1
      meta_block_blen_l = NONE
      meta_block_blen_i = NONE
      meta_block_blen_d = NONE
      meta_block_btype_i = 0
      meta_block_btype_i_prev = 1
      meta_block_btype_d = 0
      meta_block_btype_d_prev = 1
      meta_block_prefix_tree_block_types_insert_and_copy_lengths = NONE
      meta_block_prefix_tree_block_counts_insert_and_copy_lengths = NONE
      meta_block_prefix_tree_block_types_distances = NONE
      meta_block_prefix_tree_block_counts_distances = NONE
      meta_block_prefix_trees_insert_and_copy_lengths = NONE
      meta_block_prefix_trees_distances = NONE
      meta_block_context_modes_literals = NONE
      meta_block_insert_and_copy_length = NONE
      meta_block_copy_length = NONE
      meta_block_insert_length = NONE
      meta_block_distance = NONE
      meta_block_distance_code = NONE
      state = parse_is_last()
    elif state == IsLast and IsLast_data == 1:
      meta_block_header_is_last = 1
      state = parse_is_last_empty()
    elif state == IsLast and IsLast_data == 0:
      meta_block_header_is_last = 0
      state = parse_m_nibbles()
    elif state == IsLastEmpty and IsLastEmpty_data == 1:
      meta_block_header_is_last_empty = 1
      state = StreamEnd
    elif state == IsLastEmpty and IsLastEmpty_data == 0:
      meta_block_header_is_last_empty = 0
      state = parse_m_nibbles()
    elif state == MNibbles and MNibbles_data == 0:
      if read_bit():
        error() # eof
      if read_bit_result:
        error() # NonZeroReservedBit
        return
      meta_block_header_m_nibbles = 0
      state = parse_m_skip_bytes()
    elif state == MNibbles:
      meta_block_header_m_nibbles = MNibbles_data
      state = parse_m_len()
    elif state == MSkipBytes and MSkipBytes_data == 0:
      meta_block_header_m_skip_bytes = 0
      if read_u8_from_byte_tail() != 0:
        error() # NonZeroFillBit
        return
      state = MetaBlockEnd
    elif state == MSkipBytes:
      meta_block_header_m_skip_bytes = MSkipBytes_data
      state = parse_m_skip_len()
    elif state == MSkipLen:
      meta_block_header_m_skip_len = MSkipLen_data
      if read_u8_from_byte_tail() != 0:
        error() # NonZeroFillBit
        return
      state = MetaBlockEnd
    elif state == MLen:
      meta_block_header_m_len = MLen_data
      if meta_block_header_is_last:
        state = parse_n_bltypes_l()
      else:
        state = parse_is_uncompressed()
    elif state == IsUncompressed and IsUncompressed_data == 1:
      meta_block_header_is_uncompressed = 1
      if read_u8_from_byte_tail() != 0:
        error() # NonZeroFillBit
      state = parse_mlen_literals()
    elif state == MLenLiterals:
      i = 0
      while i < len(MLenLiterals_data):
        literal = MLenLiterals_data[i]
        out(literal)
        output_window_pointer = (output_window_pointer + 1) % len(output_window)
        output_window[output_window_pointer] = literal
        literal_buf_pointer = (literal_buf_pointer + 1) % 2
        literal_buf[literal_buf_pointer] = literal
        count_output += 1
        i += 1
      state = MetaBlockEnd
    elif state == IsUncompressed and IsUncompressed_data == 0:
      meta_block_header_is_uncompressed = 0
      state = parse_n_bltypes_l()
    elif state == NBltypesL:
      meta_block_header_n_bltypes_l = NBltypesL_data
      if NBltypesL_data >= 2:
        state = parse_prefix_code_block_types_literals()
      else:
        state = parse_n_bltypes_i()
    elif state == PrefixCodeBlockTypesLiterals:
      meta_block_prefix_tree_block_types_literals = PrefixCodeBlockTypesLiterals_data
      state = parse_prefix_code_block_counts_literals()
    elif state == PrefixCodeBlockCountsLiterals:
      meta_block_prefix_tree_block_counts_literals = PrefixCodeBlockCountsLiterals_data
      state = parse_first_block_count_literals()
    elif state == FirstBlockCountLiterals:
      meta_block_blen_l = FirstBlockCountLiterals_data
      state = parse_n_bltypes_i()
    elif state == NBltypesI:
      meta_block_header_n_bltypes_i = NBltypesI_data
      if NBltypesI_data >= 2:
        state = parse_prefix_code_block_types_insert_and_copy_lengths()
      else:
        state = parse_n_bltypes_d()
    elif state == PrefixCodeBlockTypesInsertAndCopyLengths:
      meta_block_prefix_tree_block_types_insert_and_copy_lengths = PrefixCodeBlockTypesInsertAndCopyLengths_data
      state = parse_prefix_code_block_counts_insert_and_copy_lengths()
    elif state == PrefixCodeBlockCountsInsertAndCopyLengths:
      meta_block_prefix_tree_block_counts_insert_and_copy_lengths = PrefixCodeBlockCountsInsertAndCopyLengths_data
      state = parse_first_block_count_insert_and_copy_lengths()
    elif state == FirstBlockCountInsertAndCopyLengths:
      meta_block_blen_i = FirstBlockCountInsertAndCopyLengths_data
      state = parse_n_bltypes_d()
    elif state == NBltypesD:
      meta_block_header_n_bltypes_d = NBltypesD_data
      if NBltypesD_data >= 2:
        state = parse_prefix_code_block_types_distances()
      else:
        state = parse_n_postfix()
    elif state == PrefixCodeBlockTypesDistances:
      meta_block_prefix_tree_block_types_distances = PrefixCodeBlockTypesDistances_data
      state = parse_prefix_code_block_counts_distances()
    elif state == PrefixCodeBlockCountsDistances:
      meta_block_prefix_tree_block_counts_distances = PrefixCodeBlockCountsDistances_data
      state = parse_first_block_count_distances()
    elif state == FirstBlockCountDistances:
      meta_block_blen_d = FirstBlockCountDistances_data
      state = parse_n_postfix()
    elif state == NPostfix:
      meta_block_header_n_postfix = NPostfix_data
      state = parse_n_direct()
    elif state == NDirect:
      meta_block_header_n_direct = NDirect_data
      state = parse_context_modes_literals()
    elif state == ContextModesLiterals:
      meta_block_context_modes_literals = ContextModesLiterals_data
      state = parse_n_trees_l()
    elif state == NTreesL:
      meta_block_header_n_trees_l = NTreesL_data
      meta_block_header_c_map_l = alloc_pM(64 * meta_block_header_n_bltypes_l)
      if NTreesL_data >= 2:
        state = parse_context_map_literals()
      else:
        state = parse_n_trees_d()
    elif state == ContextMapLiterals:
      meta_block_header_c_map_l = ContextMapLiterals_data
      state = parse_n_trees_d()
    elif state == NTreesD:
      meta_block_header_n_trees_d = NTreesD_data
      meta_block_header_c_map_d = alloc_pM(4 * meta_block_header_n_bltypes_d)
      if NTreesD_data >= 2:
        state = parse_context_map_distances()
      else:
        state = parse_prefix_codes_literals()
    elif state == ContextMapDistances:
      meta_block_header_c_map_d = ContextMapDistances_data
      state = parse_prefix_codes_literals()
    elif state == PrefixCodesLiterals:
      meta_block_prefix_trees_literals = PrefixCodesLiterals_data
      state = parse_prefix_codes_insert_and_copy_lengths()
    elif state == PrefixCodesInsertAndCopyLengths:
      meta_block_prefix_trees_insert_and_copy_lengths = PrefixCodesInsertAndCopyLengths_data
      state = parse_prefix_codes_distances()
    elif state == PrefixCodesDistances:
      meta_block_prefix_trees_distances = PrefixCodesDistances_data
      state = DataMetaBlockBegin
    elif state == DataMetaBlockBegin:
      state = parse_insert_and_copy_length()
    elif state == InsertAndCopyLength:
      meta_block_insert_and_copy_length = InsertAndCopyLength_data
      if InsertAndCopyLength_data >= 0 and InsertAndCopyLength_data <= 127:
        meta_block_distance = 0
      else:
        meta_block_distance = NONE
      state = decode_insert_and_copy_length()
    elif state == InsertLengthAndCopyLength:
      m_len = meta_block_header_m_len
      meta_block_insert_length = InsertLengthAndCopyLength_data_in_len
      meta_block_copy_length = InsertLengthAndCopyLength_data_co_len
      if m_len < meta_block_count_output + meta_block_insert_length:  # or (m_len > meta_block_count_output + meta_block_insert_length and m_len < meta_block_count_output + meta_block_insert_length + meta_block_copy_length)
        error() # ExceededExpectedBytes
      state = parse_insert_literals()
    elif state == InsertLiterals:
      m_len = meta_block_header_m_len
      if m_len < meta_block_count_output + len(InsertLiterals_data):
        error() # ExceededExpectedBytes
      i = 0
      while i < len(InsertLiterals_data):
        literal = InsertLiterals_data[i]
        out(literal)
        output_window_pointer = (output_window_pointer + 1) % len(output_window)
        output_window[output_window_pointer] = literal
        count_output += 1
        meta_block_count_output += 1
        i += 1
      if meta_block_header_m_len == meta_block_count_output:
        state = DataMetaBlockEnd
      else:
        state = parse_distance_code()
    elif state == DistanceCode:
      meta_block_distance_code = DistanceCode_data
      state = decode_distance()
    elif state == Distance:
      meta_block_distance = Distance_data
      state = copy_literals()
    elif state == CopyLiterals:
      m_len = meta_block_header_m_len
      if m_len < meta_block_count_output + len(CopyLiterals_data):
        error() # err ExceededExpectedBytes
      i = 0
      while i < len(CopyLiterals_data):
        literal = CopyLiterals_data[i]
        out(literal)
        literal_buf_pointer = (literal_buf_pointer + 1) % 2
        literal_buf[literal_buf_pointer] = literal
        output_window_pointer = (output_window_pointer + 1) % len(output_window)
        output_window[output_window_pointer] = literal
        count_output += 1
        meta_block_count_output += 1
        i += 1
      if meta_block_header_m_len == meta_block_count_output:
        state = DataMetaBlockEnd
      else:
        state = DataMetaBlockBegin
    elif state == DataMetaBlockEnd:
      state = MetaBlockEnd
    elif state == MetaBlockEnd:
      if meta_block_header_is_last:
        state = StreamEnd
      else:
        state = HeaderMetaBlockBegin
    elif state == StreamEnd:
      if read_u8_from_byte_tail() != 0:
        error() # NonZeroTrailerBit
      if read_u8() == NONE: # i.e. BitReaderError
        state = StreamBegin
        tmbuf = output_buf
        output_buf = []
        input_buf = []
        return bytes(tmbuf)


def main():
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('input', nargs='?', type=argparse.FileType('rb'), default=sys.stdin.buffer, help='input file')
  parser.add_argument('--append', type=argparse.FileType('rb'), dest='addseg', default=[], metavar='FILE', action='append', help='additional input files')
  parser.add_argument('--compare', type=argparse.FileType('rb'), dest='compare', default=None, metavar='EXPECTEDFILE', help='compare output and run ipdb for mismatch')
  parser.add_argument('output', nargs='*', type=argparse.FileType('wb'), default=[sys.stdout.buffer], help='output file')
  args = parser.parse_args()
  cmpbuf = args.compare.read() if args.compare else None
  outb = brotlidec(args.input.read(), [], cmpbuf=cmpbuf)
  args.output[0].write(bytes(outb))
  for additional_segment in args.addseg:
    if len(args.output) > 1:
      args.output.pop(0)
    outb = brotlidec(additional_segment.read(), [])
    args.output[0].write(bytes(outb))

if __name__ == '__main__':
    main()

