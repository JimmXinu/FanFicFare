# -*- coding: utf-8 -*-

# Copyright 2015 Fanficdownloader team, 2018 FanFicFare team
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

from optparse import OptionParser, SUPPRESS_HELP
from os.path import expanduser, join, dirname
from os import access, R_OK
from subprocess import call
from six import StringIO
import six.moves.configparser
import getpass
import logging
import pprint
import string
import sys

import pickle
import http.cookiejar as cl

version="2.27.8"

if sys.version_info < (3,0):
    print('this program requires python 3 or newer.')
    sys.exit(1)

# if sys.version_info >= (2, 7):
#     # suppresses default logger.  logging is setup in fanficfare/__init__.py so it works in calibre, too.
#     rootlogger = logging.getlogger()
#     loghandler = logging.nullhandler()
#     loghandler.setformatter(logging.formatter('(=====)(levelname)s:%(message)s'))
#     rootlogger.addhandler(loghandler)

logger = logging.getLogger('fanficfare')

try:
    # running under calibre
    from calibre_plugins.fanficfare_plugin.fanficfare import adapters, writers, exceptions
    from calibre_plugins.fanficfare_plugin.fanficfare.configurable import configuration
    from calibre_plugins.fanficfare_plugin.fanficfare.epubutils import (
        get_dcsource_chaptercount, get_update_data, reset_orig_chapters_epub)
    from calibre_plugins.fanficfare_plugin.fanficfare.geturls import get_urls_from_page, get_urls_from_imap
except ImportError:
    from fanficfare import adapters, writers, exceptions
    from fanficfare.configurable import configuration
    from fanficfare.epubutils import (
        get_dcsource_chaptercount, get_update_data, reset_orig_chapters_epub)
    from fanficfare.geturls import get_urls_from_page, get_urls_from_imap


def write_story(config, adapter, writeformat, metaonly=false, outstream=none):
    writer = writers.getwriter(writeformat, config, adapter)
    writer.writestory(outstream=outstream, metaonly=metaonly)
    output_filename = writer.getoutputfilename()
    del writer
    return output_filename

