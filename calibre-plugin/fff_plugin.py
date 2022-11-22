# -*- coding: utf-8 -*-

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import six
from six.moves import range

__license__   = 'GPL v3'
__copyright__ = '2021, Jim Miller'
__docformat__ = 'restructuredtext en'

from fanficfare.six import ensure_text, string_types, text_type as unicode

# import cProfile

# def do_cprofile(func):
#     def profiled_func(*args, **kwargs):
#         profile = cProfile.Profile()
#         try:
#             profile.enable()
#             result = func(*args, **kwargs)
#             profile.disable()
#             return result
#         finally:
#             profile.print_stats()
#     return profiled_func

import logging
logger = logging.getLogger(__name__)

import os
import re
import sys
import threading
from io import BytesIO
from functools import partial
from datetime import datetime, time
from string import Template
import traceback
from collections import defaultdict

from PyQt5.Qt import (QApplication, QMenu, QTimer, QToolButton)

from calibre.constants import numeric_version as calibre_version

from calibre.ptempfile import PersistentTemporaryFile, PersistentTemporaryDirectory, remove_dir
from calibre.ebooks.metadata import MetaInformation
from calibre.ebooks.metadata.meta import get_metadata as calibre_get_metadata
from calibre.gui2 import error_dialog, info_dialog, question_dialog
from calibre.gui2.dialogs.message_box import ViewLog
from calibre.gui2.dialogs.confirm_delete import confirm
from calibre.utils.config import prefs as calibre_prefs
from calibre.utils.date import local_tz
from calibre.constants import config_dir as calibre_config_dir

# The class that all interface action plugins must inherit from
from calibre.gui2.actions import InterfaceAction

# pulls in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

try:
    # should be present from cal2.3.0 on.
    from calibre.ebooks.covers import generate_cover as cal_generate_cover
    HAS_CALGC=True
except:
    HAS_CALGC=False

from calibre.library.field_metadata import FieldMetadata
field_metadata = FieldMetadata()

from calibre_plugins.fanficfare_plugin.common_utils import (
    set_plugin_icon_resources, get_icon, create_menu_action_unique,
    busy_cursor)

from fanficfare import adapters, exceptions

from fanficfare.epubutils import (
    get_dcsource, get_dcsource_chaptercount, get_story_url_from_epub_html,
    get_story_url_from_zip_html, reset_orig_chapters_epub, get_cover_data)

from fanficfare.geturls import (
    get_urls_from_page, get_urls_from_text,get_urls_from_imap,
    get_urls_from_mime)

from calibre_plugins.fanficfare_plugin.fff_util import (
    get_fff_adapter, get_fff_config, get_fff_personalini,
    get_common_elements)

from calibre_plugins.fanficfare_plugin.config import (
    permitted_values, rejecturllist, STD_COLS_SKIP)

from calibre_plugins.fanficfare_plugin.prefs import (
    prefs,
    SKIP,
    ADDNEW,
    UPDATE,
    UPDATEALWAYS,
    OVERWRITE,
    OVERWRITEALWAYS,
    CALIBREONLY,
    CALIBREONLYSAVECOL,
    SAVE_YES,
    SAVE_NO,
    SAVE_YES_IF_IMG,
    SAVE_YES_UNLESS_IMG)

from calibre_plugins.fanficfare_plugin.dialogs import (
    AddNewDialog, UpdateExistingDialog,
    LoopProgressDialog, UserPassDialog, AboutDialog, CollectURLDialog,
    RejectListDialog, EmailPassDialog,
    save_collisions, question_dialog_all,
    NotGoingToDownload, RejectUrlEntry)

# because calibre immediately transforms html into zip and don't want
# to have an 'if html'.  db.has_format is cool with the case mismatch,
# but if I'm doing it anyway...
formmapping = {
    'epub':'EPUB',
    'mobi':'MOBI',
    'html':'ZIP',
    'txt':'TXT'
    }

imagetypes = {
    'image/jpeg':'jpg',
    'image/png':'png',
    'image/gif':'gif',
    'image/svg+xml':'svg',
    }

PLUGIN_ICONS = ['images/icon.png']

