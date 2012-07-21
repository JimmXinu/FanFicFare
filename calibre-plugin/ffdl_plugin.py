#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2012, Jim Miller'
__docformat__ = 'restructuredtext en'

import time, os, copy, threading, re
from ConfigParser import SafeConfigParser
from StringIO import StringIO
from functools import partial
from datetime import datetime
from string import Template

from PyQt4.Qt import (QApplication, QMenu, QToolButton)

from PyQt4.Qt import QPixmap, Qt
from PyQt4.QtCore import QBuffer

from calibre.constants import numeric_version as calibre_version

from calibre.ptempfile import PersistentTemporaryFile, PersistentTemporaryDirectory, remove_dir
from calibre.ebooks.metadata import MetaInformation, authors_to_string
from calibre.ebooks.metadata.meta import get_metadata
from calibre.gui2 import error_dialog, warning_dialog, question_dialog, info_dialog
from calibre.gui2.dialogs.message_box import ViewLog
from calibre.gui2.dialogs.confirm_delete import confirm
from calibre.utils.date import local_tz

# The class that all interface action plugins must inherit from
from calibre.gui2.actions import InterfaceAction

from calibre_plugins.fanfictiondownloader_plugin.common_utils import (set_plugin_icon_resources, get_icon,
                                         create_menu_action_unique, get_library_uuid)

from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader import adapters, writers, exceptions
from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader.htmlcleanup import stripHTML
from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader.epubutils import get_dcsource, get_dcsource_chaptercount, get_story_url_from_html
from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader.geturls import get_urls_from_page

