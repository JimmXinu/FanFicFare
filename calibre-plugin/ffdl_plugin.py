#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2014, Jim Miller'
__docformat__ = 'restructuredtext en'

import logging
logger = logging.getLogger(__name__)

import time, os, copy, threading, re, platform, sys
from StringIO import StringIO
from functools import partial
from datetime import datetime, time
from string import Template
import urllib
import email
import traceback

try:
    from PyQt5.Qt import (QApplication, QMenu, QTimer)
    from PyQt5.QtCore import QBuffer
except ImportError as e:
    from PyQt4.Qt import (QApplication, QMenu, QTimer)
    from PyQt4.QtCore import QBuffer

from calibre.constants import numeric_version as calibre_version

from calibre.ptempfile import PersistentTemporaryFile, PersistentTemporaryDirectory, remove_dir
from calibre.ebooks.metadata import MetaInformation
from calibre.ebooks.metadata.meta import get_metadata
from calibre.gui2 import error_dialog, warning_dialog, question_dialog, info_dialog
from calibre.gui2.dialogs.message_box import ViewLog
from calibre.gui2.dialogs.confirm_delete import confirm
from calibre.utils.config import prefs as calibre_prefs
from calibre.utils.date import local_tz
from calibre.library.comments import sanitize_comments_html
from calibre.constants import config_dir as calibre_config_dir

# The class that all interface action plugins must inherit from
from calibre.gui2.actions import InterfaceAction

# pulls in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre_plugins.fanfictiondownloader_plugin.common_utils import (set_plugin_icon_resources, get_icon,
                                         create_menu_action_unique, get_library_uuid)

from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader import adapters, exceptions
from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader.epubutils import get_dcsource, get_dcsource_chaptercount, get_story_url_from_html
from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader.geturls import get_urls_from_page, get_urls_from_html, get_urls_from_text

