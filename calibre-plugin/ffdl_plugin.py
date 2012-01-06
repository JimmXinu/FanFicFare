#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2012, Jim Miller'
__docformat__ = 'restructuredtext en'

import time, os
from ConfigParser import SafeConfigParser
from StringIO import StringIO
from functools import partial
from datetime import datetime

from PyQt4.Qt import (QApplication, QMenu, QToolButton)

from calibre.ptempfile import PersistentTemporaryFile, PersistentTemporaryDirectory, remove_dir
from calibre.ebooks.metadata import MetaInformation, authors_to_string
from calibre.ebooks.metadata.meta import get_metadata
from calibre.gui2 import error_dialog, warning_dialog, question_dialog, info_dialog
# The class that all interface action plugins must inherit from
from calibre.gui2.actions import InterfaceAction
from calibre.gui2.threaded_jobs import ThreadedJob

from calibre_plugins.fanfictiondownloader_plugin.common_utils import (set_plugin_icon_resources, get_icon,
                                         create_menu_action_unique, get_library_uuid)

from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader import adapters, writers, exceptions
from calibre_plugins.fanfictiondownloader_plugin.epubmerge import doMerge

from calibre_plugins.fanfictiondownloader_plugin.config import (prefs)
from calibre_plugins.fanfictiondownloader_plugin.dialogs import (
    AddNewDialog, UpdateExistingDialog, DisplayStoryListDialog,
    MetadataProgressDialog, UserPassDialog, AboutDialog,
    OVERWRITE, OVERWRITEALWAYS, UPDATE, UPDATEALWAYS, ADDNEW, SKIP, CALIBREONLY,
    NotGoingToDownload )

# because calibre immediately transforms html into zip and don't want
# to have an 'if html'.  db.has_format is cool with the case mismatch,
# but if I'm doing it anyway...
formmapping = {
    'epub':'EPUB',
    'mobi':'MOBI',
    'html':'ZIP',
    'txt':'TXT'
    }

PLUGIN_ICONS = ['images/icon.png']

class FanFictionDownLoaderPlugin(InterfaceAction):

    name = 'FanFictionDownLoader'

    # Declare the main action associated with this plugin
    # The keyboard shortcut can be None if you dont want to use a keyboard
    # shortcut. Remember that currently calibre has no central management for
    # keyboard shortcuts, so try to use an unusual/unused shortcut.
    # (text, icon_path, tooltip, keyboard shortcut)
    # icon_path isn't in the zip--icon loaded below.
    action_spec = (name, None,
                   'Download FanFiction stories from various web sites', None)

    action_type = 'global'
    # make button menu drop down only
    #popup_type = QToolButton.InstantPopup

    def genesis(self):
        # This method is called once per plugin, do initial setup here

        # Read the plugin icons and store for potential sharing with the config widget
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)
        
        # Show the config dialog
        # The config dialog can also be shown from within
        # Preferences->Plugins, which is why the do_user_config
        # method is defined on the base plugin class
        do_user_config = self.interface_action_base_plugin.do_user_config

        # Set the icon for this interface action
        # The get_icons function is a builtin function defined for all your
        # plugin code. It loads icons from the plugin zip file. It returns
        # QIcon objects, if you want the actual data, use the analogous
        # get_resources builtin function.

        # Note that if you are loading more than one icon, for performance, you
        # should pass a list of names to get_icons. In this case, get_icons
        # will return a dictionary mapping names to QIcons. Names that
        # are not found in the zip file will result in null QIcons.
        icon = get_icon('images/icon.png')

        # The qaction is automatically created from the action_spec defined
        # above
        self.qaction.setIcon(icon)

        # Call function when plugin triggered.
        self.qaction.triggered.connect(self.plugin_button)

        # Assign our menu to this action
        self.menu = QMenu(self.gui)
        self.qaction.setMenu(self.menu)

        self.menu.aboutToShow.connect(self.about_to_show_menu)

        self.actions_unique_map = {}

        self.add_action = self.create_menu_item_ex(self.menu, '&Add New from URL(s)', image='plus.png',
                                                   unique_name='Add New FanFiction Book(s) from URL(s)',
                                                   shortcut_name='Add New FanFiction Book(s) from URL(s)',
                                                   triggered=self.add_dialog )

        self.update_action = self.create_menu_item_ex(self.menu, '&Update Existing FanFiction Book(s)', image='plusplus.png',
                                                      unique_name='Update Existing FanFiction Book(s)',
                                                      shortcut_name='Update Existing FanFiction Book(s)',
                                                      triggered=self.update_existing) #partial(self._update_existing,'qwerty'))

        self.menu.addSeparator()
        self.config_action = create_menu_action_unique(self, self.menu, '&Configure Plugin', shortcut=False,
                                                       image= 'config.png',
                                                       unique_name='Configure FanFictionDownLoader',
                                                       shortcut_name='Configure FanFictionDownLoader',
                                                       triggered=partial(do_user_config,parent=self.gui))

        self.config_action = create_menu_action_unique(self, self.menu, '&About Plugin', shortcut=False,
                                                       image= 'images/icon.png',
                                                       unique_name='About FanFictionDownLoader',
                                                       shortcut_name='About FanFictionDownLoader',
                                                       triggered=self.about)


    def about_to_show_menu(self):
        self.update_action.setEnabled( len(self.gui.library_view.get_selected_ids()) > 0 )

    def about(self):
        # Get the about text from a file inside the plugin zip file
        # The get_resources function is a builtin function defined for all your
        # plugin code. It loads files from the plugin zip file. It returns
        # the bytes from the specified file.
        #
        # Note that if you are loading more than one file, for performance, you
        # should pass a list of names to get_resources. In this case,
        # get_resources will return a dictionary mapping names to bytes. Names that
        # are not found in the zip file will not be in the returned dictionary.
        text = get_resources('about.txt')