def main(argv=none,
         parser=none,
         passed_defaultsini=none,
         passed_personalini=none):
    if argv is none:
        argv = sys.argv[1:]
    # read in args, anything starting with -- will be treated as --<varible>=<value>
    if not parser:
        parser = optionparser('usage: %prog [options] [storyurl]...')
    parser.add_option('-f', '--format', dest='format', default='epub',
                      help='write story as format, epub(default), mobi, txt or html', metavar='format')
    if passed_defaultsini:
        config_help = 'read config from specified file(s) in addition to calibre plugin personal.ini, ~/.fanficfare/personal.ini, and ./personal.ini'
    else:
        config_help = 'read config from specified file(s) in addition to ~/.fanficfare/defaults.ini, ~/.fanficfare/personal.ini, ./defaults.ini, and ./personal.ini'
    parser.add_option('-c', '--config',
                      action='append', dest='configfile', default=none,
                      help=config_help, metavar='config')
    range_help = '  --begin and --end will be overridden by a chapter range on the storyurl like storyurl[1-2], storyurl[-3], storyurl[3-] or storyurl[3]'
    parser.add_option('-b', '--begin', dest='begin', default=none,
                      help='begin with chapter start.'+range_help, metavar='start')
    parser.add_option('-e', '--end', dest='end', default=none,
                      help='end with chapter end.'+range_help, metavar='end')
    parser.add_option('-o', '--option',
                      action='append', dest='options',
                      help='set an option name=value', metavar='name=value')
    parser.add_option('-m', '--meta-only',
                      action='store_true', dest='metaonly',
                      help='retrieve metadata and stop.  or, if --update-epub, update metadata title page only.', )
    parser.add_option('--json-meta',
                      action='store_true', dest='jsonmeta',
                      help='when used with --meta-only, output metadata as json.  no effect without --meta-only flag', )
    parser.add_option('-u', '--update-epub',
                      action='store_true', dest='update',
                      help='update an existing epub(if present) with new chapters.  give either epub filename or story url.', )
    parser.add_option('--update-cover',
                      action='store_true', dest='updatecover',
                      help='update cover in an existing epub, otherwise existing cover (if any) is used on update.  only valid with --update-epub.', )
    parser.add_option('--unnew',
                      action='store_true', dest='unnew',
                      help='remove (new) chapter marks left by mark_new_chapters setting.', )
    parser.add_option('--force',
                      action='store_true', dest='force',
                      help='force overwrite of an existing epub, download and overwrite all chapters.', )
    parser.add_option('-i', '--infile',
                      help='give a filename to read for urls (and/or existing epub files with --update-epub).',
                      dest='infile', default=none,
                      metavar='infile')

    parser.add_option('-l', '--list',
                      dest='list', default=none, metavar='url',
                      help='get list of valid story urls from page given.', )
    parser.add_option('-n', '--normalize-list',
                      dest='normalize', default=none, metavar='url',
                      help='get list of valid story urls from page given, but normalized to standard forms.', )
    parser.add_option('--download-list',
                      dest='downloadlist', default=none, metavar='url',
                      help='download story urls retrieved from page given.  update existing epubs if used with --update-epub.', )

    parser.add_option('--imap',
                      action='store_true', dest='imaplist',
                      help='get list of valid story urls from unread email from imap account configured in ini.', )

    parser.add_option('--download-imap',
                      action='store_true', dest='downloadimap',
                      help='download valid story urls from unread email from imap account configured in ini.  update existing epubs if used with --update-epub.', )

    parser.add_option('-s', '--sites-list',
                      action='store_true', dest='siteslist', default=false,
                      help='get list of valid story urls examples.', )
    parser.add_option('--non-interactive',
                      action='store_false', dest='interactive', default=sys.stdin.isatty() and sys.stdout.isatty(),
                      help='prevent interactive prompts (for scripting).', )
    parser.add_option('-d', '--debug',
                      action='store_true', dest='debug',
                      help='show debug and notice output.', )
    parser.add_option('-p', '--progressbar',
                      action='store_true', dest='progressbar',
                      help='display a simple progress bar while downloading--one dot(.) per network fetch.', )
    parser.add_option('-v', '--version',
                      action='store_true', dest='version',
                      help='display version and quit.', )

    ## undocumented feature for development use.  save page cache and
    ## cookies between runs.  saves in pwd as files global_cache and
    ## global_cookies
    parser.add_option('--save-cache', '--save_cache',
                      action='store_true', dest='save_cache',
                      help=suppress_help, )

    options, args = parser.parse_args(argv)

    if options.version:
        print("version: %s" % version)
        return

    if not options.debug:
        logger.setlevel(logging.warning)

    list_only = any((options.imaplist,
                     options.siteslist,
                     options.list,
                     options.normalize,
                     ))

    if list_only and (args or any((options.downloadimap,
                                   options.downloadlist))):
        parser.error('incorrect arguments: cannot download and list urls at the same time.')

    if options.siteslist:
        for site, examples in adapters.getsiteexamples():
            print('\n#### %s\nexample urls:' % site)
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
        retlist = get_urls_from_page(options.normalize, configuration,normalize=true)
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
        markread = configuration.getconfig('imap_mark_read') == 'true' or \
            (configuration.getconfig('imap_mark_read') == 'downloadonly' and options.downloadimap)
        retlist = get_urls_from_imap(configuration.getconfig('imap_server'),
                                     configuration.getconfig('imap_username'),
                                     configuration.getconfig('imap_password'),
                                     configuration.getconfig('imap_folder'),
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
            with open('global_cache','rb') as jin:
                options.pagecache = pickle.load(jin) # ,encoding="utf-8"
            options.cookiejar = cl.lwpcookiejar()
            options.cookiejar.load('global_cookies')
        except:
            print("didn't load global_cache")

    if not list_only:
        if len(urls) < 1:
            print("no valid story urls found")
        else:
            for url in urls:
                try:
                    do_download(url,
                                options,
                                passed_defaultsini,
                                passed_personalini)
                #print("pagecache:%s"%options.pagecache.keys())
                except exception as e:
                    if len(urls) == 1:
                        raise
                    print("url(%s) failed: exception (%s). run url individually for more detail."%(url,e))

    if options.save_cache:
        with open('global_cache','wb') as jout:
            pickle.dump(options.pagecache,jout)
        options.cookiejar.save('global_cookies')

# make rest a function and loop on it.
def do_download(arg,
                options,
                passed_defaultsini,
                passed_personalini):

    # attempt to update an existing epub.
    chaptercount = none
    output_filename = none

    if options.unnew:
        # remove mark_new_chapters marks
        reset_orig_chapters_epub(arg,arg)
        return

    if options.update:
        try:
            url, chaptercount = get_dcsource_chaptercount(arg)
            if not url:
                print('no story url found in epub to update.')
                return
            print('updating %s, url: %s' % (arg, url))
            output_filename = arg
        except exception:
            # if there's an error reading the update file, maybe it's a url?
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
        # allow chapter range with url.
        # like test1.com?sid=5[4-6] or [4,6]
        # overrides cli options if present.
        url,ch_begin,ch_end = adapters.get_url_chapter_range(url)

        adapter = adapters.getadapter(configuration, url)

        ## share pagecache and cookiejar between multiple downloads.
        if not hasattr(options,'pagecache'):
            options.pagecache = configuration.get_empty_pagecache()
        if not hasattr(options,'cookiejar'):
            options.cookiejar = configuration.get_empty_cookiejar()
        configuration.set_pagecache(options.pagecache)
        configuration.set_cookiejar(options.cookiejar)

        # url[begin-end] overrides cli option if present.
        if ch_begin or ch_end:
            adapter.setchaptersrange(ch_begin, ch_end)
        else:
            adapter.setchaptersrange(options.begin, options.end)

        # check for updating from url (vs from file)
        if options.update and not chaptercount:
            try:
                writer = writers.getwriter('epub', configuration, adapter)
                output_filename = writer.getoutputfilename()
                noturl, chaptercount = get_dcsource_chaptercount(output_filename)
                print('updating %s, url: %s' % (output_filename, url))
            except exception:
                options.update = false
                pass

        # check for include_images without no_image_processing. in absence of pil, give warning.
        if adapter.getconfig('include_images') and not adapter.getconfig('no_image_processing'):
            try:
                from calibre.utils.magick import image
            except importerror:
                try:
                    ## pillow is a more current fork of pil library
                    from pil import image
                except importerror:
                    try:
                        import image
                    except importerror:
                        print("you have include_images enabled, but python image library(pil) isn't found.\nimages will be included full size in original format.\ncontinue? (y/n)?")
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
                adapter.getstorymetadataonly()
            except exceptions.failedtologin as f:
                if not options.interactive:
                    print('login failed on non-interactive process. set username and password in personal.ini.')
                    return
                if f.passwdonly:
                    print('story requires a password.')
                else:
                    print('login failed, need username/password.')
                    sys.stdout.write('username: ')
                    adapter.username = sys.stdin.readline().strip()
                adapter.password = getpass.getpass(prompt='password: ')
                # print('login: `%s`, password: `%s`' % (adapter.username, adapter.password))
            except exceptions.adultcheckrequired:
                if options.interactive:
                    print('please confirm you are an adult in your locale: (y/n)?')
                    if sys.stdin.readline().strip().lower().startswith('y'):
                        adapter.is_adult = true
                else:
                    print('adult check required on non-interactive process. set is_adult:true in personal.ini or pass -o "is_adult=true" to the command.')
                    return

        if options.update and not options.force:
            urlchaptercount = int(adapter.getstorymetadataonly().getmetadata('numchapters').replace(',',''))
            # returns int adjusted for start-end range.
            urlchaptercount = adapter.getstorymetadataonly().getchaptercount()

            if chaptercount == urlchaptercount and not options.metaonly:
                print('%s already contains %d chapters.' % (output_filename, chaptercount))
            elif chaptercount > urlchaptercount:
                print('%s contains %d chapters, more than source: %d.' % (output_filename, chaptercount, urlchaptercount))
            elif chaptercount == 0:
                print("%s doesn't contain any recognizable chapters, probably from a different source.  not updating." % output_filename)
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

                print('do update - epub(%d) vs url(%d)' % (chaptercount, urlchaptercount))

                if not options.update and chaptercount == urlchaptercount and adapter.getconfig('do_update_hook'):
                    adapter.hookforupdates(chaptercount)

                if adapter.getconfig('pre_process_safepattern'):
                    metadata = adapter.story.get_filename_safe_metadata(pattern=adapter.getconfig('pre_process_safepattern'))
                else:
                    metadata = adapter.story.getallmetadata()
                call(string.template(adapter.getconfig('pre_process_cmd')).substitute(metadata), shell=true)

                write_story(configuration, adapter, 'epub')

        else:
            # regular download
            if options.metaonly:
                metadata = adapter.getstorymetadataonly().getallmetadata()
                metadata['zchapters'] = []
                for i, chap in enumerate(adapter.get_chapters()):
                    metadata['zchapters'].append((i+1,chap))

            if not options.metaonly and adapter.getconfig('pre_process_cmd'):
                if adapter.getconfig('pre_process_safepattern'):
                    metadata = adapter.story.get_filename_safe_metadata(pattern=adapter.getconfig('pre_process_safepattern'))
                else:
                    metadata = adapter.story.getallmetadata()
                call(string.template(adapter.getconfig('pre_process_cmd')).substitute(metadata), shell=true)

            output_filename = write_story(configuration, adapter, options.format, options.metaonly)

            if options.metaonly:
                metadata['output_filename'] = output_filename
                if options.jsonmeta:
                    import json
                    print(json.dumps(metadata, sort_keys=true,
                                     indent=2, separators=(',', ':')))
                else:
                    pprint.pprint(metadata)

        if not options.metaonly and adapter.getconfig('post_process_cmd'):
            if adapter.getconfig('post_process_safepattern'):
                metadata = adapter.story.get_filename_safe_metadata(pattern=adapter.getconfig('post_process_safepattern'))
            else:
                metadata = adapter.story.getallmetadata()
            metadata['output_filename'] = output_filename
            call(string.template(adapter.getconfig('post_process_cmd')).substitute(metadata), shell=true)

        del adapter

    except exceptions.invalidstoryurl as isu:
        print(isu)
    except exceptions.storydoesnotexist as dne:
        print(dne)
    except exceptions.unknownsite as us:
        print(us)
    except exceptions.accessdenied as ad:
        print(ad)

def get_configuration(url,
                      passed_defaultsini,
                      passed_personalini,
                      options,
                      chaptercount=none,
                      output_filename=none):
    try:
        configuration = configuration(adapters.getconfigsectionsfor(url), options.format)
    except exceptions.unknownsite as e:
        if options.list or options.normalize or options.downloadlist:
            # list for page doesn't have to be a supported site.
            configuration = configuration(['unknown'], options.format)
        else:
            raise e

    conflist = []
    homepath = join(expanduser('~'), '.fanficdownloader')
    ## also look for .fanficfare now, give higher priority than old dir.
    homepath2 = join(expanduser('~'), '.fanficfare')

    if passed_defaultsini:
        # new stringio each time rather than pass stringio and rewind
        # for case of list download.  just makes more sense to me.
        configuration.readfp(stringio(passed_defaultsini))
    else:
        # don't need to check existance for our selves.
        conflist.append(join(dirname(__file__), 'defaults.ini'))
        conflist.append(join(homepath, 'defaults.ini'))
        conflist.append(join(homepath2, 'defaults.ini'))
        conflist.append('defaults.ini')

    if passed_personalini:
        # new stringio each time rather than pass stringio and rewind
        # for case of list download.  just makes more sense to me.
        configuration.readfp(stringio(passed_personalini))

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
