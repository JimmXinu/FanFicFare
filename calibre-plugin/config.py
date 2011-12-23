#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2011, Jim Miller'
__docformat__ = 'restructuredtext en'

from PyQt4.Qt import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
                      QComboBox, QCheckBox)

from calibre.utils.config import JSONConfig

from calibre_plugins.fanfictiondownloader_plugin.dialogs import (OVERWRITE, ADDNEW, SKIP,CALIBREONLY,UPDATE)

# This is where all preferences for this plugin will be stored
# Remember that this name (i.e. plugins/fanfictiondownloader_plugin) is also
# in a global namespace, so make it as unique as possible.
# You should always prefix your config file name with plugins/,
# so as to ensure you dont accidentally clobber a calibre config file
prefs = JSONConfig('plugins/fanfictiondownloader_plugin')

# Set defaults
prefs.defaults['personal.ini'] = get_resources('example.ini')
prefs.defaults['updatemeta'] = True
prefs.defaults['onlyoverwriteifnewer'] = False
prefs.defaults['fileform'] = 'epub'
prefs.defaults['collision'] = OVERWRITE

class ConfigWidget(QWidget):

    def __init__(self):
        QWidget.__init__(self)
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
        label.setBuddy(self.fileform)
        horz.addWidget(self.fileform)
        self.l.addLayout(horz)

        horz = QHBoxLayout()
        label = QLabel('Default If Story Already Exists?')
        label.setToolTip("What to do if there's already an existing story with the same title and author.")
        horz.addWidget(label)
        self.collision = QComboBox(self)
        self.collision.addItem(OVERWRITE)
        self.collision.addItem(UPDATE)
        self.collision.addItem(ADDNEW)
        self.collision.addItem(SKIP)
        self.collision.addItem(CALIBREONLY)
        self.collision.setCurrentIndex(self.collision.findText(prefs['collision']))
        self.collision.setToolTip('Overwrite will replace the existing story.  Add New will create a new story with the same title and author.')
        label.setBuddy(self.collision)
        horz.addWidget(self.collision)
        self.l.addLayout(horz)

        self.updatemeta = QCheckBox('Default Update Calibre &Metadata?',self)
        self.updatemeta.setToolTip('Update metadata for story in Calibre from web site?')
        self.updatemeta.setChecked(prefs['updatemeta'])
        self.l.addWidget(self.updatemeta)

        self.onlyoverwriteifnewer = QCheckBox('Default Only Overwrite Story if Newer',self)
        self.onlyoverwriteifnewer.setToolTip("Don't overwrite existing book unless the story on the web site is newer or from the same day.")
        self.onlyoverwriteifnewer.setChecked(prefs['onlyoverwriteifnewer'])
        self.l.addWidget(self.onlyoverwriteifnewer)
        
        self.label = QLabel('personal.ini:')
        self.l.addWidget(self.label)

        self.ini = QTextEdit(self)
        self.ini.setLineWrapMode(QTextEdit.NoWrap)
        self.ini.setText(prefs['personal.ini'])
        self.l.addWidget(self.ini)
        
    def save_settings(self):
        prefs['fileform'] = unicode(self.fileform.currentText())
        prefs['collision'] = unicode(self.collision.currentText())
        prefs['updatemeta'] = self.updatemeta.isChecked()
        prefs['onlyoverwriteifnewer'] = self.onlyoverwriteifnewer.isChecked()
        
        ini = unicode(self.ini.toPlainText())
        if ini:
            prefs['personal.ini'] = ini
        else:
            # if they've removed everything, clear it so they get the
            # default next time.
            del prefs['personal.ini']
        

