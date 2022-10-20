# -*- coding: utf-8 -*-

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import six

__license__   = 'GPL v3'
__copyright__ = '2021, Jim Miller'
__docformat__ = 'restructuredtext en'

import logging
logger = logging.getLogger(__name__)

import re
import threading
from collections import OrderedDict

from PyQt5 import QtWidgets as QtGui
from PyQt5.Qt import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
                      QLineEdit, QComboBox, QCheckBox, QPushButton, QTabWidget,
                      QScrollArea, QGroupBox, QButtonGroup, QRadioButton,
                      Qt)

from calibre.gui2 import dynamic, info_dialog
from calibre.gui2.complete2 import EditWithComplete
from calibre.gui2.dialogs.confirm_delete import confirm
from fanficfare.six import text_type as unicode

try:
    from calibre.ebooks.covers import generate_cover as cal_generate_cover
    HAS_CALGC=True
except:
    HAS_CALGC=False

# pulls in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.library.field_metadata import FieldMetadata
field_metadata = FieldMetadata()

# There are a number of things used several times that shouldn't be
# translated.  This is just a way to make that easier by keeping them
# out of the _() strings.
# I'm tempted to override _() to include them...
no_trans = { 'pini':'personal.ini',
             'gcset':'generate_cover_settings',
             'ccset':'custom_columns_settings',
             'gc':'Generate Cover',
             'rl':'Reading List',
             'cp':'Count Pages',
             'cmplt':'Completed',
             'inprog':'In-Progress',
             'lul':'Last Updated',
             'lus':'lastupdate',
             'is':'include_subject',
             'isa':'is_adult',
             'u':'username',
             'p':'password',
             }

STD_COLS_SKIP = ['size','cover','news','ondevice','path','series_sort','sort']

from calibre_plugins.fanficfare_plugin.prefs import (
    prefs, rejects_data, PREFS_NAMESPACE, prefs_save_options,
    updatecalcover_order, gencalcover_order, do_wordcount_order,
    SAVE_YES, SAVE_NO)

from calibre_plugins.fanficfare_plugin.dialogs import (
    UPDATE, UPDATEALWAYS, collision_order, save_collisions, RejectListDialog,
    EditTextDialog, IniTextDialog, RejectUrlEntry)

from fanficfare.adapters import getSiteSections, get_section_url

from calibre_plugins.fanficfare_plugin.common_utils import (
    KeyboardConfigDialog, PrefsViewerDialog, busy_cursor )


class RejectURLList:
    def __init__(self,prefs,rejects_data):
        self.prefs = prefs
        self.rejects_data = rejects_data
        self.sync_lock = threading.RLock()
        self.listcache = None

    def _read_list_from_text(self,text,addreasontext='',normalize=True):
        cache = OrderedDict()

        #print("_read_list_from_text")
        for line in text.splitlines():
            rue = RejectUrlEntry(line,addreasontext=addreasontext,
                                 fromline=True,normalize=normalize)
            #print("rue.url:%s"%rue.url)
            if rue.valid:
                cache[get_section_url(rue.url)] = rue
        return cache

    ## Note that RejectURLList now applies
    ## adapters.get_section_url(url) to all urls before caching and
    ## before checking so ffnet/a/123/1/Title -> ffnet/a/123/1/,
    ## xenforo too.  Saved list still contains full URL so we're not
    ## destorying any data.  Could have duplicates, though.
    def _get_listcache(self):
        with busy_cursor():
            if self.listcache == None:
                # logger.debug("prefs['last_saved_version']:%s"%unicode(self.prefs['last_saved_version']))
                if tuple(self.prefs['last_saved_version']) > (3, 1, 7) and \
                        self.rejects_data['rejecturls_data']:
                    # logger.debug("_get_listcache: rejects_data['rejecturls_data']")
                    self.listcache = OrderedDict()
                    for x in self.rejects_data['rejecturls_data']:
                        rue = RejectUrlEntry.from_data(x)
                        if rue.valid:
                            # if rue.url != get_section_url(rue.url):
                            #     logger.debug("\n=============\nurl:%s section:%s\n================"%(rue.url,get_section_url(rue.url)))
                            section_url = get_section_url(rue.url)
                            if section_url in self.listcache:
                                logger.debug("Duplicate in Reject list: %s %s (use longer)"%(
                                        self.listcache[section_url].url, rue.url))
                            ## if there's a dup, keep the one with the
                            ## longer URL, more likely to be titled
                            ## version.
                            if( section_url not in self.listcache
                                or len(rue.url) > len(self.listcache[section_url].url) ):
                                self.listcache[section_url] = rue
                else:
                    # Assume saved rejects list is already normalized after
                    # v2.10.9.  If normalization needs to change someday, can
                    # increase this to do it again.
                    normalize = tuple(self.prefs['last_saved_version']) < (2, 10, 9)
                    #print("normalize:%s"%normalize)
                    self.listcache = self._read_list_from_text(self.prefs['rejecturls'],
                                                               normalize=normalize)
                    if normalize:
                        self._save_list(self.listcache,clearcache=False)
                    # logger.debug("_get_listcache: prefs['rejecturls']")

        # logger.debug(self.listcache)
        # logger.debug([ x.to_data() for x in self.listcache.values()])
        return self.listcache

    def _save_list(self,listcache,clearcache=True):
        with busy_cursor():
            #print("_save_list")
            ## As of July 2020 it's been > 1.5 years since
            ## rejects_data added.  Stop keeping older version in
            ## prefs.
            del self.prefs['rejecturls']
            self.prefs.save_to_db()
            rejects_data['rejecturls_data'] = [x.to_data() for x in listcache.values()]
            rejects_data.save_to_db()
            if clearcache:
                self.listcache = None

    def clear_cache(self):
        self.listcache = None

    # true if url is in list.
    def check(self,url):
        # logger.debug("Checking %s(%s)"%(url,get_section_url(url)))
        url = get_section_url(url)
        with self.sync_lock:
            listcache = self._get_listcache()
            return url in listcache

    def get_note(self,url):
        url = get_section_url(url)
        with self.sync_lock:
            listcache = self._get_listcache()
            if url in listcache:
                return listcache[url].note
            # not found
            return ''

    def get_full_note(self,url):
        url = get_section_url(url)
        with self.sync_lock:
            listcache = self._get_listcache()
            if url in listcache:
                return listcache[url].fullnote()
            # not found
            return ''

    def remove(self,url):
        url = get_section_url(url)
        with self.sync_lock:
            listcache = self._get_listcache()
            if url in listcache:
                del listcache[url]
                self._save_list(listcache)

    def add_text(self,rejecttext,addreasontext):
        self.add(list(self._read_list_from_text(rejecttext,addreasontext).values()))

    def add(self,rejectlist,clear=False):
        with self.sync_lock:
            if clear:
                listcache=OrderedDict()
            else:
                listcache = self._get_listcache()
            for l in rejectlist:
                listcache[get_section_url(l.url)]=l
            self._save_list(listcache)

    def get_list(self):
        return list(self._get_listcache().values())

    def get_reject_reasons(self):
        return self.prefs['rejectreasons'].splitlines()

rejecturllist = RejectURLList(prefs,rejects_data)