from calibre_plugins.fanfictiondownloader_plugin.ffdl_util import (get_ffdl_adapter, get_ffdl_config, get_ffdl_personalini)
from calibre_plugins.fanfictiondownloader_plugin.config import (permitted_values, rejecturllist)
from calibre_plugins.fanfictiondownloader_plugin.prefs import prefs
from calibre_plugins.fanfictiondownloader_plugin.dialogs import (
    AddNewDialog, UpdateExistingDialog,
    LoopProgressDialog, UserPassDialog, AboutDialog, CollectURLDialog, RejectListDialog,
    OVERWRITE, OVERWRITEALWAYS, UPDATE, UPDATEALWAYS, ADDNEW, SKIP, CALIBREONLY,
    NotGoingToDownload, RejectUrlEntry )

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
    action_spec = (_('FanFictionDownLoader'), None,
                   _('Download FanFiction stories from various web sites'), ())
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

        self.qaction.setText(_('FanFictionDL'))
        
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
        self.menus_lock = threading.RLock()
        self.menu.aboutToShow.connect(self.about_to_show_menu)

    def initialization_complete(self):
        # otherwise configured hot keys won't work until the menu's
        # been displayed once.
        self.rebuild_menus()

        self.add_new_dialog = AddNewDialog(self.gui,
                                           prefs,
                                           self.qaction.icon())

    ## Kludgey, yes, but with the real configuration inside the
    ## library now, how else would a user be able to change this
    ## setting if it's crashing calibre?
    def check_macmenuhack(self):
        try:
            return self.macmenuhack
        except:
            file_path = os.path.join(calibre_config_dir,
                                     *("plugins/fanfictiondownloader_macmenuhack.txt".split('/')))
            file_path = os.path.abspath(file_path)
            logger.debug("Plugin %s macmenuhack file_path:%s"%(self.name,file_path))
            self.macmenuhack = os.access(file_path, os.F_OK)
            return self.macmenuhack

    accepts_drops = True

    def accept_enter_event(self, event, mime_data):
        if mime_data.hasFormat("application/calibre+from_library") or \
                mime_data.hasFormat("text/plain") or \
                mime_data.hasFormat("text/uri-list"):
            return True
                
        return False

    def accept_drag_move_event(self, event, mime_data):
        return self.accept_enter_event(event, mime_data)

    def drop_event(self, event, mime_data):

        dropped_ids=None
        urllist=[]
        
        mime = 'application/calibre+from_library'
        if mime_data.hasFormat(mime):
            dropped_ids = tuple(map(int, str(mime_data.data(mime)).split()))
        
        mimetype='text/uri-list'
        filelist="%s"%event.mimeData().data(mimetype)
        if filelist:
            for f in filelist.splitlines():
                #print("filename:%s"%f)
                if f.endswith(".eml"):
                    fhandle = urllib.urlopen(f)
                    msg = email.message_from_file(fhandle)
                    if msg.is_multipart():
                        for part in msg.walk():
                            #print("part type:%s"%part.get_content_type())
                            if part.get_content_type() == "text/html":
                                #print("URL list:%s"%get_urls_from_data(part.get_payload(decode=True)))
                                urllist.extend(get_urls_from_html(part.get_payload(decode=True)))
                            if part.get_content_type() == "text/plain":
                                #print("part content:text/plain")
                                #print("part content:%s"%part.get_payload(decode=True))
                                urllist.extend(get_urls_from_text(part.get_payload(decode=True)))
                    else:
                        urllist.extend(get_urls_from_text("%s"%msg))
                else:
                    urllist.extend(get_urls_from_text(f))
        else:
            mimetype='text/plain'
            if mime_data.hasFormat(mimetype):
                #print("text/plain:%s"%event.mimeData().data(mimetype))
                urllist.extend(get_urls_from_text(event.mimeData().data(mimetype)))

        # print("urllist:%s\ndropped_ids:%s"%(urllist,dropped_ids))
        if urllist or dropped_ids:
            QTimer.singleShot(1, partial(self.do_drop,
                                         dropped_ids=dropped_ids,
                                         urllist=urllist))
            return True
        
        return False

    def do_drop(self,dropped_ids=None,urllist=None):
        # shouldn't ever be both.
        if dropped_ids:
            self.update_dialog(dropped_ids)
        elif urllist:
            self.add_dialog("\n".join(urllist))
    
    def about_to_show_menu(self):
        self.rebuild_menus()

    def library_changed(self, db):
        # We need to reset our menus after switching libraries
        self.rebuild_menus()
        rejecturllist.clear_cache()
        
    def rebuild_menus(self):
        with self.menus_lock:
            #self.qaction.setText("FFDL")
            do_user_config = self.interface_action_base_plugin.do_user_config
            self.menu.clear()
            self.actions_unique_map = {}
            self.menu_actions = []
            self.add_action = self.create_menu_item_ex(self.menu, _('&Add New from URL(s)'), image='plus.png',
                                                       unique_name='Add New FanFiction Book(s) from URL(s)',
                                                       shortcut_name=_('Add New FanFiction Book(s) from URL(s)'),
                                                       triggered=self.add_dialog )

            self.update_action = self.create_menu_item_ex(self.menu, _('&Update Existing FanFiction Book(s)'), image='plusplus.png',
                                                          unique_name='&Update Existing FanFiction Book(s)',
                                                          triggered=self.update_dialog)

            if self.get_epubmerge_plugin():
                self.menu.addSeparator()
                self.get_list_url_action = self.create_menu_item_ex(self.menu, _('Get Story URLs to Download from Web Page'), image='view.png',
                                                                    unique_name='Get Story URLs from Web Page',
                                                                    triggered=self.get_urls_from_page_menu)
                
                self.makeanth_action = self.create_menu_item_ex(self.menu, _('&Make Anthology Epub Manually from URL(s)'), image='plusplus.png',
                                                                unique_name='Make FanFiction Anthology Epub Manually from URL(s)',
                                                                shortcut_name=_('Make FanFiction Anthology Epub Manually from URL(s)'),
                                                                triggered=partial(self.add_dialog,merge=True) )
                
                self.updateanth_action = self.create_menu_item_ex(self.menu, _('&Update Anthology Epub'), image='plusplus.png',
                                                                  unique_name='Update FanFiction Anthology Epub',
                                                                  shortcut_name=_('Update FanFiction Anthology Epub'),
                                                                  triggered=self.update_anthology)

            if 'Reading List' in self.gui.iactions and (prefs['addtolists'] or prefs['addtoreadlists']) :
                
                self.menu.addSeparator()
                addmenutxt, rmmenutxt = None, None
                if prefs['addtolists'] and prefs['addtoreadlists'] :
                    addmenutxt = _('Add to "To Read" and "Send to Device" Lists')
                    if prefs['addtolistsonread']:
                        rmmenutxt = _('Remove from "To Read" and add to "Send to Device" Lists')
                    else:
                        rmmenutxt = _('Remove from "To Read" Lists')
                elif prefs['addtolists'] :
                    addmenutxt = _('Add Selected to "Send to Device" Lists')
                elif prefs['addtoreadlists']:
                    addmenutxt = _('Add to "To Read" Lists')
                    rmmenutxt = _('Remove from "To Read" Lists')

                if addmenutxt:
                    self.add_send_action = self.create_menu_item_ex(self.menu, addmenutxt,
                                                                    unique_name='Add to "To Read" and "Send to Device" Lists',
                                                                    image='plusplus.png',
                                                                    triggered=partial(self.update_lists,add=True))

                if rmmenutxt:
                    self.add_remove_action = self.create_menu_item_ex(self.menu, rmmenutxt,
                                                                      unique_name='Remove from "To Read" and add to "Send to Device" Lists',
                                                                      image='minusminus.png',
                                                                      triggered=partial(self.update_lists,add=False))
                
            self.menu.addSeparator()
            self.get_list_action = self.create_menu_item_ex(self.menu, _('Get URLs from Selected Books'),
                                                            unique_name='Get URLs from Selected Books',
                                                            image='bookmarks.png',
                                                            triggered=self.list_story_urls)

            if not self.get_epubmerge_plugin():
                self.get_list_url_action = self.create_menu_item_ex(self.menu, _('Get Story URLs from Web Page'),
                                                                    unique_name='Get Story URLs from Web Page',
                                                                    image='view.png',
                                                                    triggered=self.get_urls_from_page_menu)

            self.reject_list_action = self.create_menu_item_ex(self.menu, _('Reject Selected Books'),
                                                               unique_name='Reject Selected Books', image='rotate-right.png',
                                                               triggered=self.reject_list_urls)

            # print("platform.system():%s"%platform.system())
            # print("platform.mac_ver()[0]:%s"%platform.mac_ver()[0])
            if not self.check_macmenuhack(): # not platform.mac_ver()[0]: # Some macs crash on these menu items for unknown reasons.
                self.menu.addSeparator()
                self.config_action = self.create_menu_item_ex(self.menu, _('&Configure Plugin'),
                                                              image= 'config.png',
                                                              unique_name='Configure FanFictionDownLoader',
                                                              shortcut_name=_('Configure FanFictionDownLoader'),
                                                              triggered=partial(do_user_config,parent=self.gui))
            
                self.about_action = self.create_menu_item_ex(self.menu, _('About Plugin'),
                                                             image= 'images/icon.png',
                                                             unique_name='About FanFictionDownLoader', 
                                                             shortcut_name=_('About FanFictionDownLoader'), 
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
        #print("create_menu_item_ex before %s"%menu_text)
        ac = create_menu_action_unique(self, parent_menu, menu_text, image, tooltip,
                                       shortcut, triggered, is_checked, shortcut_name, unique_name)
        self.actions_unique_map[ac.calibre_shortcut_unique_name] = ac.calibre_shortcut_unique_name
        self.menu_actions.append(ac)
        #print("create_menu_item_ex after %s"%menu_text)
        return ac

    def is_library_view(self):
        # 0 = library, 1 = main, 2 = card_a, 3 = card_b
        return self.gui.stack.currentIndex() == 0
    
    def plugin_button(self):
        if self.is_library_view() and \
                len(self.gui.library_view.get_selected_ids()) > 0 and \
                prefs['updatedefault']:
            self.update_dialog()
        else:
            self.add_dialog()

    def get_epubmerge_plugin(self):
        if 'EpubMerge' in self.gui.iactions and self.gui.iactions['EpubMerge'].interface_action_base_plugin.version >= (1,3,1):
            return self.gui.iactions['EpubMerge']
            
    def update_lists(self,add=True):
        if prefs['addtolists'] or prefs['addtoreadlists']:
            if not self.is_library_view():
                self.gui.status_bar.show_message(_('Cannot Update Reading Lists from Device View'), 3000)
                return
        
            if len(self.gui.library_view.get_selected_ids()) == 0:
                self.gui.status_bar.show_message(_('No Selected Books to Update Reading Lists'), 3000)
                return

            self.update_reading_lists(self.gui.library_view.get_selected_ids(),add)

    def get_urls_from_page_menu(self):

        urltxt = ""
        if prefs['urlsfromclip']:
            try:
                urltxt = self.get_urls_clip(storyurls=False)[0]
            except:
                urltxt = ""
        
        d = CollectURLDialog(self.gui,_("Get Story URLs from Web Page"),urltxt,self.get_epubmerge_plugin())
        d.exec_()
        if not d.status:
            return
        url = u"%s"%d.url.text()

        url_list = self.get_urls_from_page(url)

        if url_list:
            self.add_dialog("\n".join(url_list),merge=d.anthology,anthology_url=url)
        else:
            info_dialog(self.gui, _('List of Story URLs'),
                        _('No Valid Story URLs found on given page.'),
                        show=True,
                        show_copy_button=False)

    def get_urls_from_page(self,url):
        logger.debug("get_urls_from_page URL:%s"%url)
        if 'archiveofourown.org' in url:
            configuration = get_ffdl_config(url)
        else:
            configuration = None
        return get_urls_from_page(url,configuration)
        
    def list_story_urls(self):
        '''Get list of URLs from existing books.'''
        if self.gui.current_view().selectionModel().selectedRows() == 0 :
            self.gui.status_bar.show_message(_('No Selected Books to Get URLs From'),
                                             3000)
            return
            
        if self.is_library_view():
            book_list = map( partial(self.make_book_id_only),
                             self.gui.library_view.get_selected_ids() )

        else: # device view, get from epubs on device.
            view = self.gui.current_view()
            rows = view.selectionModel().selectedRows()
            # paths = view.model().paths(rows)
            book_list = map( partial(self.make_book_from_device_row), rows )
            
        LoopProgressDialog(self.gui,
                           book_list,
                           partial(self.get_list_story_urls_loop, db=self.gui.current_db),
                           self.get_list_story_urls_finish,
                           init_label=_("Collecting URLs for stories..."),
                           win_title=_("Get URLs for stories"),
                           status_prefix=_("URL retrieved"))
            
    def get_list_story_urls_loop(self,book,db=None):
        if book['calibre_id']:
            book['url'] = self.get_story_url(db,book_id=book['calibre_id'])
        elif book['path']:
            book['url'] = self.get_story_url(db,path=book['path'])
            
        if book['url'] == None:
            book['good']=False
        else:
            book['good']=True
            
    def get_list_story_urls_finish(self, book_list):
        url_list = [ x['url'] for x in book_list if x['good'] ]
        if url_list:
            d = ViewLog(_("List of Story URLs"),"\n".join(url_list),parent=self.gui)
            d.setWindowIcon(get_icon('bookmarks.png'))
            d.exec_()
        else:
            info_dialog(self.gui, _('List of URLs'),
                        _('No Story URLs found in selected books.'),
                        show=True,
                        show_copy_button=False)
                
    def reject_list_urls(self):
        if self.is_library_view():
            book_list = map( partial(self.make_book_id_only),
                             self.gui.library_view.get_selected_ids() )

        else: # device view, get from epubs on device.
            view = self.gui.current_view()
            rows = view.selectionModel().selectedRows()
            #paths = view.model().paths(rows)
            book_list = map( partial(self.make_book_from_device_row), rows )
            
        if len(book_list) == 0 :
            self.gui.status_bar.show_message(_('No Selected Books have URLs to Reject'), 3000)
            return

        # Progbar because fetching urls from device epubs can be slow.
        LoopProgressDialog(self.gui,
                           book_list,
                           partial(self.reject_list_urls_loop, db=self.gui.current_db),
                           self.reject_list_urls_finish,
                           init_label=_("Collecting URLs for Reject List..."),
                           win_title=_("Get URLs for Reject List"),
                           status_prefix=_("URL retrieved"))
            
    def reject_list_urls_loop(self,book,db=None):
        self.get_list_story_urls_loop(book,db) # common with get_list_story_urls_loop
        if book['calibre_id']:
            # want title/author, too, for rejects.
            self.populate_book_from_calibre_id(book,db)
        if book['url']:
            # get existing note, if on rejected list.
            book['oldrejnote']=rejecturllist.get_note(book['url'])
            
    def reject_list_urls_finish(self, book_list):

        # construct reject list of objects
        reject_list = [ RejectUrlEntry(x['url'],
                                       x['oldrejnote'],
                                       x['title'],
                                       ', '.join(x['author']),
                                       book_id=x['calibre_id'])
                        for x in book_list if x['good'] ]
        if reject_list:
            d = RejectListDialog(self.gui,reject_list,
                                 rejectreasons=rejecturllist.get_reject_reasons())
            d.exec_()
            
            if d.result() != d.Accepted:
                return

            rejecturllist.add(d.get_reject_list())

            if d.get_deletebooks():
                self.gui.iactions['Remove Books'].do_library_delete(d.get_reject_list_ids())
            
        else:
            message="<p>"+_("Rejecting FFDL URLs: None of the books selected have FanFiction URLs.")+"</p><p>"+_("Proceed to Remove?")+"</p>"
            if confirm(message,'fanfictiondownloader_reject_non_fanfiction', self.gui):
                self.gui.iactions['Remove Books'].delete_books()

    def add_dialog(self,url_list_text=None,merge=False,anthology_url=None):
        'Both new individual stories and new anthologies are created here.'

        if not url_list_text:
            url_list = self.get_urls_clip()
            url_list_text = "\n".join(url_list)
        
        # AddNewDialog collects URLs, format and presents buttons.
        # add_new_dialog is modeless and reused, both for new stories
        # and anthologies, and for updating existing anthologies.
        self.add_new_dialog.show_dialog(url_list_text,
                                        self.prep_downloads,
                                        merge=merge,
                                        newmerge=True,
                                        extraoptions={'anthology_url':anthology_url})

    def update_anthology(self):
        if not self.get_epubmerge_plugin():
            self.gui.status_bar.show_message(_('Cannot Make Anthologys without %s')%'EpubMerge 1.3.1+', 3000)
            return
            
        if not self.is_library_view():
            self.gui.status_bar.show_message(_('Cannot Update Books from Device View'), 3000)
            return
        
        if len(self.gui.library_view.get_selected_ids()) != 1:
            self.gui.status_bar.show_message(_('Can only update 1 anthology at a time'), 3000)
            return
        
        db = self.gui.current_db
        book_id = self.gui.library_view.get_selected_ids()[0]
        mergebook = self.make_book_id_only(book_id)
        self.populate_book_from_calibre_id(mergebook, db)

        if not db.has_format(book_id,'EPUB',index_is_id=True):
            self.gui.status_bar.show_message(_('Can only Update Epub Anthologies'), 3000)
            return
            
        tdir = PersistentTemporaryDirectory(prefix='ffdl_anthology_')
        logger.debug("tdir:\n%s"%tdir)

        bookepubio = StringIO(db.format(book_id,'EPUB',index_is_id=True))
        
        filenames = self.get_epubmerge_plugin().do_unmerge(bookepubio,tdir)
        urlmapfile = {}
        url_list = []
        for f in filenames:
            url = get_dcsource(f)
            if url:
                urlmapfile[url]=f
                url_list.append(url)

        if not filenames or len(filenames) != len (url_list):
            info_dialog(self.gui, _("Cannot Update Anthology"),
                        "<p>"+_("Cannot Update Anthology")+"</p><p>"+_("Book isn't an FFDL Anthology or contains book(s) without valid FFDL URLs."),
                        show=True,
                        show_copy_button=False)
            remove_dir(tdir)
            return

        # get list from identifiers:url/uri if present, but only if
        # it's *not* a valid story URL.
        mergeurl = self.get_story_url(db,book_id)
        if mergeurl and not self.is_good_downloader_url(mergeurl):
            url_list = self.get_urls_from_page(mergeurl)

        url_list_text = "\n".join(url_list)
        
        #print("urlmapfile:%s"%urlmapfile)
        
        # AddNewDialog collects URLs, format and presents buttons.
        # add_new_dialog is modeless and reused, both for new stories
        # and anthologies, and for updating existing anthologies.
        self.add_new_dialog.show_dialog(url_list_text,
                                        self.prep_anthology_downloads,
                                        show=False,
                                        merge=True,
                                        newmerge=False,
                                        extrapayload=urlmapfile,
                                        extraoptions={'tdir':tdir,
                                                      'mergebook':mergebook})
        # Need to use AddNewDialog modal here because it's an update
        # of an existing book.  Don't want the user deleting it or
        # switching libraries on us.
        self.add_new_dialog.exec_()


    def prep_anthology_downloads(self, options, update_books,
                                 merge=False, urlmapfile=None):
        
        if isinstance(update_books,basestring):
            url_list = split_text_to_urls(update_books)
            update_books = self.convert_urls_to_books(url_list)
        
        for j, book in enumerate(update_books):
            url = book['url']
            book['listorder'] = j
            if url in urlmapfile:
                #print("found epub for %s"%url)
                book['epub_for_update']=urlmapfile[url]
                del urlmapfile[url]
            #else:
                #print("didn't found epub for %s"%url)

        if urlmapfile:
            text = '''
                 <p>%s</p>
                 <p>%s</p>
                 <ul>
                 <li>%s</li>
                 </ul>
                 <p>%s</p>'''%(
                _('There are %d stories in the current anthology that are <b>not</b> going to be kept if you go ahead.')%len(urlmapfile),
                _('Story URLs that will be removed:'),
                "</li><li>".join(urlmapfile.keys()),
                _('Update anyway?'))
            if not question_dialog(self.gui, _('Stories Removed'),
                               text, show_copy_button=False):
                logger.debug("Canceling anthology update due to removed stories.")
                return

        # Now that we've 
        self.prep_downloads( options, update_books, merge=True )
        
    def update_dialog(self, id_list=None):
        if not self.is_library_view():
            self.gui.status_bar.show_message(_('Cannot Update Books from Device View'), 3000)
            return

        if not id_list:
            id_list = self.gui.library_view.get_selected_ids()
        
        if len(id_list) == 0:
            self.gui.status_bar.show_message(_('No Selected Books to Update'), 3000)
            return
        #print("update_dialog()")
        
        db = self.gui.current_db
        books = map( self.make_book_id_only, id_list )

        for j, book in enumerate(books):
            book['listorder'] = j

        LoopProgressDialog(self.gui,
                           books,
                           partial(self.populate_book_from_calibre_id, db=self.gui.current_db),
                           self.update_dialog_finish,
                           init_label=_("Collecting stories for update..."),
                           win_title=_("Get stories for updates"),
                           status_prefix=_("URL retrieved"))            
        
        #books = self.convert_calibre_ids_to_books(db, book_ids)
        #print("update books:%s"%books)

    def update_dialog_finish(self,book_list):
        '''Present list to update and head to prep when done.'''
        
        d = UpdateExistingDialog(self.gui,
                                 _('Update Existing List'),
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
            self.prep_downloads( options, update_books )
            
    def get_urls_clip(self,storyurls=True):
        url_list = []
        if prefs['urlsfromclip']:
            for url in unicode(QApplication.instance().clipboard().text()).split():
                if not storyurls or self.is_good_downloader_url(url):
                    url_list.append(url)
                    
        return url_list

    def apply_settings(self):
        # No need to do anything with perfs here, but we could.
        prefs

    def make_id_searchstr(self,url):
        # older idents can be uri vs url and have | instead of : after
        # http, plus many sites are now switching to https.
        return 'identifiers:"~ur(i|l):~^%s$"'%re.sub(r'https?\\\:','https?(\:|\|)',re.escape(url))

    def prep_downloads(self, options, books, merge=False, extrapayload=None):
        '''Fetch metadata for stories from servers, launch BG job when done.'''

        if isinstance(books,basestring):
            url_list = split_text_to_urls(books)
            books = self.convert_urls_to_books(url_list)

        ## for tweak_fg_sleep
        options['ffnetcount']=len(filter(lambda x : x['site']=='www.fanfiction.net', books))

        options['version'] = self.version
        logger.debug(self.version)
        options['personal.ini'] = get_ffdl_personalini()
        
        #print("prep_downloads:%s"%books)

        if 'tdir' not in options: # if merging an anthology, there's alread a tdir.
            # create and pass temp dir.
            tdir = PersistentTemporaryDirectory(prefix='fanfictiondownloader_')
            options['tdir']=tdir

        if 0 < len(filter(lambda x : x['good'], books)):
            self.gui.status_bar.show_message(_('Started fetching metadata for %s stories.')%len(books), 3000)
            LoopProgressDialog(self.gui,
                               books,
                               partial(self.prep_download_loop, options = options, merge=merge),
                               partial(self.start_download_job, options = options, merge=merge))
        else:
            self.gui.status_bar.show_message(_('No valid story URLs entered.'), 3000)
        # LoopProgressDialog calls prep_download_loop for each 'good' story,
        # prep_download_loop updates book object for each with metadata from site,
        # LoopProgressDialog calls start_download_job at the end which goes
        # into the BG, or shows list if no 'good' books.

    def prep_download_loop(self,book,
                           options={'fileform':'epub',
                                    'collision':ADDNEW,
                                    'updatemeta':True,
                                    'updateepubcover':True},
                           merge=False):
        '''
        Update passed in book dict with metadata from website and
        necessary data.  To be called from LoopProgressDialog
        'loop'.  Also pops dialogs for is adult, user/pass.
        '''

        url = book['url']
        logger.debug("url:%s"%url)
        mi = None

        if not merge: # skip reject list when merging.
            if rejecturllist.check(url):
                rejnote = rejecturllist.get_full_note(url)
                if prefs['reject_always'] or question_dialog(self.gui, _('Reject URL?'),'''
                          <h3>%s</h3>
                          <p>%s</p>
                          <p>"<b>%s</b>"</p>
                          <p>%s</p>
                          <p>%s</p>'''%(
                        _('Reject URL?'),
                        _('<b>%s</b> is on your Reject URL list:')%url,
                        rejnote,
                        _("Click '<b>Yes</b>' to Reject."),
                        _("Click '<b>No</b>' to download anyway.")),
                                   show_copy_button=False):
                    book['comment'] = _("Story on Reject URLs list (%s).")%rejnote
                    book['good']=False
                    book['icon']='rotate-right.png'
                    book['status'] = _('Rejected')
                    return
                else:
                    if question_dialog(self.gui, _('Remove Reject URL?'),'''
                              <h3>%s</h3>
                              <p>%s</p>
                              <p>"<b>%s</b>"</p>
                              <p>%s</p>
                              <p>%s</p>'''%(
                            _("Remove URL from Reject List?"),
                            _('<b>%s</b> is on your Reject URL list:')%url,
                            rejnote,
                            _("Click '<b>Yes</b>' to remove it from the list,"),
                            _("Click '<b>No</b>' to leave it on the list.")),
                                       show_copy_button=False):
                        rejecturllist.remove(url)
            
        # The current database shown in the GUI
        # db is an instance of the class LibraryDatabase2 from database.py
        # This class has many, many methods that allow you to do a lot of
        # things.
        db = self.gui.current_db
        
        fileform  = options['fileform']
        collision = options['collision']
        updatemeta= options['updatemeta']
        updateepubcover= options['updateepubcover']

        # Dialogs should prevent this case now.
        if collision in (UPDATE,UPDATEALWAYS) and fileform != 'epub':
            raise NotGoingToDownload(_("Cannot update non-epub format."))
        
        if not book['good']:
            # book has already been flagged bad for whatever reason.
            return
        
        skip_date_update = False
        
        adapter = get_ffdl_adapter(url,fileform)
        ## save and share cookiejar and pagecache between all
        ## downloads.
        if 'pagecache' not in options:
            options['pagecache'] = adapter.get_empty_pagecache()
        adapter.set_pagecache(options['pagecache'])
        if 'cookiejar' not in options:
            options['cookiejar'] = adapter.get_empty_cookiejar()
        adapter.set_cookiejar(options['cookiejar'])
            
        # reduce foreground sleep time for ffnet when few books.
        if 'ffnetcount' in options and \
                adapter.getConfig('tweak_fg_sleep') and \
                adapter.getSiteDomain() == 'www.fanfiction.net':
            minslp = float(adapter.getConfig('min_fg_sleep'))
            maxslp = float(adapter.getConfig('max_fg_sleep'))
            dwnlds = float(adapter.getConfig('max_fg_sleep_at_downloads'))
            m = (maxslp-minslp) / (dwnlds-1)
            b = minslp - m
            slp = min(maxslp,m*float(options['ffnetcount'])+b)
            #print("m:%s b:%s = %s"%(m,b,slp))
            adapter.set_sleep(slp)

        ## three tries, that's enough if both user/pass & is_adult needed,
        ## or a couple tries of one or the other
        for x in range(0,2):
            try:
                adapter.getStoryMetadataOnly(get_cover=False)
            except exceptions.FailedToLogin, f:
                logger.warn("Login Failed, Need Username/Password.")
                userpass = UserPassDialog(self.gui,url,f)
                userpass.exec_() # exec_ will make it act modal
                if userpass.status:
                    adapter.username = userpass.user.text()
                    adapter.password = userpass.passwd.text()
                
            except exceptions.AdultCheckRequired:
                if question_dialog(self.gui, _('Are You an Adult?'), '<p>'+
                                   _("%s requires that you be an adult.  Please confirm you are an adult in your locale:")%url,
                                   show_copy_button=False):
                    adapter.is_adult=True

        # let other exceptions percolate up.
        story = adapter.getStoryMetadataOnly(get_cover=False)

        series = story.getMetadata('series')
        if not merge and series and prefs['checkforseriesurlid']:
            # try to find *series anthology* by *seriesUrl* identifier url or uri first.
            searchstr = self.make_id_searchstr(story.getMetadata('seriesUrl'))
            identicalbooks = db.search_getting_ids(searchstr, None)
            # print("searchstr:%s"%searchstr)
            # print("identicalbooks:%s"%identicalbooks)
            if len(identicalbooks) > 0 and question_dialog(self.gui, _('Skip Story?'),'''
                                                              <h3>%s</h3>
                                                              <p>%s</p>
                                                              <p>%s</p>
                                                              <p>%s</p>
                                                           '''%(
                                                           _('Skip Anthology Story?'),
                                                           _('"<b>%s</b>" is in series "<b><a href="%s">%s</a></b>" that you have an anthology book for.')%(story.getMetadata('title'),story.getMetadata('seriesUrl'),series[:series.index(' [')]),
                                                           _("Click '<b>Yes</b>' to Skip."),
                                                           _("Click '<b>No</b>' to download anyway.")),
                                                           show_copy_button=False):
                book['comment'] = _("Story in Series Anthology(%s).")%series
                book['title'] = story.getMetadata('title')
                book['author'] = [story.getMetadata('author')]
                book['good']=False
                book['icon']='rotate-right.png'
                book['status'] = _('Skipped')
                return
                

        ################################################################################################################################################33

        # set PI version instead of default.
        if 'version' in options:
            story.setMetadata('version',options['version'])

        # all_metadata duplicates some data, but also includes extra_entries, etc.
        book['all_metadata'] = story.getAllMetadata(removeallentities=True)

        book['title'] = story.getMetadata("title", removeallentities=True)
        book['author_sort'] = book['author'] = story.getList("author", removeallentities=True)
        book['publisher'] = story.getMetadata("site")
        book['tags'] = story.getSubjectTags(removeallentities=True)
        if story.getMetadata("description"):
            book['comments'] = sanitize_comments_html(story.getMetadata("description"))
        else:
            book['comments']=''
        book['series'] = story.getMetadata("series", removeallentities=True)
        
        book['is_adult'] = adapter.is_adult
        book['username'] = adapter.username
        book['password'] = adapter.password

        book['icon'] = 'plus.png'
        book['status'] = _('Add')
        if story.getMetadataRaw('datePublished'):
            book['pubdate'] = story.getMetadataRaw('datePublished').replace(tzinfo=local_tz)
        if story.getMetadataRaw('dateUpdated'):
            book['updatedate'] = story.getMetadataRaw('dateUpdated').replace(tzinfo=local_tz)
        if story.getMetadataRaw('dateCreated'):
            book['timestamp'] = story.getMetadataRaw('dateCreated').replace(tzinfo=local_tz)
        else:
            book['timestamp'] = None # need *something* there for calibre.

        if not merge:# skip all the collision code when d/ling for merging.
            if collision in (CALIBREONLY):
                book['icon'] = 'metadata.png'
                book['status'] = _('Meta')
            
            book_id = None
            
            if book['calibre_id'] != None:
                # updating an existing book.  Update mode applies.
                logger.debug("update existing id:%s"%book['calibre_id'])
                book_id = book['calibre_id']
                # No handling needed: OVERWRITEALWAYS,CALIBREONLY
                
            # only care about collisions when not ADDNEW
            elif collision != ADDNEW:
                # 'new' book from URL.  collision handling applies.
                logger.debug("from URL(%s)"%url)
    
                # try to find by identifier url or uri first.
                searchstr = self.make_id_searchstr(url)
                identicalbooks = db.search_getting_ids(searchstr, None)
                # print("searchstr:%s"%searchstr)
                # print("identicalbooks:%s"%identicalbooks)
                if len(identicalbooks) < 1:
                    # find dups
                    authlist = story.getList("author", removeallentities=True)
                    mi = MetaInformation(story.getMetadata("title", removeallentities=True),
                                         authlist)
                    identicalbooks = db.find_identical_books(mi)
                    if len(identicalbooks) > 0:
                        logger.debug("existing found by title/author(s)")
    
                else:
                    logger.debug("existing found by identifier URL")
                    
                if collision == SKIP and identicalbooks:
                    raise NotGoingToDownload(_("Skipping duplicate story."),"list_remove.png")
    
                if len(identicalbooks) > 1:
                    raise NotGoingToDownload(_("More than one identical book by Identifer URL or title/author(s)--can't tell which book to update/overwrite."),"minusminus.png")
    
                ## changed: add new book when CALIBREONLY if none found.
                if collision == CALIBREONLY and not identicalbooks:
                    collision = ADDNEW
                    options['collision'] = ADDNEW
    
                if len(identicalbooks)>0:
                    book_id = identicalbooks.pop()
                    book['calibre_id'] = book_id
                    book['icon'] = 'edit-redo.png'
                    book['status'] = _('Update')
    
                if book_id and mi: # book_id and mi only set if matched by title/author.
                    liburl = self.get_story_url(db,book_id)
                    if book['url'] != liburl and prefs['checkforurlchange'] and \
                        not (book['url'].replace('https','http') == liburl): # several sites have been changing to
                                                                             # https now.  Don't flag when that's the only change.
                        # special case for ffnet urls change to https.
                        if not question_dialog(self.gui, _('Change Story URL?'),'''
                                                  <h3>%s</h3>
                                                  <p>%s</p>
                                                  <p>%s</p>
                                                  <p>%s</p>
                                                  <p>%s</p>
                                                  <p>%s</p>'''%(
                                _('Change Story URL?'),
                                _('<b>%s</b> by <b>%s</b> is already in your library with a different source URL:')%(mi.title,', '.join(mi.author)),
                                _('In library: <a href="%(liburl)s">%(liburl)s</a>')%{'liburl':liburl},
                                _('New URL: <a href="%(newurl)s">%(newurl)s</a>')%{'newurl':book['url']},
                                _("Click '<b>Yes</b>' to update/overwrite book with new URL."),
                                _("Click '<b>No</b>' to skip updating/overwriting this book.")),
                                               show_copy_button=False):
                            if question_dialog(self.gui, _('Download as New Book?'),'''
                                                  <h3>%s</h3>
                                                  <p>%s</p>
                                                  <p>%s</p>
                                                  <p>%s</p>
                                                  <p>%s</p>
                                                  <p>%s</p>'''%(
                                    _('Download as New Book?'),
                                    _('<b>%s</b> by <b>%s</b> is already in your library with a different source URL.')%(mi.title,', '.join(mi.author)),
                                    _('You chose not to update the existing book.  Do you want to add a new book for this URL?'),
                                    _('New URL: <a href="%(newurl)s">%(newurl)s</a>')%{'newurl':book['url']},
                                    _("Click '<b>Yes</b>' to a new book with new URL."),
                                    _("Click '<b>No</b>' to skip URL.")),
                                               show_copy_button=False):
                                book_id = None
                                mi = None
                                book['calibre_id'] = None
                            else:
                                book['comment'] = _("Update declined by user due to differing story URL(%s)")%liburl
                                book['good']=False
                                book['icon']='rotate-right.png'
                                book['status'] = _('Different URL')
                                return
        
            if book_id != None and collision != ADDNEW:
                if collision in (CALIBREONLY):
                    book['comment'] = _('Metadata collected.')
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
                        urlchaptercount = int(story.getMetadata('numChapters').replace(',',''))
                        if chaptercount == urlchaptercount:
                            if collision == UPDATE:
                                raise NotGoingToDownload(_("Already contains %d chapters.")%chaptercount,'edit-undo.png')
                            else:
                                # UPDATEALWAYS
                                skip_date_update = True
                        elif chaptercount > urlchaptercount:
                            raise NotGoingToDownload(_("Existing epub contains %d chapters, web site only has %d. Use Overwrite to force update.") % (chaptercount,urlchaptercount),'dialog_error.png')
                        elif chaptercount == 0:
                            raise NotGoingToDownload(_("FFDL doesn't recognize chapters in existing epub, epub is probably from a different source. Use Overwrite to force update."),'dialog_error.png')
        
                if collision == OVERWRITE and \
                        db.has_format(book_id,formmapping[fileform],index_is_id=True):
                    # check make sure incoming is newer.
                    lastupdated=story.getMetadataRaw('dateUpdated')
                    fileupdated=datetime.fromtimestamp(os.stat(db.format_abspath(book_id, formmapping[fileform], index_is_id=True))[8])

                    # updated doesn't have time (or is midnight), use dates only.
                    # updated does have time, use full timestamps.
                    if (lastupdated.time() == time.min and fileupdated.date() > lastupdated.date()) or \
                            (lastupdated.time() != time.min and fileupdated > lastupdated):
                        raise NotGoingToDownload(_("Not Overwriting, web site is not newer."),'edit-undo.png')
                    
                    
        
                # For update, provide a tmp file copy of the existing epub so
                # it can't change underneath us.  Now also overwrite for logpage preserve.
                if collision in (UPDATE,UPDATEALWAYS,OVERWRITE,OVERWRITEALWAYS) and \
                        fileform == 'epub' and \
                        db.has_format(book['calibre_id'],'EPUB',index_is_id=True):
                    tmp = PersistentTemporaryFile(prefix='old-%s-'%book['calibre_id'],
                                                  suffix='.epub',
                                                  dir=options['tdir'])
                    db.copy_format_to(book_id,fileform,tmp,index_is_id=True)
                    logger.debug("existing epub tmp:"+tmp.name)
                    book['epub_for_update'] = tmp.name

            if book_id != None and prefs['injectseries']:
                mi = db.get_metadata(book_id,index_is_id=True)
                if not book['series'] and mi.series != None:
                    book['calibre_series'] = (mi.series,mi.series_index)
                    #print("calibre_series:%s [%s]"%book['calibre_series'])
                
        if book['good']: # there shouldn't be any !'good' books at this point.
            # if still 'good', make a temp file to write the output to.
            # For HTML format users, make the filename inside the zip something reasonable.
            # For crazy long titles/authors, limit it to 200chars.
            # For weird/OS-unsafe characters, use file safe only.
            tmp = PersistentTemporaryFile(prefix=story.formatFileName("${title}-${author}-",allowunsafefilename=False)[:100],
                                          suffix='.'+options['fileform'],
                                          dir=options['tdir'])
            logger.debug("title:"+book['title'])
            logger.debug("outfile:"+tmp.name)
            book['outfile'] = tmp.name
            
            # cookiejar = PersistentTemporaryFile(prefix=story.formatFileName("${title}-${author}-",allowunsafefilename=False)[:100],
            #                                     suffix='.cookiejar',
            #                                     dir=options['tdir'])
            # adapter.save_cookiejar(cookiejar.name)
            # book['cookiejar'] = cookiejar.name
            # pagecache = PersistentTemporaryFile(prefix=story.formatFileName("${title}-${author}-",allowunsafefilename=False)[:100],
            #                                     suffix='.pagecache',
            #                                     dir=options['tdir'])
            # adapter.save_pagecache(pagecache.name)
            # book['pagecache'] = pagecache.name
                
        return
        
    def start_download_job(self,book_list,
                            options={'fileform':'epub',
                                     'collision':ADDNEW,
                                     'updatemeta':True,
                                     'updateepubcover':True},
                            merge=False):
        '''
        Called by LoopProgressDialog to start story downloads BG processing.
        adapter_list is a list of tuples of (url,adapter)
        '''
        #print("start_download_job:book_list:%s"%book_list)

        ## No need to BG process when CALIBREONLY!  Fake it.
        #print("options:%s"%options)
        if options['collision'] == CALIBREONLY:
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
            ## updating error col.
            msg = '''
                    <p>%s</p>
                    <p>%s</p>
                    <p>%s</p>'''%(
                _('None of the <b>%d</b> URLs/stories given can be/need to be downloaded.')%len(book_list),
                _('See log for details.'),
                _('Proceed with updating your library(Error Column, if configured)?'))
    
            htmllog='<html><body><table border="1"><tr><th>'+_('Status')+'</th><th>'+_('Title')+'</th><th>'+_('Author')+'</th><th>'+_('Comment')+'</th><th>URL</th></tr>'
            for book in book_list:
                if 'status' in book:
                    status = book['status']
                else:
                    status = _('Bad')
                htmllog = htmllog + '<tr><td>' + '</td><td>'.join([escapehtml(status),escapehtml(book['title']),escapehtml(", ".join(book['author'])),escapehtml(book['comment']),book['url']]) + '</td></tr>'
            
            htmllog = htmllog + '</table></body></html>'

            payload = ([], book_list, options)
            self.gui.proceed_question(self.update_error_column,
                                      payload, htmllog,
                                      _('FFDL log'), _('FFDL download ended'), msg,
                                      show_copy_button=False)
            return

        cookiejarfile = PersistentTemporaryFile(suffix='.cookiejar',
                                                dir=options['tdir'])
        options['cookiejar'].save(cookiejarfile.name,
                                  ignore_discard=True,
                                  ignore_expires=True)
        options['cookiejarfile']=cookiejarfile.name
        del options['cookiejar'] ## can't be pickled.
        
        func = 'arbitrary_n'
        cpus = self.gui.job_manager.server.pool_size
        args = ['calibre_plugins.fanfictiondownloader_plugin.jobs', 'do_download_worker',
                (book_list, options, cpus)]
        desc = _('Download FanFiction Book')
        job = self.gui.job_manager.run_job(
                self.Dispatcher(partial(self.download_list_completed,options=options,merge=merge)),
                func, args=args,
                description=desc)
        
        self.gui.jobs_pointer.start()
        self.gui.status_bar.show_message(_('Starting %d FanFictionDownLoads')%len(book_list),3000)

    def update_books_loop(self,book,db=None,
                     options={'fileform':'epub',
                              'collision':ADDNEW,
                              'updatemeta':True,
                              'updateepubcover':True}):
        custom_columns = self.gui.library_view.model().custom_columns
        if book['calibre_id'] and prefs['errorcol'] != '' and prefs['errorcol'] in custom_columns:
            label = custom_columns[prefs['errorcol']]['label']
            if not book['good']:
                logger.debug("record/update error message column %s %s"%(book['title'],book['url']))
                db.set_custom(book['calibre_id'], book['comment'], label=label, commit=True) # book['comment']
            else:
                db.set_custom(book['calibre_id'], '', label=label, commit=True) # book['comment']
                
        if not book['good']:
            return # only update errorcol on error.
        
        logger.debug("add/update %s %s"%(book['title'],book['url']))
        mi = self.make_mi_from_book(book)
                
        if options['collision'] != CALIBREONLY:
            self.add_book_or_update_format(book,options,prefs,mi)

        if options['collision'] == CALIBREONLY or \
                ( (options['updatemeta'] or book['added']) and book['good'] ):
            try:
                self.update_metadata(db, book['calibre_id'], book, mi, options)
            except:
                det_msg = "".join(traceback.format_exception(*sys.exc_info()))+"\n"+_("Story Details:")+pretty_book(book)
                logger.error("Error Updating Metadata:\n%s"%det_msg)
                error_dialog(self.gui,
                             _("Error Updating Metadata"),
                             "<p>"+_("An error has occurred while FFDL was updating calibre's metadata for <a href='%s'>%s</a>.")%(book['url'],book['title'])+"</p>"+
                             _("The ebook has been updated, but the metadata has not."),
                             det_msg=det_msg,
                             show=True)

    def update_books_finish(self, book_list, options={}, showlist=True):
        '''Notify calibre about updated rows, update external plugins
        (Reading Lists & Count Pages) as configured'''

        add_list = filter(lambda x : x['good'] and x['added'], book_list)
        add_ids = [ x['calibre_id'] for x in add_list ]
        update_list = filter(lambda x : x['good'] and not x['added'], book_list)
        update_ids = [ x['calibre_id'] for x in update_list ]
        all_ids = add_ids + update_ids

        failed_list = filter(lambda x : not x['good'] , book_list)
        failed_ids = [ x['calibre_id'] for x in failed_list ]

        if options['collision'] != CALIBREONLY and \
                (prefs['addtolists'] or prefs['addtoreadlists']):
            self.update_reading_lists(all_ids,add=True)
        
        if len(add_list):
            self.gui.library_view.model().books_added(len(add_list))
            self.gui.library_view.model().refresh_ids(add_ids)

        if len(update_list):
            self.gui.library_view.model().refresh_ids(update_ids)

        current = self.gui.library_view.currentIndex()
        self.gui.library_view.model().current_changed(current, self.previous)
        self.gui.tags_view.recount()
        
        if self.gui.cover_flow:
            self.gui.cover_flow.dataChanged()

        if showlist and prefs['mark']: # don't use with anthology
            db = self.gui.current_db
            marked_ids = dict()
            marked_text = "ffdl_success"
            for index, book_id in enumerate(all_ids):
                marked_ids[book_id] = '%s_%04d' % (marked_text, index)
            for index, book_id in enumerate(failed_ids):
                marked_ids[book_id] = 'ffdl_failed_%04d' % index
            # Mark the results in our database
            db.set_marked_ids(marked_ids)
            
            if prefs['showmarked']: # show add/update
                # Search to display the list contents
                self.gui.search.set_search_string('marked:' + marked_text)
                # Sort by our marked column to display the books in order
                self.gui.library_view.sort_by_named_field('marked', True)
                
        self.gui.status_bar.show_message(_('Finished Adding/Updating %d books.')%(len(update_list) + len(add_list)), 3000)
        remove_dir(options['tdir'])
        
        if 'Count Pages' in self.gui.iactions and len(prefs['countpagesstats']) and len(all_ids):
            cp_plugin = self.gui.iactions['Count Pages']
            cp_plugin.count_statistics(all_ids,prefs['countpagesstats'])

        if prefs['autoconvert'] and options['collision'] != CALIBREONLY:
            self.gui.status_bar.show_message(_('Starting auto conversion of %d books.')%(len(all_ids)), 3000)
            self.gui.iactions['Convert Books'].auto_convert_auto_add(all_ids)

    def download_list_completed(self, job, options={},merge=False):
        if job.failed:
            self.gui.job_exception(job, dialog_title='Failed to Download Stories')
            return

        self.previous = self.gui.library_view.currentIndex()
        db = self.gui.current_db

        book_list = job.result
        good_list = filter(lambda x : x['good'], book_list)
        bad_list = filter(lambda x : not x['good'], book_list)
        good_list = sorted(good_list,key=lambda x : x['listorder'])
        bad_list = sorted(bad_list,key=lambda x : x['listorder'])
        #print("book_list:%s"%book_list)
        payload = (good_list, bad_list, options)
        
        if merge:
            if len(good_list) < 1:
                info_dialog(self.gui, _('No Good Stories for Anthology'),
                            _('No good stories/updates where downloaded, Anthology creation/update aborted.'),
                            show=True,
                            show_copy_button=False)
                return

            msg = '<p>'+_('FFDL found <b>%s</b> good and <b>%s</b> bad updates.')%(len(good_list),len(bad_list))+'</p>'
            if len(bad_list) > 0:
                msg = msg + '''
                            <p>%s</p>
                            <p>%s</p>
                            <p>%s</p>
                            <p>%s</p>'''%(
                    _('Are you sure you want to continue with creating/updating this Anthology?'),
                    _('Any updates that failed will <b>not</b> be included in the Anthology.'),
                    _("However, if there's an older version, it will still be included."),
                    _('See log for details.'))

            msg = msg + '<p>'+_('Proceed with updating this anthology and your library?')+ '</p>'
    
            htmllog='<html><body><table border="1"><tr><th>'+_('Status')+'</th><th>'+_('Title')+'</th><th>'+_('Author')+'</th><th>'+_('Comment')+'</th><th>URL</th></tr>'
            for book in sorted(good_list+bad_list,key=lambda x : x['listorder']):
                if 'status' in book:
                    status = book['status']
                else:
                    if book in good_list:
                        status = _('Good')
                    else:
                        status = _('Bad')
                htmllog = htmllog + '<tr><td>' + '</td><td>'.join([escapehtml(status),escapehtml(book['title']),escapehtml(", ".join(book['author'])),escapehtml(book['comment']),book['url']]) + '</td></tr>'
            
            htmllog = htmllog + '</table></body></html>'

            for book in bad_list:
                if 'epub_for_update' in book:
                    book['good']=True
                    book['outfile'] = book['epub_for_update']
                    good_list.append(book)
    
            do_update_func = self.do_download_merge_update
        else:        
            msg = '''
                  <p>%s</p>
                  <p>%s</p>
                  <p>%s</p>'''%(
                _('FFDL found <b>%s</b> good and <b>%s</b> bad updates.')%(len(good_list),len(bad_list)),
                _('See log for details.'),
                _('Proceed with updating your library?')
                )
    
            htmllog='<html><body><table border="1"><tr><th>'+_('Status')+'</th><th>'+_('Title')+'</th><th>'+_('Author')+'</th><th>'+_('Comment')+'</th><th>URL</th></tr>'
            for book in good_list:
                if 'status' in book:
                    status = book['status']
                else:
                    status = 'Good'
                htmllog = htmllog + '<tr><td>' + '</td><td>'.join([escapehtml(status),escapehtml(book['title']),escapehtml(", ".join(book['author'])),escapehtml(book['comment']),book['url']]) + '</td></tr>'
            
            for book in bad_list:
                if 'status' in book:
                    status = book['status']
                else:
                    status = 'Bad'
                htmllog = htmllog + '<tr><td>' + '</td><td>'.join([escapehtml(status),escapehtml(book['title']),escapehtml(", ".join(book['author'])),escapehtml(book['comment']),book['url']]) + '</td></tr>'
            
            htmllog = htmllog + '</table></body></html>'
    
            do_update_func = self.do_download_list_update
            
        self.gui.proceed_question(do_update_func,
                                  payload, htmllog,
                                  _('FFDL log'), _('FFDL download complete'), msg,
                                  show_copy_button=False)
        
    def do_download_merge_update(self, payload):
        
        (good_list,bad_list,options) = payload
        total_good = len(good_list)

        logger.debug("merge titles:\n%s"%"\n".join([ "%s %s"%(x['title'],x['listorder']) for x in good_list ]))

        good_list = sorted(good_list,key=lambda x : x['listorder'])
        bad_list = sorted(bad_list,key=lambda x : x['listorder'])
        
        self.gui.status_bar.show_message(_('Merging %s books.')%total_good)
        
        existingbook = None
        if 'mergebook' in options:
            existingbook = options['mergebook']
        #print("existingbook:\n%s"%existingbook)
        mergebook = self.merge_meta_books(existingbook,good_list,options['fileform'])

        if 'mergebook' in options:
            mergebook['calibre_id'] = options['mergebook']['calibre_id']

        if 'anthology_url' in options:
            mergebook['url'] = options['anthology_url']
                    
        #print("mergebook:\n%s"%mergebook)
        
        if mergebook['good']: # there shouldn't be any !'good' books at this point.
            # if still 'good', make a temp file to write the output to.
            tmp = PersistentTemporaryFile(suffix='.'+options['fileform'],
                                          dir=options['tdir'])
            logger.debug("title:"+mergebook['title'])
            logger.debug("outfile:"+tmp.name)
            mergebook['outfile'] = tmp.name

        self.get_epubmerge_plugin().do_merge(tmp.name,
                                             [ x['outfile'] for x in good_list ],
                                             titleopt=mergebook['title'],
                                             keepmetadatafiles=True,
                                             source=mergebook['url'])
        
        options['collision']=OVERWRITEALWAYS
        self.update_books_loop(mergebook,self.gui.current_db,options)
        self.update_books_finish([mergebook], options=options, showlist=False)
        
    def do_download_list_update(self, payload):
        
        (good_list,bad_list,options) = payload
        good_list = sorted(good_list,key=lambda x : x['listorder'])
        bad_list = sorted(bad_list,key=lambda x : x['listorder'])

        self.gui.status_bar.show_message(_('FFDL Adding/Updating books.'))

        if good_list or prefs['mark'] or (bad_list and prefs['errorcol'] != '' and prefs['errorcol'] in self.gui.library_view.model().custom_columns):
            LoopProgressDialog(self.gui,
                               good_list+bad_list,
                               partial(self.update_books_loop, options=options, db=self.gui.current_db),
                               partial(self.update_books_finish, options=options),
                               init_label=_("Updating calibre for FanFiction stories..."),
                               win_title=_("Update calibre for FanFiction stories"),
                               status_prefix=_("Updated"))

    def update_error_column(self,payload):
        '''Update custom error column if configured.'''
        (empty_list,book_list,options)=payload
        custom_columns = self.gui.library_view.model().custom_columns
        if prefs['mark'] or (prefs['errorcol'] != '' and prefs['errorcol'] in custom_columns):
            self.previous = self.gui.library_view.currentIndex() # used by update_books_finish.
            self.gui.status_bar.show_message(_('Adding/Updating %s BAD books.')%len(book_list))
            if (prefs['errorcol'] != '' and prefs['errorcol'] in custom_columns):
                label = custom_columns[prefs['errorcol']]['label']
            else:
                label = None
            LoopProgressDialog(self.gui,
                               book_list,
                               partial(self.update_error_column_loop, db=self.gui.current_db, label=label),
                               partial(self.update_books_finish, options=options),
                               init_label=_("Updating calibre for BAD FanFiction stories..."),
                               win_title=_("Update calibre for BAD FanFiction stories"),
                               status_prefix=_("Updated"))

    def update_error_column_loop(self,book,db=None,label=None):
        if book['calibre_id'] and label:
            logger.debug("add/update bad %s %s %s"%(book['title'],book['url'],book['comment']))
            db.set_custom(book['calibre_id'], book['comment'], label=label, commit=True)

    def add_book_or_update_format(self,book,options,prefs,mi=None):
        db = self.gui.current_db
        
        if mi == None:
            mi = self.make_mi_from_book(book)

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
            book['comment'] = _("Adding format to book failed for some reason...")
            book['good']=False
            book['icon']='dialog_error.png'
            book['status'] = _('Error')

        if prefs['deleteotherforms']:
            fmts = db.formats(book['calibre_id'], index_is_id=True).split(',')
            for fmt in fmts:
                if fmt != formmapping[options['fileform']]:
                    logger.debug("deleteotherforms remove f:"+fmt)
                    db.remove_format(book['calibre_id'], fmt, index_is_id=True)#, notify=False
        elif prefs['autoconvert']:
            ## 'Convert Book'.auto_convert_auto_add doesn't convert if
            ## the format is already there.
            fmt = calibre_prefs['output_format']
            # delete if there, but not if the format we just made.
            if fmt != formmapping[options['fileform']] and \
                    db.has_format(book_id,fmt,index_is_id=True):
                logger.debug("autoconvert remove f:"+fmt)
                db.remove_format(book['calibre_id'], fmt, index_is_id=True)#, notify=False
                

        return book_id

    def update_metadata(self, db, book_id, book, mi, options):
        oldmi = db.get_metadata(book_id,index_is_id=True)
        if prefs['keeptags']:
            old_tags = db.get_tags(book_id)
            #print("old_tags:%s"%old_tags)
            #print("mi.tags:%s"%mi.tags)
            # remove old Completed/In-Progress only if there's a new one.
            if 'Completed' in mi.tags or 'In-Progress' in mi.tags:
                old_tags = filter( lambda x : x not in ('Completed', 'In-Progress'), old_tags)
                # remove old Last Update tags if there are new ones.
            if len(filter( lambda x : not x.startswith("Last Update"), mi.tags)) > 0:
                old_tags = filter( lambda x : not x.startswith("Last Update"), old_tags)
                
            # mi.tags needs to be list, but set kills dups.
            # this way also removes case-mismatched dups, keeping old_tags version.
            foldedcase_tags = dict()
            for t in list(mi.tags) + list(old_tags):
                foldedcase_tags[t.lower()] = t

            mi.tags = foldedcase_tags.values()   
            #print("mi.tags:%s"%mi.tags)

        if book['all_metadata']['langcode']:
            mi.languages=[book['all_metadata']['langcode']]
        else:
            # Set language english, but only if not already set.
            if not oldmi.languages:
                mi.languages=['en']
                
        if options['fileform'] == 'epub' and prefs['updatecover']:
            existingepub = db.format(book_id,'EPUB',index_is_id=True, as_file=True)
            epubmi = get_metadata(existingepub,'EPUB')
            if epubmi.cover_data[1] is not None:
                try:
                    db.set_cover(book_id, epubmi.cover_data[1])
                except:
                    logger.info("Failed to set_cover, skipping")

        # implement 'newonly' flags here by setting to the current
        # value again.
        if not book['added']:
            for (col,newonly) in prefs['std_cols_newonly'].iteritems():
                if newonly:
                    if col == "identifiers":
                        mi.set_identifiers(oldmi.get_identifiers())
                    else:
                        try:
                            mi.__setattr__(col,oldmi.__getattribute__(col))
                        except AttributeError:
                            logger.warn("AttributeError? %s"%col)
                            pass

        db.set_metadata(book_id,mi)
        # mi.authors gets run through the string_to_authors and split on '&' ',' 'and' and 'with'
        db.set_authors(book_id,book['author']) # author is a list.

        # do configured column updates here.
        #print("all_metadata: %s"%book['all_metadata'])
        custom_columns = self.gui.library_view.model().custom_columns

        #print("prefs['custom_cols'] %s"%prefs['custom_cols'])
        for col, meta in prefs['custom_cols'].iteritems():
            #print("setting %s to %s"%(col,meta))
            if col not in custom_columns:
                logger.debug("%s not an existing column, skipping."%col)
                continue
            coldef = custom_columns[col]
            if col in prefs['custom_cols_newonly'] and prefs['custom_cols_newonly'][col] and not book['added']:
                logger.debug("Skipping custom column(%s) update, set to New Books Only"%coldef['name'])
                continue
            if not meta.startswith('status-') and meta not in book['all_metadata'] or \
                    meta.startswith('status-') and 'status' not in book['all_metadata']:
                logger.debug("No value for %s, skipping custom column(%s) update."%(meta,coldef['name']))
                continue
            if meta not in permitted_values[coldef['datatype']]:
                logger.debug("%s not a valid column type for %s, skipping."%(col,meta))
                continue
            label = coldef['label']
            if coldef['datatype'] in ('enumeration','text','comments','datetime','series'):
                db.set_custom(book_id, book['all_metadata'][meta], label, commit=False)
            elif coldef['datatype'] in ('int','float'):
                num = unicode(book['all_metadata'][meta]).replace(",","")
                if num != '':
                    db.set_custom(book_id, num, label=label, commit=False)
            elif coldef['datatype'] == 'bool' and meta.startswith('status-'):
                if meta == 'status-C':
                    val = book['all_metadata']['status'] == 'Completed'
                if meta == 'status-I':
                    val = book['all_metadata']['status'] == 'In-Progress'
                db.set_custom(book_id, val, label=label, commit=False)

        configuration = None
        if prefs['allow_custcol_from_ini']:
            configuration = get_ffdl_config(book['url'],options['fileform'])
            # meta => custcol[,a|n|r]
            # cliches=>\#acolumn,r
            for line in configuration.getConfig('custom_columns_settings').splitlines():
                if "=>" in line:
                    (meta,custcol) = map( lambda x: x.strip(), line.split("=>") )
                    flag='r'
                    if "," in custcol:
                        (custcol,flag) = map( lambda x: x.strip(), custcol.split(",") )

                    if meta not in book['all_metadata']:
                        # if double quoted, use as a literal value.
                        if meta[0] == '"' and meta[-1] == '"':
                            val = meta[1:-1]
                            logger.debug("No metadata value for %s, setting custom column(%s) literally to %s."%(meta,custcol,val))
                        else:
                            logger.debug("No value for %s, skipping custom column(%s) update."%(meta,custcol))
                            continue
                    else:
                        val = book['all_metadata'][meta]    
                    
                    if custcol not in custom_columns:
                        continue
                    else:
                        coldef = custom_columns[custcol]
                        label = coldef['label']

                    if flag == 'r' or book['added']: # flag 'n' isn't actually needed--*always* set if configured and new book.
                        if coldef['datatype'] in ('int','float'): # for favs, etc--site specific metadata.
                            if 'anthology_meta_list' in book and meta in book['anthology_meta_list']:
                                # re-split list, strip commas, convert to floats, sum up.
                                val = sum([ float(x.replace(",","")) for x in val.split(", ") ])
                            else:
                                val = unicode(val).replace(",","")
                        else:
                            val = val
                        if val != '':
                            if coldef['datatype'] == 'bool':
                                if val.lower() in ('t','true','1','yes','y'):
                                    val = True
                                elif val.lower() in ('f','false','0','no','n'):
                                    val = False
                                else:
                                    val = None # for tri-state 'booleans'. Yes/No/Null
                            db.set_custom(book_id, val, label=label, commit=False)

                    if flag == 'a':
                        vallist = []
                        try:
                            existing=db.get_custom(book_id,label=label,index_is_id=True)
                            if isinstance(existing,list):
                                vallist = existing
                            elif existing:
                                vallist = [existing]
                        except:
                            pass

                        if val:
                            vallist.append(val)
                            
                        db.set_custom(book_id, ", ".join(vallist), label=label, commit=False)

        # set author link if found.  All current adapters have authorUrl, except anonymous on AO3.
        # Moved down so author's already in the DB.
        if 'authorUrl' in book['all_metadata']:
            authurls = book['all_metadata']['authorUrl'].split(", ")
            authorlist = [ a.replace('&',';') for a in book['author'] ]
            authorids = db.new_api.get_item_ids('authors',authorlist)
            authordata = db.new_api.author_data(authorids.values())
            # print("\n\nauthorids:%s"%authorids)
            # print("authordata:%s"%authordata)

            author_id_to_link_map = dict()
            for i, author in enumerate(authorlist):
                author_id_to_link_map[authorids[author]] = authurls[i]

            # print("author_id_to_link_map:%s\n\n"%author_id_to_link_map)
            db.new_api.set_link_for_authors(author_id_to_link_map)
            
        db.commit()

        if 'Generate Cover' in self.gui.iactions and (book['added'] or not prefs['gcnewonly']):

            #logger.debug("Do Generate Cover added:%s gcnewonly:%s"%(book['added'],prefs['gcnewonly']))
            
            # force a refresh if generating cover so complex composite
            # custom columns are current and correct
            db.refresh_ids([book_id])
                
            gc_plugin = self.gui.iactions['Generate Cover']
            setting_name = None
            if prefs['allow_gc_from_ini']:
                if not configuration: # might already have it from allow_custcol_from_ini
                    configuration = get_ffdl_config(book['url'],options['fileform'])

                # template => regexp to match => GC Setting to use.
                # generate_cover_settings:
                # ${category} => Buffy:? the Vampire Slayer => Buffy
                for line in configuration.getConfig('generate_cover_settings').splitlines():
                    if "=>" in line:
                        (template,regexp,setting) = map( lambda x: x.strip(), line.split("=>") )
                        value = Template(template).safe_substitute(book['all_metadata']).encode('utf8')
                        # print("%s(%s) => %s => %s"%(template,value,regexp,setting))
                        if re.search(regexp,value):
                            setting_name = setting
                            break

                if setting_name:
                    logger.debug("Generate Cover Setting from generate_cover_settings(%s)"%line)
                    if setting_name not in gc_plugin.get_saved_setting_names():
                        logger.info("GC Name %s not found, discarding! (check personal.ini for typos)"%setting_name)
                        setting_name = None
                
            if not setting_name and book['all_metadata']['site'] in prefs['gc_site_settings']:
                setting_name =  prefs['gc_site_settings'][book['all_metadata']['site']]
                logger.debug("Generate Cover Setting from site(%s)"%setting_name)

            if not setting_name and 'Default' in prefs['gc_site_settings']:
                setting_name =  prefs['gc_site_settings']['Default']
                logger.debug("Generate Cover Setting from Default(%s)"%setting_name)
                
            if setting_name:
                logger.debug("Running Generate Cover with settings %s."%setting_name)
                realmi = db.get_metadata(book_id, index_is_id=True)
                gc_plugin.generate_cover_for_book(realmi,saved_setting_name=setting_name)

                if prefs['gc_polish_cover'] and \
                        options['fileform'] == "epub":
                    # set cover inside epub from calibre's polish feature
                    from calibre.ebooks.oeb.polish.main import polish, ALL_OPTS
                    from calibre.utils.logging import Log
                    from collections import namedtuple

                    # Couldn't find a better way to get the cover path.
                    cover_path = os.path.join(db.library_path, db.path(book_id, index_is_id=True), 'cover.jpg')
                    data = {'cover':cover_path}
                    #print("cover_path:%s"%cover_path)
                    opts = ALL_OPTS.copy()
                    opts.update(data)
                    O = namedtuple('Options', ' '.join(ALL_OPTS.iterkeys()))
                    opts = O(**opts)
                
                    log = Log(level=Log.DEBUG)
                    outfile = db.format_abspath(book_id, formmapping[options['fileform']], index_is_id=True)
                    #print("polish cover outfile:%s"%outfile)
                    polish({outfile:outfile}, opts, log, logger.info)
                

    def get_clean_reading_lists(self,lists):
        if lists == None or lists.strip() == "" :
            return []
        else:
            return filter( lambda x : x, map( lambda x : x.strip(), lists.split(',') ) )
        
    def update_reading_lists(self,book_ids,add=True):
        try:
            rl_plugin = self.gui.iactions['Reading List']
        except:
            if prefs['addtolists'] or prefs['addtoreadlists']:
                message="<p>"+_("You configured FanFictionDownLoader to automatically update Reading Lists, but you don't have the %s plugin installed anymore?")%'Reading List'+"</p>"
                confirm(message,'fanfictiondownloader_no_reading_list_plugin', self.gui)
            return
        
        if prefs['addtoreadlists']:
            if add:
                addremovefunc = rl_plugin.add_books_to_list
            else:
                addremovefunc = rl_plugin.remove_books_from_list
                
            lists = self.get_clean_reading_lists(prefs['read_lists'])
            if len(lists) < 1 :
                message="<p>"+_("You configured FanFictionDownLoader to automatically update \"To Read\" Reading Lists, but you don't have any lists set?")+"</p>"
                confirm(message,'fanfictiondownloader_no_read_lists', self.gui)
            for l in lists:
                if l in rl_plugin.get_list_names():
                    #print("add good read l:(%s)"%l)
                    addremovefunc(l,
                                  book_ids,
                                  display_warnings=False)
                else:
                    if l != '':
                        message="<p>"+_("You configured FanFictionDownLoader to automatically update Reading List '%s', but you don't have a list of that name?")%l+"</p>"
                        confirm(message,'fanfictiondownloader_no_reading_list_%s'%l, self.gui)
                        
        if prefs['addtolists'] and (add or (prefs['addtolistsonread'] and prefs['addtoreadlists']) ):
            lists = self.get_clean_reading_lists(prefs['send_lists'])
            if len(lists) < 1 :
                message="<p>"+_("You configured FanFictionDownLoader to automatically update \"Send to Device\" Reading Lists, but you don't have any lists set?")+"</p>"
                confirm(message,'fanfictiondownloader_no_send_lists', self.gui)

            for l in lists:
                if l in rl_plugin.get_list_names():
                    #print("good send l:(%s)"%l)
                    rl_plugin.add_books_to_list(l,
                                                #add_book_ids,
                                                book_ids,
                                                display_warnings=False)
                else:
                    if l != '':
                        message="<p>"+_("You configured FanFictionDownLoader to automatically update Reading List '%s', but you don't have a list of that name?")%l+"</p>"
                        confirm(message,'fanfictiondownloader_no_reading_list_%s'%l, self.gui)

    def make_mi_from_book(self,book):
        mi = MetaInformation(book['title'],book['author']) # author is a list.
        if prefs['suppressauthorsort']:
            # otherwise author names will have calibre's sort algs
            # applied automatically.
            mi.author_sort = ' & '.join(book['author'])
        if prefs['suppresstitlesort']:
            # otherwise titles will have calibre's sort algs applied
            # automatically.
            mi.title_sort = book['title']
        mi.set_identifiers({'url':book['url']})
        mi.publisher = book['publisher']
        mi.tags = book['tags']
        #mi.languages = ['en'] # handled in update_metadata so it can check for existing lang.
        mi.pubdate = book['pubdate']
        mi.timestamp = book['timestamp']
        mi.comments = book['comments']
        mi.series = book['series']
        return mi

    # Can't make book a class because it needs to be passed into the
    # bg jobs and only serializable things can be.
    def make_book(self):
        book = {}
        book['title'] = 'Unknown'
        book['author_sort'] = book['author'] = ['Unknown'] # list    
        book['comments'] = '' # note this is the book comments.
        
        book['good'] = True
        book['calibre_id'] = None
        book['begin'] = None
        book['end'] = None
        book['comment'] = '' # note this is a comment on the d/l or update.
        book['url'] = ''
        book['site'] = ''
        book['added'] = False
        book['pubdate'] = None
        return book
    
    def convert_urls_to_books(self, urls):
        books = []
        uniqueurls = set()
        for i, url in enumerate(urls):
            book = self.convert_url_to_book(url)
            if book['url'] in uniqueurls:
                book['good'] = False
                book['comment'] = "Same story already included."
            uniqueurls.add(book['url'])
            book['listorder']=i # BG d/l jobs don't come back in order.
                                # Didn't matter until anthologies & 'marked' successes
            books.append(book)
        return books

    def convert_url_to_book(self, url):
        book = self.make_book()
        # look here for [\d,\d] at end of url, and remove?
        mc = re.match(r"^(?P<url>.*?)(?:\[(?P<begin>\d+)?(?P<comma>[,-])?(?P<end>\d+)?\])?$",url)
        #print("url:(%s) begin:(%s) end:(%s)"%(mc.group('url'),mc.group('begin'),mc.group('end')))
        url = mc.group('url')
        book['begin'] = mc.group('begin')
        book['end'] = mc.group('end')
        if book['begin'] and not mc.group('comma'):
            book['end'] = book['begin']
            
        self.set_book_url_and_comment(book,url)
        return book

    # basic book, plus calibre_id.  Assumed bad until proven
    # otherwise.
    def make_book_id_only(self, idval):
        book = self.make_book()
        book['good'] = False
        book['calibre_id'] = idval
        return book

    def populate_book_from_mi(self,book,mi):
        book['title'] = mi.title
        book['author'] = mi.authors
        book['author_sort'] = mi.author_sort
        if hasattr(mi,'publisher'):
            book['publisher'] = mi.publisher
        if hasattr(mi,'path'):
            book['path'] = mi.path
        if hasattr(mi,'id'):
            book['calibre_id'] = mi.id

    # book data from device.  Assumed bad until proven otherwise.
    def make_book_from_device_row(self, row):
        book = self.make_book()
        mi = self.gui.current_view().model().get_book_display_info(row.row())
        self.populate_book_from_mi(book,mi)
        book['good'] = False
        return book
            
    def populate_book_from_calibre_id(self, book, db=None):
        mi = db.get_metadata(book['calibre_id'], index_is_id=True)
        #book = {}
        book['good'] = True
        self.populate_book_from_mi(book,mi)

        url = self.get_story_url(db,book['calibre_id'])
        self.set_book_url_and_comment(book,url)
        #return book - populated passed in book.

    def set_book_url_and_comment(self,book,url):
        if not url:
            book['comment'] = _("No story URL found.")
            book['good'] = False
            book['icon'] = 'search_delete_saved.png'
            book['status'] = _('Not Found')
        else:
            # get normalized url or None.
            urlsitetuple = adapters.getNormalStoryURLSite(url)
            if urlsitetuple == None:
                book['url'] = url
                book['comment'] = _("URL is not a valid story URL.")
                book['good'] = False
                book['icon']='dialog_error.png'
                book['status'] = _('Bad URL')
            else:
                (book['url'],book['site'])=urlsitetuple
    
    def get_story_url(self, db, book_id=None, path=None):
        if book_id == None:
            identifiers={}
        else:
            identifiers = db.get_identifiers(book_id,index_is_id=True)
        if 'url' in identifiers:
            # identifiers have :->| in url.
            # print("url from ident url:%s"%identifiers['url'].replace('|',':'))
            return identifiers['url'].replace('|',':')
        elif 'uri' in identifiers:
            # identifiers have :->| in uri.
            # print("uri from ident uri:%s"%identifiers['uri'].replace('|',':'))
            return identifiers['uri'].replace('|',':')
        else:
            existingepub = None
            if path == None and db.has_format(book_id,'EPUB',index_is_id=True):
                existingepub = db.format(book_id,'EPUB',index_is_id=True, as_file=True)
                mi = get_metadata(existingepub,'EPUB')
                identifiers = mi.get_identifiers()
                if 'url' in identifiers:
                    # print("url from get_metadata:%s"%identifiers['url'].replace('|',':'))
                    return identifiers['url'].replace('|',':')
                elif 'uri' in identifiers:
                    # identifiers have :->| in uri.
                    # print("uri from ident uri:%s"%identifiers['uri'].replace('|',':'))
                    return identifiers['uri'].replace('|',':')
            elif path and path.lower().endswith('.epub'):
                existingepub = path
                
            ## only epub has URL in it--at least where I can easily find it.
            if existingepub:                
                # look for dc:source first, then scan HTML if lookforurlinhtml
                link = get_dcsource(existingepub)
                if link:
                    # print("url from get_dcsource:%s"%link)
                    return link
                elif prefs['lookforurlinhtml']:
                    link = get_story_url_from_html(existingepub,self.is_good_downloader_url)
                    # print("url from get_story_url_from_html:%s"%link)
                    return link
        return None

    def is_good_downloader_url(self,url):
        return adapters.getNormalStoryURL(url)

    def merge_meta_books(self,existingbook,book_list,fileform):
        book = self.make_book()
        book['author'] = []
        book['tags'] = []
        book['url'] = ''
        book['all_metadata'] = {}
        book['anthology_meta_list'] = {}
        book['comment'] = ''
        book['added'] = True
        book['good'] = True
        book['calibre_id'] = None
        book['series'] = None
    
        serieslist=[]
        
        # copy list top level
        for b in book_list:
            if b['series']:
                serieslist.append(b['series'][:b['series'].index(" [")])
                #print("book series:%s"%serieslist[-1])

            if b['publisher']:
                if 'publisher' not in book:
                    book['publisher']=b['publisher']
                elif book['publisher']!=b['publisher']:
                    book['publisher']=None # if any are different, don't use.
                
            # copy authors & tags.
            for k in ('author','tags'):
                for v in b[k]:
                    if v not in book[k]:
                        book[k].append(v)
                        
            # fill from first of each if not already present:
            for k in ('pubdate', 'timestamp', 'updatedate'):
                if k not in b or not b[k]: # not in this book?  Skip it.
                    continue
                if k not in book or not book[k]: # first is good enough for publisher.
                    book[k]=b[k]

                # Do these even on first to get the all_metadata settings.
                # pubdate should be earliest date.
                if k == 'pubdate' and book[k] >= b[k]:
                    book[k]=b[k]
                    book['all_metadata']['datePublished'] = b['all_metadata']['datePublished']
                # timestamp should be latest date.
                if k == 'timestamp' and book[k] <= b[k]:
                    book[k]=b[k]
                    book['all_metadata']['dateCreated'] = b['all_metadata']['dateCreated']
                # updated should be latest date.
                if k == 'updatedate' and book[k] <= b[k]:
                    book[k]=b[k]
                    book['all_metadata']['dateUpdated'] = b['all_metadata']['dateUpdated']
        
            # copy list all_metadata
            for (k,v) in b['all_metadata'].iteritems():
                #print("merge_meta_books v:%s k:%s"%(v,k))
                if k in ('numChapters','numWords'):
                    if k in b['all_metadata'] and b['all_metadata'][k]:
                        if k not in book['all_metadata']:
                            book['all_metadata'][k] = b['all_metadata'][k]
                        else:
                            # lot of work for a simple add.
                            book['all_metadata'][k] = unicode(int(book['all_metadata'][k].replace(',',''))+int(b['all_metadata'][k].replace(',','')))
                elif k in ('dateUpdated','datePublished','dateCreated',
                           'series','status','title'):
                    pass # handled above, below or skip these for now, not going to do anything with them.
                elif k not in book['all_metadata'] or not book['all_metadata'][k]:
                    book['all_metadata'][k]=v
                elif v:
                    if k == 'description':
                        book['all_metadata'][k]=book['all_metadata'][k]+"\n\n"+v
                    else:
                        book['all_metadata'][k]=book['all_metadata'][k]+", "+v
                        # flag psuedo list element.  Used so numeric
                        # cust cols can convert back to numbers and
                        # add.
                        book['anthology_meta_list'][k]=True

        print("book['url']:%s"%book['url'])
        configuration = get_ffdl_config(book['url'],fileform)
        if existingbook:
            book['title'] = deftitle = existingbook['title']
            book['comments'] = existingbook['comments']
        else:
            book['title'] = deftitle = book_list[0]['title']
            if len(book['author']) > 1:
                book['comments'] = _("Anthology containing:")+"\n" + \
                    "\n".join([ _("%s by %s")%(b['title'],', '.join(b['author'])) for b in book_list ])
            else:
                book['comments'] = _("Anthology containing:")+"\n" + \
                    "\n".join([ b['title'] for b in book_list ])
            # book['all_metadata']['description']
        
            # if all same series, use series for name.  But only if all and not previous named
            if len(serieslist) == len(book_list):
                series = serieslist[0]
                book['title'] = series
                for sr in serieslist:
                    if series != sr:
                        book['title'] = deftitle
                        break
            
            logger.debug("anthology_title_pattern:%s"%configuration.getConfig('anthology_title_pattern'))
            if configuration.getConfig('anthology_title_pattern'):
                tmplt = Template(configuration.getConfig('anthology_title_pattern'))
                book['title'] = tmplt.safe_substitute({'title':book['title']}).encode('utf8')
            else:
                # No setting, do fall back default.  Shouldn't happen,
                # should always have a version in defaults.
                book['title'] = book['title']+_(" Anthology")
        
        book['all_metadata']['title'] = book['title'] # because custom columns are set from all_metadata
        book['all_metadata']['author'] = ", ".join(book['author'])
        book['author_sort']=book['author']
        for v in ['Completed','In-Progress']:
            if v in book['tags']:
                book['tags'].remove(v)
        book['tags'].extend(configuration.getConfigList('anthology_tags'))
        book['all_metadata']['anthology'] = "true"
        
        return book

def split_text_to_urls(urls):
    # remove dups while preserving order.
    dups=set()
    def f(x):
        x=x.strip()
        if x and x not in dups:
            dups.add(x)
            return True
        else:
            return False
    return filter(f,urls.strip().splitlines())

def escapehtml(txt):
    return txt.replace("&","&amp;").replace(">","&gt;").replace("<","&lt;")
        
def pretty_book(d, indent=0, spacer='     '):
    kindent = spacer * indent

    # if isinstance(d, list):
    #     return '\n'.join([(pretty_book(v, indent, spacer)) for v in d])

    if isinstance(d, dict):
        for k in ('password','username'):
            if k in d and d[k]:
                d[k]=_('(was set, removed for security)')
        return '\n'.join(['%s%s:\n%s' % (kindent, k, pretty_book(v, indent + 1, spacer)) 
                          for k, v in d.items()])
    return "%s%s"%(kindent, d)

