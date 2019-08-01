# -*- coding: utf-8 -*-

# Copyright 2015 Fanficdownloader team, 2019 FanFicFare team
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

from __future__ import absolute_import
from __future__ import print_function
from optparse import OptionParser, SUPPRESS_HELP
from os.path import expanduser, join, dirname
from os import access, R_OK
from subprocess import call
import getpass
import logging
import pprint
import string
import os, sys
import pickle

if sys.version_info < (2, 7):
    sys.exit('This program requires Python 2.7 or newer.')
elif sys.version_info < (3, 0):
    reload(sys)  # Reload restores 'hidden' setdefaultencoding method
    sys.setdefaultencoding("utf-8")
    def pickle_load(f):
        return pickle.load(f)
else: # > 3.0
    def pickle_load(f):
        return pickle.load(f,encoding="bytes")

version="3.10.8"
os.environ['CURRENT_VERSION_ID']=version

global_cache = 'global_cache'
global_cookies = 'global_cookies'

if sys.version_info >= (2, 7):
    # suppresses default logger.  Logging is setup in fanficfare/__init__.py so it works in calibre, too.
    rootlogger = logging.getLogger()
    loghandler = logging.NullHandler()
    loghandler.setFormatter(logging.Formatter('(=====)(levelname)s:%(message)s'))
    rootlogger.addHandler(loghandler)

logger = logging.getLogger('fanficfare')

try:
    # running under calibre
    from calibre_plugins.fanficfare_plugin.fanficfare import adapters, writers, exceptions
    from calibre_plugins.fanficfare_plugin.fanficfare.configurable import Configuration
    from calibre_plugins.fanficfare_plugin.fanficfare.epubutils import (
        get_dcsource_chaptercount, get_update_data, reset_orig_chapters_epub)
    from calibre_plugins.fanficfare_plugin.fanficfare.geturls import get_urls_from_page, get_urls_from_imap
    from calibre_plugins.fanficfare_plugin.fanficfare.six import StringIO
    from calibre_plugins.fanficfare_plugin.fanficfare.six.moves import configparser
    from calibre_plugins.fanficfare_plugin.fanficfare.six.moves import http_cookiejar as cl
