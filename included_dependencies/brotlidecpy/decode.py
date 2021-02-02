# Copyright 2021 Sidney Markowitz All Rights Reserved.
# Distributed under MIT license.
# See file LICENSE for detail or copy at https://opensource.org/licenses/MIT

from .huffman import HuffmanCode, brotli_build_huffman_table
from .prefix import Prefix, kBlockLengthPrefixCode, kInsertLengthPrefixCode, kCopyLengthPrefixCode
from .bit_reader import BrotliBitReader
from .dictionary import BrotliDictionary
from .context import Context
from .transform import Transform, kNumTransforms

kDefaultCodeLength = 8
kCodeLengthRepeatCode = 16
kNumLiteralCodes = 256
kNumInsertAndCopyCodes = 704
kNumBlockLengthCodes = 26
kLiteralContextBits = 6
kDistanceContextBits = 2

HUFFMAN_TABLE_BITS = 8
HUFFMAN_TABLE_MASK = 0xff
#  Maximum possible Huffman table size for an alphabet size of 704, max code length 15 and root table bits 8.
HUFFMAN_MAX_TABLE_SIZE = 1080

CODE_LENGTH_CODES = 18
kCodeLengthCodeOrder = bytearray([1, 2, 3, 4, 0, 5, 17, 6, 16, 7, 8, 9, 10, 11, 12, 13, 14, 15])

NUM_DISTANCE_SHORT_CODES = 16
kDistanceShortCodeIndexOffset = bytearray([3, 2, 1, 0, 3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2])

kDistanceShortCodeValueOffset = [0, 0, 0, 0, -1, 1, -2, 2, -3, 3, -1, 1, -2, 2, -3, 3]

kMaxHuffmanTableSize = [256, 402, 436, 468, 500, 534, 566, 598, 630, 662, 694, 726, 758, 790, 822, 854, 886, 920, 952,
                        984, 1016, 1048, 1080]


def decode_window_bits(br):
    if br.read_bits(1) == 0:
        return 16
    n = br.read_bits(3)
    if n > 0:
        return 17 + n
    n = br.read_bits(3)
    if n > 0:
        return 8 + n
    return 17


def decode_var_len_uint8(br):
    """Decodes a number in the range [0..255], by reading 1 - 11 bits"""
    if br.read_bits(1):
        nbits = br.read_bits(3)
        if nbits == 0:
            return 1
        return br.read_bits(nbits) + (1 << nbits)
    return 0


class MetaBlockLength:
    def __init__(self):
        self.meta_block_length = 0
        self.input_end = 0
        self.is_uncompressed = 0
        self.is_metadata = False


def decode_meta_block_length(br):
    out = MetaBlockLength()
    out.input_end = br.read_bits(1)
    if out.input_end and br.read_bits(1):
        return out

    size_nibbles = br.read_bits(2) + 4
    if size_nibbles == 7:
        out.is_metadata = True

        if br.read_bits(1) != 0:
            raise Exception('Invalid reserved bit')

        size_bytes = br.read_bits(2)
        if size_bytes == 0:
            return out

        for i in range(0, size_bytes):
            next_byte = br.read_bits(8)
            if i + 1 == size_bytes and size_bytes > 1 and next_byte == 0:
                raise Exception('Invalid size byte')

            out.meta_block_length |= next_byte << (i * 8)
    else:
        for i in range(0, size_nibbles):
            next_nibble = br.read_bits(4)
            if i + 1 == size_nibbles and size_nibbles > 4 and next_nibble == 0:
                raise Exception('Invalid size nibble')

            out.meta_block_length |= next_nibble << (i * 4)

    out.meta_block_length += 1

    if not out.input_end and not out.is_metadata:
        out.is_uncompressed = br.read_bits(1)

    return out


