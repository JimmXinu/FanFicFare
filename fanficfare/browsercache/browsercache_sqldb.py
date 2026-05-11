# -*- coding: utf-8 -*-

# Copyright 2026 FanFicFare team
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

## XXX
##
## This doesn't work with Chrome running -- we can't open the DB file
## due to permissions (on windows at least).
##
## See:
## https://github.com/JimmXinu/FanFicFare/issues/1341
## https://chromium.googlesource.com/experimental/chromium/src/+/HEAD/net/disk_cache/sql
##
## Currently, this cache type raises an exception if sqldb0 found and
## cannot be opened.
##
## I do not consider this impl to be 100% at this time, but I also
## don't expect it to be used.
##
## XXX

from __future__ import absolute_import
import os
import apsw
import ctypes
import glob

from ..exceptions import BrowserCacheException

# note share_open (on windows CLI) is implicitly readonly.
from .share_open import share_open
from .base_chromium import BaseChromiumCache
from .chromagnon import SuperFastHash

import logging
logger = logging.getLogger(__name__)

class SqldbCache(BaseChromiumCache):
    """Class to access data stream in Chrome Disk Sqldb Cache format cache files"""

    def __init__(self, *args, **kargs):
        """Constructor for SqldbCache"""
        super(SqldbCache,self).__init__(*args, **kargs)
        logger.debug("Using SqldbCache")

    # def scan_cache_keys(self):
        ## XXX will impl a scan if and when needed.  It's a lot easier
        ## to peek inside an sqlite

    @staticmethod
    def is_cache_dir(cache_dir):
        """Return True only if a directory is a valid Cache for this class"""
        if not os.path.isdir(cache_dir):
            logger.debug("Cache dir not found")
            return False
        index_path = os.path.join(cache_dir, "index")
        if not os.path.isfile(index_path):
            logger.debug("index file not found")
            return False
        sqldb0_path = os.path.join(cache_dir, "sqldb0")
        if not os.path.isfile(sqldb0_path):
            logger.debug("sqldb0 file not found")
            return False
        else:
            ## XXX Change if we ever figure out how to read sqlite
            ## while browser is running.
            logger.debug("sqldb0 file found, test whether it can be read.")
            try:
                testfile = share_open(sqldb0_path, 'rb')
                testfile.close()
                return True
            except:
                # did find sqldb0, raise an exception explaing
                raise BrowserCacheException("FanFicFare cannot use Chrome's SQL-based disk cache while browser is running.  See https://github.com/JimmXinu/FanFicFare/issues/1341#issuecomment-4413556330")
        ## XXX check schema of db?
        return True

    def get_data_key_impl(self, url, key):
        """
        returns location, entry age(unix epoch), content-encoding and
        raw(compressed) data
        """
        location, age, encoding, data = '', None, None, None
        qstr = 'SELECT last_used, head, blob FROM resources as r join blobs as b on b.res_id=r.res_id where cache_key_hash=?'
        cache_key_hash = _key_hash(key)
        logger.debug("           key:%s"%key)
        logger.debug("cache_key_hash:%s"%cache_key_hash)
        ## XXX worth optimizing to keep sql conn open?
        ## XXX Is hash key collision an issue?
        ## XXX What do the other columns (body_end, start, end) mean?

        from ..six.moves.urllib.request import pathname2url
        shareopenVFS = ShareOpenVFS()
        logger.debug("VFS available %s"% apsw.vfs_names())

        for filename in glob.glob(os.path.join(self.cache_dir, "sqldb*")):
            logger.debug(filename)
            with apsw.Connection("file:"+filename+"?immutable=1",
                                 flags=apsw.SQLITE_OPEN_READONLY | apsw.SQLITE_OPEN_URI,
                                 vfs=shareopenVFS.vfs_name
                                 ) as db:
                logger.debug("db flags:%xd"%db.open_flags)
                logger.debug("db vfs:%s"%db.open_vfs)
                for last, head, blob in db.execute(qstr,[cache_key_hash]):

                    row_age = self.make_age(last)
                    if age and row_age < age:
                        logger.debug("skipping an older row for same hash")
                        break

                    age = row_age
                    logger.debug("age from last_used:%s"%age)

                    ## cheesy way to pull out the http headers, inspired
                    ## by equal cheese in chromagnon/cacheData.py.  Only
                    ## actually care about location &content-encoding,
                    ## ignore the rest.
                    head = head[head.index(b'HTTP'):]
                    head = head[:head.index(b'\x00\x00')]
                    # logger.debug(head)
                    for line in head.split(b'\0'):
                        logger.debug(line)
                        if b'content-encoding' in line.lower():
                            encoding = line.split(b':')[1].strip().lower()
                            logger.debug("encoding from header:%s"%encoding)
                        if b'location' in line.lower():
                            location = b':'.join(line.split(b':')[1:]).strip()
                            logger.debug("location from header:%s"%encoding)
                        ## XXX might need entry age from header, too.
                        ## Hoping db last_used is equiv.
                    data = blob
        if data:
            return (location, age, encoding, data)
        else:
            return None

## calculate SuperFashHash, but the sql saved it signed.
def _key_hash(key):
    unsigned_hash = SuperFastHash.superFastHash(key)
    number = unsigned_hash & 0xFFFFFFFF
    return ctypes.c_int32(number).value


class ShareOpenVFS(apsw.VFS):
    def __init__(self):
        self.vfs_name = 'shareopen'
        super().__init__(name=self.vfs_name, base='')

    def xAccess(self, pathname, flags):
        return True

    def xFullPathname(self, filename):
        return filename

    def xDelete(self, filename, syncdir):
        logger.debug("xDelete NOT DELETING")
        pass

    def xOpen(self, name, flags):
        return ShareOpenVFSFile(name, flags)

class ShareOpenVFSFile:
    def __init__(self, name, flags):
        self.filename = name.filename() if isinstance(name, apsw.URIFilename) else name
        self.filename = os.path.normpath(self.filename)
        logger.debug("Doing share open(%s)"%self.filename)
        self.file = share_open(self.filename, 'rb')

    def xRead(self, amount, offset):
        self.file.seek(offset, 0)
        return self.file.read(amount)

    def xFileSize(self):
        return os.stat(self.filename).st_size

    def xClose(self):
        self.file.close()

    def xSectorSize(self):
        return 0

    def xFileControl(self, *args):
        return False

    def xCheckReservedLock(self):
        return False

    def xLock(self, level):
        pass

    def xUnlock(self, level):
        pass

    def xSync(self, flags):
        return True

    def xTruncate(self, newsize):
        logger.debug("xTruncate NOT TRUNCING")
        pass

    def xWrite(self, data, offset):
        logger.debug("xWrite NOT WRITING")
        pass