class FanFicFarePlugin(InterfaceAction):

    name = 'FanFicFare'

    # Declare the main action associated with this plugin
    # The keyboard shortcut can be None if you dont want to use a keyboard
    # shortcut. Remember that currently calibre has no central management for
    # keyboard shortcuts, so try to use an unusual/unused shortcut.
    # (text, icon_path, tooltip, keyboard shortcut)
    # icon_path isn't in the zip--icon loaded below.
    action_spec = (_('FanFicFare'), None,
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

        # Set the icon for this interface action.
        # We use our own get_icon, originally inherited from kiwidude,
        # later extended to allow new cal6 theming of plugins.
        # For theme creators, use:
        # FanFicFare/images/icon.png
        # (optionally)
        # FanFicFare/images/icon-for-dark-theme.png
        # FanFicFare/images/icon-for-light-theme.png
        icon = get_icon('images/icon.png')

        self.qaction.setText(_('FanFicFare'))

        # The qaction is automatically created from the action_spec defined
        # above
        self.qaction.setIcon(icon)

        # Call function when plugin triggered.
        self.qaction.triggered.connect(self.plugin_button)

        # Assign our menu to this action
        self.menu = QMenu(self.gui)
        # menu_actions is to keep a live reference to the menu items
        # to prevent GC removing it and so rebuild_menus has a list
        self.menu_actions = []
        self.qaction.setMenu(self.menu)
        self.menus_lock = threading.RLock()
        self.menu.aboutToShow.connect(self.about_to_show_menu)

        self.imap_pass = None

    def initialization_complete(self):
        # otherwise configured hot keys won't work until the menu's
        # been displayed once.
        self.rebuild_menus()
        self.set_popup_mode()
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
                                     *("plugins/fanficfare_macmenuhack.txt".split('/')))
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

        libmime = 'application/calibre+from_library'
        if mime_data.hasFormat(libmime):
            ## mime_data.data(libmime) returns QByteArray.
            ## mime_data.data(libmime).data() returns bytes.
            dropped_ids = [ int(x) for x in ensure_text(mime_data.data(libmime).data()).split() ]
        else:
            urllist = get_urls_from_mime(mime_data)

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
            self.update_dialog(False,dropped_ids)
        elif urllist:
            self.add_dialog(False,"\n".join(urllist))

    def about_to_show_menu(self):
        self.rebuild_menus()

    def library_changed(self, db):
        # We need to reset our menus after switching libraries
        self.rebuild_menus()
        self.set_popup_mode()
        rejecturllist.clear_cache()
        self.imap_pass = None

    def rebuild_menus(self):
        with self.menus_lock:
            def do_user_config(checked):
                self.interface_action_base_plugin.do_user_config(parent=self.gui)
            self.menu.clear()

            for action in self.menu_actions:
                self.gui.keyboard.unregister_shortcut(action.calibre_shortcut_unique_name)
                # starting in calibre 2.10.0, actions are registers at
                # the top gui level for OSX' benefit.
                if calibre_version >= (2,10,0):
                    self.gui.removeAction(action)
            self.menu_actions = []

            self.add_action = self.create_menu_item_ex(self.menu, _('&Download from URLs'), image='plus.png',
                                                       unique_name='Download FanFiction Books from URLs',
                                                       shortcut_name=_('Download FanFiction Books from URLs'),
                                                       triggered=self.add_dialog)

            self.update_action = self.create_menu_item_ex(self.menu, _('&Update Existing FanFiction Books'), image='plusplus.png',
                                                          unique_name='&Update Existing FanFiction Books',
                                                          triggered=self.update_dialog)

            self.get_list_imap_action = self.create_menu_item_ex(self.menu, _('Get Story URLs from &Email'), image='view.png',
                                                                 unique_name='Get Story URLs from IMAP',
                                                                 triggered=self.get_urls_from_imap_menu)
            self.get_list_imap_action.setVisible( bool(prefs['imapserver'] and prefs['imapuser'] and prefs['imapfolder']) )

            self.get_list_url_action = self.create_menu_item_ex(self.menu, _('Get Story URLs from Web Page'), image='view.png',
                                                                unique_name='Get Story URLs from Web Page',
                                                                triggered=self.get_urls_from_page_menu)

            self.get_list_action = self.create_menu_item_ex(self.menu, _('Get Story URLs from Selected Books'),
                                                            unique_name='Get URLs from Selected Books',
                                                            image='bookmarks.png',
                                                            triggered=self.list_story_urls)
            self.menu.addSeparator()
            anth_on = bool(self.get_epubmerge_plugin())
            self.anth_sub_menu = self.menu.addMenu(_('Anthology Options'))
            self.get_anthlist_url_action = self.create_menu_item_ex(self.anth_sub_menu, _('Make Anthology Epub from Web Page'),
                                                                    image='view.png',
                                                                    unique_name='Make FanFiction Anthology Epub from Web Page',
                                                                    shortcut_name=_('Make FanFiction Anthology Epub from Web Page'),
                                                                    triggered=partial(self.get_urls_from_page_menu,anthology=True))

            self.makeanth_action = self.create_menu_item_ex(self.anth_sub_menu, _('&Make Anthology Epub from URLs'),
                                                            image='plusplus.png',
                                                            unique_name='Make FanFiction Anthology Epub from URLs',
                                                            shortcut_name=_('Make FanFiction Anthology Epub from URLs'),
                                                            triggered=partial(self.add_dialog,merge=True) )

            self.updateanth_action = self.create_menu_item_ex(self.anth_sub_menu, _('Update Anthology Epub'),
                                                              image='plusplus.png',
                                                              unique_name='Update FanFiction Anthology Epub',
                                                              shortcut_name=_('Update FanFiction Anthology Epub'),
                                                              triggered=self.update_anthology)

            # Make, but set invisible--that way they still appear in
            # keyboard shortcuts (and can be set/reset) even when not
            # available.  Set actions, not just sub invisible because
            # that also serves to disable them.
            for ac in (self.anth_sub_menu.menuAction(),
                       self.get_anthlist_url_action,
                       self.makeanth_action,
                       self.updateanth_action):
                ac.setVisible(anth_on)

            rl_on = bool('Reading List' in self.gui.iactions and (prefs['addtolists'] or prefs['addtoreadlists']))
            self.rl_sub_menu = self.menu.addMenu(_('Reading List Options'))
            addmenutxt, rmmenutxt = None, None
            if prefs['addtolists'] and prefs['addtoreadlists'] :
                addmenutxt = _('Mark Unread: Add to "To Read" and "Send to Device" Lists')
                if prefs['addtolistsonread']:
                    rmmenutxt = _('Mark Read: Remove from "To Read" and add to "Send to Device" Lists')
                else:
                    rmmenutxt = _('Mark Read: Remove from "To Read" Lists')
            elif prefs['addtolists'] :
                addmenutxt = _('Add to "Send to Device" Lists')
            elif prefs['addtoreadlists']:
                addmenutxt = _('Mark Unread: Add to "To Read" Lists')
                rmmenutxt = _('Mark Read: Remove from "To Read" Lists')

            add_off = not addmenutxt
            if add_off:
                addmenutxt = _('Add to Lists Not Configured')

            self.add_send_action = self.create_menu_item_ex(self.rl_sub_menu, addmenutxt,
                                                            unique_name='Add to "To Read" and "Send to Device" Lists',
                                                            image='plusplus.png',
                                                            triggered=partial(self.update_lists,add=True))
            self.add_send_action.setVisible(rl_on and not add_off)

            rm_off = not rmmenutxt
            if rm_off:
                rmmenutxt = _('Remove from Lists Not Configured')
            self.add_remove_action = self.create_menu_item_ex(self.rl_sub_menu, rmmenutxt,
                                                              unique_name='Remove from "To Read" and add to "Send to Device" Lists',
                                                              image='minusminus.png',
                                                              triggered=partial(self.update_lists,add=False))
            self.add_remove_action.setVisible(rl_on and not rm_off)
            self.rl_sub_menu.menuAction().setVisible(rl_on)


            self.modes_sub_menu = self.menu.addMenu(_('Actions by Update Modes'))

            def add_mode_menu(parent_menu,icon_file,unique_name,translated_name,mode,triggered):
                self.create_menu_item_ex(parent_menu, mode,
                                         image=icon_file,
                                         unique_name='%s - %s'%(unique_name,save_collisions[mode]),
                                         # mode is already translated
                                         shortcut_name='%s - %s'%(translated_name,mode),
                                         triggered=partial(triggered,
                                                           extraoptions={'collision':mode}) )

            def add_action_menu(menu_name,
                                icon_file,
                                unique_name,
                                translated_name,
                                mode_list,
                                triggered):
                sub_menu = self.modes_sub_menu.addMenu(menu_name)
                sub_menu.setIcon(get_icon(icon_file))
                for mode in mode_list:
                    add_mode_menu(sub_menu, icon_file, unique_name, translated_name, mode, triggered)

            add_action_menu(_('&Download from URLs'),
                            'plus.png',
                            'Download FanFiction Books from URLs',
                            _('Download FanFiction Books from URLs'),
                            (SKIP, ADDNEW, UPDATE, UPDATEALWAYS, OVERWRITE,
                             OVERWRITEALWAYS, CALIBREONLY, CALIBREONLYSAVECOL),
                            self.add_dialog)

            add_action_menu(_('&Update Existing FanFiction Books'),
                            'plusplus.png',
                            'Update Existing FanFiction Books',
                            _('Update Existing FanFiction Books'),
                            (UPDATE, UPDATEALWAYS, OVERWRITE, OVERWRITEALWAYS,
                             CALIBREONLY, CALIBREONLYSAVECOL),
                            self.update_dialog)

            add_action_menu(_('Get Story URLs from &Email'),
                            'view.png',
                            'Get FanFiction Story URLs from Email',
                              _('Get FanFiction Story URLs from Email'),
                            (SKIP, ADDNEW, UPDATE, UPDATEALWAYS, OVERWRITE,
                             OVERWRITEALWAYS, CALIBREONLY, CALIBREONLYSAVECOL),
                            self.get_urls_from_imap_menu)

            add_action_menu(_('Get Story URLs from Web Page'),
                            'view.png',
                            'Get FanFiction Story URLs from Web Page',
                            _('Get FanFiction Story URLs from Web Page'),
                            (SKIP, ADDNEW, UPDATE, UPDATEALWAYS, OVERWRITE,
                             OVERWRITEALWAYS, CALIBREONLY, CALIBREONLYSAVECOL),
                            self.get_urls_from_page_menu)

            add_action_menu(_('Update Anthology Epub'),
                            'plusplus.png',
                            'Update FanFiction Anthology Epub',
                            _('Update FanFiction Anthology Epub'),
                            (UPDATE, UPDATEALWAYS, OVERWRITEALWAYS),
                            self.update_anthology)

            self.menu.addSeparator()
            self.get_list_action = self.create_menu_item_ex(self.menu, _('Remove "New" Chapter Marks from Selected books'),
                                                            unique_name='Remove "(new)" chapter marks created by personal.ini <i>mark_new_chapters</i> setting.',
                                                            image='edit-undo.png',
                                                            triggered=self.unnew_books)

            self.reject_list_action = self.create_menu_item_ex(self.menu, _('Reject Selected Books'),
                                                               unique_name='Reject Selected Books', image='rotate-right.png',
                                                               triggered=self.reject_list_urls)
            # self.menu.addSeparator()

            # print("platform.system():%s"%platform.system())
            # print("platform.mac_ver()[0]:%s"%platform.mac_ver()[0])
            if not self.check_macmenuhack(): # not platform.mac_ver()[0]: # Some macs crash on these menu items for unknown reasons.
                # self.menu.addSeparator()
                self.config_action = self.create_menu_item_ex(self.menu, _('&Configure FanFicFare'),
                                                              image= 'config.png',
                                                              unique_name='Configure FanFicFare',
                                                              shortcut_name=_('Configure FanFicFare'),
                                                              triggered=do_user_config)

                self.about_action = self.create_menu_item_ex(self.menu, _('About FanFicFare'),
                                                             image= 'images/icon.png',
                                                             unique_name='About FanFicFare',
                                                             shortcut_name=_('About FanFicFare'),
                                                             triggered=self.about)

            self.gui.keyboard.finalize()

    def about(self,checked):
        # Get the about text from a file inside the plugin zip file
        # The get_resources function is a builtin function defined for all your
        # plugin code. It loads files from the plugin zip file. It returns
        # the bytes from the specified file.
        #
        # Note that if you are loading more than one file, for performance, you
        # should pass a list of names to get_resources. In this case,
        # get_resources will return a dictionary mapping names to bytes. Names that
        # are not found in the zip file will not be in the returned dictionary.

        text = get_resources('about.html').decode('utf-8')
        AboutDialog(self.gui,self.qaction.icon(),self.version + text).exec_()

    def create_menu_item_ex(self, parent_menu, menu_text, image=None, tooltip=None,
                           shortcut=None, triggered=None, is_checked=None, shortcut_name=None,
                           unique_name=None):
        ac = create_menu_action_unique(self, parent_menu, menu_text, image, tooltip,
                                       shortcut, triggered, is_checked, shortcut_name, unique_name)
        self.menu_actions.append(ac)
        return ac

    def is_library_view(self):
        # 0 = library, 1 = main, 2 = card_a, 3 = card_b
        return self.gui.stack.currentIndex() == 0

    def plugin_button(self):
        if self.is_library_view() and \
                len(self.gui.library_view.get_selected_ids()) > 0 and \
                prefs['updatedefault']:
            self.update_dialog(False)
        else:
            self.add_dialog(False)

    def set_popup_mode(self):
        if prefs['button_instantpopup']:
            self.popup_type = QToolButton.InstantPopup
        else:
            self.popup_type = QToolButton.MenuButtonPopup
        for bar in self.gui.bars_manager.bars:
            w = bar.widgetForAction(self.qaction)
            if w is not None:
                w.setPopupMode(self.popup_type)
                w.update()
        return

    def get_epubmerge_plugin(self):
        if 'EpubMerge' in self.gui.iactions and self.gui.iactions['EpubMerge'].interface_action_base_plugin.version >= (1,3,1):
            return self.gui.iactions['EpubMerge']

    def update_lists(self,checked,add=True):
        if prefs['addtolists'] or prefs['addtoreadlists']:
            if not self.is_library_view():
                self.gui.status_bar.show_message(_('Cannot Update Reading Lists from Device View'), 3000)
                return

            if len(self.gui.library_view.get_selected_ids()) == 0:
                self.gui.status_bar.show_message(_('No Selected Books to Update Reading Lists'), 3000)
                return

            self.update_reading_lists(self.gui.library_view.get_selected_ids(),add)
            if not add and prefs['autounnew']:
                self.unnew_books(False)

    def check_valid_collision(self,extraoptions):
        collision = extraoptions.get('collision',None)
        if collision == CALIBREONLYSAVECOL and not prefs['savemetacol']:
            s=_('FanFicFare Saved Metadata Column not configured.')
            info_dialog(self.gui, s, s, show=True, show_copy_button=False)
            extraoptions['collision'] = CALIBREONLY
            return

        if collision in (UPDATE,UPDATEALWAYS) and prefs['fileform'] != 'epub':
            s=_('Cannot update non-epub format.')
            info_dialog(self.gui, s, s, show=True, show_copy_button=False)
            extraoptions['collision'] = OVERWRITE
            return

    def get_urls_from_imap_menu(self,checked,extraoptions={}):
        if not (prefs['imapserver'] and prefs['imapuser'] and prefs['imapfolder']):
            s=_('FanFicFare Email Settings are not configured.')
            info_dialog(self.gui, s, s, show=True, show_copy_button=False)
            return
        self.check_valid_collision(extraoptions)

        imap_pass = None
        if prefs['imappass']:
            imap_pass = prefs['imappass']
        elif self.imap_pass is not None:
            imap_pass = self.imap_pass

        if not imap_pass:
            d = EmailPassDialog(self.gui,prefs['imapuser'])
            d.exec_()
            if not d.status:
                return
            imap_pass = d.get_pass()
            if prefs['imapsessionpass']:
                self.imap_pass = imap_pass

        with busy_cursor():
            self.gui.status_bar.show_message(_('Fetching Story URLs from Email...'))
            url_list = get_urls_from_imap(prefs['imapserver'],
                                          prefs['imapuser'],
                                          imap_pass,
                                          prefs['imapfolder'],
                                          prefs['imapmarkread'],)

            ## reject will now be redundant with reject check inside
            ## prep_downloads because of change-able story URLs.
            ## Keeping here to because it's the far more common case.
            reject_list=set()
            if prefs['auto_reject_from_email']:
                # need to normalize for reject list.
                reject_list = set([x for x in url_list if rejecturllist.check(x)])
            url_list = url_list - reject_list

            ## feature for update-only - check url_list with
            ## self.do_id_search(url)
            notupdate_list = set()
            if prefs['update_existing_only_from_email']:
                notupdate_list = set([x for x in url_list if not self.do_id_search(adapters.getNormalStoryURL(x))])
            url_list = url_list - notupdate_list

            self.gui.status_bar.show_message(_('No Valid Story URLs Found in Unread Emails.'),3000)

        if prefs['download_from_email_immediately']:
            ## do imap fetch w/o GUI elements
            if url_list:
                self.prep_downloads({
                        'fileform': prefs['fileform'],
                        # save_collisions==convert from save value to local lang value
                        'collision': extraoptions.get('collision',save_collisions[prefs['collision']]),
                        'updatemeta': prefs['updatemeta'],
                        'bgmeta': False,
                        'smarten_punctuation':prefs['smarten_punctuation'],
                        'do_wordcount':prefs['do_wordcount'],
                        'add_tag':prefs['imaptags'],
                        },"\n".join(url_list))
            else:
                self.gui.status_bar.show_message(_('Finished Fetching Story URLs from Email.'),3000)

        else:
            if url_list:
                if prefs['imaptags']:
                    message="<p>"+_("Tag(s) <b><i>%s</i></b> will be added to all stories downloaded in the next dialog, including any story URLs you add manually.")%prefs['imaptags']+"</p>"
                    confirm(message,'fff_add_imaptags', self.gui, show_cancel_button=False, title=_("Warning"))
                extraoptions['add_tag']=prefs['imaptags']
                self.add_dialog(False,"\n".join(url_list),
                                merge=False,
                                extraoptions=extraoptions)
            else:
                msg = _('No Valid Story URLs Found in Unread Emails.')
                if reject_list:
                    msg = msg + '<p>'+(_('(%d Story URLs Skipped, on Rejected URL List)')%len(reject_list))+'</p>'
                if notupdate_list:
                    msg = msg + '<p>'+(_("(%d Story URLs Skipped, no Existing Book in Library)")%len(notupdate_list))+'</p>'
                info_dialog(self.gui, _('Get Story URLs from Email'),
                            msg,
                            show=True,
                            show_copy_button=False)

    def get_urls_from_page_menu(self,checked,anthology=False,extraoptions={}):

        self.check_valid_collision(extraoptions)
        urltxt = ""
        if prefs['urlsfromclip']:
            try:
                urltxt = self.get_urls_clip(storyurls=False)[0]
            except:
                urltxt = ""

        d = CollectURLDialog(self.gui,_("Get Story URLs from Web Page"),urltxt,
                             anthology=anthology or ('collision' not in extraoptions and self.get_epubmerge_plugin()),
                             indiv=not anthology)
        d.exec_()
        if not d.status:
            return
        url = u"%s"%d.url.text()

        if (anthology or d.anthology) and prefs['checkforseriesurlid']:
            identicalbooks = self.do_id_search(url)
            if ( len(identicalbooks) > 0 and
                         question_dialog(self.gui, _('Skip Story?'),'''
                                                         <h3>%s</h3>
                                                         <p>%s</p>
                                                         <p>%s</p>
                                                         <p>%s</p>
                                                         '''%(_('Skip Anthology Story?'),
                                                              _('You already have an Anthology Ebook in your library for series "<b><a href="%s">%s</a></b>".')%(url,url),
                                                              _("Click '<b>Yes</b>' to Skip."),
                                                              _("Click '<b>No</b>' to download anyway.")),
                                             show_copy_button=False)):
                self.do_mark_series_anthologies(identicalbooks)
                return

        with busy_cursor():
            self.gui.status_bar.show_message(_('Fetching Story URLs from Page...'))

            frompage = self.get_urls_from_page(url)
            url_list = frompage.get('urllist',[])

            self.gui.status_bar.show_message(_('Finished Fetching Story URLs from Page.'),3000)

        if url_list:
            # make a copy before adding to avoid changing passed param
            eo = dict(extraoptions)
            eo.update({'anthology_url':url,
                       'frompage':frompage})
            self.add_dialog(False,"\n".join(url_list),
                            merge=d.anthology,
                            extraoptions=eo)
        else:
            info_dialog(self.gui, _('List of Story URLs'),
                        _('No Valid Story URLs found on given page.'),
                        show=True,
                        show_copy_button=False)

    def get_urls_from_page(self,url):
        ## now returns a {} with at least 'urllist'
        logger.debug("get_urls_from_page URL:%s"%url)
        configuration = get_fff_config(url)
        return get_urls_from_page(url,configuration)

    def list_story_urls(self,checked):
        '''Get list of URLs from existing books.'''
        if not self.gui.current_view().selectionModel().selectedRows() :
            self.gui.status_bar.show_message(_('No Selected Books to Get URLs From'),
                                             3000)
            return

        if self.is_library_view():
            book_list = [ self.make_book_id_only(x) for x in
                          self.gui.library_view.get_selected_ids() ]

        else: # device view, get from epubs on device.
            book_list = [ self.make_book_from_device_row(x) for x in
                          self.gui.current_view().selectionModel().selectedRows() ]

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
            book['status']=_('Bad')
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

    def unnew_books(self,checked):
        '''Get list of URLs from existing books.'''
        if not self.is_library_view():
            self.gui.status_bar.show_message(_('Can only UnNew books in library'),
                                             3000)
            return

        if not self.gui.current_view().selectionModel().selectedRows() :
            self.gui.status_bar.show_message(_('No Selected Books to Get URLs From'),
                                             3000)
            return

        book_list = [ self.make_book_id_only(x) for x in
                      self.gui.library_view.get_selected_ids() ]

        tdir = PersistentTemporaryDirectory(prefix='fanficfare_')
        LoopProgressDialog(self.gui,
                           book_list,
                           partial(self.get_unnew_books_loop, db=self.gui.current_db, tdir=tdir),
                           partial(self.get_unnew_books_finish, tdir=tdir),
                           init_label=_("UnNewing books..."),
                           win_title=_("UnNew Books"),
                           status_prefix=_("Books UnNewed"))

    def get_unnew_books_loop(self,book,db=None,tdir=None):

        book['changed']=False
        if book['calibre_id'] and db.has_format(book['calibre_id'],'EPUB',index_is_id=True) and self.get_story_url(db,book['calibre_id']):
            tmp = PersistentTemporaryFile(prefix='%s-'%book['calibre_id'],
                                          suffix='.epub',
                                          dir=tdir)
            db.copy_format_to(book['calibre_id'],'EPUB',tmp,index_is_id=True)

            unnewtmp = PersistentTemporaryFile(prefix='unnew-%s-'%book['calibre_id'],
                                               suffix='.epub',
                                               dir=tdir)
            book['changed']=reset_orig_chapters_epub(tmp,unnewtmp)
            if book['changed']:
                try:
                    # Remove before adding so the previous version is in the
                    # OS Trash (on Windows, at least)
                    db.remove_format(book['calibre_id'],'EPUB', index_is_id=True)
                except:
                    pass
                db.add_format_with_hooks(book['calibre_id'],
                                         'EPUB',
                                         unnewtmp,
                                         index_is_id=True)
                if prefs['deleteotherforms']:
                    fmts = db.formats(book['calibre_id'], index_is_id=True).split(',')
                    for fmt in fmts:
                        if fmt.lower() != formmapping['epub'].lower():
                            logger.debug("deleteotherforms remove f:"+fmt)
                            db.remove_format(book['calibre_id'], fmt, index_is_id=True)#, notify=False
                elif prefs['autoconvert']:
                    ## 'Convert Book'.auto_convert_auto_add doesn't convert if
                    ## the format is already there.
                    fmt = calibre_prefs['output_format']
                    # delete if there, but not if the format we just made.
                    if fmt.lower() != 'epub' and db.has_format(book['calibre_id'],fmt,index_is_id=True):
                        logger.debug("autoconvert remove f:"+fmt)
                        db.remove_format(book['calibre_id'], fmt, index_is_id=True)#, notify=False

    def get_unnew_books_finish(self, book_list, tdir=None):
        remove_dir(tdir)
        if prefs['autoconvert']:
            changed_ids = [ x['calibre_id'] for x in book_list if x['changed'] ]
            if changed_ids:
                logger.debug(_('Starting auto conversion of %d books.')%(len(changed_ids)))
                self.gui.status_bar.show_message(_('Starting auto conversion of %d books.')%(len(changed_ids)), 3000)
                self.gui.iactions['Convert Books'].auto_convert_auto_add(changed_ids)

    def reject_list_urls(self,checked):
        if self.is_library_view():
            book_list = [ self.make_book_id_only(x) for x in
                          self.gui.library_view.get_selected_ids() ]

        else: # device view, get from epubs on device.
            view = self.gui.current_view()
            rows = view.selectionModel().selectedRows()
            #paths = view.model().paths(rows)
            book_list = [ self.make_book_from_device_row(x) for x in rows ]

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
            message="<p>"+_("Rejecting FanFicFare URLs: None of the books selected have FanFiction URLs.")+"</p><p>"+_("Proceed to Remove?")+"</p>"
            if confirm(message,'fff_reject_non_fanfiction', self.gui):
                self.gui.iactions['Remove Books'].delete_books()

    def add_dialog(self,
                   checked,
                   url_list_text=None,
                   merge=False,
                   extraoptions={}):
        '''
        Both new individual stories and new anthologies are created here.
        Expected extraoptions entries: anthology_url, add_tag, frompage
        '''
        # logger.debug("extraoptions['anthology_url']:%s"%extraoptions.get('anthology_url','NOT FOUND'))
        self.check_valid_collision(extraoptions)

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
                                        extraoptions=extraoptions)

    def update_anthology(self,checked,extraoptions={}):
        self.check_valid_collision(extraoptions)
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
        class NotAnthologyException(Exception):
            def __init__(self):
                return

        try:
            with busy_cursor():
                self.gui.status_bar.show_message(_('Fetching Story URLs for Series...'))
                book_id = self.gui.library_view.get_selected_ids()[0]
                mergebook = self.make_book_id_only(book_id)
                self.populate_book_from_calibre_id(mergebook, db)

                if not db.has_format(book_id,'EPUB',index_is_id=True):
                    self.gui.status_bar.show_message(_('Can only Update Epub Anthologies'), 3000)
                    return

                tdir = PersistentTemporaryDirectory(prefix='fff_anthology_')
                logger.debug("tdir:\n%s"%tdir)

                bookepubio = BytesIO(db.format(book_id,'EPUB',index_is_id=True))

                filenames = self.get_epubmerge_plugin().do_unmerge(bookepubio,tdir)
                urlmapfile = {}
                url_list = []
                for f in filenames:
                    url = adapters.getNormalStoryURL(get_dcsource(f))
                    if url:
                        urlmapfile[url]=f
                        url_list.append(url)

                if not filenames or len(filenames) != len (url_list):
                    raise NotAnthologyException()

                # get list from identifiers:url/uri if present, but only if
                # it's *not* a valid story URL.
                mergeurl = self.get_story_url(db,book_id)
                frompage = {}
                if mergeurl and not self.is_good_downloader_url(mergeurl):
                    frompage = self.get_urls_from_page(mergeurl)
                    url_list = [ adapters.getNormalStoryURL(url) for url in frompage.get('urllist',[]) ]
                frompage['urllist']=url_list

                url_list_text = "\n".join(url_list)

                self.gui.status_bar.show_message(_('Finished Fetching Story URLs for Series.'),3000)
        except NotAnthologyException:
            # using an exception purely to get outside 'with busy_cursor:'
            info_dialog(self.gui, _("Cannot Update Anthology"),
                        "<p>"+_("Cannot Update Anthology")+"</p><p>"+_("Book isn't an FanFicFare Anthology or contains book(s) without valid Story URLs."),
                        show=True,
                        show_copy_button=False)
            remove_dir(tdir)
            return


        #print("urlmapfile:%s"%urlmapfile)

        # AddNewDialog collects URLs, format and presents buttons.
        # add_new_dialog is modeless and reused, both for new stories
        # and anthologies, and for updating existing anthologies.
        # make a copy before adding to avoid changing passed param
        eo = dict(extraoptions)
        eo.update({'anthology_url':mergebook['url'],
                   'frompage':frompage,
                   'tdir':tdir,
                   'mergebook':mergebook})
        self.add_new_dialog.show_dialog(url_list_text,
                                        self.prep_anthology_downloads,
                                        show=False,
                                        merge=True,
                                        newmerge=False,
                                        extrapayload=urlmapfile,
                                        extraoptions=eo)
        # Need to use AddNewDialog modal here because it's an update
        # of an existing book.  Don't want the user deleting it or
        # switching libraries on us.
        self.add_new_dialog.exec_()


    def prep_anthology_downloads(self, options, update_books,
                                 merge=False, urlmapfile=None):
        # new question_cache each time we start prep'ing downloads.
        self.question_cache = {}
        if isinstance(update_books, string_types):
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

    def update_dialog(self,checked,id_list=None,extraoptions={}):
        if not self.is_library_view():
            self.gui.status_bar.show_message(_('Cannot Update Books from Device View'), 3000)
            return

        if not id_list:
            id_list = self.gui.library_view.get_selected_ids()

        if len(id_list) == 0:
            self.gui.status_bar.show_message(_('No Selected Books to Update'), 3000)
            return

        self.check_valid_collision(extraoptions)
        #print("update_dialog()")

        db = self.gui.current_db
        books = [ self.make_book_id_only(x) for x in id_list ]

        for j, book in enumerate(books):
            book['listorder'] = j

        LoopProgressDialog(self.gui,
                           books,
                           partial(self.populate_book_from_calibre_id, db=self.gui.current_db),
                           partial(self.update_dialog_finish,extraoptions=extraoptions),
                           init_label=_("Collecting stories for update..."),
                           win_title=_("Get stories for updates"),
                           status_prefix=_("URL retrieved"))

        #books = self.convert_calibre_ids_to_books(db, book_ids)
        #print("update books:%s"%books)

    def update_dialog_finish(self,book_list,extraoptions={}):
        '''Present list to update and head to prep when done.'''

        d = UpdateExistingDialog(self.gui,
                                 _('Update Existing List'),
                                 prefs,
                                 self.qaction.icon(),
                                 book_list,
                                 extraoptions=extraoptions,
                                 )
        d.exec_()
        if d.result() != d.Accepted:
            return

        update_books = d.get_books()

        #print("update_books:%s"%update_books)
        #print("options:%s"%d.get_fff_options())
        # only if there's some good ones.
        if any(x['good'] for x in update_books):
            options = d.get_fff_options()
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

    def do_id_search(self,url):
        # older idents can be uri vs url and have | instead of : after
        # http, plus many sites are now switching to https.
        regexp = r'identifiers:"~ur(i|l):~^https?%s$"'%(re.sub(r'^https?','',re.escape(url)))
        # logger.debug(regexp)
        ## Added Jan 2021, adapter_fanfictionnet is keeping title in
        ## URL now, search with and without url title.  'URL changed'
        ## check will still trigger if existing URL has a *different*
        ## url title.
        ## Changed Sep 2021, adapter_fanfictionnet is keeping title in
        ## storyURL now, but if the story title changes, the Jan
        ## solution wasn't finding the existing story.
        if "\.fanfiction\.net" in regexp:
            regexp = re.sub(r"^(?P<keep>.*net/s/\d+/\d+/)(?P<urltitle>[^\$]*)?",
                            r"\g<keep>(.*)",regexp)
        # logger.debug(regexp)
        retval = self.gui.current_db.search_getting_ids(regexp,None,use_virtual_library=False)
        # logger.debug(retval)
        return retval

    def prep_downloads(self, options, books, merge=False, extrapayload=None):
        '''Fetch metadata for stories from servers, launch BG job when done.'''
        # new question_cache each time we start prep'ing downloads.
        self.question_cache = {}
        if isinstance(books, string_types):
            url_list = split_text_to_urls(books)
            books = self.convert_urls_to_books(url_list)

        ## for tweak_fg_sleep
        d = options['site_counts'] = defaultdict(int)
        for b in books:
            d[b['site']] += 1

        options['version'] = self.version
        logger.debug(self.version)
        options['personal.ini'] = get_fff_personalini()
        options['savemetacol'] = prefs['savemetacol']

        #print("prep_downloads:%s"%books)

        if 'tdir' not in options: # if merging an anthology, there's alread a tdir.
            # create and pass temp dir.
            tdir = PersistentTemporaryDirectory(prefix='fanficfare_')
            options['tdir']=tdir

        if any(x['good'] for x in books):
            if options['bgmeta']:
                status_bar=_('Start queuing downloading for %s stories.')%len(books)
                init_label=_("Queuing download for stories...")
                win_title=_("Queuing download for stories")
                status_prefix=_("Queued download for")
            else:
                status_bar=_('Started fetching metadata for %s stories.')%len(books)
                init_label=_("Fetching metadata for stories...")
                win_title=_("Downloading metadata for stories")
                status_prefix=_("Fetched metadata for")

            self.gui.status_bar.show_message(status_bar, 3000)
            LoopProgressDialog(self.gui,
                               books,
                               partial(self.prep_download_loop, options = options, merge=merge),
                               partial(self.start_download_job, options = options, merge=merge),
                               init_label=init_label,
                               win_title=win_title,
                               status_prefix=status_prefix)
        else:
            self.gui.status_bar.show_message(_('No valid story URLs entered.'), 3000)
        # LoopProgressDialog calls prep_download_loop for each 'good' story,
        # prep_download_loop updates book object for each with metadata from site,
        # LoopProgressDialog calls start_download_job at the end which goes
        # into the BG, or shows list if no 'good' books.

    def reject_url(self,merge,book):
        url = book['url']
        if not merge and rejecturllist.check(url): # skip reject list when merging.
            rejnote = rejecturllist.get_full_note(url)
            if prefs['reject_always'] or \
                    question_dialog_all(self.gui,
                                        _('Reject URL?'),'''
                                          <h3>%s</h3>
                                          <p>%s</p>
                                          <p>"<b>%s</b>"</p>
                                          <p>%s</p>
                                          <p>%s</p>'''%(_('Reject URL?'),
                                                        _('<b>%s</b> is on your Reject URL list:')%url,
                                                        rejnote,
                                                        _("Click '<b>Yes</b>' to Reject."),
                                                        _("Click '<b>No</b>' to download anyway.")),
                                        show_copy_button=False,
                                        question_name='reject_url',
                                        question_cache=self.question_cache):
                book['comment'] = _("Story on Reject URLs list (%s).")%rejnote
                book['good']=False
                book['icon']='rotate-right.png'
                book['status'] = _('Rejected')
                return True
            else:
                if question_dialog_all(self.gui,
                                       _('Remove Reject URL?'),'''
                                         <h3>%s</h3>
                                         <p>%s</p>
                                         <p>"<b>%s</b>"</p>
                                         <p>%s</p>
                                         <p>%s</p>'''%(_("Remove URL from Reject List?"),
                                                       _('<b>%s</b> is on your Reject URL list:')%url,
                                                       rejnote,
                                                       _("Click '<b>Yes</b>' to remove it from the list,"),
                                                       _("Click '<b>No</b>' to leave it on the list.")),
                                       show_copy_button=False,
                                       question_name='remove_reject_url',
                                       question_cache=self.question_cache):
                    rejecturllist.remove(url)
        return False

    def get_story_metadata_only(self,adapter):
        url = adapter.url
        ## three tries, that's enough if both user/pass & is_adult needed,
        ## or a couple tries of one or the other
        for x in range(0,2):
            try:
                adapter.getStoryMetadataOnly(get_cover=False)
            except exceptions.FailedToLogin as f:
                logger.warn("Login Failed, Need Username/Password.")
                userpass = UserPassDialog(self.gui,url,f)
                userpass.exec_() # exec_ will make it act modal
                if userpass.status:
                    adapter.username = userpass.user.text()
                    adapter.password = userpass.passwd.text()

            except exceptions.AdultCheckRequired:
                if question_dialog_all(self.gui, _('Are You an Adult?'), '<p>'+
                                       _("%s requires that you be an adult.  Please confirm you are an adult in your locale:")%url,
                                       show_copy_button=False,
                                       question_name='is_adult',
                                       question_cache=self.question_cache):
                    adapter.is_adult=True

        # let other exceptions percolate up.
        return adapter.getStoryMetadataOnly(get_cover=False)

    # @do_cprofile
    def prep_download_loop(self,book,
                           options={'fileform':'epub',
                                    'collision':ADDNEW,
                                    'updatemeta':True,
                                    'bgmeta':False},
                           merge=False):
        '''
        Update passed in book dict with metadata from website and
        necessary data.  To be called from LoopProgressDialog
        'loop'.  Also pops dialogs for is adult, user/pass.
        '''

        url = book['url']
        # logger.debug("prep_download_loop url:%s"%url)
        mi = None

        # The current database shown in the GUI
        # db is an instance of the class LibraryDatabase2 from database.py
        # This class has many, many methods that allow you to do a lot of
        # things.
        db = self.gui.current_db

        fileform  = options['fileform']
        collision = book['collision'] = options['collision']
        updatemeta= options['updatemeta']
        bgmeta= options['bgmeta']

        ## Check reject list.  Redundant with below for when story URL
        ## changes, but also kept here to avoid network hit in most
        ## common case where given url is story url.
        if self.reject_url(merge,book):
            return

        # Dialogs should prevent this case now.
        if collision in (UPDATE,UPDATEALWAYS) and fileform != 'epub':
            raise NotGoingToDownload(_("Cannot update non-epub format."))

        if not book['good']:
            # book has already been flagged bad for whatever reason.
            return

        adapter = get_fff_adapter(url,fileform)
        ## chapter range for title_chapter_range_pattern
        adapter.setChaptersRange(book['begin'],book['end'])

        ## save and share caches and cookiejar between all downloads.
        configuration = adapter.get_configuration()
        ## browser cache before basic to avoid incidentally reloading
        if configuration.getConfig('use_browser_cache'):
            if 'browser_cache' in options:
                configuration.set_browser_cache(options['browser_cache'])
            else:
                options['browser_cache'] = configuration.get_browser_cache()
        if 'basic_cache' in options:
            configuration.set_basic_cache(options['basic_cache'])
        else:
            options['basic_cache'] = configuration.get_basic_cache()
        if 'cookiejar' in options:
            configuration.set_cookiejar(options['cookiejar'])
        else:
            options['cookiejar'] = configuration.get_cookiejar()

        if collision in (CALIBREONLY, CALIBREONLYSAVECOL):
            ## Getting metadata from configured column.
            custom_columns = self.gui.library_view.model().custom_columns
            if ( collision in (CALIBREONLYSAVECOL) and
                 prefs['savemetacol'] != '' and
                 prefs['savemetacol'] in custom_columns ):

                savedmeta_book_id = book['calibre_id']
                # won't have calibre_id if update by URL vs book.
                if not savedmeta_book_id:
                    identicalbooks = self.do_id_search(url)
                    if len(identicalbooks) == 1:
                        savedmeta_book_id = identicalbooks.pop()

                if savedmeta_book_id:
                    label = custom_columns[prefs['savemetacol']]['label']
                    savedmetadata = db.get_custom(savedmeta_book_id, label=label, index_is_id=True)
                else:
                    savedmetadata = None

                if savedmetadata:
                    # sets flag inside story so getStoryMetadataOnly won't hit server.
                    adapter.setStoryMetadata(savedmetadata)

            # let other exceptions percolate up.
            # bgmeta doesn't work with CALIBREONLY.
            story = self.get_story_metadata_only(adapter)
            bgmeta = False
        else:
            if not bgmeta:
                # reduce foreground sleep time for configured sites when few books.
                if adapter.getConfig('tweak_fg_sleep'):
                    minslp = float(adapter.getConfig('min_fg_sleep'))
                    maxslp = float(adapter.getConfig('max_fg_sleep'))
                    dwnlds = float(adapter.getConfig('max_fg_sleep_at_downloads'))
                    m = (maxslp-minslp) / (dwnlds-1)
                    b = minslp - m
                    slp = min(maxslp,m*float(options['site_counts'][book['site']])+b)
                    # logger.debug("tweak_fg_sleep count:%s"%options['site_counts'][book['site']])
                    # logger.debug("m:%s b:%s = %s"%(m,b,slp))
                    # logger.debug("tweak_fg_sleep: Set FG sleep override time %s"%slp)
                    configuration.set_sleep_override(slp)

                story = self.get_story_metadata_only(adapter)
                book['title'] = story.getMetadata('title')
                book['author'] = [story.getMetadata('author')]
                url = book['url'] = story.getMetadata('storyUrl', removeallentities=True)

            ## Check reject list.  Redundant with above for when story
            ## URL changes, but also kept above to avoid network hit
            ## in most common case where given url is story url.
            if self.reject_url(merge,book):
                return

            ## Do a second dup URL in download check here, same
            ## reasons as reject_url()
            if 'uniqueurls' not in options:
                options['uniqueurls'] = set()
            ## add begin/end to allow for same story split into ranges
            book['uniqueurl']="%s[%s-%s]"%(book['url'],book['begin'],book['end'])
            if book['uniqueurl'] in options['uniqueurls']:
                book['good'] = False
                book['comment'] = _("Same story already included.")
                book['status']=_('Skipped')
            else:
                options['uniqueurls'].add(book['uniqueurl'])

        # logger.debug("series:%s"%story.getMetadata('series'))
        # logger.debug("seriesUrl:%s"%story.getMetadata('seriesUrl'))
        # logger.debug("search seriesUrl:%s"%self.do_id_search(story.getMetadata('seriesUrl')))
        if not bgmeta:
            series = story.getMetadata('series')
            if not merge and series and prefs['checkforseriesurlid']:
                # try to find *series anthology* by *seriesUrl* identifier url or uri first.
                identicalbooks = self.do_id_search(story.getMetadata('seriesUrl'))
                # print("identicalbooks:%s"%identicalbooks)
                if len(identicalbooks) > 0 and \
                        (prefs['auto_reject_seriesurlid'] or
                         question_dialog_all(self.gui, _('Skip Story?'),'''
                                                         <h3>%s</h3>
                                                         <p>%s</p>
                                                         <p>%s</p>
                                                         <p>%s</p>
                                                         '''%(_('Skip Anthology Story?'),
                                                              _('"<b>%s</b>" is in series "<b><a href="%s">%s</a></b>" that you have an anthology book for.')%(story.getMetadata('title'),story.getMetadata('seriesUrl'),series[:series.index(' [')]),
                                                              _("Click '<b>Yes</b>' to Skip."),
                                                              _("Click '<b>No</b>' to download anyway.")),
                                             show_copy_button=False,
                                             question_name='skip_in_anthology',
                                             question_cache=self.question_cache)):
                    book['comment'] = _("Story in Series Anthology(%s).")%series
                    book['title'] = story.getMetadata('title')
                    book['author'] = [story.getMetadata('author')]
                    url = book['url'] = story.getMetadata('storyUrl', removeallentities=True)
                    book['good']=False
                    book['icon']='rotate-right.png'
                    book['status'] = _('Skipped')
                    ## save anthology ids to mark (python set doesn't have extend())
                    options['mark_anthology_ids']=options.get('mark_anthology_ids',set()).union(identicalbooks)
                    return

        ################################################################################################################################################33

        book['is_adult'] = adapter.is_adult
        book['username'] = adapter.username
        book['password'] = adapter.password

        book['icon'] = 'plus.png'
        book['status'] = _('Add')

        if not bgmeta:
            # set PI version instead of default.
            if 'version' in options:
                story.setMetadata('version',options['version'])

            # all_metadata duplicates some data, but also includes extra_entries, etc.
            book['all_metadata'] = story.getAllMetadata(removeallentities=True)
            if prefs['savemetacol'] != '':
                # get metadata to save in configured column.
                book['savemetacol'] = story.dump_html_metadata()

            book['title'] = story.getMetadata("title", removeallentities=True)
            book['author_sort'] = book['author'] = story.getList("author", removeallentities=True)
            book['publisher'] = story.getMetadata("publisher")
            url = book['url'] = story.getMetadata("storyUrl", removeallentities=True)
            book['tags'] = story.getSubjectTags(removeallentities=True)
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

        if not merge:# skip all the collision code when d/ling for merging.
            if collision in (CALIBREONLY, CALIBREONLYSAVECOL):
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
                identicalbooks = self.do_id_search(url)
                # logger.debug("identicalbooks:%s"%identicalbooks)
                if len(identicalbooks) < 1 and prefs['matchtitleauth']:
                    # find dups
                    mi = MetaInformation(book['title'],book['author'])
                    identicalbooks = db.find_identical_books(mi)
                    if len(identicalbooks) > 0:
                        logger.debug("existing found by title/author(s)")

                else:
                    logger.debug("existing found by identifier URL")

                if collision == SKIP and identicalbooks:
                    raise NotGoingToDownload(_("Skipping duplicate story."),"list_remove.png")

                if len(identicalbooks) > 1:
                    raise NotGoingToDownload(_("More than one identical book by Identifier URL or title/author(s)--can't tell which book to update/overwrite."),"minusminus.png")

                ## changed: add new book when CALIBREONLY if none found.
                if collision in (CALIBREONLY, CALIBREONLYSAVECOL) and not identicalbooks:
                    logger.debug("No existing book for %s, changing collision to ADDNEW for this book only"%url)
                    collision = book['collision'] = ADDNEW

                if len(identicalbooks)>0:
                    book_id = identicalbooks.pop()
                    book['calibre_id'] = book_id
                    book['icon'] = 'edit-redo.png'
                    book['status'] = _('Update')

                if book_id and mi: # book_id and mi only set if matched by title/author.
                    liburl = self.get_story_url(db,book_id)
                    if book['url'] != liburl and \
                        not (book['url'].replace('https','http') == liburl): # several sites have been changing to
                                                                             # https now.  Don't flag when that's the only change.
                        tags = db.get_tags(book_id)
                        flag_tag = "FFF Frozen URL" # not translated so it works across languages.
                        if flag_tag in tags:
                            book['comment'] = _("Update declined due to differing story URL(%s)(%s tag present)")%(liburl,flag_tag)
                            book['good']=False
                            book['icon']='rotate-right.png'
                            book['status'] = _('Different URL')
                            return
                        if prefs['checkforurlchange'] and not \
                                question_dialog_all(self.gui,
                                                _('Change Story URL?'),'''
                                                  <h3>%s</h3>
                                                  <p>%s</p>
                                                  <p>%s</p>
                                                  <p>%s</p>
                                                  <p>%s</p>
                                                  <p>%s</p>'''%(_('Change Story URL?'),
                                                                _('<b>%(title)s</b> by <b>%(author)s</b> is already in your library with a different source URL:')%{'title':mi.title,'author':', '.join(mi.author)},
                                                                _('In library: <a href="%(liburl)s">%(liburl)s</a>')%{'liburl':liburl},
                                                                _('New URL: <a href="%(newurl)s">%(newurl)s</a>')%{'newurl':book['url']},
                                                                _("Click '<b>Yes</b>' to update/overwrite book with new URL."),
                                                                _("Click '<b>No</b>' to skip updating/overwriting this book.")),
                                                    show_copy_button=False,
                                                    question_name='change_story_url',
                                                    question_cache=self.question_cache):
                            if question_dialog_all(self.gui,
                                                   _('Download as New Book?'),'''
                                                     <h3>%s</h3>
                                                     <p>%s</p>
                                                     <p>%s</p>
                                                     <p>%s</p>
                                                     <p>%s</p>
                                                     <p>%s</p>'''%(_('Download as New Book?'),
                                                                   _('<b>%(title)s</b> by <b>%(author)s</b> is already in your library with a different source URL.')%{'title':mi.title,'author':', '.join(mi.author)},
                                                                   _('You chose not to update the existing book.  Do you want to add a new book for this URL?'),
                                                                   _('New URL: <a href="%(newurl)s">%(newurl)s</a>')%{'newurl':book['url']},
                                                                   _("Click '<b>Yes</b>' to a new book with new URL."),
                                                                   _("Click '<b>No</b>' to skip URL.")),
                                                   show_copy_button=False,
                                                   question_name='download_new',
                                                   question_cache=self.question_cache):
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
                if collision in (CALIBREONLY, CALIBREONLYSAVECOL):
                    book['comment'] = _('Metadata collected.')
                    # don't need temp file created below.
                    return

                ## newer/chaptercount checks are the same for both:
                # Update epub, but only if more chapters.
                if not bgmeta and collision in (UPDATE,UPDATEALWAYS): # collision == UPDATE
                    # 'book' can exist without epub.  If there's no existing epub,
                    # let it go and it will download it.
                    if db.has_format(book_id,fileform,index_is_id=True):
                        (epuburl,chaptercount) = \
                            get_dcsource_chaptercount(BytesIO(db.format(book_id,'EPUB',
                                                                         index_is_id=True)))
                        #urlchaptercount = int(story.getMetadata('numChapters').replace(',',''))
                        # returns int adjusted for start-end range.
                        urlchaptercount = story.getChapterCount()
                        if chaptercount == urlchaptercount:
                            if collision == UPDATE:
                                raise NotGoingToDownload(_("Already contains %d chapters.")%chaptercount,'edit-undo.png',showerror=False)
                        elif chaptercount > urlchaptercount:
                            raise NotGoingToDownload(_("Existing epub contains %d chapters, web site only has %d. Use Overwrite to force update.") % (chaptercount,urlchaptercount),'dialog_error.png')
                        elif chaptercount == 0:
                            raise NotGoingToDownload(_("FanFicFare doesn't recognize chapters in existing epub, epub is probably from a different source. Use Overwrite to force update."),'dialog_error.png')

                if collision == OVERWRITE and \
                        db.has_format(book_id,formmapping[fileform],index_is_id=True):
                    logger.debug("OVERWRITE file: "+db.format_abspath(book_id, formmapping[fileform], index_is_id=True))
                    fileupdated=datetime.fromtimestamp(os.stat(db.format_abspath(book_id, formmapping[fileform], index_is_id=True))[8])
                    logger.debug("OVERWRITE file updated: %s"%fileupdated)
                    book['fileupdated']=fileupdated
                    if not bgmeta:
                        # check make sure incoming is newer.
                        lastupdated=story.getMetadataRaw('dateUpdated')
                        logger.debug("OVERWRITE site updated: %s"%lastupdated)

                        # updated doesn't have time (or is midnight), use dates only.
                        # updated does have time, use full timestamps.
                        if (lastupdated.time() == time.min and fileupdated.date() > lastupdated.date()) or \
                                (lastupdated.time() != time.min and fileupdated > lastupdated):
                            raise NotGoingToDownload(_("Not Overwriting, web site is not newer."),'edit-undo.png',showerror=False)

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

            ## Filling calibre_std_* and calibre_cust_* metadata
            book['calibre_columns']={}
            if prefs['cal_cols_pass_in']:
                # std columns
                mi = db.get_metadata(book['calibre_id'],index_is_id=True)
                # book['calibre_columns']['calibre_std_identifiers']=\
                #     {'val':', '.join(["%s:%s"%(k,v) for (k,v) in mi.get_identifiers().iteritems()]),
                #                      'label':_('Ids')}
                for k in mi.standard_field_keys():
                # for k in mi:
                    if k in STD_COLS_SKIP:
                        continue
                    (label,value,v,fmd) = mi.format_field_extended(k)
                    if not label and k in field_metadata:
                        label=field_metadata[k]['name']
                    key='calibre_std_'+k

                    # if k == 'user_categories':
                    #     value=u', '.join(mi.get(k))
                    #     label=_('User Categories')

                    if label: # only if it has a human readable name.
                        if value is None or not book['calibre_id']:
                            ## if existing book, populate existing calibre column
                            ## values in metadata, else '' to hide.
                            value=''
                        book['calibre_columns'][key]={'val':value,'label':label}
                        #logger.debug("%s(%s): %s"%(label,key,value))

                # custom columns
                for k, column in six.iteritems(self.gui.library_view.model().custom_columns):
                    if k != prefs['savemetacol']:
                        key='calibre_cust_'+k[1:]
                        label=column['name']
                        value=db.get_custom(book['calibre_id'],
                                            label=column['label'],
                                            index_is_id=True)
                        # custom always have name.
                        if value is None or not book['calibre_id']:
                            ## if existing book, populate existing calibre column
                            ## values in metadata, else '' to hide.
                            value=''
                        book['calibre_columns'][key]={'val':value,'label':label}
                        # logger.debug("%s(%s): %s"%(label,key,value))

            # if still 'good', make a temp file to write the output to.
            # For HTML format users, make the filename inside the zip something reasonable.
            # For crazy long titles/authors, limit it to 200chars.
            # For weird/OS-unsafe characters, use file safe only.
            try:
                prefix = story.formatFileName("${title}-${author}-",allowunsafefilename=False)[:100]
            except NameError:
                prefix = "bgmeta-"
            tmp = PersistentTemporaryFile(prefix=prefix,
                                          suffix='.'+options['fileform'],
                                          dir=options['tdir'])
            logger.debug("title:"+book['title'])
            logger.debug("outfile:"+tmp.name)
            book['outfile'] = tmp.name

        return

    def start_download_job(self,book_list,
                            options={'fileform':'epub',
                                     'collision':ADDNEW,
                                     'updatemeta':True,
                                     'bgmeta':False},
                            merge=False):
        '''
        Called by LoopProgressDialog to start story downloads BG processing.
        '''
        #print("start_download_job:book_list:%s"%book_list)

        ## No need to BG process when CALIBREONLY!  Fake it.  if
        ## CALIBREONLY, CALIBREONLYSAVECOL called on a url that isn't
        ## in the library, it's switched to ADDNEW for that one.  Only
        ## do NotJob version if not downloading any.
        calonly = True
        for book in book_list:
            if book['collision'] not in (CALIBREONLY, CALIBREONLYSAVECOL):
                calonly = False
                break
        if calonly:
            class NotJob(object):
                def __init__(self,result):
                    self.failed=False
                    self.result=result
            notjob = NotJob(book_list)
            self.download_list_completed(notjob,options=options)
            return

        self.do_mark_series_anthologies(options.get('mark_anthology_ids',set()))

        for book in book_list:
            if book['good']:
                break
        else:
            ## No good stories to try to download, go straight to
            ## updating error col.
            msgl = [
                _('None of the <b>%d</b> URLs/stories given can be/need to be downloaded.')%len(book_list),
                _('See log for details.'),
                _('Proceed with updating your library(Error or Last Checked Columns, if configured)?')]

            htmllog='<html><body><table border="1"><tr><th>'+_('Status')+'</th><th>'+_('Title')+'</th><th>'+_('Author')+'</th><th>'+_('Comment')+'</th><th>URL</th></tr>'
            for book in book_list:
                htmllog = htmllog + '<tr><td>' + '</td><td>'.join([escapehtml(book['status']),escapehtml(book['title']),escapehtml(", ".join(book['author'])),escapehtml(book['comment']),book['url']]) + '</td></tr>'

            htmllog = htmllog + '</table></body></html>'

            payload = ([], book_list, options)

            self.do_proceed_question(self.update_error_column,
                                     payload,
                                     htmllog,
                                     msgl)
            return

        ## save and pass cookiejar and caches to BG downloads.
        if 'browser_cache' in options:
            if not options['bgmeta']:
                ## With load-on-demand, the cache exists, but hasn't
                ## been loaded.  Once it is (file)loaded in jobs, it's
                ## marked as having been 'loaded'.  So don't send when
                ## bgmeta
                browser_cachefile = PersistentTemporaryFile(suffix='.browser_cache',
                                                            dir=options['tdir'])
                options['browser_cache'].save_cache(browser_cachefile.name)
                options['browser_cachefile'] = browser_cachefile.name
            ## can't be pickled by Calibre to send to BG proc
            del options['browser_cache']

        basic_cachefile = PersistentTemporaryFile(suffix='.basic_cache',
                                                dir=options['tdir'])
        options['basic_cache'].save_cache(basic_cachefile.name)
        options['basic_cachefile'] = basic_cachefile.name
        ## can't be pickled by Calibre to send to BG proc
        del options['basic_cache']

        cookiejarfile = PersistentTemporaryFile(suffix='.cookiejar',
                                                dir=options['tdir'])
        ## assumed to be a LWPCookieJar
        options['cookiejar'].save_cookiejar(cookiejarfile.name)
        options['cookiejarfile']=cookiejarfile.name
        ## can't be pickled by Calibre to send to BG proc
        del options['cookiejar']

        # pass the plugin path in for jobs.py to use for 'with:' to
        # get libs from plugin zip.
        options['plugin_path'] = self.interface_action_base_plugin.plugin_path

        func = 'arbitrary_n'
        cpus = self.gui.job_manager.server.pool_size
        args = ['calibre_plugins.fanficfare_plugin.jobs', 'do_download_worker',
                (book_list, options, cpus, merge)]
        desc = _('Download %s FanFiction Book(s)') % sum(1 for x in book_list if x['good'])
        job = self.gui.job_manager.run_job(
                self.Dispatcher(partial(self.download_list_completed,options=options,merge=merge)),
                func, args=args,
                description=desc)

        self.gui.jobs_pointer.start()
        self.gui.status_bar.show_message(_('Starting %d FanFicFare Downloads')%len(book_list),3000)

    def do_mark_series_anthologies(self,mark_anthology_ids):
        if prefs['mark_series_anthologies'] and mark_anthology_ids:
            #logger.debug(mark_anthology_ids)
            marked_ids = dict()
            marked_text = "fff"
            for index, book_id in enumerate(mark_anthology_ids):
                marked_ids[book_id] = '%s_anthology_%04d' % (marked_text, index)
            # Mark the results in our database
            logger.debug("set_marked_ids:%s"%marked_ids)
            if None in marked_ids:
                del marked_ids[None]
            self.gui.current_db.set_marked_ids(marked_ids)
            # Search to display the list contents
            self.gui.search.set_search_string('marked:' + marked_text)
            # Sort by our marked column to display the books in order
            self.gui.library_view.sort_by_named_field('marked', True)
            message=_('FanFicFare is marking and showing matching Anthology Books')+"\n\n"+ \
                _('To disable, uncheck the "Mark Matching Anthologies?" setting in FanFicFare configuration.')
            confirm(message,'fff_mark_series_anthologies', self.gui, show_cancel_button=False, title=_("Info"), pixmap='dialog_information.png')

    def get_custom_col_label(self,col):
        custom_columns = self.gui.library_view.model().custom_columns
        if col and col in custom_columns:
            return custom_columns[col]['label']
        else:
            return None

    def update_books_loop(self,book,db=None,
                          options={'fileform':'epub',
                                   'collision':ADDNEW,
                                   'updatemeta':True,
                                   'bgmeta':False},
                          errorcol_label=None,
                          lastcheckedcol_label=None):

        if options.get('add_tag',False):
            book['tags'].extend(options.get('add_tag').split(','))

        self.update_error_column_loop(book,db,errorcol_label,lastcheckedcol_label)

        if not book['good']:
            return # on error, only update errorcol

        logger.debug("add/update %s %s id(%s)"%(book['title'],book['url'],book['calibre_id']))
        mi = self.make_mi_from_book(book)

        if book['collision'] not in (CALIBREONLY, CALIBREONLYSAVECOL):
            new_book = book['calibre_id'] is None
            self.add_book_or_update_format(book,options,prefs,mi)
            if new_book:
                ## For failed chapters.  Didn't have calibre_id before
                ## add_book_or_update_format
                self.update_error_column_loop(book,db,errorcol_label,lastcheckedcol_label)

        if book['collision'] in (CALIBREONLY, CALIBREONLYSAVECOL) or \
                ( (options['updatemeta'] or book['added']) and book['good'] ):
            try:
                self.update_metadata(db, book['calibre_id'], book, mi, options)
            except:
                det_msg = "".join(traceback.format_exception(*sys.exc_info()))+"\n"+_("Story Details:")+pretty_book(book)
                logger.error("Error Updating Metadata:\n%s"%det_msg)
                error_dialog(self.gui,
                             _("Error Updating Metadata"),
                             "<p>"+_("An error has occurred while FanFicFare was updating calibre's metadata for <a href='%s'>%s</a>.")%(book['url'],book['title'])+"</p>"+
                             _("The ebook has been updated, but the metadata has not."),
                             det_msg=det_msg,
                             show=True)

    def update_books_finish(self, book_list, options={}, showlist=True):
        '''Notify calibre about updated rows, update external plugins
        (Reading Lists & Count Pages) as configured'''

        add_list = [ x for x in book_list if x['good'] and x['added'] ]
        add_ids = [ x['calibre_id'] for x in add_list ]
        update_list = [ x for x in book_list if x['good'] and not x['added'] ]
        update_ids = [ x['calibre_id'] for x in update_list ]
        all_ids = add_ids + update_ids
        all_not_calonly_list = [ x for x in add_list + update_list if x['collision'] not in (CALIBREONLY, CALIBREONLYSAVECOL) ]
        all_not_calonly_ids = [ x['calibre_id'] for x in all_not_calonly_list ]

        failed_list = [ x for x in book_list if not x['good'] ]
        failed_ids = [ x['calibre_id'] for x in failed_list ]

        chapter_error_list = [ x for x in book_list if 'chapter_error_count' in  x ]
        chapter_error_ids = [ x['calibre_id'] for x in chapter_error_list ]

        if all_not_calonly_ids and \
                (prefs['addtolists'] or prefs['addtoreadlists']):
            self.update_reading_lists(all_not_calonly_ids,add=True)

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
            marked_text = "fff"
            if prefs['mark_success']:
                for index, book_id in enumerate(all_ids):
                    marked_ids[book_id] = '%s_success_%04d' % (marked_text, index)
            if prefs['mark_failed']:
                for index, book_id in enumerate(failed_ids):
                    marked_ids[book_id] = '%s_failed_%04d' % (marked_text, index)
            if prefs['mark_chapter_error']:
                for index, book_id in enumerate(chapter_error_ids):
                    marked_ids[book_id] = '%s_chapter_error_%04d' % (marked_text, index)

            # Mark the results in our database, even if none.
            if None in marked_ids:
                del marked_ids[None]
            logger.debug("set_marked_ids:%s"%marked_ids)
            db.set_marked_ids(marked_ids)
            # only show if there are some.
            if marked_ids and prefs['showmarked']: # show add/update
                # Search to display the list contents
                self.gui.search.set_search_string('marked:' + marked_text)
                # Sort by our marked column to display the books in order
                self.gui.library_view.sort_by_named_field('marked', True)

        logger.debug(_('Finished Adding/Updating %d books.')%(len(update_list) + len(add_list)))
        self.gui.status_bar.show_message(_('Finished Adding/Updating %d books.')%(len(update_list) + len(add_list)), 3000)
        remove_dir(options['tdir'])
        logger.debug("removed tdir")

        if 'Count Pages' in self.gui.iactions and len(prefs['countpagesstats']) and len(all_ids):
            cp_plugin = self.gui.iactions['Count Pages']
            countpagesstats = list(prefs['countpagesstats']) # copy because we're changing it.
            # print("all_ids:%s"%all_ids)
            # print("countpagesstats:%s"%countpagesstats)

            ## If only some of the books need word counting, they'll
            ## have to be launched separately.
            if prefs['wordcountmissing'] and 'WordCount' in countpagesstats:
                # print("numWords:%s"%[ y['all_metadata']['numWords'] for y in add_list + update_list ])
                wc_ids = [ x['calibre_id'] for x in add_list + update_list if '' == x['all_metadata'].get('numWords','') ]
                ## not all need word count
                # print("wc_ids:%s"%wc_ids)
                ## if lists don't match
                if len(wc_ids)!=len(all_ids):
                    if wc_ids: # because often the lists don't match because 0
                        cp_plugin.count_statistics(wc_ids,['WordCount'])
                    ## don't do WordCount below.
                    while 'WordCount' in countpagesstats: countpagesstats.remove('WordCount')

            ## check that there's stuff to do in case wordcount was it.
            # print("countpagesstats:%s"%countpagesstats)
            if countpagesstats:
                cp_plugin.count_statistics(all_ids,countpagesstats)

        if prefs['autoconvert'] and all_not_calonly_ids:
            logger.debug(_('Starting auto conversion of %d books.')%(len(all_ids)))
            self.gui.status_bar.show_message(_('Starting auto conversion of %d books.')%(len(all_ids)), 3000)
            self.gui.iactions['Convert Books'].auto_convert_auto_add(all_not_calonly_ids)

    def download_list_completed(self, job, options={},merge=False):
        if job.failed:
            self.gui.job_exception(job, dialog_title='Failed to Download Stories')
            return

        self.previous = self.gui.library_view.currentIndex()
        db = self.gui.current_db

        book_list = job.result
        good_list = [ x for x in book_list if x['good'] ]
        bad_list = [ x for x in book_list if not x['good'] ]
        chapter_error_list = [ x for x in book_list if 'chapter_error_count' in  x ]
        try:
            good_list = sorted(good_list,key=lambda x : x['reportorder'])
            bad_list = sorted(bad_list,key=lambda x : x['reportorder'])
        except KeyError:
            good_list = sorted(good_list,key=lambda x : x['listorder'])
            bad_list = sorted(bad_list,key=lambda x : x['listorder'])
        #print("book_list:%s"%book_list)
        payload = (good_list, bad_list, options)

        msgl = [ _('FanFicFare found <b>%s</b> good and <b>%s</b> bad updates.')%(len(good_list),len(bad_list)) ]
        if chapter_error_list:
            message = _('Some of the stories downloaded have chapters errors.  Click View Log in the next dialog to see which.')
            confirm(message,'fff_chapter_errors', self.gui, show_cancel_button=False, title=_("Warning"))
            msgl.append(_('<b>%s</b> good stories contain chapter errors.')%len(chapter_error_list))
        if merge:
            if len(good_list) < 1:
                info_dialog(self.gui, _('FanFicFare: ')+_('No Good Stories for Anthology'),
                            _('No good stories/updates where downloaded, Anthology creation/update aborted.'),
                            show=True,
                            show_copy_button=False)
                return

            if len(bad_list) > 0:
                msgl.extend([
                        _('Are you sure you want to continue with creating/updating this Anthology?'),
                        _('Any updates that failed will <b>not</b> be included in the Anthology.'),
                        _("However, if there's an older version, it will still be included."),
                        _('See log for details.')])

            msgl.append(_('Proceed with updating this anthology and your library?'))

            htmllog='<html><body><table border="1"><tr><th>'+_('Status')+'</th><th>'+_('Title')+'</th><th>'+_('Author')+'</th><th>'+_('Comment')+'</th><th>URL</th></tr>'
            for book in sorted(good_list+bad_list,key=lambda x : x['listorder']):
                htmllog = htmllog + '<tr><td>' + '</td><td>'.join([escapehtml(book['status']),escapehtml(book['title']),escapehtml(", ".join(book['author'])),escapehtml(book['comment']),book['url']]) + '</td></tr>'

            htmllog = htmllog + '</table></body></html>'

            for book in bad_list:
                if 'epub_for_update' in book:
                    book['good']=True
                    book['outfile'] = book['epub_for_update']
                    good_list.append(book)

            do_update_func = self.do_download_merge_update
        else:
            msgl.extend([
                    _('See log for details.'),
                    _('Proceed with updating your library?')])

            htmllog='<html><body><table border="1"><tr><th>'+_('Status')+'</th><th>'+_('Title')+'</th><th>'+_('Author')+'</th><th>'+_('Comment')+'</th><th>URL</th></tr>'
            for book in good_list:
                htmllog = htmllog + '<tr><td>' + '</td><td>'.join([escapehtml(book['status']),escapehtml(book['title']),escapehtml(", ".join(book['author'])),escapehtml(book['comment']),book['url']]) + '</td></tr>'

            for book in bad_list:
                htmllog = htmllog + '<tr><td>' + '</td><td>'.join([escapehtml(book['status']),escapehtml(book['title']),escapehtml(", ".join(book['author'])),escapehtml(book['comment']),book['url']]) + '</td></tr>'

            htmllog = htmllog + '</table></body></html>'

            do_update_func = self.do_download_list_update

        self.do_proceed_question(do_update_func,
                                 payload,
                                 htmllog,
                                 msgl)

    def do_proceed_question(self, update_func, payload, htmllog, msgl):
        msg = '<p>'+'</p>\n<p>'.join(msgl)+ '</p>\n'
        if calibre_version >= (2, 57, 0):
            # log_viewer_unique_name implemented here: https://github.com/kovidgoyal/calibre/compare/v2.56.0...v2.57.0
            self.gui.proceed_question(update_func,
                                      payload, htmllog,
                                      _('FanFicFare log'), _('FanFicFare download complete'),
                                      msg,
                                      show_copy_button=False,
                                      log_viewer_unique_name="FanFicFare log viewer")
        else:
            self.gui.proceed_question(update_func,
                                      payload, htmllog,
                                      _('FanFicFare log'), _('FanFicFare download complete'),
                                      msg,
                                      show_copy_button=False)


    def do_download_merge_update(self, payload):
        with busy_cursor():
            db = self.gui.current_db

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
            mergebook = self.merge_meta_books(existingbook,good_list,options)

            #print("mergebook:\n%s"%mergebook)

            # make a temp file to write the output to.
            tmp = PersistentTemporaryFile(suffix='.'+options['fileform'],
                                          dir=options['tdir'])
            # logger.debug("title:"+mergebook['title'])
            logger.debug("outfile:"+tmp.name)
            mergebook['outfile'] = tmp.name

            ## Calibre's Polish heuristics for covers can cause problems
            ## if a merged anthology book has sub-book covers, but not a
            ## proper main cover.  So, now if there are any covers, we
            ## will force a main cover.

            ## start with None.  If no subbook covers, don't force one
            ## here.  User can configure FFF to always create/polish a
            ## cover if they want.  This is about when we force it.
            coverpath = None
            coverimgtype = None

            ## first, look for covers inside the subbooks.  Stop at the
            ## first one, which will be used if there isn't a pre-existing
            ## calibre cover.
            if not coverpath:
                for book in good_list:
                    coverdata = get_cover_data(book['outfile'])
                    if coverdata: # found a cover.
                        (coverimgtype,coverimgdata) = coverdata[4:6]
                        # logger.debug('coverimgtype:%s [%s]'%(coverimgtype,imagetypes[coverimgtype]))
                        tmpcover = PersistentTemporaryFile(suffix='.'+imagetypes[coverimgtype],
                                                           dir=options['tdir'])
                        tmpcover.write(coverimgdata)
                        tmpcover.flush()
                        tmpcover.close()
                        coverpath = tmpcover.name
                        break
            # logger.debug('coverpath:%s'%coverpath)

            ## if updating an existing book and there is at least one
            ## subbook cover:
            if coverpath and mergebook['calibre_id']:
                # Couldn't find a better way to get the cover path.
                calcoverpath = os.path.join(db.library_path,
                                         db.path(mergebook['calibre_id'], index_is_id=True),
                                         'cover.jpg')
                ## if there's an existing cover, use it.  Calibre will set
                ## it for us during lots of different actions anyway.
                if os.path.exists(calcoverpath):
                    coverpath = calcoverpath

            # logger.debug('coverpath:%s'%coverpath)
            self.get_epubmerge_plugin().do_merge(tmp.name,
                                                 [ x['outfile'] for x in good_list ],
                                                 tags=mergebook['tags'],
                                                 titleopt=mergebook['title'],
                                                 keepmetadatafiles=True,
                                                 source=mergebook['url'],
                                                 coverjpgpath=coverpath)

            mergebook['collision'] = options['collision'] = OVERWRITEALWAYS
            errorcol_label = self.get_custom_col_label(prefs['errorcol'])
            lastcheckedcol_label = self.get_custom_col_label(prefs['lastcheckedcol'])
            self.update_books_loop(mergebook,
                                   self.gui.current_db,
                                   options,
                                   errorcol_label=errorcol_label,
                                   lastcheckedcol_label=lastcheckedcol_label)
            self.update_books_finish([mergebook], options=options, showlist=False)

    def do_download_list_update(self, payload):

        (good_list,bad_list,options) = payload
        good_list = sorted(good_list,key=lambda x : x['listorder'])
        bad_list = sorted(bad_list,key=lambda x : x['listorder'])

        self.gui.status_bar.show_message(_('FanFicFare Adding/Updating books.'))
        errorcol_label = self.get_custom_col_label(prefs['errorcol'])
        lastcheckedcol_label = self.get_custom_col_label(prefs['lastcheckedcol'])

        columns = self.gui.library_view.model().custom_columns
        if good_list or prefs['mark'] or (bad_list and errorcol_label) or lastcheckedcol_label:
            LoopProgressDialog(self.gui,
                               good_list+bad_list,
                               partial(self.update_books_loop,
                                       options=options,
                                       db=self.gui.current_db,
                                       errorcol_label=errorcol_label,
                                       lastcheckedcol_label=lastcheckedcol_label),
                               partial(self.update_books_finish, options=options),
                               init_label=_("Updating calibre for FanFiction stories..."),
                               win_title=_("Update calibre for FanFiction stories"),
                               status_prefix=_("Updated"),
                               disable_cancel=True)

    def update_error_column(self,payload):
        '''Update custom error column if configured.'''
        (empty_list,book_list,options)=payload
        errorcol_label = self.get_custom_col_label(prefs['errorcol'])
        lastcheckedcol_label = self.get_custom_col_label(prefs['lastcheckedcol'])
        if prefs['mark'] or errorcol_label or lastcheckedcol_label:
            self.previous = self.gui.library_view.currentIndex() # used by update_books_finish.
            LoopProgressDialog(self.gui,
                               book_list,
                               partial(self.update_error_column_loop, db=self.gui.current_db, errorcol_label=errorcol_label, lastcheckedcol_label=lastcheckedcol_label),
                               partial(self.update_books_finish, options=options),
                               init_label=_("Updating calibre for BAD FanFiction stories..."),
                               win_title=_("Update calibre for BAD FanFiction stories"),
                               status_prefix=_("Updated"),
                               disable_cancel=True)

    def update_error_column_loop(self,book,db=None,errorcol_label=None,lastcheckedcol_label=None):
        if book['calibre_id'] and errorcol_label:
            if (not book['good'] or 'chapter_error_count' in book) and (book['showerror'] or prefs['save_all_errors']):
                logger.debug("update_error_column_loop bad %s %s %s"%(book['title'],book['url'],book['comment']))
                self.set_custom(db, book['calibre_id'], 'comment', book['comment'], label=errorcol_label, commit=True)
            else:
                ## if not recording error, clear any existing error, but only if not empty.
                prev_val = db.get_custom(book['calibre_id'],label=errorcol_label,index_is_id=True)
                logger.debug("update_error_column_loop prev_val:%s"%prev_val)
                if prev_val:
                    logger.debug("update_error_column_loop bad %s %s ''"%(book['title'],book['url']))
                    self.set_custom(db, book['calibre_id'], '(none)', '', label=errorcol_label, commit=True)
        if book['calibre_id'] and lastcheckedcol_label:
            #logger.debug("lastcheckedcol %s %s %s"%(book['title'],book['url'],book['timestamp']))
            self.set_custom(db, book['calibre_id'], 'timestamp',
                            book.get('timestamp',datetime.now().replace(tzinfo=local_tz)), # default to now if not in book.
                            label=lastcheckedcol_label, commit=True)

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

        try:
            # Remove before adding so the previous version is in the
            # OS Trash (on Windows, at least)
            db.remove_format(book_id,options['fileform'], index_is_id=True)
        except:
            pass
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
                if fmt.lower() != formmapping[options['fileform']].lower():
                    logger.debug("deleteotherforms remove f:"+fmt)
                    db.remove_format(book['calibre_id'], fmt, index_is_id=True)#, notify=False
        elif prefs['autoconvert']:
            ## 'Convert Book'.auto_convert_auto_add doesn't convert if
            ## the format is already there.
            fmt = calibre_prefs['output_format']
            # delete if there, but not if the format we just made.
            if fmt.lower() != formmapping[options['fileform']].lower() and \
                    db.has_format(book_id,fmt,index_is_id=True):
                logger.debug("autoconvert remove f:"+fmt)
                db.remove_format(book['calibre_id'], fmt, index_is_id=True)#, notify=False


        return book_id

    def set_custom(self,db,book_id,meta,val,label,commit=True):
        def raise_exception(meta,val,label,e):
            errmsg="Trying to set entry (%s) value(%s) to column (#%s) failed (%s)"%(meta,val,label,e)
            logger.warn(errmsg)
            raise Exception(errmsg)
        try:
            db.set_custom(book_id, val, label=label, commit=commit)
        except ValueError as ve:
            # editable flag off throws ValueError
            data = db.backend.custom_field_metadata(label)
            if not data['editable']:
                logger.debug("Skipping custom column(%s) update, column is set editable=False"%label)
            else:
                raise_exception(meta,val,label,e)
        except Exception as e:
            raise_exception(meta,val,label,e)

    def update_metadata(self, db, book_id, book, mi, options):
        oldmi = db.get_metadata(book_id,index_is_id=True)
        if prefs['keeptags']:
            old_tags = db.get_tags(book_id)
            #print("old_tags:%s"%old_tags)
            #print("mi.tags:%s"%mi.tags)
            # remove old Completed/In-Progress only if there's a new one.
            if 'Completed' in mi.tags or 'In-Progress' in mi.tags:
                old_tags = [ x for x in old_tags if x not in ('Completed', 'In-Progress') ]
                # remove old Last Update tags if there are new ones.
            if sum(1 for x in mi.tags if not x.startswith("Last Update")):
                old_tags = [ x for x in old_tags if not x.startswith("Last Update") ]

            # mi.tags needs to be list, but set kills dups.
            # this way also removes case-mismatched dups, keeping old_tags version.
            foldedcase_tags = dict()
            for t in list(mi.tags) + list(old_tags):
                foldedcase_tags[t.lower()] = t

            mi.tags = list(foldedcase_tags.values())
            #print("mi.tags:%s"%mi.tags)

        if book['all_metadata']['langcode']:
            # split due to anthologies.  Gives list of one for non-anth.
            mi.languages=book['all_metadata']['langcode'].split(', ')
        else:
            # Set language english, but only if not already set.
            if not oldmi.languages:
                mi.languages=['en']

        # implement 'newonly' flags here by setting to the current
        # value again.
        if not book['added']:
            for (col,newonly) in six.iteritems(prefs['std_cols_newonly']):
                if newonly:
                    if col == "identifiers":
                        mi.set_identifiers(oldmi.get_identifiers())
                    else:
                        try:
                            mi.__setattr__(col,oldmi.__getattribute__(col))
                        except AttributeError:
                            logger.warn("AttributeError? %s"%col)

        ## fix for suppressauthorsort (Force Author into Author Sort)
        ## option overriding Author-New-Only setting.  not done where
        ## suppressauthorsort/suppresstitlesort done because that
        ## would need an additional check for new books.
        if prefs['std_cols_newonly'].get('authors',False):
            mi.author_sort = oldmi.author_sort

        ## Ditto for title sort.
        if prefs['std_cols_newonly'].get('title',False):
            mi.title_sort = oldmi.title_sort

        db.set_metadata(book_id,mi)
        if not prefs['std_cols_newonly'].get('authors',False):
            # mi.authors gets run through the string_to_authors and split on '&' ',' 'and' and 'with'
            db.set_authors(book_id,book['author'],
                           allow_case_change=True) # author is a list.

        # do configured column updates here.
        #print("all_metadata: %s"%book['all_metadata'])
        custom_columns = self.gui.library_view.model().custom_columns

        # save metadata to configured column
        if 'savemetacol' in book and prefs['savemetacol'] != '' and prefs['savemetacol'] in custom_columns:
            label = custom_columns[prefs['savemetacol']]['label']
            self.set_custom(db, book_id, 'comment', book['savemetacol'], label=label, commit=True)

        # save lastchecked for new books.  Otherwise new books don't get lastchecked
        if prefs['lastcheckedcol'] != '' and prefs['lastcheckedcol'] in custom_columns:
            label = custom_columns[prefs['lastcheckedcol']]['label']
            self.set_custom(db, book_id, 'lastcheckedcol', book['timestamp'], label=label, commit=True)

        #print("prefs['custom_cols'] %s"%prefs['custom_cols'])
        for col, meta in six.iteritems(prefs['custom_cols']):
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
            if coldef['datatype'] in ('enumeration','comments','datetime','series'):
                self.set_custom(db, book_id, meta, book['all_metadata'][meta], label, commit=False)
            elif coldef['datatype'] == 'text':
                joined_val = book['all_metadata'][meta]
                # 'Contains names' custom columns need & separators.
                # If user has changed join_string_X, it's on them to fix.
                if coldef['display'].get('is_names',False):
                    joined_val = joined_val.replace(', ',' & ')
                self.set_custom(db, book_id, meta, joined_val, label, commit=False)
            elif coldef['datatype'] in ('int','float'):
                num = unicode(book['all_metadata'][meta]).replace(",","")
                if num != '':
                    self.set_custom(db, book_id, meta, num, label=label, commit=False)
            elif coldef['datatype'] == 'bool' and meta.startswith('status-'):
                if meta == 'status-C':
                    # Complete or Completed.
                    val = 'complete' in book['all_metadata']['status'].lower()
                if meta == 'status-I':
                    # In-Progress, In Progress, or In progress.
                    val = 'progress' in book['all_metadata']['status'].lower()
                self.set_custom(db, book_id, meta, val, label=label, commit=False)

        configuration = None
        if prefs['allow_custcol_from_ini']:
            configuration = get_fff_config(book['url'],options['fileform'])
            # meta => custcol[,a|n|r|n_anthaver,r_anthaver]
            # cliches=>\#acolumn,r
            for line in configuration.getConfig('custom_columns_settings').splitlines():
                if "=>" in line:
                    (meta,custcol) = [ x.strip() for x in line.split("=>") ]
                    flag='r'
                    anthaver=False
                    if "," in custcol:
                        (custcol,flag) = [ x.strip() for x in custcol.split(",") ]
                        anthaver = 'anthaver' in flag
                        flag=flag[0] # first char only.

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

                    # 'Contains names' custom columns need & separators.
                    # If user has changed join_string_X, it's on them to fix.
                    if coldef['display'].get('is_names',False):
                        val = val.replace(', ',' & ')

                    if flag == 'r' or (flag == 'n' and book['added']):
                        if coldef['datatype'] in ('int','float'): # for favs, etc--site specific metadata.
                            if 'anthology_meta_list' in book and meta in book['anthology_meta_list']:
                                # re-split list, strip commas, convert to floats
                                items = [ float(x.replace(",","")) for x in val.split(", ") ]
                                if anthaver:
                                    if items:
                                        val = sum(items) / float(len(items))
                                    else:
                                        val = 0
                                else:
                                    val = sum(items)
                            else:
                                val = unicode(val).replace(",","")
                        else:
                            val = val
                        if coldef['datatype'] == 'bool':
                            if val.lower() in ('t','true','1','yes','y'):
                                val = True
                            elif val.lower() in ('f','false','0','no','n'):
                                val = False
                            else:
                                val = None # for tri-state 'booleans'. Yes/No/Null
                        # logger.debug("setting 'r' or 'added':meta:%s label:%s val:%s"%(meta,label,val))
                        if val != '':
                            self.set_custom(db, book_id, meta, val, label=label, commit=False)

                    if flag == 'a':
                        vallist = []
                        try:
                            existing=db.get_custom(book_id,label=label,index_is_id=True)
                            # logger.debug("existing:%s"%existing)
                            if isinstance(existing,list):
                                vallist = existing
                            elif existing:
                                vallist = [existing]
                        except:
                            pass

                        #print("vallist:%s"%vallist)
                        if val:
                            vallist.append(val)

                        if coldef['display'].get('is_names',False):
                            join_str=' & '
                        else:
                            join_str=', '
                        self.set_custom(db, book_id, meta, join_str.join(vallist), label=label, commit=False)

        # set author link if found.  All current adapters have authorUrl, except anonymous on AO3.
        # Moved down so author's already in the DB.
        if 'authorUrl' in book['all_metadata'] and prefs['set_author_url']:
            authurls = book['all_metadata']['authorUrl'].split(", ")
            authorlist = [ a.replace('&',';') for a in book['author'] ]
            authorids = db.new_api.get_item_ids('authors',authorlist)
            authordata = db.new_api.author_data(list(authorids.values()))
            # logger.debug("\n\nauthorids:%s"%authorids)
            # logger.debug("authordata:%s"%authordata)

            author_id_to_link_map = dict()
            for i, author in enumerate(authorlist):
                # logger.debug("\n==============\nincoming authorUrl:(%s)\nexisting author url? (%s)\n"%(authurls[i],authordata.get(authorids[author],{}).get('link',None)))
                # - Only update author URL if different.  Saves calibre
                # updating other books by the same author.
                # - Author *can* be missing from Calibre if author is
                # set New Only and isn't the same anymore.
                if len(authurls) > i and authorids[author] is not None and authurls[i] != authordata.get(authorids[author],{}).get('link',None):
                    author_id_to_link_map[authorids[author]] = authurls[i]

            # logger.debug("author_id_to_link_map:%s\n\n"%author_id_to_link_map)
            if author_id_to_link_map:
                db.new_api.set_link_for_authors(author_id_to_link_map)

        db.commit()

        logger.info("cover_image:%s"%book['all_metadata']['cover_image'])
        # updating calibre cover from book.
        if options['fileform'] == 'epub' and \
            ( book['added'] or not prefs['covernewonly'] ) and (
            (prefs['updatecover'] and not prefs['updatecalcover']) ## backward compat
            or prefs['updatecalcover'] == SAVE_YES ## yes, always
            or (prefs['updatecalcover'] == SAVE_YES_IF_IMG ## yes, if image.
                and book['all_metadata']['cover_image'] )): # in ('specific','first','default','old')
            existingepub = db.format(book_id,'EPUB',index_is_id=True, as_file=True)
            epubmi = calibre_get_metadata(existingepub,'EPUB')
            if epubmi.cover_data[1] is not None:
                try:
                    db.set_cover(book_id, epubmi.cover_data[1])
                except:
                    logger.info("Failed to set_cover, skipping")

        # logger.debug("book['all_metadata']['cover_image']:%s"%book['all_metadata']['cover_image'])
        if (book['added'] or not prefs['gcnewonly']) and ( # skip if not new book and gcnewonly is True
            prefs['gencalcover'] == SAVE_YES ## yes, always
            or (prefs['gencalcover'] == SAVE_YES_UNLESS_IMG ## yes, unless image.
                and not book['all_metadata']['cover_image']) ): # not in ('specific','first','default','old')

            cover_generated = False # flag for polish below.
            # Yes, should do gencov.  Which?
            if prefs['calibre_gen_cover'] and HAS_CALGC:
                ## calibre's builtin, if available.  fetch updated mi
                ## object from database. Additional normalization of
                ## series (at least) happens
                realmi = db.get_metadata(book_id, index_is_id=True)
                cdata = cal_generate_cover(realmi)
                db.set_cover(book_id, cdata)
                cover_generated = True
            elif prefs['plugin_gen_cover'] and 'Generate Cover' in self.gui.iactions:
                # plugin, if available.

                #logger.debug("Do Generate Cover added:%s gcnewonly:%s"%(book['added'],prefs['gcnewonly']))

                # force a refresh if generating cover so complex composite
                # custom columns are current and correct
                db.refresh_ids([book_id])

                gc_plugin = self.gui.iactions['Generate Cover']
                setting_name = None
                if prefs['allow_gc_from_ini']:
                    if not configuration: # might already have it from allow_custcol_from_ini
                        configuration = get_fff_config(book['url'],options['fileform'])

                    for (template,regexp,setting) in configuration.get_generate_cover_settings():
                        value = Template(template).safe_substitute(book['all_metadata'])
                        # print("%s(%s) => %s => %s"%(template,value,regexp,setting))
                        if re.search(regexp,value):
                            setting_name = setting
                            break

                    if setting_name:
                        logger.debug("Generate Cover Setting from generate_cover_settings(%s)"%setting_name)
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
                    ## fetch updated mi object from
                    ## database. Additional normalization of series
                    ## (at least) happens
                    realmi = db.get_metadata(book_id, index_is_id=True)
                    gc_plugin.generate_cover_for_book(realmi,saved_setting_name=setting_name)
                    cover_generated = True

            if cover_generated and prefs['gc_polish_cover'] and \
                    options['fileform'] == "epub" and \
                    db.has_format(book['calibre_id'],'EPUB',index_is_id=True) :
                # set cover inside epub from calibre's polish feature
                from calibre.ebooks.oeb.polish.main import polish, ALL_OPTS
                from calibre.utils.logging import Log
                from collections import namedtuple

                # Couldn't find a better way to get the cover path.
                cover_path = os.path.join(db.library_path,
                                          db.path(book_id, index_is_id=True),
                                          'cover.jpg')
                data = {'cover':cover_path}
                #print("cover_path:%s"%cover_path)
                opts = ALL_OPTS.copy()
                opts.update(data)
                O = namedtuple('Options', ' '.join(six.iterkeys(ALL_OPTS)))
                opts = O(**opts)

                log = Log(level=Log.DEBUG)
                outfile = db.format_abspath(book_id,
                                            formmapping[options['fileform']],
                                            index_is_id=True)
                #print("polish cover outfile:%s"%outfile)
                polish({outfile:outfile}, opts, log, logger.info)

    def get_clean_reading_lists(self,lists):
        if lists == None or lists.strip() == "" :
            return []
        else:
            return [ x.strip() for x in lists.split(',') ]

    def update_reading_lists(self,book_ids,add=True):
        try:
            rl_plugin = self.gui.iactions['Reading List']
        except:
            if prefs['addtolists'] or prefs['addtoreadlists']:
                message="<p>"+_("You configured FanFicFare to automatically update Reading Lists, but you don't have the %s plugin installed anymore?")%'Reading List'+"</p>"
                confirm(message,'fff_no_reading_list_plugin', self.gui, show_cancel_button=False, title=_("Warning"))
            return

        if prefs['addtoreadlists']:
            if add:
                addremovefunc = rl_plugin.add_books_to_list
            else:
                addremovefunc = rl_plugin.remove_books_from_list

            lists = self.get_clean_reading_lists(prefs['read_lists'])
            if len(lists) < 1 :
                message="<p>"+_("You configured FanFicFare to automatically update \"To Read\" Reading Lists, but you don't have any lists set?")+"</p>"
                confirm(message,'fff_no_read_lists', self.gui, show_cancel_button=False, title=_("Warning"))
            for l in lists:
                if l in rl_plugin.get_list_names():
                    #print("add good read l:(%s)"%l)
                    addremovefunc(l,
                                  book_ids,
                                  display_warnings=False,
                                  refresh_screen=False)
                else:
                    if l != '':
                        message="<p>"+_("You configured FanFicFare to automatically update Reading List '%s', but you don't have a list of that name?")%l+"</p>"
                        confirm(message,'fff_no_reading_list_%s'%l, self.gui, show_cancel_button=False, title=_("Warning"))

        if prefs['addtolists'] and (add or (prefs['addtolistsonread'] and prefs['addtoreadlists']) ):
            lists = self.get_clean_reading_lists(prefs['send_lists'])
            if len(lists) < 1 :
                message="<p>"+_("You configured FanFicFare to automatically update \"Send to Device\" Reading Lists, but you don't have any lists set?")+"</p>"
                confirm(message,'fff_no_send_lists', self.gui, show_cancel_button=False, title=_("Warning"))

            for l in lists:
                if l in rl_plugin.get_list_names():
                    #print("good send l:(%s)"%l)
                    rl_plugin.add_books_to_list(l,
                                                #add_book_ids,
                                                book_ids,
                                                display_warnings=False,
                                                refresh_screen=False)
                else:
                    if l != '':
                        message="<p>"+_("You configured FanFicFare to automatically update Reading List '%s', but you don't have a list of that name?")%l+"</p>"
                        confirm(message,'fff_no_reading_list_%s'%l, self.gui, show_cancel_button=False, title=_("Warning"))
        self.gui.library_view.model().refresh_ids(book_ids)
        self.gui.tags_view.recount()

    def make_mi_from_book(self,book):
        if prefs['titlecase']:
            from calibre.ebooks.metadata.sources.base import fixcase
            book['title'] = fixcase(book['title'])
        if prefs['authorcase']:
            from calibre.ebooks.metadata.sources.base import fixauthors
            book['author'] = fixauthors(book['author'])
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
        book['status'] = 'Bad'
        book['showerror'] = True # False when NotGoingToDownload is
                                 # not-overwrite / not-update / skip
                                 # -- what some would consider 'not an
                                 # error'
        book['calibre_id'] = None
        book['begin'] = None
        book['end'] = None
        book['comment'] = '' # note this is a comment on the d/l or update.
        book['url'] = ''
        book['site'] = ''
        book['series'] = ''
        book['added'] = False
        book['pubdate'] = None
        book['publisher'] = None
        return book

    def convert_urls_to_books(self, urls):
        books = []
        uniqueurls = set()
        for i, url in enumerate(urls):
            book = self.convert_url_to_book(url)
            if book['uniqueurl'] in uniqueurls:
                book['good'] = False
                book['comment'] = _("Same story already included.")
                book['status']=_('Skipped')
            uniqueurls.add(book['uniqueurl'])
            book['listorder']=i # BG d/l jobs don't come back in order.
                                # Didn't matter until anthologies & 'marked' successes
            books.append(book)
        return books

    def convert_url_to_book(self, url):
        book = self.make_book()
        # Allow chapter range with URL.
        # like test1.com?sid=5[4-6] or [4,6]
        url,book['begin'],book['end'] = adapters.get_url_chapter_range(url)

        self.set_book_url_and_comment(book,url) # normalizes book[url]
        # for case of trying to download book by sections. url[1-5], url[6-10], etc.
        book['uniqueurl']="%s[%s-%s]"%(book['url'],book['begin'],book['end'])
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
                mi = calibre_get_metadata(existingepub,'EPUB')
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

            link = None
            ## only epub has URL in it--at least where I can easily find it.
            if existingepub:
                # look for dc:source first, then scan HTML if lookforurlinhtml
                link = get_dcsource(existingepub)
                if link:
                    # print("url from get_dcsource:%s"%link)
                    return link

            ## now also can search html and txt formats.
            if prefs['lookforurlinhtml']:
                # print(db.formats(book_id, index_is_id=True))
                if existingepub:
                    link = get_story_url_from_epub_html(existingepub,self.is_good_downloader_url)
                    # print("url from get_story_url_from_epub_html:%s"%link)
                    if link:
                        return link
                if db.has_format(book_id,'ZIP',index_is_id=True):
                    # print("has zip/html format")
                    existingziphtml = db.format(book_id,'ZIP',index_is_id=True, as_file=True)
                    link = get_story_url_from_zip_html(existingziphtml,self.is_good_downloader_url)
                    # print("url from get_story_url_from_zip_html:%s"%link)
                    if link:
                        return link
                if db.has_format(book_id,'TXT',index_is_id=True):
                    # print("has txt format")
                    existingtxt = db.format(book_id,'TXT',index_is_id=True)
                    links = get_urls_from_text(existingtxt,normalize=True)
                    if links:
                        return links[0]
        return None

    def is_good_downloader_url(self,url):
        return adapters.getNormalStoryURL(url)

    def merge_meta_books(self,existingbook,book_list,options):
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
        serieslists=[]

        logger.debug("options['anthology_url']:%s"%options.get('anthology_url','NOT FOUND'))

        # copy list top level
        for b in book_list:
            if b['status'] == 'Error':
                ## only tripped by a failure to get metadata for a
                ## pre-existing book in anthology.
                b['title']=_('Existing Book Update Failed')
                b['comments']=_('''A pre-existing book in this anthology failed to find metadata.<br>
Story URL: %s<br>
Error: %s<br>
The previously downloaded book is still in the anthology, but FFF doesn't have the metadata to fill this field.
''')%(b['url'],b['comment'])
                continue
            if b['series']:
                bookserieslist = []
                serieslists.append(bookserieslist)
                j = 0
                # looking for series00, series01, etc.  it is assumed
                # that 'series' is set and == series00 when numbered
                # series are used.
                while b['all_metadata'].get('series%02d'%j,False):
                    try:
                        bookserieslist.append(b['all_metadata']['series%02d'%j][:b['all_metadata']['series%02d'%j].index(" [")])
                    except ValueError: # substring not found
                        bookserieslist.append(b['all_metadata']['series%02d'%j])
                    j+=1
                try:
                    serieslist.append(b['series'][:b['series'].index(" [")])
                except ValueError: # substring not found
                    serieslist.append(b['series'])

            if b['publisher']:
                if not book['publisher']:
                    ## not set in all_metadata because it's not one of
                    ## the permitted metadata--use site instead.
                    book['publisher']=b['publisher']
                elif book['publisher']!=b['publisher']:
                    book['publisher']=None # if any are different, don't use.

            # copy authors & tags.
            for k in ('author','tags'):
                if k in b:
                    for v in b[k]:
                        if v not in book[k]:
                            book[k].append(v)
                else:
                    logger.debug("book: %s lacks %s"%(b['title'],k))

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
            if 'all_metadata' in b:
                for (k,v) in six.iteritems(b['all_metadata']):
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
            # else:
            #     logger.debug("'all_metadata' not in b:%s"%b)

        # logger.debug("book['url']:%s"%book['url'])

        ## if series explicitly collected, include desc, if it's there.
        d = options.get('frompage',{}).get('desc','')
        book['comments'] = '<div>'+d+'<p>' +_("Anthology containing:")+"</p>\n\n"
        wraptitle = lambda x : '<p><b>'+x+'</b></p>\n'
        if len(book['author']) > 1:
            mkbooktitle = lambda x : wraptitle(_("%(title)s by %(author)s") % {'title':x['title'],'author':' & '.join(x['author'])})
        else:
            mkbooktitle = lambda x : wraptitle(x['title'])

        if prefs['includecomments']:
            def mkbookcomments(x):
                if x['comments']:
                    return '%s<div>%s</div>'%(mkbooktitle(x),x['comments'])
                else:
                    return '%s\n'%mkbooktitle(x)

            book['comments'] += (
                            '<hr></div><div class="mergedbook">'.join([ mkbookcomments(x) for x in book_list]) +
                            '</div>')
        else:
            book['comments'] += '\n'.join( [ mkbooktitle(x) for x in book_list ] )
        book['comments'] += '</div>'
        # logger.debug(book['comments'])

        configuration = get_fff_config(book['url'],options['fileform'])
        if existingbook:
            book['title'] = deftitle = existingbook['title']
            if prefs['anth_comments_newonly']:
                book['comments'] = existingbook['comments']
        else:
            book['title'] = deftitle = book_list[0]['title']
            # book['all_metadata']['description']

            series = None
            n = options.get('frompage',{}).get('name',None)
            if n:
                # series explicitly parsed, use name.
                book['title'] = series = n
            else:
                # logger.debug("serieslists:%s"%serieslists)
                # if all same series, use series for name.  But only if all and not previous named
                if len(serieslist) == len(book_list):
                    series = serieslist[0]
                    book['title'] = series
                    for sr in serieslist:
                        if series != sr:
                            book['title'] = deftitle
                            series = None
                            break
                if not series and serieslists:
                    # for multiple series sites: if all stories are
                    # members of the same series, use it.  Or the first
                    # one, rather.
                    common_series = get_common_elements(serieslists)
                    # logger.debug("common_series:%s"%common_series)
                    if common_series:
                        series = common_series[0]
                        book['title'] = series

            if prefs['setanthologyseries'] and book['title'] == series:
                book['series'] = series+' [0]'

            # logger.debug("anthology_title_pattern:%s"%configuration.getConfig('anthology_title_pattern'))
            if configuration.getConfig('anthology_title_pattern'):
                tmplt = Template(configuration.getConfig('anthology_title_pattern'))
                book['title'] = tmplt.safe_substitute({'title':book['title']})
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
        ## some adapters, like AO3, may have series status.
        s = options.get('frompage',{}).get('status','')
        if s:
            book['all_metadata']['status'] = s
            book['tags'].append(s)
        book['tags'].extend(configuration.getConfigList('anthology_tags'))
        book['all_metadata']['anthology'] = "true"

        if 'mergebook' in options:
            book['calibre_id'] = options['mergebook']['calibre_id']

        if 'anthology_url' in options:
            book['url'] = options['anthology_url']

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
    return [ x for x in urls.strip().splitlines() if f(x)]

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
