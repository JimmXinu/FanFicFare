#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2012, Jim Miller'
__docformat__ = 'restructuredtext en'

import traceback, copy, threading
from collections import OrderedDict

from PyQt4.Qt import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                      QLineEdit, QFont, QWidget, QTextEdit, QComboBox,
                      QCheckBox, QPushButton, QTabWidget, QVariant, QScrollArea,
                      QDialogButtonBox, QGroupBox )

from calibre.gui2.ui import get_gui
from calibre.gui2 import dynamic, info_dialog
from calibre.constants import numeric_version as calibre_version

from calibre_plugins.fanfictiondownloader_plugin.prefs import prefs, PREFS_NAMESPACE
from calibre_plugins.fanfictiondownloader_plugin.dialogs \
    import (UPDATE, UPDATEALWAYS, OVERWRITE, collision_order, RejectListDialog,
            EditTextDialog, RejectUrlEntry)
    
from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader.adapters \
    import (getConfigSections, getNormalStoryURL)

from calibre_plugins.fanfictiondownloader_plugin.common_utils \
    import ( KeyboardConfigDialog, PrefsViewerDialog )

from calibre.gui2.complete import MultiCompleteLineEdit

class RejectURLList:
    def __init__(self,prefs):
        self.prefs = prefs
        self.sync_lock = threading.RLock()
        self.listcache = None

    def _read_list_from_text(self,text,addreasontext=''):
        cache = OrderedDict()

        #print("_read_list_from_text")
        for line in text.splitlines():
            rue = RejectUrlEntry(line,addreasontext=addreasontext,fromline=True)
            #print("rue.url:%s"%rue.url)
            if rue.valid:
                cache[rue.url] = rue
        return cache        

    def _get_listcache(self):
        if self.listcache == None:
            self.listcache = self._read_list_from_text(prefs['rejecturls'])
        return self.listcache

    def _save_list(self,listcache):
        #print("_save_list")
        self.prefs['rejecturls'] = '\n'.join([x.to_line() for x in listcache.values()])
        self.prefs.save_to_db()
        self.listcache = None
        
    def clear_cache(self):
        self.listcache = None

    # true if url is in list.
    def check(self,url):
        with self.sync_lock:
            listcache = self._get_listcache()
            return url in listcache
        
    def get_note(self,url):
        with self.sync_lock:
            listcache = self._get_listcache()
            if url in listcache:
                return listcache[url].note
            # not found
            return ''

    def get_full_note(self,url):
        with self.sync_lock:
            listcache = self._get_listcache()
            if url in listcache:
                return listcache[url].fullnote()
            # not found
            return ''

    def remove(self,url):
        with self.sync_lock:
            listcache = self._get_listcache()
            if url in listcache:
                del listcache[url]
                self._save_list(listcache)

    def add_text(self,rejecttext,addreasontext):
        self.add(self._read_list_from_text(rejecttext,addreasontext).values())
            
    def add(self,rejectlist,clear=False):
        with self.sync_lock:
            if clear:
                listcache=OrderedDict()
            else:
                listcache = self._get_listcache()
            for l in rejectlist:
                listcache[l.url]=l
            self._save_list(listcache)

    def get_list(self):
        return self._get_listcache().values()
            
    def get_reject_reasons(self):
        return self.prefs['rejectreasons'].splitlines()

rejecturllist = RejectURLList(prefs)

