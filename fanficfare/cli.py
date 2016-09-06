# -*- coding: utf-8 -*-

# Copyright 2015 Fanficdownloader team, 2016 FanFicFare team
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from optparse import OptionParser
from os.path import expanduser, join, dirname
from os import access, R_OK

from os import listdir, remove, errno, devnull
from os.path import isfile, join, abspath
from subprocess import call, check_output, STDOUT
from tempfile import mkdtemp
from shutil import rmtree

import ConfigParser
import getpass
import logging
import pprint
import string
import sys

if sys.version_info < (2, 5):
    print 'This program requires Python 2.5 or newer.'
    sys.exit(1)

if sys.version_info >= (2, 7):
    # suppresses default logger.  Logging is setup in fanficfare/__init__.py so it works in calibre, too.
    rootlogger = logging.getLogger()
    loghandler = logging.NullHandler()
    loghandler.setFormatter(logging.Formatter('(=====)(levelname)s:%(message)s'))
    rootlogger.addHandler(loghandler)

try:
    # running under calibre
    from calibre_plugins.fanficfare_plugin.fanficfare import adapters, writers, exceptions, __version__
    from calibre_plugins.fanficfare_plugin.fanficfare.configurable import Configuration
    from calibre_plugins.fanficfare_plugin.fanficfare.epubutils import (
        get_dcsource_chaptercount, get_update_data, reset_orig_chapters_epub)
    from calibre_plugins.fanficfare_plugin.fanficfare.geturls import get_urls_from_page, get_urls_from_imap
except ImportError:
    from fanficfare import adapters, writers, exceptions,# __version__ THIS DIDN'T WORK I DON'T KNOW WHY.
    from fanficfare.configurable import Configuration
    from fanficfare.epubutils import (
        get_dcsource_chaptercount, get_update_data, reset_orig_chapters_epub)
    from fanficfare.geturls import get_urls_from_page, get_urls_from_imap


def write_story(config, adapter, writeformat, metaonly=False, outstream=None):
    writer = writers.getWriter(writeformat, config, adapter)
    writer.writeStory(outstream=outstream, metaonly=metaonly)
    output_filename = writer.getOutputFileName()
    del writer
    return output_filename

def parse_url(url): # this is required because of how calibre stores urls in the identifier field vs how the url appears in many email notification updates
    url = url.replace("https://", "")
    url = url.replace("http://", "")
    if "fanfiction.net" in url: #have to likely write something for every supported url
        url = url[:url.find("/", url.find("/s/") + 3)+1]
    return url

def get_files(mypath, filetype=None):
    if filetype:
        return [f for f in listdir(mypath) if isfile(join(mypath, f)) and f.endswith(filetype)]
    else:
        return [f for f in listdir(mypath) if isfile(join(mypath, f))]

