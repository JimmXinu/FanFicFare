#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2011, Fanficdownloader team'
__docformat__ = 'restructuredtext en'

from PyQt4.Qt import (QDialog, QMessageBox, QVBoxLayout, QGridLayout, QPushButton, QProgressDialog, QString,
                      QLabel, QLineEdit, QInputDialog, QComboBox, QProgressDialog, QTimer )

from calibre.gui2 import error_dialog, warning_dialog, question_dialog

from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader import adapters,writers,exceptions

class DownloadDialog(QDialog):

    def __init__(self, gui, icon, do_user_config, pluginaction):
        QDialog.__init__(self, gui)
        self.gui = gui
        self.do_user_config = do_user_config
        self.pluginaction = pluginaction

        self.l = QVBoxLayout()
        self.setLayout(self.l)

        self.setWindowTitle('FanFictionDownLoader')
        self.setWindowIcon(icon)

        self.l.addWidget(QLabel('Story URL:'))
        self.url = QLineEdit(self)
        self.url.setText('http://test1.com?sid=12345')
        self.l.addWidget(self.url)

        self.l.addWidget(QLabel('Output Format:'))
        self.fileform = QComboBox(self)
        self.fileform.addItem('epub')
        self.fileform.addItem('mobi')
        self.fileform.addItem('html')
        self.fileform.addItem('txt')
        self.l.addWidget(self.fileform)

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
        self.pluginaction.start_downloads(unicode(self.url.text()),
                                     unicode(self.fileform.currentText()))
        self.hide()

    def config(self):
        self.do_user_config(parent=self)
        # Apply the changes
        #self.label.setText(prefs['hello_world_msg'])

class UserPassDialog(QDialog):
    
    def __init__(self, gui, site):
        QDialog.__init__(self, gui)
        self.gui = gui
        self.status=False
        self.setWindowTitle('User/Password')

        self.l = QGridLayout()
        self.setLayout(self.l)

        self.l.addWidget(QLabel("%s requires you to login to download this story."%site),0,0,1,2)
        
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

class QueueProgressDialog(QProgressDialog):

    def __init__(self, gui, title, loop_list, fileform, loop_function, enqueue_function, db):
        QProgressDialog.__init__(self, title, QString(), 0, len(loop_list), gui)
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self.gui = gui
        self.db = db
        self.loop_list = loop_list
        self.fileform = fileform
        self.loop_function = loop_function
        self.enqueue_function = enqueue_function
        # self.book_ids, self.tdir, self.format_order, self.queue, self.db = \
        #                             book_ids, tdir, format_order, queue, db
        # self.pages_algorithm, self.pages_custom_column = pages_algorithm, pages_col
        # self.words_algorithm, self.words_custom_column = words_algorithm, words_col
        self.i, self.loop_bad, self.loop_good = 0, [], []
        self.setValue(0)
        self.setLabelText("Fetching metadata for %d of %d"%(0,len(self.loop_list)))
        QTimer.singleShot(0, self.do_loop)
        self.exec_()

    def do_loop(self):
        current = self.loop_list[self.i]
        self.i += 1

        try:
            retval = self.loop_function(current,self.fileform)
            self.loop_good.append((current,retval))
        except Exception as e:
            self.loop_bad.append(current)

        self.setValue(self.i)
        self.setLabelText("Fetching metadata for %d of %d"%(self.i,len(self.loop_list)))
        if self.i >= len(self.loop_list):
            return self.do_queue()
        else:
            QTimer.singleShot(0, self.do_loop)

    def do_queue(self):
        self.hide()
        if self.loop_bad != []:
            res = []
            for current in self.loop_bad:
                res.append('%s'%current)
            msg = '%s' % '\n'.join(res)
            warning_dialog(self.gui, _('Could not get metadata for some stories'),
                _('Could not get metadata for %d of %d stories.') %
                (len(self.loop_bad), len(self.loop_list)),
                msg).exec_()
        self.gui = None
        # Queue a job to process these ePub/Mobi books
        self.enqueue_function(self.loop_good,self.fileform)
