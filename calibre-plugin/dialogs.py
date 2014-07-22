#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2011, Jim Miller'
__docformat__ = 'restructuredtext en'

import logging
logger = logging.getLogger(__name__)

import traceback, re
from functools import partial

import logging
logger = logging.getLogger(__name__)

import urllib
import email

try:
    from PyQt5 import QtWidgets as QtGui
    from PyQt5.Qt import (QDialog, QTableWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                          QPushButton, QLabel, QCheckBox, QIcon, QLineEdit,
                          QComboBox, QProgressDialog, QTimer, QDialogButtonBox,
                          QPixmap, Qt, QAbstractItemView, QTextEdit, pyqtSignal,
                          QGroupBox, QFrame)
except ImportError as e:
    from PyQt4 import QtGui
    from PyQt4.Qt import (QDialog, QTableWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                          QPushButton, QLabel, QCheckBox, QIcon, QLineEdit,
                          QComboBox, QProgressDialog, QTimer, QDialogButtonBox,
                          QPixmap, Qt, QAbstractItemView, QTextEdit, pyqtSignal,
                          QGroupBox, QFrame)

try:
    from calibre.gui2 import QVariant
    del QVariant
except ImportError:
    is_qt4 = False
    convert_qvariant = lambda x: x
else:
    is_qt4 = True
    def convert_qvariant(x):
        vt = x.type()
        if vt == x.String:
            return unicode(x.toString())
        if vt == x.List:
            return [convert_qvariant(i) for i in x.toList()]
        return x.toPyObject()

from calibre.gui2.dialogs.confirm_delete import confirm
from calibre.gui2.complete2 import EditWithComplete

# pulls in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre_plugins.fanfictiondownloader_plugin.common_utils \
    import (ReadOnlyTableWidgetItem, ReadOnlyTextIconWidgetItem, SizePersistedDialog,
            ImageTitleLayout, get_icon)

from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader.geturls import get_urls_from_html, get_urls_from_text
from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader.adapters import getNormalStoryURL

SKIP=_('Skip')
ADDNEW=_('Add New Book')
UPDATE=_('Update EPUB if New Chapters')
UPDATEALWAYS=_('Update EPUB Always')
OVERWRITE=_('Overwrite if Newer')
OVERWRITEALWAYS=_('Overwrite Always')
CALIBREONLY=_('Update Calibre Metadata Only')
collision_order=[SKIP,
                 ADDNEW,
                 UPDATE,
                 UPDATEALWAYS,
                 OVERWRITE,
                 OVERWRITEALWAYS,
                 CALIBREONLY,]

# best idea I've had for how to deal with config/pref saving the
# collision name in english.
SAVE_SKIP='Skip'
SAVE_ADDNEW='Add New Book'
SAVE_UPDATE='Update EPUB if New Chapters'
SAVE_UPDATEALWAYS='Update EPUB Always'
SAVE_OVERWRITE='Overwrite if Newer'
SAVE_OVERWRITEALWAYS='Overwrite Always'
SAVE_CALIBREONLY='Update Calibre Metadata Only'
save_collisions={
    SKIP:SAVE_SKIP,
    ADDNEW:SAVE_ADDNEW,
    UPDATE:SAVE_UPDATE,
    UPDATEALWAYS:SAVE_UPDATEALWAYS,
    OVERWRITE:SAVE_OVERWRITE,
    OVERWRITEALWAYS:SAVE_OVERWRITEALWAYS,
    CALIBREONLY:SAVE_CALIBREONLY,
    SAVE_SKIP:SKIP,
    SAVE_ADDNEW:ADDNEW,
    SAVE_UPDATE:UPDATE,
    SAVE_UPDATEALWAYS:UPDATEALWAYS,
    SAVE_OVERWRITE:OVERWRITE,
    SAVE_OVERWRITEALWAYS:OVERWRITEALWAYS,
    SAVE_CALIBREONLY:CALIBREONLY,
    }
    
anthology_collision_order=[UPDATE,
                           UPDATEALWAYS,
                           OVERWRITEALWAYS]

gpstyle='QGroupBox {border:0; padding-top:10px; padding-bottom:0px; margin-bottom:0px;}' #  background-color:red;

