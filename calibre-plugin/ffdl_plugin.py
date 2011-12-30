#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2011, Jim Miller'
__docformat__ = 'restructuredtext en'

import ConfigParser, os
from StringIO import StringIO
from functools import partial
from datetime import datetime

from PyQt4.Qt import (QApplication)

# The class that all interface action plugins must inherit from
from calibre.ptempfile import PersistentTemporaryFile
from calibre.ebooks.metadata import MetaInformation
from calibre.ebooks.metadata.meta import get_metadata
from calibre.gui2 import error_dialog, warning_dialog, question_dialog, info_dialog
from calibre.gui2.actions import InterfaceAction
from calibre.gui2.threaded_jobs import ThreadedJob

from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader import adapters, writers, exceptions
from calibre_plugins.fanfictiondownloader_plugin.epubmerge import doMerge

from calibre_plugins.fanfictiondownloader_plugin.config import (prefs, CLIP, SELECTED)
from calibre_plugins.fanfictiondownloader_plugin.dialogs import (
    DownloadDialog, MetadataProgressDialog, UserPassDialog,
    OVERWRITE, UPDATE, ADDNEW, SKIP, CALIBREONLY, NotGoingToDownload )

# because calibre immediately transforms html into zip and don't want
# to have an 'if html'.  db.has_format is cool with the case mismatch,
# but if I'm doing it anyway...
formmapping = {
    'epub':'EPUB',
    'mobi':'MOBI',
    'html':'ZIP',
    'txt':'TXT'
    }

class FanFictionDownLoaderPlugin(InterfaceAction):

    name = 'FanFictionDownLoader'

    # Declare the main action associated with this plugin
    # The keyboard shortcut can be None if you dont want to use a keyboard
    # shortcut. Remember that currently calibre has no central management for
    # keyboard shortcuts, so try to use an unusual/unused shortcut.
    # (text, icon_path, tooltip, keyboard shortcut)
    # icon_path isn't in the zip--icon loaded below.
    action_spec = ('FanFictionDownLoader', None,
                   'Download FanFiction stories from various web sites', None)

    action_type = 'global'
    
    def genesis(self):
        # This method is called once per plugin, do initial setup here

        # Set the icon for this interface action
        # The get_icons function is a builtin function defined for all your
        # plugin code. It loads icons from the plugin zip file. It returns
        # QIcon objects, if you want the actual data, use the analogous
        # get_resources builtin function.
        #
        # Note that if you are loading more than one icon, for performance, you
        # should pass a list of names to get_icons. In this case, get_icons
        # will return a dictionary mapping names to QIcons. Names that
        # are not found in the zip file will result in null QIcons.
        icon = get_icons('images/icon.png')
        
        # The qaction is automatically created from the action_spec defined
        # above
        self.qaction.setIcon(icon)
        # Call function when plugin triggered.
        self.qaction.triggered.connect(self.show_dialog)

    def show_dialog(self):
        # The base plugin object defined in __init__.py
        base_plugin_object = self.interface_action_base_plugin
        # Show the config dialog
        # The config dialog can also be shown from within
        # Preferences->Plugins, which is why the do_user_config
        # method is defined on the base plugin class
        do_user_config = base_plugin_object.do_user_config

        # The current database shown in the GUI
        # db is an instance of the class LibraryDatabase2 from database.py
        # This class has many, many methods that allow you to do a lot of
        # things.
        self.db = self.gui.current_db

        # pre-pop urls from selected stories or clipboard.  but with
        # configurable priority and on/off option on each
        if prefs['urlsfrompriority'] == SELECTED:
            from_first_func = self.get_urls_select
            from_second_func = self.get_urls_clip
        elif prefs['urlsfrompriority'] == CLIP:
            from_first_func = self.get_urls_clip
            from_second_func = self.get_urls_select

        url_list_text = from_first_func()
        if not url_list_text:
            url_list_text = from_second_func()

            #'''http://test1.com?sid=6
