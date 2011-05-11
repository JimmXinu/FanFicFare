# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team
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

import os, sys, glob
from os.path import dirname, basename, normpath
import logging
import urlparse as up

import fanficdownloader.exceptions as exceptions

## This bit of complexity allows adapters to be added by just adding
## the source file.  It eliminates the long if/else clauses we used to
## need to pick out the adapter.
    
## List of registered site adapters.
    
__class_list = []

def getAdapter(config,url):
    parsedUrl = up.urlparse(url)
    logging.debug("site:"+parsedUrl.netloc)
    for cls in __class_list:
        if cls.matchesSite(parsedUrl.netloc):
            adapter = cls(config,url) # raises InvalidStoryURL
            return adapter
    # No adapter found.
    raise exceptions.UnknownSite( url, [cls.getSiteDomain() for cls in __class_list] )

## Automatically import each adapter_*.py file.
## Each implement getClass() to their class

filelist = glob.glob(dirname(__file__)+'/adapter_*.py')
sys.path.insert(0,normpath(dirname(__file__)))

for file in filelist:
    #print "file: "+basename(file)[:-3]
    module = __import__(basename(file)[:-3])
    __class_list.append(module.getClass())

del sys.path[0]