class RejectUrlEntry:

    matchpat=re.compile(r"^(?P<url>[^,]+)(,(?P<fullnote>(((?P<title>.+) by (?P<auth>.+?)( - (?P<note>.+))?)|.*)))?$")
    
    def __init__(self,url_or_line,note=None,title=None,auth=None,
                 addreasontext=None,fromline=False,book_id=None):

        self.url=url_or_line
        self.note=note
        self.title=title
        self.auth=auth
        self.valid=False
        self.book_id=book_id

        if fromline:
            mc = re.match(self.matchpat,url_or_line)
            if mc:
                #print("mc:%s"%mc.groupdict())
                (url,title,auth,note) = mc.group('url','title','auth','note')
                if not mc.group('title'):
                    title=''
                    auth=''
                    note=mc.group('fullnote')
                self.url=url
                self.note=note
                self.title=title
                self.auth=auth
        
        if not self.note:
            if addreasontext:
                self.note = addreasontext
            else:
                self.note = ''
        else:
            if addreasontext:
                self.note = self.note + ' - ' + addreasontext
                
        self.url = getNormalStoryURL(self.url)
        self.valid = self.url != None
                
    def to_line(self):
        # always 'url,'
        return self.url+","+self.fullnote()
        
    def fullnote(self):
        retval = ""
        if self.title and self.auth:
            # don't translate--ends up being saved and confuses regex above.
            retval = retval + "%s by %s"%(self.title,self.auth)
            if self.note:
                retval = retval + " - "
                
        if self.note:
            retval = retval + self.note
            
        return retval

class NotGoingToDownload(Exception):
    def __init__(self,error,icon='dialog_error.png'):
        self.error=error
        self.icon=icon

    def __str__(self):
        return self.error

class DroppableQTextEdit(QTextEdit):
    def __init__(self,parent):
        QTextEdit.__init__(self,parent)

    def dropEvent(self,event):
        # print("event:%s"%event)

        mimetype='text/uri-list'

        urllist=[]
        filelist="%s"%event.mimeData().data(mimetype)
        for f in filelist.splitlines():
            #print("filename:%s"%f)
            if f.endswith(".eml"):
                fhandle = urllib.urlopen(f)
                #print("file:\n%s\n\n"%fhandle.read())
                msg = email.message_from_file(fhandle)
                if msg.is_multipart():
                    for part in msg.walk():
                        #print("part type:%s"%part.get_content_type())
                        if part.get_content_type() == "text/html":
                            #print("URL list:%s"%get_urls_from_data(part.get_payload(decode=True)))
                            urllist.extend(get_urls_from_html(part.get_payload(decode=True)))
                        if part.get_content_type() == "text/plain":
                            #print("part content:text/plain")
                            # print("part content:%s"%part.get_payload(decode=True))
                            urllist.extend(get_urls_from_text(part.get_payload(decode=True)))
                else:
                    urllist.extend(get_urls_from_text("%s"%msg))
        if urllist:
            self.append("\n".join(urllist))
            return None
        return QTextEdit.dropEvent(self,event)
        
    def canInsertFromMimeData(self, source):
        if source.hasUrls():
            return True
        else:
            return QTextEdit.canInsertFromMimeData(self,source)

    def insertFromMimeData(self, source):
        if source.hasText():
            self.append(source.text())
        else:
            return QTextEdit.insertFromMimeData(self, source)
                            
