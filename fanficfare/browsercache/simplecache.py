import os
import struct
import hashlib
import glob
import time
import re
import traceback
from . import BaseBrowserCache, BrowserCacheException
from ..six import ensure_binary, ensure_text

from .share_open import share_open

import logging
logger = logging.getLogger(__name__)

class SimpleCacheException(BrowserCacheException):
    pass

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

    def __init__(self, *args, **kargs):
        """Constructor for SimpleCache"""
        BaseBrowserCache.__init__(self, *args, **kargs)
        logger.debug("Using SimpleCache")

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
        with share_open(real_index_file, 'rb') as index_file:
            if struct.unpack('QQ', index_file.read(16))[1] != THE_REAL_INDEX_MAGIC_NUMBER:
                return False
        try:
            # logger.debug("\n\nStarting cache check\n\n")
            for en_fl in glob.iglob(os.path.join(cache_dir, '????????????????_[0-9]*')):
                k = _validate_entry_file(en_fl)
                if k is not None:
                    return True
        except SimpleCacheException:
            # raise
            return False
        return False

    def map_cache_keys(self):
        """Scan index file and cache entries to save entries in this cache"""

        # can't use self.age_comp_time because it's set to 1601 epoch.
        if self.age_limit > 0.0 :
            file_comp_time = time.time() - (self.age_limit*3600)
        else:
            file_comp_time = 0

        self.count=0
        if hasattr(os, 'scandir'):
            logger.debug("using scandir")
            for entry in os.scandir(self.cache_dir):
                self.do_cache_key_entry(entry.path,entry.stat(),file_comp_time)
        else:
            logger.debug("using listdir")
            for en_fl in os.listdir(self.cache_dir):
                en_path = os.path.join(self.cache_dir,en_fl)
                self.do_cache_key_entry(en_path,os.stat(en_path),file_comp_time)
        logger.debug("Read %s entries"%self.count)

    def do_cache_key_entry(self,path,stats,file_comp_time):
        ## there are some other files in simple cache dir.
        # logger.debug("%s: %s > %s"%(os.path.basename(path),stats.st_mtime,file_comp_time))
        if( re.match(r'^[0-9a-fA-F]{16}_[0-9]+$',os.path.basename(path))
            and stats.st_mtime > file_comp_time ):
            try:
                (cache_url,created) = _get_entry_file_created(path)
                if cache_url:
                    self.add_key_mapping(cache_url,path,created)
                    self.count+=1
            except Exception as e:
                logger.warning("Cache file %s failed to load, skipping."%path)
                logger.debug(traceback.format_exc())

    # key == filename for simple cache
    def get_data_key(self, key):
        headers = _get_headers(key)
        encoding = headers.get('content-encoding', '').strip().lower()
        try:
            return self.decompress(encoding,_get_data_from_entry_file(key))
        except:
            # logger.debug("\n\n%s\n\n"%key)
            raise

    # def get_data_url(self, url):
    #     """ Return decoded data for specified key (a URL string) or None """
    #     glob_pattern = os.path.join(self.cache_dir, _key_hash(url) + '_?')
    #     # because hash collisions are so rare, this will usually only find zero or one file,
    #     # so there is no real savings to be had by reading the index file instead of going straight to the entry files
    #     url = ensure_text(url)
    #     for en_fl in glob.glob(glob_pattern):
    #         try:
    #             file_key = _validate_entry_file(en_fl)
    #             if file_key == url:
    #                 return self.get_data_key(en_fl)
    #         except SimpleCacheException:
    #             pass
    #     return None

# Here come the utility functions for the class

import codecs
def _key_hash(key):
    """Compute hash of key as used to generate name of cache entry file"""
    # py2 lacks convenient .hex() method on bytes
    key = ensure_binary(key)
    return ensure_text(codecs.encode(hashlib.sha1(key).digest()[7::-1],'hex'))
    # return hashlib.sha1(key).digest()[7::-1].hex()


def _get_entry_file_created(path):
    with share_open(path, "rb") as entry_file:
        key = _read_entry_file(path,entry_file)
        (info_size, flags, request_time, response_time, header_size) = _read_meta_headers(entry_file)
        # logger.debug("\nkey:%s\n request_time:%s\nresponse_time:%s"%(key,request_time, response_time))
        return (key, response_time)

def _validate_entry_file(path):
    with share_open(path, "rb") as entry_file:
        return _read_entry_file(path,entry_file)

def _read_entry_file(path,entry_file):
    """Validate that a file is a cache entry file, return the URL (key) if valid"""
    # read from path into SimpleFileHeader, use key_length field to determine size of key, return key as byte string
    shformat = struct.Struct('<QLLLL')
    shformat_size = shformat.size
    data = entry_file.read(shformat_size)
    (magic, version, key_length, key_hash, padding) = shformat.unpack(data)
    if magic != ENTRY_MAGIC_NUMBER:
        return None  # path is not a cache entry file, wrong magic number
    key = entry_file.read(key_length)
    if _key_hash(key) != os.path.basename(path).split('_')[0]:
        return None  # key in file does not match the hash, something is wrong
    return key.decode('utf-8')


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
    with share_open(path, "rb") as entry_file:
        entry_file.seek(0, os.SEEK_END)
        _skip_to_start_of_stream(entry_file)
        stream_size = _skip_to_start_of_stream(entry_file)
        ret = entry_file.read(stream_size)
    return ret


def _get_headers(path):
    with share_open(path, "rb") as entry_file:
        (info_size, flags, request_time, response_time, header_size) = _read_meta_headers(entry_file)
        return _read_headers(entry_file,header_size)


def _read_meta_headers(entry_file):
    """ Read the HTTP header (stream 0 data) from a cache entry file """
    entry_file.seek(0, os.SEEK_END)
    _skip_to_start_of_stream(entry_file)
    # read stream 0 meta header:
    #   uint32 info_size, uint32 flags, uint64 request_time, uint64 response_time, uint32 header_size
    data = entry_file.read(META_HEADER_SIZE)
    (info_size, flags, request_time, response_time, header_size) = META_HEADER.unpack(data)
    return (info_size, flags, request_time, response_time, header_size)


def _read_headers(entry_file,header_size):
    """ Read the HTTP header (stream 0 data) from a cache entry file """
    # read header_size bytes to get the raw bytes of the HTTP headers
    # parse the raw bytes into a HttpHeader structure:
    # It is a series of null terminated strings, first is status code,e.g., "HTTP/1.1 200"
    # the rest are name:value pairs used to populate the headers dict.
    strings = entry_file.read(header_size).decode('utf-8').split('\0')
    headers = dict(s.split(':', 1) for s in strings[1:] if ':' in s)
    return headers