class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        
        self.l = QVBoxLayout()
        self.setLayout(self.l)

        label = QLabel('<a href="http://code.google.com/p/fanficdownloader/wiki/FanFictionDownloaderSupportedsites">List of Supported Sites</a> -- <a href="http://code.google.com/p/fanficdownloader/wiki/FanFictionDownloaderFAQs">FAQs</a>')
        label.setOpenExternalLinks(True)
        self.l.addWidget(label)

        tab_widget = QTabWidget(self)
        self.l.addWidget(tab_widget)

        self.basic_tab = BasicTab(self, plugin_action)
        tab_widget.addTab(self.basic_tab, 'Basic')

        self.personalini_tab = PersonalIniTab(self, plugin_action)
        tab_widget.addTab(self.personalini_tab, 'personal.ini')
        
        self.readinglist_tab = ReadingListTab(self, plugin_action)
        tab_widget.addTab(self.readinglist_tab, 'Reading Lists')
        if 'Reading List' not in plugin_action.gui.iactions:
            self.readinglist_tab.setEnabled(False)

        self.generatecover_tab = GenerateCoverTab(self, plugin_action)
        tab_widget.addTab(self.generatecover_tab, 'Generate Cover')
        if 'Generate Cover' not in plugin_action.gui.iactions:
            self.generatecover_tab.setEnabled(False)

        self.countpages_tab = CountPagesTab(self, plugin_action)
        tab_widget.addTab(self.countpages_tab, 'Count Pages')
        if 'Count Pages' not in plugin_action.gui.iactions:
            self.countpages_tab.setEnabled(False)

        self.std_columns_tab = StandardColumnsTab(self, plugin_action)
        tab_widget.addTab(self.std_columns_tab, 'Standard Columns')

        self.cust_columns_tab = CustomColumnsTab(self, plugin_action)
        tab_widget.addTab(self.cust_columns_tab, 'Custom Columns')

        self.other_tab = OtherTab(self, plugin_action)
        tab_widget.addTab(self.other_tab, 'Other')


    def save_settings(self):

        # basic
        prefs['fileform'] = unicode(self.basic_tab.fileform.currentText())
        prefs['collision'] = unicode(self.basic_tab.collision.currentText())
        prefs['updatemeta'] = self.basic_tab.updatemeta.isChecked()
        prefs['updatecover'] = self.basic_tab.updatecover.isChecked()
        prefs['updateepubcover'] = self.basic_tab.updateepubcover.isChecked()
        prefs['keeptags'] = self.basic_tab.keeptags.isChecked()
        prefs['suppressauthorsort'] = self.basic_tab.suppressauthorsort.isChecked()
        prefs['suppresstitlesort'] = self.basic_tab.suppresstitlesort.isChecked()
        prefs['showmarked'] = self.basic_tab.showmarked.isChecked()
        prefs['urlsfromclip'] = self.basic_tab.urlsfromclip.isChecked()
        prefs['updatedefault'] = self.basic_tab.updatedefault.isChecked()
        prefs['deleteotherforms'] = self.basic_tab.deleteotherforms.isChecked()
        prefs['adddialogstaysontop'] = self.basic_tab.adddialogstaysontop.isChecked()
        prefs['includeimages'] = self.basic_tab.includeimages.isChecked()
        prefs['lookforurlinhtml'] = self.basic_tab.lookforurlinhtml.isChecked()
        prefs['checkforseriesurlid'] = self.basic_tab.checkforseriesurlid.isChecked()
        prefs['checkforurlchange'] = self.basic_tab.checkforurlchange.isChecked()
        prefs['injectseries'] = self.basic_tab.injectseries.isChecked()
        prefs['smarten_punctuation'] = self.basic_tab.smarten_punctuation.isChecked()

        if self.readinglist_tab:
            # lists
            prefs['send_lists'] = ', '.join(map( lambda x : x.strip(), filter( lambda x : x.strip() != '', unicode(self.readinglist_tab.send_lists_box.text()).split(','))))
            prefs['read_lists'] = ', '.join(map( lambda x : x.strip(), filter( lambda x : x.strip() != '', unicode(self.readinglist_tab.read_lists_box.text()).split(','))))
            # print("send_lists: %s"%prefs['send_lists'])
            # print("read_lists: %s"%prefs['read_lists'])
            prefs['addtolists'] = self.readinglist_tab.addtolists.isChecked()
            prefs['addtoreadlists'] = self.readinglist_tab.addtoreadlists.isChecked()
            prefs['addtolistsonread'] = self.readinglist_tab.addtolistsonread.isChecked()

        # personal.ini
        ini = unicode(self.personalini_tab.ini.toPlainText())
        if ini:
            prefs['personal.ini'] = ini
        else:
            # if they've removed everything, reset to default.
            prefs['personal.ini'] = get_resources('plugin-example.ini')

        # Generate Covers tab
        prefs['gcnewonly'] = self.generatecover_tab.gcnewonly.isChecked()
        gc_site_settings = {}
        for (site,combo) in self.generatecover_tab.gc_dropdowns.iteritems():
            val = unicode(combo.itemData(combo.currentIndex()).toString())
            if val != 'none':
                gc_site_settings[site] = val
                #print("gc_site_settings[%s]:%s"%(site,gc_site_settings[site]))
        prefs['gc_site_settings'] = gc_site_settings
        prefs['allow_gc_from_ini'] = self.generatecover_tab.allow_gc_from_ini.isChecked()

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
        
        # Standard Columns tab
        colsnewonly = {}
        for (col,checkbox) in self.std_columns_tab.stdcol_newonlycheck.iteritems():
            colsnewonly[col] = checkbox.isChecked()
        prefs['std_cols_newonly'] = colsnewonly

        # Custom Columns tab
        # error column
        prefs['errorcol'] = unicode(self.cust_columns_tab.errorcol.itemData(self.cust_columns_tab.errorcol.currentIndex()).toString())

        # cust cols tab
        colsmap = {}
        for (col,combo) in self.cust_columns_tab.custcol_dropdowns.iteritems():
            val = unicode(combo.itemData(combo.currentIndex()).toString())
            if val != 'none':
                colsmap[col] = val
                #print("colsmap[%s]:%s"%(col,colsmap[col]))
        prefs['custom_cols'] = colsmap

        colsnewonly = {}
        for (col,checkbox) in self.cust_columns_tab.custcol_newonlycheck.iteritems():
            colsnewonly[col] = checkbox.isChecked()
        prefs['custom_cols_newonly'] = colsnewonly
        
        prefs['allow_custcol_from_ini'] = self.cust_columns_tab.allow_custcol_from_ini.isChecked()
        
        prefs.save_to_db()

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

        label = QLabel('These settings control the basic features of the plugin--downloading FanFiction.')
        label.setWordWrap(True)
        topl.addWidget(label)

        defs_gb = groupbox = QGroupBox("Defaults Options on Download")
        self.l = QVBoxLayout()
        groupbox.setLayout(self.l)

        tooltip = "On each download, FFDL offers an option to select the output format. <br />This sets what that option will default to."
        horz = QHBoxLayout()
        label = QLabel('Default Output &Format:')
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

        tooltip = "On each download, FFDL offers an option of what happens if that story already exists. <br />This sets what that option will default to."
        horz = QHBoxLayout()
        label = QLabel('Default If Story Already Exists?')
        label.setToolTip(tooltip)
        horz.addWidget(label)
        self.collision = QComboBox(self)
        # add collision options
        self.set_collisions()
        i = self.collision.findText(prefs['collision'])
        if i > -1:
            self.collision.setCurrentIndex(i)
        self.collision.setToolTip(tooltip)
        label.setBuddy(self.collision)
        horz.addWidget(self.collision)
        self.l.addLayout(horz)

        self.updatemeta = QCheckBox('Default Update Calibre &Metadata?',self)
        self.updatemeta.setToolTip("On each download, FFDL offers an option to update Calibre's metadata (title, author, URL, tags, custom columns, etc) from the web site. <br />This sets whether that will default to on or off. <br />Columns set to 'New Only' in the column tabs will only be set for new books.")
        self.updatemeta.setChecked(prefs['updatemeta'])
        self.l.addWidget(self.updatemeta)

        self.updateepubcover = QCheckBox('Default Update EPUB Cover when Updating EPUB?',self)
        self.updateepubcover.setToolTip("On each download, FFDL offers an option to update the book cover image <i>inside</i> the EPUB from the web site when the EPUB is updated.<br />This sets whether that will default to on or off.")
        self.updateepubcover.setChecked(prefs['updateepubcover'])
        self.l.addWidget(self.updateepubcover)

        self.smarten_punctuation = QCheckBox('Smarten Punctuation (EPUB only)',self)
        self.smarten_punctuation.setToolTip("Run Smarten Punctuation from Calibre's Polish Book feature on each EPUB download and update.")
        self.smarten_punctuation.setChecked(prefs['smarten_punctuation'])
        if calibre_version >= (0, 9, 39):
            self.l.addWidget(self.smarten_punctuation)

        cali_gb = groupbox = QGroupBox("Updating Calibre Options")
        self.l = QVBoxLayout()
        groupbox.setLayout(self.l)

        self.deleteotherforms = QCheckBox('Delete other existing formats?',self)
        self.deleteotherforms.setToolTip('Check this to automatically delete all other ebook formats when updating an existing book.\nHandy if you have both a Nook(epub) and Kindle(mobi), for example.')
        self.deleteotherforms.setChecked(prefs['deleteotherforms'])
        self.l.addWidget(self.deleteotherforms)
        
        self.updatecover = QCheckBox('Update Calibre Cover when Updating Metadata?',self)
        self.updatecover.setToolTip("Update calibre book cover image from EPUB when metadata is updated.  (EPUB only.)\nDoesn't go looking for new images on 'Update Calibre Metadata Only'.")
        self.updatecover.setChecked(prefs['updatecover'])
        self.l.addWidget(self.updatecover)

        self.keeptags = QCheckBox('Keep Existing Tags when Updating Metadata?',self)
        self.keeptags.setToolTip("Existing tags will be kept and any new tags added.\nCompleted and In-Progress tags will be still be updated, if known.\nLast Updated tags will be updated if lastupdate in include_subject_tags.\n(If Tags is set to 'New Only' in the Standard Columns tab, this has no effect.)")
        self.keeptags.setChecked(prefs['keeptags'])
        self.l.addWidget(self.keeptags)

        self.suppressauthorsort = QCheckBox('Force Author into Author Sort?',self)
        self.suppressauthorsort.setToolTip("If checked, the author(s) as given will be used for the Author Sort, too.\nIf not checked, calibre will apply it's built in algorithm which makes 'Bob Smith' sort as 'Smith, Bob', etc.")
        self.suppressauthorsort.setChecked(prefs['suppressauthorsort'])
        self.l.addWidget(self.suppressauthorsort)

        self.suppresstitlesort = QCheckBox('Force Title into Title Sort?',self)
        self.suppresstitlesort.setToolTip("If checked, the title as given will be used for the Title Sort, too.\nIf not checked, calibre will apply it's built in algorithm which makes 'The Title' sort as 'Title, The', etc.")
        self.suppresstitlesort.setChecked(prefs['suppresstitlesort'])
        self.l.addWidget(self.suppresstitlesort)

        self.checkforseriesurlid = QCheckBox("Check for existing Series Anthology books?",self)
        self.checkforseriesurlid.setToolTip("Check for existings Series Anthology books using each new story's series URL before downloading.\nOffer to skip downloading if a Series Anthology is found.")
        self.checkforseriesurlid.setChecked(prefs['checkforseriesurlid'])
        self.l.addWidget(self.checkforseriesurlid)

        self.checkforurlchange = QCheckBox("Check for changed Story URL?",self)
        self.checkforurlchange.setToolTip("Warn you if an update will change the URL of an existing book.")
        self.checkforurlchange.setChecked(prefs['checkforurlchange'])
        self.l.addWidget(self.checkforurlchange)

        self.lookforurlinhtml = QCheckBox("Search EPUB text for Story URL?",self)
        self.lookforurlinhtml.setToolTip("Look for first valid story URL inside EPUB text if not found in metadata.\nSomewhat risky, could find wrong URL depending on EPUB content.\nAlso finds and corrects bad ffnet URLs from ficsaver.com files.")
        self.lookforurlinhtml.setChecked(prefs['lookforurlinhtml'])
        self.l.addWidget(self.lookforurlinhtml)

        self.showmarked = QCheckBox("Show added/updated books when finished?",self)
        self.showmarked.setToolTip("Show added/updated books only when finished.\nYou can also manually search for 'marked:ffdl_success'.\n'marked:ffdl_failed' is also available, or search 'marked:ffdl' for both.")
        self.showmarked.setChecked(prefs['showmarked'])
        self.l.addWidget(self.showmarked)

        gui_gb = groupbox = QGroupBox("GUI Options")
        self.l = QVBoxLayout()
        groupbox.setLayout(self.l)

        self.urlsfromclip = QCheckBox('Take URLs from Clipboard?',self)
        self.urlsfromclip.setToolTip('Prefill URLs from valid URLs in Clipboard when Adding New.')
        self.urlsfromclip.setChecked(prefs['urlsfromclip'])
        self.l.addWidget(self.urlsfromclip)

        self.updatedefault = QCheckBox('Default to Update when books selected?',self)
        self.updatedefault.setToolTip('The top FanFictionDownLoader plugin button will start Update if\n'+
                                      'books are selected.  If unchecked, it will always bring up \'Add New\'.')
        self.updatedefault.setChecked(prefs['updatedefault'])
        self.l.addWidget(self.updatedefault)

        self.adddialogstaysontop = QCheckBox("Keep 'Add New from URL(s)' dialog on top?",self)
        self.adddialogstaysontop.setToolTip("Instructs the OS and Window Manager to keep the 'Add New from URL(s)'\ndialog on top of all other windows.  Useful for dragging URLs onto it.")
        self.adddialogstaysontop.setChecked(prefs['adddialogstaysontop'])
        self.l.addWidget(self.adddialogstaysontop)

        misc_gb = groupbox = QGroupBox("Misc Options")
        self.l = QVBoxLayout()
        groupbox.setLayout(self.l)

        # this is a cheat to make it easier for users to realize there's a new include_images features.
        self.includeimages = QCheckBox("Include images in EPUBs?",self)
        self.includeimages.setToolTip("Download and include images in EPUB stories.  This is equivalent to adding:\n\n[epub]\ninclude_images:true\nkeep_summary_html:true\nmake_firstimage_cover:true\n\n ...to the top of personal.ini.  Your settings in personal.ini will override this.")
        self.includeimages.setChecked(prefs['includeimages'])
        self.l.addWidget(self.includeimages)

        self.injectseries = QCheckBox("Inject calibre Series when none found?",self)
        self.injectseries.setToolTip("If no series is found, inject the calibre series (if there is one) so it appears on the FFDL title page(not cover).")
        self.injectseries.setChecked(prefs['injectseries'])
        self.l.addWidget(self.injectseries)

        rej_gb = groupbox = QGroupBox("Reject List")
        self.l = QVBoxLayout()
        groupbox.setLayout(self.l)

        self.rejectlist = QPushButton('Edit Reject URL List', self)
        self.rejectlist.setToolTip("Edit list of URLs FFDL will automatically Reject.")
        self.rejectlist.clicked.connect(self.show_rejectlist)
        self.l.addWidget(self.rejectlist)
        
        self.reject_urls = QPushButton('Add Reject URLs', self)
        self.reject_urls.setToolTip("Add additional URLs to Reject as text.")
        self.reject_urls.clicked.connect(self.add_reject_urls)
        self.l.addWidget(self.reject_urls)
        
        self.reject_reasons = QPushButton('Edit Reject Reasons List', self)
        self.reject_reasons.setToolTip("Customize the Reasons presented when Rejecting URLs")
        self.reject_reasons.clicked.connect(self.show_reject_reasons)
        self.l.addWidget(self.reject_reasons)

        topl.addWidget(defs_gb)

        horz = QHBoxLayout()
        topl.addLayout(horz)
        horz.addWidget(cali_gb)
        horz.addWidget(rej_gb)
        
        horz = QHBoxLayout()
        topl.addLayout(horz)
        horz.addWidget(gui_gb)
        horz.addWidget(misc_gb)

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
        
    def show_defaults(self):
        text = get_resources('plugin-defaults.ini')
        ShowDefaultsIniDialog(self.windowIcon(),text,self).exec_()

    def show_rejectlist(self):
        d = RejectListDialog(self,
                             rejecturllist.get_list(),
                             rejectreasons=rejecturllist.get_reject_reasons(),
                             header="Edit Reject URLs List",
                             show_delete=False,
                             show_all_reasons=False)
        d.exec_()
        
        if d.result() != d.Accepted:
            return
        
        rejecturllist.add(d.get_reject_list(),clear=True)
        
    def show_reject_reasons(self):
        d = EditTextDialog(self,
                           prefs['rejectreasons'],
                           icon=self.windowIcon(),
                           title="Reject Reasons",
                           label="Customize Reject List Reasons",
                           tooltip="Customize the Reasons presented when Rejecting URLs")
        d.exec_()
        if d.result() == d.Accepted:
            prefs['rejectreasons'] = d.get_plain_text()
                
    def add_reject_urls(self):
        d = EditTextDialog(self,
                           "http://example.com/story.php?sid=5,Reason why I rejected it\nhttp://example.com/story.php?sid=6,Title by Author - Reason why I rejected it",
                           icon=self.windowIcon(),
                           title="Add Reject URLs",
                           label="Add Reject URLs. Use: <b>http://...,note</b> or <b>http://...,title by author - note</b><br>Invalid story URLs will be ignored.",
                           tooltip="One URL per line:\n<b>http://...,note</b>\n<b>http://...,title by author - note</b>",
                           rejectreasons=rejecturllist.get_reject_reasons(),
                           reasonslabel='Add this reason to all URLs added:')
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

        label = QLabel('These settings provide more detailed control over what metadata will be displayed inside the ebook as well as let you set is_adult and user/password for different sites.')
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)
        
        self.label = QLabel('personal.ini:')
        self.l.addWidget(self.label)

        self.ini = QTextEdit(self)
        try:
            self.ini.setFont(QFont("Courier",
                                   self.plugin_action.gui.font().pointSize()+1))
        except Exception as e:
            print("Couldn't get font: %s"%e)
        self.ini.setLineWrapMode(QTextEdit.NoWrap)
        self.ini.setText(prefs['personal.ini'])
        self.l.addWidget(self.ini)

        self.defaults = QPushButton('View Defaults (plugin-defaults.ini)', self)
        self.defaults.setToolTip("View all of the plugin's configurable settings\nand their default settings.")
        self.defaults.clicked.connect(self.show_defaults)
        self.l.addWidget(self.defaults)
        
        # self.l.insertStretch(-1)
        # let edit box fill the space.
        
    def show_defaults(self):
        text = get_resources('plugin-defaults.ini')
        ShowDefaultsIniDialog(self.windowIcon(),text,self).exec_()
        
