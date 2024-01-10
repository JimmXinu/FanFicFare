## Prior version had issues with giving wrong values once in a while.
## Replace rather than try to troubleshoot bit processing in python.

## This code is from:
## https://github.com/vperron/python-superfasthash
## under http://www.gnu.org/licenses/lgpl-2.1.txt

class uint32_t(int):
    def __rshift__(self, other):
        return uint32_t(int.__rshift__(self, other) & ((1 << 32) - 1))
    def __lshift__(self, other):
        return uint32_t(int.__lshift__(self, other) & ((1 << 32) - 1))
    def __add__(self, other):
        return uint32_t(int.__add__(self, other) & ((1 << 32) - 1))
    def __xor__(self, other):
        return uint32_t(int.__xor__(self, other) & ((1 << 32) - 1))

def __get_16_bits(ptr):
    return ord(ptr[0]) + (ord(ptr[1]) << 8)

def superFastHash(data, seed=None):
    """
    Stream-adapted SuperFastHash algorithm from Paul Hsieh,
    http://www.azillionmonkeys.com/qed/hash.html
    LGPLv2.1
    Python version with no dependencies.
    Victor Perron <victor@iso3103.net>
    """

    if(data == None or len(data) == 0): return 0

    len_ = len(data)
    rem = len_ & 3
    len_ >>= 2

    if seed is None:
        seed = len(data)
    hash_ = uint32_t(seed)

    # Main loop
    while len_ > 0:
        len_  -= 1
        hash_ += __get_16_bits(data)
        tmp    = (__get_16_bits(data[2:]) << 11) ^ hash_
        hash_  = (hash_ << 16) ^ tmp
        data   = data[4:]
        hash_ += (hash_ >> 11)

    # Handle end cases
    if rem == 3:
        hash_ += __get_16_bits (data)
        hash_ ^= (hash_ << 16)
        hash_ ^= (ord(data[2]) << 18)
        hash_ += (hash_ >> 11)
    elif rem == 2:
        hash_ += __get_16_bits (data)
        hash_ ^= (hash_ << 11)
        hash_ += (hash_ >> 17)
    elif rem == 1:
        hash_ += ord(data[0])
        hash_ ^= (hash_ << 10)
        hash_ += (hash_ >> 1)

    # Force "avalanching" of final 127 bits
    hash_ ^= (hash_ << 3)
    hash_ += (hash_ >> 5)
    hash_ ^= (hash_ << 4)
    hash_ += (hash_ >> 17)
    hash_ ^= (hash_ << 25)
    hash_ += (hash_ >> 6)

    return hash_
