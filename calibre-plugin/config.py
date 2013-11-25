#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2012, Jim Miller'
__docformat__ = 'restructuredtext en'

import logging
logger = logging.getLogger(__name__)

import traceback, copy, threading
from collections import OrderedDict

from PyQt4.Qt import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                      QLineEdit, QFont, QWidget, QTextEdit, QComboBox,
                      QCheckBox, QPushButton, QTabWidget, QVariant, QScrollArea,
                      QDialogButtonBox, QGroupBox )

from calibre.gui2.ui import get_gui
from calibre.gui2 import dynamic, info_dialog
from calibre.constants import numeric_version as calibre_version

# pulls in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

# There are a number of things used several times that shouldn't be
# translated.  This is just a way to make that easier by keeping them
# out of the _() strings.
# I'm tempted to override _() to include them...
no_trans = { 'pini':'personal.ini',
             'imgset':'\n\n[epub]\ninclude_images:true\nkeep_summary_html:true\nmake_firstimage_cover:true\n\n',
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

from calibre_plugins.fanfictiondownloader_plugin.prefs import prefs, PREFS_NAMESPACE
from calibre_plugins.fanfictiondownloader_plugin.dialogs \
    import (UPDATE, UPDATEALWAYS, collision_order, save_collisions, RejectListDialog,
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

        label = QLabel('<a href="http://code.google.com/p/fanficdownloader/wiki/FanFictionDownloaderSupportedsites">'+_('List of Supported Sites')+'</a> -- <a href="http://code.google.com/p/fanficdownloader/wiki/FanFictionDownloaderFAQs">'+_('FAQs')+'</a>')
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

        self.generatecover_tab = GenerateCoverTab(self, plugin_action)
        tab_widget.addTab(self.generatecover_tab, 'Generate Cover')
        if 'Generate Cover' not in plugin_action.gui.iactions:
            self.generatecover_tab.setEnabled(False)

        self.countpages_tab = CountPagesTab(self, plugin_action)
        tab_widget.addTab(self.countpages_tab, 'Count Pages')
        if 'Count Pages' not in plugin_action.gui.iactions:
            self.countpages_tab.setEnabled(False)

        self.std_columns_tab = StandardColumnsTab(self, plugin_action)
        tab_widget.addTab(self.std_columns_tab, _('Standard Columns'))

        self.cust_columns_tab = CustomColumnsTab(self, plugin_action)
        tab_widget.addTab(self.cust_columns_tab, _('Custom Columns'))

        self.other_tab = OtherTab(self, plugin_action)
        tab_widget.addTab(self.other_tab, _('Other'))


    def save_settings(self):

        # basic
        prefs['fileform'] = unicode(self.basic_tab.fileform.currentText())
        prefs['collision'] = save_collisions[unicode(self.basic_tab.collision.currentText())]
        prefs['updatemeta'] = self.basic_tab.updatemeta.isChecked()
        prefs['updatecover'] = self.basic_tab.updatecover.isChecked()
        prefs['updateepubcover'] = self.basic_tab.updateepubcover.isChecked()
        prefs['keeptags'] = self.basic_tab.keeptags.isChecked()
        prefs['suppressauthorsort'] = self.basic_tab.suppressauthorsort.isChecked()
        prefs['suppresstitlesort'] = self.basic_tab.suppresstitlesort.isChecked()
        prefs['mark'] = self.basic_tab.mark.isChecked()
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

        label = QLabel(_('These settings control the basic features of the plugin--downloading FanFiction.'))
        label.setWordWrap(True)
        topl.addWidget(label)

        defs_gb = groupbox = QGroupBox(_("Defaults Options on Download"))
        self.l = QVBoxLayout()
        groupbox.setLayout(self.l)

        tooltip = _("On each download, FFDL offers an option to select the output format. <br />This sets what that option will default to.")
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

        tooltip = _("On each download, FFDL offers an option of what happens if that story already exists. <br />This sets what that option will default to.")
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

        self.updatemeta = QCheckBox(_('Default Update Calibre &Metadata?'),self)
        self.updatemeta.setToolTip(_("On each download, FFDL offers an option to update Calibre's metadata (title, author, URL, tags, custom columns, etc) from the web site. <br />This sets whether that will default to on or off. <br />Columns set to 'New Only' in the column tabs will only be set for new books."))
        self.updatemeta.setChecked(prefs['updatemeta'])
        self.l.addWidget(self.updatemeta)

        self.updateepubcover = QCheckBox(_('Default Update EPUB Cover when Updating EPUB?'),self)
        self.updateepubcover.setToolTip(_("On each download, FFDL offers an option to update the book cover image <i>inside</i> the EPUB from the web site when the EPUB is updated.<br />This sets whether that will default to on or off."))
        self.updateepubcover.setChecked(prefs['updateepubcover'])
        self.l.addWidget(self.updateepubcover)

        self.smarten_punctuation = QCheckBox(_('Smarten Punctuation (EPUB only)'),self)
        self.smarten_punctuation.setToolTip(_("Run Smarten Punctuation from Calibre's Polish Book feature on each EPUB download and update."))
        self.smarten_punctuation.setChecked(prefs['smarten_punctuation'])
        if calibre_version >= (0, 9, 39):
            self.l.addWidget(self.smarten_punctuation)

        cali_gb = groupbox = QGroupBox(_("Updating Calibre Options"))
        self.l = QVBoxLayout()
        groupbox.setLayout(self.l)

        self.deleteotherforms = QCheckBox(_('Delete other existing formats?'),self)
        self.deleteotherforms.setToolTip(_('Check this to automatically delete all other ebook formats when updating an existing book.\nHandy if you have both a Nook(epub) and Kindle(mobi), for example.'))
        self.deleteotherforms.setChecked(prefs['deleteotherforms'])
        self.l.addWidget(self.deleteotherforms)
        
        self.updatecover = QCheckBox(_('Update Calibre Cover when Updating Metadata?'),self)
        self.updatecover.setToolTip(_("Update calibre book cover image from EPUB when metadata is updated.  (EPUB only.)\nDoesn't go looking for new images on 'Update Calibre Metadata Only'."))
        self.updatecover.setChecked(prefs['updatecover'])
        self.l.addWidget(self.updatecover)

        self.keeptags = QCheckBox(_('Keep Existing Tags when Updating Metadata?'),self)
        self.keeptags.setToolTip(_("Existing tags will be kept and any new tags added.\n%(cmplt)s and %(inprog)s tags will be still be updated, if known.\n%(lul)s tags will be updated if %(lus)s in %(is)s.\n(If Tags is set to 'New Only' in the Standard Columns tab, this has no effect.)")%no_trans)
        self.keeptags.setChecked(prefs['keeptags'])
        self.l.addWidget(self.keeptags)

        self.suppressauthorsort = QCheckBox(_('Force Author into Author Sort?'),self)
        self.suppressauthorsort.setToolTip(_("If checked, the author(s) as given will be used for the Author Sort, too.\nIf not checked, calibre will apply it's built in algorithm which makes 'Bob Smith' sort as 'Smith, Bob', etc."))
        self.suppressauthorsort.setChecked(prefs['suppressauthorsort'])
        self.l.addWidget(self.suppressauthorsort)

        self.suppresstitlesort = QCheckBox(_('Force Title into Title Sort?'),self)
        self.suppresstitlesort.setToolTip(_("If checked, the title as given will be used for the Title Sort, too.\nIf not checked, calibre will apply it's built in algorithm which makes 'The Title' sort as 'Title, The', etc."))
        self.suppresstitlesort.setChecked(prefs['suppresstitlesort'])
        self.l.addWidget(self.suppresstitlesort)

        self.checkforseriesurlid = QCheckBox(_("Check for existing Series Anthology books?"),self)
        self.checkforseriesurlid.setToolTip(_("Check for existings Series Anthology books using each new story's series URL before downloading.\nOffer to skip downloading if a Series Anthology is found."))
        self.checkforseriesurlid.setChecked(prefs['checkforseriesurlid'])
        self.l.addWidget(self.checkforseriesurlid)

        self.checkforurlchange = QCheckBox(_("Check for changed Story URL?"),self)
        self.checkforurlchange.setToolTip(_("Warn you if an update will change the URL of an existing book.\nfanfiction.net URLs will change from http to https silently."))
        self.checkforurlchange.setChecked(prefs['checkforurlchange'])
        self.l.addWidget(self.checkforurlchange)

        self.lookforurlinhtml = QCheckBox(_("Search EPUB text for Story URL?"),self)
        self.lookforurlinhtml.setToolTip(_("Look for first valid story URL inside EPUB text if not found in metadata.\nSomewhat risky, could find wrong URL depending on EPUB content.\nAlso finds and corrects bad ffnet URLs from ficsaver.com files."))
        self.lookforurlinhtml.setChecked(prefs['lookforurlinhtml'])
        self.l.addWidget(self.lookforurlinhtml)

        self.mark = QCheckBox(_("Mark added/updated books when finished?"),self)
        self.mark.setToolTip(_("Mark added/updated books when finished.  Use with option below.\nYou can also manually search for 'marked:ffdl_success'.\n'marked:ffdl_failed' is also available, or search 'marked:ffdl' for both."))
        self.mark.setChecked(prefs['mark'])
        self.l.addWidget(self.mark)

        self.showmarked = QCheckBox(_("Show Marked books when finished?"),self)
        self.showmarked.setToolTip(_("Show Marked added/updated books only when finished.\nYou can also manually search for 'marked:ffdl_success'.\n'marked:ffdl_failed' is also available, or search 'marked:ffdl' for both."))
        self.showmarked.setChecked(prefs['showmarked'])
        self.l.addWidget(self.showmarked)

        gui_gb = groupbox = QGroupBox(_("GUI Options"))
        self.l = QVBoxLayout()
        groupbox.setLayout(self.l)

        self.urlsfromclip = QCheckBox(_('Take URLs from Clipboard?'),self)
        self.urlsfromclip.setToolTip(_('Prefill URLs from valid URLs in Clipboard when Adding New.'))
        self.urlsfromclip.setChecked(prefs['urlsfromclip'])
        self.l.addWidget(self.urlsfromclip)

        self.updatedefault = QCheckBox(_('Default to Update when books selected?'),self)
        self.updatedefault.setToolTip(_('The top FanFictionDownLoader plugin button will start Update if\nbooks are selected.  If unchecked, it will always bring up \'Add New\'.'))
        self.updatedefault.setChecked(prefs['updatedefault'])
        self.l.addWidget(self.updatedefault)

        self.adddialogstaysontop = QCheckBox(_("Keep 'Add New from URL(s)' dialog on top?"),self)
        self.adddialogstaysontop.setToolTip(_("Instructs the OS and Window Manager to keep the 'Add New from URL(s)'\ndialog on top of all other windows.  Useful for dragging URLs onto it."))
        self.adddialogstaysontop.setChecked(prefs['adddialogstaysontop'])
        self.l.addWidget(self.adddialogstaysontop)

        misc_gb = groupbox = QGroupBox(_("Misc Options"))
        self.l = QVBoxLayout()
        groupbox.setLayout(self.l)

        # this is a cheat to make it easier for users to realize there's a new include_images features.
        self.includeimages = QCheckBox(_("Include images in EPUBs?"),self)
        self.includeimages.setToolTip(_("Download and include images in EPUB stories.  This is equivalent to adding:%(imgset)s ...to the top of %(pini)s.  Your settings in %(pini)s will override this.")%no_trans)
        self.includeimages.setChecked(prefs['includeimages'])
        self.l.addWidget(self.includeimages)

        self.injectseries = QCheckBox(_("Inject calibre Series when none found?"),self)
        self.injectseries.setToolTip(_("If no series is found, inject the calibre series (if there is one) so it appears on the FFDL title page(not cover)."))
        self.injectseries.setChecked(prefs['injectseries'])
        self.l.addWidget(self.injectseries)

        rej_gb = groupbox = QGroupBox(_("Reject List"))
        self.l = QVBoxLayout()
        groupbox.setLayout(self.l)

        self.rejectlist = QPushButton(_('Edit Reject URL List'), self)
        self.rejectlist.setToolTip(_("Edit list of URLs FFDL will automatically Reject."))
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

        topl.addWidget(defs_gb)

        horz = QHBoxLayout()

        horz.addWidget(cali_gb)

        vert = QVBoxLayout()
        vert.addWidget(gui_gb)
        vert.addWidget(misc_gb)
        vert.addWidget(rej_gb)
        
        horz.addLayout(vert)
        
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
        
    def show_defaults(self):
        text = get_resources('plugin-defaults.ini')
        ShowDefaultsIniDialog(self.windowIcon(),text,self).exec_()

    def show_rejectlist(self):
        d = RejectListDialog(self,
                             rejecturllist.get_list(),
                             rejectreasons=rejecturllist.get_reject_reasons(),
                             header=_("Edit Reject URLs List"),
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
                           title=_("Reject Reasons"),
                           label=_("Customize Reject List Reasons"),
                           tooltip=_("Customize the Reasons presented when Rejecting URLs"))
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
                           reasonslabel=_('Add this reason to all URLs added:'))
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
        
        self.label = QLabel('personal.ini:')
        self.l.addWidget(self.label)

        self.ini = QTextEdit(self)
        try:
            self.ini.setFont(QFont("Courier",
                                   self.plugin_action.gui.font().pointSize()+1))
        except Exception as e:
            logger.error("Couldn't get font: %s"%e)
        self.ini.setLineWrapMode(QTextEdit.NoWrap)
        self.ini.setText(prefs['personal.ini'])
        self.l.addWidget(self.ini)

        self.defaults = QPushButton(_('View Defaults')+' (plugin-defaults.ini)', self)
        self.defaults.setToolTip(_("View all of the plugin's configurable settings\nand their default settings."))
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
        self.label = QLabel(_("Plugin Defaults (%s) (Read-Only)")%'plugin-defaults.ini')
        self.label.setToolTip(_("These are all of the plugin's configurable options\nand their default settings."))
        self.setWindowTitle(_('Plugin Defaults'))
        self.setWindowIcon(icon)
        self.l.addWidget(self.label)
        
        self.ini = QTextEdit(self)
        self.ini.setToolTip(_("These are all of the plugin's configurable options\nand their default settings."))
        try:
            self.ini.setFont(QFont("Courier",
                                   get_gui().font().pointSize()+1))
        except Exception as e:
            logger.error("Couldn't get font: %s"%e)
        self.ini.setLineWrapMode(QTextEdit.NoWrap)
        self.ini.setText(text)
        self.ini.setReadOnly(True)
        self.l.addWidget(self.ini)
        
        self.ok_button = QPushButton(_('OK'), self)
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
        self.send_lists_box = MultiCompleteLineEdit(self)
        self.send_lists_box.setToolTip(_("When enabled, new/updated stories will be automatically added to these lists."))
        self.send_lists_box.update_items_cache(reading_lists)
        self.send_lists_box.setText(prefs['send_lists'])
        horz.addWidget(self.send_lists_box)
        self.l.addLayout(horz)
        
        self.addtoreadlists = QCheckBox(_('Add new/updated stories to "To Read" Reading List(s).'),self)
        self.addtoreadlists.setToolTip(_('Automatically add new/updated stories to these lists in the %(rl)s plugin.\nAlso offers menu option to remove stories from the "To Read" lists.')%no_trans)
        self.addtoreadlists.setChecked(prefs['addtoreadlists'])
        self.l.addWidget(self.addtoreadlists)
            
        horz = QHBoxLayout()
        label = QLabel(_('"To Read" Reading Lists'))
        label.setToolTip(_("When enabled, new/updated stories will be automatically added to these lists."))
        horz.addWidget(label)        
        self.read_lists_box = MultiCompleteLineEdit(self)
        self.read_lists_box.setToolTip(_("When enabled, new/updated stories will be automatically added to these lists."))
        self.read_lists_box.update_items_cache(reading_lists)
        self.read_lists_box.setText(prefs['read_lists'])
        horz.addWidget(self.read_lists_box)
        self.l.addLayout(horz)
        
        self.addtolistsonread = QCheckBox(_('Add stories back to "Send to Device" Reading List(s) when marked "Read".'),self)
        self.addtolistsonread.setToolTip(_('Menu option to remove from "To Read" lists will also add stories back to "Send to Device" Reading List(s)'))
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
            
        label = QLabel(_('The %(gc)s plugin can create cover images for books using various metadata and configurations.  If you have GC installed, FFDL can run GC on new downloads and metadata updates.  Pick a GC setting by site or Default.')%no_trans)
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
        sitelist.insert(0,_("Default"))
        for site in sitelist:
            horz = QHBoxLayout()
            label = QLabel(site)
            if site == _("Default"):
                s = _("On Metadata update, run %(gc)s with this setting, if not selected for specific site.")%no_trans
            else:
                no_trans['site']=site # not ideal, but, meh.
                s = _("On Metadata update, run %(gc)s with this setting for %(site)s stories.")%no_trans

            label.setToolTip(s)
            horz.addWidget(label)
            dropdown = QComboBox(self)
            dropdown.setToolTip(s)
            dropdown.addItem('',QVariant('none'))
            for setting in gc_settings:
                dropdown.addItem(setting,QVariant(setting))
            if site == _("Default"):
                self.gc_dropdowns["Default"] = dropdown
                dropdown.setCurrentIndex(dropdown.findData(QVariant(prefs['gc_site_settings']['Default'])))
            else:
                self.gc_dropdowns[site] = dropdown
            if site in prefs['gc_site_settings']:
                dropdown.setCurrentIndex(dropdown.findData(QVariant(prefs['gc_site_settings'][site])))

            horz.addWidget(dropdown)
            self.sl.addLayout(horz)
        
        self.sl.insertStretch(-1)
        
        self.gcnewonly = QCheckBox(_("Run %(gc)s Only on New Books")%no_trans,self)
        self.gcnewonly.setToolTip(_("Default is to run GC any time the calibre metadata is updated."))
        self.gcnewonly.setChecked(prefs['gcnewonly'])
        self.l.addWidget(self.gcnewonly)

        self.allow_gc_from_ini = QCheckBox(_('Allow %(gcset)s from %(pini)s to override')%no_trans,self)
        self.allow_gc_from_ini.setToolTip(_("The %(pini)s parameter %(gcset)s allows you to choose a GC setting based on metadata rather than site, but it's much more complex.<br \>%(gcset)s is ignored when this is off.")%no_trans)
        self.allow_gc_from_ini.setChecked(prefs['allow_gc_from_ini'])
        self.l.addWidget(self.allow_gc_from_ini)
            
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
            
        self.wordcount = QCheckBox('Word Count',self)
        self.wordcount.setToolTip(tooltip+"\n"+_('Will overwrite word count from FFDL metadata if set to update the same custom column.'))
        self.wordcount.setChecked('WordCount' in prefs['countpagesstats'])
        self.l.addWidget(self.wordcount)

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

        label = QLabel(_("These controls aren't plugin settings as such, but convenience buttons for setting Keyboard shortcuts and getting all the FanFictionDownLoader confirmation dialogs back again."))
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)
        
        keyboard_shortcuts_button = QPushButton(_('Keyboard shortcuts...'), self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(parent_dialog.edit_shortcuts)
        self.l.addWidget(keyboard_shortcuts_button)

        reset_confirmation_button = QPushButton(_('Reset disabled &confirmation dialogs'), self)
        reset_confirmation_button.setToolTip(_('Reset all show me again dialogs for the FanFictionDownLoader plugin'))
        reset_confirmation_button.clicked.connect(self.reset_dialogs)
        self.l.addWidget(reset_confirmation_button)
        
        view_prefs_button = QPushButton(_('&View library preferences...'), self)
        view_prefs_button.setToolTip(_('View data stored in the library database for this plugin'))
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
    'version':_('FFDL Version')
    }

