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
from subprocess import call
import ConfigParser
import getpass
import logging
import pprint
import string
import sys

version="2.3.6"

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
    from calibre_plugins.fanficfare_plugin.fanficfare import adapters, writers, exceptions
    from calibre_plugins.fanficfare_plugin.fanficfare.configurable import Configuration
    from calibre_plugins.fanficfare_plugin.fanficfare.epubutils import (
        get_dcsource_chaptercount, get_update_data, reset_orig_chapters_epub)
    from calibre_plugins.fanficfare_plugin.fanficfare.geturls import get_urls_from_page, get_urls_from_imap
except ImportError:
    from fanficfare import adapters, writers, exceptions
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

def main(argv=None,
         parser=None,
         passed_defaultsini=None,
         passed_personalini=None):
    if argv is None:
        argv = sys.argv[1:]
    # read in args, anything starting with -- will be treated as --<varible>=<value>
    if not parser:
        parser = OptionParser('usage: %prog [options] [STORYURL]...')
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
                      help='Update an existing epub(if present) with new chapters.  Give either epub filename or story URL.', )
    parser.add_option('--update-cover',
                      action='store_true', dest='updatecover',
                      help='Update cover in an existing epub, otherwise existing cover (if any) is used on update.  Only valid with --update-epub.', )
    parser.add_option('--unnew',
                      action='store_true', dest='unnew',
                      help='Remove (new) chapter marks left by mark_new_chapters setting.', )
    parser.add_option('--force',
                      action='store_true', dest='force',
                      help='Force overwrite of an existing epub, download and overwrite all chapters.', )
    parser.add_option('-i', '--infile',
                      help='Give a filename to read for URLs (and/or existing EPUB files with --update-epub).',
                      dest='infile', default=None,
                      metavar='INFILE')

    parser.add_option('-l', '--list',
                      dest='list', default=None, metavar='URL',
                      help='Get list of valid story URLs from page given.', )
    parser.add_option('-n', '--normalize-list',
                      dest='normalize', default=None, metavar='URL',
                      help='Get list of valid story URLs from page given, but normalized to standard forms.', )
    parser.add_option('--download-list',
                      dest='downloadlist', default=None, metavar='URL',
                      help='Download story URLs retrieved from page given.  Update existing EPUBs if used with --update-epub.', )

    parser.add_option('--imap',
                      action='store_true', dest='imaplist',
                      help='Get list of valid story URLs from unread email from IMAP account configured in ini.', )

    parser.add_option('--download-imap',
                      action='store_true', dest='downloadimap',
                      help='Download valid story URLs from unread email from IMAP account configured in ini.  Update existing EPUBs if used with --update-epub.', )

    parser.add_option('-s', '--sites-list',
                      action='store_true', dest='siteslist', default=False,
                      help='Get list of valid story URLs examples.', )
    parser.add_option('-d', '--debug',
                      action='store_true', dest='debug',
                      help='Show debug and notice output.', )
    parser.add_option('-v', '--version',
                      action='store_true', dest='version',
                      help='Display version and quit.', )

    options, args = parser.parse_args(argv)

    if options.version:
        print("Version: %s" % version)
        return

    if not options.debug:
        logger = logging.getLogger('fanficfare')
        logger.setLevel(logging.WARNING)

    list_only = any((options.imaplist,
                     options.siteslist,
                     options.list,
                     options.normalize,
                     ))

    if list_only and (args or any((options.downloadimap,
                                   options.downloadlist))):
        parser.error('Incorrect arguments: Cannot download and list URLs at the same time.')

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

    urls=args

    if not list_only and not (args or any((options.downloadimap,
                                           options.downloadlist))):
        parser.print_help();
        return
    
    if options.list:
        configuration = get_configuration(options.list,
                                          passed_defaultsini,
                                          passed_personalini,options)
        retlist = get_urls_from_page(options.list, configuration)
        print '\n'.join(retlist)

    if options.normalize:
        configuration = get_configuration(options.normalize,
                                          passed_defaultsini,
                                          passed_personalini,options)
        retlist = get_urls_from_page(options.normalize, configuration,normalize=True)
        print '\n'.join(retlist)

    if options.downloadlist:
        configuration = get_configuration(options.downloadlist,
                                          passed_defaultsini,
                                          passed_personalini,options)
        retlist = get_urls_from_page(options.downloadlist, configuration)
        urls.extend(retlist)

    if options.imaplist or options.downloadimap:
        # list doesn't have a supported site.
        configuration = get_configuration('test1.com',passed_defaultsini,passed_personalini,options)
        markread = configuration.getConfig('imap_mark_read') == 'true' or \
            (configuration.getConfig('imap_mark_read') == 'downloadonly' and options.downloadimap)
        retlist = get_urls_from_imap(configuration.getConfig('imap_server'),
                                     configuration.getConfig('imap_username'),
                                     configuration.getConfig('imap_password'),
                                     configuration.getConfig('imap_folder'),
                                     markread)

        if options.downloadimap:
            urls.extend(retlist)
        else:
            print '\n'.join(retlist)

    # for passing in a file list
    if options.infile:
        with open(options.infile,"r") as infile:
            #print "File exists and is readable"

            #fileurls = [line.strip() for line in infile]
            for url in infile:
                url = url[:url.find('#')].strip()
                if len(url) > 0:
                    #print "URL: (%s)"%url
                    urls.append(url)

    if not list_only:
        if len(urls) < 1:
            print "No valid story URLs found"
        else:
            for url in urls:
                try:
                    do_download(url,
                                options,
                                passed_defaultsini,
                                passed_personalini)
                #print("pagecache:%s"%options.pagecache.keys())
                except Exception, e:
                    print "URL(%s) Failed: Exception (%s). Run URL individually for more detail."%(url,e)

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

    configuration = get_configuration(url,
                                      passed_defaultsini,
                                      passed_personalini,
                                      options,
                                      chaptercount)

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
                    ## Pillow is a more current fork of PIL library
                    from PIL import Image
                    logging.debug('Using Pillow')
                except ImportError:
                    try:
                        import Image
                        logging.debug('Using PIL')
                    except ImportError:
                        print "You have include_images enabled, but Python Image Library(PIL) isn't found.\nImages will be included full size in original format.\nContinue? (y/n)?"
                        if not sys.stdin.readline().strip().lower().startswith('y'):
                            return

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
            elif chaptercount > urlchaptercount:
                print '%s contains %d chapters, more than source: %d.' % (output_filename, chaptercount, urlchaptercount)
            elif chaptercount == 0:
                print "%s doesn't contain any recognizable chapters, probably from a different source.  Not updating." % output_filename
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
    except exceptions.StoryDoesNotExist as dne:
        print dne
    except exceptions.UnknownSite as us:
        print us
    except exceptions.AccessDenied as ad:
        print ad

def get_configuration(url,
                      passed_defaultsini,
                      passed_personalini,
                      options,
                      chaptercount=None):
    try:
        configuration = Configuration(adapters.getConfigSectionsFor(url), options.format)
    except exceptions.UnknownSite, e:
        if options.list or options.normalize or options.downloadlist:
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

    return configuration

if __name__ == '__main__':
    main()