#        QMessageBox.about(self, 'About the FanFictionDownLoader Plugin',
 #               text.decode('utf-8'))
        AboutDialog(self.gui,self.qaction.icon(),text).exec_()
        
    def create_menu_item_ex(self, parent_menu, menu_text, image=None, tooltip=None,
                           shortcut=None, triggered=None, is_checked=None, shortcut_name=None,
                           unique_name=None):
        ac = create_menu_action_unique(self, parent_menu, menu_text, image, tooltip,
                                       shortcut, triggered, is_checked, shortcut_name, unique_name)
        self.actions_unique_map[ac.calibre_shortcut_unique_name] = ac.calibre_shortcut_unique_name
        return ac

    def plugin_button(self):
        if len(self.gui.library_view.get_selected_ids()) > 0 and prefs['updatedefault']:
            self.update_existing()
        else:
            self.add_dialog()
    
    def add_dialog(self):

        #print("add_dialog()")

        # Show the config dialog
        # The config dialog can also be shown from within
        # Preferences->Plugins, which is why the do_user_config
        # method is defined on the base plugin class
        do_user_config = self.interface_action_base_plugin.do_user_config

        url_list = self.get_urls_clip()
        url_list_text = "\n".join(url_list)
        
        # self.gui is the main calibre GUI. It acts as the gateway to access
        # all the elements of the calibre user interface, it should also be the
        # parent of the dialog
        # AddNewDialog just collects URLs, format and presents buttons.
        d = AddNewDialog(self.gui,
                         prefs,
                         self.qaction.icon(),
                         url_list_text,
                         )
        d.exec_()
        if d.result() != d.Accepted:
            return
        
        url_list = get_url_list(d.get_urlstext())
        add_books = self._convert_urls_to_books(url_list)
        #print("add_books:%s"%add_books)
        #print("options:%s"%d.get_ffdl_options())

        self.start_downloads( d.get_ffdl_options(),add_books )
        
    def update_existing(self):
        #print("update_existing()")
        previous = self.gui.library_view.currentIndex()
        db = self.gui.current_db
        book_ids = self.gui.library_view.get_selected_ids()
        books = self._convert_calibre_ids_to_books(db, book_ids)
        #print("update books:%s"%books)

        d = UpdateExistingDialog(self.gui,
                                 'Update Existing List',
                                 prefs,
                                 self.qaction.icon(),
                                 books,
                                 )
        d.exec_()
        if d.result() != d.Accepted:
            return

        update_books = d.get_books()

        #print("update_books:%s"%update_books)
        #print("options:%s"%d.get_ffdl_options())
        # only if there's some good ones.
        if 0 < len(filter(lambda x : x['good'], update_books)):
            self.start_downloads( d.get_ffdl_options(), update_books )
        
    def get_urls_clip(self):
        url_list = []
        if prefs['urlsfromclip']:
            for url in unicode(QApplication.instance().clipboard().text()).split():
                if( self._is_good_downloader_url(url) ):
                    url_list.append(url)
        return url_list

    def apply_settings(self):
        # No need to do anything with perfs here, but we could.
        prefs

    def start_downloads(self, options, books):

        #print("start_downloads:%s"%books)

        # create and pass temp dir.
        tdir = PersistentTemporaryDirectory(prefix='fanfictiondownloader_')
        options['tdir']=tdir

        self.gui.status_bar.show_message(_('Started fetching metadata for %s stories.'%len(books)), 3000)
        
        MetadataProgressDialog(self.gui,
                               books,
                               options,
                               partial(self.get_metadata_for_book, options = options),
                               partial(self.start_download_list, options = options))
        # MetadataProgressDialog calls get_adapter_for_story for each 'good' story,
        # get_adapter_for_story updates book for each,
        # MetadataProgressDialog calls download_list at the end which goes into the BG.
        # Not sure yet how I get back to display the 'do updates?' list.

    def get_metadata_for_book(self,book,
                              options={'fileform':'epub',
                                       'collision':ADDNEW,
                                       'updatemeta':True}):
        '''
        Update passed in book dict with metadata from website and
        necessary data.  To be called from MetadataProgressDialog
        'loop'.  Also pops dialogs for is adult, user/pass.
        '''
        
        # The current database shown in the GUI
        # db is an instance of the class LibraryDatabase2 from database.py
        # This class has many, many methods that allow you to do a lot of
        # things.
        db = self.gui.current_db
        
        fileform  = options['fileform']
        collision = options['collision']
        updatemeta= options['updatemeta']

        if not book['good']:
            # book has already been flagged bad for whatever reason.
            return
        
        url = book['url']
        
        ## was self.ffdlconfig, but we need to be able to change it
        ## when doing epub update.
        ffdlconfig = SafeConfigParser()
        ffdlconfig.readfp(StringIO(get_resources("defaults.ini")))
        ffdlconfig.readfp(StringIO(prefs['personal.ini']))
        adapter = adapters.getAdapter(ffdlconfig,url)

        #options['defaults.ini'] = get_resources("defaults.ini")
        options['personal.ini'] = prefs['personal.ini']

        try:
            adapter.getStoryMetadataOnly()
        except exceptions.FailedToLogin:
            print("Login Failed, Need Username/Password.")
            userpass = UserPassDialog(self.gui,url)
            userpass.exec_() # exec_ will make it act modal
            if userpass.status:
                adapter.username = userpass.user.text()
                adapter.password = userpass.passwd.text()
                
        except exceptions.AdultCheckRequired:
            if question_dialog(self.gui, 'Are You Adult?', '<p>'+
                               "%s requires that you be an adult.  Please confirm you are an adult in your locale:"%url,
                               show_copy_button=False):
                adapter.is_adult=True

        # let other exceptions percolate up.
        story = adapter.getStoryMetadataOnly()
        writer = writers.getWriter(options['fileform'],adapter.config,adapter)

        book['title'] = story.getMetadata("title", removeallentities=True)
        book['author_sort'] = book['author'] = story.getMetadata("author", removeallentities=True)
        book['publisher'] = story.getMetadata("site")
        book['tags'] = writer.getTags()
        book['pubdate'] = story.getMetadataRaw('datePublished')
        book['timestamp'] = story.getMetadataRaw('dateCreated')
        book['comments'] = story.getMetadata("description") #, removeallentities=True) comments handles entities better.
        
        # adapter.opener is the element with a threadlock.  But del
        # adapter.opener doesn't work--subproc fails when it tries
        # to pull in the adapter object that hasn't been imported yet.
        # book['adapter'] = adapter
        
        book['is_adult'] = adapter.is_adult
        book['username'] = adapter.username
        book['password'] = adapter.password

        book['icon'] = 'plus.png'
        
        if collision in (CALIBREONLY):
            book['icon'] = 'metadata.png'
        
        # XXX should really do a 'you can't do that' dialog when the
        # hit 'OK' for this case.
        if collision in (UPDATE,UPDATEALWAYS) and fileform != 'epub':
            raise NotGoingToDownload("Cannot update non-epub format.")
        
        book_id = None
        
        if book['calibre_id'] != None:
            # updating an existing book.  Update mode applies.
            print("update id:%s"%book['calibre_id'])            
            book_id = book['calibre_id']
            # No handling needed: OVERWRITEALWAYS,CALIBREONLY
            
        # only care about collisions when not ADDNEW
        elif collision != ADDNEW:
            # 'new' book from URL.  collision handling applies.
            print("from URL")

            # find dups
            mi = MetaInformation(story.getMetadata("title", removeallentities=True),
                                 (story.getMetadata("author", removeallentities=True),)) # author is a list.
            identicalbooks = db.find_identical_books(mi)
            ## removed for being overkill.
            # for ib in db.find_identical_books(mi):
            #     # only *really* identical if URL matches, too.
            #     # XXX make an option?
            #     if self._get_story_url(db,ib) == url:
            #         identicalbooks.append(ib)
            print("identicalbooks:%s"%identicalbooks)

            if collision == SKIP and identicalbooks:
                raise NotGoingToDownload("Skipping duplicate story.","list_remove.png")

            if len(identicalbooks) > 1:
                raise NotGoingToDownload("More than one identical book--can't tell which to update/overwrite.","minusminus.png")

            if collision == CALIBREONLY and not identicalbooks:
                raise NotGoingToDownload("Not updating Calibre Metadata, no existing book to update.","search_delete_saved.png")

            if len(identicalbooks)>0:
                book_id = identicalbooks.pop()
                book['calibre_id'] = book_id
                book['icon'] = 'edit-redo.png'

        if book_id != None and collision != ADDNEW:
            if options['collision'] in (CALIBREONLY):
                book['comment'] = 'Metadata collected.'
                # don't need temp file created below.
                return
            
            ## newer/chaptercount checks are the same for both:
            # Update epub, but only if more chapters.
            if collision == UPDATE:
                # 'book' can exist without epub.  If there's no existing epub,
                # let it go and it will download it.
                if db.has_format(book_id,fileform,index_is_id=True):
                    toupdateio = StringIO()
                    (epuburl,chaptercount) = doMerge(toupdateio,
                                                     [StringIO(db.format(book_id,'EPUB',
                                                                              index_is_id=True))],
                                                     titlenavpoints=False,
                                                     striptitletoc=True,
                                                     forceunique=False)
    
                    urlchaptercount = int(story.getMetadata('numChapters'))
                    if chaptercount == urlchaptercount: # and not onlyoverwriteifnewer:
                        raise NotGoingToDownload("Already contains %d chapters."%chaptercount,'edit-undo.png')
                    elif chaptercount > urlchaptercount:
                        raise NotGoingToDownload("Existing epub contains %d chapters, web site only has %d." % (chaptercount,urlchaptercount),'dialog_error.png')
    
            if collision == OVERWRITE and \
                    db.has_format(book_id,formmapping[fileform],index_is_id=True):
                # check make sure incoming is newer.
                lastupdated=story.getMetadataRaw('dateUpdated').date()
                fileupdated=datetime.fromtimestamp(os.stat(db.format_abspath(book_id, formmapping[fileform], index_is_id=True))[8]).date()
                if fileupdated > lastupdated:
                    raise NotGoingToDownload("Not Overwriting, web site is not newer.",'edit-undo.png')
    
            # For update, provide a tmp file copy of the existing epub so
            # it can't change underneath us.
            if collision in (UPDATE,UPDATEALWAYS) and \
                    db.has_format(book['calibre_id'],'EPUB',index_is_id=True):
                tmp = PersistentTemporaryFile(prefix='old-%s-'%book['calibre_id'],
                                              suffix='.epub',
                                              dir=options['tdir'])
                db.copy_format_to(book_id,fileform,tmp,index_is_id=True)
                print("existing epub tmp:"+tmp.name)
                book['epub_for_update'] = tmp.name

        if book['good']: # there shouldn't be any !'good' books at this point.
            # if still 'good', make a temp file to write the output to.
            tmp = PersistentTemporaryFile(prefix='new-%s-'%book['calibre_id'],
                                               suffix='.'+options['fileform'],
                                               dir=options['tdir'])
            print("outfile:"+tmp.name)
            book['outfile'] = tmp.name            
                
        return
        
        # if collision != ADDNEW:
        #     mi = MetaInformation(story.getMetadata("title"),
        #                          (story.getMetadata("author"),)) # author is a list.

        #     identicalbooks = self.db.find_identical_books(mi)
        #     ## more than one match will need to be handled differently.
        #     if identicalbooks:
        #         book_id = identicalbooks.pop()
        #         if collision == SKIP:
        #             raise NotGoingToDownload("Skipping duplicate story.")

        #         if collision == OVERWRITE and len(identicalbooks) > 1:
        #             raise NotGoingToDownload("More than one identical books--can't tell which to overwrite.")

        #         if collision == OVERWRITE and \
        #                 onlyoverwriteifnewer and \
        #                 self.db.has_format(book_id,fileform,index_is_id=True):
        #             # check make sure incoming is newer.
        #             lastupdated=story.getMetadataRaw('dateUpdated').date()
        #             fileupdated=datetime.fromtimestamp(os.stat(self.db.format_abspath(book_id, fileform, index_is_id=True))[8]).date()
        #             if fileupdated > lastupdated:
        #                 raise NotGoingToDownload("Not Overwriting, story is not newer.")

        #         if collision == UPDATE:
        #             if fileform != 'epub':
        #                 raise NotGoingToDownload("Not updating non-epub format.")
        #             # 'book' can exist without epub.  If there's no existing epub,
        #             # let it go and it will download it.
        #             if self.db.has_format(book_id,fileform,index_is_id=True):
        #                 toupdateio = StringIO()
        #                 (epuburl,chaptercount) = doMerge(toupdateio,
        #                                                  [StringIO(self.db.format(book_id,'EPUB',
        #                                                                           index_is_id=True))],
        #                                                  titlenavpoints=False,
        #                                                  striptitletoc=True,
        #                                                  forceunique=False)

        #                 urlchaptercount = int(story.getMetadata('numChapters'))
        #                 if chaptercount == urlchaptercount: # and not onlyoverwriteifnewer:
        #                     raise NotGoingToDownload("%s already contains %d chapters." % (url,chaptercount))
        #                 elif chaptercount > urlchaptercount:
        #                     raise NotGoingToDownload("%s contains %d chapters, more than epub." % (url,chaptercount))
        #                 else:
        #                     print("Do update - epub(%d) vs url(%d)" % (chaptercount, urlchaptercount))

        #     else: # not identicalbooks
        #         if collision == CALIBREONLY:
        #             raise NotGoingToDownload("Not updating Calibre Metadata, no existing book to update.")

        # return adapter

    def start_download_list(self,book_list,
                            options={'fileform':'epub',
                                     'collision':ADDNEW,
                                     'updatemeta':True}):
        '''
        Called by MetadataProgressDialog to start story downloads BG processing.
        adapter_list is a list of tuples of (url,adapter)
        '''
        #print("start_download_list:book_list:%s"%book_list)

        ## No need to BG process when CALIBREONLY!  Fake it.
        if options['collision'] in (CALIBREONLY):
            class NotJob(object):
                def __init__(self,result):
                    self.failed=False
                    self.result=result
            notjob = NotJob(book_list)
            self.download_list_completed(notjob,options=options)
            return

        for book in book_list:
            if book['good']:
                break
        else:
            ## No good stories to try to download, go straight to
            ## list.
            d = DisplayStoryListDialog(self.gui,
                                       'Nothing to Download',
                                       prefs,
                                       self.qaction.icon(),
                                       book_list,
                                       label_text='None of the URLs/stories given can be/need to be downloaded.'
                                       )
            d.exec_()
            return
            
        func = 'arbitrary_n'
        cpus = self.gui.job_manager.server.pool_size
        #print("cpus:%s <<<======================================"%cpus)
        # XXX - option for parallel downloads?
        args = ['calibre_plugins.fanfictiondownloader_plugin.jobs', 'do_download_worker',
                (book_list, options, cpus)]
        desc = 'Download FanFiction Book'
        job = self.gui.job_manager.run_job(
                self.Dispatcher(partial(self.download_list_completed,options=options)),
                func, args=args,
                description=desc)
        
        self.gui.status_bar.show_message('Starting %d FanFictionDownLoads'%len(book_list),3000)

    def download_list_completed(self, job, options={}):
        if job.failed:
            self.gui.job_exception(job, dialog_title='Failed to Download Stories')
            return
        #print("download_list_completed job:%s"%job.result)
        # for b in job.result:
        #     print("job.result: %s"%b['title'])

        db = self.gui.current_db

        d = DisplayStoryListDialog(self.gui,
                                   'Downloads finished, confirm to update Calibre',
                                   prefs,
                                   self.qaction.icon(),
                                   job.result,
                                   label_text='Stories will not be added or updated in Calibre without confirmation.'
                                   )
        d.exec_()
        if d.result() == d.Accepted:
            
            ## in case the user removed any from the list.
            book_list = d.get_books()
            # for b in book_list:
            #     print("d list: %s"%b['title'])

            update_list = filter(lambda x : x['good'] and x['calibre_id'] != None,
                                 book_list)

            add_list = filter(lambda x : x['good'] and x['calibre_id'] == None,
                              book_list)

            total_good = len(update_list)+len(add_list)

            self.gui.status_bar.show_message(_('Adding/Updating %s books.'%total_good), 3000)
            
            print("==================================================")
            addfiles,addfileforms,addmis=[],[],[]
            
            added=0
            for book in add_list:
                print("adding %s %s"%(book['title'],book['url']))
                addfiles.append(book['outfile'])
                addfileforms.append(options['fileform'])
                addmis.append(self._make_mi_from_book(book))
                    
            (notadded,added)=db.add_books(addfiles,addfileforms,addmis,
                                               add_duplicates=True)

            print("==================================================")
            updated=0
            for book in update_list:
                print("updating (%s)%s %s"%(book['calibre_id'],book['title'],book['url']))

                if options['collision'] == CALIBREONLY:
                    updated += 1
                else:
                    if not db.add_format_with_hooks(book['calibre_id'], options['fileform'], book['outfile'], index_is_id=True):
                        book['comment'] = "Adding format to book failed for some reason..."
                        book['good']=False
                        book['icon']='dialog_error.png'
                    else:
                        updated += 1
                        # get all formats.
                        if prefs['deleteotherforms']:
                            fmts = set([x.lower() for x in db.formats(book['calibre_id'], index_is_id=True).split(',')])
                            for fmt in fmts:
                                if fmt != options['fileform']:
                                    print("remove f:"+fmt)
                                    db.remove_format(book['calibre_id'], fmt, index_is_id=True)#, notify=False

                if options['collision'] == CALIBREONLY or \
                        (options['updatemeta'] or book['good']) :
                    db.set_metadata(book['calibre_id'],
                                    self._make_mi_from_book(book))
                    
            if added:
                self.gui.library_view.model().books_added(added)

            # the refresh causes problems sometimes?  Switching libraries
            # and back cleared it?
            self.gui.library_view.model().refresh()

            self.gui.status_bar.show_message(_('Finished Adding/Updating %d books.'%(updated + added)), 3000)
            
            if updated + added != total_good:
                d = DisplayStoryListDialog(self.gui,
                                           'Updates completed, final status',
                                           prefs,
                                           self.qaction.icon(),
                                           book_list,
                                           label_text='Stories have be added or updated in Calibre, some had additional problems.'
                                           )
                d.exec_()
    
        print("all done, remove temp dir.")
        remove_dir(options['tdir'])


    def _make_mi_from_book(self,book):
        mi = MetaInformation(book['title'],(book['author'],)) # author is a list.
        mi.set_identifiers({'url':book['url']})
        mi.publisher = book['publisher']
        mi.tags = book['tags']
        #mi.languages = ['en']
        mi.pubdate = book['pubdate']
        mi.timestamp = book['timestamp']
        mi.comments = book['comments']
        return mi


    def _convert_urls_to_books(self, urls):
        books = []
        for url in urls:
            book = {}
            book['good'] = True
            book['calibre_id'] = None
            book['title'] = 'Unknown'
            book['author'] = 'Unknown'
            book['author_sort'] = 'Unknown'
                
            book['comment'] = ''
            book['url'] = ''
            
            self._set_book_url_and_comment(book,url)
                    
            books.append(book)
        return books
    
    def _convert_calibre_ids_to_books(self, db, ids):
        books = []
        for book_id in ids:
            mi = db.get_metadata(book_id, index_is_id=True)
            book = {}
            book['good'] = True
            book['calibre_id'] = mi.id
            book['title'] = mi.title
            book['author'] = authors_to_string(mi.authors)
            book['author_sort'] = mi.author_sort
            # book['series'] = mi.series
            # if mi.series:
            #     book['series_index'] = mi.series_index
            # else:
            #     book['series_index'] = 0
                
            book['comment'] = ''
            book['url'] = ""
            
            url = self._get_story_url(db,book_id)
            self._set_book_url_and_comment(book,url)
                    
            books.append(book)
        return books

    def _set_book_url_and_comment(self,book,url):
        if not url:
            book['comment'] = "No story URL found."
            book['good'] = False
            book['icon'] = 'search_delete_saved.png'
        else:
            # get normalized url or None.
            book['url'] = self._is_good_downloader_url(url)
            if book['url'] == None:
                book['url'] = url
                book['comment'] = "URL is not a valid story URL."
                book['good'] = False
                book['icon']='dialog_error.png'
    
    def _get_story_url(self, db, book_id):
        identifiers = db.get_identifiers(book_id,index_is_id=True)
        if 'url' in identifiers:
            # identifiers have :->| in url.
            #print("url from book:"+identifiers['url'].replace('|',':'))
            return identifiers['url'].replace('|',':')
        else:
            ## only epub has URL in it.
            if db.has_format(book_id,'EPUB',index_is_id=True):
                existingepub = db.format(book_id,'EPUB',index_is_id=True, as_file=True)
                mi = get_metadata(existingepub,'EPUB')
                #print("mi:%s"%mi)
                identifiers = mi.get_identifiers()
                if 'url' in identifiers:
                    #print("url from epub:"+identifiers['url'].replace('|',':'))
                    return identifiers['url'].replace('|',':')
        return None

    def _is_good_downloader_url(self,url):
        # this is the accepted way to 'check for existance'?  really?
        try:
            self.dummyconfig
        except AttributeError:
            self.dummyconfig = SafeConfigParser()
        # pulling up an adapter is pretty low over-head.  If
        # it fails, it's a bad url.
        try:
            adapter = adapters.getAdapter(self.dummyconfig,url)
            url = adapter.url
            del adapter
            return url
        except:
            return None;