#''')
# http://test1.com?sid=6701
# http://test1.com?sid=6702
# http://test1.com?sid=6703
# http://test1.com?sid=6704
# http://test1.com?sid=6705
# http://test1.com?sid=6706
# http://test1.com?sid=6707
# http://test1.com?sid=6708
# http://test1.com?sid=6709

            
        # self.gui is the main calibre GUI. It acts as the gateway to access
        # all the elements of the calibre user interface, it should also be the
        # parent of the dialog
        # DownloadDialog just collects URLs, format and presents buttons.
        d = DownloadDialog(self.gui,
                           prefs,
                           self.qaction.icon(),
                           url_list_text,
                           do_user_config,  # method for config button
                           self.start_downloads, # method to start downloads
                           )
        d.show()

    ## if there's rows selected, try to find a source URL from
    ## either identifier in the metadata, or from the epub
    ## metadata.
    def get_urls_select(self):
        url_list = []
        rows = self.gui.library_view.selectionModel().selectedRows()
        if rows and prefs['urlsfromselected']:
            book_ids = self.gui.library_view.get_selected_ids()
            print("book_ids: %s"%book_ids)
            for book_id in book_ids:
                identifiers = self.db.get_identifiers(book_id,index_is_id=True) 
                if 'url' in identifiers:
                    # identifiers have :->| in url.
                    #print("url from book:"+identifiers['url'].replace('|',':'))
                    url_list.append(identifiers['url'].replace('|',':'))
                else:
                    ## only epub has that in it.
                    if self.db.has_format(book_id,'EPUB',index_is_id=True):
                        existingepub = self.db.format(book_id,'EPUB',index_is_id=True, as_file=True)
                        mi = get_metadata(existingepub,'EPUB')
                        #print("mi:%s"%mi)
                        identifiers = mi.get_identifiers()
                        if 'url' in identifiers:
                            #print("url from epub:"+identifiers['url'].replace('|',':'))
                            url_list.append(identifiers['url'].replace('|',':'))
        return self.get_valid_urls(url_list)
        
    def get_urls_clip(self):
        url_list = []
        if prefs['urlsfromclip']:
            # no rows selected, check for valid URLs in the clipboard.
            cliptext = unicode(QApplication.instance().clipboard().text())
            url_list.extend(cliptext.split())
        return self.get_valid_urls(url_list)

    def get_valid_urls(self,url_list):
        url_list_text = ""
            
        # Check and make sure the URLs are valid ffdl URLs.
        if url_list:
            # this is the accepted way to 'check for existance'?  really?
            try:
                self.dummyconfig
            except AttributeError:
                self.dummyconfig = ConfigParser.SafeConfigParser()
                
            alreadyin=[]
            for url in url_list:
                if url in alreadyin:
                    continue
                alreadyin.append(url)
                # pulling up an adapter is pretty low over-head.  If
                # it fails, it's a bad url.
                try:
                    adapters.getAdapter(self.dummyconfig,url)
                except:
                    pass
                else:
                    if url_list_text:
                        url_list_text += "\n"
                    url_list_text += url
                    
        return url_list_text
    
    def apply_settings(self):
        # No need to do anything with perfs here, but we could.
        prefs

    def start_downloads(self,urls,fileform,
                        collision,updatemeta,onlyoverwriteifnewer):

        url_list = get_url_list(urls)

        self.fetchmeta_qpd = \
            MetadataProgressDialog(self.gui,
                                   url_list,
                                   fileform,
                                   partial(self.get_adapter_for_story, collision=collision,onlyoverwriteifnewer=onlyoverwriteifnewer),
                                   partial(self.download_list,collision=collision,updatemeta=updatemeta,onlyoverwriteifnewer=onlyoverwriteifnewer),
                                   self.db)
            
    def get_adapter_for_story(self,url,fileform,
                              collision=SKIP,
                              onlyoverwriteifnewer=False):
        '''
        Returns adapter object for story at URL.  To be called from
        MetadataProgressDialog 'loop' to build up list of adapters.  Also
        pops dialogs for is adult, user/pass, duplicate
        '''
        
        print("URL:"+url)
        ## was self.ffdlconfig, but we need to be able to change it
        ## when doing epub update.
        ffdlconfig = ConfigParser.SafeConfigParser()
        ffdlconfig.readfp(StringIO(get_resources("defaults.ini")))
        ffdlconfig.readfp(StringIO(prefs['personal.ini']))
        adapter = adapters.getAdapter(ffdlconfig,url)

        try:
            adapter.getStoryMetadataOnly()
        except exceptions.FailedToLogin:
            print("Login Failed, Need Username/Password.")
            userpass = UserPassDialog(self.gui,url)
            userpass.exec_() # exec_ will make it act modal
            if userpass.status:
                adapter.username = userpass.user.text()
                adapter.password = userpass.passwd.text()
            # else:
            #     del adapter
            #     return
        except exceptions.AdultCheckRequired:
            if question_dialog(self.gui, 'Are You Adult?', '<p>'+
                               "%s requires that you be an adult.  Please confirm you are an adult in your locale:"%url,
                               show_copy_button=False):
                adapter.is_adult=True
            # else:
            #     del adapter
            #     return

        # let exceptions percolate up.
        story = adapter.getStoryMetadataOnly()

        if collision != ADDNEW:
            mi = MetaInformation(story.getMetadata("title"),
                                 (story.getMetadata("author"),)) # author is a list.

            identicalbooks = self.db.find_identical_books(mi)
            print(identicalbooks)
            ## more than one match will need to be handled differently.
            if identicalbooks:
                book_id = identicalbooks.pop()
                if collision == SKIP:
                    raise NotGoingToDownload("Skipping duplicate story.")

                if collision == OVERWRITE and len(identicalbooks) > 1:
                    raise NotGoingToDownload("More than one identical books--can't tell which to overwrite.")

                if collision == OVERWRITE and \
                        onlyoverwriteifnewer and \
                        self.db.has_format(book_id,fileform,index_is_id=True):
                    # check make sure incoming is newer.
                    lastupdated=story.getMetadataRaw('dateUpdated').date()
                    fileupdated=datetime.fromtimestamp(os.stat(self.db.format_abspath(book_id, fileform, index_is_id=True))[8]).date()
                    if fileupdated > lastupdated:
                        raise NotGoingToDownload("Not Overwriting, story is not newer.")

                if collision == UPDATE:
                    if fileform != 'epub':
                        raise NotGoingToDownload("Not updating non-epub format.")
                    # 'book' can exist without epub.  If there's no existing epub,
                    # let it go and it will download it.
                    if self.db.has_format(book_id,fileform,index_is_id=True):
                        toupdateio = StringIO()
                        (epuburl,chaptercount) = doMerge(toupdateio,
                                                         [StringIO(self.db.format(book_id,'EPUB',
                                                                                  index_is_id=True))],
                                                         titlenavpoints=False,
                                                         striptitletoc=True,
                                                         forceunique=False)
                
                        urlchaptercount = int(story.getMetadata('numChapters'))
                        if chaptercount == urlchaptercount: # and not onlyoverwriteifnewer:
                            raise NotGoingToDownload("%s already contains %d chapters." % (url,chaptercount))
                        elif chaptercount > urlchaptercount:
                            raise NotGoingToDownload("%s contains %d chapters, more than epub." % (url,chaptercount))
                        else:
                            print("Do update - epub(%d) vs url(%d)" % (chaptercount, urlchaptercount))
                    
            else: # not identicalbooks
                if collision == CALIBREONLY:
                    raise NotGoingToDownload("Not updating Calibre Metadata, no existing book to update.")

        return adapter
        
    def download_list(self,adaptertuple_list,fileform,
                      collision=ADDNEW,
                      updatemeta=True,
                      onlyoverwriteifnewer=True):
        '''
        Called by MetadataProgressDialog to start story downloads BG processing.
        adapter_list is a list of tuples of (url,adapter)
        '''
        print("download_list")
        
        job = ThreadedJob('FanFictionDownload',
                          'Downloading FanFiction Stories',
                          func=self.do_story_downloads,
                          args=(adaptertuple_list, fileform, self.db),
                          kwargs={'collision':collision,'updatemeta':updatemeta,
                                  'onlyoverwriteifnewer':onlyoverwriteifnewer},
                          callback=self._get_stories_completed)
        
        
        self.gui.job_manager.run_threaded_job(job)
        
        self.gui.status_bar.show_message('Downloading %d stories'%len(adaptertuple_list))

    def _get_stories_completed(self, job):
        print("_get_stories_completed")

    def do_story_downloads(self, adaptertuple_list, fileform, db,
                           **kwargs):
        '''
        Master job, loop to download this list of stories
        '''
        print("do_story_downloads")
        abort = kwargs['abort']
        notifications=kwargs['notifications']
        log = kwargs['log']
        notifications.put((0.01, 'Start Downloading Stories'))
        count = 0.01
        total = len(adaptertuple_list)
        # Queue all the jobs
        for (url,adapter) in adaptertuple_list:
            if abort.is_set():
                notifications.put(1.0,'Aborting...')
                return
            notifications.put((float(count)/total,
                               'Downloading %s'%adapter.getStoryMetadataOnly().getMetadata("title")))
            log.prints(log.INFO,'Downloading %s'%adapter.getStoryMetadataOnly().getMetadata("title"))
            try:
                self.do_story_download(adapter,fileform,db,
                                       kwargs['collision'],kwargs['updatemeta'],kwargs['onlyoverwriteifnewer'])
            except Exception as e:
                log.prints(log.ERROR,'Failed Downloading %s: %s'%
                           (adapter.getStoryMetadataOnly().getMetadata("title"),e))
                
            count = count + 1
        return
    
    def do_story_download(self,adapter,fileform,db,collision,
                          updatemeta,onlyoverwriteifnewer):
        print("do_story_download")
    
        story = adapter.getStoryMetadataOnly()
    
        mi = MetaInformation(story.getMetadata("title"),
                             (story.getMetadata("author"),)) # author is a list.
        
        writer = writers.getWriter(fileform,adapter.config,adapter)
        tmp = PersistentTemporaryFile("."+fileform)
        titleauth = "%s by %s"%(story.getMetadata("title"), story.getMetadata("author"))
        url = story.getMetadata("storyUrl")
        print(titleauth)
        print("tmp: "+tmp.name)

        mi.set_identifiers({'url':story.getMetadata("storyUrl")})
        mi.publisher = story.getMetadata("site")    
        mi.tags = writer.getTags()
        mi.languages = ['en']
        mi.pubdate = story.getMetadataRaw('datePublished')
        mi.timestamp = story.getMetadataRaw('dateCreated')
        mi.comments = story.getMetadata("description")
    
        identicalbooks = self.db.find_identical_books(mi)
        #print(identicalbooks)
        addedcount=0
        if identicalbooks and collision != ADDNEW:
            ## more than one match?  add to first off the list.
            ## Shouldn't happen--we checked above.
            book_id = identicalbooks.pop()
            if collision == UPDATE:
                if self.db.has_format(book_id,fileform,index_is_id=True):
                    urlchaptercount = int(story.getMetadata('numChapters'))
                    ## First, get existing epub with titlepage and tocpage stripped.
                    updateio = StringIO()
                    (epuburl,chaptercount) = doMerge(updateio,
                                                     [StringIO(self.db.format(book_id,'EPUB',
                                                                              index_is_id=True))],
                                                     titlenavpoints=False,
                                                     striptitletoc=True,
                                                     forceunique=False)
                    print("Do update - epub(%d) vs url(%d)" % (chaptercount, urlchaptercount))

                    ## Get updated title page/metadata by itself in an epub.
                    ## Even if the title page isn't included, this carries the metadata.
                    titleio = StringIO()
                    writer.writeStory(outstream=titleio,metaonly=True)
                    
                    newchaptersio = None
                    if urlchaptercount > chaptercount :
                        ## Go get the new chapters only in another epub.
                        newchaptersio = StringIO()
                        adapter.setChaptersRange(chaptercount+1,urlchaptercount)

                        adapter.config.set("overrides",'include_tocpage','false')
                        adapter.config.set("overrides",'include_titlepage','false')
                        writer.writeStory(outstream=newchaptersio)

                    ## Merge the three epubs together.
                    doMerge(tmp,
                            [titleio,updateio,newchaptersio],
                            fromfirst=True,
                            titlenavpoints=False,
                            striptitletoc=False,
                            forceunique=False)

                    
                else: # update, but there's no epub extant, so do overwrite.
                    collision = OVERWRITE
                    
            if collision == OVERWRITE:
                writer.writeStory(tmp)

            db.add_format_with_hooks(book_id, fileform, tmp, index_is_id=True)

            # get all formats.
            # fmts = set([x.lower() for x in db.formats(book_id, index_is_id=True).split(',')])
            # for fmt in fmts:
            #     if fmt != fileform:
            #         print("f:"+fmt)
            #         ## calling convert doesn't work here because we're in a BG thread.
            #         # (jobs,changed,bad)=convert_single_ebook(self.gui,
            #         #                      db,
            #         #                      [book_id],
            #         #                      auto_conversion=True,
            #         #                      out_format=fmt)
            #         # print("jobs:%s changed:%s bad:%s"%(jobs,changed,bad))
            #         db.remove_format(book_id, fmt,index_is_id=True)#, notify=False

            # for a in self.gui.iactions: # ['Convert Books']
            #     print("a:%s"%a)


            if updatemeta or collision == CALIBREONLY:
                db.set_metadata(book_id,mi)
                
        else: # no matching, adding new.
            writer.writeStory(tmp)
            (notadded,addedcount)=db.add_books([tmp],[fileform],[mi], add_duplicates=True)
            
            
        # Otherwise list of books doesn't update right away.
        if addedcount:
            self.gui.library_view.model().books_added(addedcount)

        self.gui.library_view.model().refresh()
        #self.gui.library_view.model().research()
        #self.gui.tags_view.recount()
    
        del adapter
        del writer

def f(x):
    if x.strip(): return True
    else: return False
    
def get_url_list(urls):
    return filter(f,urls.strip().splitlines())