class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action

        self.l = QVBoxLayout()
        self.setLayout(self.l)

        label = QLabel('<a href="'\
                           +'https://github.com/JimmXinu/FanFicFare/wiki/Supportedsites">'\
                           +_('List of Supported Sites')+'</a> -- <a href="'\
                           +'https://github.com/JimmXinu/FanFicFare/wiki/FAQs">'\
                           +_('FAQs')+'</a>')

        label.setOpenExternalLinks(True)
        self.l.addWidget(label)


        self.scroll_area = QScrollArea(self)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)
        self.scroll_area.setWidgetResizable(True)
        self.l.addWidget(self.scroll_area)

        tab_widget = QTabWidget(self)
        self.scroll_area.setWidget(tab_widget)

        self.basic_tab = BasicTab(self, plugin_action)
        tab_widget.addTab(self.basic_tab, _('Basic'))

        self.personalini_tab = PersonalIniTab(self, plugin_action)
        tab_widget.addTab(self.personalini_tab, 'personal.ini')

        self.readinglist_tab = ReadingListTab(self, plugin_action)
        tab_widget.addTab(self.readinglist_tab, 'Reading Lists')
        if 'Reading List' not in plugin_action.gui.iactions:
            self.readinglist_tab.setEnabled(False)

        self.calibrecover_tab = CalibreCoverTab(self, plugin_action)
        tab_widget.addTab(self.calibrecover_tab, _('Calibre Cover'))

        self.countpages_tab = CountPagesTab(self, plugin_action)
        tab_widget.addTab(self.countpages_tab, 'Count Pages')
        if 'Count Pages' not in plugin_action.gui.iactions:
            self.countpages_tab.setEnabled(False)

        self.std_columns_tab = StandardColumnsTab(self, plugin_action)
        tab_widget.addTab(self.std_columns_tab, _('Standard Columns'))

        self.cust_columns_tab = CustomColumnsTab(self, plugin_action)
        tab_widget.addTab(self.cust_columns_tab, _('Custom Columns'))

        self.imap_tab = ImapTab(self, plugin_action)
        tab_widget.addTab(self.imap_tab, _('Email Settings'))

        self.other_tab = OtherTab(self, plugin_action)
        tab_widget.addTab(self.other_tab, _('Other'))


    def save_settings(self):
        with busy_cursor():

            # basic
            prefs['fileform'] = unicode(self.basic_tab.fileform.currentText())
            prefs['collision'] = save_collisions[unicode(self.basic_tab.collision.currentText())]
            prefs['updatemeta'] = self.basic_tab.updatemeta.isChecked()
            prefs['bgmeta'] = self.basic_tab.bgmeta.isChecked()
            prefs['keeptags'] = self.basic_tab.keeptags.isChecked()
            prefs['mark'] = self.basic_tab.mark.isChecked()
            prefs['mark_success'] = self.basic_tab.mark_success.isChecked()
            prefs['mark_failed'] = self.basic_tab.mark_failed.isChecked()
            prefs['mark_chapter_error'] = self.basic_tab.mark_chapter_error.isChecked()
            prefs['showmarked'] = self.basic_tab.showmarked.isChecked()
            prefs['autoconvert'] = self.basic_tab.autoconvert.isChecked()
            prefs['show_est_time'] = self.basic_tab.show_est_time.isChecked()
            prefs['urlsfromclip'] = self.basic_tab.urlsfromclip.isChecked()
            prefs['button_instantpopup'] = self.basic_tab.button_instantpopup.isChecked()
            prefs['updatedefault'] = self.basic_tab.updatedefault.isChecked()
            prefs['deleteotherforms'] = self.basic_tab.deleteotherforms.isChecked()
            prefs['adddialogstaysontop'] = self.basic_tab.adddialogstaysontop.isChecked()
            prefs['lookforurlinhtml'] = self.basic_tab.lookforurlinhtml.isChecked()
            prefs['checkforseriesurlid'] = self.basic_tab.checkforseriesurlid.isChecked()
            prefs['auto_reject_seriesurlid'] = self.basic_tab.auto_reject_seriesurlid.isChecked()
            prefs['mark_series_anthologies'] = self.basic_tab.mark_series_anthologies.isChecked()
            prefs['checkforurlchange'] = self.basic_tab.checkforurlchange.isChecked()
            prefs['injectseries'] = self.basic_tab.injectseries.isChecked()
            prefs['matchtitleauth'] = self.basic_tab.matchtitleauth.isChecked()
            prefs['do_wordcount'] = prefs_save_options[unicode(self.basic_tab.do_wordcount.currentText())]
            prefs['smarten_punctuation'] = self.basic_tab.smarten_punctuation.isChecked()
            prefs['reject_always'] = self.basic_tab.reject_always.isChecked()
            prefs['reject_delete_default'] = self.basic_tab.reject_delete_default.isChecked()

            if self.readinglist_tab:
                # lists
                prefs['send_lists'] = ', '.join([ x.strip() for x in unicode(self.readinglist_tab.send_lists_box.text()).split(',') if x.strip() ])
                prefs['read_lists'] = ', '.join([ x.strip() for x in unicode(self.readinglist_tab.read_lists_box.text()).split(',') if x.strip() ])
                # logger.debug("send_lists: %s"%prefs['send_lists'])
                # logger.debug("read_lists: %s"%prefs['read_lists'])
                prefs['addtolists'] = self.readinglist_tab.addtolists.isChecked()
                prefs['addtoreadlists'] = self.readinglist_tab.addtoreadlists.isChecked()
                prefs['addtolistsonread'] = self.readinglist_tab.addtolistsonread.isChecked()
                prefs['autounnew'] = self.readinglist_tab.autounnew.isChecked()

            # personal.ini
            ini = self.personalini_tab.personalini
            if ini:
                prefs['personal.ini'] = ini
            else:
                # if they've removed everything, reset to default.
                prefs['personal.ini'] = get_resources('plugin-example.ini')

            prefs['cal_cols_pass_in'] = self.personalini_tab.cal_cols_pass_in.isChecked()

            # Covers tab
            prefs['updatecalcover'] = prefs_save_options[unicode(self.calibrecover_tab.updatecalcover.currentText())]
            # for backward compatibility:
            prefs['updatecover'] = prefs['updatecalcover'] == SAVE_YES
            prefs['gencalcover'] = prefs_save_options[unicode(self.calibrecover_tab.gencalcover.currentText())]
            prefs['calibre_gen_cover'] = self.calibrecover_tab.calibre_gen_cover.isChecked()
            prefs['plugin_gen_cover'] = self.calibrecover_tab.plugin_gen_cover.isChecked()
            prefs['gcnewonly'] = self.calibrecover_tab.gcnewonly.isChecked()
            prefs['covernewonly'] = self.calibrecover_tab.covernewonly.isChecked()
            gc_site_settings = {}
            for (site,combo) in six.iteritems(self.calibrecover_tab.gc_dropdowns):
                val = unicode(combo.itemData(combo.currentIndex()))
                if val != 'none':
                    gc_site_settings[site] = val
                    #print("gc_site_settings[%s]:%s"%(site,gc_site_settings[site]))
            prefs['gc_site_settings'] = gc_site_settings
            prefs['allow_gc_from_ini'] = self.calibrecover_tab.allow_gc_from_ini.isChecked()
            prefs['gc_polish_cover'] = self.calibrecover_tab.gc_polish_cover.isChecked()

            # Count Pages tab
            countpagesstats = []

            if self.countpages_tab.pagecount.isChecked():
                countpagesstats.append('PageCount')
            if self.countpages_tab.wordcount.isChecked():
                countpagesstats.append('WordCount')
            if self.countpages_tab.fleschreading.isChecked():
                countpagesstats.append('FleschReading')
            if self.countpages_tab.fleschgrade.isChecked():
                countpagesstats.append('FleschGrade')
            if self.countpages_tab.gunningfog.isChecked():
                countpagesstats.append('GunningFog')

            prefs['countpagesstats'] = countpagesstats
            prefs['wordcountmissing'] = self.countpages_tab.wordcount.isChecked() and self.countpages_tab.wordcountmissing.isChecked()

            # Standard Columns tab
            colsnewonly = {}
            for (col,checkbox) in six.iteritems(self.std_columns_tab.stdcol_newonlycheck):
                colsnewonly[col] = checkbox.isChecked()
            prefs['std_cols_newonly'] = colsnewonly

            prefs['suppressauthorsort'] = self.std_columns_tab.suppressauthorsort.isChecked()
            prefs['suppresstitlesort'] = self.std_columns_tab.suppresstitlesort.isChecked()
            prefs['authorcase'] = self.std_columns_tab.authorcase.isChecked()
            prefs['titlecase'] = self.std_columns_tab.titlecase.isChecked()
            prefs['setanthologyseries'] = self.std_columns_tab.setanthologyseries.isChecked()

            prefs['set_author_url'] =self.std_columns_tab.set_author_url.isChecked()
            prefs['includecomments'] =self.std_columns_tab.includecomments.isChecked()
            prefs['anth_comments_newonly'] =self.std_columns_tab.anth_comments_newonly.isChecked()

            # Custom Columns tab
            # error column
            prefs['errorcol'] = unicode(self.cust_columns_tab.errorcol.itemData(self.cust_columns_tab.errorcol.currentIndex()))
            prefs['save_all_errors'] = self.cust_columns_tab.save_all_errors.isChecked()

            # metadata column
            prefs['savemetacol'] = unicode(self.cust_columns_tab.savemetacol.itemData(self.cust_columns_tab.savemetacol.currentIndex()))

            # lastchecked column
            prefs['lastcheckedcol'] = unicode(self.cust_columns_tab.lastcheckedcol.itemData(self.cust_columns_tab.lastcheckedcol.currentIndex()))

            # cust cols tab
            colsmap = {}
            for (col,combo) in six.iteritems(self.cust_columns_tab.custcol_dropdowns):
                val = unicode(combo.itemData(combo.currentIndex()))
                if val != 'none':
                    colsmap[col] = val
                    #print("colsmap[%s]:%s"%(col,colsmap[col]))
            prefs['custom_cols'] = colsmap

            colsnewonly = {}
            for (col,checkbox) in six.iteritems(self.cust_columns_tab.custcol_newonlycheck):
                colsnewonly[col] = checkbox.isChecked()
            prefs['custom_cols_newonly'] = colsnewonly

            prefs['allow_custcol_from_ini'] = self.cust_columns_tab.allow_custcol_from_ini.isChecked()

            prefs['imapserver'] = unicode(self.imap_tab.imapserver.text()).strip()
            prefs['imapuser'] = unicode(self.imap_tab.imapuser.text()).strip()
            prefs['imappass'] = unicode(self.imap_tab.imappass.text()).strip()
            prefs['imapfolder'] = unicode(self.imap_tab.imapfolder.text()).strip()
            # prefs['imaptags'] = unicode(self.imap_tab.imaptags.text()).strip()
            prefs['imaptags'] = ', '.join([ x.strip() for x in unicode(self.imap_tab.imaptags.text()).split(',') if x.strip() ])
            prefs['imapmarkread'] = self.imap_tab.imapmarkread.isChecked()
            prefs['imapsessionpass'] = self.imap_tab.imapsessionpass.isChecked()
            prefs['auto_reject_from_email'] = self.imap_tab.auto_reject_from_email.isChecked()
            prefs['update_existing_only_from_email'] = self.imap_tab.update_existing_only_from_email.isChecked()
            prefs['download_from_email_immediately'] = self.imap_tab.download_from_email_immediately.isChecked()
            prefs.save_to_db()
            self.plugin_action.set_popup_mode()

    def edit_shortcuts(self):
        self.save_settings()
        # Force the menus to be rebuilt immediately, so we have all our actions registered
        self.plugin_action.rebuild_menus()
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()