def read_symbol(table, index, br):
    """Decodes the next Huffman code from bit-stream. table is array of nodes in a huffman tree, index points to root"""
    x_bits = br.read_bits(16, 0)  # The C reference version assumes 15 is the max needed and uses 16 in this function
    index += (x_bits & HUFFMAN_TABLE_MASK)
    nbits = table[index].bits - HUFFMAN_TABLE_BITS
    skip = 0
    if nbits > 0:
        skip = HUFFMAN_TABLE_BITS
        index += table[index].value + ((x_bits >> HUFFMAN_TABLE_BITS) & br.kBitMask[nbits])
    br.read_bits(None, skip + table[index].bits)
    return table[index].value


def read_huffman_code_lengths(code_length_code_lengths, num_symbols, code_lengths, br):
    symbol = 0
    prev_code_len = kDefaultCodeLength
    repeat = 0
    repeat_code_len = 0
    space = 32768

    table = [HuffmanCode(0, 0) for _ in range(0, 32)]

    brotli_build_huffman_table(table, 0, 5, code_length_code_lengths, CODE_LENGTH_CODES)

    while (symbol < num_symbols) and (space > 0):
        p = 0
        p += br.read_bits(5, 0)
        br.read_bits(None, table[p].bits)
        code_len = table[p].value & 0xff
        if code_len < kCodeLengthRepeatCode:
            repeat = 0
            code_lengths[symbol] = code_len
            symbol += 1
            if code_len != 0:
                prev_code_len = code_len
                space -= 0x8000 >> code_len
        else:
            extra_bits = code_len - 14
            new_len = 0
            if code_len == kCodeLengthRepeatCode:
                new_len = prev_code_len
            if repeat_code_len != new_len:
                repeat = 0
                repeat_code_len = new_len
            old_repeat = repeat
            if repeat > 0:
                repeat -= 2
                repeat <<= extra_bits
            repeat += br.read_bits(extra_bits) + 3
            repeat_delta = repeat - old_repeat
            if symbol + repeat_delta > num_symbols:
                raise Exception('[read_huffman_code_lengths] symbol + repeat_delta > num_symbols')

            for x in range(0, repeat_delta):
                code_lengths[symbol + x] = repeat_code_len

            symbol += repeat_delta

            if repeat_code_len != 0:
                space -= repeat_delta << (15 - repeat_code_len)

    if space != 0:
        raise Exception('[read_huffman_code_lengths] space = %s' % space)

    for i in range(symbol, num_symbols):
        code_lengths[i] = 0


