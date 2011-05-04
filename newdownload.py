# -*- coding: utf-8 -*-

import logging
logging.basicConfig(level=logging.DEBUG,format="%(levelname)s:%(filename)s(%(lineno)d):%(message)s")

import sys, os
import getpass

from fanficdownloader import adapters,writers

import ConfigParser

config = ConfigParser.ConfigParser()

logging.debug('reading defaults.ini config file, if present')
config.read('defaults.ini')
logging.debug('reading personal.ini config file, if present')
config.read('personal.ini')

def writeStory(adapter,writeformat):
    writer = writers.getWriter(writeformat,config,adapter.getStory())
    writer.writeStory()
    del writer

try:
    adapter = adapters.getAdapter(config,sys.argv[1])
        
    try:
        print adapter.getStory()
    except adapters.FailedToLogin, ftl:
        print "Login Failed, Need Username/Password."
        sys.stdout.write("Username: ")
        adapter.username = sys.stdin.readline().strip()
        adapter.password = getpass.getpass(prompt='Password: ')
        #print("Login: `%s`, Password: `%s`" % (adapter.username, adapter.password))
        print adapter.getStory()

    writeStory(adapter,"epub")
    writeStory(adapter,"html")
    writeStory(adapter,"txt")
    del adapter

except adapters.InvalidStoryURL, isu:
    print isu
except adapters.StoryDoesNotExist, dne:
    print dne
except adapters.UnknownSite, us:
    print us
