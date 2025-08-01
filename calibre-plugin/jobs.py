# -*- coding: utf-8 -*-

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2020, Jim Miller, 2011, Grant Drake <grant.drake@gmail.com>'
__docformat__ = 'restructuredtext en'

import logging
logger = logging.getLogger(__name__)

from time import sleep
from datetime import time
from io import StringIO
from collections import defaultdict
import sys

from calibre.utils.date import local_tz

# pulls in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

# ------------------------------------------------------------------------------
#
#              Functions to perform downloads using worker jobs
#
# ------------------------------------------------------------------------------

def do_download_worker_single(site,
                              book_list,
                              options,
                              merge,
                              notification=lambda x,y:x):

    logger.info(options['version'])

    ## same info debug calibre prints out at startup. For when users
    ## give me job output instead of debug log.
    from calibre.debug import print_basic_debug_info
    print_basic_debug_info(sys.stderr)

    notification(0.01, _('Downloading FanFiction Stories'))

    count = 0
    totals = {}
    # can't do direct assignment in list comprehension?  I'm sure it
    # makes sense to some pythonista.
    # [ totals[x['url']]=0.0 for x in book_list if x['good'] ]
    [ totals.update({x['url']:0.0}) for x in book_list if x['good']  ]
    # logger.debug(sites_lists.keys())

    def do_indiv_notif(percent,msg):
        totals[msg] = percent/len(totals)
        notification(max(0.01,sum(totals.values())), _('%(count)d of %(total)d stories finished downloading')%{'count':count,'total':len(totals)})

    do_list = []
    done_list = []
    ## pass failures from metadata through bg job so all results are
    ## together.
    for book in book_list:
        if book['good']:
            do_list.append(book)
        else:
            done_list.append(book)
    for book in do_list:
        # logger.info("%s"%book['url'])
        done_list.append(do_download_for_worker(book,options,merge,do_indiv_notif))
        count += 1
    return finish_download(done_list)

def finish_download(donelist):
    book_list = sorted(donelist,key=lambda x : x['listorder'])
    logger.info("\n"+_("Download Results:")+"\n%s\n"%("\n".join([ "%(status)s %(url)s %(comment)s" % book for book in book_list])))

    good_lists = defaultdict(list)
    bad_lists = defaultdict(list)
    for book in book_list:
        if book['good']:
            good_lists[book['status']].append(book)
        else:
            bad_lists[book['status']].append(book)

    order = [_('Add'),
             _('Update'),
             _('Meta'),
             _('Different URL'),
             _('Rejected'),
             _('Skipped'),
             _('Bad'),
             _('Error'),
             ]
    stnum = 0
    for d in [ good_lists, bad_lists ]:
        for status in order:
            stnum += 1
            if d[status]:
                l = d[status]
                logger.info("\n"+status+"\n%s\n"%("\n".join([book['url'] for book in l])))
                for book in l:
                    # Add prior listorder to 10000 * status num for
                    # ordering of accumulated results with multiple bg
                    # jobs
                    book['reportorder'] = stnum*10000 + book['listorder']
            del d[status]
        # just in case a status is added but doesn't appear in order.
        for status in d.keys():
            logger.info("\n"+status+"\n%s\n"%("\n".join([book['url'] for book in d[status]])))

    # return the book list as the job result
    return book_list

def do_download_site(site,book_list,options,merge,notification=lambda x,y:x):
    # logger.info(_("Started job for %s")%site)
    retval = []
    for book in book_list:
        # logger.info("%s"%book['url'])
        retval.append(do_download_for_worker(book,options,merge,notification))
        notification(10.0,book['url'])
    return retval

