#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2011, Jim Miller'
__docformat__ = 'restructuredtext en'

import traceback, copy

from PyQt4.Qt import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                      QTextEdit, QComboBox, QCheckBox, QPushButton, QTabWidget, QVariant)

from calibre.gui2 import dynamic, info_dialog
from calibre.utils.config import JSONConfig
from calibre.gui2.ui import get_gui

from calibre_plugins.fanfictiondownloader_plugin.dialogs \
    import (SKIP, ADDNEW, UPDATE, UPDATEALWAYS, OVERWRITE, OVERWRITEALWAYS,
             CALIBREONLY,collision_order)

from calibre_plugins.fanfictiondownloader_plugin.common_utils \
    import ( get_library_uuid, KeyboardConfigDialog )

from calibre.gui2.complete import MultiCompleteLineEdit

# This is where all preferences for this plugin will be stored
# Remember that this name (i.e. plugins/fanfictiondownloader_plugin) is also
# in a global namespace, so make it as unique as possible.
# You should always prefix your config file name with plugins/,
# so as to ensure you dont accidentally clobber a calibre config file
all_prefs = JSONConfig('plugins/fanfictiondownloader_plugin')

# Set defaults used by all.  Library specific settings continue to
# take from here.
all_prefs.defaults['personal.ini'] = get_resources('plugin-example.ini')
all_prefs.defaults['updatemeta'] = True
all_prefs.defaults['keeptags'] = False
all_prefs.defaults['urlsfromclip'] = True
all_prefs.defaults['updatedefault'] = True
all_prefs.defaults['fileform'] = 'epub'
all_prefs.defaults['collision'] = OVERWRITE
all_prefs.defaults['deleteotherforms'] = False
all_prefs.defaults['send_lists'] = ''
all_prefs.defaults['read_lists'] = ''
all_prefs.defaults['addtolists'] = False
all_prefs.defaults['addtoreadlists'] = False
all_prefs.defaults['addtolistsonread'] = False
all_prefs.defaults['custom_cols'] = {}

# The list of settings to copy from all_prefs or the previous library
# when config is called for the first time on a library.
copylist = ['personal.ini',
            'updatemeta',
            'keeptags',
            'urlsfromclip',
            'updatedefault',
            'fileform',
            'collision',
            'deleteotherforms',
            'addtolists',
            'addtoreadlists',
            'addtolistsonread']

# fake out so I don't have to change the prefs calls anywhere.  The
# Java programmer in me is offended by op-overloading, but it's very
# tidy.
class PrefsFacade():
    def __init__(self,all_prefs):
        self.all_prefs = all_prefs
        self.lastlibid = None

    def _get_copylist_prefs(self,frompref):
        return filter( lambda x : x[0] in copylist, frompref.items() )
        
    def _get_prefs(self):
        libraryid = get_library_uuid(get_gui().current_db)
        if libraryid not in self.all_prefs:
            if self.lastlibid == None:
                self.all_prefs[libraryid] = dict(self._get_copylist_prefs(self.all_prefs))
            else:
                self.all_prefs[libraryid] = dict(self._get_copylist_prefs(self.all_prefs[self.lastlibid]))
            self.lastlibid = libraryid
            
        return self.all_prefs[libraryid]

    def _save_prefs(self,prefs):
        libraryid = get_library_uuid(get_gui().current_db)
        self.all_prefs[libraryid] = prefs
        
    def __getitem__(self,k):            
        prefs = self._get_prefs()
        if k not in prefs:
            # pulls from all_prefs.defaults automatically if not set
            # in all_prefs
            return self.all_prefs[k]
        return prefs[k]

    def __setitem__(self,k,v):
        prefs = self._get_prefs()
        prefs[k]=v
        self._save_prefs(prefs)

    # to be avoided--can cause unexpected results as possibly ancient
    # all_pref settings may be pulled.
    def __delitem__(self,k):
        prefs = self._get_prefs()
        del prefs[k]
        self._save_prefs(prefs)

prefs = PrefsFacade(all_prefs)
    