def read_huffman_code(alphabet_size, tables, table, br):
    code_lengths = bytearray([0] * alphabet_size)

    # simple_code_or_skip is used as follows:
    # 1 for simple code
    # 0 for no skipping, 2 skips 2 code lengths, 3 skips 3 code lengths
    simple_code_or_skip = br.read_bits(2)
    if simple_code_or_skip == 1:
        # Read symbols, codes & code lengths directly.
        max_bits_counter = alphabet_size - 1
        max_bits = 0
        symbols = [0, 0, 0, 0]
        num_symbols = br.read_bits(2) + 1
        while max_bits_counter:
            max_bits_counter >>= 1
            max_bits += 1

        for i in range(0, num_symbols):
            symbols[i] = br.read_bits(max_bits) % alphabet_size
            code_lengths[symbols[i]] = 2
        code_lengths[symbols[0]] = 1

        if num_symbols == 2:
            if symbols[0] == symbols[1]:
                raise Exception('[read_huffman_code] invalid symbols')
            code_lengths[symbols[1]] = 1
        elif num_symbols == 3:
            if symbols[0] == symbols[1] or symbols[0] == symbols[2] or symbols[1] == symbols[2]:
                raise Exception('[read_huffman_code] invalid symbols')
        elif num_symbols == 4:
            if symbols[0] == symbols[1] or symbols[0] == symbols[2] or symbols[0] == symbols[3] or symbols[1] == \
                    symbols[2] or symbols[1] == symbols[3] or symbols[2] == symbols[3]:
                raise Exception('[read_huffman_code] invalid symbols')
            if br.read_bits(1):
                code_lengths[symbols[2]] = 3
                code_lengths[symbols[3]] = 3
            else:
                code_lengths[symbols[0]] = 2
    else:  # Decode Huffman-coded code lengths
        code_length_code_lengths = bytearray([0] * CODE_LENGTH_CODES)
        space = 32
        num_codes = 0
        # Static Huffman code for the code length code lengths
        huff = [HuffmanCode(2, 0), HuffmanCode(2, 4), HuffmanCode(2, 3), HuffmanCode(3, 2),
                HuffmanCode(2, 0), HuffmanCode(2, 4), HuffmanCode(2, 3), HuffmanCode(4, 1),
                HuffmanCode(2, 0), HuffmanCode(2, 4), HuffmanCode(2, 3), HuffmanCode(3, 2),
                HuffmanCode(2, 0), HuffmanCode(2, 4), HuffmanCode(2, 3), HuffmanCode(4, 5)]
        for i in range(simple_code_or_skip, CODE_LENGTH_CODES):
            if space <= 0:
                break
            code_len_idx = kCodeLengthCodeOrder[i]
            p = 0
            p += br.read_bits(4, 0)
            br.read_bits(None, huff[p].bits)
            v = huff[p].value
            code_length_code_lengths[code_len_idx] = v
            if v != 0:
                space -= (32 >> v)
                num_codes += 1

        if num_codes != 1 and space != 0:
            raise Exception('[read_huffman_code] invalid num_codes or space')

        read_huffman_code_lengths(code_length_code_lengths, alphabet_size, code_lengths, br)

    table_size = brotli_build_huffman_table(tables, table, HUFFMAN_TABLE_BITS, code_lengths, alphabet_size)

    if table_size == 0:
        raise Exception('[read_huffman_code] BuildHuffmanTable failed: ')

    return table_size


def read_block_length(table, index, br):
    code = read_symbol(table, index, br)
    nbits = kBlockLengthPrefixCode[code].nbits
    return kBlockLengthPrefixCode[code].offset + br.read_bits(nbits)


def translate_short_codes(code, ringbuffer, index):
    if code < NUM_DISTANCE_SHORT_CODES:
        index += kDistanceShortCodeIndexOffset[code]
        index &= 3
        val = ringbuffer[index] + kDistanceShortCodeValueOffset[code]
    else:
        val = code - NUM_DISTANCE_SHORT_CODES + 1
    return val


def move_to_front(v, index):
    v.insert(0, v.pop(index))


def inverse_move_to_front_transform(v, v_len):
    mtf = list(range(0, 256))
    for i in range(0, v_len):
        index = v[i]
        v[i] = mtf[index]
        if index:
            move_to_front(mtf, index)


# Contains a collection of huffman trees with the same alphabet size.
class HuffmanTreeGroup:
    def __init__(self, alphabet_size, num_huff_trees):
        self.alphabet_size = alphabet_size
        self.num_huff_trees = num_huff_trees
        self.codes = [0] * (num_huff_trees + num_huff_trees * kMaxHuffmanTableSize[(alphabet_size + 31) >> 5])
        self.huff_trees = [0] * num_huff_trees

    def decode(self, br):
        next_entry = 0
        for i in range(0, self.num_huff_trees):
            self.huff_trees[i] = next_entry
            table_size = read_huffman_code(self.alphabet_size, self.codes, next_entry, br)
            next_entry += table_size


