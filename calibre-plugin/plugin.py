#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2011, Fanficdownloader team'
__docformat__ = 'restructuredtext en'

from StringIO import StringIO

from PyQt4.Qt import (QDialog, QVBoxLayout, QGridLayout, QPushButton, QMessageBox,
                      QLabel, QLineEdit, QInputDialog, QComboBox )

from calibre.ptempfile import PersistentTemporaryFile
from calibre.ebooks.metadata import MetaInformation

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

        self.setWindowTitle('FanFictionDownLoader')
        self.setWindowIcon(icon)

        self.l.addWidget(QLabel('Story URL:'))
        self.url = QLineEdit(self)
        self.url.setText('http://test1.com?sid=12345')
        self.l.addWidget(self.url)

        self.l.addWidget(QLabel('Output Format:'))
        self.format = QComboBox(self)
        self.format.addItem('epub')
        self.format.addItem('mobi')
        self.format.addItem('html')
        self.format.addItem('txt')
        self.l.addWidget(self.format)

        self.ffdl_button = QPushButton(
            'Download Story', self)
        self.ffdl_button.clicked.connect(self.ffdl)
        self.l.addWidget(self.ffdl_button)

        self.conf_button = QPushButton(
                'Configure this plugin', self)
        self.conf_button.clicked.connect(self.config)
        self.l.addWidget(self.conf_button)

        self.about_button = QPushButton('About', self)
        self.about_button.clicked.connect(self.about)
        self.l.addWidget(self.about_button)

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

    def ffdl(self):

        config = ConfigParser.SafeConfigParser()
        config.readfp(StringIO(get_resources("defaults.ini")))
        config.readfp(StringIO(prefs['personal.ini']))
        print("URL:"+unicode(self.url.text()))
        adapter = adapters.getAdapter(config,unicode(self.url.text()))

        try:
            adapter.getStoryMetadataOnly()
        except exceptions.FailedToLogin:
            print("Login Failed, Need Username/Password.")
            userpass = UserPassDialog(self.gui)
            userpass.exec_() # exec_ will make it act modal
            if userpass.status:
                adapter.username = userpass.user.text()
                adapter.password = userpass.passwd.text()
            else:
                del adapter
                return
        except exceptions.AdultCheckRequired:
            adult = QMessageBox.warning(self, 'Are You Adult?',
                                        "This story requires that you be an adult.  Please confirm you are an adult in your locale:",
                                        QMessageBox.Yes |  QMessageBox.No,
                                        QMessageBox.No)

            if adult == QMessageBox.Yes:
                adapter.is_adult=True
            else:
                del adapter
                return
#        except exceptions.StoryDoesNotExist
                
        story = adapter.getStoryMetadataOnly()
        fileform = unicode(self.format.currentText())
        writer = writers.getWriter(fileform,config,adapter)
        tmp = PersistentTemporaryFile("."+fileform)
        print("tmp: "+tmp.name)
        
        writer.writeStory(tmp)
        
        mi = MetaInformation(story.getMetadata("title"),
                             (story.getMetadata("author"),)) # author is a list.
        mi.set_identifiers({'url':story.getMetadata("storyUrl")})
        mi.publisher = story.getMetadata("site")

        mi.tags = writer.getTags()
        mi.languages = ['en']
        mi.pubdate = story.getMetadataRaw('datePublished').strftime("%Y-%m-%d")
        mi.timestamp = story.getMetadataRaw('dateCreated').strftime("%Y-%m-%d")
        mi.comments = story.getMetadata("description")
        
        self.db.add_books([tmp],[fileform],[mi])
        self.hide()

        # Otherwise list of books doesn't update right away.
        self.gui.library_view.model().books_added(1)
        
        # QMessageBox.about(self, 'FFDL Metadata',
        #                   str(adapter.getStoryMetadataOnly()).decode('utf-8'))
        del adapter
        del writer


    def config(self):
        self.do_user_config(parent=self)
        # Apply the changes
        #self.label.setText(prefs['hello_world_msg'])

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
