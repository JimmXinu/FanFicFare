# -*- coding: utf-8 -*-

import os, sys, glob
from os.path import dirname, basename, normpath
import logging
import urlparse as up

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
    raise UnknownSite( url, (cls.getSiteDomain() for cls in __class_list) )

## Automatically import each adapter_*.py file.
## Each must call _register_handler() with their class to be
## registered.

filelist = glob.glob(dirname(__file__)+'/adapter_*.py')
sys.path.insert(0,normpath(dirname(__file__)))

for file in filelist:
    #print "file: "+basename(file)[:-3]
    module = __import__(basename(file)[:-3])
    __class_list.append(module.getClass())

del sys.path[0]
