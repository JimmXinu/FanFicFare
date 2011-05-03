# -*- coding: utf-8 -*-

import os, sys, glob
from os.path import dirname, basename, normpath
import logging
import urlparse as up

## A few exceptions for different things for adapters

class FailedToDownload(Exception):
    def __init__(self,error):
        self.error=error

    def __str__(self):
        return self.error

class InvalidStoryURL(Exception):
    def __init__(self,url,domain,example):
        self.url=url
        self.domain=domain
        self.example=example
        
    def __str__(self):
        return "Bad Story URL: %s\nFor site: %s\nExample: %s" % (self.url, self.domain, self.example)

class FailedToLogin(Exception):
    def __init__(self,url,username):
        self.url=url
        self.username=username
        
    def __str__(self):
        return "Failed to Login for URL: %s with username: %s" % (self.url, self.username)

class StoryDoesNotExist(Exception):
    def __init__(self,url):
        self.url=url
        
    def __str__(self):
        return "Story Does Not Exit: " + self.url

class UnknownSite(Exception):
    def __init__(self,url,supported_sites_list):
        self.url=url
        self.supported_sites_list=supported_sites_list

    def __str__(self):
        return "Unknown Site("+self.url+").  Supported sites: "+", ".join(self.supported_sites_list)

## This bit of complexity allows adapters to be added by just adding
## the source file.  It eliminates the long if/else clauses we used to
## need to pick out the adapter.
    
## List of registered site adapters.
    
__class_list = []

def _register_handler(cls):
    __class_list.append(cls)

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
    __import__(basename(file)[:-3])    

del sys.path[0]
