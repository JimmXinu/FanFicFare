#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2012, Jim Miller'
__docformat__ = 'restructuredtext en'

import traceback, copy
from collections import OrderedDict

from PyQt4.Qt import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QFont, QWidget,
                      QTextEdit, QComboBox, QCheckBox, QPushButton, QTabWidget, QVariant, QScrollArea)

from calibre.gui2 import dynamic, info_dialog
from calibre.utils.config import JSONConfig
from calibre.gui2.ui import get_gui

from calibre_plugins.fanfictiondownloader_plugin.dialogs \
    import (UPDATE, UPDATEALWAYS, OVERWRITE, collision_order)

from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader.adapters import getConfigSections

from calibre_plugins.fanfictiondownloader_plugin.common_utils \
    import ( get_library_uuid, KeyboardConfigDialog, PrefsViewerDialog )

from calibre.gui2.complete import MultiCompleteLineEdit

PREFS_NAMESPACE = 'FanFictionDownLoaderPlugin'
PREFS_KEY_SETTINGS = 'settings'

# Set defaults used by all.  Library specific settings continue to
# take from here.
default_prefs = {}
default_prefs['personal.ini'] = get_resources('plugin-example.ini')

default_prefs['updatemeta'] = True
default_prefs['updatecover'] = False
default_prefs['updateepubcover'] = False
default_prefs['keeptags'] = False
default_prefs['urlsfromclip'] = True
default_prefs['updatedefault'] = True
default_prefs['fileform'] = 'epub'
default_prefs['collision'] = OVERWRITE
default_prefs['deleteotherforms'] = False
default_prefs['adddialogstaysontop'] = False
default_prefs['includeimages'] = False
default_prefs['lookforurlinhtml'] = False
default_prefs['injectseries'] = False

default_prefs['send_lists'] = ''
default_prefs['read_lists'] = ''
default_prefs['addtolists'] = False
default_prefs['addtoreadlists'] = False
default_prefs['addtolistsonread'] = False

default_prefs['gcnewonly'] = False
default_prefs['gc_site_settings'] = {}
default_prefs['allow_gc_from_ini'] = True

default_prefs['countpagesstats'] = []

default_prefs['errorcol'] = ''
default_prefs['custom_cols'] = {}
default_prefs['custom_cols_newonly'] = {}

default_prefs['std_cols_newonly'] = {}

def set_library_config(library_config):
    get_gui().current_db.prefs.set_namespaced(PREFS_NAMESPACE,
                                              PREFS_KEY_SETTINGS,
                                              library_config)
    
def get_library_config():
    db = get_gui().current_db
    library_id = get_library_uuid(db)
    library_config = None
    # Check whether this is a configuration needing to be migrated
    # from json into database.  If so: get it, set it, rename it in json.
    if library_id in old_prefs:
        #print("get prefs from old_prefs")
        library_config = old_prefs[library_id]
        set_library_config(library_config)
        old_prefs["migrated to library db %s"%library_id] = old_prefs[library_id]
        del old_prefs[library_id]

    if library_config is None:
        #print("get prefs from db")
        library_config = db.prefs.get_namespaced(PREFS_NAMESPACE, PREFS_KEY_SETTINGS,
                                                 copy.deepcopy(default_prefs))
    return library_config

# This is where all preferences for this plugin *were* stored
# Remember that this name (i.e. plugins/fanfictiondownloader_plugin) is also
# in a global namespace, so make it as unique as possible.
# You should always prefix your config file name with plugins/,
# so as to ensure you dont accidentally clobber a calibre config file
old_prefs = JSONConfig('plugins/fanfictiondownloader_plugin')

# fake out so I don't have to change the prefs calls anywhere.  The
# Java programmer in me is offended by op-overloading, but it's very
# tidy.
class PrefsFacade():
    def __init__(self,default_prefs):
        self.default_prefs = default_prefs
        self.libraryid = None
        self.current_prefs = None
        
    def _get_prefs(self):
        libraryid = get_library_uuid(get_gui().current_db)
        if self.current_prefs == None or self.libraryid != libraryid:
            #print("self.current_prefs == None(%s) or self.libraryid != libraryid(%s)"%(self.current_prefs == None,self.libraryid != libraryid))
            self.libraryid = libraryid
            self.current_prefs = get_library_config()
        return self.current_prefs
        
    def __getitem__(self,k):            
        prefs = self._get_prefs()
        if k not in prefs:
            # pulls from default_prefs.defaults automatically if not set
            # in default_prefs
            return self.default_prefs[k]
        return prefs[k]

    def __setitem__(self,k,v):
        prefs = self._get_prefs()
        prefs[k]=v
        # self._save_prefs(prefs)

    def __delitem__(self,k):
        prefs = self._get_prefs()
        if k in prefs:
            del prefs[k]

    def save_to_db(self):
        set_library_config(self._get_prefs())
        

