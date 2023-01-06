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

## Cache parsing code lifted from:
## https://github.com/JamesHabben/FirefoxCache2

import os
import struct
import hashlib
import glob
import datetime
import time

from . import BaseBrowserCache
from ..six import ensure_text
from ..six.moves.urllib.parse import urlparse
from ..exceptions import BrowserCacheException
from .share_open import share_open

import logging
logger = logging.getLogger(__name__)

class FirefoxCache2(BaseBrowserCache):
    """Class to access data stream in Firefox Cache2 format cache files"""

    def __init__(self, *args, **kargs):
        """Constructor for FirefoxCache2"""
        super(FirefoxCache2,self).__init__(*args, **kargs)
        logger.debug("Using FirefoxCache2")
        ## save the difference between utc and local.
        self.utc_offset = datetime.datetime.now() - datetime.datetime.utcnow()
        # self.scan_cache_keys()
        # 1/0

    def scan_cache_keys(self):
        """Scan cache entries to save entries in this cache"""
        ## scandir and checking age *before* parsing saves a ton of
        ## hits and time.
        logger.debug("using scandir")
        for entry in os.scandir(os.path.join(self.cache_dir,'entries')):
            if stats.st_mtime > time.time() - 3600: # last hour only
                with share_open(entry.path, "rb") as entry_file:
                    metadata = _read_entry_headers(entry_file)
                    if 'fanfiktion.de/s/' in metadata['key']:
                        logger.debug("%s->%s"%(metadata['key'],metadata['key_hash']))

    @staticmethod
    def is_cache_dir(cache_dir):
        """Return True only if a directory is a valid Cache for this class"""
        # logger.debug("\n\n1Starting cache check\n\n")
        if not os.path.isdir(cache_dir):
            return False
        ## check at least one entry file exists.
        for en_fl in glob.iglob(os.path.join(cache_dir, 'entries', '????????????????????????????????????????')):
            # logger.debug(en_fl)
            k = _validate_entry_file(en_fl)
            if k is not None:
                return True
        return False

    def make_keys(self,url):
        (domain, url) = self.make_key_parts(url)
        ## WebToEpub appears to leave just
        ## ':'+url
        return [ 'O^partitionKey=%28https%2C'+domain+'%29,:'+url,
                 ':'+url
                 ]

    def make_key_path(self,key):
        hashkey = hashlib.sha1(key.encode('utf8')).hexdigest().upper()
        # logger.debug(hashkey)
        fullkey = os.path.join(self.cache_dir, 'entries', hashkey)
        # logger.debug(fullkey)
        return fullkey

    def get_data_key_impl(self, url, key):
        key_path = self.make_key_path(key)
        if os.path.isfile(key_path): # share_open()'s failure for non-existent is some win error.
            with share_open(key_path, "rb") as entry_file:
                metadata = _read_entry_headers(entry_file)
                # import json
                # logger.debug(json.dumps(metadata, sort_keys=True,
                #                 indent=2, separators=(',', ':')))
                # redirect when Location header
                headers  = metadata.get('response-headers',{})
                ## seen both Location and location
                location = headers.get('location','')
                entry_file.seek(0)
                rawdata = None if location else entry_file.read(metadata['readsize'])
                return (
                    location,
                    # metadata['lastModInt'] and stats.st_mtime both update on fails(?!)
                    time.mktime((datetime.datetime.strptime(metadata.get('response-headers',{}).get('date', 'Wed, 31 Dec 1969 18:00:00 GMT'),
                                               "%a, %d %b %Y %H:%M:%S GMT")+self.utc_offset).timetuple()),
                    metadata.get('response-headers',{}).get('content-encoding', '').strip().lower(),
                    rawdata)
        return None

def _validate_entry_file(path):
    with share_open(path, "rb") as entry_file:
        metadata = _read_entry_headers(entry_file)
        # import json
        # logger.debug(json.dumps(metadata, sort_keys=True,
        #                         indent=2, separators=(',', ':')))
        if metadata['key_hash'] != os.path.basename(path):
            return None  # key in file does not match the hash, something is wrong
    return metadata['key']