def get_job_details(job):
    '''
    Convert the job result into a set of parameters including a detail message
    summarising the success of the extraction operation.
    This is used by both the threaded and worker approaches to extraction
    '''
    extracted_ids, same_isbn_ids, failed_ids, no_format_ids = job.result
    if not hasattr(job, 'html_details'):
        job.html_details = job.details
    det_msg = []
    for i, title in failed_ids:
        if i in no_format_ids:
            msg = title + ' (No formats)'
        else:
            msg = title + ' (ISBN not found)'
        det_msg.append(msg)
    if same_isbn_ids:
        if det_msg:
            det_msg.append('----------------------------------')
        for i, title in same_isbn_ids:
            msg = title + ' (Same ISBN)'
            det_msg.append(msg)
    if len(extracted_ids) > 0:
        if det_msg:
            det_msg.append('----------------------------------')
        for i, title, last_modified, isbn in extracted_ids:
            msg = '%s (Extracted %s)'%(title, isbn)
            det_msg.append(msg)

    det_msg = '\n'.join(det_msg)
    return extracted_ids, same_isbn_ids, failed_ids, det_msg

def get_url_list(urls):
    def f(x):
        if x.strip(): return True
        else: return False
    # set removes dups.
    return set(filter(f,urls.strip().splitlines()))