class BasicTab(QWidget):

    def __init__(self, parent_dialog, plugin_action):
        self.parent_dialog = parent_dialog
        self.plugin_action = plugin_action
        QWidget.__init__(self)

        topl = QVBoxLayout()
        self.setLayout(topl)

        label = QLabel(_('These settings control the basic features of the plugin--downloading FanFiction.'))
        label.setWordWrap(True)
        topl.addWidget(label)

        defs_gb = groupbox = QGroupBox(_("Defaults Options on Download"))
        self.l = QVBoxLayout()
        groupbox.setLayout(self.l)

        tooltip = _("On each download, FanFicFare offers an option to select the output format. <br />This sets what that option will default to.")
        horz = QHBoxLayout()
        label = QLabel(_('Default Output &Format:'))
        label.setToolTip(tooltip)
        horz.addWidget(label)
        self.fileform = QComboBox(self)
        self.fileform.addItem('epub')
        self.fileform.addItem('mobi')
        self.fileform.addItem('html')
        self.fileform.addItem('txt')
        self.fileform.setCurrentIndex(self.fileform.findText(prefs['fileform']))
        self.fileform.setToolTip(tooltip)
        self.fileform.activated.connect(self.set_collisions)
        label.setBuddy(self.fileform)
        horz.addWidget(self.fileform)
        self.l.addLayout(horz)

        tooltip = _("On each download, FanFicFare offers an option of what happens if that story already exists. <br />This sets what that option will default to.")
        horz = QHBoxLayout()
        label = QLabel(_('Default If Story Already Exists?'))
        label.setToolTip(tooltip)
        horz.addWidget(label)
        self.collision = QComboBox(self)
        # add collision options
        self.set_collisions()
        i = self.collision.findText(save_collisions[prefs['collision']])
        if i > -1:
            self.collision.setCurrentIndex(i)
        self.collision.setToolTip(tooltip)
        label.setBuddy(self.collision)
        horz.addWidget(self.collision)
        self.l.addLayout(horz)

        horz = QHBoxLayout()
        self.updatemeta = QCheckBox(_('Default Update Calibre &Metadata?'),self)
        self.updatemeta.setToolTip(_("On each download, FanFicFare offers an option to update Calibre's metadata (title, author, URL, tags, custom columns, etc) from the web site. <br />This sets whether that will default to on or off. <br />Columns set to 'New Only' in the column tabs will only be set for new books."))
        self.updatemeta.setChecked(prefs['updatemeta'])
        horz.addWidget(self.updatemeta)

        self.bgmeta = QCheckBox(_('Default Background Metadata?'),self)
        self.bgmeta.setToolTip(_("On each download, FanFicFare offers an option to Collect Metadata from sites in a Background process.<br />This returns control to you quicker while updating, but you won't be asked for username/passwords or if you are an adult--stories that need those will just fail.<br />Only available for Update/Overwrite of existing books in case URL given isn't canonical or matches to existing book by Title/Author."))
        self.bgmeta.setChecked(prefs['bgmeta'])
        horz.addWidget(self.bgmeta)

        self.l.addLayout(horz)

        cali_gb = groupbox = QGroupBox(_("Updating Calibre Options"))
        self.l = QVBoxLayout()
        groupbox.setLayout(self.l)

        self.deleteotherforms = QCheckBox(_('Delete other existing formats?'),self)
        self.deleteotherforms.setToolTip(_('Check this to automatically delete all other ebook formats when updating an existing book.\nHandy if you have both a Nook(epub) and Kindle(mobi), for example.'))
        self.deleteotherforms.setChecked(prefs['deleteotherforms'])
        self.l.addWidget(self.deleteotherforms)

        self.keeptags = QCheckBox(_('Keep Existing Tags when Updating Metadata?'),self)
        self.keeptags.setToolTip(_("Existing tags will be kept and any new tags added.\n%(cmplt)s and %(inprog)s tags will be still be updated, if known.\n%(lul)s tags will be updated if %(lus)s in %(is)s.\n(If Tags is set to 'New Only' in the Standard Columns tab, this has no effect.)")%no_trans)
        self.keeptags.setChecked(prefs['keeptags'])
        self.l.addWidget(self.keeptags)

        self.checkforseriesurlid = QCheckBox(_("Check for existing Series Anthology books?"),self)
        self.checkforseriesurlid.setToolTip(_("Check for existing Series Anthology books using each new story's series URL before downloading.\nOffer to skip downloading if a Series Anthology is found.\nDoesn't work when Collect Metadata in Background is selected."))
        self.checkforseriesurlid.setChecked(prefs['checkforseriesurlid'])
        self.l.addWidget(self.checkforseriesurlid)

        self.auto_reject_seriesurlid = QCheckBox(_("Reject Without Confirmation?"),self)
        self.auto_reject_seriesurlid.setToolTip(_("Automatically reject storys with existing Series Anthology books.\nOnly works if 'Check for existing Series Anthology books' is on.\nDoesn't work when Collect Metadata in Background is selected."))
        self.auto_reject_seriesurlid.setChecked(prefs['auto_reject_seriesurlid'])
        self.auto_reject_seriesurlid.setEnabled(self.checkforseriesurlid.isChecked())

        self.mark_series_anthologies = QCheckBox(_("Mark Matching Anthologies?"),self)
        self.mark_series_anthologies.setToolTip(_("Mark and show existing Series Anthology books when individual updates are skipped.\nOnly works if 'Check for existing Series Anthology books' is on.\nDoesn't work when Collect Metadata in Background is selected."))
        self.mark_series_anthologies.setChecked(prefs['mark_series_anthologies'])
        self.mark_series_anthologies.setEnabled(self.checkforseriesurlid.isChecked())

        def mark_anthologies():
            self.auto_reject_seriesurlid.setEnabled(self.checkforseriesurlid.isChecked())
            self.mark_series_anthologies.setEnabled(self.checkforseriesurlid.isChecked())
        self.checkforseriesurlid.stateChanged.connect(mark_anthologies)
        mark_anthologies()

        horz = QHBoxLayout()
        horz.addItem(QtGui.QSpacerItem(20, 1))
        vertright = QVBoxLayout()
        horz.addLayout(vertright)
        vertright.addWidget(self.auto_reject_seriesurlid)
        vertright.addWidget(self.mark_series_anthologies)
        self.l.addLayout(horz)

        self.checkforurlchange = QCheckBox(_("Check for changed Story URL?"),self)
        self.checkforurlchange.setToolTip(_("Warn you if an update will change the URL of an existing book(normally automatic and silent).\nURLs may be changed from http to https silently if the site changed."))
        self.checkforurlchange.setChecked(prefs['checkforurlchange'])
        self.l.addWidget(self.checkforurlchange)

        self.lookforurlinhtml = QCheckBox(_("Search inside ebooks for Story URL?"),self)
        self.lookforurlinhtml.setToolTip(_("Look for first valid story URL inside EPUB, ZIP(HTML) or TXT ebook formats if not found in metadata.\nSomewhat risky, could find wrong URL depending on ebook content."))
        self.lookforurlinhtml.setChecked(prefs['lookforurlinhtml'])
        self.l.addWidget(self.lookforurlinhtml)

        proc_gb = groupbox = QGroupBox(_("Post Processing Options"))
        self.l = QVBoxLayout()
        groupbox.setLayout(self.l)

        self.mark = QCheckBox(_("Mark added/updated books when finished?"),self)
        self.mark.setToolTip(_("Mark added/updated books when finished.  Use with option below.\nYou can also manually search for 'marked:fff_success'.\n'marked:fff_failed' and 'marked:fff_chapter_error' are also available, or search 'marked:fff' for all."))
        self.mark.setChecked(prefs['mark'])
        self.l.addWidget(self.mark)

        horz = QHBoxLayout()
        horz.addItem(QtGui.QSpacerItem(20, 1))
        self.l.addLayout(horz)

        self.mark_success = QCheckBox(_("Success"),self)
        self.mark_success.setToolTip(_("Mark successfully downloaded or updated books."))
        self.mark_success.setChecked(prefs['mark_success'])
        self.mark_success.setEnabled(self.checkforseriesurlid.isChecked())
        horz.addWidget(self.mark_success)

        self.mark_failed = QCheckBox(_("Failed"),self)
        self.mark_failed.setToolTip(_("Mark failed downloaded or updated books."))
        self.mark_failed.setChecked(prefs['mark_failed'])
        self.mark_failed.setEnabled(self.checkforseriesurlid.isChecked())
        horz.addWidget(self.mark_failed)

        self.mark_chapter_error = QCheckBox(_("Chapter Error"),self)
        self.mark_chapter_error.setToolTip(_("Mark downloaded or updated books with chapter errors (only when <i>continue_on_chapter_error:true</i>)."))
        self.mark_chapter_error.setChecked(prefs['mark_chapter_error'])
        self.mark_chapter_error.setEnabled(self.checkforseriesurlid.isChecked())
        horz.addWidget(self.mark_chapter_error)

        def mark_state():
            self.mark_success.setEnabled(self.mark.isChecked())
            self.mark_failed.setEnabled(self.mark.isChecked())
            self.mark_chapter_error.setEnabled(self.mark.isChecked())
        self.mark.stateChanged.connect(mark_state)
        mark_state()

        self.showmarked = QCheckBox(_("Show Marked books when finished?"),self)
        self.showmarked.setToolTip(_("Show Marked added/updated books only when finished.\nYou can also manually search for 'marked:fff_success'.\n'marked:fff_failed' and 'marked:fff_chapter_error' are also available, or search 'marked:fff' for all."))
        self.showmarked.setChecked(prefs['showmarked'])
        self.l.addWidget(self.showmarked)

        self.smarten_punctuation = QCheckBox(_('Smarten Punctuation (EPUB only)'),self)
        self.smarten_punctuation.setToolTip(_("Run Smarten Punctuation from Calibre's Polish Book feature on each EPUB download and update."))
        self.smarten_punctuation.setChecked(prefs['smarten_punctuation'])
        self.l.addWidget(self.smarten_punctuation)


        tooltip = _("Calculate Word Counts using Calibre internal methods.\n"
                    "Many sites include Word Count, but many do not.\n"
                    "This will count the words in each book and include it as if it came from the site.")
        horz = QHBoxLayout()
        label = QLabel(_('Calculate Word Count:'))
        label.setToolTip(tooltip)
        horz.addWidget(label)
        self.do_wordcount = QComboBox(self)
        for i in do_wordcount_order:
            self.do_wordcount.addItem(i)
        self.do_wordcount.setCurrentIndex(self.do_wordcount.findText(prefs_save_options[prefs['do_wordcount']]))
        self.do_wordcount.setToolTip(tooltip)
        label.setBuddy(self.do_wordcount)
        horz.addWidget(self.do_wordcount)
        self.l.addLayout(horz)


        self.autoconvert = QCheckBox(_("Automatically Convert new/update books?"),self)
        self.autoconvert.setToolTip(_("Automatically call calibre's Convert for new/update books.\nConverts to the current output format as chosen in calibre's\nPreferences->Behavior settings."))
        self.autoconvert.setChecked(prefs['autoconvert'])
        self.l.addWidget(self.autoconvert)

        gui_gb = groupbox = QGroupBox(_("GUI Options"))
        self.l = QVBoxLayout()
        groupbox.setLayout(self.l)

        self.urlsfromclip = QCheckBox(_('Take URLs from Clipboard?'),self)
        self.urlsfromclip.setToolTip(_('Prefill URLs from valid URLs in Clipboard when Adding New.'))
        self.urlsfromclip.setChecked(prefs['urlsfromclip'])
        self.l.addWidget(self.urlsfromclip)

        self.button_instantpopup = QCheckBox(_('FanFicFare button opens menu?'),self)
        self.button_instantpopup.setToolTip(_('The FanFicFare toolbar button will bring up the plugin menu.  If unchecked, it will <i>Download from URLs</i> or optionally Update, see below.'))
        self.button_instantpopup.setChecked(prefs['button_instantpopup'])
        self.l.addWidget(self.button_instantpopup)

        self.updatedefault = QCheckBox(_('Default to Update when books selected?'),self)
        self.updatedefault.setToolTip(_('The FanFicFare toolbar button will Update if books are selected.  If unchecked, it will always <i>Download from URLs</i>.'))
        self.updatedefault.setChecked(prefs['updatedefault'])
        self.updatedefault.setEnabled(not self.button_instantpopup.isChecked())
        self.button_instantpopup.stateChanged.connect(lambda x : self.updatedefault.setEnabled(not self.button_instantpopup.isChecked()))
        horz = QHBoxLayout()
        horz.addItem(QtGui.QSpacerItem(20, 1))
        horz.addWidget(self.updatedefault)
        self.l.addLayout(horz)

        self.adddialogstaysontop = QCheckBox(_("Keep 'Add New from URL(s)' dialog on top?"),self)
        self.adddialogstaysontop.setToolTip(_("Instructs the OS and Window Manager to keep the 'Add New from URL(s)'\ndialog on top of all other windows.  Useful for dragging URLs onto it."))
        self.adddialogstaysontop.setChecked(prefs['adddialogstaysontop'])
        self.l.addWidget(self.adddialogstaysontop)

        self.show_est_time = QCheckBox(_("Show estimated time left?"),self)
        self.show_est_time.setToolTip(_("When a Progress Bar is shown, show a rough estimate of the time left."))
        self.show_est_time.setChecked(prefs['show_est_time'])
        self.l.addWidget(self.show_est_time)

        misc_gb = groupbox = QGroupBox(_("Misc Options"))
        self.l = QVBoxLayout()
        groupbox.setLayout(self.l)

        self.injectseries = QCheckBox(_("Inject calibre Series when none found?"),self)
        self.injectseries.setToolTip(_("If no series is found, inject the calibre series (if there is one) so \nit appears on the FanFicFare title page(not cover)."))
        self.injectseries.setChecked(prefs['injectseries'])
        self.l.addWidget(self.injectseries)

        self.matchtitleauth = QCheckBox(_("Search by Title/Author(s) for If Story Already Exists?"),self)
        self.matchtitleauth.setToolTip(_("When checking <i>If Story Already Exists</i> FanFicFare will first match by URL Identifier.  But if not found, it can also search existing books by Title and Author(s)."))
        self.matchtitleauth.setChecked(prefs['matchtitleauth'])
        self.l.addWidget(self.matchtitleauth)

        rej_gb = groupbox = QGroupBox(_("Reject List"))
        self.l = QVBoxLayout()
        groupbox.setLayout(self.l)

        self.rejectlist = QPushButton(_('Edit Reject URL List'), self)
        self.rejectlist.setToolTip(_("Edit list of URLs FanFicFare will automatically Reject."))
        self.rejectlist.clicked.connect(self.show_rejectlist)
        self.l.addWidget(self.rejectlist)

        self.reject_urls = QPushButton(_('Add Reject URLs'), self)
        self.reject_urls.setToolTip(_("Add additional URLs to Reject as text."))
        self.reject_urls.clicked.connect(self.add_reject_urls)
        self.l.addWidget(self.reject_urls)

        self.reject_reasons = QPushButton(_('Edit Reject Reasons List'), self)
        self.reject_reasons.setToolTip(_("Customize the Reasons presented when Rejecting URLs"))
        self.reject_reasons.clicked.connect(self.show_reject_reasons)
        self.l.addWidget(self.reject_reasons)

        self.reject_always = QCheckBox(_('Reject Without Confirmation?'),self)
        self.reject_always.setToolTip(_("Always reject URLs on the Reject List without stopping and asking."))
        self.reject_always.setChecked(prefs['reject_always'])
        self.l.addWidget(self.reject_always)

        self.reject_delete_default = QCheckBox(_('Delete on Reject by Default?'),self)
        self.reject_delete_default.setToolTip(_("Should the checkbox to delete Rejected books be checked by default?"))
        self.reject_delete_default.setChecked(prefs['reject_delete_default'])
        self.l.addWidget(self.reject_delete_default)

        topl.addWidget(defs_gb)

        horz = QHBoxLayout()

        vertleft = QVBoxLayout()
        vertleft.addWidget(cali_gb)
        vertleft.addWidget(proc_gb)

        vertright = QVBoxLayout()
        vertright.addWidget(gui_gb)
        vertright.addWidget(misc_gb)
        vertright.addWidget(rej_gb)

        horz.addLayout(vertleft)
        horz.addLayout(vertright)

        topl.addLayout(horz)
        topl.insertStretch(-1)

    def set_collisions(self):
        prev=self.collision.currentText()
        self.collision.clear()
        for o in collision_order:
            if self.fileform.currentText() == 'epub' or o not in [UPDATE,UPDATEALWAYS]:
                self.collision.addItem(o)
        i = self.collision.findText(prev)
        if i > -1:
            self.collision.setCurrentIndex(i)

    def show_rejectlist(self):
        with busy_cursor():
            d = RejectListDialog(self,
                                 rejecturllist.get_list(),
                                 rejectreasons=rejecturllist.get_reject_reasons(),
                                 header=_("Edit Reject URLs List"),
                                 show_delete=False,
                                 show_all_reasons=False)
        d.exec_()
        if d.result() != d.Accepted:
            return
        with busy_cursor():
            rejecturllist.add(d.get_reject_list(),clear=True)

    def show_reject_reasons(self):
        d = EditTextDialog(self,
                           prefs['rejectreasons'],
                           icon=self.windowIcon(),
                           title=_("Reject Reasons"),
                           label=_("Customize Reject List Reasons"),
                           tooltip=_("Customize the Reasons presented when Rejecting URLs"),
                           save_size_name='fff:Reject List Reasons')
        d.exec_()
        if d.result() == d.Accepted:
            prefs['rejectreasons'] = d.get_plain_text()

    def add_reject_urls(self):
        d = EditTextDialog(self,
                           "http://example.com/story.php?sid=5,"+_("Reason why I rejected it")+"\nhttp://example.com/story.php?sid=6,"+_("Title by Author")+" - "+_("Reason why I rejected it"),
                           icon=self.windowIcon(),
                           title=_("Add Reject URLs"),
                           label=_("Add Reject URLs. Use: <b>http://...,note</b> or <b>http://...,title by author - note</b><br>Invalid story URLs will be ignored."),
                           tooltip=_("One URL per line:\n<b>http://...,note</b>\n<b>http://...,title by author - note</b>"),
                           rejectreasons=rejecturllist.get_reject_reasons(),
                           reasonslabel=_('Add this reason to all URLs added:'),
                           save_size_name='fff:Add Reject List')
        d.exec_()
        if d.result() == d.Accepted:
            rejecturllist.add_text(d.get_plain_text(),d.get_reason_text())

