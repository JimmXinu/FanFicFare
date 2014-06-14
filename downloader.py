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

# Modifying the path at the entry point allows all subsequent imports to
# directly import packages contained within the packages directory
import packages
packages.insert_into_python_path()

import sys, os
from os.path import normpath, expanduser, isfile, join
from StringIO import StringIO
from optparse import OptionParser      
import getpass
import string
import ConfigParser
from subprocess import call
import pprint

import logging
if sys.version_info >= (2, 7):
    # suppresses default logger.  Logging is setup in fanficdownload/__init__.py so it works in calibre, too.
    rootlogger = logging.getLogger()
    loghandler=logging.NullHandler()
    loghandler.setFormatter(logging.Formatter("(=====)(levelname)s:%(message)s"))
    rootlogger.addHandler(loghandler)

try:
    from calibre.constants import numeric_version as calibre_version
    is_calibre = True
except:
    is_calibre = False

# using try/except directly was masking errors during development.
if is_calibre:
    # running under calibre
    from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader import adapters,writers,exceptions
    from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader.configurable import Configuration
    from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader.epubutils import get_dcsource_chaptercount, get_update_data
    from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader.geturls import get_urls_from_page
else:
    from fanficdownloader import adapters,writers,exceptions
    from fanficdownloader.configurable import Configuration
    from fanficdownloader.epubutils import get_dcsource_chaptercount, get_update_data
    from fanficdownloader.geturls import get_urls_from_page
    

if sys.version_info < (2, 5):
    print "This program requires Python 2.5 or newer."
    sys.exit(1)

def writeStory(config,adapter,writeformat,metaonly=False,outstream=None):
    writer = writers.getWriter(writeformat,config,adapter)
    writer.writeStory(outstream=outstream,metaonly=metaonly)
    output_filename=writer.getOutputFileName()
    del writer
    return output_filename