def main(argv=None, parser=None, passed_defaultsini=None, passed_personalini=None):
    if argv is None:
        argv = sys.argv[1:]
    # read in args, anything starting with -- will be treated as --<varible>=<value>
    if not parser:
        parser = OptionParser('usage: %prog [options] storyurl')
    parser.add_option('-f', '--format', dest='format', default='epub',
                      help='write story as FORMAT, epub(default), mobi, text or html', metavar='FORMAT')

    if passed_defaultsini:
        config_help = 'read config from specified file(s) in addition to calibre plugin personal.ini, ~/.fanficfare/personal.ini, and ./personal.ini'
    else:
        config_help = 'read config from specified file(s) in addition to ~/.fanficfare/defaults.ini, ~/.fanficfare/personal.ini, ./defaults.ini, and ./personal.ini'
    parser.add_option('-c', '--config',
                      action='append', dest='configfile', default=None,
                      help=config_help, metavar='CONFIG')
    parser.add_option('-b', '--begin', dest='begin', default=None,
                      help='Begin with Chapter START', metavar='START')
    parser.add_option('-e', '--end', dest='end', default=None,
                      help='End with Chapter END', metavar='END')
    parser.add_option('-o', '--option',
                      action='append', dest='options',
                      help='set an option NAME=VALUE', metavar='NAME=VALUE')
    parser.add_option('-m', '--meta-only',
                      action='store_true', dest='metaonly',
                      help='Retrieve metadata and stop.  Or, if --update-epub, update metadata title page only.', )
    parser.add_option('-u', '--update-epub',
                      action='store_true', dest='update',
                      help='Update an existing epub with new chapters, give epub filename instead of storyurl.', )
    parser.add_option('--unnew',
                      action='store_true', dest='unnew',
                      help='Remove (new) chapter marks left by mark_new_chapters setting.', )
    parser.add_option('--update-cover',
                      action='store_true', dest='updatecover',
                      help='Update cover in an existing epub, otherwise existing cover (if any) is used on update.  Only valid with --update-epub.', )
    parser.add_option('--force',
                      action='store_true', dest='force',
                      help='Force overwrite of an existing epub, download and overwrite all chapters.', )
    parser.add_option('-i', '--infile',
                      help='Give a filename to read for URLs (and/or existing EPUB files with -u for updates).',
                      dest='infile', default=None,
                      metavar='INFILE')
    parser.add_option('-l', '--list',
                      action='store_true', dest='list',
                      help='Get list of valid story URLs from page given.', )
    parser.add_option('-n', '--normalize-list',
                      action='store_true', dest='normalize', default=False,
                      help='Get list of valid story URLs from page given, but normalized to standard forms.', )
    parser.add_option('-s', '--sites-list',
                      action='store_true', dest='siteslist', default=False,
                      help='Get list of valid story URLs examples.', )
    parser.add_option('-d', '--debug',
                      action='store_true', dest='debug',
                      help='Show debug output while downloading.', )
    parser.add_option('-v', '--version',
                      action='store_true', dest='version',
                      help='Display version and quit.', )
                      
    parser.add_option('-a', '--address', dest='address', default=None, help='Email Address. Requires -p, -r, and -q. Will search the supplied email for unread messages with download links and attempt to use them to download stories from.') #email address
    
    parser.add_option('-p', '--password', dest='password', default=None, help='Email Password.') #password for email address
    
    parser.add_option('-r', '--imap-server', dest='imap', default=None, help='Imap Server.') #imap server for email address
    
    parser.add_option('-q', '--label', dest='label', default=None, help='Location of emails to look for in email address, such as INBOX') #label for email
    
    parser.add_option('-z', '--output', dest='output', default=devnull, help='Name of file to output problem urls to. If the name is the same as the input file, will overwrite the input file') #for reuse mostly
    
    parser.add_option('-w', '--with-library', dest='library', default=None, help='Path to calibre library. If you enable this option, any urls passed in will be looked for in the calibre library and those epubs updated.') #calibredb

    options, args = parser.parse_args(argv)

    if options.version:
        ## single sourcing version number in fanficfare/__init__.py
        print("Version: %s" % __version__)
        return

    if not options.debug:
        logger = logging.getLogger('fanficfare')
        logger.setLevel(logging.INFO)

    if not (options.siteslist or options.infile or options.address) and len(args) != 1:
        parser.error('incorrect number of arguments')

    if options.siteslist:
        for site, examples in adapters.getSiteExamples():
            print '\n#### %s\nExample URLs:' % site
            for u in examples:
                print '  * %s' % u
        return

    if options.update and options.format != 'epub':
        parser.error('-u/--update-epub only works with epub')

    if options.unnew and options.format != 'epub':
        parser.error('--unnew only works with epub')
        
    if options.library:
        try:
            with open(devnull, 'w') as nullout:
                call(['calibredb'], stdout=nullout, stderr=nullout)
        except OSError as e:
            if errno == ENOENT:
                print "Calibredb is not installed on this system. Cannot search the calibre library or update it."
                options.library = None

    # for passing in a file list
    
    #put in the email lookup here
    
    if any([options.address, options.password, options.imap, options.label]) and not all([options.address, options.password, options.imap, options.label]):
        print "An email option was supplied without all information being given. Please use -h for help."
        return
    if not (options.infile or options.address):
        urls = args
    else:
        urls = []
        if options.infile:
            with open(options.infile,"r") as infile:
                #print "File exists and is readable"

                #fileurls = [line.strip() for line in infile]
                for url in infile:
                    url = url[:url.find('#')].strip()
                    if len(url) > 0:
                        #print "URL: (%s)"%url
                        urls.append(url)
        if options.address:
            email_urls = get_urls_from_imap(options.imap, options.address, options.password, options.label)
            for url in email_urls:
                url = url.strip()
                if len(url) > 0:
                    #print "URL: (%s)"%url
                    urls.append(url)
        urls = [parse_url(x) for x in urls]
    with open(options.output, "w") as outfile:
        for url in urls:
            try:
            
                #if calibre library, do exports here
                
                if options.library:
                    loc = None
                    try:
                        storyID = check_output('calibredb search "Identifiers:{}" --with-library "{}"'.format(url, options.library), shell=True,stderr=STDOUT)
                        try:
                            loc = mkdtemp()
                            print "Found in calibre library with ID {}".format(storyID)
                            res = check_output('calibredb export {} --with-library "{}" --dont-save-cover --dont-write-opf --single-dir --to-dir "{}"'.format(storyID, options.library, loc), shell=True) #use tempdir
                            current_file = join(loc, get_files(loc, ".epub")[0])
                            output_file = do_download(current_file,
                                options,
                                passed_defaultsini,
                                passed_personalini)
                        except Exception, e:
                             print "URL({}) Failed: Exception ({}).".format(url, e)
                             outfile.write("{}\n".format(url))
                             rmtree(loc)
                             #remove(current_file) # not needed because of rmtree
                             continue
                    
                    except:
                        output_file = do_download(url,
                            options,
                            passed_defaultsini,
                            passed_personalini)
                        output_file = join(abspath("."), output_file)
                    res = check_output('calibredb add "{}" --with-library "{}"'.format(output_file, options.library), shell=True, stderr=STDOUT) #uses the output file now returned by do_download in order to add the file to calibre and then remove it. 
                    res = check_output('calibredb search "Identifiers:{}" --with-library "{}"'.format(url, options.library), shell=True, stderr=STDOUT)
                    print "Added {} to library with id {}".format(output_file[output_file.rfind("/")+1:], res)
                    if loc: #if loc was set it means we used it, so remove it and all of the files within. else just removes the file itself
                        rmtree(loc)
                    else:
                        remove(output_file)
                
                else:
                    do_download(url,
                            options,
                            passed_defaultsini,
                            passed_personalini)
                #print("pagecache:%s"%options.pagecache.keys())
                
            except Exception, e:
                print "URL(%s) Failed: Exception (%s). Run URL individually for more detail."%(url,e)
                outfile.write("{}\n".format(url))
        '''else:
            do_download(urls[0],
                        options,
                        passed_defaultsini,
                        passed_personalini)'''