class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        
        self.l = QVBoxLayout()
        self.setLayout(self.l)

        tab_widget = QTabWidget(self)
        self.l.addWidget(tab_widget)

        self.basic_tab = BasicTab(self, plugin_action)
        tab_widget.addTab(self.basic_tab, 'Basic')

        self.personalini_tab = PersonalIniTab(self, plugin_action)
        tab_widget.addTab(self.personalini_tab, 'personal.ini')
        
        self.list_tab = ListTab(self, plugin_action)
        tab_widget.addTab(self.list_tab, 'Reading Lists')
        if 'Reading List' not in plugin_action.gui.iactions:
            self.list_tab.setEnabled(False)

        self.columns_tab = ColumnsTab(self, plugin_action)
        tab_widget.addTab(self.columns_tab, 'Custom Columns')

        self.other_tab = OtherTab(self, plugin_action)
        tab_widget.addTab(self.other_tab, 'Other')


    def save_settings(self):

        # basic
        prefs['fileform'] = unicode(self.basic_tab.fileform.currentText())
        prefs['collision'] = unicode(self.basic_tab.collision.currentText())
        prefs['updatemeta'] = self.basic_tab.updatemeta.isChecked()
        prefs['keeptags'] = self.basic_tab.keeptags.isChecked()
        prefs['urlsfromclip'] = self.basic_tab.urlsfromclip.isChecked()
        prefs['updatedefault'] = self.basic_tab.updatedefault.isChecked()
        prefs['deleteotherforms'] = self.basic_tab.deleteotherforms.isChecked()

        if self.list_tab:
            # lists
            prefs['send_lists'] = ', '.join(map( lambda x : x.strip(), filter( lambda x : x.strip() != '', unicode(self.list_tab.send_lists_box.text()).split(','))))
            prefs['read_lists'] = ', '.join(map( lambda x : x.strip(), filter( lambda x : x.strip() != '', unicode(self.list_tab.read_lists_box.text()).split(','))))
            # print("send_lists: %s"%prefs['send_lists'])
            # print("read_lists: %s"%prefs['read_lists'])
            prefs['addtolists'] = self.list_tab.addtolists.isChecked()
            prefs['addtoreadlists'] = self.list_tab.addtoreadlists.isChecked()
            prefs['addtolistsonread'] = self.list_tab.addtolistsonread.isChecked()

        # personal.ini
        ini = unicode(self.personalini_tab.ini.toPlainText())
        if ini:
            prefs['personal.ini'] = ini
        else:
            # if they've removed everything, reset to default.
            prefs['personal.ini'] = get_resources('plugin-example.ini')

        # Custom Columns tab
        colsmap = {}
        for (col,combo) in self.columns_tab.custcol_dropdowns.iteritems():
            val = unicode(combo.itemData(combo.currentIndex()).toString())
            if val != 'none':
                colsmap[col] = val
                #print("colsmap[%s]:%s"%(col,colsmap[col]))
        prefs['custom_cols'] = colsmap
        
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
        
        horz = QHBoxLayout()
        label = QLabel('Default Output &Format:')
        horz.addWidget(label)
        self.fileform = QComboBox(self)
        self.fileform.addItem('epub')
        self.fileform.addItem('mobi')
        self.fileform.addItem('html')
        self.fileform.addItem('txt')
        self.fileform.setCurrentIndex(self.fileform.findText(prefs['fileform']))
        self.fileform.setToolTip('Choose output format to create.  May set default from plugin configuration.')
        self.fileform.activated.connect(self.set_collisions)
        label.setBuddy(self.fileform)
        horz.addWidget(self.fileform)
        self.l.addLayout(horz)

        horz = QHBoxLayout()
        label = QLabel('Default If Story Already Exists?')
        label.setToolTip("What to do if there's already an existing story with the same title and author.")
        horz.addWidget(label)
        self.collision = QComboBox(self)
        # add collision options
        self.set_collisions()
        i = self.collision.findText(prefs['collision'])
        if i > -1:
            self.collision.setCurrentIndex(i)
        # self.collision.setToolTip('Overwrite will replace the existing story.  Add New will create a new story with the same title and author.')
        label.setBuddy(self.collision)
        horz.addWidget(self.collision)
        self.l.addLayout(horz)

        self.updatemeta = QCheckBox('Default Update Calibre &Metadata?',self)
        self.updatemeta.setToolTip('Update title, author, URL, tags, custom columns, etc for story in Calibre from web site.')
        self.updatemeta.setChecked(prefs['updatemeta'])
        self.l.addWidget(self.updatemeta)

        self.keeptags = QCheckBox('Keep Existing Tags when Updating Metadata?',self)
        self.keeptags.setToolTip('Existing tags will be kept and any new tags added.\nCompleted and In-Progress tags will be still be updated, if known.\nLast Updated tags will be updated if lastupdate in include_subject_tags.')
        self.keeptags.setChecked(prefs['keeptags'])
        self.l.addWidget(self.keeptags)

        self.urlsfromclip = QCheckBox('Take URLs from Clipboard?',self)
        self.urlsfromclip.setToolTip('Prefill URLs from valid URLs in Clipboard when Adding New.')
        self.urlsfromclip.setChecked(prefs['urlsfromclip'])
        self.l.addWidget(self.urlsfromclip)

        self.updatedefault = QCheckBox('Default to Update when books selected?',self)
        self.updatedefault.setToolTip('The top FanFictionDownLoader plugin button will start Update if\n'+
                                      'books are selected.  If unchecked, it will always bring up \'Add New\'.')
        self.updatedefault.setChecked(prefs['updatedefault'])
        self.l.addWidget(self.updatedefault)

        self.deleteotherforms = QCheckBox('Delete other existing formats?',self)
        self.deleteotherforms.setToolTip('Check this to automatically delete all other ebook formats when updating an existing book.\nHandy if you have both a Nook(epub) and Kindle(mobi), for example.')
        self.deleteotherforms.setChecked(prefs['deleteotherforms'])
        self.l.addWidget(self.deleteotherforms)
        
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
        self.ini.setLineWrapMode(QTextEdit.NoWrap)
        self.ini.setText(text)
        self.ini.setReadOnly(True)
        self.l.addWidget(self.ini)
        
        self.ok_button = QPushButton('OK', self)
        self.ok_button.clicked.connect(self.hide)
        self.l.addWidget(self.ok_button)
        
