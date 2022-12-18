# -*- coding: utf-8 -*-

# Copyright 2021 FanFicFare team
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

'''
On windows, simple built-in open() fails on cache files due to a
lock--even when opening read-only.

Need to jump through various hoops to *really* open
read-only--different hoops in CLI and Calibre, too.
'''

import logging
logger = logging.getLogger(__name__)

## CLI version:

import sys
_plat = sys.platform.lower()
iswindows = 'win32' in _plat or 'win64' in _plat

if iswindows:
    try:
        ## Calibre has already had to solve the same problem.
        from calibre.utils.shared_file import share_open
    except ImportError:
        ## not stealing calibre's version because read-only is all we
        ## need.
        import os
        import win32file
        import msvcrt

        def share_open(path,*args,**kargs):
            logger.debug("share_open(%s)"%path)
            # does need all three file share flags.
            handle = win32file.CreateFile(path,
                                          win32file.GENERIC_READ,
                                          win32file.FILE_SHARE_DELETE |
                                          win32file.FILE_SHARE_READ |
                                          win32file.FILE_SHARE_WRITE,
                                          None,
                                          win32file.OPEN_EXISTING,
                                          0,
                                          None)

            # detach the handle
            detached_handle = handle.Detach()

            # get a file descriptor associated to the handle
            file_descriptor = msvcrt.open_osfhandle(detached_handle, os.O_RDONLY)

            ## these can be called *before* the with open read, so
            ## clearly they don't matter to that and I don't want to
            ## risk leaking file descriptors.
            handle.close()
            win32file.CloseHandle(handle)

            # open the file descriptor
            # this will still allow for "with share_open():"
            return open(file_descriptor,*args,**kargs)
else:
    ## use normal open.
    share_open = open
