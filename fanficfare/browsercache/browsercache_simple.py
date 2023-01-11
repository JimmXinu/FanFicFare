# -*- coding: utf-8 -*-

# Copyright 2022 FanFicFare team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import struct
import hashlib
import glob
import time, datetime
import re
import traceback

from ..six import ensure_binary, ensure_text
from ..exceptions import BrowserCacheException
from .share_open import share_open

from .base_chromium import BaseChromiumCache

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

class SimpleCache(BaseChromiumCache):
    """Class to access data stream in Chrome Simple Cache format cache files"""

    def __init__(self, *args, **kargs):
        """Constructor for SimpleCache"""
        super(SimpleCache,self).__init__(*args, **kargs)
        logger.debug("Using SimpleCache")
        # self.scan_cache_keys()
        # 1/0

    def scan_cache_keys(self):
        """Scan cache entries to save entries in this cache"""
        ## scandir and checking age *before* parsing saves a ton of
        ## hits and time.
        logger.debug("using scandir")
        for entry in os.scandir(self.cache_dir):
            if re.match(r'^[0-9a-fA-F]{16}_[0-9]+$',os.path.basename(entry.path)):
                with share_open(entry.path, "rb") as entry_file:
                    try:
                        file_key = _read_entry_file(entry.path,entry_file)
                        if '/s/14161667/1/' in file_key:
                            (info_size, flags, request_time, response_time, header_size) = _read_meta_headers(entry_file)
                            logger.debug("file_key:%s"%file_key)
                            #logger.debug("response_time:%s"%response_time)
                            logger.debug("Creation Time: %s"%datetime.datetime.fromtimestamp(int(response_time/1000000)-EPOCH_DIFFERENCE))
                    except Exception as e:
                        raise e
                        pass

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

    def get_data_key_impl(self, url, key):
        """
        returns location, entry age(unix epoch), content-encoding and
        raw(compressed) data
        """
        hashkey = _key_hash(key)
        glob_pattern = os.path.join(self.cache_dir, hashkey + '_?')
        # because hash collisions are so rare, this will usually only find zero or one file,
        # so there is no real savings to be had by reading the index file instead of going straight to the entry files
        # logger.debug(glob_pattern)

        ## glob'ing for the collisions avoids ever trying to open
        ## non-existent files.
        for en_fl in glob.glob(glob_pattern):
            try:
                ## --- need to check vs full key due to possible hash
                ## --- collision--can't just do url in key
                with share_open(en_fl, "rb") as entry_file:
                    file_key = _read_entry_file(en_fl,entry_file)
                    if file_key != key:
                        # theoretically, there can be hash collision.
                        continue
                    (info_size, flags, request_time, response_time, header_size) = _read_meta_headers(entry_file)
                    headers = _read_headers(entry_file,header_size)
                    logger.debug("file_key:%s"%file_key)
                    logger.debug("response_time:%s"%response_time)
                    # logger.debug("Creation Time: %s"%datetime.datetime.fromtimestamp(int(response_time/1000000)-EPOCH_DIFFERENCE))
                    logger.debug(headers)
                    ## seen both Location and location
                    location = headers.get('location','')
                    # don't need data when redirect
                    rawdata = None if location else _read_data_from_entry(entry_file)
                    return (
                        location,
                        self.make_age(response_time),
                        headers.get('content-encoding', '').strip().lower(),
                        rawdata)
            except SimpleCacheException:
                pass
        return None

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
        return _read_data_from_entry(entry_file)


def _read_data_from_entry(entry_file):
    """ Read the contents portion (stream 1 data) from the instance's cache entry. Return a byte string """
    entry_file.seek(0, os.SEEK_END)
    _skip_to_start_of_stream(entry_file)
    stream_size = _skip_to_start_of_stream(entry_file)
    ret = entry_file.read(stream_size)
    return ret


def _get_headers(path):
    with share_open(path, "rb") as entry_file:
        (info_size, flags, request_time, response_time, header_size) = _read_meta_headers(entry_file)
        logger.debug("request_time:%s, response_time:%s"%(request_time, response_time))
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
    headers = dict([ (y[0].lower(),y[1]) for y in [s.split(':', 1) for s in strings[1:] if ':' in s]])
    return headers