class ListTab(QWidget):

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
        
        self.l.insertStretch(-1)
        
    def reset_dialogs(self):
        for key in dynamic.keys():
            if key.startswith('fanfictiondownloader_') and key.endswith('_again') \
                                                  and dynamic[key] is False:
                dynamic[key] = True
        info_dialog(self, _('Done'),
                _('Confirmation dialogs have all been reset'), show=True)

permitted_values = {
    'int' : ['numWords','numChapters'],
    'float' : ['numWords','numChapters'],
    'bool' : ['status-C','status-I'],
    'datetime' : ['datePublished', 'dateUpdated', 'dateCreated'],
    'enumeration' : ['category',
                     'genre',
                     'characters',
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
    'status':'Status',
    'status-C':'Status:Completed',
    'status-I':'Status:In-Progress',
    'characters':'Characters',
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
    'version':'FFD Version'
    }

class ColumnsTab(QWidget):

    def __init__(self, parent_dialog, plugin_action):
        self.parent_dialog = parent_dialog
        self.plugin_action = plugin_action
        QWidget.__init__(self)
        
        self.l = QVBoxLayout()
        self.setLayout(self.l)

        label = QLabel("If you have custom columns defined, they will be listed below.  Choose a metadata value type to fill your columns automatically.")
        label.setWordWrap(True)
        self.l.addWidget(label)
        self.l.addSpacing(5)
        
        self.custcol_dropdowns = {}

        custom_columns = self.plugin_action.gui.library_view.model().custom_columns

        for key, column in custom_columns.iteritems():

            if column['datatype'] in permitted_values:
                # print("\n============== %s ===========\n"%key)
                # for (k,v) in column.iteritems():
                #     print("column['%s'] => %s"%(k,v))
                horz = QHBoxLayout()
                label = QLabel('%s(%s)'%(column['name'],key))
                label.setToolTip("Update this %s column with..."%column['datatype'])
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
                self.l.addLayout(horz)
        
        self.l.insertStretch(-1)

        #print("prefs['custom_cols'] %s"%prefs['custom_cols'])