class ShowDefaultsIniDialog(QDialog):

    def __init__(self, icon, text, parent=None):
        QDialog.__init__(self, parent)
        self.resize(600, 500)
        self.l = QVBoxLayout()
        self.setLayout(self.l)
        self.label = QLabel("Plugin Defaults (plugin-defaults.ini) (Read-Only)")
        self.label.setToolTip("These are all of the plugin's configurable options\nand their default settings.")
        self.setWindowTitle(_('Plugin Defaults'))
        self.setWindowIcon(icon)
        self.l.addWidget(self.label)
        
        self.ini = QTextEdit(self)
        self.ini.setToolTip("These are all of the plugin's configurable options\nand their default settings.")
        try:
            self.ini.setFont(QFont("Courier",
                                   get_gui().font().pointSize()+1))
        except Exception as e:
            print("Couldn't get font: %s"%e)
        self.ini.setLineWrapMode(QTextEdit.NoWrap)
        self.ini.setText(text)
        self.ini.setReadOnly(True)
        self.l.addWidget(self.ini)
        
        self.ok_button = QPushButton('OK', self)
        self.ok_button.clicked.connect(self.hide)
        self.l.addWidget(self.ok_button)
        
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
            
        label = QLabel('These settings provide integration with the Reading List Plugin.  Reading List can automatically send to devices and change custom columns.  You have to create and configure the lists in Reading List to be useful.')
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)
        
        self.addtolists = QCheckBox('Add new/updated stories to "Send to Device" Reading List(s).',self)
        self.addtolists.setToolTip('Automatically add new/updated stories to these lists in the Reading List plugin.')
        self.addtolists.setChecked(prefs['addtolists'])
        self.l.addWidget(self.addtolists)
            
        horz = QHBoxLayout()
        label = QLabel('"Send to Device" Reading Lists')
        label.setToolTip("When enabled, new/updated stories will be automatically added to these lists.")
        horz.addWidget(label)        
        self.send_lists_box = MultiCompleteLineEdit(self)
        self.send_lists_box.setToolTip("When enabled, new/updated stories will be automatically added to these lists.")
        self.send_lists_box.update_items_cache(reading_lists)
        self.send_lists_box.setText(prefs['send_lists'])
        horz.addWidget(self.send_lists_box)
        self.l.addLayout(horz)
        
        self.addtoreadlists = QCheckBox('Add new/updated stories to "To Read" Reading List(s).',self)
        self.addtoreadlists.setToolTip('Automatically add new/updated stories to these lists in the Reading List plugin.\nAlso offers menu option to remove stories from the "To Read" lists.')
        self.addtoreadlists.setChecked(prefs['addtoreadlists'])
        self.l.addWidget(self.addtoreadlists)
            
        horz = QHBoxLayout()
        label = QLabel('"To Read" Reading Lists')
        label.setToolTip("When enabled, new/updated stories will be automatically added to these lists.")
        horz.addWidget(label)        
        self.read_lists_box = MultiCompleteLineEdit(self)
        self.read_lists_box.setToolTip("When enabled, new/updated stories will be automatically added to these lists.")
        self.read_lists_box.update_items_cache(reading_lists)
        self.read_lists_box.setText(prefs['read_lists'])
        horz.addWidget(self.read_lists_box)
        self.l.addLayout(horz)
        
        self.addtolistsonread = QCheckBox('Add stories back to "Send to Device" Reading List(s) when marked "Read".',self)
        self.addtolistsonread.setToolTip('Menu option to remove from "To Read" lists will also add stories back to "Send to Device" Reading List(s)')
        self.addtolistsonread.setChecked(prefs['addtolistsonread'])
        self.l.addWidget(self.addtolistsonread)
            
        self.l.insertStretch(-1)
        
