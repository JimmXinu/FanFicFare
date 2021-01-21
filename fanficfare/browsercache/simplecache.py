import os
import struct
import hashlib
import gzip
import zlib
import glob
from typing import cast, Tuple
from . import BaseBrowserCache, BrowserCacheException


class SimpleCacheException(BrowserCacheException):
    pass


try:
    from brotli import decompress as brotli_decompress
except ImportError:
    # Calibre doesn't include brotli, so use packaged brotlipython
    # which is waaaay slower, but pure python.
    from brotlipython import brotlidec

    def brotli_decompress(inbuf):
        # wants the output, too, but returns it
        return brotlidec(inbuf, [])

SIMPLE_EOF = struct.Struct('<QLLLL')   # magic_number, flags, crc32, stream_size, padding
SIMPLE_EOF_SIZE = SIMPLE_EOF.size
FLAG_HAS_SHA256 = 2
META_HEADER = struct.Struct('<LLQQL')
META_HEADER_SIZE = META_HEADER.size
ENTRY_MAGIC_NUMBER = 0xfcfb6d1ba7725c30
EOF_MAGIC_NUMBER = 0xf4fa6f45970d41d8
THE_REAL_INDEX_MAGIC_NUMBER = 0x656e74657220796f


class SimpleCache(BaseBrowserCache):
    """Class to access data stream in Chrome Simple Cache format cache files"""

    def __init__(self, cache_dir=None):
        """Constructor for SimpleCache"""
        super().__init__(cache_dir)
        if not self.is_cache_dir(cache_dir):
            raise SimpleCacheException("Directory does not contain a Chrome Simple Cache: '%s'" % cache_dir)

    @staticmethod
    def is_cache_dir(cache_dir):
        """Return True only if a directory is a valid Cache for this class"""
        if not os.path.isdir(cache_dir):
            return False
        index_file = os.path.join(cache_dir, "index")
        if not (os.path.isfile(index_file) and os.path.getsize(index_file) == 24):
            return False
        real_index_file = os.path.join(cache_dir, "index-dir", "the-real-index")
        if not os.path.isfile(real_index_file):
            return False
        with open(real_index_file, 'rb') as index_file:
            if struct.unpack('QQ', index_file.read(16))[1] != THE_REAL_INDEX_MAGIC_NUMBER:
                return False
        try:
            for en_fl in glob.iglob(os.path.join(cache_dir, '????????????????_?')):
                _validate_entry_file(en_fl)
                return True
        except SimpleCacheException:
            return False
        return False

    def get_data(self, url):
        """ Return decoded data for specified key (a URL string) or None """
        if isinstance(url, str):
            url = url.encode('utf-8')
        glob_pattern = os.path.join(self.cache_dir, _key_hash(url) + '_?')
        # because hash collisions are so rare, this will usually only find zero or one file,
        # so there is no real savings to be had by reading the index file instead of going straight to the entry files
        for en_fl in glob.glob(glob_pattern):
            try:
                file_key = _validate_entry_file(en_fl)
                if file_key == url:
                    return _get_decoded_data(en_fl)
            except SimpleCacheException:
                pass
        return None

# Here come the utility functions for the class


def _key_hash(key):
    """Compute hash of key as used to generate name of cache entry file"""
    return hashlib.sha1(key).digest()[7::-1].hex()


def _validate_entry_file(path):
    """Validate that a file is a cache entry file, return the URL (key) if valid"""
    # read from path into SimpleFileHeader, use key_length field to determine size of key, return key as byte string
    shformat = struct.Struct('<QLLLL')
    shformat_size = shformat.size
    with open(path, "rb") as entry_file:
        data = entry_file.read(shformat_size)
        (magic, version, key_length, key_hash, padding) = shformat.unpack(data)
        if magic != ENTRY_MAGIC_NUMBER:
            raise SimpleCacheException("Supposed cache entry file did not start with correct magic number: "
                                       "'%s'" % path)
        key = entry_file.read(key_length)
        if _key_hash(key) != os.path.basename(path).split('_')[0]:
            raise SimpleCacheException("Cache entry file name '%s' does not match hash of key '%s'" %
                                       os.path.basename(path), key)
    return key


def _skip_to_start_of_stream(entry_file):
    """Assuming reader is at end of a stream back up to beginning of stream, returning size of data in stream"""
    entry_file.seek(-SIMPLE_EOF_SIZE, os.SEEK_CUR)
    data = entry_file.read(SIMPLE_EOF_SIZE)
    (magic, flags, crc32, stream_size, padding) = SIMPLE_EOF.unpack(data)
    if magic != EOF_MAGIC_NUMBER:
        raise SimpleCacheException("Supposed cache entry file did not end with EOF header with correct magic "
                                   "number: '%s'" % entry_file.name)
    seek_back = stream_size + SIMPLE_EOF_SIZE
    if flags & FLAG_HAS_SHA256:
        seek_back += 32
    entry_file.seek(-seek_back, os.SEEK_CUR)
    return stream_size


def _get_data_from_entry_file(path):
    """ Read the contents portion (stream 1 data) from the instance's cache entry file. Return a byte string """
    with open(path, "rb") as entry_file:
        entry_file.seek(0, os.SEEK_END)
        _skip_to_start_of_stream(entry_file)
        stream_size = _skip_to_start_of_stream(entry_file)
        ret = entry_file.read(stream_size)
    return ret


def _get_headers(path):
    """ Read the HTTP header (stream 0 data) from a cache entry file """
    with open(path, "rb") as entry_file:
        entry_file.seek(0, os.SEEK_END)
        _skip_to_start_of_stream(entry_file)
        # read stream 0 meta header:
        #   uint32 info_size, uint32 flags, uint64 request_time, uint64 response_time, uint32 header_size
        data = entry_file.read(META_HEADER_SIZE)
        (info_size, flags, request_time, response_time, header_size) = META_HEADER.unpack(data)
        # read header_size bytes to get the raw bytes of the HTTP headers
        # parse the raw bytes into a HttpHeader structure:
        # It is a series of null terminated strings, first is status code,e.g., "HTTP/1.1 200"
        # the rest are name:value pairs used to populate the headers dict.
        strings: list[str] = entry_file.read(header_size).decode('utf-8').split('\0')
        headers = dict(cast(Tuple[str, str], s.split(':', 1)) for s in strings[1:] if ':' in s)
    return headers


def _get_decoded_data(path):
    """ Read and decompress if necessary data from a cache entry file. Returns a byte string """
    headers = _get_headers(path)
    encoding = headers.get('content-encoding', '').strip().lower()
    data = _get_data_from_entry_file(path)
    if encoding == 'gzip':
        return gzip.decompress(data)
    elif encoding == 'br':
        return brotli_decompress(data)
    elif encoding == 'deflate':
        return zlib.decompress(data)
    return data