def do_download_for_worker(book,options,merge,notification=lambda x,y:x):
    '''
    Child job, to download story when run as a worker job
    '''

    from calibre_plugins.fanficfare_plugin import FanFicFareBase
    fffbase = FanFicFareBase(options['plugin_path'])
    with fffbase: # so the sys.path was modified while loading the
                  # plug impl.
        from calibre_plugins.fanficfare_plugin.dialogs import NotGoingToDownload
        from calibre_plugins.fanficfare_plugin.prefs import (
                SAVE_YES, SAVE_YES_UNLESS_SITE, OVERWRITE, OVERWRITEALWAYS, UPDATE,
                UPDATEALWAYS, ADDNEW, SKIP, CALIBREONLY, CALIBREONLYSAVECOL)
        from calibre_plugins.fanficfare_plugin.wordcount import get_word_count
        from fanficfare import adapters, writers
        from fanficfare.epubutils import get_update_data
        from fanficfare.six import text_type as unicode

        from calibre_plugins.fanficfare_plugin.fff_util import get_fff_config

        try:
            logger.info("\n\n" + ("-"*80) + " " + book['url'])
            ## No need to download at all.  Can happen now due to
            ## collision moving into book for CALIBREONLY changing to
            ## ADDNEW when story URL not in library.
            if book['collision'] in (CALIBREONLY, CALIBREONLYSAVECOL):
                logger.info("Skipping CALIBREONLY 'update' down inside worker")
                return book

            book['comment'] = _('Download started...')

            configuration = get_fff_config(book['url'],
                                            options['fileform'],
                                            options['personal.ini'])

            # images only for epub, html, even if the user mistakenly
            # turned it on else where.
            if options['fileform'] not in ("epub","html"):
                configuration.set("overrides","include_images","false")

            adapter = adapters.getAdapter(configuration,book['url'])
            adapter.is_adult = book['is_adult']
            adapter.username = book['username']
            adapter.password = book['password']
            adapter.totp = book['totp']
            adapter.setChaptersRange(book['begin'],book['end'])

            ## each site download job starts with a new copy of the
            ## cookiejar and basic_cache from the FG process.  They
            ## are not shared between different sites' BG downloads
            if 'basic_cache' in options:
                configuration.set_basic_cache(options['basic_cache'])
            else:
                options['basic_cache'] = configuration.get_basic_cache()
                options['basic_cache'].load_cache(options['basic_cachefile'])
            if 'cookiejar' in options:
                configuration.set_cookiejar(options['cookiejar'])
            else:
                options['cookiejar'] = configuration.get_cookiejar()
                options['cookiejar'].load_cookiejar(options['cookiejarfile'])

            story = adapter.getStoryMetadataOnly()
            if not story.getMetadata("series") and 'calibre_series' in book:
                adapter.setSeries(book['calibre_series'][0],book['calibre_series'][1])

            # logger.debug(merge)
            # logger.debug(book.get('epub_for_update','(NONE)'))
            # logger.debug(options.get('mergebook','(NOMERGEBOOK)'))

            # is a merge, is a pre-existing anthology, and is not a pre-existing book in anthology.
            if merge and 'mergebook' in options and 'epub_for_update' not in book:
                # internal for plugin anthologies to mark chapters
                # (new) in new stories
                story.setMetadata("newforanthology","true")
            logger.debug("metadata newforanthology:%s"%story.getMetadata("newforanthology"))

            # set PI version instead of default.
            if 'version' in options:
                story.setMetadata('version',options['version'])

            book['title'] = story.getMetadata("title", removeallentities=True)
            book['author_sort'] = book['author'] = story.getList("author", removeallentities=True)
            book['publisher'] = story.getMetadata("publisher")
            book['url'] = story.getMetadata("storyUrl", removeallentities=True)
            book['comments'] = story.get_sanitized_description()
            book['series'] = story.getMetadata("series", removeallentities=True)

            if story.getMetadataRaw('datePublished'):
                book['pubdate'] = story.getMetadataRaw('datePublished').replace(tzinfo=local_tz)
            if story.getMetadataRaw('dateUpdated'):
                book['updatedate'] = story.getMetadataRaw('dateUpdated').replace(tzinfo=local_tz)
            if story.getMetadataRaw('dateCreated'):
                book['timestamp'] = story.getMetadataRaw('dateCreated').replace(tzinfo=local_tz)
            else:
                book['timestamp'] = datetime.now().replace(tzinfo=local_tz) # need *something* there for calibre.

            writer = writers.getWriter(options['fileform'],configuration,adapter)
            outfile = book['outfile']

            ## checks were done earlier, it's new or not dup or newer--just write it.
            if book['collision'] in (ADDNEW, SKIP, OVERWRITE, OVERWRITEALWAYS) or \
                    ('epub_for_update' not in book and book['collision'] in (UPDATE, UPDATEALWAYS)):

                # preserve logfile even on overwrite.
                if 'epub_for_update' in book:
                    adapter.logfile = get_update_data(book['epub_for_update'])[6]
                    # change the existing entries id to notid so
                    # write_epub writes a whole new set to indicate overwrite.
                    if adapter.logfile:
                        adapter.logfile = adapter.logfile.replace("span id","span notid")

                if book['collision'] == OVERWRITE and 'fileupdated' in book:
                    lastupdated=story.getMetadataRaw('dateUpdated')
                    fileupdated=book['fileupdated']

                    # updated doesn't have time (or is midnight), use dates only.
                    # updated does have time, use full timestamps.
                    if (lastupdated.time() == time.min and fileupdated.date() > lastupdated.date()) or \
                            (lastupdated.time() != time.min and fileupdated > lastupdated):
                        raise NotGoingToDownload(_("Not Overwriting, web site is not newer."),'edit-undo.png',showerror=False)


                logger.info("write to %s"%outfile)
                inject_cal_cols(book,story,configuration)
                writer.writeStory(outfilename=outfile,
                                  forceOverwrite=True,
                                  notification=notification)

                if adapter.story.chapter_error_count > 0:
                    book['comment'] = _('Download %(fileform)s completed, %(failed)s failed chapters, %(total)s total chapters.')%\
                        {'fileform':options['fileform'],
                         'failed':adapter.story.chapter_error_count,
                         'total':story.getMetadata("numChapters")}
                    book['chapter_error_count'] = adapter.story.chapter_error_count
                else:
                    book['comment'] = _('Download %(fileform)s completed, %(total)s chapters.')%\
                        {'fileform':options['fileform'],
                         'total':story.getMetadata("numChapters")}
                book['all_metadata'] = story.getAllMetadata(removeallentities=True)
                if options['savemetacol'] != '':
                    book['savemetacol'] = story.dump_html_metadata()

            ## checks were done earlier, just update it.
            elif 'epub_for_update' in book and book['collision'] in (UPDATE, UPDATEALWAYS):

                # update now handled by pre-populating the old images and
                # chapters in the adapter rather than merging epubs.
                #urlchaptercount = int(story.getMetadata('numChapters').replace(',',''))
                # returns int adjusted for start-end range.
                urlchaptercount = story.getChapterCount()
                (url,
                 chaptercount,
                 adapter.oldchapters,
                 adapter.oldimgs,
                 adapter.oldcover,
                 adapter.calibrebookmark,
                 adapter.logfile,
                 adapter.oldchaptersmap,
                 adapter.oldchaptersdata) = get_update_data(book['epub_for_update'])[0:9]

                # dup handling from fff_plugin needed for anthology updates & BG metadata.
                if book['collision'] in (UPDATE,UPDATEALWAYS):
                    if chaptercount == urlchaptercount and book['collision'] == UPDATE:
                        if merge:
                            ## Deliberately pass for UPDATEALWAYS merge.
                            book['comment']=_("Already contains %d chapters.  Reuse as is.")%chaptercount
                            book['all_metadata'] = story.getAllMetadata(removeallentities=True)
                            if options['savemetacol'] != '':
                                book['savemetacol'] = story.dump_html_metadata()
                            book['outfile'] = book['epub_for_update'] # for anthology merge ops.
                            return book
                        else:
                            raise NotGoingToDownload(_("Already contains %d chapters.")%chaptercount,'edit-undo.png',showerror=False)
                    elif chaptercount > urlchaptercount and not (book['collision'] == UPDATEALWAYS and adapter.getConfig('force_update_epub_always')):
                        raise NotGoingToDownload(_("Existing epub contains %d chapters, web site only has %d. Use Overwrite or force_update_epub_always to force update.") % (chaptercount,urlchaptercount),'dialog_error.png')
                    elif chaptercount == 0:
                        raise NotGoingToDownload(_("FanFicFare doesn't recognize chapters in existing epub, epub is probably from a different source. Use Overwrite to force update."),'dialog_error.png')

                if not (book['collision'] == UPDATEALWAYS and chaptercount == urlchaptercount) \
                        and adapter.getConfig("do_update_hook"):
                    chaptercount = adapter.hookForUpdates(chaptercount)

                logger.info("Do update - epub(%d) vs url(%d)" % (chaptercount, urlchaptercount))
                logger.info("write to %s"%outfile)

                inject_cal_cols(book,story,configuration)
                writer.writeStory(outfilename=outfile,
                                  forceOverwrite=True,
                                  notification=notification)

                if adapter.story.chapter_error_count > 0:
                    book['comment'] = _('Update %(fileform)s completed, added %(added)s chapters, %(failed)s failed chapters, for %(total)s total.')%\
                        {'fileform':options['fileform'],
                         'failed':adapter.story.chapter_error_count,
                         'added':(urlchaptercount-chaptercount),
                         'total':urlchaptercount}
                    book['chapter_error_count'] = adapter.story.chapter_error_count
                else:
                    book['comment'] = _('Update %(fileform)s completed, added %(added)s chapters for %(total)s total.')%\
                        {'fileform':options['fileform'],'added':(urlchaptercount-chaptercount),'total':urlchaptercount}
                book['all_metadata'] = story.getAllMetadata(removeallentities=True)
                if options['savemetacol'] != '':
                    book['savemetacol'] = story.dump_html_metadata()
            else:
                ## Shouldn't ever get here, but hey, it happened once
                ## before with prefs['collision']
                raise Exception("Impossible state reached -- Book: %s:\nOptions:%s:"%(book,options))

            if options['do_wordcount'] == SAVE_YES or (
                options['do_wordcount'] == SAVE_YES_UNLESS_SITE and not story.getMetadataRaw('numWords') ):
                try:
                    wordcount = get_word_count(outfile)
                    # logger.info("get_word_count:%s"%wordcount)
                    # clear cache for the rather unusual case of
                    # numWords affecting other previously cached
                    # entries.
                    story.clear_processed_metadata_cache()
                    story.setMetadata('numWords',wordcount)
                    writer.writeStory(outfilename=outfile, forceOverwrite=True)
                    book['all_metadata'] = story.getAllMetadata(removeallentities=True)
                    if options['savemetacol'] != '':
                        book['savemetacol'] = story.dump_html_metadata()
                except:
                    logger.error("WordCount failed")

            if options['smarten_punctuation'] and options['fileform'] == "epub":
                # for smarten punc
                from calibre.ebooks.oeb.polish.main import polish, ALL_OPTS
                from calibre.utils.logging import Log
                from collections import namedtuple

                # do smarten_punctuation from calibre's polish feature
                data = {'smarten_punctuation':True}
                opts = ALL_OPTS.copy()
                opts.update(data)
                O = namedtuple('Options', ' '.join(ALL_OPTS.keys()))
                opts = O(**opts)

                log = Log(level=Log.DEBUG)
                polish({outfile:outfile}, opts, log, logger.info)
            ## here to catch tags set in chapters in literotica for
            ## both overwrites and updates.
            book['tags'] = story.getSubjectTags(removeallentities=True)
        except NotGoingToDownload as d:
            book['good']=False
            book['status']=_('Bad')
            book['showerror']=d.showerror
            book['comment']=unicode(d)
            book['icon'] = d.icon

        except Exception as e:
            book['good']=False
            book['status']=_('Error')
            book['comment']=unicode(e)
            book['icon']='dialog_error.png'
            book['status'] = _('Error')
            logger.info("Exception: %s:%s"%(book,book['comment']),exc_info=True)
    return book

## calibre's columns for an existing book are passed in and injected
## into the story's metadata.  For convenience, we also add labels and
## valid_entries for them in a special [injected] section that has
## even less precedence than [defaults]
def inject_cal_cols(book,story,configuration):
    configuration.remove_section('injected')
    if 'calibre_columns' in book:
        injectini = ['[injected]']
        extra_valid = []
        for k in book['calibre_columns'].keys():
            v = book['calibre_columns'][k]
            story.setMetadata(k,v['val'])
            injectini.append('%s_label:%s'%(k,v['label']))
            extra_valid.append(k)
        if extra_valid: # if empty, there's nothing to add.
            injectini.append("add_to_extra_valid_entries:,"+','.join(extra_valid))
            configuration.read_file(StringIO('\n'.join(injectini)))
            #print("added:\n%s\n"%('\n'.join(injectini)))
