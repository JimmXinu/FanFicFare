# -*- coding: utf-8 -*-

# Copyright 2015 Fanficdownloader team, 2020 FanFicFare team
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
from io import StringIO
from optparse import OptionParser, SUPPRESS_HELP
from os.path import expanduser, join, dirname
from subprocess import call
import getpass
import logging
import pprint
import string
import os, sys, platform


version="4.9.3"
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

from fanficfare import adapters, writers, exceptions
from fanficfare.configurable import Configuration
from fanficfare.epubutils import (
    get_dcsource_chaptercount, get_update_data, reset_orig_chapters_epub)
from fanficfare.geturls import get_urls_from_page, get_urls_from_imap
from fanficfare.six.moves import configparser
from fanficfare.six import text_type as unicode

def write_story(config, adapter, writeformat,
                metaonly=False, nooutput=False,
                outstream=None):
    writer = writers.getWriter(writeformat, config, adapter)
    output_filename = writer.getOutputFileName()
    if nooutput:
        logger.info("Output suppressed by --no-output")
    else:
        writer.writeStory(outstream=outstream, metaonly=metaonly)
        logger.debug("Successfully wrote '%s'"%output_filename)
    del writer
    return output_filename

def mkParser(calibre, parser=None):
    # read in args, anything starting with -- will be treated as --<varible>=<value>
    if not parser:
        parser = OptionParser('usage: %prog [options] [STORYURL]...')
    parser.add_option('-f', '--format', dest='format', default='epub',
                      help='Write story as FORMAT, epub(default), mobi, txt or html.', metavar='FORMAT')
    if calibre:
        config_help = 'calibre plugin defaults.ini, calibre plugin personal.ini'
    else:
        config_help = '~/.fanficfare/defaults.ini, $XDG_CONFIG_HOME/fanficfare/defaults.ini, ./defaults.ini'
    parser.add_option('-c', '--config',
                      action='append', dest='configfile', default=None,
                      help=('Read config from specified file(s) in addition to (ordered lowest to highest priority): '
                            +config_help
                            +', ~/.fanficfare/personal.ini, $XDG_CONFIG_HOME/fanficfare/personal.ini, and ./personal.ini.  -c/--config files take highest priority'),
                      metavar='CONFIG')
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
                      help='Output metadata as JSON with download, or with --meta-only flag.  (Only JSON will be output with --meta-only flag.)  Also now series name and desc if available with --list', )
    parser.add_option('--json-meta-file',
                      action='store_true', dest='jsonmetafile',
                      help='Similar to --json-meta, but output metadata for each download as JSON to an individual file named by appending ".json" to the output_filename.', )
    parser.add_option('--no-output',
                      action='store_true', dest='nooutput',
                      help='Do not download chapters and do not write output file.  Intended for testing and with --meta-only.', )
    parser.add_option('-u', '--update-epub',
                      action='store_true', dest='update',
                      help='Update an existing epub(if present) with new chapters.  Give either epub filename or story URL.', )
    parser.add_option('-U', '--update-epub-always',
                      action='store_true', dest='updatealways',
                      help="Update an existing epub(if present) even if there aren't new chapters.  Give either epub filename or story URL.", )
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

    def sitesList(*args):
        for site, examples in adapters.getSiteExamples():
            print('\n#### %s\nExample URLs:' % site)
            for u in examples:
                print('  * %s' % u)
        sys.exit()

    parser.add_option('-s', '--sites-list',
                      action='callback', callback=sitesList,
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
    parser.add_option('--color',
                      action='store_true', dest='color',
                      help='Display a errors and warnings in a contrasting color.  Requires package colorama on Windows.', )

    def printVersion(*args):
        print("Version: %s" % version)
        sys.exit()

    parser.add_option('-v', '--version',
                      action='callback', callback=printVersion,
                      help='Display version and quit.', )

    ## undocumented feature for development use.  Save page cache and
    ## cookies between runs.  Saves in PWD as files global_cache and
    ## global_cookies
    parser.add_option('--save-cache', '--save_cache',
                      action='store_true', dest='save_cache',
                      help=SUPPRESS_HELP, )
    ## 'undocumented' feature to allow expired/unverified SSL certs pass.
    ## removed in favor of use_ssl_unverified_context ini setting.
    parser.add_option('--unverified_ssl',
                      action='store_true', dest='unverified_ssl',
                      help=SUPPRESS_HELP, )

    return parser

def expandOptions(options):
    options.list_only = any((options.imaplist,
                             options.list,
                             options.normalize,
                             ))

    # options.updatealways should also invoke most options.update logic.
    if options.updatealways:
        options.update = True

def validateOptions(parser, options, args):
    if options.unverified_ssl:
        parser.error("Option --unverified_ssl removed.\nSet use_ssl_unverified_context:true in ini file or --option instead.")

    if options.list_only and (args or any((options.downloadimap,
                                           options.downloadlist))):
        parser.error('Incorrect arguments: Cannot download and list URLs at the same time.')

    if options.update and options.format != 'epub':
        parser.error('-u/--update-epub/-U/--update-epub-always only work with epub')

    if options.unnew and options.format != 'epub':
        parser.error('--unnew only works with epub')

    if not options.list_only and not (args or any((options.infile,
                                                   options.downloadimap,
                                                   options.downloadlist))):
        parser.print_help()
        sys.exit()

def setup(options):
    if not options.debug:
        logger.setLevel(logging.WARNING)
    else:
        logger.debug("    OS Version:%s"%platform.platform())
        logger.debug("Python Version:%s"%sys.version)
        logger.debug("   FFF Version:%s"%version)

    if options.color:
        if 'Windows' in platform.platform():
            try:
                from colorama import init as colorama_init
                colorama_init()
            except ImportError:
                print("Option --color will not work on Windows without installing Python package colorama.\nContinue? (y/n)?")
                if options.interactive:
                    if not sys.stdin.readline().strip().lower().startswith('y'):
                        sys.exit()
                    else:
                        # for non-interactive, default the response to yes and continue processing
                        print('y')
        def warn(t):
            print("\033[{}m{}\033[0m".format(34, t)) # blue
        def fail(t):
            print("\033[{}m{}\033[0m".format(31, t)) # red
    else:
        warn = fail = print

    return warn, fail

def dispatch(options, urls,
             passed_defaultsini=None, passed_personalini=None,
             warn=print, fail=print):
    if options.list:
        configuration = get_configuration(options.list,
                                          passed_defaultsini,
                                          passed_personalini,options)
        frompage = get_urls_from_page(options.list, configuration)
        if options.jsonmeta:
            import json
            print(json.dumps(frompage, sort_keys=True,
                             indent=2, separators=(',', ':')))
        else:
            retlist = frompage.get('urllist',[])
            print('\n'.join(retlist))

    if options.normalize:
        configuration = get_configuration(options.normalize,
                                          passed_defaultsini,
                                          passed_personalini,options)
        retlist = get_urls_from_page(options.normalize, configuration,normalize=True).get('urllist',[])
        print('\n'.join(retlist))

    if options.downloadlist:
        configuration = get_configuration(options.downloadlist,
                                          passed_defaultsini,
                                          passed_personalini,options)
        retlist = get_urls_from_page(options.downloadlist, configuration).get('urllist',[])
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

    if not options.list_only:
        if len(urls) < 1:
            print("No valid story URLs found")
        else:
            for url in urls:
                try:
                    do_download(url,
                                options,
                                passed_defaultsini,
                                passed_personalini,
                                warn,
                                fail)
                except Exception as e:
                    if len(urls) == 1:
                        raise
                    fail("URL(%s) Failed: Exception (%s). Run URL individually for more detail."%(url,e))

def main(argv=None,
         parser=None,
         passed_defaultsini=None,
         passed_personalini=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = mkParser(bool(passed_defaultsini), parser)
    options, args = parser.parse_args(argv)
    expandOptions(options)
    validateOptions(parser, options, args)
    warn, fail = setup(options)
    urls=args
    dispatch(options, urls, passed_defaultsini, passed_personalini, warn, fail)

# make rest a function and loop on it.
def do_download(arg,
                options,
                passed_defaultsini,
                passed_personalini,
                warn=print,
                fail=print):

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
                fail('No story URL found in epub to update.')
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

        # url[begin-end] overrides CLI option if present.
        if ch_begin or ch_end:
            adapter.setChaptersRange(ch_begin, ch_end)
        else:
            adapter.setChaptersRange(options.begin, options.end)

        # check for updating from URL (vs from file)
        update_story = options.update
        if update_story and not chaptercount:
            try:
                writer = writers.getWriter('epub', configuration, adapter)
                output_filename = writer.getOutputFileName()
                noturl, chaptercount = get_dcsource_chaptercount(output_filename)
                print('Updating %s, URL: %s' % (output_filename, url))
            except Exception as e:
                warn("Failed to read epub for update: (%s) Continuing with update=false"%e)
                update_story = False

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

        if update_story and not options.force:
            urlchaptercount = int(adapter.getStoryMetadataOnly().getMetadata('numChapters').replace(',',''))
            # returns int adjusted for start-end range.
            urlchaptercount = adapter.getStoryMetadataOnly().getChapterCount()

            if chaptercount == urlchaptercount and not options.metaonly and not options.updatealways:
                print('%s already contains %d chapters.' % (output_filename, chaptercount))
            elif chaptercount > urlchaptercount:
                warn('%s contains %d chapters, more than source: %d.' % (output_filename, chaptercount, urlchaptercount))
            elif chaptercount == 0:
                warn("%s doesn't contain any recognizable chapters, probably from a different source.  Not updating." % output_filename)
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

                if not update_story and chaptercount == urlchaptercount and adapter.getConfig('do_update_hook'):
                    adapter.hookForUpdates(chaptercount)

                if adapter.getConfig('pre_process_safepattern'):
                    metadata = adapter.story.get_filename_safe_metadata(pattern=adapter.getConfig('pre_process_safepattern'))
                else:
                    metadata = adapter.story.getAllMetadata()
                call(string.Template(adapter.getConfig('pre_process_cmd')).substitute(metadata), shell=True)

                output_filename = write_story(configuration, adapter, 'epub',
                                              nooutput=options.nooutput)

        else:
            if not options.metaonly and adapter.getConfig('pre_process_cmd'):
                if adapter.getConfig('pre_process_safepattern'):
                    metadata = adapter.story.get_filename_safe_metadata(pattern=adapter.getConfig('pre_process_safepattern'))
                else:
                    metadata = adapter.story.getAllMetadata()
                call(string.Template(adapter.getConfig('pre_process_cmd')).substitute(metadata), shell=True)

            output_filename = write_story(configuration, adapter, options.format,
                                          metaonly=options.metaonly, nooutput=options.nooutput)

            if options.metaonly and not options.jsonmeta:
                metadata = adapter.getStoryMetadataOnly().getAllMetadata()
                metadata['output_filename'] = output_filename
                if not options.nometachapters:
                    metadata['zchapters'] = []
                    for i, chap in enumerate(adapter.get_chapters()):
                        metadata['zchapters'].append((i+1,chap))
                else:
                    # If no chapters, also suppress output_css so
                    # metadata is shorter.
                    del metadata['output_css']
                pprint.pprint(metadata)

        if not options.metaonly and adapter.getConfig('post_process_cmd'):
            if adapter.getConfig('post_process_safepattern'):
                metadata = adapter.story.get_filename_safe_metadata(pattern=adapter.getConfig('post_process_safepattern'))
            else:
                metadata = adapter.story.getAllMetadata()
            metadata['output_filename'] = output_filename
            call(string.Template(adapter.getConfig('post_process_cmd')).substitute(metadata), shell=True)

        if options.jsonmeta or options.jsonmetafile:
            metadata = adapter.getStoryMetadataOnly().getAllMetadata()
            metadata['output_filename'] = output_filename
            if not options.nometachapters:
                metadata['zchapters'] = []
                for i, chap in enumerate(adapter.get_chapters()):
                    metadata['zchapters'].append((i+1,chap))
            import json
            if options.jsonmeta:
                print(json.dumps(metadata, sort_keys=True,
                                 indent=2, separators=(',', ':')))
            if options.jsonmetafile:
                with open(output_filename+".json","w") as jsonfile:
                    json.dump(metadata, jsonfile, sort_keys=True,
                                 indent=2, separators=(',', ':'))
        if adapter.story.chapter_error_count > 0:
            warn("===================\n!!!! %s chapters errored downloading %s !!!!\n==================="%(adapter.story.chapter_error_count,
                                                        url))
        del adapter

    except exceptions.InvalidStoryURL as isu:
        fail(isu)
    except exceptions.StoryDoesNotExist as dne:
        fail(dne)
    except exceptions.UnknownSite as us:
        fail(us)
    except exceptions.AccessDenied as ad:
        fail(ad)

def get_configuration(url,
                      passed_defaultsini,
                      passed_personalini,
                      options,
                      chaptercount=None,
                      output_filename=None):
    try:
        configuration = Configuration(adapters.getConfigSectionsFor(url),
                                      options.format)
    except exceptions.UnknownSite as e:
        if options.list or options.normalize or options.downloadlist:
            # list for page doesn't have to be a supported site.
            configuration = Configuration(['unknown'],
                                          options.format)
        else:
            raise

    conflist = []
    homepath = join(expanduser('~'), '.fanficdownloader')
    ## also look for .fanficfare now, give higher priority than old dir.
    homepath2 = join(expanduser('~'), '.fanficfare')
    xdgpath = os.environ.get('XDG_CONFIG_HOME', join(expanduser('~'),'.config'))
    xdgpath = join(xdgpath, 'fanficfare')

    if passed_defaultsini:
        # new StringIO each time rather than pass StringIO and rewind
        # for case of list download.  Just makes more sense to me.
        configuration.readfp(StringIO(unicode(passed_defaultsini)))
    else:
        # don't need to check existance for our selves.
        conflist.append(join(dirname(__file__), 'defaults.ini'))
        conflist.append(join(homepath, 'defaults.ini'))
        conflist.append(join(homepath2, 'defaults.ini'))
        conflist.append(join(xdgpath, 'defaults.ini'))
        conflist.append('defaults.ini')

    if passed_personalini:
        # new StringIO each time rather than pass StringIO and rewind
        # for case of list download.  Just makes more sense to me.
        configuration.readfp(StringIO(unicode(passed_personalini)))

    conflist.append(join(homepath, 'personal.ini'))
    conflist.append(join(homepath2, 'personal.ini'))
    conflist.append(join(xdgpath, 'personal.ini'))
    conflist.append('personal.ini')

    if options.configfile:
        conflist.extend(options.configfile)

    configuration.read(conflist)

    try:
        configuration.add_section('overrides')
    except configparser.DuplicateSectionError:
        # generally already exists in defaults.ini
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

    ## do page cache and cookie load after reading INI files because
    ## settings (like use_basic_cache) matter.

    ## only need browser cache if one of the URLs needs it, and it
    ## isn't saved or dependent on options.save_cache.  This needs to
    ## be above basic_cache to avoid loading more than once anyway.
    if configuration.getConfig('use_browser_cache'):
        if not hasattr(options,'browser_cache'):
            configuration.get_fetcher() # force browser cache read.
            options.browser_cache = configuration.get_browser_cache()
        else:
            configuration.set_browser_cache(options.browser_cache)

    ## Share basic_cache between multiple downloads.
    if not hasattr(options,'basic_cache'):
        options.basic_cache = configuration.get_basic_cache()
        if options.save_cache:
            try:
                options.basic_cache.load_cache(global_cache)
            except Exception as e:
                logger.warning("Didn't load --save-cache %s\nContinue without loading BasicCache"%e)
            options.basic_cache.set_autosave(True,filename=global_cache)
    else:
        configuration.set_basic_cache(options.basic_cache)
    # logger.debug(options.basic_cache.basic_cache.keys())

    ## All CLI downloads are sequential and share one cookiejar,
    ## loaded the first time through here.
    if not hasattr(options,'cookiejar'):
        options.cookiejar = configuration.get_cookiejar()
        if options.save_cache:
            try:
                options.cookiejar.load_cookiejar(global_cookies)
            except Exception as e:
                logger.warning("Didn't load --save-cache %s\nContinue without loading cookies"%e)
            options.cookiejar.set_autosave(True,filename=global_cookies)
    else:
        configuration.set_cookiejar(options.cookiejar)

    return configuration

if __name__ == '__main__':
    ## this isn't actually used by pip installed CLI.
    ## that calls main() itself.
    main()