class GenerateCoverTab(QWidget):

    def __init__(self, parent_dialog, plugin_action):
        self.parent_dialog = parent_dialog
        self.plugin_action = plugin_action
        QWidget.__init__(self)
        
        self.l = QVBoxLayout()
        self.setLayout(self.l)

        try:
            gc_plugin = plugin_action.gui.iactions['Generate Cover']
            gc_settings = gc_plugin.get_saved_setting_names()
        except KeyError:
            gc_settings= []
            
        label = QLabel('The Generate Cover plugin can create cover images for books using various metadata and configurations.  If you have GC installed, FFDL can run GC on new downloads and metadata updates.  Pick a GC setting by site or Default.')
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

        sitelist = getConfigSections()
        sitelist.sort()
        sitelist.insert(0,u"Default")
        for site in sitelist:
            horz = QHBoxLayout()
            label = QLabel(site)
            if site == u"Default":
                s = "On Metadata update, run Generate Cover with this setting, if not selected for specific site."
            else:
                s = "On Metadata update, run Generate Cover with this setting for %s stories."%site

            label.setToolTip(s)
            horz.addWidget(label)
            dropdown = QComboBox(self)
            dropdown.setToolTip(s)
            dropdown.addItem('',QVariant('none'))
            for setting in gc_settings:
                dropdown.addItem(setting,QVariant(setting))
            self.gc_dropdowns[site] = dropdown
            if site in prefs['gc_site_settings']:
                dropdown.setCurrentIndex(dropdown.findData(QVariant(prefs['gc_site_settings'][site])))

            horz.addWidget(dropdown)
            self.sl.addLayout(horz)
        
        self.sl.insertStretch(-1)
        
        self.gcnewonly = QCheckBox("Run Generate Cover Only on New Books",self)
        self.gcnewonly.setToolTip("Default is to run GC any time the calibre metadata is updated.")
        self.gcnewonly.setChecked(prefs['gcnewonly'])
        self.l.addWidget(self.gcnewonly)

        self.allow_gc_from_ini = QCheckBox('Allow generate_cover_settings from personal.ini to override',self)
        self.allow_gc_from_ini.setToolTip("The personal.ini parameter generate_cover_settings allows you to choose a GC setting based on metadata rather than site, but it's much more complex.<br \>generate_cover_settings is ignored when this is off.")
        self.allow_gc_from_ini.setChecked(prefs['allow_gc_from_ini'])
        self.l.addWidget(self.allow_gc_from_ini)
            
