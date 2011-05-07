# -*- coding: utf-8 -*-

import logging
logging.basicConfig(level=logging.DEBUG,format="%(levelname)s:%(filename)s(%(lineno)d):%(message)s")

import sys, os
import getpass

from fanficdownloader import adapters,writers,exceptions

import ConfigParser

config = ConfigParser.SafeConfigParser()

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
    except exceptions.FailedToLogin, ftl:
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

except exceptions.InvalidStoryURL, isu:
    print isu
except exceptions.StoryDoesNotExist, dne:
    print dne
except exceptions.UnknownSite, us:
    print us