class PersonalIniTab(QWidget):

    def __init__(self, parent_dialog, plugin_action):
        self.parent_dialog = parent_dialog
        self.plugin_action = plugin_action
        QWidget.__init__(self)

        self.l = QVBoxLayout()
        self.setLayout(self.l)

        label = QLabel(_('These settings provide more detailed control over what metadata will be displayed inside the ebook as well as let you set %(isa)s and %(u)s/%(p)s for different sites.')%no_trans)
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)

        self.personalini = prefs['personal.ini']

        groupbox = QGroupBox(_("personal.ini"))
        vert = QVBoxLayout()
        groupbox.setLayout(vert)
        self.l.addWidget(groupbox)

        horz = QHBoxLayout()
        vert.addLayout(horz)
        self.ini_button = QPushButton(_('Edit personal.ini'), self)
        #self.ini_button.setToolTip(_("Edit personal.ini file."))
        self.ini_button.clicked.connect(self.add_ini_button)
        horz.addWidget(self.ini_button)

        label = QLabel(_("FanFicFare now includes find, color coding, and error checking for personal.ini editing.  Red generally indicates errors."))
        label.setWordWrap(True)
        horz.addWidget(label)

        vert.addSpacing(5)

        horz = QHBoxLayout()
        vert.addLayout(horz)
        self.ini_button = QPushButton(_('View "Safe" personal.ini'), self)
        #self.ini_button.setToolTip(_("Edit personal.ini file."))
        self.ini_button.clicked.connect(self.safe_ini_button)
        horz.addWidget(self.ini_button)

        label = QLabel(_("View your personal.ini with usernames and passwords removed.  For safely sharing your personal.ini settings with others."))
        label.setWordWrap(True)
        horz.addWidget(label)

        self.l.addSpacing(5)

        groupbox = QGroupBox(_("defaults.ini"))
        horz = QHBoxLayout()
        groupbox.setLayout(horz)
        self.l.addWidget(groupbox)

        view_label = _("View all of the plugin's configurable settings\nand their default settings.")
        self.defaults = QPushButton(_('View Defaults')+' (plugin-defaults.ini)', self)
        self.defaults.setToolTip(view_label)
        self.defaults.clicked.connect(self.show_defaults)
        horz.addWidget(self.defaults)

        label = QLabel(view_label)
        label.setWordWrap(True)
        horz.addWidget(label)

        self.l.addSpacing(5)

        groupbox = QGroupBox(_("Calibre Columns"))
        vert = QVBoxLayout()
        groupbox.setLayout(vert)
        self.l.addWidget(groupbox)

        horz = QHBoxLayout()
        vert.addLayout(horz)
        pass_label = _("If checked, when updating/overwriting an existing book, FanFicFare will have the Calibre Columns available to use in replace_metadata, title_page, etc.<br>Click the button below to see the Calibre Column names.")%no_trans
        self.cal_cols_pass_in = QCheckBox(_('Pass Calibre Columns into FanFicFare on Update/Overwrite')%no_trans,self)
        self.cal_cols_pass_in.setToolTip(pass_label)
        self.cal_cols_pass_in.setChecked(prefs['cal_cols_pass_in'])
        horz.addWidget(self.cal_cols_pass_in)

        label = QLabel(pass_label)
        label.setWordWrap(True)
        horz.addWidget(label)

        vert.addSpacing(5)

        horz = QHBoxLayout()
        vert.addLayout(horz)
        col_label = _("FanFicFare can pass the Calibre Columns into the download/update process.<br>This will show you the columns available by name.")
        self.showcalcols = QPushButton(_('Show Calibre Column Names'), self)
        self.showcalcols.setToolTip(col_label)
        self.showcalcols.clicked.connect(self.show_showcalcols)
        horz.addWidget(self.showcalcols)

        label = QLabel(col_label)
        label.setWordWrap(True)
        horz.addWidget(label)

        label = QLabel(_("Changes will only be saved if you click 'OK' to leave Customize FanFicFare."))
        label.setWordWrap(True)
        self.l.addWidget(label)

        self.l.insertStretch(-1)

    def show_defaults(self):
        IniTextDialog(self,
                       get_resources('plugin-defaults.ini').decode('utf-8'),
                       icon=self.windowIcon(),
                       title=_('Plugin Defaults'),
                       label=_("Plugin Defaults (%s) (Read-Only)")%'plugin-defaults.ini',
                       use_find=True,
                       read_only=True,
                       save_size_name='fff:defaults.ini').exec_()

    def safe_ini_button(self):
        personalini = re.sub(r'((username|password) *[=:]).*$',r'\1XXXXXXXX',self.personalini,flags=re.MULTILINE)

        d = EditTextDialog(self,
                           personalini,
                           icon=self.windowIcon(),
                           title=_("View 'Safe' personal.ini"),
                           label=_("View your personal.ini with usernames and passwords removed.  For safely sharing your personal.ini settings with others."),
                           save_size_name='fff:safe personal.ini',
                           read_only=True)
        d.exec_()

    def add_ini_button(self):
        d = IniTextDialog(self,
                           self.personalini,
                           icon=self.windowIcon(),
                           title=_("Edit personal.ini"),
                           label=_("Edit personal.ini"),
                           use_find=True,
                           save_size_name='fff:personal.ini')
        d.exec_()
        if d.result() == d.Accepted:
            self.personalini = d.get_plain_text()

    def show_showcalcols(self):
        lines=[]#[('calibre_std_user_categories',_('User Categories'))]
        for k,f in six.iteritems(field_metadata):
            if f['name'] and k not in STD_COLS_SKIP: # only if it has a human readable name.
                lines.append(('calibre_std_'+k,f['name']))

        for k, column in six.iteritems(self.plugin_action.gui.library_view.model().custom_columns):
            if k != prefs['savemetacol']:
                # custom always have name.
                lines.append(('calibre_cust_'+k[1:],column['name']))

        lines.sort() # sort by key.

        EditTextDialog(self,
                       '\n'.join(['%s (%s)'%(l,k) for (k,l) in lines]),
                       icon=self.windowIcon(),
                       title=_('Calibre Column Entry Names'),
                       label=_('Label (entry_name)'),
                       read_only=True,
                       save_size_name='fff:showcalcols').exec_()