from calibre_plugins.fanfictiondownloader_plugin.config import (prefs, permitted_values)
from calibre_plugins.fanfictiondownloader_plugin.dialogs import (
    AddNewDialog, UpdateExistingDialog, display_story_list, DisplayStoryListDialog,
    LoopProgressDialog, UserPassDialog, AboutDialog, CollectURLDialog, 
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
                   'Download FanFiction stories from various web sites', ())
    # None for keyboard shortcut doesn't allow shortcut.  () does, there just isn't one yet

    action_type = 'global'
    # make button menu drop down only
    #popup_type = QToolButton.InstantPopup

    def genesis(self):

        # This method is called once per plugin, do initial setup here

        # Read the plugin icons and store for potential sharing with the config widget
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)
        
        base = self.interface_action_base_plugin
        self.version = base.name+" v%d.%d.%d"%base.version

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

        #self.qaction.setText('FFDL')
        
        # The qaction is automatically created from the action_spec defined
        # above
        self.qaction.setIcon(icon)

        # Call function when plugin triggered.
        self.qaction.triggered.connect(self.plugin_button)

        # Assign our menu to this action
        self.menu = QMenu(self.gui)
        self.old_actions_unique_map = {}
        # menu_actions is just to keep a live reference to the menu
        # items to prevent GC removing it.
        self.menu_actions = []
        self.qaction.setMenu(self.menu)
        self.menu.aboutToShow.connect(self.about_to_show_menu)

        self.menus_lock = threading.RLock()

    def initialization_complete(self):
        # otherwise configured hot keys won't work until the menu's
        # been displayed once.
        self.rebuild_menus()

    def about_to_show_menu(self):
        self.rebuild_menus()

    def library_changed(self, db):
        # We need to reset our menus after switching libraries
        self.rebuild_menus()
        
    def rebuild_menus(self):
        with self.menus_lock:
            # Show the config dialog
            # The config dialog can also be shown from within
            # Preferences->Plugins, which is why the do_user_config
            # method is defined on the base plugin class
            do_user_config = self.interface_action_base_plugin.do_user_config
            self.menu.clear()
            self.actions_unique_map = {}
            self.menu_actions = []
            self.add_action = self.create_menu_item_ex(self.menu, '&Add New from URL(s)', image='plus.png',
                                                       unique_name='Add New FanFiction Book(s) from URL(s)',
                                                       shortcut_name='Add New FanFiction Book(s) from URL(s)',
                                                       triggered=self.add_dialog )

            self.update_action = self.create_menu_item_ex(self.menu, '&Update Existing FanFiction Book(s)', image='plusplus.png',
                                                          unique_name='Update Existing FanFiction Book(s)',
                                                          shortcut_name='Update Existing FanFiction Book(s)',
                                                          triggered=self.update_existing)

            if 'Reading List' in self.gui.iactions and (prefs['addtolists'] or prefs['addtoreadlists']) :
                self.menu.addSeparator()
                addmenutxt, rmmenutxt = None, None
                if prefs['addtolists'] and prefs['addtoreadlists'] :
                    addmenutxt = 'Add to "To Read" and "Send to Device" Lists'
                    if prefs['addtolistsonread']:
                        rmmenutxt = 'Remove from "To Read" and add to "Send to Device" Lists'
                    else:
                        rmmenutxt = 'Remove from "To Read" Lists'
                elif prefs['addtolists'] :
                    addmenutxt = 'Add Selected to "Send to Device" Lists'
                elif prefs['addtoreadlists']:
                    addmenutxt = 'Add to "To Read" Lists'
                    rmmenutxt = 'Remove from "To Read" Lists'

                if addmenutxt:
                    self.add_send_action = self.create_menu_item_ex(self.menu, addmenutxt, image='plusplus.png',
                                                                    unique_name=addmenutxt,
                                                                    shortcut_name=addmenutxt,
                                                                    triggered=partial(self.update_lists,add=True))

                if rmmenutxt:
                    self.add_remove_action = self.create_menu_item_ex(self.menu, rmmenutxt, image='minusminus.png',
                                                                      unique_name=rmmenutxt,
                                                                      shortcut_name=rmmenutxt,
                                                                      triggered=partial(self.update_lists,add=False))
                
                # try:
                #     self.add_send_action.setEnabled( len(self.gui.library_view.get_selected_ids()) > 0 )
                # except:
                #     pass
                # try:
                #     self.add_remove_action.setEnabled( len(self.gui.library_view.get_selected_ids()) > 0 )
                # except:
                #     pass

            self.menu.addSeparator()
            self.get_list_action = self.create_menu_item_ex(self.menu, 'Get URLs from Selected Books', image='bookmarks.png',
                                                            unique_name='Get URLs from Selected Books',
                                                            shortcut_name='Get URLs from Selected Books',
                                                            triggered=self.get_list_urls)

            self.get_list_url_action = self.create_menu_item_ex(self.menu, 'Get Story URLs from Web Page', image='view.png',
                                                                unique_name='Get Story URLs from Web Page',
                                                                shortcut_name='Get Story URLs from Web Page',
                                                                triggered=self.get_urls_from_page)

            self.menu.addSeparator()
            self.config_action = create_menu_action_unique(self, self.menu, '&Configure Plugin', shortcut=False,
                                                           image= 'config.png',
                                                           unique_name='Configure FanFictionDownLoader',
                                                           shortcut_name='Configure FanFictionDownLoader',
                                                           triggered=partial(do_user_config,parent=self.gui))
            
            self.about_action = create_menu_action_unique(self, self.menu, '&About Plugin', shortcut=False,
                                                          image= 'images/icon.png',
                                                          unique_name='About FanFictionDownLoader',
                                                          shortcut_name='About FanFictionDownLoader',
                                                          triggered=self.about)
            
            # Before we finalize, make sure we delete any actions for menus that are no longer displayed
            for menu_id, unique_name in self.old_actions_unique_map.iteritems():
                if menu_id not in self.actions_unique_map:
                    self.gui.keyboard.unregister_shortcut(unique_name)
            self.old_actions_unique_map = self.actions_unique_map
            self.gui.keyboard.finalize()            

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
        AboutDialog(self.gui,self.qaction.icon(),self.version + text).exec_()

    def create_menu_item_ex(self, parent_menu, menu_text, image=None, tooltip=None,
                           shortcut=None, triggered=None, is_checked=None, shortcut_name=None,
                           unique_name=None):
        ac = create_menu_action_unique(self, parent_menu, menu_text, image, tooltip,
                                       shortcut, triggered, is_checked, shortcut_name, unique_name)
        self.actions_unique_map[ac.calibre_shortcut_unique_name] = ac.calibre_shortcut_unique_name
        self.menu_actions.append(ac)
        return ac

    def plugin_button(self):
        if len(self.gui.library_view.get_selected_ids()) > 0 and prefs['updatedefault']:
            self.update_existing()
        else:
            self.add_dialog()

    def update_lists(self,add=True):
        if len(self.gui.library_view.get_selected_ids()) > 0 and \
                (prefs['addtolists'] or prefs['addtoreadlists']) :
            self._update_reading_lists(self.gui.library_view.get_selected_ids(),add)

    def get_urls_from_page(self):
        d = CollectURLDialog(self.gui,"Get Story URLs from Web Page")
        d.exec_()
        if not d.status:
            return
        print("URL:%s"%d.url.text())

        url_list = get_urls_from_page("%s"%d.url.text())

        if url_list:
            d = ViewLog(_("List of URLs"),"\n".join(url_list),parent=self.gui)
            d.setWindowIcon(get_icon('bookmarks.png'))
            d.exec_()
        else:
            info_dialog(self.gui, _('List of URLs'),
                        _('No Valid URLs found on given page.'),
                        show=True,
                        show_copy_button=False)
        
            
    def get_list_urls(self):
        if len(self.gui.library_view.get_selected_ids()) > 0:
            book_list = map( partial(self._convert_id_to_book, good=False), self.gui.library_view.get_selected_ids() )

            LoopProgressDialog(self.gui,
                               book_list,
                               partial(self._get_story_url_for_list, db=self.gui.current_db),
                               self._finish_get_list_urls,
                               init_label="Collecting URLs for stories...",
                               win_title="Get URLs for stories",
                               status_prefix="URL retrieved")
            
    def _get_story_url_for_list(self,book,db=None):
        book['url'] = self._get_story_url(db,book['calibre_id'])
        if book['url'] == None:
            book['good']=False
        else:
            book['good']=True
            
    def _finish_get_list_urls(self, book_list):
        url_list = [ x['url'] for x in book_list if x['good'] ]
        if url_list:
            d = ViewLog(_("List of URLs"),"\n".join(url_list),parent=self.gui)
            d.setWindowIcon(get_icon('bookmarks.png'))
            d.exec_()
        else:
            info_dialog(self.gui, _('List of URLs'),
                        _('No URLs found in selected books.'),
                        show=True,
                        show_copy_button=False)
                
    def add_dialog(self):

        #print("add_dialog()")

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

        options = d.get_ffdl_options()
        options['version'] = self.version
        print(self.version)
        
        self.start_downloads( options, add_books )
        
    def update_existing(self):
        if len(self.gui.library_view.get_selected_ids()) == 0:
            return
        #print("update_existing()")
        
        db = self.gui.current_db
        book_list = map( partial(self._convert_id_to_book, good=False), self.gui.library_view.get_selected_ids() )
        #book_ids = self.gui.library_view.get_selected_ids()

        LoopProgressDialog(self.gui,
                           book_list,
                           partial(self._populate_book_from_calibre_id, db=self.gui.current_db),
                           self._update_existing_2,
                           init_label="Collecting stories for update...",
                           win_title="Get stories for updates",
                           status_prefix="URL retrieved")            
        
        #books = self._convert_calibre_ids_to_books(db, book_ids)
        #print("update books:%s"%books)

    def _update_existing_2(self,book_list):
        
        d = UpdateExistingDialog(self.gui,
                                 'Update Existing List',
                                 prefs,
                                 self.qaction.icon(),
                                 book_list,
                                 )
        d.exec_()
        if d.result() != d.Accepted:
            return

        update_books = d.get_books()

        #print("update_books:%s"%update_books)
        #print("options:%s"%d.get_ffdl_options())
        # only if there's some good ones.
        if 0 < len(filter(lambda x : x['good'], update_books)):
            options = d.get_ffdl_options()
            options['version'] = self.version
            print(self.version)
            self.start_downloads( options, update_books )
        
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
        
        if 0 < len(filter(lambda x : x['good'], books)):
            LoopProgressDialog(self.gui,
                               books,
                               partial(self.get_metadata_for_book, options = options),
                               partial(self.start_download_list, options = options))
        # LoopProgressDialog calls get_metadata_for_book for each 'good' story,
        # get_metadata_for_book updates book for each,
        # LoopProgressDialog calls start_download_list at the end which goes
        # into the BG, or shows list if no 'good' books.

    def get_metadata_for_book(self,book,
                              options={'fileform':'epub',
                                       'collision':ADDNEW,
                                       'updatemeta':True,
                                       'updateepubcover':True}):
        '''
        Update passed in book dict with metadata from website and
        necessary data.  To be called from LoopProgressDialog
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
        updateepubcover= options['updateepubcover']

        if not book['good']:
            # book has already been flagged bad for whatever reason.
            return
        
        url = book['url']
        print("url:%s"%url)
        skip_date_update = False
        
        ## was self.ffdlconfig, but we need to be able to change it
        ## when doing epub update.
        ffdlconfig = SafeConfigParser()
        ffdlconfig.readfp(StringIO(get_resources("plugin-defaults.ini")))
        ffdlconfig.readfp(StringIO(prefs['personal.ini']))
        adapter = adapters.getAdapter(ffdlconfig,url,fileform)

        options['personal.ini'] = prefs['personal.ini']
        if prefs['includeimages']:
            # this is a cheat to make it easier for users.
            options['personal.ini'] = '''[epub]