# make rest a function and loop on it.
def do_download(arg,
                options,
                passed_defaultsini,
                passed_personalini):

    # Attempt to update an existing epub.
    chaptercount = None
    output_filename = None

    if options.unnew:
        # remove mark_new_chapters marks
        reset_orig_chapters_epub(arg,arg)
        return

    if options.update:
        try:
            url, chaptercount = get_dcsource_chaptercount(arg)
            if not url:
                print 'No story URL found in epub to update.'
                return
            print 'Updating %s, URL: %s' % (arg, url)
            output_filename = arg
        except Exception:
            # if there's an error reading the update file, maybe it's a URL?
            # we'll look for an existing outputfile down below.
            url = arg
    else:
        url = arg

    try:
        configuration = Configuration(adapters.getConfigSectionsFor(url), options.format)
    except exceptions.UnknownSite, e:
        if options.list or options.normalize:
            # list for page doesn't have to be a supported site.
            configuration = Configuration('test1.com', options.format)
        else:
            raise e

    conflist = []
    homepath = join(expanduser('~'), '.fanficdownloader')
    ## also look for .fanficfare now, give higher priority than old dir.
    homepath2 = join(expanduser('~'), '.fanficfare')

    if passed_defaultsini:
        configuration.readfp(passed_defaultsini)

    # don't need to check existance for our selves.
    conflist.append(join(dirname(__file__), 'defaults.ini'))
    conflist.append(join(homepath, 'defaults.ini'))
    conflist.append(join(homepath2, 'defaults.ini'))
    conflist.append('defaults.ini')

    if passed_personalini:
        configuration.readfp(passed_personalini)

    conflist.append(join(homepath, 'personal.ini'))
    conflist.append(join(homepath2, 'personal.ini'))
    conflist.append('personal.ini')

    if options.configfile:
        conflist.extend(options.configfile)

    logging.debug('reading %s config file(s), if present' % conflist)
    configuration.read(conflist)

    try:
        configuration.add_section('overrides')
    except ConfigParser.DuplicateSectionError:
        pass

    if options.force:
        configuration.set('overrides', 'always_overwrite', 'true')

    if options.update and chaptercount:
        configuration.set('overrides', 'output_filename', output_filename)

    if options.update and not options.updatecover:
        configuration.set('overrides', 'never_make_cover', 'true')

    # images only for epub, even if the user mistakenly turned it
    # on else where.
    if options.format not in ('epub', 'html'):
        configuration.set('overrides', 'include_images', 'false')

    if options.options:
        for opt in options.options:
            (var, val) = opt.split('=')
            configuration.set('overrides', var, val)

    if options.list or options.normalize:
        retlist = get_urls_from_page(arg, configuration, normalize=options.normalize)
        print '\n'.join(retlist)
        return

    try:
        adapter = adapters.getAdapter(configuration, url)

        if not hasattr(options,'pagecache'):
            options.pagecache = adapter.get_empty_pagecache()
            options.cookiejar = adapter.get_empty_cookiejar()

        adapter.set_pagecache(options.pagecache)
        adapter.set_cookiejar(options.cookiejar)

        adapter.setChaptersRange(options.begin, options.end)

        # check for updating from URL (vs from file)
        if options.update and not chaptercount:
            try:
                writer = writers.getWriter('epub', configuration, adapter)
                output_filename = writer.getOutputFileName()
                noturl, chaptercount = get_dcsource_chaptercount(output_filename)
                print 'Updating %s, URL: %s' % (output_filename, url)
            except Exception:
                options.update = False
                pass

        # Check for include_images without no_image_processing. In absence of PIL, give warning.
        if adapter.getConfig('include_images') and not adapter.getConfig('no_image_processing'):
            try:
                from calibre.utils.magick import Image

                logging.debug('Using calibre.utils.magick')
            except ImportError:
                try:
                    import Image

                    logging.debug('Using PIL')
                except ImportError:
                    print "You have include_images enabled, but Python Image Library(PIL) isn't found.\nImages will be included full size in original format.\nContinue? (y/n)?"
                    if not sys.stdin.readline().strip().lower().startswith('y'):
                        raise#return

        # three tries, that's enough if both user/pass & is_adult needed,
        # or a couple tries of one or the other
        for x in range(0, 2):
            try:
                adapter.getStoryMetadataOnly()
            except exceptions.FailedToLogin, f:
                if f.passwdonly:
                    print 'Story requires a password.'
                else:
                    print 'Login Failed, Need Username/Password.'
                    sys.stdout.write('Username: ')
                    adapter.username = sys.stdin.readline().strip()
                adapter.password = getpass.getpass(prompt='Password: ')
                # print('Login: `%s`, Password: `%s`' % (adapter.username, adapter.password))
            except exceptions.AdultCheckRequired:
                print 'Please confirm you are an adult in your locale: (y/n)?'
                if sys.stdin.readline().strip().lower().startswith('y'):
                    adapter.is_adult = True

        if options.update and not options.force:
            urlchaptercount = int(adapter.getStoryMetadataOnly().getMetadata('numChapters'))

            if chaptercount == urlchaptercount and not options.metaonly:
                print '%s already contains %d chapters.' % (output_filename, chaptercount)
                raise ValueError('%s already contains %d chapters.' % (output_filename, chaptercount))
            elif chaptercount > urlchaptercount:
                print '%s contains %d chapters, more than source: %d.' % (output_filename, chaptercount, urlchaptercount)
                raise ValueError('%s contains %d chapters, more than source: %d.' % (output_filename, chaptercount, urlchaptercount))
            elif chaptercount == 0:
                print "%s doesn't contain any recognizable chapters, probably from a different source.  Not updating." % output_filename
                raise ValueError("%s doesn't contain any recognizable chapters, probably from a different source.  Not updating." % output_filename)
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
                 adapter.logfile,
                 adapter.oldchaptersmap,
                 adapter.oldchaptersdata) = (get_update_data(output_filename))[0:9]

                print 'Do update - epub(%d) vs url(%d)' % (chaptercount, urlchaptercount)

                if not options.update and chaptercount == urlchaptercount and adapter.getConfig('do_update_hook'):
                    adapter.hookForUpdates(chaptercount)

                write_story(configuration, adapter, 'epub')

        else:
            # regular download
            if options.metaonly:
                pprint.pprint(adapter.getStoryMetadataOnly().getAllMetadata())
                pprint.pprint(adapter.chapterUrls)

            output_filename = write_story(configuration, adapter, options.format, options.metaonly)

        if not options.metaonly and adapter.getConfig('post_process_cmd'):
            metadata = adapter.story.metadata
            metadata['output_filename'] = output_filename
            call(string.Template(adapter.getConfig('post_process_cmd')).substitute(metadata), shell=True)

        del adapter

    except exceptions.InvalidStoryURL as isu:
        print isu
        raise isu
    except exceptions.StoryDoesNotExist as dne:
        print dne
        raise dne
    except exceptions.UnknownSite as us:
        print us
        raise us
    except exceptions.AccessDenied as ad:
        print ad
        raise ad
        
    return output_filename

#put raises in

if __name__ == '__main__':
    main()