class ReadingListTab(QWidget):

    def __init__(self, parent_dialog, plugin_action):
        self.parent_dialog = parent_dialog
        self.plugin_action = plugin_action
        QWidget.__init__(self)

        self.l = QVBoxLayout()
        self.setLayout(self.l)

        try:
            rl_plugin = plugin_action.gui.iactions['Reading List']
            reading_lists = rl_plugin.get_list_names()
        except KeyError:
            reading_lists= []

        label = QLabel(_('These settings provide integration with the %(rl)s Plugin.  %(rl)s can automatically send to devices and change custom columns.  You have to create and configure the lists in %(rl)s to be useful.')%no_trans)
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)

        self.addtolists = QCheckBox(_('Add new/updated stories to "Send to Device" Reading List(s).'),self)
        self.addtolists.setToolTip(_('Automatically add new/updated stories to these lists in the %(rl)s plugin.')%no_trans)
        self.addtolists.setChecked(prefs['addtolists'])
        self.l.addWidget(self.addtolists)

        horz = QHBoxLayout()
        label = QLabel(_('"Send to Device" Reading Lists'))
        label.setToolTip(_("When enabled, new/updated stories will be automatically added to these lists."))
        horz.addWidget(label)
        self.send_lists_box = EditWithComplete(self)
        self.send_lists_box.setToolTip(_("When enabled, new/updated stories will be automatically added to these lists."))
        self.send_lists_box.update_items_cache(reading_lists)
        self.send_lists_box.setText(prefs['send_lists'])
        horz.addWidget(self.send_lists_box)
        self.send_lists_box.setCursorPosition(0)
        self.l.addLayout(horz)

        self.addtoreadlists = QCheckBox(_('Add new/updated stories to "To Read" Reading List(s).'),self)
        self.addtoreadlists.setToolTip(_('Automatically add new/updated stories to these lists in the %(rl)s plugin.\nAlso offers menu option to remove stories from the "To Read" lists.')%no_trans)
        self.addtoreadlists.setChecked(prefs['addtoreadlists'])
        self.l.addWidget(self.addtoreadlists)

        horz = QHBoxLayout()
        label = QLabel(_('"To Read" Reading Lists'))
        label.setToolTip(_("When enabled, new/updated stories will be automatically added to these lists."))
        horz.addWidget(label)
        self.read_lists_box = EditWithComplete(self)
        self.read_lists_box.setToolTip(_("When enabled, new/updated stories will be automatically added to these lists."))
        self.read_lists_box.update_items_cache(reading_lists)
        self.read_lists_box.setText(prefs['read_lists'])
        horz.addWidget(self.read_lists_box)
        self.read_lists_box.setCursorPosition(0)
        self.l.addLayout(horz)

        self.addtolistsonread = QCheckBox(_('Add stories back to "Send to Device" Reading List(s) when marked "Read".'),self)
        self.addtolistsonread.setToolTip(_('Menu option to remove from "To Read" lists will also add stories back to "Send to Device" Reading List(s)'))
        self.addtolistsonread.setChecked(prefs['addtolistsonread'])
        self.l.addWidget(self.addtolistsonread)

        self.autounnew = QCheckBox(_('Automatically run Remove "New" Chapter Marks when marking books "Read".'),self)
        self.autounnew.setToolTip(_('Menu option to remove from "To Read" lists will also remove "(new)" chapter marks created by personal.ini <i>mark_new_chapters</i> setting.'))
        self.autounnew.setChecked(prefs['autounnew'])
        self.l.addWidget(self.autounnew)

        self.l.insertStretch(-1)