class AddNewDialog(SizePersistedDialog):

    go_signal = pyqtSignal(object, object, object, object)

    def __init__(self, gui, prefs, icon):
        SizePersistedDialog.__init__(self, gui, 'FanFictionDownLoader plugin:add new dialog')
        self.prefs = prefs
        
        self.setMinimumWidth(300)
        self.l = QVBoxLayout()
        self.setLayout(self.l)

        self.setWindowTitle(_('FanFictionDownLoader'))
        self.setWindowIcon(icon)

        self.toplabel=QLabel("Toplabel")
        self.l.addWidget(self.toplabel)
        self.url = DroppableQTextEdit(self)
        self.url.setToolTip("UrlTooltip")
        self.url.setLineWrapMode(QTextEdit.NoWrap)
        self.l.addWidget(self.url)

        self.merge = self.newmerge = False
        
        # elements to hide when doing merge.
        self.mergehide = []
        # elements to show again when doing *update* merge
        self.mergeupdateshow = []

        self.groupbox = QGroupBox(_("Show Download Options"))
        self.groupbox.setCheckable(True)
        self.groupbox.setChecked(False)
        self.groupbox.setFlat(True)
        #print("style:%s"%self.groupbox.styleSheet())
        self.groupbox.setStyleSheet(gpstyle)

        self.gbf = QFrame()
        self.gbl = QVBoxLayout()
        self.gbl.addWidget(self.gbf)
        self.groupbox.setLayout(self.gbl)
        self.gbl = QVBoxLayout()
        self.gbf.setLayout(self.gbl)
        self.l.addWidget(self.groupbox)

        self.gbf.setVisible(False)
        self.groupbox.toggled.connect(self.gbf.setVisible)
        
        horz = QHBoxLayout()
        label = QLabel(_('Output &Format:'))
        self.mergehide.append(label)
        
        self.fileform = QComboBox(self)
        self.fileform.addItem('epub')
        self.fileform.addItem('mobi')
        self.fileform.addItem('html')
        self.fileform.addItem('txt')
        self.fileform.setToolTip(_('Choose output format to create.  May set default from plugin configuration.'))
        self.fileform.activated.connect(self.set_collisions)
        
        horz.addWidget(label)
        label.setBuddy(self.fileform)
        horz.addWidget(self.fileform)
        self.gbl.addLayout(horz)
        self.mergehide.append(self.fileform)

        horz = QHBoxLayout()
        self.collisionlabel = QLabel("CollisionLabel")
        horz.addWidget(self.collisionlabel)
        self.collision = QComboBox(self)
        self.collision.setToolTip("CollisionToolTip")
        # add collision options
        self.set_collisions()
        i = self.collision.findText(save_collisions[prefs['collision']])
        if i > -1:
            self.collision.setCurrentIndex(i)
        self.collisionlabel.setBuddy(self.collision)
        horz.addWidget(self.collision)
        self.gbl.addLayout(horz)
        self.mergehide.append(self.collisionlabel)
        self.mergehide.append(self.collision)
        self.mergeupdateshow.append(self.collisionlabel)
        self.mergeupdateshow.append(self.collision)

        horz = QHBoxLayout()
        self.updatemeta = QCheckBox(_('Update Calibre &Metadata?'),self)
        self.updatemeta.setToolTip(_("Update metadata for existing stories in Calibre from web site?\n(Columns set to 'New Only' in the column tabs will only be set for new books.)"))
        self.updatemeta.setChecked(prefs['updatemeta'])
        horz.addWidget(self.updatemeta)
        self.mergehide.append(self.updatemeta)
        self.mergeupdateshow.append(self.updatemeta)

        self.updateepubcover = QCheckBox(_('Update EPUB Cover?'),self)
        self.updateepubcover.setToolTip(_('Update book cover image from site or defaults (if found) <i>inside</i> the EPUB when EPUB is updated.'))
        self.updateepubcover.setChecked(prefs['updateepubcover'])
        horz.addWidget(self.updateepubcover)
        self.mergehide.append(self.updateepubcover)
        
        self.gbl.addLayout(horz)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.ok_clicked)
        self.button_box.rejected.connect(self.reject)
        self.l.addWidget(self.button_box)

    # invoke the 
    def ok_clicked(self):
        self.dialog_closing(None) # save persistent size.
        self.hide()
        self.go_signal.emit( self.get_ffdl_options(),
                             self.get_urlstext(),
                             self.merge,
                             self.extrapayload )

    def show_dialog(self,
                    url_list_text,
                    callback,
                    show=True,
                    merge=False,
                    newmerge=True,
                    extraoptions={},
                    extrapayload=None):
        # rather than mutex in ffdl_plugin, just bail here if it's
        # already in use.
        if self.isVisible(): return

        try:
            self.go_signal.disconnect()
        except:
            pass # if not already connected.
        self.go_signal.connect(callback)

        self.merge = merge
        self.newmerge = newmerge
        self.extraoptions = extraoptions
        self.extrapayload = extrapayload

        self.groupbox.setVisible(not(self.merge and self.newmerge))
        
        if self.merge:
            self.toplabel.setText(_('Story URL(s) for anthology, one per line:'))
            self.url.setToolTip(_('URLs for stories to include in the anthology, one per line.\nWill take URLs from clipboard, but only valid URLs.'))
            self.collisionlabel.setText(_('If Story Already Exists in Anthology?'))
            self.collision.setToolTip(_("What to do if there's already an existing story with the same URL in the anthology."))
            for widget in self.mergehide:
                widget.setVisible(False)
            if not self.newmerge:
                for widget in self.mergeupdateshow:
                    widget.setVisible(True)
        else:
            for widget in self.mergehide:
                widget.setVisible(True)
            self.toplabel.setText(_('Story URL(s), one per line:'))
            self.url.setToolTip(_('URLs for stories, one per line.\nWill take URLs from clipboard, but only valid URLs.\nAdd [1,5] after the URL to limit the download to chapters 1-5.'))
            self.collisionlabel.setText(_('If Story Already Exists?'))
            self.collision.setToolTip(_("What to do if there's already an existing story with the same URL or title and author."))

        # Need to re-able after hiding/showing
        self.setAcceptDrops(True)
        self.url.setFocus()
            
        if self.prefs['adddialogstaysontop']:
            QDialog.setWindowFlags ( self, Qt.Dialog | Qt.WindowStaysOnTopHint )
        else:
            QDialog.setWindowFlags ( self, Qt.Dialog )

        if not self.merge:
            self.fileform.setCurrentIndex(self.fileform.findText(self.prefs['fileform']))

        # add collision options
        self.set_collisions()
        i = self.collision.findText(save_collisions[self.prefs['collision']])
        if i > -1:
            self.collision.setCurrentIndex(i)
            
        self.updatemeta.setChecked(self.prefs['updatemeta'])
            
        if not self.merge:
            self.updateepubcover.setChecked(self.prefs['updateepubcover'])
                
        self.url.setText(url_list_text)
        if url_list_text:
            self.button_box.button(QDialogButtonBox.Ok).setFocus()
        # restore saved size.
        self.resize_dialog()
        
        if show: # so anthology update can be modal still.
            self.show()
        #self.resize(self.sizeHint())

    def set_collisions(self):
        prev=self.collision.currentText()
        self.collision.clear()
        if self.merge:
            order = anthology_collision_order
        else:
            order = collision_order
        for o in order:
            if self.merge or self.fileform.currentText() == 'epub' or o not in [UPDATE,UPDATEALWAYS]:
                self.collision.addItem(o)
        i = self.collision.findText(prev)
        if i > -1:
            self.collision.setCurrentIndex(i)
        
    def get_ffdl_options(self):
        retval =  {
            'fileform': unicode(self.fileform.currentText()),
            'collision': unicode(self.collision.currentText()),
            'updatemeta': self.updatemeta.isChecked(),
            'updateepubcover': self.updateepubcover.isChecked(),
            'smarten_punctuation':self.prefs['smarten_punctuation']
                }
        
        if self.merge:
            retval['fileform']=='epub'
            retval['updateepubcover']=True
            if self.newmerge:
                retval['updatemeta']=True
                retval['collision']=ADDNEW
            
        return dict(retval.items() + self.extraoptions.items() )

    def get_urlstext(self):
        return unicode(self.url.toPlainText())


