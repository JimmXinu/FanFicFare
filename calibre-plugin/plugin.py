#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2011, Fanficdownloader team'
__docformat__ = 'restructuredtext en'

if False:
    # This is here to keep my python error checker from complaining about
    # the builtin functions that will be defined by the plugin loading system
    # You do not need this code in your plugins
    get_icons = get_resources = None

from StringIO import StringIO

from PyQt4.Qt import (QDialog, QVBoxLayout, QGridLayout, QPushButton, QMessageBox,
                      QLabel, QLineEdit, QInputDialog )
from calibre.ptempfile import PersistentTemporaryFile

from calibre.ebooks.metadata.epub import get_metadata

from calibre_plugins.fanfictiondownloader_plugin.config import prefs

from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader import adapters,writers,exceptions

import ConfigParser

class DemoDialog(QDialog):

    def __init__(self, gui, icon, do_user_config):
        QDialog.__init__(self, gui)
        self.gui = gui
        self.do_user_config = do_user_config

        # The current database shown in the GUI
        # db is an instance of the class LibraryDatabase2 from database.py
        # This class has many, many methods that allow you to do a lot of
        # things.
        self.db = gui.current_db

        self.l = QVBoxLayout()
        self.setLayout(self.l)

        self.label = QLabel(prefs['hello_world_msg'])
        self.l.addWidget(self.label)

        self.setWindowTitle('FanFictionDownLoader')
        self.setWindowIcon(icon)

        self.about_button = QPushButton('About', self)
        self.about_button.clicked.connect(self.about)
        self.l.addWidget(self.about_button)

        # self.marked_button = QPushButton(
        #     'Show books with only one format in the calibre GUI', self)
        # self.marked_button.clicked.connect(self.marked)
        # self.l.addWidget(self.marked_button)

        # self.view_button = QPushButton(
        #     'View the most recently added book', self)
        # self.view_button.clicked.connect(self.view)
        # self.l.addWidget(self.view_button)

        self.l.addWidget(QLabel('Story &URL:'))
        
        self.url = QLineEdit(self)
        #self.url.setText('http://test1.com?sid=668')
        self.l.addWidget(self.url)
        self.label.setBuddy(self.url)

        self.ffdl_button = QPushButton(
            'Download Story', self)
        self.ffdl_button.clicked.connect(self.ffdl)
        self.l.addWidget(self.ffdl_button)

        self.conf_button = QPushButton(
                'Configure this plugin', self)
        self.conf_button.clicked.connect(self.config)
        self.l.addWidget(self.conf_button)

        self.resize(self.sizeHint())

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
        QMessageBox.about(self, 'About the Interface Plugin Demo',
                text.decode('utf-8'))

    # def marked(self):
    #     fmt_idx = self.db.FIELD_MAP['formats']
    #     matched_ids = set()
    #     for record in self.db.data.iterall():
    #         # Iterate over all records
    #         fmts = record[fmt_idx]
    #         # fmts is either None or a comma separated list of formats
    #         if fmts and ',' not in fmts:
    #             matched_ids.add(record[0])
    #     # Mark the records with the matching ids
    #     self.db.set_marked_ids(matched_ids)

    #     # Tell the GUI to search for all marked records
    #     self.gui.search.setEditText('marked:true')
    #     self.gui.search.do_search()

    def ffdl(self):

        config = ConfigParser.SafeConfigParser()
        config.readfp(StringIO(get_resources("defaults.ini")))
        config.readfp(StringIO(prefs['personal.ini']))
        print("URL:"+unicode(self.url.text()))
        adapter = adapters.getAdapter(config,unicode(self.url.text()))
        # "http://test1.com?sid=6646") # http://www.fanfiction.net/s/6439390/1/All_Hallows_Eve") #

        try:
            adapter.getStoryMetadataOnly()
        except exceptions.FailedToLogin:
            print("Login Failed, Need Username/Password.")
            userpass = UserPassDialog(self.gui)
            userpass.exec_() # exec_ will make it act modal
            if userpass.status:
                adapter.username = userpass.user.text()
                adapter.password = userpass.passwd.text()
        except exceptions.AdultCheckRequired:
            adult = QMessageBox.warning(self, 'Are You Adult?',
                                        "This story requires that you be an adult.  Please confirm you are an adult in your locale:",
                                        QMessageBox.Yes |  QMessageBox.No,
                                        QMessageBox.No)

            if adult == QMessageBox.Yes:
                adapter.is_adult=True
                
        adapter.getStoryMetadataOnly()
        
        writer = writers.getWriter("epub",config,adapter)
        tmp = PersistentTemporaryFile(".epub")
        print("tmp: "+tmp.name)
        
        writer.writeStory(tmp)
        mi = get_metadata(tmp,extract_cover=False)
        self.db.add_books([tmp],["EPUB"],[mi])
        self.hide()
        QMessageBox.about(self, 'FFDL Metadata',
                          str(adapter.getStoryMetadataOnly()).decode('utf-8'))

    # def view(self):
    #     most_recent = most_recent_id = None
    #     timestamp_idx = self.db.FIELD_MAP['timestamp']

    #     for record in self.db.data:
    #         # Iterate over all currently showing records
    #         timestamp = record[timestamp_idx]
    #         if most_recent is None or timestamp > most_recent:
    #             most_recent = timestamp
    #             most_recent_id = record[0]

    #     if most_recent_id is not None:
    #         # Get the row number of the id as shown in the GUI
    #         row_number = self.db.row(most_recent_id)
    #         # Get a reference to the View plugin
    #         view_plugin = self.gui.iactions['View']
    #         # Ask the view plugin to launch the viewer for row_number
    #         view_plugin._view_books([row_number])

    def config(self):
        self.do_user_config(parent=self)
        # Apply the changes
        self.label.setText(prefs['hello_world_msg'])

class UserPassDialog(QDialog):
    
    def __init__(self, gui):
        QDialog.__init__(self, gui)
        self.gui = gui
        self.status=False
        self.setWindowTitle('User/Password')

        self.l = QGridLayout()
        self.setLayout(self.l)

        self.l.addWidget(QLabel("This site/story requires you to login."),0,0,1,2)
        
        self.l.addWidget(QLabel("User:"),1,0)
        self.user = QLineEdit(self)
        self.l.addWidget(self.user,1,1)
   
        self.l.addWidget(QLabel("Password:"),2,0)
        self.passwd = QLineEdit(self)
        self.l.addWidget(self.passwd,2,1)
   
        self.ok_button = QPushButton('OK', self)
        self.ok_button.clicked.connect(self.ok)
        self.l.addWidget(self.ok_button,3,0)

        self.cancel_button = QPushButton('Cancel', self)
        self.cancel_button.clicked.connect(self.cancel)
        self.l.addWidget(self.cancel_button,3,1)

        self.resize(self.sizeHint())

    def ok(self):
        self.status=True
        self.hide()

    def cancel(self):
        self.status=False
        self.hide()