class CalibreCoverTab(QWidget):

    def __init__(self, parent_dialog, plugin_action):
        self.parent_dialog = parent_dialog
        self.plugin_action = plugin_action
        QWidget.__init__(self)

        self.gencov_elements=[] ## used to disable/enable when gen
                                ## cover is off/on.  This is more
                                ## about being a visual cue than real
                                ## necessary function.

        topl = self.l = QVBoxLayout()
        self.setLayout(self.l)

        try:
            gc_plugin = plugin_action.gui.iactions['Generate Cover']
            gc_settings = gc_plugin.get_saved_setting_names()
        except KeyError:
            gc_settings= []


        label = QLabel(_("The Calibre cover image for a downloaded book can come"
                         " from the story site(if EPUB and images are enabled), or"
                         " from either Calibre's built-in random cover generator or"
                         " the %(gc)s plugin.")%no_trans)
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)

        tooltip = _("Update Calibre book cover image from EPUB when Calibre metadata is updated.\n"
                    "Doesn't go looking for new images on 'Update Calibre Metadata Only'.\n"
                    "Cover in EPUB could be from site or previously injected into the EPUB.\n"
                    "This comes before Generate Cover so %(gc)s(Plugin) use the image if configured to.")%no_trans
        horz = QHBoxLayout()
        label = QLabel(_('Update Calibre Cover (from EPUB):'))
        label.setToolTip(tooltip)
        horz.addWidget(label)
        self.updatecalcover = QComboBox(self)
        for i in updatecalcover_order:
            self.updatecalcover.addItem(i)
        # back compat.  If has own value, use.
        if prefs['updatecalcover']:
            self.updatecalcover.setCurrentIndex(self.updatecalcover.findText(prefs_save_options[prefs['updatecalcover']]))
        elif prefs['updatecover']: # doesn't have own val, set YES if old value set.
            self.updatecalcover.setCurrentIndex(self.updatecalcover.findText(prefs_save_options[SAVE_YES]))
        else: # doesn't have own value, old value not set, NO.
            self.updatecalcover.setCurrentIndex(self.updatecalcover.findText(prefs_save_options[SAVE_NO]))
        self.updatecalcover.setToolTip(tooltip)
        label.setBuddy(self.updatecalcover)
        horz.addWidget(self.updatecalcover)
        self.l.addLayout(horz)

        self.covernewonly = QCheckBox(_("Set Calibre Cover Only for New Books"),self)
        self.covernewonly.setToolTip(_("Set the Calibre cover from EPUB only for new\nbooks, not updates to existing books."))
        self.covernewonly.setChecked(prefs['covernewonly'])
        horz = QHBoxLayout()
        horz.addItem(QtGui.QSpacerItem(20, 1))
        horz.addWidget(self.covernewonly)
        self.l.addLayout(horz)
        self.l.addSpacing(5)

        tooltip = _("Generate a Calibre book cover image when Calibre metadata is updated.<br />"
                    "Note that %(gc)s(Plugin) will only run if there is a %(gc)s setting configured below for Default or the appropriate site.")%no_trans
        horz = QHBoxLayout()
        label = QLabel(_('Generate Calibre Cover:'))
        label.setToolTip(tooltip)
        horz.addWidget(label)
        self.gencalcover = QComboBox(self)
        for i in gencalcover_order:
            self.gencalcover.addItem(i)
        self.gencalcover.setCurrentIndex(self.gencalcover.findText(prefs_save_options[prefs['gencalcover']]))

        self.gencalcover.setToolTip(tooltip)
        label.setBuddy(self.gencalcover)
        horz.addWidget(self.gencalcover)
        self.l.addLayout(horz)
        self.gencalcover.currentIndexChanged.connect(self.endisable_elements)

        horz = QHBoxLayout()
        horz.addItem(QtGui.QSpacerItem(20, 1))
        vert = QVBoxLayout()
        horz.addLayout(vert)
        self.l.addLayout(horz)

        self.gcnewonly = QCheckBox(_("Generate Covers Only for New Books")%no_trans,self)
        self.gcnewonly.setToolTip(_("Default is to generate a cover any time the calibre metadata is"
                                    " updated.<br />Used for both Calibre and Plugin generated covers."))
        self.gcnewonly.setChecked(prefs['gcnewonly'])
        vert.addWidget(self.gcnewonly)
        self.gencov_elements.append(self.gcnewonly)

        self.gc_polish_cover = QCheckBox(_("Inject/update the generated cover inside EPUB"),self)
        self.gc_polish_cover.setToolTip(_("Calibre's Polish feature will be used to inject or update the generated"
                                          " cover into the EPUB ebook file.<br />Used for both Calibre and Plugin generated covers."))
        self.gc_polish_cover.setChecked(prefs['gc_polish_cover'])
        vert.addWidget(self.gc_polish_cover)
        self.gencov_elements.append(self.gc_polish_cover)

        # can't be local or it's destroyed when __init__ is done and
        # connected things don't fire.
        self.gencov_rdgrp = QButtonGroup()
        self.gencov_gb = QGroupBox()
        horz = QHBoxLayout()
        self.gencov_gb.setLayout(horz)

        self.plugin_gen_cover = QRadioButton(_('Plugin %(gc)s')%no_trans,self)
        self.plugin_gen_cover.setToolTip(_("Use the %(gc)s plugin to create covers.<br>"
                                           "Requires that you have the the %(gc)s plugin installed.<br>"
                                           "Additional settings are below."%no_trans))
        self.gencov_rdgrp.addButton(self.plugin_gen_cover)
        # always, new only, when no cover from site, inject yes/no...
        self.plugin_gen_cover.setChecked(prefs['plugin_gen_cover'])
        horz.addWidget(self.plugin_gen_cover)
        self.gencov_elements.append(self.plugin_gen_cover)

        self.calibre_gen_cover = QRadioButton(_('Calibre Generate Cover'),self)
        self.calibre_gen_cover.setToolTip(_("Call Calibre's Edit Metadata Generate cover"
                                            " feature to create a random cover each time"
                                            " a story is downloaded or updated.<br />"
                                            "Right click or long click the 'Generate cover'"
                                            " button in Calibre's Edit Metadata to customize."))
        self.gencov_rdgrp.addButton(self.calibre_gen_cover)
        # always, new only, when no cover from site, inject yes/no...
        self.calibre_gen_cover.setChecked(prefs['calibre_gen_cover'])
        horz.addWidget(self.calibre_gen_cover)
        self.gencov_elements.append(self.calibre_gen_cover)

        #self.l.addLayout(horz)
        self.l.addWidget(self.gencov_gb)

        self.gcp_gb = QGroupBox(_("%(gc)s(Plugin) Settings")%no_trans)
        topl.addWidget(self.gcp_gb)
        self.l = QVBoxLayout()
        self.gcp_gb.setLayout(self.l)
        self.gencov_elements.append(self.gcp_gb)

        self.gencov_rdgrp.buttonClicked.connect(self.endisable_elements)

        label = QLabel(_('The %(gc)s plugin can create cover images for books using various metadata (including existing cover image).  If you have %(gc)s installed, FanFicFare can run %(gc)s on new downloads and metadata updates.  Pick a %(gc)s setting by site and/or one to use by Default.')%no_trans)
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)

        scrollable = QScrollArea()
        scrollcontent = QWidget()
        scrollable.setWidget(scrollcontent)
        scrollable.setWidgetResizable(True)
        self.l.addWidget(scrollable)

        self.sl = QVBoxLayout()
        scrollcontent.setLayout(self.sl)

        self.gc_dropdowns = {}

        sitelist = getSiteSections()
        sitelist.sort()
        sitelist.insert(0,_("Default"))
        for site in sitelist:
            horz = QHBoxLayout()
            label = QLabel(site)
            if site == _("Default"):
                s = _("On Metadata update, run %(gc)s with this setting, if there isn't a more specific setting below.")%no_trans
            else:
                no_trans['site']=site # not ideal, but, meh.
                s = _("On Metadata update, run %(gc)s with this setting for %(site)s stories.")%no_trans

            label.setToolTip(s)
            horz.addWidget(label)
            dropdown = QComboBox(self)
            dropdown.setToolTip(s)
            dropdown.addItem('','none')
            for setting in gc_settings:
                dropdown.addItem(setting,setting)
            if site == _("Default"):
                self.gc_dropdowns["Default"] = dropdown
                if 'Default' in prefs['gc_site_settings']:
                    dropdown.setCurrentIndex(dropdown.findData(prefs['gc_site_settings']['Default']))
            else:
                self.gc_dropdowns[site] = dropdown
            if site in prefs['gc_site_settings']:
                dropdown.setCurrentIndex(dropdown.findData(prefs['gc_site_settings'][site]))

            horz.addWidget(dropdown)
            self.sl.addLayout(horz)

        self.sl.insertStretch(-1)

        self.allow_gc_from_ini = QCheckBox(_('Allow %(gcset)s from %(pini)s to override')%no_trans,self)
        self.allow_gc_from_ini.setToolTip(_("The %(pini)s parameter %(gcset)s allows you to choose a %(gc)s setting based on metadata"
                                            " rather than site, but it's much more complex.<br />%(gcset)s is ignored when this is off.")%no_trans)
        self.allow_gc_from_ini.setChecked(prefs['allow_gc_from_ini'])
        self.l.addWidget(self.allow_gc_from_ini)

        # keep at end.
        self.endisable_elements()

    def endisable_elements(self,button=None):
        "Clearing house function for setting elements of Calibre"
        "Cover tab enabled/disabled depending on all factors."

        ## First, cover gen on/off
        for e in self.gencov_elements:
            e.setEnabled(prefs_save_options[unicode(self.gencalcover.currentText())] != SAVE_NO)

        # next, disable plugin settings when using calibre gen cov.
        if not self.plugin_gen_cover.isChecked():
            self.gcp_gb.setEnabled(False)

        # disable (but not enable) unsupported options.
        if not HAS_CALGC:
            self.calibre_gen_cover.setEnabled(False)
        if not 'Generate Cover' in self.plugin_action.gui.iactions:
            self.plugin_gen_cover.setEnabled(False)
            self.gcp_gb.setEnabled(False)


class CountPagesTab(QWidget):

    def __init__(self, parent_dialog, plugin_action):
        self.parent_dialog = parent_dialog
        self.plugin_action = plugin_action
        QWidget.__init__(self)

        self.l = QVBoxLayout()
        self.setLayout(self.l)

        label = QLabel(_('These settings provide integration with the %(cp)s Plugin.  %(cp)s can automatically update custom columns with page, word and reading level statistics.  You have to create and configure the columns in %(cp)s first.')%no_trans)
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)

        label = QLabel(_('If any of the settings below are checked, when stories are added or updated, the %(cp)s Plugin will be called to update the checked statistics.')%no_trans)
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)

        # the same for all settings.  Mostly.
        tooltip = _('Which column and algorithm to use are configured in %(cp)s.')%no_trans
        # 'PageCount', 'WordCount', 'FleschReading', 'FleschGrade', 'GunningFog'
        self.pagecount = QCheckBox('Page Count',self)
        self.pagecount.setToolTip(tooltip)
        self.pagecount.setChecked('PageCount' in prefs['countpagesstats'])
        self.l.addWidget(self.pagecount)

        horz = QHBoxLayout()

        self.wordcount = QCheckBox('Word Count',self)
        self.wordcount.setToolTip(tooltip+"\n"+_('Will overwrite word count from FanFicFare metadata if set to update the same custom column.'))
        self.wordcount.setChecked('WordCount' in prefs['countpagesstats'])
        horz.addWidget(self.wordcount)

        self.wordcountmissing = QCheckBox('Only if Word Count is Missing in FanFicFare Metadata',self)
        self.wordcountmissing.setToolTip(_("Only run Count Page's Word Count if checked <i>and</i> FanFicFare metadata doesn't already have a word count.  If this is used with one of the other Page Counts, the Page Count plugin will be called twice."))
        self.wordcountmissing.setChecked(prefs['wordcountmissing'])
        self.wordcountmissing.setEnabled(self.wordcount.isChecked())
        horz.addWidget(self.wordcountmissing)

        self.wordcount.stateChanged.connect(lambda x : self.wordcountmissing.setEnabled(self.wordcount.isChecked()))

        self.l.addLayout(horz)

        self.fleschreading = QCheckBox('Flesch Reading Ease',self)
        self.fleschreading.setToolTip(tooltip)
        self.fleschreading.setChecked('FleschReading' in prefs['countpagesstats'])
        self.l.addWidget(self.fleschreading)

        self.fleschgrade = QCheckBox('Flesch-Kincaid Grade Level',self)
        self.fleschgrade.setToolTip(tooltip)
        self.fleschgrade.setChecked('FleschGrade' in prefs['countpagesstats'])
        self.l.addWidget(self.fleschgrade)

        self.gunningfog = QCheckBox('Gunning Fog Index',self)
        self.gunningfog.setToolTip(tooltip)
        self.gunningfog.setChecked('GunningFog' in prefs['countpagesstats'])
        self.l.addWidget(self.gunningfog)

        self.l.insertStretch(-1)