class FakeLineEdit():
    def __init__(self):
        pass
    
    def text(self):
        pass
    
class CollectURLDialog(SizePersistedDialog):
    '''
    Collect single url for get urls.
    '''
    def __init__(self, gui, title, url_text, epubmerge_plugin=None): 
        SizePersistedDialog.__init__(self, gui, 'FanFictionDownLoader plugin:get story urls')
        self.status=False
        self.anthology=False

        self.setMinimumWidth(300)
        
        self.l = QGridLayout()
        self.setLayout(self.l)

        self.setWindowTitle(title)
        self.l.addWidget(QLabel(title),0,0,1,3)
        
        self.l.addWidget(QLabel("URL:"),1,0)
        self.url = QLineEdit(self)
        self.url.setText(url_text)
        self.l.addWidget(self.url,1,1,1,2)
   
        self.indiv_button = QPushButton(_('For Individual Books'), self)
        self.indiv_button.setToolTip(_('Get URLs and go to dialog for individual story downloads.'))
        self.indiv_button.clicked.connect(self.indiv)
        self.l.addWidget(self.indiv_button,2,0)

        self.merge_button = QPushButton(_('For Anthology Epub'), self)
        self.merge_button.setToolTip(_('Get URLs and go to dialog for Anthology download.\nRequires %s plugin.')%'EpubMerge 1.3.1+')
        self.merge_button.clicked.connect(self.merge)
        self.l.addWidget(self.merge_button,2,1)
        self.merge_button.setEnabled(epubmerge_plugin!=None)

        self.cancel_button = QPushButton(_('Cancel'), self)
        self.cancel_button.clicked.connect(self.cancel)
        self.l.addWidget(self.cancel_button,2,2)

        # restore saved size.
        self.resize_dialog()

    def indiv(self):
        self.status=True
        self.accept()

    def merge(self):
        self.status=True
        self.anthology=True
        self.accept()

    def cancel(self):
        self.status=False
        self.reject()

class UserPassDialog(QDialog):
    '''
    Need to collect User/Pass for some sites.
    '''
    def __init__(self, gui, site, exception=None):
        QDialog.__init__(self, gui)
        self.status=False

        self.l = QGridLayout()
        self.setLayout(self.l)

        if exception.passwdonly:
            self.setWindowTitle(_('Password'))
            self.l.addWidget(QLabel(_("Author requires a password for this story(%s).")%exception.url),0,0,1,2)
            # user isn't used, but it's easier to still have it for
            # post processing.
            self.user = FakeLineEdit()
        else:
            self.setWindowTitle(_('User/Password'))
            self.l.addWidget(QLabel(_("%s requires you to login to download this story.")%site),0,0,1,2)
        
            self.l.addWidget(QLabel(_("User:")),1,0)
            self.user = QLineEdit(self)
            self.l.addWidget(self.user,1,1)
   
        self.l.addWidget(QLabel(_("Password:")),2,0)
        self.passwd = QLineEdit(self)
        self.passwd.setEchoMode(QLineEdit.Password)
        self.l.addWidget(self.passwd,2,1)
   
        self.ok_button = QPushButton(_('OK'), self)
        self.ok_button.clicked.connect(self.ok)
        self.l.addWidget(self.ok_button,3,0)

        self.cancel_button = QPushButton(_('Cancel'), self)
        self.cancel_button.clicked.connect(self.cancel)
        self.l.addWidget(self.cancel_button,3,1)

        self.resize(self.sizeHint())

    def ok(self):
        self.status=True
        self.hide()

    def cancel(self):
        self.status=False
        self.hide()

