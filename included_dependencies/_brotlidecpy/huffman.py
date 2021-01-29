# Copyright 2021 Sidney Markowitz All Rights Reserved.
# Distributed under MIT license.
# See file LICENSE for detail or copy at https://opensource.org/licenses/MIT

MAX_LENGTH = 15


def _get_next_key(key, length):
    """Returns reverse(reverse(key, len) + 1, len), where reverse(key, len) is the
     bit-wise reversal of the length least significant bits of key"""
    step = 1 << (length - 1)
    while key & step:
        step >>= 1
    return (key & (step - 1)) + step


def _replicate_value(table, i, step, end, code):
    """Stores code in table[0], table[step], table[2*step], ..., table[end] Assumes end is integer multiple of step"""
    for index in range(i+end-step, i - step, -step):
        table[index] = HuffmanCode(code.bits, code.value)


def _next_table_bit_size(count, length, root_bits):
    """Returns the table width of the next 2nd level table. count is the histogram of bit lengths for the
     remaining symbols, len is the code length of the next processed symbol"""
    left = 1 << (length - root_bits)
    while length < MAX_LENGTH:
        left -= count[length]
        if left <= 0:
            break
        length += 1
        left <<= 1
    return length - root_bits


class HuffmanCode:
    def __init__(self, bits, value):
        self.bits = bits  # number of bits used for this symbol
        self.value = value  # symbol value or table offset


def brotli_build_huffman_table(root_table, table, root_bits, code_lengths, code_lengths_size):
    start_table = table
    # Local variables used
    # code             current table entry
    # len;             current code length
    # symbol;          symbol index in original or sorted table
    # key;             reversed prefix code
    # step;            step size to replicate values in current table
    # low;             low bits for current root entry
    # mask;            mask for low bits
    # table_bits;      key length of current table
    # table_size;      size of current table
    # total_size;      sum of root table size and 2nd level table sizes
    # sorted_symbols;      symbols sorted by code length
    count = [0] * (MAX_LENGTH + 1)  # number of codes of each length
    offset = [0] * (MAX_LENGTH + 1)  # offsets in sorted table for each length

    sorted_symbols = [0] * code_lengths_size

    # build histogram of code lengths
    for symbol in range(0,  code_lengths_size):
        count[code_lengths[symbol]] += 1

    # generate offsets into sorted symbol table by code length
    offset[1] = 0
    for length in range(1, MAX_LENGTH):
        offset[length + 1] = offset[length] + count[length]

    # sort symbols by length, by symbol order within each length
    for symbol in range(0, code_lengths_size):
        length = code_lengths[symbol]
        if length != 0:
            sorted_symbols[offset[length]] = symbol
            offset[length] += 1

    table_bits = root_bits
    table_size = 1 << table_bits
    total_size = table_size

    # special case code with only one value
    if offset[MAX_LENGTH] == 1:
        for key in range(0, total_size):
            root_table[table + key] = HuffmanCode(0, sorted_symbols[0] & 0xffff)
        return total_size

    # fill in root table
    key = 0
    symbol = 0
    step = 2
    for length in range(1, root_bits+1):
        while count[length] > 0:
            code = HuffmanCode(length & 0xff, sorted_symbols[symbol] & 0xffff)
            symbol += 1
            _replicate_value(root_table, table + key, step, table_size, code)
            key = _get_next_key(key, length)
            count[length] -= 1
        step <<= 1

    # fill in 2nd level tables and add pointers to root table
    mask = total_size - 1
    low = -1
    step = 2
    for length in range(root_bits + 1, MAX_LENGTH+1):
        while count[length] > 0:
            if (key & mask) != low:
                table += table_size
                table_bits = _next_table_bit_size(count, length, root_bits)
                table_size = 1 << table_bits
                total_size += table_size
                low = key & mask
                root_table[start_table + low] = HuffmanCode((table_bits + root_bits) & 0xff,
                                                            ((table - start_table) - low) & 0xffff)
            code = HuffmanCode((length - root_bits) & 0xff, sorted_symbols[symbol] & 0xffff)
            symbol += 1
            _replicate_value(root_table, table + (key >> root_bits), step, table_size, code)
            key = _get_next_key(key, length)
            count[length] -= 1
        step <<= 1

    return total_size