class OtherTab(QWidget):

    def __init__(self, parent_dialog, plugin_action):
        self.parent_dialog = parent_dialog
        self.plugin_action = plugin_action
        QWidget.__init__(self)

        self.l = QVBoxLayout()
        self.setLayout(self.l)

        label = QLabel(_("These controls aren't plugin settings as such, but convenience buttons for setting Keyboard shortcuts and getting all the FanFicFare confirmation dialogs back again."))
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)

        keyboard_shortcuts_button = QPushButton(_('Keyboard shortcuts...'), self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(parent_dialog.edit_shortcuts)
        self.l.addWidget(keyboard_shortcuts_button)

        reset_confirmation_button = QPushButton(_('Reset disabled &confirmation dialogs'), self)
        reset_confirmation_button.setToolTip(_('Reset all show me again dialogs for the FanFicFare plugin'))
        reset_confirmation_button.clicked.connect(self.reset_dialogs)
        self.l.addWidget(reset_confirmation_button)

        view_prefs_button = QPushButton(_('&View library preferences...'), self)
        view_prefs_button.setToolTip(_('View data stored in the library database for this plugin'))
        view_prefs_button.clicked.connect(self.view_prefs)
        self.l.addWidget(view_prefs_button)

        self.l.insertStretch(-1)

    def reset_dialogs(self):
        for key in dynamic.keys():
            if key.startswith('fff_') and dynamic[key] is False:
                dynamic[key] = True
        info_dialog(self, _('Done'),
                    _('Confirmation dialogs have all been reset'),
                    show=True,
                    show_copy_button=False)

    def view_prefs(self):
        d = PrefsViewerDialog(self.plugin_action.gui, PREFS_NAMESPACE)
        d.exec_()

permitted_values = {
    'int' : ['numWords','numChapters'],
    'float' : ['numWords','numChapters'],
    'bool' : ['status-C','status-I'],
    'datetime' : ['datePublished', 'dateUpdated', 'dateCreated'],
    'series' : ['series'],
    'enumeration' : ['category',
                     'genre',
                     'language',
                     'series',
                     'characters',
                     'ships',
                     'status',
                     'datePublished',
                     'dateUpdated',
                     'dateCreated',
                     'rating',
                     'warnings',
                     'numChapters',
                     'numWords',
                     'site',
                     'publisher',
                     'storyId',
                     'authorId',
                     'extratags',
                     'title',
                     'storyUrl',
                     'description',
                     'author',
                     'authorUrl',
                     'formatname',
                     'version'
                     #,'formatext'   # not useful information.
                     #,'siteabbrev'
                     ]
    }
# no point copying the whole list.
permitted_values['text'] = permitted_values['enumeration']
permitted_values['comments'] = permitted_values['enumeration']

titleLabels = {
    'category':_('Category'),
    'genre':_('Genre'),
    'language':_('Language'),
    'status':_('Status'),
    'status-C':_('Status:%(cmplt)s')%no_trans,
    'status-I':_('Status:%(inprog)s')%no_trans,
    'series':_('Series'),
    'characters':_('Characters'),
    'ships':_('Relationships'),
    'datePublished':_('Published'),
    'dateUpdated':_('Updated'),
    'dateCreated':_('Created'),
    'rating':_('Rating'),
    'warnings':_('Warnings'),
    'numChapters':_('Chapters'),
    'numWords':_('Words'),
    'site':_('Site'),
    'publisher':_('Publisher'),
    'storyId':_('Story ID'),
    'authorId':_('Author ID'),
    'extratags':_('Extra Tags'),
    'title':_('Title'),
    'storyUrl':_('Story URL'),
    'description':_('Description'),
    'author':_('Author'),
    'authorUrl':_('Author URL'),
    'formatname':_('File Format'),
    'formatext':_('File Extension'),
    'siteabbrev':_('Site Abbrev'),
    'version':_('FanFicFare Version')
    }

class CustomColumnsTab(QWidget):

    def __init__(self, parent_dialog, plugin_action):
        self.parent_dialog = parent_dialog
        self.plugin_action = plugin_action
        QWidget.__init__(self)

        ## sort by visible Column Name (vs #name)
        custom_columns = sorted(self.plugin_action.gui.library_view.model().custom_columns.items(), key=lambda x: x[1]['name'])

        self.l = QVBoxLayout()
        self.setLayout(self.l)

        label = QLabel(_("If you have custom columns defined, they will be listed below.  Choose a metadata value type to fill your columns automatically."))
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)

        self.custcol_dropdowns = {}
        self.custcol_newonlycheck = {}

        scrollable = QScrollArea()
        scrollcontent = QWidget()
        scrollable.setWidget(scrollcontent)
        scrollable.setWidgetResizable(True)
        self.l.addWidget(scrollable)

        self.sl = QVBoxLayout()
        scrollcontent.setLayout(self.sl)

        for key, column in custom_columns:

            if column['datatype'] in permitted_values:
                # print("\n============== %s ===========\n"%key)
                # for (k,v) in column.iteritems():
                #     print("column['%s'] => %s"%(k,v))
                horz = QHBoxLayout()
                # label = QLabel(column['name'])
                label = QLabel('%s(%s)'%(column['name'],key))
                label.setToolTip(_("Update this %s column(%s) with...")%(key,column['datatype']))
                horz.addWidget(label)
                dropdown = QComboBox(self)
                dropdown.addItem('','none')
                for md in permitted_values[column['datatype']]:
                    dropdown.addItem(titleLabels[md],md)
                self.custcol_dropdowns[key] = dropdown
                if key in prefs['custom_cols']:
                    dropdown.setCurrentIndex(dropdown.findData(prefs['custom_cols'][key]))
                if column['datatype'] == 'enumeration':
                    dropdown.setToolTip(_("Metadata values valid for this type of column.")+"\n"+_("Values that aren't valid for this enumeration column will be ignored."))
                else:
                    dropdown.setToolTip(_("Metadata values valid for this type of column."))
                horz.addWidget(dropdown)

                newonlycheck = QCheckBox(_("New Only"),self)
                newonlycheck.setToolTip(_("Write to %s(%s) only for new\nbooks, not updates to existing books.")%(column['name'],key))
                self.custcol_newonlycheck[key] = newonlycheck
                if key in prefs['custom_cols_newonly']:
                    newonlycheck.setChecked(prefs['custom_cols_newonly'][key])
                horz.addWidget(newonlycheck)

                self.sl.addLayout(horz)

        self.sl.insertStretch(-1)

        self.l.addSpacing(5)
        self.allow_custcol_from_ini = QCheckBox(_('Allow %(ccset)s from %(pini)s to override')%no_trans,self)
        self.allow_custcol_from_ini.setToolTip(_("The %(pini)s parameter %(ccset)s allows you to set custom columns to site specific values that aren't common to all sites.<br />%(ccset)s is ignored when this is off.")%no_trans)
        self.allow_custcol_from_ini.setChecked(prefs['allow_custcol_from_ini'])
        self.l.addWidget(self.allow_custcol_from_ini)

        label = QLabel(_("Special column:"))
        label.setWordWrap(True)
        self.l.addWidget(label)

        horz = QHBoxLayout()
        label = QLabel(_("Update/Overwrite Error Column:"))
        tooltip=_("When an update or overwrite of an existing story fails, record the reason in this column.\n(Text and Long Text columns only.)")
        label.setToolTip(tooltip)
        horz.addWidget(label)

        self.errorcol = QComboBox(self)
        self.errorcol.setToolTip(tooltip)
        self.errorcol.addItem('','none')
        for key, column in custom_columns:
            if column['datatype'] in ('text','comments'):
                self.errorcol.addItem(column['name'],key)
        self.errorcol.setCurrentIndex(self.errorcol.findData(prefs['errorcol']))
        horz.addWidget(self.errorcol)

        self.save_all_errors = QCheckBox(_('Save All Errors'),self)
        self.save_all_errors.setToolTip(_('If unchecked, these errors will not be saved: %s')%(
                '\n'+
                '\n'.join((_("Not Overwriting, web site is not newer."),
                           _("Already contains %d chapters.").replace('%d','X')))))
        self.save_all_errors.setChecked(prefs['save_all_errors'])
        horz.addWidget(self.save_all_errors)

        self.l.addLayout(horz)

        horz = QHBoxLayout()
        label = QLabel(_("Saved Metadata Column:"))
        tooltip=_("If set, FanFicFare will save a copy of all its metadata in this column when the book is downloaded or updated.<br/>The metadata from this column can later be used to update custom columns without having to request the metadata from the server again.<br/>(Long Text columns only.)")
        label.setToolTip(tooltip)
        horz.addWidget(label)
        self.savemetacol = QComboBox(self)
        self.savemetacol.setToolTip(tooltip)
        self.savemetacol.addItem('','')
        for key, column in custom_columns:
            if column['datatype'] in ('comments'):
                self.savemetacol.addItem(column['name'],key)
        self.savemetacol.setCurrentIndex(self.savemetacol.findData(prefs['savemetacol']))
        horz.addWidget(self.savemetacol)

        label = QLabel('')
        horz.addWidget(label) # empty spacer for alignment with error column line.

        self.l.addLayout(horz)

        horz = QHBoxLayout()
        label = QLabel(_("Last Checked Column:"))
        tooltip=_("Record the last time FanFicFare updated or checked for updates.\n(Date columns only.)")
        label.setToolTip(tooltip)
        horz.addWidget(label)

        self.lastcheckedcol = QComboBox(self)
        self.lastcheckedcol.setToolTip(tooltip)
        self.lastcheckedcol.addItem('','none')
        ## sort by visible Column Name (vs #name)
        for key, column in custom_columns:
            if column['datatype'] == 'datetime':
                self.lastcheckedcol.addItem(column['name'],key)
        self.lastcheckedcol.setCurrentIndex(self.lastcheckedcol.findData(prefs['lastcheckedcol']))
        horz.addWidget(self.lastcheckedcol)

        label = QLabel('')
        horz.addWidget(label) # empty spacer for alignment with error column line.

        self.l.addLayout(horz)