class CustomColumnsTab(QWidget):

    def __init__(self, parent_dialog, plugin_action):
        self.parent_dialog = parent_dialog
        self.plugin_action = plugin_action
        QWidget.__init__(self)
        
        custom_columns = self.plugin_action.gui.library_view.model().custom_columns

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
        
        for key, column in custom_columns.iteritems():

            if column['datatype'] in permitted_values:
                # print("\n============== %s ===========\n"%key)
                # for (k,v) in column.iteritems():
                #     print("column['%s'] => %s"%(k,v))
                horz = QHBoxLayout()
                label = QLabel(column['name'])
                label.setToolTip(_("Update this %s column(%s) with...")%(key,column['datatype']))
                horz.addWidget(label)
                dropdown = QComboBox(self)
                dropdown.addItem('',QVariant('none'))
                for md in permitted_values[column['datatype']]:
                    dropdown.addItem(titleLabels[md],QVariant(md))
                self.custcol_dropdowns[key] = dropdown
                if key in prefs['custom_cols']:
                    dropdown.setCurrentIndex(dropdown.findData(QVariant(prefs['custom_cols'][key])))
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
        
        self.l.addSpacing(5)
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

        label = QLabel(_("The standard calibre metadata columns are listed below.  You may choose whether FFDL will fill each column automatically on updates or only for new books."))
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)
        
        self.stdcol_newonlycheck = {}

        for key, column in columns.iteritems():
            horz = QHBoxLayout()
            label = QLabel(column)
            #label.setToolTip("Update this %s column(%s) with..."%(key,column['datatype']))
            horz.addWidget(label)

            newonlycheck = QCheckBox(_("New Only"),self)
            newonlycheck.setToolTip(_("Write to %s only for new\nbooks, not updates to existing books.")%column)
            self.stdcol_newonlycheck[key] = newonlycheck
            if key in prefs['std_cols_newonly']:
                newonlycheck.setChecked(prefs['std_cols_newonly'][key])
            horz.addWidget(newonlycheck)
            
            self.l.addLayout(horz)
        
        self.l.insertStretch(-1)