class LoopProgressDialog(QProgressDialog):
    '''
    ProgressDialog displayed while fetching metadata for each story.
    '''
    def __init__(self, gui,
                 book_list,
                 foreach_function,
                 finish_function,
                 init_label=_("Fetching metadata for stories..."),
                 win_title=_("Downloading metadata for stories"),
                 status_prefix=_("Fetched metadata for")):
        QProgressDialog.__init__(self,
                                 init_label,
                                 _('Cancel'), 0, len(book_list), gui)
        self.setWindowTitle(win_title)
        self.setMinimumWidth(500)
        self.book_list = book_list
        self.foreach_function = foreach_function
        self.finish_function = finish_function
        self.status_prefix = status_prefix
        self.i = 0
        
        ## self.do_loop does QTimer.singleShot on self.do_loop also.
        ## A weird way to do a loop, but that was the example I had.
        QTimer.singleShot(0, self.do_loop)
        self.exec_()

    def updateStatus(self):
        self.setLabelText("%s %d / %d"%(self.status_prefix,self.i+1,len(self.book_list)))
        self.setValue(self.i+1)
        #print(self.labelText())

    def do_loop(self):

        if self.i == 0:
            self.setValue(0)

        book = self.book_list[self.i]
        try:
            ## collision spec passed into getadapter by partial from ffdl_plugin
            ## no retval only if it exists, but collision is SKIP
            self.foreach_function(book)
            
        except NotGoingToDownload as d:
            book['good']=False
            book['comment']=unicode(d)
            book['icon'] = d.icon

        except Exception as e:
            book['good']=False
            book['comment']=unicode(e)
            logger.error("Exception: %s:%s"%(book,unicode(e)))
            traceback.print_exc()
            
        self.updateStatus()
        self.i += 1
            
        if self.i >= len(self.book_list) or self.wasCanceled():
            return self.do_when_finished()
        else:
            QTimer.singleShot(0, self.do_loop)

    def do_when_finished(self):
        self.hide()
        # Queues a job to process these books in the background.
        self.finish_function(self.book_list)

class AboutDialog(QDialog):

    def __init__(self, parent, icon, text):
        QDialog.__init__(self, parent)
        self.resize(400, 250)
        self.l = QGridLayout()
        self.setLayout(self.l)
        self.logo = QLabel()
        self.logo.setMaximumWidth(110)
        self.logo.setPixmap(QPixmap(icon.pixmap(100,100)))
        self.label = QLabel(text)
        self.label.setOpenExternalLinks(True)
        self.label.setWordWrap(True)
        self.setWindowTitle(_('About FanFictionDownLoader'))
        self.setWindowIcon(icon)
        self.l.addWidget(self.logo, 0, 0)
        self.l.addWidget(self.label, 0, 1)
        self.bb = QDialogButtonBox(self)
        b = self.bb.addButton(_('OK'), self.bb.AcceptRole)
        b.setDefault(True)
        self.l.addWidget(self.bb, 2, 0, 1, -1)
        self.bb.accepted.connect(self.accept)

class IconWidgetItem(ReadOnlyTextIconWidgetItem):
    def __init__(self, text, icon, sort_key):
        ReadOnlyTextIconWidgetItem.__init__(self, text, icon)
        self.sort_key = sort_key

    #Qt uses a simple < check for sorting items, override this to use the sortKey
    def __lt__(self, other):
        return self.sort_key < other.sort_key

class AuthorTableWidgetItem(ReadOnlyTableWidgetItem):
    def __init__(self, text, sort_key):
        ReadOnlyTableWidgetItem.__init__(self, text)
        self.sort_key = sort_key

    #Qt uses a simple < check for sorting items, override this to use the sortKey
    def __lt__(self, other):
        return self.sort_key.lower() < other.sort_key.lower()