class StandardColumnsTab(QWidget):

    def __init__(self, parent_dialog, plugin_action):
        self.parent_dialog = parent_dialog
        self.plugin_action = plugin_action
        QWidget.__init__(self)

        columns=OrderedDict()

        columns["title"]=_("Title")
        columns["authors"]=_("Author(s)")
        columns["publisher"]=_("Publisher")
        columns["tags"]=_("Tags")
        columns["languages"]=_("Languages")
        columns["pubdate"]=_("Published Date")
        columns["timestamp"]=_("Date")
        columns["comments"]=_("Comments")
        columns["series"]=_("Series")
        columns["identifiers"]=_("Ids(url id only)")

        self.l = QVBoxLayout()
        self.setLayout(self.l)

        label = QLabel(_("The standard calibre metadata columns are listed below.  You may choose whether FanFicFare will fill each column automatically on updates or only for new books."))
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)

        self.stdcol_newonlycheck = {}

        rows=[]
        for key, column in six.iteritems(columns):
            row = []
            rows.append(row)
            label = QLabel(column)
            #label.setToolTip("Update this %s column(%s) with..."%(key,column['datatype']))
            row.append(label)

            newonlycheck = QCheckBox(_("New Only"),self)
            newonlycheck.setToolTip(_("Write to %s only for new\nbooks, not updates to existing books.")%column)
            self.stdcol_newonlycheck[key] = newonlycheck
            if key in prefs['std_cols_newonly']:
                newonlycheck.setChecked(prefs['std_cols_newonly'][key])
            row.append(newonlycheck)

            if key == 'title':
                self.suppresstitlesort = QCheckBox(_('Force Title into Title Sort?'),self)
                self.suppresstitlesort.setToolTip(_("If checked, the title as given will be used for the Title Sort, too.\nIf not checked, calibre will apply it's built in algorithm which makes 'The Title' sort as 'Title, The', etc."))
                self.suppresstitlesort.setChecked(prefs['suppresstitlesort'])
                row.append(self.suppresstitlesort)
                self.titlecase = QCheckBox(_('Fix Title Case?'),self)
                self.titlecase.setToolTip(_("If checked, Calibre's routine for correcting the capitalization of title will be applied.")
                                          +"\n"+_("This effects Calibre metadata only, not FanFicFare metadata in title page."))
                self.titlecase.setChecked(prefs['titlecase'])
                row.append(self.titlecase)
            elif key == 'authors':
                self.suppressauthorsort = QCheckBox(_('Force Author into Author Sort?'),self)
                self.suppressauthorsort.setToolTip(_("If checked, the author(s) as given will be used for the Author Sort, too.\nIf not checked, calibre will apply it's built in algorithm which makes 'Bob Smith' sort as 'Smith, Bob', etc."))
                self.suppressauthorsort.setChecked(prefs['suppressauthorsort'])
                row.append(self.suppressauthorsort)
                self.authorcase = QCheckBox(_('Fix Author Case?'),self)
                self.authorcase.setToolTip(_("If checked, Calibre's routine for correcting the capitalization of author names will be applied.")
                                          +"\n"+_("Calibre remembers all authors in the library; changing the author case on one book will effect all books by that author.")
                                          +"\n"+_("This effects Calibre metadata only, not FanFicFare metadata in title page."))
                self.authorcase.setChecked(prefs['authorcase'])
                row.append(self.authorcase)
            elif key == 'series':
                self.setanthologyseries = QCheckBox(_("Set 'Series [0]' for New Anthologies?"),self)
                self.setanthologyseries.setToolTip(_("If checked, the Series column will be set to 'Series Name [0]' when an Anthology for a series is first created."))
                self.setanthologyseries.setChecked(prefs['setanthologyseries'])
                row.append(self.setanthologyseries)

        grid = QGridLayout()
        for rownum, row in enumerate(rows):
            for colnum, col in enumerate(row):
                grid.addWidget(col,rownum,colnum)
        self.l.addLayout(grid)

        self.l.addSpacing(5)
        label = QLabel(_("Other Standard Column Options"))
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)

        self.set_author_url = QCheckBox(_('Set Calibre Author URL'),self)
        self.set_author_url.setToolTip(_("Set Calibre Author URL to Author's URL on story site."))
        self.set_author_url.setChecked(prefs['set_author_url'])
        self.l.addWidget(self.set_author_url)

        self.includecomments = QCheckBox(_("Include Books' Comments in Anthology Comments?"),self)
        self.includecomments.setToolTip(_('''Include all the merged books' comments in the new book's comments.
Default is a list of included titles only.'''))
        self.includecomments.setChecked(prefs['includecomments'])
        self.l.addWidget(self.includecomments)

        self.anth_comments_newonly = QCheckBox(_("Set Anthology Comments only for new books"),self)
        self.anth_comments_newonly.setToolTip(_("Comments will only be set for New Anthologies, not updates.\nThat way comments you set manually are retained."))
        self.anth_comments_newonly.setChecked(prefs['anth_comments_newonly'])
        self.l.addWidget(self.anth_comments_newonly)

        self.l.insertStretch(-1)

class ImapTab(QWidget):

    def __init__(self, parent_dialog, plugin_action):
        self.parent_dialog = parent_dialog
        self.plugin_action = plugin_action
        QWidget.__init__(self)

        self.l = QGridLayout()
        self.setLayout(self.l)
        row=0

        label = QLabel(_('These settings will allow FanFicFare to fetch story URLs from your email account.  It will only look for story URLs in unread emails in the folder specified below.'))
        label.setWordWrap(True)
        self.l.addWidget(label,row,0,1,-1)
        row+=1

        label = QLabel(_('IMAP Server Name'))
        tooltip = _("Name of IMAP server--must allow IMAP4 with SSL.  Eg: imap.gmail.com")
        label.setToolTip(tooltip)
        self.l.addWidget(label,row,0)
        self.imapserver = QLineEdit(self)
        self.imapserver.setToolTip(tooltip)
        self.imapserver.setText(prefs['imapserver'])
        self.l.addWidget(self.imapserver,row,1)
        row+=1

        label = QLabel(_('IMAP User Name'))
        tooltip = _("Name of IMAP user.  Eg: yourname@gmail.com\nNote that Gmail accounts need to have IMAP enabled in Gmail Settings first.")
        label.setToolTip(tooltip)
        self.l.addWidget(label,row,0)
        self.imapuser = QLineEdit(self)
        self.imapuser.setToolTip(tooltip)
        self.imapuser.setText(prefs['imapuser'])
        self.l.addWidget(self.imapuser,row,1)
        row+=1

        label = QLabel(_('IMAP User Password'))
        tooltip = _("IMAP password.  If left empty, FanFicFare will ask you for your password when you use the feature.")
        label.setToolTip(tooltip)
        self.l.addWidget(label,row,0)
        self.imappass = QLineEdit(self)
        self.imappass.setToolTip(tooltip)
        self.imappass.setEchoMode(QLineEdit.Password)
        self.imappass.setText(prefs['imappass'])
        self.l.addWidget(self.imappass,row,1)
        row+=1

        self.imapsessionpass = QCheckBox(_('Remember Password for Session (when not saved above)'),self)
        self.imapsessionpass.setToolTip(_('If checked, and no password is entered above, FanFicFare will remember your password until you close calibre or change Libraries.'))
        self.imapsessionpass.setChecked(prefs['imapsessionpass'])
        self.l.addWidget(self.imapsessionpass,row,0,1,-1)
        row+=1

        label = QLabel(_('IMAP Folder Name'))
        tooltip = _("Name of IMAP folder to search for new emails.  The folder (or label) has to already exist.  Use INBOX for your default inbox.")
        label.setToolTip(tooltip)
        self.l.addWidget(label,row,0)
        self.imapfolder = QLineEdit(self)
        self.imapfolder.setToolTip(tooltip)
        self.imapfolder.setText(prefs['imapfolder'])
        self.l.addWidget(self.imapfolder,row,1)
        row+=1

        self.imapmarkread = QCheckBox(_('Mark Emails Read'),self)
        self.imapmarkread.setToolTip(_('If checked, emails will be marked as having been read if they contain any story URLs.'))
        self.imapmarkread.setChecked(prefs['imapmarkread'])
        self.l.addWidget(self.imapmarkread,row,0,1,-1)
        row+=1

        self.auto_reject_from_email = QCheckBox(_('Discard URLs on Reject List'),self)
        self.auto_reject_from_email.setToolTip(_('If checked, FanFicFare will silently discard story URLs from emails that are on your Reject URL List.<br>Otherwise they will appear and you will see the normal Reject URL dialog.<br>The Emails will still be marked Read if configured to.'))
        self.auto_reject_from_email.setChecked(prefs['auto_reject_from_email'])
        self.l.addWidget(self.auto_reject_from_email,row,0,1,-1)
        row+=1

        self.update_existing_only_from_email = QCheckBox(_('Update Existing Books Only'),self)
        self.update_existing_only_from_email.setToolTip(_('If checked, FanFicFare will silently discard story URLs from emails that are not already in your library.<br>Otherwise all story URLs, new and existing, will be used.<br>The Emails will still be marked Read if configured to.'))
        self.update_existing_only_from_email.setChecked(prefs['update_existing_only_from_email'])
        self.l.addWidget(self.update_existing_only_from_email,row,0,1,-1)
        row+=1

        self.download_from_email_immediately = QCheckBox(_('Download from Email Immediately'),self)
        self.download_from_email_immediately.setToolTip(_('If checked, FanFicFare will start downloading story URLs from emails immediately.<br>Otherwise the usual Download from URLs dialog will appear.'))
        self.download_from_email_immediately.setChecked(prefs['download_from_email_immediately'])
        self.l.addWidget(self.download_from_email_immediately,row,0,1,-1)
        row+=1

        label = QLabel(_('Add these Tag(s) Automatically'))
        tooltip = ( _("Tags entered here will be automatically added to stories downloaded from email story URLs.") +"\n"+
                    _("Any additional stories you then manually add to the Story URL dialog will also have these tags added.") )
        label.setToolTip(tooltip)
        self.l.addWidget(label,row,0)
        self.imaptags = EditWithComplete(self) # QLineEdit(self)
        self.imaptags.update_items_cache(self.plugin_action.gui.current_db.all_tags())
        self.imaptags.setToolTip(tooltip)
        self.imaptags.setText(prefs['imaptags'])
        self.imaptags.setCursorPosition(0)
        self.l.addWidget(self.imaptags,row,1)
        row+=1

        label = QLabel(_("<b>It's safest if you create a separate email account that you use only "
                         "for your story update notices.  FanFicFare and calibre cannot guarantee that "
                         "malicious code cannot get your email password once you've entered it. "
                         "<br>Use this feature at your own risk. </b>"))
        label.setWordWrap(True)
        self.l.addWidget(label,row,0,1,-1,Qt.AlignTop)
        self.l.setRowStretch(row,1)
        row+=1
