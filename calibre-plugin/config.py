#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2011, Jim Miller'
__docformat__ = 'restructuredtext en'

import traceback, copy

from PyQt4.Qt import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                      QTextEdit, QComboBox, QCheckBox, QPushButton)

from calibre.gui2 import dynamic, info_dialog
from calibre.utils.config import JSONConfig
from calibre.gui2.ui import get_gui

from calibre_plugins.fanfictiondownloader_plugin.dialogs \
    import (SKIP, ADDNEW, UPDATE, UPDATEALWAYS, OVERWRITE, OVERWRITEALWAYS,
             CALIBREONLY,collision_order)

from calibre_plugins.fanfictiondownloader_plugin.common_utils \
    import ( get_library_uuid )

# This is where all preferences for this plugin will be stored
# Remember that this name (i.e. plugins/fanfictiondownloader_plugin) is also
# in a global namespace, so make it as unique as possible.
# You should always prefix your config file name with plugins/,
# so as to ensure you dont accidentally clobber a calibre config file
all_prefs = JSONConfig('plugins/fanfictiondownloader_plugin')

# Set defaults used by all.  Library specific settings continue to
# take from here.
all_prefs.defaults['personal.ini'] = get_resources('example.ini')
all_prefs.defaults['updatemeta'] = True
all_prefs.defaults['keeptags'] = False
all_prefs.defaults['urlsfromclip'] = True
all_prefs.defaults['updatedefault'] = True
all_prefs.defaults['fileform'] = 'epub'
all_prefs.defaults['collision'] = OVERWRITE
all_prefs.defaults['deleteotherforms'] = False
all_prefs.defaults['addtolists'] = False

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
            'addtolists']

## fake out so I don't have to change the prefs calls anywhere.  The
## Java programmer in me is offended by op-overloading, but it's very
## tidy.
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
        
    def __getitem__(self,k):            
        prefs = self._get_prefs()
        if k not in prefs:
            ## pulls from all_prefs.defaults automatically if not set
            ## in all_prefs
            return self.all_prefs[k]
        return prefs[k]

    def __setitem__(self,k,v):
        prefs = self._get_prefs()
        prefs[k]=v

prefs = PrefsFacade(all_prefs)
    
class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        
        self.l = QVBoxLayout()
        self.setLayout(self.l)

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
        self.updatemeta.setToolTip('Update title, author, URL, tags, etc for story in Calibre from web site.')
        self.updatemeta.setChecked(prefs['updatemeta'])
        self.l.addWidget(self.updatemeta)

        self.keeptags = QCheckBox('Keep Existing Tags when Updating Metadata?',self)
        self.keeptags.setToolTip('Existing tags will be kept and any new tags added.\nCompleted and In-Progress tags will be still be updated, if known.\nLast Updated tags will be updated if lastupdate in include_subject_tags.')
        self.keeptags.setChecked(prefs['keeptags'])
        self.l.addWidget(self.keeptags)

        self.urlsfromclip = QCheckBox('Take URLs from Clipboard?',self)
        self.urlsfromclip.setToolTip('Prefill URLs from valid URLs in Clipboard when Adding New?')
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

        try:
            ## XXX hide when Reading List not installed?
            rl_plugin = plugin_action.gui.iactions['Reading List']
            print("Reading Lists:%s"%rl_plugin.get_list_names())
            
            self.addtolists = QCheckBox('Add new/updated stories to Reading List(s)?',self)
            self.addtolists.setToolTip('Check this to automatically add new/updated stories to list in the Reading List plugin.')
            self.addtolists.setChecked(prefs['addtolists'])
            self.l.addWidget(self.addtolists)
        except Exception as e:
            print("no Reading List available:%s"%unicode(e))
            traceback.print_exc()
        
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
        
        reset_confirmation_button = QPushButton(_('Reset disabled &confirmation dialogs'), self)
        reset_confirmation_button.setToolTip(_(
                    'Reset all show me again dialogs for the FanFictionDownLoader plugin'))
        reset_confirmation_button.clicked.connect(self.reset_dialogs)
        self.l.addWidget(reset_confirmation_button)
        
    def set_collisions(self):
        prev=self.collision.currentText()
        self.collision.clear()
        for o in collision_order:
            if self.fileform.currentText() == 'epub' or o not in [UPDATE,UPDATEALWAYS]:
                self.collision.addItem(o)
        i = self.collision.findText(prev)
        if i > -1:
            self.collision.setCurrentIndex(i)
        
    def save_settings(self):
        prefs['fileform'] = unicode(self.fileform.currentText())
        prefs['collision'] = unicode(self.collision.currentText())
        prefs['updatemeta'] = self.updatemeta.isChecked()
        prefs['keeptags'] = self.keeptags.isChecked()
        prefs['urlsfromclip'] = self.urlsfromclip.isChecked()
        prefs['updatedefault'] = self.updatedefault.isChecked()
        prefs['deleteotherforms'] = self.deleteotherforms.isChecked()
        prefs['addtolists'] = self.addtolists.isChecked()
        
        ini = unicode(self.ini.toPlainText())
        if ini:
            prefs['personal.ini'] = ini
        else:
            # if they've removed everything, clear it so they get the
            # default next time.
            del prefs['personal.ini']
        
    def show_defaults(self):
        text = get_resources('plugin-defaults.ini')
        ShowDefaultsIniDialog(self.windowIcon(),text,self).exec_()

    def reset_dialogs(self):
        for key in dynamic.keys():
            if key.startswith('fanfictiondownloader_') and key.endswith('_again') \
                                                  and dynamic[key] is False:
                dynamic[key] = True
        info_dialog(self, _('Done'),
                _('Confirmation dialogs have all been reset'), show=True)

        
class ShowDefaultsIniDialog(QDialog):

    def __init__(self, icon, text, parent=None):
        QDialog.__init__(self, parent)
        self.resize(600, 500)
        self.l = QVBoxLayout()
        self.setLayout(self.l)
        self.label = QLabel("Plugin Defaults (Read-Only)")
        self.label.setToolTip("These all of the plugin's configurable settings\nand their default settings.")
        self.setWindowTitle(_('Plugin Defaults'))
        self.setWindowIcon(icon)
        self.l.addWidget(self.label)
        
        self.ini = QTextEdit(self)
        self.ini.setToolTip("These all of the plugin's configurable settings\nand their default settings.")
        self.ini.setLineWrapMode(QTextEdit.NoWrap)
        self.ini.setText(text)
        self.ini.setReadOnly(True)
        self.l.addWidget(self.ini)
        
        self.ok_button = QPushButton('OK', self)
        self.ok_button.clicked.connect(self.hide)
        self.l.addWidget(self.ok_button)
        