include_images:true
keep_summary_html:true
make_firstimage_cover:true
''' + options['personal.ini']

        ## three tries, that's enough if both user/pass & is_adult needed,
        ## or a couple tries of one or the other
        for x in range(0,2):
            try:
                adapter.getStoryMetadataOnly()
            except exceptions.FailedToLogin, f:
                print("Login Failed, Need Username/Password.")
                userpass = UserPassDialog(self.gui,url,f)
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

        book['all_metadata'] = story.getAllMetadata(removeallentities=True)
        book['title'] = story.getMetadata("title", removeallentities=True)
        book['author_sort'] = book['author'] = story.getList("author", removeallentities=True)
        book['publisher'] = story.getMetadata("site")
        book['tags'] = writer.getTags() # getTags could be moved up into adapter now.  Adapter didn't used to know the fileform
        book['comments'] = stripHTML(story.getMetadata("description")) #, removeallentities=True) comments handles entities better.
        book['series'] = story.getMetadata("series")
        
        # adapter.opener is the element with a threadlock.  But del
        # adapter.opener doesn't work--subproc fails when it tries
        # to pull in the adapter object that hasn't been imported yet.
        # book['adapter'] = adapter
        
        book['is_adult'] = adapter.is_adult
        book['username'] = adapter.username
        book['password'] = adapter.password

        book['icon'] = 'plus.png'
        if story.getMetadataRaw('datePublished'):
            # should only happen when an adapter is broken, but better to
            # fail gracefully.
            book['pubdate'] = story.getMetadataRaw('datePublished').replace(tzinfo=local_tz)
        book['timestamp'] = None # filled below if not skipped.
        
        if collision in (CALIBREONLY):
            book['icon'] = 'metadata.png'
        
        # Dialogs should prevent this case now.
        if collision in (UPDATE,UPDATEALWAYS) and fileform != 'epub':
            raise NotGoingToDownload("Cannot update non-epub format.")
        
        book_id = None
        
        if book['calibre_id'] != None:
            # updating an existing book.  Update mode applies.
            print("update existing id:%s"%book['calibre_id'])
            book_id = book['calibre_id']
            # No handling needed: OVERWRITEALWAYS,CALIBREONLY
            
        # only care about collisions when not ADDNEW
        elif collision != ADDNEW:
            # 'new' book from URL.  collision handling applies.
            print("from URL(%s)"%url)

            # try to find by identifier url first.
            searchstr = 'identifiers:"=url:%s"'%url.replace(":","|")
            identicalbooks = db.search_getting_ids(searchstr, None)
            if len(identicalbooks) < 1:
                # find dups
                authlist = story.getList("author", removeallentities=True)
                if len(authlist) > 100 and calibre_version < (0, 8, 61):
                    ## should be fixed from 0.8.61 on.  In the
                    ## meantime, if it matches the title *and* first
                    ## 100 authors, I'm prepared to assume it's a
                    ## match.
                    print("reduce author list to 100 only when calibre < 0.8.61")
                    authlist = authlist[:100]
                mi = MetaInformation(story.getMetadata("title", removeallentities=True),
                                     authlist)
                identicalbooks = db.find_identical_books(mi)
                if len(identicalbooks) > 0:
                    print("existing found by title/author(s)")

            else:
                print("existing found by identifier URL")
                
            if collision == SKIP and identicalbooks:
                raise NotGoingToDownload("Skipping duplicate story.","list_remove.png")

            if len(identicalbooks) > 1:
                raise NotGoingToDownload("More than one identical book--can't tell which to update/overwrite.","minusminus.png")

            ## changed: add new book when CALIBREONLY if none found.
            if collision == CALIBREONLY and not identicalbooks:
                collision = ADDNEW
                options['collision'] = ADDNEW

            if len(identicalbooks)>0:
                book_id = identicalbooks.pop()
                book['calibre_id'] = book_id
                book['icon'] = 'edit-redo.png'

        if book_id != None and collision != ADDNEW:
            if collision in (CALIBREONLY):
                book['comment'] = 'Metadata collected.'
                # don't need temp file created below.
                return
            
            ## newer/chaptercount checks are the same for both:
            # Update epub, but only if more chapters.
            if collision in (UPDATE,UPDATEALWAYS): # collision == UPDATE
                # 'book' can exist without epub.  If there's no existing epub,
                # let it go and it will download it.
                if db.has_format(book_id,fileform,index_is_id=True):
                    (epuburl,chaptercount) = \
                        get_dcsource_chaptercount(StringIO(db.format(book_id,'EPUB',
                                                                     index_is_id=True)))
                    urlchaptercount = int(story.getMetadata('numChapters'))
                    if chaptercount == urlchaptercount:
                        if collision == UPDATE:
                            raise NotGoingToDownload("Already contains %d chapters."%chaptercount,'edit-undo.png')
                        else:
                            # UPDATEALWAYS
                            skip_date_update = True
                    elif chaptercount > urlchaptercount:
                        raise NotGoingToDownload("Existing epub contains %d chapters, web site only has %d. Use Overwrite to force update." % (chaptercount,urlchaptercount),'dialog_error.png')
    
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

        if collision != CALIBREONLY and not skip_date_update:
            # I'm half convinced this should be dateUpdated instead, but
            # this behavior matches how epubs come out when imported
            # dateCreated == packaged--epub/etc created.
            book['timestamp'] = story.getMetadataRaw('dateCreated').replace(tzinfo=local_tz)

        if book_id != None and prefs['injectseries']:
            mi = db.get_metadata(book_id,index_is_id=True)
            if not book['series'] and mi.series != None:
                book['calibre_series'] = (mi.series,mi.series_index)
                print("calibre_series:%s [%s]"%book['calibre_series'])
            
        if book['good']: # there shouldn't be any !'good' books at this point.
            # if still 'good', make a temp file to write the output to.
            tmp = PersistentTemporaryFile(prefix='new-%s-'%book['calibre_id'],
                                               suffix='.'+options['fileform'],
                                               dir=options['tdir'])
            print("title:"+book['title'])
            print("outfile:"+tmp.name)
            book['outfile'] = tmp.name            
                
        return
        
    def start_download_list(self,book_list,
                            options={'fileform':'epub',
                                     'collision':ADDNEW,
                                     'updatemeta':True,
                                     'updateepubcover':True}):
        '''
        Called by LoopProgressDialog to start story downloads BG processing.
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

            
            custom_columns = self.gui.library_view.model().custom_columns
            if prefs['errorcol'] != '' and prefs['errorcol'] in custom_columns:
                label = custom_columns[prefs['errorcol']]['label']
                ## if error column and all bad.
                self.previous = self.gui.library_view.currentIndex()
                LoopProgressDialog(self.gui,
                                   book_list,
                                   partial(self._update_bad_book, label=label, options=options, db=self.gui.current_db),
                                   partial(self._update_books_completed, options=options, showlist=False),
                                   init_label="Updating calibre for BAD FanFiction stories...",
                                   win_title="Update calibre for BAD FanFiction stories",
                                   status_prefix="Updated")
            
            
            return
            
        func = 'arbitrary_n'
        cpus = self.gui.job_manager.server.pool_size
        args = ['calibre_plugins.fanfictiondownloader_plugin.jobs', 'do_download_worker',
                (book_list, options, cpus)]
        desc = 'Download FanFiction Book'
        job = self.gui.job_manager.run_job(
                self.Dispatcher(partial(self.download_list_completed,options=options)),
                func, args=args,
                description=desc)
        
        self.gui.status_bar.show_message('Starting %d FanFictionDownLoads'%len(book_list),3000)

    def _update_book(self,book,db=None,
                     options={'fileform':'epub',
                              'collision':ADDNEW,
                              'updatemeta':True,
                              'updateepubcover':True}):
        print("add/update %s %s"%(book['title'],book['url']))
        mi = self._make_mi_from_book(book)
                
        if options['collision'] != CALIBREONLY:
            self._add_or_update_book(book,options,prefs,mi)

        if options['collision'] == CALIBREONLY or \
                (options['updatemeta'] and book['good']):
            self._update_metadata(db, book['calibre_id'], book, mi, options)

    def _update_bad_book(self,book,db=None,label='errorcol',
                         options={'fileform':'epub',
                                  'collision':ADDNEW,
                                  'updatemeta':True,
                                  'updateepubcover':True},):
        if book['calibre_id']:
            print("add/update bad %s %s %s"%(book['title'],book['url'],book['comment']))
            db.set_custom(book['calibre_id'], book['comment'], label=label, commit=True)

    def _update_books_completed(self, book_list, options={}, showlist=True):
        
        add_list = filter(lambda x : x['good'] and x['added'], book_list)
        add_ids = [ x['calibre_id'] for x in add_list ]
        update_list = filter(lambda x : x['good'] and not x['added'], book_list)
        update_ids = [ x['calibre_id'] for x in update_list ]
        
        if len(add_list):
            ## even shows up added to searchs.  Nice.
            self.gui.library_view.model().books_added(len(add_list))
            self.gui.library_view.model().refresh_ids(add_ids)

        if len(update_list):
            self.gui.library_view.model().refresh_ids(update_ids)

        current = self.gui.library_view.currentIndex()
        self.gui.library_view.model().current_changed(current, self.previous)
        self.gui.tags_view.recount()
        
        if self.gui.cover_flow:
            self.gui.cover_flow.dataChanged()
        
        self.gui.status_bar.show_message(_('Finished Adding/Updating %d books.'%(len(update_list) + len(add_list))), 3000)
            
        if showlist and (len(update_list) + len(add_list) != len(book_list)):
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

        all_ids = add_ids
        all_ids.extend(update_ids)
        if 'Count Pages' in self.gui.iactions and len(prefs['countpagesstats']) and len(all_ids):
            cp_plugin = self.gui.iactions['Count Pages']
            cp_plugin.count_statistics(all_ids,prefs['countpagesstats'])

    def download_list_completed(self, job, options={}):
        if job.failed:
            self.gui.job_exception(job, dialog_title='Failed to Download Stories')
            return

        self.previous = self.gui.library_view.currentIndex()
        db = self.gui.current_db

        if display_story_list(self.gui,
                              'Downloads finished, confirm to update Calibre',
                              prefs,
                              self.qaction.icon(),
                              job.result,
                              label_text='Stories will not be added or updated in Calibre without confirmation.',
                              offer_skip=True):
            
            book_list = job.result
            good_list = filter(lambda x : x['good'], book_list)
            total_good = len(good_list)

            self.gui.status_bar.show_message(_('Adding/Updating %s books.'%total_good))

            if total_good > 0:
                LoopProgressDialog(self.gui,
                                   good_list,
                                   partial(self._update_book, options=options, db=self.gui.current_db),
                                   partial(self._update_books_completed, options=options),
                                   init_label="Updating calibre for FanFiction stories...",
                                   win_title="Update calibre for FanFiction stories",
                                   status_prefix="Updated")

            bad_list = filter(lambda x : x['calibre_id'] and not x['good'], book_list)
            total_bad = len(bad_list)

            if total_bad > 0:
                custom_columns = self.gui.library_view.model().custom_columns
                if prefs['errorcol'] != '' and prefs['errorcol'] in custom_columns:
                    self.gui.status_bar.show_message(_('Adding/Updating %s BAD books.'%total_bad))
                    label = custom_columns[prefs['errorcol']]['label']
                    ## if error column and all bad.
                    LoopProgressDialog(self.gui,
                                       bad_list,
                                       partial(self._update_bad_book, label=label, options=options, db=self.gui.current_db),
                                       partial(self._update_books_completed, options=options, showlist=False),
                                       init_label="Updating calibre for BAD FanFiction stories...",
                                       win_title="Update calibre for BAD FanFiction stories",
                                       status_prefix="Updated")

                
    def _add_or_update_book(self,book,options,prefs,mi=None):
        db = self.gui.current_db
        
        if mi == None:
            mi = self._make_mi_from_book(book)

        book_id = book['calibre_id']
        if book_id == None:
            book_id = db.create_book_entry(mi,
                                           add_duplicates=True)
            book['calibre_id'] = book_id
            book['added'] = True
        else:
            book['added'] = False

        if not db.add_format_with_hooks(book_id,
                                        options['fileform'],
                                        book['outfile'], index_is_id=True):
            book['comment'] = "Adding format to book failed for some reason..."
            book['good']=False
            book['icon']='dialog_error.png'

        if prefs['deleteotherforms']:
            fmts = db.formats(book['calibre_id'], index_is_id=True).split(',')
            for fmt in fmts:
                if fmt != formmapping[options['fileform']]:
                    print("remove f:"+fmt)
                    db.remove_format(book['calibre_id'], fmt, index_is_id=True)#, notify=False

        if prefs['addtolists'] or prefs['addtoreadlists']:
            self._update_reading_lists([book_id],add=True)
                
        return book_id

    def _update_metadata(self, db, book_id, book, mi, options):
        if prefs['keeptags']:
            old_tags = db.get_tags(book_id)
            # remove old Completed/In-Progress only if there's a new one.
            if 'Completed' in mi.tags or 'In-Progress' in mi.tags:
                old_tags = filter( lambda x : x not in ('Completed', 'In-Progress'), old_tags)
                # remove old Last Update tags if there are new ones.
            if len(filter( lambda x : not x.startswith("Last Update"), mi.tags)) > 0:
                old_tags = filter( lambda x : not x.startswith("Last Update"), old_tags)
            # mi.tags needs to be list, but set kills dups.
            mi.tags = list(set(list(old_tags)+mi.tags))

        if 'langcode' in book['all_metadata']:
            mi.languages=[book['all_metadata']['langcode']]
        else:
            # Set language english, but only if not already set.
            oldmi = db.get_metadata(book_id,index_is_id=True)
            if not oldmi.languages:
                mi.languages=['eng']

        if options['fileform'] == 'epub' and prefs['updatecover']:
            existingepub = db.format(book_id,'EPUB',index_is_id=True, as_file=True)
            epubmi = get_metadata(existingepub,'EPUB')
            if epubmi.cover_data[1] is not None:
                db.set_cover(book_id, epubmi.cover_data[1])

        # set author link if found.  All current adapters have authorUrl, except anonymous on AO3.
        if 'authorUrl' in book['all_metadata']:
            authurls = book['all_metadata']['authorUrl'].split(", ")
            for i, auth in enumerate(book['author']):
                autid=db.get_author_id(auth)
                db.set_link_field_for_author(autid, unicode(authurls[i]),
                                             commit=False, notify=False)
            
        db.set_metadata(book_id,mi)

        # do configured column updates here.
        #print("all_metadata: %s"%book['all_metadata'])
        custom_columns = self.gui.library_view.model().custom_columns

        #print("prefs['custom_cols'] %s"%prefs['custom_cols'])
        for col, meta in prefs['custom_cols'].iteritems():
            #print("setting %s to %s"%(col,meta))
            if col not in custom_columns:
                print("%s not an existing column, skipping."%col)
                continue
            coldef = custom_columns[col]
            if not meta.startswith('status-') and meta not in book['all_metadata'] or \
                    meta.startswith('status-') and 'status' not in book['all_metadata']:
                print("No value for %s, skipping custom column(%s) update."%(meta,coldef['name']))
                continue
            if meta not in permitted_values[coldef['datatype']]:
                print("%s not a valid column type for %s, skipping."%(col,meta))
                continue
            label = coldef['label']
            if coldef['datatype'] in ('enumeration','text','comments','datetime','series'):
                db.set_custom(book_id, book['all_metadata'][meta], label=label, commit=False)
            elif coldef['datatype'] in ('int','float'):
                num = unicode(book['all_metadata'][meta]).replace(",","")
                db.set_custom(book_id, num, label=label, commit=False)
            elif coldef['datatype'] == 'bool' and meta.startswith('status-'):
                if meta == 'status-C':
                    val = book['all_metadata']['status'] == 'Completed'
                if meta == 'status-I':
                    val = book['all_metadata']['status'] == 'In-Progress'
                db.set_custom(book_id, val, label=label, commit=False)

        db.commit()

        if 'Generate Cover' in self.gui.iactions and (book['added'] or not prefs['gcnewonly']):
            
            # force a refresh if generating cover so complex composite
            # custom columns are current and correct
            db.refresh_ids([book_id])
                
            gc_plugin = self.gui.iactions['Generate Cover']
            setting_name = None
            if prefs['allow_gc_from_ini']:
                ffdlconfig = SafeConfigParser()
                ffdlconfig.readfp(StringIO(get_resources("plugin-defaults.ini")))
                ffdlconfig.readfp(StringIO(prefs['personal.ini']))
                adapter = adapters.getAdapter(ffdlconfig,book['url'],options['fileform'])

                # template => regexp to match => GC Setting to use.
                # generate_cover_settings:
                # ${category} => Buffy:? the Vampire Slayer => Buffy
                for line in adapter.getConfig('generate_cover_settings').splitlines():
                    if "=>" in line:
                        (template,regexp,setting) = map( lambda x: x.strip(), line.split("=>") )
                        value = Template(template).safe_substitute(book['all_metadata']).encode('utf8')
                        print("%s(%s) => %s => %s"%(template,value,regexp,setting))
                        if re.search(regexp,value):
                            setting_name = setting
                            break

                if setting_name:
                    print("Generate Cover Setting from generate_cover_settings(%s)"%line)
                    if setting_name not in gc_plugin.get_saved_setting_names():
                        print("GC Name %s not found, discarding! (check personal.ini for typos)"%setting_name)
                        setting_name = None
                
            if not setting_name and book['all_metadata']['site'] in prefs['gc_site_settings']:
                setting_name =  prefs['gc_site_settings'][book['all_metadata']['site']]

            if not setting_name and 'Default' in prefs['gc_site_settings']:
                setting_name =  prefs['gc_site_settings']['Default']
                
            if setting_name:
                print("Running Generate Cover with settings %s."%setting_name)
                realmi = db.get_metadata(book_id, index_is_id=True)
                gc_plugin.generate_cover_for_book(realmi,saved_setting_name=setting_name)

        ## if error column set.
        if prefs['errorcol'] != '' and prefs['errorcol'] in custom_columns:
            label = custom_columns[prefs['errorcol']]['label']
            db.set_custom(book['calibre_id'], '', label=label, commit=True) # book['comment']

    def _get_clean_reading_lists(self,lists):
        if lists == None or lists.strip() == "" :
            return []
        else:
            return filter( lambda x : x, map( lambda x : x.strip(), lists.split(',') ) )
        
    def _update_reading_lists(self,book_ids,add=True):
        try:
            rl_plugin = self.gui.iactions['Reading List']
        except:
            if prefs['addtolists'] or prefs['addtoreadlists']:
                message="<p>You configured FanFictionDownLoader to automatically update Reading Lists, but you don't have the Reading List plugin installed anymore?</p>"
                confirm(message,'fanfictiondownloader_no_reading_list_plugin', self.gui)
            return
        
        # XXX check for existence of lists, warning if not.
        if prefs['addtoreadlists']:
            if add:
                addremovefunc = rl_plugin.add_books_to_list
            else:
                addremovefunc = rl_plugin.remove_books_from_list
                
            lists = self._get_clean_reading_lists(prefs['read_lists'])
            if len(lists) < 1 :
                message="<p>You configured FanFictionDownLoader to automatically update \"To Read\" Reading Lists, but you don't have any lists set?</p>"
                confirm(message,'fanfictiondownloader_no_read_lists', self.gui)
            for l in lists:
                if l in rl_plugin.get_list_names():
                    #print("add good read l:(%s)"%l)
                    addremovefunc(l,
                                  book_ids,
                                  display_warnings=False)
                else:
                    if l != '':
                        message="<p>You configured FanFictionDownLoader to automatically update Reading List '%s', but you don't have a list of that name?</p>"%l
                        confirm(message,'fanfictiondownloader_no_reading_list_%s'%l, self.gui)
                        
        if prefs['addtolists'] and (add or (prefs['addtolistsonread'] and prefs['addtoreadlists']) ):
            lists = self._get_clean_reading_lists(prefs['send_lists'])
            if len(lists) < 1 :
                message="<p>You configured FanFictionDownLoader to automatically update \"Send to Device\" Reading Lists, but you don't have any lists set?</p>"
                confirm(message,'fanfictiondownloader_no_send_lists', self.gui)

            # Quick demo of how an 'allow send' list might work.
            # Issues: allow list per send list?  Naming convention?  "send(allow)"
            # allow_list = rl_plugin.get_book_list("Allow Send to Device")
            # # intersection of book_ids & allow_list
            # add_book_ids = list(set(book_ids) & set(allow_list))

            for l in lists:
                if l in rl_plugin.get_list_names():
                    #print("good send l:(%s)"%l)
                    rl_plugin.add_books_to_list(l,
                                                #add_book_ids,
                                                book_ids,
                                                display_warnings=False)
                else:
                    if l != '':
                        message="<p>You configured FanFictionDownLoader to automatically update Reading List '%s', but you don't have a list of that name?</p>"%l
                        confirm(message,'fanfictiondownloader_no_reading_list_%s'%l, self.gui)

    # def _find_existing_book_id(self,db,book,matchurl=True):
    #     mi = MetaInformation(book["title"],book["author"]) # author is a list.
    #     identicalbooks = db.find_identical_books(mi)
    #     if matchurl: # only *really* identical if URL matches, too.
    #         for ib in identicalbooks:
    #             if self._get_story_url(db,ib) == book['url']:
    #                 return ib
    #     if identicalbooks:
    #         return identicalbooks.pop()
    #     return None
    
    def _make_mi_from_book(self,book):
        mi = MetaInformation(book['title'],book['author']) # author is a list.
        mi.set_identifiers({'url':book['url']})
        mi.publisher = book['publisher']
        mi.tags = book['tags']
        #mi.languages = ['en'] # handled in _update_metadata so it can check for existing lang.
        mi.pubdate = book['pubdate']
        mi.timestamp = book['timestamp']
        mi.comments = book['comments']
        mi.series = book['series']
        return mi


    def _convert_urls_to_books(self, urls):
        books = []
        uniqueurls = set()
        for url in urls:
            # look here for [\d,\d] at end of url, and remove?
            mc = re.match(r"^(?P<url>.*?)(?:\[(?P<begin>\d+)?(?P<comma>,)?(?P<end>\d+)?\])?$",url)
            print("url:(%s) begin:(%s) end:(%s)"%(mc.group('url'),mc.group('begin'),mc.group('end')))
            url = mc.group('url')
            book = self._convert_url_to_book(url)
            book['begin'] = mc.group('begin')
            book['end'] = mc.group('end')
            if book['begin'] and not mc.group('comma'):
                book['end'] = book['begin']
            if book['url'] in uniqueurls:
                book['good'] = False
                book['comment'] = "Same story already included."
            uniqueurls.add(book['url'])
            books.append(book)
        return books

    def _convert_url_to_book(self, url):
        book = {}
        book['good'] = True
        book['calibre_id'] = None
        book['title'] = 'Unknown'
        book['author_sort'] = book['author'] = ['Unknown'] # list
        book['begin'] = None
        book['end'] = None
            
        book['comment'] = ''
        book['url'] = ''
        book['added'] = False
        
        self._set_book_url_and_comment(book,url)
        return book
        
    def _convert_id_to_book(self, idval, good=True):
        book = {}
        book['good'] = good
        book['calibre_id'] = idval
        book['title'] = 'Unknown'
        book['author_sort'] = book['author'] = ['Unknown'] # list
        book['begin'] = None
        book['end'] = None
            
        book['comment'] = ''
        book['url'] = ''
        book['added'] = False
        
        return book
            
    def _populate_book_from_calibre_id(self, book, db=None):
        mi = db.get_metadata(book['calibre_id'], index_is_id=True)
        #book = {}
        book['good'] = True
        book['calibre_id'] = mi.id
        book['title'] = mi.title
        book['author'] = mi.authors
        book['author_sort'] = mi.author_sort
        book['comment'] = ''
        book['url'] = ""
        book['added'] = False
        
        url = self._get_story_url(db,book['calibre_id'])
        self._set_book_url_and_comment(book,url)
        #return book

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
            ## only epub has URL in it--at least where I can easily find it.
            if db.has_format(book_id,'EPUB',index_is_id=True):
                existingepub = db.format(book_id,'EPUB',index_is_id=True, as_file=True)
                mi = get_metadata(existingepub,'EPUB')
                identifiers = mi.get_identifiers()
                if 'url' in identifiers:
                    #print("url from epub:"+identifiers['url'].replace('|',':'))
                    return identifiers['url'].replace('|',':')
                # look for dc:source first, then scan HTML if 
                link = get_dcsource(existingepub)
                if link:
                    return link
                elif prefs['lookforurlinhtml']:
                    return get_story_url_from_html(existingepub,self._is_good_downloader_url)
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

def get_url_list(urls):
    def f(x):
        if x.strip(): return True
        else: return False
    # set removes dups.
    return set(filter(f,urls.strip().splitlines()))

