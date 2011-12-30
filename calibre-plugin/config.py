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

# urlsfrompriority values
CLIP = 'Clipboard'
SELECTED = 'Selected Stories'

# Set defaults
prefs.defaults['personal.ini'] = get_resources('example.ini')
prefs.defaults['updatemeta'] = True
prefs.defaults['onlyoverwriteifnewer'] = False
prefs.defaults['urlsfromclip'] = True
prefs.defaults['urlsfromselected'] = True
prefs.defaults['urlsfrompriority'] = SELECTED
prefs.defaults['fileform'] = 'epub'
prefs.defaults['collision'] = OVERWRITE
prefs.defaults['deleteotherforms'] = False

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
        
        self.urlsfromclip = QCheckBox('Take URLs from Clipboard?',self)
        self.urlsfromclip.setToolTip('Prefill URLs from valid URLs in Clipboard when starting plugin?')
        self.urlsfromclip.setChecked(prefs['urlsfromclip'])
        self.l.addWidget(self.urlsfromclip)

        self.urlsfromselected = QCheckBox('Take URLs from Selected Stories?',self)
        self.urlsfromselected.setToolTip('Prefill URLs from valid URLs in selected stories when starting plugin?')
        self.urlsfromselected.setChecked(prefs['urlsfromselected'])
        self.l.addWidget(self.urlsfromselected)

        horz = QHBoxLayout()
        label = QLabel('Take URLs from which first:')
        label.setToolTip("If both clipbaord and selected enabled and populated, which is used?")
        horz.addWidget(label)
        self.urlsfrompriority = QComboBox(self)
        self.urlsfrompriority.addItem(SELECTED)
        self.urlsfrompriority.addItem(CLIP)
        self.urlsfrompriority.setCurrentIndex(self.urlsfrompriority.findText(prefs['urlsfrompriority']))
        self.urlsfrompriority.setToolTip('If both clipbaord and selected enabled and populated, which is used?')
        label.setBuddy(self.urlsfrompriority)
        horz.addWidget(self.urlsfrompriority)
        self.l.addLayout(horz)

        self.deleteotherforms = QCheckBox('Delete other existing formats?',self)
        self.deleteotherforms.setToolTip('Check this to automatically delete all other ebook formats when updating an existing book.\nHandy if you have both a Nook(epub) and Kindle(mobi), for example.')
        self.deleteotherforms.setChecked(prefs['deleteotherforms'])
        self.l.addWidget(self.deleteotherforms)
        
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
        prefs['urlsfrompriority'] = unicode(self.urlsfrompriority.currentText())
        prefs['urlsfromclip'] = self.urlsfromclip.isChecked()
        prefs['urlsfromselected'] = self.urlsfromselected.isChecked()
        prefs['onlyoverwriteifnewer'] = self.onlyoverwriteifnewer.isChecked()
        prefs['deleteotherforms'] = self.deleteotherforms.isChecked()
        
        ini = unicode(self.ini.toPlainText())
        if ini:
            prefs['personal.ini'] = ini
        else:
            # if they've removed everything, clear it so they get the
            # default next time.
            del prefs['personal.ini']
        