class UpdateExistingDialog(SizePersistedDialog):
    def __init__(self, gui, header, prefs, icon, books,
                 save_size_name='fanfictiondownloader_plugin:update list dialog'):
        SizePersistedDialog.__init__(self, gui, save_size_name)

        self.prefs = prefs
        self.setWindowTitle(header)
        self.setWindowIcon(icon)
        
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        title_layout = ImageTitleLayout(self, 'images/icon.png',
                                        header)
        layout.addLayout(title_layout)
        books_layout = QHBoxLayout()
        layout.addLayout(books_layout)

        self.books_table = StoryListTableWidget(self)
        books_layout.addWidget(self.books_table)

        button_layout = QVBoxLayout()
        books_layout.addLayout(button_layout)

        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        button_layout.addItem(spacerItem)
        self.remove_button = QtGui.QToolButton(self)
        self.remove_button.setToolTip(_('Remove selected books from the list'))
        self.remove_button.setIcon(get_icon('list_remove.png'))
        self.remove_button.clicked.connect(self.remove_from_list)
        button_layout.addWidget(self.remove_button)
        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        button_layout.addItem(spacerItem1)

        options_layout = QHBoxLayout()

        groupbox = QGroupBox(_("Show Download Options"))
        groupbox.setCheckable(True)
        groupbox.setChecked(False)
        groupbox.setFlat(True)
        groupbox.setStyleSheet(gpstyle)

        gbf = QFrame()
        gbl = QVBoxLayout()
        gbl.addWidget(gbf)
        groupbox.setLayout(gbl)
        gbl = QHBoxLayout()
        gbf.setLayout(gbl)
        options_layout.addWidget(groupbox)

        gbf.setVisible(False)
        groupbox.toggled.connect(gbf.setVisible)
        
        label = QLabel(_('Output &Format:'))
        gbl.addWidget(label)
        self.fileform = QComboBox(self)
        self.fileform.addItem('epub')
        self.fileform.addItem('mobi')
        self.fileform.addItem('html')
        self.fileform.addItem('txt')
        self.fileform.setCurrentIndex(self.fileform.findText(prefs['fileform']))
        self.fileform.setToolTip(_('Choose output format to create.  May set default from plugin configuration.'))
        self.fileform.activated.connect(self.set_collisions)
        label.setBuddy(self.fileform)
        gbl.addWidget(self.fileform)
        
        label = QLabel(_('Update Mode:'))
        gbl.addWidget(label)
        self.collision = QComboBox(self)
        self.collision.setToolTip(_("What sort of update to perform.  May set default from plugin configuration."))
        # add collision options
        self.set_collisions()
        i = self.collision.findText(save_collisions[prefs['collision']])
        if i > -1:
            self.collision.setCurrentIndex(i)
        label.setBuddy(self.collision)
        gbl.addWidget(self.collision)

        self.updatemeta = QCheckBox(_('Update Calibre &Metadata?'),self)
        self.updatemeta.setToolTip(_("Update metadata for existing stories in Calibre from web site?\n(Columns set to 'New Only' in the column tabs will only be set for new books.)"))
        self.updatemeta.setChecked(prefs['updatemeta'])
        gbl.addWidget(self.updatemeta)
                
        self.updateepubcover = QCheckBox(_('Update EPUB Cover?'),self)
        self.updateepubcover.setToolTip(_('Update book cover image from site or defaults (if found) <i>inside</i> the EPUB when EPUB is updated.'))
        self.updateepubcover.setChecked(prefs['updateepubcover'])
        gbl.addWidget(self.updateepubcover)


        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        options_layout.addWidget(button_box)
        
        layout.addLayout(options_layout)
        
        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()
        self.books_table.populate_table(books)

    def set_collisions(self):
        prev=self.collision.currentText()
        self.collision.clear()
        for o in collision_order:
            if o not in [ADDNEW,SKIP] and \
                    (self.fileform.currentText() == 'epub' or o not in [UPDATE,UPDATEALWAYS]):
                self.collision.addItem(o)        
        i = self.collision.findText(prev)
        if i > -1:
            self.collision.setCurrentIndex(i)
        
    def remove_from_list(self):
        self.books_table.remove_selected_rows()

    def get_books(self):
        return self.books_table.get_books()

    def get_ffdl_options(self):
        return {
            'fileform': unicode(self.fileform.currentText()),
            'collision': unicode(self.collision.currentText()),
            'updatemeta': self.updatemeta.isChecked(),
            'updateepubcover': self.updateepubcover.isChecked(),
            'smarten_punctuation':self.prefs['smarten_punctuation']
            }