except ImportError:
    from fanficfare import adapters, writers, exceptions
    from fanficfare.configurable import Configuration
    from fanficfare.epubutils import (
        get_dcsource_chaptercount, get_update_data, reset_orig_chapters_epub)
    from fanficfare.geturls import get_urls_from_page, get_urls_from_imap
    from fanficfare.six import StringIO
    from fanficfare.six.moves import configparser
    from fanficfare.six.moves import http_cookiejar as cl


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
                      help='Write story as FORMAT, epub(default), mobi, txt or html.', metavar='FORMAT')
    if passed_defaultsini:
        config_help = 'Read config from specified file(s) in addition to calibre plugin personal.ini, ~/.fanficfare/personal.ini, and ./personal.ini'
    else:
        config_help = 'Read config from specified file(s) in addition to ~/.fanficfare/defaults.ini, ~/.fanficfare/personal.ini, ./defaults.ini, and ./personal.ini'
    parser.add_option('-c', '--config',
                      action='append', dest='configfile', default=None,
                      help=config_help, metavar='CONFIG')
    range_help = '  --begin and --end will be overridden by a chapter range on the STORYURL like STORYURL[1-2], STORYURL[-3], STORYURL[3-] or STORYURL[3]'
    parser.add_option('-b', '--begin', dest='begin', default=None,
                      help='Begin story with Chapter START.'+range_help, metavar='START')
    parser.add_option('-e', '--end', dest='end', default=None,
                      help='End story with Chapter END.'+range_help, metavar='END')
    parser.add_option('-o', '--option',
                      action='append', dest='options',
                      help='Set config option NAME=VALUE  Overrides config file setting.', metavar='NAME=VALUE')
    parser.add_option('-m', '--meta-only',
                      action='store_true', dest='metaonly',
                      help='Retrieve and write metadata to stdout without downloading or saving chapters; saves story file with titlepage only. (See also --json-meta)', )
    parser.add_option('-z', '--no-meta-chapters',
                      action='store_true', dest='nometachapters',
                      help='Exclude list of chapters("zchapters") from metadata stdout output.  No effect without --meta-only or --json-meta flags', )
    parser.add_option('-j', '--json-meta',
                      action='store_true', dest='jsonmeta',
                      help='Output metadata as JSON with download, or with --meta-only flag.  (Only JSON will be output with --meta-only flag.)', )
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
    parser.add_option('--non-interactive',
                      action='store_false', dest='interactive', default=sys.stdin.isatty() and sys.stdout.isatty(),
                      help='Prevent interactive prompts (for scripting).', )
    parser.add_option('-d', '--debug',
                      action='store_true', dest='debug',
                      help='Show debug and notice output.', )
    parser.add_option('-p', '--progressbar',
                      action='store_true', dest='progressbar',
                      help='Display a simple progress bar while downloading--one dot(.) per network fetch.', )
    parser.add_option('-v', '--version',
                      action='store_true', dest='version',
                      help='Display version and quit.', )

    ## undocumented feature for development use.  Save page cache and
    ## cookies between runs.  Saves in PWD as files global_cache and
    ## global_cookies
    parser.add_option('--save-cache', '--save_cache',
                      action='store_true', dest='save_cache',
                      help=SUPPRESS_HELP, )

    options, args = parser.parse_args(argv)

    if not options.debug:
        logger.setLevel(logging.WARNING)
    else:
        import platform
        logger.debug("    OS Version:%s"%platform.platform())
        logger.debug("Python Version:%s"%sys.version)
        logger.debug("   FFF Version:%s"%version)

    if options.version:
        print("Version: %s" % version)
        return

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
            print('\n#### %s\nExample URLs:' % site)
            for u in examples:
                print('  * %s' % u)
        return

    if options.update and options.format != 'epub':
        parser.error('-u/--update-epub only works with epub')

    if options.unnew and options.format != 'epub':
        parser.error('--unnew only works with epub')

    urls=args

    if not list_only and not (args or any((options.infile,
                                           options.downloadimap,
                                           options.downloadlist))):
        parser.print_help();
        return

    if options.list:
        configuration = get_configuration(options.list,
                                          passed_defaultsini,
                                          passed_personalini,options)
        retlist = get_urls_from_page(options.list, configuration)
        print('\n'.join(retlist))

    if options.normalize:
        configuration = get_configuration(options.normalize,
                                          passed_defaultsini,
                                          passed_personalini,options)
        retlist = get_urls_from_page(options.normalize, configuration,normalize=True)
        print('\n'.join(retlist))

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
            print('\n'.join(retlist))

    # for passing in a file list
    if options.infile:
        with open(options.infile,"r") as infile:
            #print("file exists and is readable")
            for url in infile:
                if '#' in url:
                    url = url[:url.find('#')].strip()
                url = url.strip()
                if len(url) > 0:
                    #print("url: (%s)"%url)
                    urls.append(url)

    if options.save_cache:
        try:
            with open(global_cache,'rb') as jin:
                options.pagecache = pickle_load(jin)
            options.cookiejar = cl.LWPCookieJar()
            options.cookiejar.load(global_cookies)
        except Exception as e:
            print("Didn't load --save-cache %s"%e)

    if not list_only:
        if len(urls) < 1:
            print("No valid story URLs found")
        else:
            for url in urls:
                try:
                    do_download(url,
                                options,
                                passed_defaultsini,
                                passed_personalini)
                    # print("pagecache:%s"%options.pagecache.keys())
                except Exception as e:
                    if len(urls) == 1:
                        raise
                    print("URL(%s) Failed: Exception (%s). Run URL individually for more detail."%(url,e))

    # Saved in configurable.py now.
    # if options.save_cache:
    #     with open('global_cache','wb') as jout:
    #         pickle.dump(options.pagecache,jout,protocol=2)
    #     options.cookiejar.save('global_cookies')

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
                print('No story URL found in epub to update.')
                return
            print('Updating %s, URL: %s' % (arg, url))
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
                                      chaptercount,
                                      output_filename)

    try:
        # Allow chapter range with URL.
        # like test1.com?sid=5[4-6] or [4,6]
        # Overrides CLI options if present.
        url,ch_begin,ch_end = adapters.get_url_chapter_range(url)

        adapter = adapters.getAdapter(configuration, url)

        ## Share pagecache and cookiejar between multiple downloads.
        if not hasattr(options,'pagecache'):
            options.pagecache = configuration.get_empty_pagecache()
        if not hasattr(options,'cookiejar'):
            options.cookiejar = configuration.get_empty_cookiejar()
        if options.save_cache:
            save_cache = global_cache
            save_cookies = global_cookies
        else:
            save_cache = save_cookies = None
        configuration.set_pagecache(options.pagecache,save_cache)
        configuration.set_cookiejar(options.cookiejar,save_cookies)

        # url[begin-end] overrides CLI option if present.
        if ch_begin or ch_end:
            adapter.setChaptersRange(ch_begin, ch_end)
        else:
            adapter.setChaptersRange(options.begin, options.end)

        # check for updating from URL (vs from file)
        if options.update and not chaptercount:
            try:
                writer = writers.getWriter('epub', configuration, adapter)
                output_filename = writer.getOutputFileName()
                noturl, chaptercount = get_dcsource_chaptercount(output_filename)
                print('Updating %s, URL: %s' % (output_filename, url))
            except Exception as e:
                print("Failed to read epub for update: (%s) Continuing with update=false"%e)
                options.update = False

        # Check for include_images without no_image_processing. In absence of PIL, give warning.
        if adapter.getConfig('include_images') and not adapter.getConfig('no_image_processing'):
            try:
                from calibre.utils.magick import Image
            except ImportError:
                try:
                    ## Pillow is a more current fork of PIL library
                    from PIL import Image
                except ImportError:
                    try:
                        import Image
                    except ImportError:
                        print("You have include_images enabled, but Python Image Library(PIL) isn't found.\nImages will be included full size in original format.\nContinue? (y/n)?")
                        if options.interactive:
                            if not sys.stdin.readline().strip().lower().startswith('y'):
                                return
                        else:
                            # for non-interactive, default the response to yes and continue processing
                            print('y')

        # three tries, that's enough if both user/pass & is_adult needed,
        # or a couple tries of one or the other
        for x in range(0, 2):
            try:
                adapter.getStoryMetadataOnly()
            except exceptions.FailedToLogin as f:
                if not options.interactive:
                    print('Login Failed on non-interactive process. Set username and password in personal.ini.')
                    return
                if f.passwdonly:
                    print('Story requires a password.')
                else:
                    print('Login Failed, Need Username/Password.')
                    sys.stdout.write('Username: ')
                    adapter.username = sys.stdin.readline().strip()
                adapter.password = getpass.getpass(prompt='Password: ')
                # print('Login: `%s`, Password: `%s`' % (adapter.username, adapter.password))
            except exceptions.AdultCheckRequired:
                if options.interactive:
                    print('Please confirm you are an adult in your locale: (y/n)?')
                    if sys.stdin.readline().strip().lower().startswith('y'):
                        adapter.is_adult = True
                else:
                    print('Adult check required on non-interactive process. Set is_adult:true in personal.ini or pass -o "is_adult=true" to the command.')
                    return

        if options.update and not options.force:
            urlchaptercount = int(adapter.getStoryMetadataOnly().getMetadata('numChapters').replace(',',''))
            # returns int adjusted for start-end range.
            urlchaptercount = adapter.getStoryMetadataOnly().getChapterCount()

            if chaptercount == urlchaptercount and not options.metaonly:
                print('%s already contains %d chapters.' % (output_filename, chaptercount))
            elif chaptercount > urlchaptercount:
                print('%s contains %d chapters, more than source: %d.' % (output_filename, chaptercount, urlchaptercount))
            elif chaptercount == 0:
                print("%s doesn't contain any recognizable chapters, probably from a different source.  Not updating." % output_filename)
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

                print('Do update - epub(%d) vs url(%d)' % (chaptercount, urlchaptercount))

                if not options.update and chaptercount == urlchaptercount and adapter.getConfig('do_update_hook'):
                    adapter.hookForUpdates(chaptercount)

                if adapter.getConfig('pre_process_safepattern'):
                    metadata = adapter.story.get_filename_safe_metadata(pattern=adapter.getConfig('pre_process_safepattern'))
                else:
                    metadata = adapter.story.getAllMetadata()
                call(string.Template(adapter.getConfig('pre_process_cmd')).substitute(metadata), shell=True)

                write_story(configuration, adapter, 'epub')

        else:
            if not options.metaonly and adapter.getConfig('pre_process_cmd'):
                if adapter.getConfig('pre_process_safepattern'):
                    metadata = adapter.story.get_filename_safe_metadata(pattern=adapter.getConfig('pre_process_safepattern'))
                else:
                    metadata = adapter.story.getAllMetadata()
                call(string.Template(adapter.getConfig('pre_process_cmd')).substitute(metadata), shell=True)

            output_filename = write_story(configuration, adapter, options.format, options.metaonly)

            if options.metaonly and not options.jsonmeta:
                metadata = adapter.getStoryMetadataOnly().getAllMetadata()
                metadata['output_filename'] = output_filename
                if not options.nometachapters:
                    metadata['zchapters'] = []
                    for i, chap in enumerate(adapter.get_chapters()):
                        metadata['zchapters'].append((i+1,chap))
                pprint.pprint(metadata)

        if not options.metaonly and adapter.getConfig('post_process_cmd'):
            if adapter.getConfig('post_process_safepattern'):
                metadata = adapter.story.get_filename_safe_metadata(pattern=adapter.getConfig('post_process_safepattern'))
            else:
                metadata = adapter.story.getAllMetadata()
            metadata['output_filename'] = output_filename
            call(string.Template(adapter.getConfig('post_process_cmd')).substitute(metadata), shell=True)

        if options.jsonmeta:
            metadata = adapter.getStoryMetadataOnly().getAllMetadata()
            metadata['output_filename'] = output_filename
            if not options.nometachapters:
                metadata['zchapters'] = []
                for i, chap in enumerate(adapter.get_chapters()):
                    metadata['zchapters'].append((i+1,chap))
            import json
            print(json.dumps(metadata, sort_keys=True,
                             indent=2, separators=(',', ':')))

        del adapter

    except exceptions.InvalidStoryURL as isu:
        print(isu)
    except exceptions.StoryDoesNotExist as dne:
        print(dne)
    except exceptions.UnknownSite as us:
        print(us)
    except exceptions.AccessDenied as ad:
        print(ad)

