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

from __future__ import absolute_import
import os
import struct
import time, datetime

# note share_open (on windows CLI) is implicitly readonly.
from .share_open import share_open
from .chromagnon import SuperFastHash
from .chromagnon.cacheAddress import CacheAddress
from .chromagnon.cacheBlock import CacheBlock
from .chromagnon.cacheData import CacheData
from .chromagnon.cacheEntry import CacheEntry
from .chromagnon.cacheParse import parse
from ..six.moves import range
from ..six import ensure_text

from .base_chromium import BaseChromiumCache

import logging
logger = logging.getLogger(__name__)

INDEX_MAGIC_NUMBER = 0xC103CAC3
BLOCK_MAGIC_NUMBER = 0xC104CAC3

class BlockfileCache(BaseChromiumCache):
    """Class to access data stream in Chrome Disk Blockfile Cache format cache files"""

    def __init__(self, *args, **kargs):
        """Constructor for BlockfileCache"""
        super(BlockfileCache,self).__init__(*args, **kargs)
        self.cacheBlock = CacheBlock(os.path.join(self.cache_dir, "index"))

        # Checking type
        if self.cacheBlock.type != CacheBlock.INDEX:
            raise Exception("Invalid Index File")
        logger.debug("Using BlockfileCache")
        # self.scan_cache_keys()
        # 1/0

    def scan_cache_keys(self):
        """
        Scan index file and cache entries to save entries in this cache.
        Saving uint32 address as key--hashing to find key later proved
        unreliable.
        """
        logger.debug("scan_cache_keys")
        with share_open(os.path.join(self.cache_dir, "index"), 'rb') as index:
            # Skipping Header
            index.seek(92*4)
            self.cache_keys = set()
            for key in range(self.cacheBlock.tableSize):
                raw = struct.unpack('I', index.read(4))[0]
                if raw != 0:
                    ## 0 == unused hash index slot.  I think.
                    cacheaddr = CacheAddress(raw, path=self.cache_dir)
                    # logger.debug("cacheaddr? %s"%cacheaddr)
                    entry = CacheEntry(cacheaddr)
                    # Checking if there is a next item in the bucket because
                    # such entries are not stored in the Index File so they will
                    # be ignored during iterative lookup in the hash table
                    while entry.next != 0:
                        # logger.debug("spinning on entry linked list?")
                        self.add_key_mapping_entry(entry)
                        cacheaddr = CacheAddress(entry.next, path=self.cache_dir)
                        # logger.debug("cacheaddr? %s"%cacheaddr)
                        entry = CacheEntry(cacheaddr)
                    self.add_key_mapping_entry(entry)
    def add_key_mapping_entry(self,entry):
        if '/s/14295569/' in entry.keyToStr():
            logger.debug(entry)

    @staticmethod
    def is_cache_dir(cache_dir):
        """Return True only if a directory is a valid Cache for this class"""
        if not os.path.isdir(cache_dir):
            return False
        index_path = os.path.join(cache_dir, "index")
        if not os.path.isfile(index_path):
            return False
        with share_open(index_path, 'rb') as index_file:
            if struct.unpack('I', index_file.read(4))[0] != INDEX_MAGIC_NUMBER:
                return False
        data0_path = os.path.join(cache_dir, "data_0")
        if not os.path.isfile(data0_path):
            return False
        with share_open(data0_path, 'rb') as data0_file:
            if struct.unpack('I', data0_file.read(4))[0] != BLOCK_MAGIC_NUMBER:
                return False
        return True

    def get_data_key_impl(self, url, key):
        entry = None
        entrys = parse(self.cache_dir,[key])
        logger.debug(entrys)
        for entry in entrys:
            entry_name = entry.keyToStr()
            logger.debug("Name: %s"%entry_name)
            logger.debug("Key: %s"%entry.keyToStr())
            logger.debug("Hash: 0x%08x"%entry.hash)
            logger.debug("Usage Counter: %d"%entry.usageCounter)
            logger.debug("Reuse Counter: %d"%entry.reuseCounter)
            logger.debug("Creation Time: %s"%entry.creationTime)
            # logger.debug("Creation Time: %s"%datetime.datetime.fromtimestamp(int(entry.creationTime/1000000)-EPOCH_DIFFERENCE))
            ## we've been seeing entries without headers.  I suspect
            ## it's the cache being written/page loading while we are
            ## reading it due to not being able to duplicate after
            ## seeing it.  Regardless, return None to allow retry.
            if not hasattr(entry.httpHeader, 'headers'):
                logger.debug("\n\nCache Entry without 'headers'--cache being written?\n\n")
                return None
            if entry_name == key:
                logger.debug("b'location':%s"%entry.httpHeader.headers.get(b'location','(no location)'))
                location = ensure_text(entry.httpHeader.headers.get(b'location',''))
                rawdata = None if location else self.get_raw_data(entry)
                return (
                    location,
                    self.make_age(entry.creationTime),
                    ensure_text(entry.httpHeader.headers.get(b'content-encoding','')),
                    rawdata)
        return None

    def get_raw_data(self,entry):
        for i in range(len(entry.data)):
            # logger.debug("data loop i:%s"%i)
            # logger.debug("entry.data[i].type:%s"%entry.data[i].type)
            if entry.data[i].type == CacheData.UNKNOWN:
                # Extracting data into a file
                data = entry.data[i].data()
                # logger.debug("type = UNKNOWN, data len:%s"%len(data))
                # logger.debug("entry.httpHeader:%s"%entry.httpHeader)
                return data