class DecodeContextMap:
    def __init__(self, context_map_size, br):
        max_run_length_prefix = 0
        self.num_huff_trees = decode_var_len_uint8(br) + 1
        self.context_map = bytearray([0] * context_map_size)

        if self.num_huff_trees <= 1:
            return

        use_rle_for_zeros = br.read_bits(1)
        if use_rle_for_zeros:
            max_run_length_prefix = br.read_bits(4) + 1

        table = [HuffmanCode(0, 0) for _ in range(0, HUFFMAN_MAX_TABLE_SIZE)]

        read_huffman_code(self.num_huff_trees + max_run_length_prefix, table, 0, br)

        i = 0
        while i < context_map_size:
            code = read_symbol(table, 0, br)
            if code == 0:
                self.context_map[i] = 0
                i += 1
            elif code <= max_run_length_prefix:
                for reps in range((1 << code) + br.read_bits(code), 0, -1):
                    if i >= context_map_size:
                        raise Exception('[DecodeContextMap] i >= context_map_size')
                    self.context_map[i] = 0
                    i += 1
            else:
                self.context_map[i] = code - max_run_length_prefix
                i += 1
        if br.read_bits(1):
            inverse_move_to_front_transform(self.context_map, context_map_size)


def decode_block_type(max_block_type, trees, tree_type, block_types, ring_buffers, indexes, br):
    ringbuffer = tree_type * 2
    index = tree_type
    type_code = read_symbol(trees, tree_type * HUFFMAN_MAX_TABLE_SIZE, br)
    if type_code == 0:
        block_type = ring_buffers[ringbuffer + (indexes[index] & 1)]
    elif type_code == 1:
        block_type = ring_buffers[ringbuffer + ((indexes[index] - 1) & 1)] + 1
    else:
        block_type = type_code - 2
    if block_type >= max_block_type:
        block_type -= max_block_type
    block_types[tree_type] = block_type
    ring_buffers[ringbuffer + (indexes[index] & 1)] = block_type
    indexes[index] += 1


def copy_uncompressed_block_to_output(length, pos, output_buffer, br):
    """This only is called when input is on a byte boundary. Copy length raw bytes from input to output[pos]"""
    br.copy_bytes(output_buffer, pos, length)


def jump_to_byte_boundary(br):
    """Advances the bit reader position if needed to put it on a byte boundary"""
    br.copy_bytes(b'', 0, 0)


def brotli_decompress_buffer(input_buffer):
    br = BrotliBitReader(input_buffer)
    decode_window_bits(br)
    out = decode_meta_block_length(br)
    decompressed_size = out.meta_block_length
    output_buffer = bytearray([0] * decompressed_size)
    br.reset()
    brotli_decompress_br_to_buffer(br, output_buffer)
    return output_buffer