class StoryListTableWidget(QTableWidget):

    def __init__(self, parent):
        QTableWidget.__init__(self, parent)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

    def populate_table(self, books):
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(books))
        header_labels = ['',_('Title'), _('Author'), 'URL', _('Comment')]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.horizontalHeader().setStretchLastSection(True)
        #self.verticalHeader().setDefaultSectionSize(24)
        self.verticalHeader().hide()

        self.books={}
        for row, book in enumerate(books):
            self.populate_table_row(row, book)
            self.books[row] = book

        # turning True breaks up/down.  Do we need either sorting or up/down?
        self.setSortingEnabled(True)
        self.resizeColumnsToContents()
        self.setMinimumColumnWidth(1, 100)
        self.setMinimumColumnWidth(2, 100)
        self.setMinimumColumnWidth(3, 100)
        self.setMinimumSize(300, 0)
        # if len(books) > 0:
        #     self.selectRow(0)
        self.sortItems(1)
        self.sortItems(0)

    def setMinimumColumnWidth(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)

    def populate_table_row(self, row, book):
        if book['good']:
            icon = get_icon('ok.png')
            val = 0
        else:
            icon = get_icon('minus.png')
            val = 1
        if 'icon' in book:
            icon = get_icon(book['icon'])

        status_cell = IconWidgetItem(None,icon,val)
        status_cell.setData(Qt.UserRole, val)
        self.setItem(row, 0, status_cell)
        
        title_cell = ReadOnlyTableWidgetItem(book['title'])
        title_cell.setData(Qt.UserRole, row)
        self.setItem(row, 1, title_cell)
        
        self.setItem(row, 2, AuthorTableWidgetItem(", ".join(book['author']), ", ".join(book['author_sort'])))
        
        url_cell = ReadOnlyTableWidgetItem(book['url'])
        self.setItem(row, 3, url_cell)
        
        comment_cell = ReadOnlyTableWidgetItem(book['comment'])
        self.setItem(row, 4, comment_cell)

    def get_books(self):
        books = []
        #print("=========================\nbooks:%s"%self.books)
        for row in range(self.rowCount()):
            rnum = convert_qvariant(self.item(row, 1).data(Qt.UserRole))
            book = self.books[rnum]
            books.append(book)
        return books

    def remove_selected_rows(self):
        self.setFocus()
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        message = '<p>'+_('Are you sure you want to remove this book from the list?')
        if len(rows) > 1:
            message = '<p>'+_('Are you sure you want to remove the selected %d books from the list?')%len(rows)
        if not confirm(message,'fanfictiondownloader_delete_item', self):
            return
        first_sel_row = self.currentRow()
        for selrow in reversed(rows):
            self.removeRow(selrow.row())
        if first_sel_row < self.rowCount():
            self.select_and_scroll_to_row(first_sel_row)
        elif self.rowCount() > 0:
            self.select_and_scroll_to_row(first_sel_row - 1)

    def select_and_scroll_to_row(self, row):
        self.selectRow(row)
        self.scrollToItem(self.currentItem())

class RejectListTableWidget(QTableWidget):

    def __init__(self, parent,rejectreasons=[]):
        QTableWidget.__init__(self, parent)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rejectreasons = rejectreasons

    def populate_table(self, reject_list):
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(reject_list))
        header_labels = ['URL', _('Title'), _('Author'), _('Note')]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.horizontalHeader().setStretchLastSection(True)
        #self.verticalHeader().setDefaultSectionSize(24)
        self.verticalHeader().hide()

        # it's generally recommended to enable sort after pop, not
        # before.  But then it needs to be sorted on a column and I'd
        # rather keep the order given.
        self.setSortingEnabled(True)
        # row is just row number.
        for row, rejectrow in enumerate(reject_list):
            #print("populating table:%s"%rejectrow.to_line())
            self.populate_table_row(row,rejectrow)

        self.resizeColumnsToContents()
        self.setMinimumColumnWidth(0, 100)
        self.setMinimumColumnWidth(3, 100)
        self.setMinimumSize(300, 0)

    def setMinimumColumnWidth(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)

    def populate_table_row(self, row, rej):

        url_cell = ReadOnlyTableWidgetItem(rej.url)
        url_cell.setData(Qt.UserRole, rej.book_id)
        self.setItem(row, 0, url_cell)
        self.setItem(row, 1, ReadOnlyTableWidgetItem(rej.title))
        self.setItem(row, 2, ReadOnlyTableWidgetItem(rej.auth))
        
        note_cell = EditWithComplete(self,sort_func=lambda x:1)
        
        items = [rej.note]+self.rejectreasons
        note_cell.update_items_cache(items)
        note_cell.show_initial_value(rej.note)
        note_cell.set_separator(None)
        note_cell.setToolTip(_('Select or Edit Reject Note.'))
        self.setCellWidget(row, 3, note_cell)
        
    def remove_selected_rows(self):
        self.setFocus()
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        message = '<p>'+_('Are you sure you want to remove this URL from the list?')
        if len(rows) > 1:
            message = '<p>'+_('Are you sure you want to remove the %d selected URLs from the list?')%len(rows)
        if not confirm(message,'ffdl_rejectlist_delete_item_again', self):
            return
        first_sel_row = self.currentRow()
        for selrow in reversed(rows):
            self.removeRow(selrow.row())
        if first_sel_row < self.rowCount():
            self.select_and_scroll_to_row(first_sel_row)
        elif self.rowCount() > 0:
            self.select_and_scroll_to_row(first_sel_row - 1)

    def select_and_scroll_to_row(self, row):
        self.selectRow(row)
        self.scrollToItem(self.currentItem())