############################################################################3
        
    # def do_story_downloads(self, adaptertuple_list, fileform, db,
    #                        **kwargs):
    #     '''
    #     Master job, loop to download this list of stories
    #     '''
    #     print("do_story_downloads")
    #     abort = kwargs['abort']
    #     notifications=kwargs['notifications']
    #     log = kwargs['log']
    #     notifications.put((0.01, 'Start Downloading Stories'))
    #     count = 0.01
    #     total = len(adaptertuple_list)
    #     # Queue all the jobs
    #     for (url,adapter) in adaptertuple_list:
    #         if abort.is_set():
    #             notifications.put(1.0,'Aborting...')
    #             return
    #         notifications.put((float(count)/total,
    #                            'Downloading %s'%adapter.getStoryMetadataOnly().getMetadata("title")))
    #         log.prints(log.INFO,'Downloading %s'%adapter.getStoryMetadataOnly().getMetadata("title"))
    #         try:
    #             self.do_story_download(adapter,fileform,db,
    #                                    kwargs['collision'],kwargs['updatemeta'],kwargs['onlyoverwriteifnewer'])
    #         except Exception as e:
    #             log.prints(log.ERROR,'Failed Downloading %s: %s'%
    #                        (adapter.getStoryMetadataOnly().getMetadata("title"),e))

    #         count = count + 1
    #     return

    # def do_story_download(self,adapter,fileform,db,collision,
    #                       updatemeta,onlyoverwriteifnewer):
    #     print("do_story_download")

    #     story = adapter.getStoryMetadataOnly()

    #     mi = MetaInformation(story.getMetadata("title"),
    #                          (story.getMetadata("author"),)) # author is a list.

    #     writer = writers.getWriter(fileform,adapter.config,adapter)
    #     tmp = PersistentTemporaryFile("."+fileform)
    #     titleauth = "%s by %s"%(story.getMetadata("title"), story.getMetadata("author"))
    #     url = story.getMetadata("storyUrl")
    #     print(titleauth)
    #     print("tmp: "+tmp.name)

    #     mi.set_identifiers({'url':story.getMetadata("storyUrl")})
    #     mi.publisher = story.getMetadata("site")
    #     mi.tags = writer.getTags()
    #     mi.languages = ['en']
    #     mi.pubdate = story.getMetadataRaw('datePublished')
    #     mi.timestamp = story.getMetadataRaw('dateCreated')
    #     mi.comments = story.getMetadata("description")

    #     identicalbooks = self.db.find_identical_books(mi)
    #     #print(identicalbooks)
    #     added=0
    #     if identicalbooks and collision != ADDNEW:
    #         ## more than one match?  add to first off the list.
    #         ## Shouldn't happen--we checked above.
    #         book_id = identicalbooks.pop()

    #         if collision == UPDATE:
    #             if self.db.has_format(book_id,fileform,index_is_id=True):
    #                 urlchaptercount = int(story.getMetadata('numChapters'))
    #                 ## First, get existing epub with titlepage and tocpage stripped.
    #                 updateio = StringIO()
    #                 (epuburl,chaptercount) = doMerge(updateio,
    #                                                  [StringIO(self.db.format(book_id,'EPUB',
    #                                                                           index_is_id=True))],
    #                                                  titlenavpoints=False,
    #                                                  striptitletoc=True,
    #                                                  forceunique=False)
    #                 print("Do update - epub(%d) vs url(%d)" % (chaptercount, urlchaptercount))

    #                 ## Get updated title page/metadata by itself in an epub.
    #                 ## Even if the title page isn't included, this carries the metadata.
    #                 titleio = StringIO()
    #                 writer.writeStory(outstream=titleio,metaonly=True)

    #                 newchaptersio = None
    #                 if urlchaptercount > chaptercount :
    #                     ## Go get the new chapters only in another epub.
    #                     newchaptersio = StringIO()
    #                     adapter.setChaptersRange(chaptercount+1,urlchaptercount)

    #                     adapter.config.set("overrides",'include_tocpage','false')
    #                     adapter.config.set("overrides",'include_titlepage','false')
    #                     writer.writeStory(outstream=newchaptersio)

    #                 ## Merge the three epubs together.
    #                 doMerge(tmp,
    #                         [titleio,updateio,newchaptersio],
    #                         fromfirst=True,
    #                         titlenavpoints=False,
    #                         striptitletoc=False,
    #                         forceunique=False)


    #             else: # update, but there's no epub extant, so do overwrite.
    #                 collision = OVERWRITE

    #         if collision == OVERWRITE:
    #             writer.writeStory(tmp)

    #         db.add_format_with_hooks(book_id, fileform, tmp, index_is_id=True)

    #         # get all formats.
    #         if prefs['deleteotherforms'] and collision in (OVERWRITE, UPDATE):
    #             fmts = set([x.lower() for x in db.formats(book_id, index_is_id=True).split(',')])
    #             for fmt in fmts:
    #                 if fmt != fileform:
    #                     print("remove f:"+fmt)
    #                     db.remove_format(book_id, fmt,index_is_id=True)#, notify=False

    #         if updatemeta or collision == CALIBREONLY:
    #             db.set_metadata(book_id,mi)

    #     else: # no matching, adding new.
    #         writer.writeStory(tmp)
    #         (notadded,added)=db.add_books([tmp],[fileform],[mi], add_duplicates=True)

    #     # Otherwise list of books doesn't update right away.
    #     if added:
    #         self.gui.library_view.model().books_added(added)

    #     # the refresh causes problems sometimes?  Switching libraries
    #     # and back cleared it?
    #     self.gui.library_view.model().refresh()

    #     del adapter
    #     del writer