def main(argv,
         parser=None,
         passed_defaultsini=None,
         passed_personalini=None):
   # read in args, anything starting with -- will be treated as --<varible>=<value>
   if not parser:
       parser = OptionParser("usage: %prog [options] storyurl")
   parser.add_option("-f", "--format", dest="format", default="epub",
                     help="write story as FORMAT, epub(default), mobi, text or html", metavar="FORMAT")

   if passed_defaultsini:
       config_help="read config from specified file(s) in addition to calibre plugin personal.ini, ~/.fanficdownloader/personal.ini, and ./personal.ini"
   else:
       config_help="read config from specified file(s) in addition to ~/.fanficdownloader/defaults.ini, ~/.fanficdownloader/personal.ini, ./defaults.ini, and ./personal.ini"
   parser.add_option("-c", "--config",
                     action="append", dest="configfile", default=None,
                     help=config_help, metavar="CONFIG")
   parser.add_option("-b", "--begin", dest="begin", default=None,
                     help="Begin with Chapter START", metavar="START")
   parser.add_option("-e", "--end", dest="end", default=None,
                     help="End with Chapter END", metavar="END")
   parser.add_option("-o", "--option",
                     action="append", dest="options",
                     help="set an option NAME=VALUE", metavar="NAME=VALUE")
   parser.add_option("-m", "--meta-only",
                     action="store_true", dest="metaonly",
                     help="Retrieve metadata and stop.  Or, if --update-epub, update metadata title page only.",)
   parser.add_option("-u", "--update-epub",
                     action="store_true", dest="update",
                     help="Update an existing epub with new chapters, give epub filename instead of storyurl.",)
   parser.add_option("--update-cover",
                     action="store_true", dest="updatecover",
                     help="Update cover in an existing epub, otherwise existing cover (if any) is used on update.  Only valid with --update-epub.",)
   parser.add_option("--force",
                     action="store_true", dest="force",
                     help="Force overwrite of an existing epub, download and overwrite all chapters.",)
   parser.add_option("-l", "--list",
                     action="store_true", dest="list",
                     help="Get list of valid story URLs from page given.",)
   parser.add_option("-n", "--normalize-list",
                     action="store_true", dest="normalize",default=False,
                     help="Get list of valid story URLs from page given, but normalized to standard forms.",)
   parser.add_option("-s", "--sites-list",
                     action="store_true", dest="siteslist",default=False,
                     help="Get list of valid story URLs examples.",)
   parser.add_option("-d", "--debug",
                     action="store_true", dest="debug",
                     help="Show debug output while downloading.",)
   
   (options, args) = parser.parse_args(argv)

   if not options.debug:
       logger = logging.getLogger("fanficdownloader")
       logger.setLevel(logging.INFO)
   
   if not options.siteslist and len(args) != 1:
       parser.error("incorrect number of arguments")

   if options.siteslist:
       for (site,examples) in adapters.getSiteExamples():
           print("\n====%s====\n\nExample URLs:"%site)
           for u in examples:
               print("  * %s"%u)
       return

   if options.update and options.format != 'epub':
       parser.error("-u/--update-epub only works with epub")

   ## Attempt to update an existing epub.
   chaptercount = None
   output_filename = None
   if options.update:
       try:
           (url,chaptercount) = get_dcsource_chaptercount(args[0])
           if not url:
               print "No story URL found in epub to update."
               return
           print "Updating %s, URL: %s" % (args[0],url)
           output_filename = args[0]
       except:
           # if there's an error reading the update file, maybe it's a URL?
           # we'll look for an existing outputfile down below.
           url = args[0]
   else:
       url = args[0]

   try:
       configuration = Configuration(adapters.getConfigSectionFor(url),options.format)
   except exceptions.UnknownSite, e:
       if options.list or options.normalize:
           # list for page doesn't have to be a supported site.
           configuration = Configuration("test1.com",options.format)
       else:
           raise e

   conflist = []
   homepath = join(expanduser("~"),".fanficdownloader")

   if passed_defaultsini:
       configuration.readfp(passed_defaultsini)
   
   if isfile(join(homepath,"defaults.ini")):
       conflist.append(join(homepath,"defaults.ini"))
   if isfile("defaults.ini"):
       conflist.append("defaults.ini")
       
   if passed_personalini:
       configuration.readfp(passed_personalini)
   
   if isfile(join(homepath,"personal.ini")):
       conflist.append(join(homepath,"personal.ini"))
   if isfile("personal.ini"):
       conflist.append("personal.ini")
       
   if options.configfile:
       conflist.extend(options.configfile)
      
   logging.debug('reading %s config file(s), if present'%conflist)
   configuration.read(conflist)

   try:
       configuration.add_section("overrides")
   except ConfigParser.DuplicateSectionError:
       pass

   if options.force:
       configuration.set("overrides","always_overwrite","true")

   if options.update and chaptercount:
       configuration.set("overrides","output_filename",output_filename)
       
   if options.update and not options.updatecover:
       configuration.set("overrides","never_make_cover","true")

   # images only for epub, even if the user mistakenly turned it
   # on else where.
   if options.format not in ("epub","html"):
       configuration.set("overrides","include_images","false")
       
   if options.options:
       for opt in options.options:
           (var,val) = opt.split('=')
           configuration.set("overrides",var,val)

   if options.list or options.normalize:
       retlist = get_urls_from_page(args[0], configuration, normalize=options.normalize)
       print "\n".join(retlist)               
       return

   try:
       adapter = adapters.getAdapter(configuration,url)
       adapter.setChaptersRange(options.begin,options.end)

       # check for updating from URL (vs from file)
       if options.update and not chaptercount:
           try:
               writer = writers.getWriter("epub",configuration,adapter)
               output_filename=writer.getOutputFileName()
               (noturl,chaptercount) = get_dcsource_chaptercount(output_filename)
               print "Updating %s, URL: %s" % (output_filename,url)
           except:
               options.update = False
               pass
       
       ## Check for include_images and absence of PIL, give warning.
       if adapter.getConfig('include_images'):
           try:
               from calibre.utils.magick import Image
               logging.debug("Using calibre.utils.magick")
           except:
               try:
                   import Image
                   logging.debug("Using PIL")
               except:
                   print "You have include_images enabled, but Python Image Library(PIL) isn't found.\nImages will be included full size in original format.\nContinue? (y/n)?"
                   if not sys.stdin.readline().strip().lower().startswith('y'):
                       return

       ## three tries, that's enough if both user/pass & is_adult needed,
       ## or a couple tries of one or the other
       for x in range(0,2):
           try:
               adapter.getStoryMetadataOnly()
           except exceptions.FailedToLogin, f:
               if f.passwdonly:
                   print "Story requires a password."
               else:
                   print "Login Failed, Need Username/Password."
                   sys.stdout.write("Username: ")
                   adapter.username = sys.stdin.readline().strip()
               adapter.password = getpass.getpass(prompt='Password: ')
               #print("Login: `%s`, Password: `%s`" % (adapter.username, adapter.password))
           except exceptions.AdultCheckRequired:
               print "Please confirm you are an adult in your locale: (y/n)?"
               if sys.stdin.readline().strip().lower().startswith('y'):
                   adapter.is_adult=True

       if options.update and not options.force:
           urlchaptercount = int(adapter.getStoryMetadataOnly().getMetadata('numChapters'))

           if chaptercount == urlchaptercount and not options.metaonly:
               print "%s already contains %d chapters." % (output_filename,chaptercount)
           elif chaptercount > urlchaptercount:
               print "%s contains %d chapters, more than source: %d." % (output_filename,chaptercount,urlchaptercount)
           elif chaptercount == 0:
               print "%s doesn't contain any recognizable chapters, probably from a different source.  Not updating." % (output_filename)
           else:
               # update now handled by pre-populating the old
               # images and chapters in the adapter rather than
               # merging epubs.
               (url,
                chaptercount,
                adapter.oldchapters,
                adapter.oldimgs,
                adapter.oldcover,
                adapter.calibrebookmark,
                adapter.logfile) = get_update_data(output_filename)

               print "Do update - epub(%d) vs url(%d)" % (chaptercount, urlchaptercount)

               if not (options.update and chaptercount == urlchaptercount) \
                       and adapter.getConfig("do_update_hook"):
                   chaptercount = adapter.hookForUpdates(chaptercount)

               writeStory(configuration,adapter,"epub")
                   
       else:
           # regular download
           if options.metaonly:
               pprint.pprint(adapter.getStoryMetadataOnly().getAllMetadata())
           
           output_filename=writeStory(configuration,adapter,options.format,options.metaonly)
       
       if not options.metaonly and adapter.getConfig("post_process_cmd"):
           metadata = adapter.story.metadata
           metadata['output_filename']=output_filename
           call(string.Template(adapter.getConfig("post_process_cmd"))
                .substitute(metadata), shell=True)
           
       del adapter
   
   except exceptions.InvalidStoryURL, isu:
       print isu
   except exceptions.StoryDoesNotExist, dne:
       print dne
   except exceptions.UnknownSite, us:
       print us

if __name__ == "__main__":
    #import time
    #start = time.time()
    main(sys.argv[1:])
    #print("Total time seconds:%f"%(time.time()-start))