class RejectListDialog(SizePersistedDialog):
    def __init__(self, gui, reject_list,
                 rejectreasons=[],
                 header=_("List of Books to Reject"),
                 icon='rotate-right.png',
                 show_delete=True,
                 show_all_reasons=True,
                 save_size_name='ffdl:reject list dialog'):
        SizePersistedDialog.__init__(self, gui, save_size_name)
      
        self.setWindowTitle(header)
        self.setWindowIcon(get_icon(icon))
      
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        title_layout = ImageTitleLayout(self, icon, header,
                                        '<i></i>'+_('FFDL will remember these URLs and display the note and offer to reject them if you try to download them again later.'))
        layout.addLayout(title_layout)
        rejects_layout = QHBoxLayout()
        layout.addLayout(rejects_layout)

        self.rejects_table = RejectListTableWidget(self,rejectreasons=rejectreasons)
        rejects_layout.addWidget(self.rejects_table)

        button_layout = QVBoxLayout()
        rejects_layout.addLayout(button_layout)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        button_layout.addItem(spacerItem)
        
        self.remove_button = QtGui.QToolButton(self)
        self.remove_button.setToolTip(_('Remove selected URL(s) from the list'))
        self.remove_button.setIcon(get_icon('list_remove.png'))
        self.remove_button.clicked.connect(self.remove_from_list)
        button_layout.addWidget(self.remove_button)

        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        button_layout.addItem(spacerItem1)

        if show_all_reasons:
            self.reason_edit = EditWithComplete(self,sort_func=lambda x:1)
            
            items = ['']+rejectreasons
            self.reason_edit.update_items_cache(items)
            self.reason_edit.show_initial_value('')
            self.reason_edit.set_separator(None)
            self.reason_edit.setToolTip(_("This will be added to whatever note you've set for each URL above."))
            
            horz = QHBoxLayout()
            label = QLabel(_("Add this reason to all URLs added:"))
            label.setToolTip(_("This will be added to whatever note you've set for each URL above."))
            horz.addWidget(label)
            horz.addWidget(self.reason_edit)
            horz.insertStretch(-1)
            layout.addLayout(horz)
                    
        options_layout = QHBoxLayout()

        if show_delete:
            self.deletebooks = QCheckBox(_('Delete Books (including books without FanFiction URLs)?'),self)
            self.deletebooks.setToolTip(_("Delete the selected books after adding them to the Rejected URLs list."))
            self.deletebooks.setChecked(True)
            options_layout.addWidget(self.deletebooks)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        options_layout.addWidget(button_box)
      
        layout.addLayout(options_layout)
      
        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()
        self.rejects_table.populate_table(reject_list)

    def remove_from_list(self):
        self.rejects_table.remove_selected_rows()

    def get_reject_list(self):
        rejectrows = []
        for row in range(self.rejects_table.rowCount()):
            url = unicode(self.rejects_table.item(row, 0).text()).strip()
            book_id =convert_qvariant(self.rejects_table.item(row, 0).data(Qt.UserRole))
            title = unicode(self.rejects_table.item(row, 1).text()).strip()
            auth = unicode(self.rejects_table.item(row, 2).text()).strip()
            note = unicode(self.rejects_table.cellWidget(row, 3).currentText()).strip()
            rejectrows.append(RejectUrlEntry(url,note,title,auth,self.get_reason_text(),book_id=book_id))
        return rejectrows

    def get_reject_list_ids(self):
        rejectrows = []
        for row in range(self.rejects_table.rowCount()):
            book_id = convert_qvariant(self.rejects_table.item(row, 0).data(Qt.UserRole))
            if book_id:
                rejectrows.append(book_id)
        return rejectrows

    def get_reason_text(self):
        try:
            return unicode(self.reason_edit.currentText()).strip()
        except:
            # doesn't have self.reason_edit when editing existing list.
            return None
    
    def get_deletebooks(self):
        return self.deletebooks.isChecked()

class EditTextDialog(QDialog):

    def __init__(self, parent, text,
                 icon=None, title=None, label=None, tooltip=None,
                 rejectreasons=[],reasonslabel=None
                 ):
        QDialog.__init__(self, parent)
        self.resize(600, 500)
        self.l = QVBoxLayout()
        self.setLayout(self.l)
        self.label = QLabel(label)
        if title:
            self.setWindowTitle(title)
        if icon:
            self.setWindowIcon(icon)
        self.l.addWidget(self.label)
        
        self.textedit = QTextEdit(self)
        self.textedit.setLineWrapMode(QTextEdit.NoWrap)
        self.textedit.setText(text)
        self.l.addWidget(self.textedit)

        if tooltip:
            self.label.setToolTip(tooltip)
            self.textedit.setToolTip(tooltip)

        if rejectreasons or reasonslabel:
            self.reason_edit = EditWithComplete(self,sort_func=lambda x:1)
            
            items = ['']+rejectreasons
            self.reason_edit.update_items_cache(items)
            self.reason_edit.show_initial_value('')
            self.reason_edit.set_separator(None)
            self.reason_edit.setToolTip(reasonslabel)
            
            if reasonslabel:
                horz = QHBoxLayout()
                label = QLabel(reasonslabel)
                label.setToolTip(reasonslabel)
                horz.addWidget(label)
                horz.addWidget(self.reason_edit)
                self.l.addLayout(horz)
            else:
                self.l.addWidget(self.reason_edit)
            
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.l.addWidget(button_box)

    def get_plain_text(self):
        return unicode(self.textedit.toPlainText())

    def get_reason_text(self):
        return unicode(self.reason_edit.currentText()).strip()
    