prefs = PrefsFacade(default_prefs)
    
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
        prefs['urlsfromclip'] = self.basic_tab.urlsfromclip.isChecked()
        prefs['updatedefault'] = self.basic_tab.updatedefault.isChecked()
        prefs['deleteotherforms'] = self.basic_tab.deleteotherforms.isChecked()
        prefs['adddialogstaysontop'] = self.basic_tab.adddialogstaysontop.isChecked()
        prefs['includeimages'] = self.basic_tab.includeimages.isChecked()
        prefs['lookforurlinhtml'] = self.basic_tab.lookforurlinhtml.isChecked()
        prefs['injectseries'] = self.basic_tab.injectseries.isChecked()

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

        # cust cols
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
        
        self.l = QVBoxLayout()
        self.setLayout(self.l)

        label = QLabel('These settings control the basic features of the plugin--downloading FanFiction.')
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)

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

        self.l.addSpacing(10)        

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

        self.l.addSpacing(10)        

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

        self.l.addSpacing(10)        

        # this is a cheat to make it easier for users to realize there's a new include_images features.
        self.includeimages = QCheckBox("Include images in EPUBs?",self)
        self.includeimages.setToolTip("Download and include images in EPUB stories.  This is equivalent to adding:\n\n[epub]\ninclude_images:true\nkeep_summary_html:true\nmake_firstimage_cover:true\n\n ...to the top of personal.ini.  Your settings in personal.ini will override this.")
        self.includeimages.setChecked(prefs['includeimages'])
        self.l.addWidget(self.includeimages)

        self.lookforurlinhtml = QCheckBox("Search EPUB text for Story URL?",self)
        self.lookforurlinhtml.setToolTip("Look for first valid story URL inside EPUB text if not found in metadata.\nSomewhat risky, could find wrong URL depending on EPUB content.\nAlso finds and corrects bad ffnet URLs from ficsaver.com files.")
        self.lookforurlinhtml.setChecked(prefs['lookforurlinhtml'])
        self.l.addWidget(self.lookforurlinhtml)

        self.injectseries = QCheckBox("Inject calibre Series when none found?",self)
        self.injectseries.setToolTip("If no series is found, inject the calibre series (if there is one) so it appears on the FFDL title page(not cover).")
        self.injectseries.setChecked(prefs['injectseries'])
        self.l.addWidget(self.injectseries)

        self.l.insertStretch(-1)
        
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
                                   self.plugin_action.gui.font().pointSize()+1));
        except Exception as e:
            print("Couldn't get font: %s"%e)
        self.ini.setLineWrapMode(QTextEdit.NoWrap)
        self.ini.setText(prefs['personal.ini'])
        self.l.addWidget(self.ini)

        self.defaults = QPushButton('View Defaults', self)
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
        self.label = QLabel("Plugin Defaults (Read-Only)")
        self.label.setToolTip("These are all of the plugin's configurable options\nand their default settings.")
        self.setWindowTitle(_('Plugin Defaults'))
        self.setWindowIcon(icon)
        self.l.addWidget(self.label)
        
        self.ini = QTextEdit(self)
        self.ini.setToolTip("These are all of the plugin's configurable options\nand their default settings.")
        try:
            self.ini.setFont(QFont("Courier",
                                   get_gui().font().pointSize()+1));
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
        
        self.gcnewonly = QCheckBox("Run Generate Cover Only on New Books",self)
        self.gcnewonly.setToolTip("Default is to run GC any time the calibre metadata is updated.")
        self.gcnewonly.setChecked(prefs['gcnewonly'])
        self.l.addWidget(self.gcnewonly)

        self.allow_gc_from_ini = QCheckBox('Allow generate_cover_settings from personal.ini to override',self)
        self.allow_gc_from_ini.setToolTip("The personal.ini parameter generate_cover_settings allows you to choose a GC setting based on metadata rather than site, but it's much more complex.<br \>generate_cover_settings is ignored when this is off.")
        self.allow_gc_from_ini.setChecked(prefs['allow_gc_from_ini'])
        self.l.addWidget(self.allow_gc_from_ini)
            
        self.l.insertStretch(-1)
        
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
                     'formatname'
                     #,'formatext'   # not useful information.
                     #,'siteabbrev'
                     #,'version'
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
    'dateCreated':'Packaged',
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
    'description':'Summary',
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
        label = QLabel("Special column:")
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)
        
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