class CountPagesTab(QWidget):

    def __init__(self, parent_dialog, plugin_action):
        self.parent_dialog = parent_dialog
        self.plugin_action = plugin_action
        QWidget.__init__(self)
        
        self.l = QVBoxLayout()
        self.setLayout(self.l)

        label = QLabel('These settings provide integration with the Count Pages Plugin.  Count Pages can automatically update custom columns with page, word and reading level statistics.  You have to create and configure the columns in Count Pages first.')
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)

        label = QLabel('If any of the settings below are checked, when stories are added or updated, the Count Pages Plugin will be called to update the checked statistics.')
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)
        
        # 'PageCount', 'WordCount', 'FleschReading', 'FleschGrade', 'GunningFog'
        self.pagecount = QCheckBox('Page Count',self)
        self.pagecount.setToolTip('Which column and algorithm to use are configured in Count Pages.')
        self.pagecount.setChecked('PageCount' in prefs['countpagesstats'])
        self.l.addWidget(self.pagecount)
            
        self.wordcount = QCheckBox('Word Count',self)
        self.wordcount.setToolTip('Which column and algorithm to use are configured in Count Words.\nWill overwrite word count from FFDL metadata if set to update the same custom column.')
        self.wordcount.setChecked('WordCount' in prefs['countpagesstats'])
        self.l.addWidget(self.wordcount)

        self.fleschreading = QCheckBox('Flesch Reading Ease',self)
        self.fleschreading.setToolTip('Which column and algorithm to use are configured in Count Pages.')
        self.fleschreading.setChecked('FleschReading' in prefs['countpagesstats'])
        self.l.addWidget(self.fleschreading)
        
        self.fleschgrade = QCheckBox('Flesch-Kincaid Grade Level',self)
        self.fleschgrade.setToolTip('Which column and algorithm to use are configured in Count Pages.')
        self.fleschgrade.setChecked('FleschGrade' in prefs['countpagesstats'])
        self.l.addWidget(self.fleschgrade)
        
        self.gunningfog = QCheckBox('Gunning Fog Index',self)
        self.gunningfog.setToolTip('Which column and algorithm to use are configured in Count Pages.')
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

        label = QLabel("These controls aren't plugin settings as such, but convenience buttons for setting Keyboard shortcuts and getting all the FanFictionDownLoader confirmation dialogs back again.")
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)
        
        keyboard_shortcuts_button = QPushButton('Keyboard shortcuts...', self)
        keyboard_shortcuts_button.setToolTip(_(
                    'Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(parent_dialog.edit_shortcuts)
        self.l.addWidget(keyboard_shortcuts_button)

        reset_confirmation_button = QPushButton(_('Reset disabled &confirmation dialogs'), self)
        reset_confirmation_button.setToolTip(_(
                    'Reset all show me again dialogs for the FanFictionDownLoader plugin'))
        reset_confirmation_button.clicked.connect(self.reset_dialogs)
        self.l.addWidget(reset_confirmation_button)
        
        view_prefs_button = QPushButton('&View library preferences...', self)
        view_prefs_button.setToolTip(_(
                    'View data stored in the library database for this plugin'))
        view_prefs_button.clicked.connect(self.view_prefs)
        self.l.addWidget(view_prefs_button)
        
        self.l.insertStretch(-1)
        
    def reset_dialogs(self):
        for key in dynamic.keys():
            if key.startswith('fanfictiondownloader_') and key.endswith('_again') \
                                                  and dynamic[key] is False:
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
    'category':'Category',
    'genre':'Genre',
    'language':'Language',
    'status':'Status',
    'status-C':'Status:Completed',
    'status-I':'Status:In-Progress',
    'series':'Series',
    'characters':'Characters',
    'ships':'Relationships',
    'datePublished':'Published',
    'dateUpdated':'Updated',
    'dateCreated':'Created',
    'rating':'Rating',
    'warnings':'Warnings',
    'numChapters':'Chapters',
    'numWords':'Words',
    'site':'Site',
    'storyId':'Story ID',
    'authorId':'Author ID',
    'extratags':'Extra Tags',
    'title':'Title',
    'storyUrl':'Story URL',
    'description':'Description',
    'author':'Author',
    'authorUrl':'Author URL',
    'formatname':'File Format',
    'formatext':'File Extension',
    'siteabbrev':'Site Abbrev',
    'version':'FFDL Version'
    }

class CustomColumnsTab(QWidget):

    def __init__(self, parent_dialog, plugin_action):
        self.parent_dialog = parent_dialog
        self.plugin_action = plugin_action
        QWidget.__init__(self)
        
        custom_columns = self.plugin_action.gui.library_view.model().custom_columns

        self.l = QVBoxLayout()
        self.setLayout(self.l)

        label = QLabel("If you have custom columns defined, they will be listed below.  Choose a metadata value type to fill your columns automatically.")
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
        
        for key, column in custom_columns.iteritems():

            if column['datatype'] in permitted_values:
                # print("\n============== %s ===========\n"%key)
                # for (k,v) in column.iteritems():
                #     print("column['%s'] => %s"%(k,v))
                horz = QHBoxLayout()
                label = QLabel(column['name'])
                label.setToolTip("Update this %s column(%s) with..."%(key,column['datatype']))
                horz.addWidget(label)
                dropdown = QComboBox(self)
                dropdown.addItem('',QVariant('none'))
                for md in permitted_values[column['datatype']]:
                    dropdown.addItem(titleLabels[md],QVariant(md))
                self.custcol_dropdowns[key] = dropdown
                if key in prefs['custom_cols']:
                    dropdown.setCurrentIndex(dropdown.findData(QVariant(prefs['custom_cols'][key])))
                if column['datatype'] == 'enumeration':
                    dropdown.setToolTip("Metadata values valid for this type of column.\nValues that aren't valid for this enumeration column will be ignored.")
                else:
                    dropdown.setToolTip("Metadata values valid for this type of column.")
                horz.addWidget(dropdown)

                newonlycheck = QCheckBox("New Only",self)
                newonlycheck.setToolTip("Write to %s(%s) only for new\nbooks, not updates to existing books."%(column['name'],key))
                self.custcol_newonlycheck[key] = newonlycheck
                if key in prefs['custom_cols_newonly']:
                    newonlycheck.setChecked(prefs['custom_cols_newonly'][key])
                horz.addWidget(newonlycheck)
                
                self.sl.addLayout(horz)
        
        self.sl.insertStretch(-1)

        self.l.addSpacing(5)
        self.allow_custcol_from_ini = QCheckBox('Allow custom_columns_settings from personal.ini to override',self)
        self.allow_custcol_from_ini.setToolTip("The personal.ini parameter custom_columns_settings allows you to set custom columns to site specific values that aren't common to all sites.<br \>custom_columns_settings is ignored when this is off.")
        self.allow_custcol_from_ini.setChecked(prefs['allow_custcol_from_ini'])
        self.l.addWidget(self.allow_custcol_from_ini)
        
        self.l.addSpacing(5)
        label = QLabel("Special column:")
        label.setWordWrap(True)
        self.l.addWidget(label)
        
        horz = QHBoxLayout()
        label = QLabel("Update/Overwrite Error Column:")
        tooltip="When an update or overwrite of an existing story fails, record the reason in this column.\n(Text and Long Text columns only.)"
        label.setToolTip(tooltip)
        horz.addWidget(label)
        self.errorcol = QComboBox(self)
        self.errorcol.setToolTip(tooltip)
        self.errorcol.addItem('',QVariant('none'))
        for key, column in custom_columns.iteritems():
            if column['datatype'] in ('text','comments'):
                self.errorcol.addItem(column['name'],QVariant(key))
        self.errorcol.setCurrentIndex(self.errorcol.findData(QVariant(prefs['errorcol'])))
        horz.addWidget(self.errorcol)
        self.l.addLayout(horz)

        #print("prefs['custom_cols'] %s"%prefs['custom_cols'])


class StandardColumnsTab(QWidget):

    def __init__(self, parent_dialog, plugin_action):
        self.parent_dialog = parent_dialog
        self.plugin_action = plugin_action
        QWidget.__init__(self)

        columns=OrderedDict()
        
        columns["title"]="Title"
        columns["authors"]="Author(s)"
        columns["publisher"]="Publisher"
        columns["tags"]="Tags"
        columns["languages"]="Languages"
        columns["pubdate"]="Published Date"
        columns["timestamp"]="Date"
        columns["comments"]="Comments"
        columns["series"]="Series"
        columns["identifiers"]="Ids(url id only)"

        self.l = QVBoxLayout()
        self.setLayout(self.l)

        label = QLabel("The standard calibre metadata columns are listed below.  You may choose whether FFDL will fill each column automatically on updates or only for new books.")
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)
        
        self.stdcol_newonlycheck = {}

        for key, column in columns.iteritems():
            horz = QHBoxLayout()
            label = QLabel(column)
            #label.setToolTip("Update this %s column(%s) with..."%(key,column['datatype']))
            horz.addWidget(label)

            newonlycheck = QCheckBox("New Only",self)
            newonlycheck.setToolTip("Write to %s only for new\nbooks, not updates to existing books."%column)
            self.stdcol_newonlycheck[key] = newonlycheck
            if key in prefs['std_cols_newonly']:
                newonlycheck.setChecked(prefs['std_cols_newonly'][key])
            horz.addWidget(newonlycheck)
            
            self.l.addLayout(horz)
        
        self.l.insertStretch(-1)

