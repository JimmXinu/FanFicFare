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

import logging
## XXX cli option for logging level.
logging.basicConfig(level=logging.WARN,format="%(levelname)s:%(filename)s(%(lineno)d):%(message)s")

import sys, os
from optparse import OptionParser      
import getpass

if sys.version_info < (2, 5):
    print "This program requires Python 2.5 or newer."
    sys.exit(1)

from fanficdownloader import adapters,writers,exceptions

import ConfigParser

def writeStory(config,adapter,writeformat):
    writer = writers.getWriter(writeformat,config,adapter)
    writer.writeStory()
    del writer

def main():
       
   # read in args, anything starting with -- will be treated as --<varible>=<value>
   usage = "usage: %prog [options] storyurl"
   parser = OptionParser(usage)
   parser.add_option("-f", "--format", dest="format", default='epub',
                     help="write story as FORMAT, epub(default), text or html", metavar="FORMAT")
   parser.add_option("-o", "--option",
                     action="append", dest="options",
                     help="set an option NAME=VALUE", metavar="NAME=VALUE")
   parser.add_option("-m", "--meta-only",
                     action="store_true", dest="metaonly",
                     help="Retrieve metadata and stop",)
   
   (options, args) = parser.parse_args()

   if len(args) != 1:
       parser.error("incorrect number of arguments")

   config = ConfigParser.SafeConfigParser()
   
   logging.debug('reading defaults.ini config file, if present')
   config.read('defaults.ini')
   logging.debug('reading personal.ini config file, if present')
   config.read('personal.ini')

   try:
       config.add_section("overrides")
   except ConfigParser.DuplicateSectionError:
       pass
   if options.options:
       for opt in options.options:
           (var,val) = opt.split('=')
           config.set("overrides",var,val)

   try:
       adapter = adapters.getAdapter(config,args[0])
           
       try:
           adapter.getStoryMetadataOnly()
       except exceptions.FailedToLogin:
           print "Login Failed, Need Username/Password."
           sys.stdout.write("Username: ")
           adapter.username = sys.stdin.readline().strip()
           adapter.password = getpass.getpass(prompt='Password: ')
           #print("Login: `%s`, Password: `%s`" % (adapter.username, adapter.password))
           adapter.getStoryMetadataOnly()
       except exceptions.AdultCheckRequired:
           print "Please confirm you are an adult in your locale: (y/n)?"
           if sys.stdin.readline().strip().lower().startswith('y'):
               adapter.is_adult=True
           adapter.getStoryMetadataOnly()

       if options.metaonly:
           print adapter.getStoryMetadataOnly()
           return
       ## XXX Use format.
       ## XXX Doing all three formats actually causes some interesting
       ## XXX config issues with format-specific sections.
       print "format: %s" % options.format
       writeStory(config,adapter,"epub")
       writeStory(config,adapter,"html")
       writeStory(config,adapter,"txt")
       del adapter
   
   except exceptions.InvalidStoryURL, isu:
       print isu
   except exceptions.StoryDoesNotExist, dne:
       print dne
   except exceptions.UnknownSite, us:
       print us
   
if __name__ == "__main__":
    main()