def _read_entry_headers(entry_file):
    chunkSize = 256 * 1024
    retval = {}

    ## seek to & read last 4 bytes,
    entry_file.seek(-4, os.SEEK_END)
    metaStart = struct.unpack('>I', entry_file.read(4))[0]
    # logger.debug("metaStart:%s"%metaStart)

    ## skipping a variably length hash--depends on how many 'chunks'
    ## long the data is
    numHashChunks = metaStart // chunkSize # int division
    # logger.debug("numHashChunks:%s"%numHashChunks)
    # logger.debug("metaStart %% chunkSize:%s"%(metaStart % chunkSize))
    if metaStart % chunkSize :
        numHashChunks += 1
    # logger.debug("numHashChunks:%s"%numHashChunks)
    # logger.debug(4 + numHashChunks * 2)

    startmeta = int(metaStart + 4 + numHashChunks * 2)
    # logger.debug("startmeta:%s"%startmeta)
    entry_file.seek(startmeta, os.SEEK_SET)
    # logger.debug("Reading meta starting at:%s"%entry_file.tell())
    version = struct.unpack('>I', entry_file.read(4))[0]
    #if version > 1 :
        # TODO quit with error
    retval['fetchCount'] = struct.unpack('>I', entry_file.read(4))[0]
    retval['lastFetchInt'] = struct.unpack('>I', entry_file.read(4))[0]
    retval['lastModInt'] = struct.unpack('>I', entry_file.read(4))[0]
    retval['frecency'] = struct.unpack('>I', entry_file.read(4))[0]
    retval['expireInt'] = struct.unpack('>I', entry_file.read(4))[0]
    keySize = struct.unpack('>I', entry_file.read(4))[0]
    retval['flags'] = struct.unpack('>I', entry_file.read(4))[0] if version >= 2 else 0
    key = entry_file.read(keySize)
    retval['key']=ensure_text(key)
    # logger.debug("key:%s"%retval['key'])
    retval['key_hash'] = hashlib.sha1(key).hexdigest().upper()

    # logger.debug("Reading meta done at:%s"%entry_file.tell())

    # logger.debug("*more* metadata")
    moremetadata = entry_file.read()[:-6]
    # not entirely sure why there's a couple extra bytes in addition
    # to the metaStart

    ## \x00 separated tuples of name\x00value\x00name\x00value...
    moremetalist = moremetadata.split(b'\x00')
    # logger.debug(len(moremetalist))
    moremetadict = {ensure_text(item) : ensure_text(moremetalist[index+2]) for index, item in enumerate(moremetalist[1:]) if index % 2 == 0}
    ## don't know what security-info contains, just that it's big.
    moremetadict.pop('security-info',None)
    ## add to retval
    retval.update(moremetadict)
    ## separate out response headers.
    # if 'response-head' in moremetadict:
    #     logger.debug("Status:%s"%moremetadict['response-head'].split('\r\n')[0])
    # else:
    #     logger.debug("Status:(no response-head)")
    if 'original-response-headers' in moremetadict:
        retval['response-headers'] = dict([ (y[0].lower(),y[1]) for y in [ x.split(': ',1) for x in moremetadict['original-response-headers'].split('\r\n') if x ]])
    # logger.debug(b"\n==>".join().decode('utf-8'))

    if 'alt-data' in moremetadict:
        # for some reason, some entries are bigger than the file
        # size. The only place I've found the real file size is
        # alt-data.  Seems to affect ~3%
        # alt-data=1;77941,javas...
        altdata = moremetadict['alt-data']
        retval['readsize'] = int(altdata[2:altdata.index(',')])
        # logger.debug("alt-size:%s"%retval['readsize'])
    else:
        # note that there are files with metaStart == 0
        retval['readsize'] = metaStart
    return retval