def brotli_decompress_br_to_buffer(br, output_buffer):
    pos = 0
    input_end = 0
    max_distance = 0
    # This ring buffer holds a few past copy distances that will be used by some special distance codes.
    dist_rb = [16, 15, 11, 4]
    dist_rb_idx = 0
    hgroup = [HuffmanTreeGroup(0, 0), HuffmanTreeGroup(0, 0), HuffmanTreeGroup(0, 0)]

    # Decode window size.
    window_bits = decode_window_bits(br)
    max_backward_distance = (1 << window_bits) - 16

    block_type_trees = [HuffmanCode(0, 0) for _ in range(0, 3 * HUFFMAN_MAX_TABLE_SIZE)]
    block_len_trees = [HuffmanCode(0, 0) for _ in range(0, 3 * HUFFMAN_MAX_TABLE_SIZE)]

    while not input_end:
        block_length = [1 << 28, 1 << 28, 1 << 28]
        block_type = [0] * 3
        num_block_types = [1] * 3
        block_type_rb = [0, 1, 0, 1, 0, 1]
        block_type_rb_index = [0] * 3

        for i in range(0, 3):
            hgroup[i].codes = None
            hgroup[i].huff_trees = None

        _out = decode_meta_block_length(br)
        meta_block_remaining_len = _out.meta_block_length
        input_end = _out.input_end
        is_uncompressed = _out.is_uncompressed

        if _out.is_metadata:
            jump_to_byte_boundary(br)

            while meta_block_remaining_len > 0:
                # Read one byte and ignore it
                br.read_bits(8)
                meta_block_remaining_len -= 1
            continue

        if meta_block_remaining_len == 0:
            continue

        if is_uncompressed:
            copy_uncompressed_block_to_output(meta_block_remaining_len, pos, output_buffer, br)
            pos += meta_block_remaining_len
            continue

        for i in range(0, 3):
            num_block_types[i] = decode_var_len_uint8(br) + 1
            if num_block_types[i] >= 2:
                read_huffman_code(num_block_types[i] + 2, block_type_trees, i * HUFFMAN_MAX_TABLE_SIZE, br)
                read_huffman_code(kNumBlockLengthCodes, block_len_trees, i * HUFFMAN_MAX_TABLE_SIZE, br)
                block_length[i] = read_block_length(block_len_trees, i * HUFFMAN_MAX_TABLE_SIZE, br)
                block_type_rb_index[i] = 1

        distance_postfix_bits = br.read_bits(2)
        num_direct_distance_codes = NUM_DISTANCE_SHORT_CODES + (br.read_bits(4) << distance_postfix_bits)
        distance_postfix_mask = (1 << distance_postfix_bits) - 1
        num_distance_codes = (num_direct_distance_codes + (48 << distance_postfix_bits))
        context_modes = bytearray([0] * num_block_types[0])

        for i in range(0, num_block_types[0]):
            context_modes[i] = (br.read_bits(2) << 1)

        _o1 = DecodeContextMap(num_block_types[0] << kLiteralContextBits, br)
        num_literal_huff_trees = _o1.num_huff_trees
        context_map = _o1.context_map

        _o2 = DecodeContextMap(num_block_types[2] << kDistanceContextBits, br)
        num_dist_huff_trees = _o2.num_huff_trees
        dist_context_map = _o2.context_map

        hgroup[0] = HuffmanTreeGroup(kNumLiteralCodes, num_literal_huff_trees)
        hgroup[1] = HuffmanTreeGroup(kNumInsertAndCopyCodes, num_block_types[1])
        hgroup[2] = HuffmanTreeGroup(num_distance_codes, num_dist_huff_trees)

        for i in range(0, 3):
            hgroup[i].decode(br)

        context_map_slice = 0
        dist_context_map_slice = 0
        context_mode = context_modes[block_type[0]]
        context_lookup_offset1 = Context.lookupOffsets[context_mode]
        context_lookup_offset2 = Context.lookupOffsets[context_mode + 1]
        huff_tree_command = hgroup[1].huff_trees[0]

        while meta_block_remaining_len > 0:

            if block_length[1] == 0:
                decode_block_type(num_block_types[1], block_type_trees, 1, block_type, block_type_rb,
                                  block_type_rb_index, br)
                block_length[1] = read_block_length(block_len_trees, HUFFMAN_MAX_TABLE_SIZE, br)
                huff_tree_command = hgroup[1].huff_trees[block_type[1]]
            block_length[1] -= 1
            cmd_code = read_symbol(hgroup[1].codes, huff_tree_command, br)
            range_idx = cmd_code >> 6
            distance_code = 0
            if range_idx >= 2:
                range_idx -= 2
                distance_code = -1
            insert_code = Prefix.kInsertRangeLut[range_idx] + ((cmd_code >> 3) & 7)
            copy_code = Prefix.kCopyRangeLut[range_idx] + (cmd_code & 7)
            insert_length = kInsertLengthPrefixCode[insert_code].offset + br.read_bits(
                kInsertLengthPrefixCode[insert_code].nbits)
            copy_length = kCopyLengthPrefixCode[copy_code].offset + br.read_bits(
                kCopyLengthPrefixCode[copy_code].nbits)
            prev_byte1 = output_buffer[pos - 1]
            prev_byte2 = output_buffer[pos - 2]
            for j in range(0, insert_length):
                if block_length[0] == 0:
                    decode_block_type(num_block_types[0], block_type_trees, 0, block_type, block_type_rb,
                                      block_type_rb_index, br)
                    block_length[0] = read_block_length(block_len_trees, 0, br)
                    context_offset = block_type[0] << kLiteralContextBits
                    context_map_slice = context_offset
                    context_mode = context_modes[block_type[0]]
                    context_lookup_offset1 = Context.lookupOffsets[context_mode]
                    context_lookup_offset2 = Context.lookupOffsets[context_mode + 1]
                context = Context.lookup[context_lookup_offset1 + prev_byte1] | Context.lookup[
                    context_lookup_offset2 + prev_byte2]
                literal_huff_tree_index = context_map[context_map_slice + context]
                block_length[0] -= 1
                prev_byte2 = prev_byte1
                prev_byte1 = read_symbol(hgroup[0].codes, hgroup[0].huff_trees[literal_huff_tree_index], br)
                output_buffer[pos] = prev_byte1
                pos += 1
            meta_block_remaining_len -= insert_length
            if meta_block_remaining_len <= 0:
                break

            if distance_code < 0:
                if block_length[2] == 0:
                    decode_block_type(num_block_types[2], block_type_trees, 2, block_type, block_type_rb,
                                      block_type_rb_index, br)
                    block_length[2] = read_block_length(block_len_trees, 2 * HUFFMAN_MAX_TABLE_SIZE, br)
                    dist_context_offset = block_type[2] << kDistanceContextBits
                    dist_context_map_slice = dist_context_offset
                block_length[2] -= 1
                context = (3 if copy_length > 4 else copy_length - 2) & 0xff
                dist_huff_tree_index = dist_context_map[dist_context_map_slice + context]
                distance_code = read_symbol(hgroup[2].codes, hgroup[2].huff_trees[dist_huff_tree_index], br)
                if distance_code >= num_direct_distance_codes:
                    distance_code -= num_direct_distance_codes
                    postfix = distance_code & distance_postfix_mask
                    distance_code >>= distance_postfix_bits
                    nbits = (distance_code >> 1) + 1
                    offset = ((2 + (distance_code & 1)) << nbits) - 4
                    distance_code = num_direct_distance_codes + (
                            (offset + br.read_bits(nbits)) << distance_postfix_bits) + postfix

            # Convert distance code to actual distance by possibly looking up past distances from the ringbuffer
            distance = translate_short_codes(distance_code, dist_rb, dist_rb_idx)
            if distance < 0:
                raise Exception('[brotli_decompress] invalid distance')

            if pos < max_backward_distance and max_distance != max_backward_distance:
                max_distance = pos
            else:
                max_distance = max_backward_distance

            copy_dst = pos

            if distance > max_distance:
                if BrotliDictionary.minDictionaryWordLength <= copy_length <= BrotliDictionary.maxDictionaryWordLength:
                    offset = BrotliDictionary.offsetsByLength[copy_length]
                    word_id = distance - max_distance - 1
                    shift = BrotliDictionary.sizeBitsByLength[copy_length]
                    mask = (1 << shift) - 1
                    word_idx = word_id & mask
                    transform_idx = word_id >> shift
                    offset += word_idx * copy_length
                    if transform_idx < kNumTransforms:
                        length = Transform.transformDictionaryWord(output_buffer, copy_dst, offset, copy_length,
                                                                   transform_idx)
                        copy_dst += length
                        pos += length
                        meta_block_remaining_len -= length
                    else:
                        raise Exception("Invalid backward reference. pos: %s distance: %s len: %s bytes left: %s" % (
                            pos, distance, copy_length, meta_block_remaining_len))
                else:
                    raise Exception("Invalid backward reference. pos: %s distance: %s len: %s bytes left: %s" % (
                        pos, distance, copy_length, meta_block_remaining_len))
            else:
                if distance_code > 0:
                    dist_rb[dist_rb_idx & 3] = distance
                    dist_rb_idx += 1

                if copy_length > meta_block_remaining_len:
                    raise Exception("Invalid backward reference. pos: %s distance: %s len: %s bytes left: %s" % (
                        pos, distance, copy_length, meta_block_remaining_len))

                for j in range(0, copy_length):
                    output_buffer[pos] = output_buffer[pos - distance]
                    pos += 1
                    meta_block_remaining_len -= 1