def get_configuration(url,
                      passed_defaultsini,
                      passed_personalini,
                      options,
                      chaptercount=None,
                      output_filename=None):
    try:
        configuration = Configuration(adapters.getConfigSectionsFor(url), options.format)
    except exceptions.UnknownSite as e:
        if options.list or options.normalize or options.downloadlist:
            # list for page doesn't have to be a supported site.
            configuration = Configuration(['unknown'], options.format)
        else:
            raise e

    conflist = []
    homepath = join(expanduser('~'), '.fanficdownloader')
    ## also look for .fanficfare now, give higher priority than old dir.
    homepath2 = join(expanduser('~'), '.fanficfare')

    if passed_defaultsini:
        # new StringIO each time rather than pass StringIO and rewind
        # for case of list download.  Just makes more sense to me.
        configuration.readfp(StringIO(passed_defaultsini))
    else:
        # don't need to check existance for our selves.
        conflist.append(join(dirname(__file__), 'defaults.ini'))
        conflist.append(join(homepath, 'defaults.ini'))
        conflist.append(join(homepath2, 'defaults.ini'))
        conflist.append('defaults.ini')

    if passed_personalini:
        # new StringIO each time rather than pass StringIO and rewind
        # for case of list download.  Just makes more sense to me.
        configuration.readfp(StringIO(passed_personalini))

    conflist.append(join(homepath, 'personal.ini'))
    conflist.append(join(homepath2, 'personal.ini'))
    conflist.append('personal.ini')

    if options.configfile:
        conflist.extend(options.configfile)

    configuration.read(conflist)

    try:
        configuration.add_section('overrides')
    except configparser.DuplicateSectionError:
        pass

    if options.force:
        configuration.set('overrides', 'always_overwrite', 'true')

    if options.update and chaptercount and output_filename:
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

    if options.progressbar:
        configuration.set('overrides','progressbar','true')

    return configuration

if __name__ == '__main__':
    main()
