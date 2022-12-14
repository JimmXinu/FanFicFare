from __future__ import absolute_import
from __future__ import print_function
import os
import struct
import sys

# note share_open (on windows CLI) is implicitly readonly.
from .share_open import share_open
from .chromagnon import SuperFastHash
from .chromagnon.cacheAddress import CacheAddress
from .chromagnon.cacheBlock import CacheBlock
from .chromagnon.cacheData import CacheData
from .chromagnon.cacheEntry import CacheEntry
from ..six.moves import range
from ..six import ensure_binary, ensure_text

from . import BrowserCacheException, BaseBrowserCache

import logging
logger = logging.getLogger(__name__)

class BlockfileCacheException(BrowserCacheException):
    pass

INDEX_MAGIC_NUMBER = 0xC103CAC3
BLOCK_MAGIC_NUMBER = 0xC104CAC3


class BlockfileCache(BaseBrowserCache):
    """Class to access data stream in Chrome Disk Blockfile Cache format cache files"""

    def __init__(self, *args, **kargs):
        """Constructor for BlockfileCache"""
        super(BlockfileCache,self).__init__(*args, **kargs)
        self.cacheBlock = CacheBlock(os.path.join(self.cache_dir, "index"))

        # Checking type
        if self.cacheBlock.type != CacheBlock.INDEX:
            raise Exception("Invalid Index File")
        logger.debug("Using BlockfileCache")

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

    def map_cache_keys(self):
        """
        Scan index file and cache entries to save entries in this cache.

        Saving uint32 address as key--hashing to find key later proved
        unreliable.
        """
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
        self.add_key_mapping(entry.keyToStr(),
                             entry.address.addr,
                             entry.creationTime)

    def get_data_key(self,addr):
        """ Return decoded data for specified key (a binary addr) or None """
        entry = self.get_cache_entry(addr)
        # logger.debug("get_data_key(%s)->%s"%(addr,entry))
        if entry:
            # logger.debug("has entry")
            for i in range(len(entry.data)):
                # logger.debug("data loop i:%s"%i)
                # logger.debug("entry.data[i].type:%s"%entry.data[i].type)
                if entry.data[i].type == CacheData.UNKNOWN:
                    # Extracting data into a file
                    data = entry.data[i].data()
                    # logger.debug("type = UNKNOWN, data len:%s"%len(data))
                    # logger.debug("entry.httpHeader:%s"%entry.httpHeader)
                    if entry.httpHeader != None and \
                       b'content-encoding' in entry.httpHeader.headers:
                        encoding = entry.httpHeader.headers.get(b'content-encoding','')
                        data = self.decompress(encoding,data)
                    return data
        return None

    def get_cache_entry(self,addr):
        cacheaddr = CacheAddress(addr, path=self.cache_dir)
        # logger.debug("cacheaddr? %s"%cacheaddr)
        entry = CacheEntry(cacheaddr)
        # logger.debug("entry? %s"%entry)
        return entry
