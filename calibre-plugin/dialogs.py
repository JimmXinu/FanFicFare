#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2011, Jim Miller'
__docformat__ = 'restructuredtext en'

from PyQt4.Qt import (QDialog, QMessageBox, QVBoxLayout, QGridLayout,
                      QPushButton, QProgressDialog, QString, QLabel,
                      QTextEdit, QLineEdit, QInputDialog, QComboBox,
                      QProgressDialog, QTimer )

from calibre.gui2 import error_dialog, warning_dialog, question_dialog, info_dialog

from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader import adapters,writers,exceptions

class DownloadDialog(QDialog):

    def __init__(self, gui, icon, do_user_config, start_downloads):
        QDialog.__init__(self, gui)
        self.gui = gui
        self.do_user_config = do_user_config
        self.start_downloads = start_downloads

        self.setMinimumWidth(300)
        self.l = QVBoxLayout()
        self.setLayout(self.l)

        self.setWindowTitle('FanFictionDownLoader')
        self.setWindowIcon(icon)

        self.l.addWidget(QLabel('Story URL(s), one per line:'))
        self.url = QTextEdit(self)
        self.url.setLineWrapMode(QTextEdit.NoWrap)
#         self.url.setText('''http://test1.com?sid=6700
# http://test1.com?sid=6701
# http://test1.com?sid=6702
# http://test1.com?sid=6703
# http://test1.com?sid=6704
# http://test1.com?sid=6705
# http://test1.com?sid=6706
# http://test1.com?sid=6707
# http://test1.com?sid=6708
# http://test1.com?sid=6709
# ''')
        self.l.addWidget(self.url)
        
        # self.url = QLineEdit(self)
        # self.url.setText('http://test1.com?sid=12345')
        # self.l.addWidget(self.url)

        self.l.addWidget(QLabel('Output Format:'))
        self.fileform = QComboBox(self)
        self.fileform.addItem('epub')
        self.fileform.addItem('mobi')
        self.fileform.addItem('html')
        self.fileform.addItem('txt')
        self.l.addWidget(self.fileform)

        self.ffdl_button = QPushButton(
            'Download Stories', self)
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
        QMessageBox.about(self, 'About the FanFictionDownLoader Plugin',
                text.decode('utf-8'))

    def ffdl(self):
        self.start_downloads(unicode(self.url.toPlainText()),
                             unicode(self.fileform.currentText()))
        self.hide()

    def config(self):
        self.do_user_config(parent=self)

        
class UserPassDialog(QDialog):
    '''
    Need to collect User/Pass for some sites.
    '''
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

class MetadataProgressDialog(QProgressDialog):
    '''
    ProgressDialog displayed while fetching metadata for each story.
    '''
    def __init__(self, gui, loop_list, fileform, getadapter_function, download_list_function, db):
        QProgressDialog.__init__(self,
                                 "Fetching metadata for stories...",
                                 QString(), 0, len(loop_list), gui)
        self.setWindowTitle("Downloading metadata for stories")
        self.setMinimumWidth(500)
        self.gui = gui
        self.db = db
        self.loop_list = loop_list
        self.fileform = fileform
        self.getadapter_function = getadapter_function
        self.download_list_function = download_list_function
        self.i, self.loop_bad, self.loop_good = 0, [], []
        
        ## self.do_loop does QTimer.singleShot on self.do_loop also.
        ## A weird way to do a loop, but that was the example I had.
        QTimer.singleShot(0, self.do_loop)
        self.exec_()

    def updateStatus(self):
        self.setLabelText("Fetched metadata for %d of %d"%(self.i+1,len(self.loop_list)))
        self.setValue(self.i+1)
        print(self.labelText())

    def do_loop(self):
        print("self.i:%d"%self.i)

        if self.i == 0:
            self.setValue(0)

        if self.i >= len(self.loop_list) or self.wasCanceled():
            return self.do_when_finished()

        else:
            current = self.loop_list[self.i]
            try:
                retval = self.getadapter_function(current,self.fileform)
                self.loop_good.append((current,retval))
            except Exception as e:
                self.loop_bad.append((current,e))
            
            self.updateStatus()
            self.i += 1
            QTimer.singleShot(0, self.do_loop)

    def do_when_finished(self):
        self.hide()
        
        # Queues a job to process these ePub/Mobi books in the background.
        self.download_list_function(self.loop_good,self.fileform)
        
        if self.loop_bad != []:
            res = []
            for j in self.loop_bad:
                res.append('%s : %s'%j)
            msg = '%s' % '\n'.join(res)
            warning_dialog(self.gui, _('Could not get metadata for some stories'),
                _('Could not get metadata for %d of %d stories.') %
                (len(self.loop_bad), len(self.loop_list)),
                msg).exec_()
        else:
            info_dialog(self.gui, "Starting Downloads",
                        "Got metadata and started download for %d stories."%len(self.loop_good),
                        show_copy_button=False).exec_()
        self.gui = None
