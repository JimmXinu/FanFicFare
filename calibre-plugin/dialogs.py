#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2011, Jim Miller'
__docformat__ = 'restructuredtext en'

import traceback
from functools import partial

from PyQt4 import QtGui
from PyQt4.Qt import (QDialog, QTableWidget, QMessageBox, QVBoxLayout, QHBoxLayout,
                      QGridLayout, QPushButton, QProgressDialog, QString, QLabel,
                      QCheckBox, QIcon, QTextCursor, QTextEdit, QLineEdit, QInputDialog,
                      QComboBox, QClipboard, QVariant, QProgressDialog, QTimer,
                      QDialogButtonBox, QPixmap, Qt, QAbstractItemView, SIGNAL,
                      QTableWidgetItem )

from calibre.gui2 import error_dialog, warning_dialog, question_dialog, info_dialog
from calibre.gui2.dialogs.confirm_delete import confirm
from calibre.gui2.complete2 import EditWithComplete

from calibre import confirm_config_name
from calibre.gui2 import dynamic

from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader import adapters,writers,exceptions
from calibre_plugins.fanfictiondownloader_plugin.common_utils \
    import (ReadOnlyTableWidgetItem, ReadOnlyTextIconWidgetItem, SizePersistedDialog,
            ImageTitleLayout, get_icon)

SKIP='Skip'
ADDNEW='Add New Book'
UPDATE='Update EPUB if New Chapters'
UPDATEALWAYS='Update EPUB Always'
OVERWRITE='Overwrite if Newer'
OVERWRITEALWAYS='Overwrite Always'
CALIBREONLY='Update Calibre Metadata Only'
collision_order=[SKIP,
                 ADDNEW,
                 UPDATE,
                 UPDATEALWAYS,
                 OVERWRITE,
                 OVERWRITEALWAYS,
                 CALIBREONLY,]
        
# This is a more than slightly kludgey way to get
# EditWithComplete to *not* alpha-order the reasons, but leave
# them in the order entered.  If
# calibre.gui2.complete2.CompleteModel.set_items ever changes,
# this function will need to also.
def complete_model_set_items_kludge(self, items):
    items = [unicode(x.strip()) for x in items]
    items = [x for x in items if x]
    items = tuple(items)
    self.all_items = self.current_items = items
    self.current_prefix = ''
    self.reset()
    
class NotGoingToDownload(Exception):
    def __init__(self,error,icon='dialog_error.png'):
        self.error=error
        self.icon=icon

    def __str__(self):
        return self.error

class DroppableQTextEdit(QTextEdit):
    def __init__(self,parent):
        QTextEdit.__init__(self,parent)
        
    def canInsertFromMimeData(self, source):
        if source.hasUrls():
            return True;
        else:
            return QTextEdit.canInsertFromMimeData(self,source)

    def insertFromMimeData(self, source):
        if source.hasText():
            self.append(source.text())
        else:
            return QTextEdit.insertFromMimeData(self, source)
                            
class AddNewDialog(SizePersistedDialog):

    def __init__(self, gui, prefs, icon, url_list_text):
        SizePersistedDialog.__init__(self, gui, 'FanFictionDownLoader plugin:add new dialog')
        self.gui = gui

        if prefs['adddialogstaysontop']:
            QDialog.setWindowFlags ( self, Qt.Dialog|Qt.WindowStaysOnTopHint )
        
        self.setMinimumWidth(300)
        self.l = QVBoxLayout()
        self.setLayout(self.l)

        self.setWindowTitle('FanFictionDownLoader')
        self.setWindowIcon(icon)

        self.l.addWidget(QLabel('Story URL(s), one per line:'))
        self.url = DroppableQTextEdit(self)
        self.url.setToolTip('URLs for stories, one per line.\nWill take URLs from clipboard, but only valid URLs.\nAdd [1,5] after the URL to limit the download to chapters 1-5.')
        self.url.setLineWrapMode(QTextEdit.NoWrap)
        self.url.setText(url_list_text)
        self.l.addWidget(self.url)
        
        horz = QHBoxLayout()
        label = QLabel('Output &Format:')
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
        label = QLabel('If Story Already Exists?')
        horz.addWidget(label)
        self.collision = QComboBox(self)
        self.collision.setToolTip("What to do if there's already an existing story with the same URL or title and author.")
        # add collision options
        self.set_collisions()
        i = self.collision.findText(prefs['collision'])
        if i > -1:
            self.collision.setCurrentIndex(i)
        label.setBuddy(self.collision)
        horz.addWidget(self.collision)
        self.l.addLayout(horz)

        horz = QHBoxLayout()
        self.updatemeta = QCheckBox('Update Calibre &Metadata?',self)
        self.updatemeta.setToolTip("Update metadata for existing stories in Calibre from web site?\n(Columns set to 'New Only' in the column tabs will only be set for new books.)")
        self.updatemeta.setChecked(prefs['updatemeta'])
        horz.addWidget(self.updatemeta)

        self.updateepubcover = QCheckBox('Update EPUB Cover?',self)
        self.updateepubcover.setToolTip('Update book cover image from site or defaults (if found) <i>inside</i> the EPUB when EPUB is updated.')
        self.updateepubcover.setChecked(prefs['updateepubcover'])
        horz.addWidget(self.updateepubcover)
        
        self.l.addLayout(horz)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.l.addWidget(button_box)
        
        if url_list_text:
            button_box.button(QDialogButtonBox.Ok).setFocus()

        # restore saved size.
        self.resize_dialog()
        #self.resize(self.sizeHint())

    def set_collisions(self):
        prev=self.collision.currentText()
        self.collision.clear()
        for o in collision_order:
            if self.fileform.currentText() == 'epub' or o not in [UPDATE,UPDATEALWAYS]:
                self.collision.addItem(o)
        i = self.collision.findText(prev)
        if i > -1:
            self.collision.setCurrentIndex(i)
        
    def get_ffdl_options(self):
        return {
            'fileform': unicode(self.fileform.currentText()),
            'collision': unicode(self.collision.currentText()),
            'updatemeta': self.updatemeta.isChecked(),
            'updateepubcover': self.updateepubcover.isChecked(),
            }

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
    def __init__(self, gui, title, url_text): 
        SizePersistedDialog.__init__(self, gui, 'FanFictionDownLoader plugin:get story urls')
        self.gui = gui
        self.status=False

        self.setMinimumWidth(300)
        
        self.l = QGridLayout()
        self.setLayout(self.l)

        self.setWindowTitle(title)
        self.l.addWidget(QLabel(title),0,0,1,2)
        
        self.l.addWidget(QLabel("URL:"),1,0)
        self.url = QLineEdit(self)
        self.url.setText(url_text)
        self.l.addWidget(self.url,1,1)
   
        self.ok_button = QPushButton('OK', self)
        self.ok_button.clicked.connect(self.ok)
        self.l.addWidget(self.ok_button,2,0)

        self.cancel_button = QPushButton('Cancel', self)
        self.cancel_button.clicked.connect(self.cancel)
        self.l.addWidget(self.cancel_button,2,1)

        # restore saved size.
        self.resize_dialog()

    def ok(self):
        self.status=True
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
        self.gui = gui
        self.status=False

        self.l = QGridLayout()
        self.setLayout(self.l)

        if exception.passwdonly:
            self.setWindowTitle('Password')
            self.l.addWidget(QLabel("Author requires a password for this story(%s)."%exception.url),0,0,1,2)
            # user isn't used, but it's easier to still have it for
            # post processing.
            self.user = FakeLineEdit()
        else:
            self.setWindowTitle('User/Password')
            self.l.addWidget(QLabel("%s requires you to login to download this story."%site),0,0,1,2)
        
            self.l.addWidget(QLabel("User:"),1,0)
            self.user = QLineEdit(self)
            self.l.addWidget(self.user,1,1)
   
        self.l.addWidget(QLabel("Password:"),2,0)
        self.passwd = QLineEdit(self)
        self.passwd.setEchoMode(QLineEdit.Password)
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

class LoopProgressDialog(QProgressDialog):
    '''
    ProgressDialog displayed while fetching metadata for each story.
    '''
    def __init__(self, gui,
                 book_list,
                 foreach_function,
                 finish_function,
                 init_label="Fetching metadata for stories...",
                 win_title="Downloading metadata for stories",
                 status_prefix="Fetched metadata for"):
        QProgressDialog.__init__(self,
                                 init_label,
                                 QString(), 0, len(book_list), gui)
        self.setWindowTitle(win_title)
        self.setMinimumWidth(500)
        self.gui = gui
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
        self.setLabelText("%s %d of %d"%(self.status_prefix,self.i+1,len(self.book_list)))
        self.setValue(self.i+1)
        print(self.labelText())

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
            print("Exception: %s:%s"%(book,unicode(e)))
            traceback.print_exc()
            
        self.updateStatus()
        self.i += 1
            
        if self.i >= len(self.book_list) or self.wasCanceled():
            return self.do_when_finished()
        else:
            QTimer.singleShot(0, self.do_loop)

    def do_when_finished(self):
        self.hide()
        self.gui = None        
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
        self.gui = gui
        
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
        # self.move_up_button = QtGui.QToolButton(self)
        # self.move_up_button.setToolTip('Move selected books up the list')
        # self.move_up_button.setIcon(QIcon(I('arrow-up.png')))
        # self.move_up_button.clicked.connect(self.books_table.move_rows_up)
        # button_layout.addWidget(self.move_up_button)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        button_layout.addItem(spacerItem)
        self.remove_button = QtGui.QToolButton(self)
        self.remove_button.setToolTip('Remove selected books from the list')
        self.remove_button.setIcon(get_icon('list_remove.png'))
        self.remove_button.clicked.connect(self.remove_from_list)
        button_layout.addWidget(self.remove_button)
        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        button_layout.addItem(spacerItem1)
        # self.move_down_button = QtGui.QToolButton(self)
        # self.move_down_button.setToolTip('Move selected books down the list')
        # self.move_down_button.setIcon(QIcon(I('arrow-down.png')))
        # self.move_down_button.clicked.connect(self.books_table.move_rows_down)
        # button_layout.addWidget(self.move_down_button)

        options_layout = QHBoxLayout()

        label = QLabel('Output &Format:')
        options_layout.addWidget(label)
        self.fileform = QComboBox(self)
        self.fileform.addItem('epub')
        self.fileform.addItem('mobi')
        self.fileform.addItem('html')
        self.fileform.addItem('txt')
        self.fileform.setCurrentIndex(self.fileform.findText(prefs['fileform']))
        self.fileform.setToolTip('Choose output format to create.  May set default from plugin configuration.')
        self.fileform.activated.connect(self.set_collisions)
        label.setBuddy(self.fileform)
        options_layout.addWidget(self.fileform)
        
        label = QLabel('Update Mode:')
        options_layout.addWidget(label)
        self.collision = QComboBox(self)
        self.collision.setToolTip("What sort of update to perform.  May set default from plugin configuration.")
        # add collision options
        self.set_collisions()
        i = self.collision.findText(prefs['collision'])
        if i > -1:
            self.collision.setCurrentIndex(i)
        # self.collision.setToolTip('Overwrite will replace the existing story.  Add New will create a new story with the same title and author.')
        label.setBuddy(self.collision)
        options_layout.addWidget(self.collision)

        self.updatemeta = QCheckBox('Update Calibre &Metadata?',self)
        self.updatemeta.setToolTip("Update metadata for existing stories in Calibre from web site?\n(Columns set to 'New Only' in the column tabs will only be set for new books.)")
        self.updatemeta.setChecked(prefs['updatemeta'])
        options_layout.addWidget(self.updatemeta)
                
        self.updateepubcover = QCheckBox('Update EPUB Cover?',self)
        self.updateepubcover.setToolTip('Update book cover image from site or defaults (if found) <i>inside</i> the EPUB when EPUB is updated.')
        self.updateepubcover.setChecked(prefs['updateepubcover'])
        options_layout.addWidget(self.updateepubcover)
        
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
            }

def display_story_list(gui, header, prefs, icon, books,
                       label_text='',
                       save_size_name='fanfictiondownloader_plugin:display list dialog',
                       offer_skip=False):
    all_good = True
    for b in books:
        if not b['good']:
            all_good=False
            break
        
    ## 
    if all_good and not dynamic.get(confirm_config_name(save_size_name), True):
        return True
        pass
            ## fake accept?
    d = DisplayStoryListDialog(gui, header, prefs, icon, books,
                               label_text,
                               save_size_name,
                               offer_skip and all_good)
    d.exec_()
    return d.result() == d.Accepted

class DisplayStoryListDialog(SizePersistedDialog):
    def __init__(self, gui, header, prefs, icon, books,
                 label_text='',
                 save_size_name='fanfictiondownloader_plugin:display list dialog',
                 offer_skip=False):
        SizePersistedDialog.__init__(self, gui, save_size_name)
        self.name = save_size_name
        self.gui = gui
        
        self.setWindowTitle(header)
        self.setWindowIcon(icon)
        
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        title_layout = ImageTitleLayout(self, 'images/icon.png',
                                        header)
        layout.addLayout(title_layout)

        self.books_table = StoryListTableWidget(self)
        layout.addWidget(self.books_table)

        options_layout = QHBoxLayout()
        self.label = QLabel(label_text)
        #self.label.setOpenExternalLinks(True)
        #self.label.setWordWrap(True)
        options_layout.addWidget(self.label)
        
        if offer_skip:
            spacerItem1 = QtGui.QSpacerItem(2, 4, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
            options_layout.addItem(spacerItem1)
            self.again = QCheckBox('Show this again?',self)
            self.again.setChecked(True)
            self.again.stateChanged.connect(self.toggle)
            self.again.setToolTip('Uncheck to skip review and update stories immediately when no problems.')
            options_layout.addWidget(self.again)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        options_layout.addWidget(button_box)
        
        layout.addLayout(options_layout)
        
        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()
        self.books_table.populate_table(books)

    def get_books(self):
        return self.books_table.get_books()

    def toggle(self, *args):
        dynamic[confirm_config_name(self.name)] = self.again.isChecked()

    

class StoryListTableWidget(QTableWidget):

    def __init__(self, parent):
        QTableWidget.__init__(self, parent)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

    def populate_table(self, books):
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(books))
        header_labels = ['','Title', 'Author', 'URL', 'Comment']
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
        status_cell.setData(Qt.UserRole, QVariant(val))
        self.setItem(row, 0, status_cell)
        
        title_cell = ReadOnlyTableWidgetItem(book['title'])
        title_cell.setData(Qt.UserRole, QVariant(row))
        self.setItem(row, 1, title_cell)
        
        self.setItem(row, 2, AuthorTableWidgetItem(", ".join(book['author']), ", ".join(book['author_sort'])))
        
        url_cell = ReadOnlyTableWidgetItem(book['url'])
        #url_cell.setData(Qt.UserRole, QVariant(book['url']))
        self.setItem(row, 3, url_cell)
        
        comment_cell = ReadOnlyTableWidgetItem(book['comment'])
        #comment_cell.setData(Qt.UserRole, QVariant(book))
        self.setItem(row, 4, comment_cell)

    def get_books(self):
        books = []
        #print("=========================\nbooks:%s"%self.books)
        for row in range(self.rowCount()):
            rnum = self.item(row, 1).data(Qt.UserRole).toPyObject()
            book = self.books[rnum]
            books.append(book)
        return books

    def remove_selected_rows(self):
        self.setFocus()
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        message = '<p>Are you sure you want to remove this book from the list?'
        if len(rows) > 1:
            message = '<p>Are you sure you want to remove the selected %d books from the list?'%len(rows)
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

    def move_rows_up(self):
        self.setFocus()
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        first_sel_row = rows[0].row()
        if first_sel_row <= 0:
            return
        # Workaround for strange selection bug in Qt which "alters" the selection
        # in certain circumstances which meant move down only worked properly "once"
        selrows = []
        for row in rows:
            selrows.append(row.row())
        selrows.sort()
        for selrow in selrows:
            self.swap_row_widgets(selrow - 1, selrow + 1)
        scroll_to_row = first_sel_row - 1
        if scroll_to_row > 0:
            scroll_to_row = scroll_to_row - 1
        self.scrollToItem(self.item(scroll_to_row, 0))

    def move_rows_down(self):
        self.setFocus()
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        last_sel_row = rows[-1].row()
        if last_sel_row == self.rowCount() - 1:
            return
        # Workaround for strange selection bug in Qt which "alters" the selection
        # in certain circumstances which meant move down only worked properly "once"
        selrows = []
        for row in rows:
            selrows.append(row.row())
        selrows.sort()
        for selrow in reversed(selrows):
            self.swap_row_widgets(selrow + 2, selrow)
        scroll_to_row = last_sel_row + 1
        if scroll_to_row < self.rowCount() - 1:
            scroll_to_row = scroll_to_row + 1
        self.scrollToItem(self.item(scroll_to_row, 0))

    def swap_row_widgets(self, src_row, dest_row):
        self.blockSignals(True)
        self.insertRow(dest_row)
        for col in range(0, self.columnCount()):
            self.setItem(dest_row, col, self.takeItem(src_row, col))
        self.removeRow(src_row)
        self.blockSignals(False)

class RejectListTableWidget(QTableWidget):

    def __init__(self, parent,rejectreasons=[]):
        QTableWidget.__init__(self, parent)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rejectreasons = rejectreasons

    def on_headersection_clicked(self):
        self.setSortingEnabled(True)
        
    def populate_table(self, reject_list):
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(reject_list))
        header_labels = ['URL', 'Note']
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.horizontalHeader().setStretchLastSection(True)
        #self.verticalHeader().setDefaultSectionSize(24)
        self.verticalHeader().hide()

        # need sortingEnbled to sort, but off to up & down.
        self.connect(self.horizontalHeader(),
                     SIGNAL('sectionClicked(int)'),
                     self.on_headersection_clicked)

        # row is just row number.
        for row, rejectrow in enumerate(reject_list):
            self.populate_table_row(row,rejectrow)

        self.resizeColumnsToContents()
        self.setMinimumColumnWidth(1, 100)
        self.setMinimumColumnWidth(2, 100)
        self.setMinimumSize(300, 0)

    def setMinimumColumnWidth(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)

    def populate_table_row(self, row, rejectrow):

        (bookid,url,titleauth,oldrejnote) = rejectrow
        if oldrejnote:
            noteprefix = note = oldrejnote
            # incase the existing note ends with one of the known reasons.
            for reason in self.rejectreasons:
                if noteprefix.endswith(' - '+reason):
                    noteprefix = noteprefix[:-len(' - '+reason)]
                    break
        else:
            noteprefix = note = titleauth
            
        if len(noteprefix) > 0:
            noteprefix = noteprefix+' - '
            
        url_cell = ReadOnlyTableWidgetItem(url)
        url_cell.setData(Qt.UserRole, QVariant(bookid))
        url_cell.setToolTip('URL to add to the Reject List.')
        self.setItem(row, 0, url_cell)

        note_cell = EditWithComplete(self)

        note_cell.lineEdit().mcompleter.model().set_items = \
            partial(complete_model_set_items_kludge,
                    note_cell.lineEdit().mcompleter.model())
        
        items = [note]+[ noteprefix+x for x in self.rejectreasons ]
        note_cell.update_items_cache(items)
        note_cell.show_initial_value(note)
        note_cell.set_separator(None)
        note_cell.setToolTip('Select or Edit Reject Note.')
        self.setCellWidget(row, 1, note_cell)
        
        # note_cell = QTableWidgetItem(note)
        # note_cell.setToolTip('Double-click to edit note.')
        # self.setItem(row, 1, note_cell)
      
    def get_reject_list(self):
        rejectrows = []
        for row in range(self.rowCount()):
            bookid = self.item(row, 0).data(Qt.UserRole).toPyObject()
            url = unicode(self.item(row, 0).text())
            note = unicode(self.cellWidget(row, 1).currentText()).strip()
            rejectrows.append((bookid,url,note))
        return rejectrows

    def remove_selected_rows(self):
        self.setFocus()
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        message = '<p>Are you sure you want to remove this URL from the list?'
        if len(rows) > 1:
            message = '<p>Are you sure you want to remove the %d selected URLs from the list?'%len(rows)
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

    def move_rows_up(self):
        self.setFocus()
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        first_sel_row = rows[0].row()
        if first_sel_row <= 0:
            return
        # Workaround for strange selection bug in Qt which "alters" the selection
        # in certain circumstances which meant move down only worked properly "once"
        selrows = []
        for row in rows:
            selrows.append(row.row())
        selrows.sort()
        for selrow in selrows:
            self.swap_row_widgets(selrow - 1, selrow + 1)
        scroll_to_row = first_sel_row - 1
        if scroll_to_row > 0:
            scroll_to_row = scroll_to_row - 1
        self.scrollToItem(self.item(scroll_to_row, 0))

    def move_rows_down(self):
        self.setFocus()
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        last_sel_row = rows[-1].row()
        if last_sel_row == self.rowCount() - 1:
            return
        # Workaround for strange selection bug in Qt which "alters" the selection
        # in certain circumstances which meant move down only worked properly "once"
        selrows = []
        for row in rows:
            selrows.append(row.row())
        selrows.sort()
        for selrow in reversed(selrows):
            self.swap_row_widgets(selrow + 2, selrow)
        scroll_to_row = last_sel_row + 1
        if scroll_to_row < self.rowCount() - 1:
            scroll_to_row = scroll_to_row + 1
        self.scrollToItem(self.item(scroll_to_row, 0))

    def swap_row_widgets(self, src_row, dest_row):
        self.blockSignals(True)
        self.setSortingEnabled(False)
        self.insertRow(dest_row)
        for col in range(0, self.columnCount()):
            self.setItem(dest_row, col, self.takeItem(src_row, col))
        self.removeRow(src_row)
        self.blockSignals(False)

class RejectListDialog(SizePersistedDialog):
    def __init__(self, gui, reject_list,
                 rejectreasons=[],
                 header="List of Books to Reject",
                 icon='rotate-right.png',
                 show_delete=True,
                 show_all_reasons=True,
                 save_size_name='ffdl:reject list dialog'):
        SizePersistedDialog.__init__(self, gui, save_size_name)
        self.gui = gui
      
        self.setWindowTitle(header)
        self.setWindowIcon(get_icon(icon))
      
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        title_layout = ImageTitleLayout(self, icon, header,
                                        '<i></i>FFDL will remember these URLs and display the note and offer to reject them if you try to download them again later.')
        layout.addLayout(title_layout)
        rejects_layout = QHBoxLayout()
        layout.addLayout(rejects_layout)

        self.rejects_table = RejectListTableWidget(self,rejectreasons=rejectreasons)
        rejects_layout.addWidget(self.rejects_table)

        button_layout = QVBoxLayout()
        rejects_layout.addLayout(button_layout)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        button_layout.addItem(spacerItem)
        # self.move_up_button = QtGui.QToolButton(self)
        # self.move_up_button.setToolTip('Move selected books up the list')
        # self.move_up_button.setIcon(QIcon(I('arrow-up.png')))
        # self.move_up_button.clicked.connect(self.books_table.move_rows_up)
        # button_layout.addWidget(self.move_up_button)
        self.remove_button = QtGui.QToolButton(self)
        self.remove_button.setToolTip('Remove selected URL(s) from the list')
        self.remove_button.setIcon(get_icon('list_remove.png'))
        self.remove_button.clicked.connect(self.remove_from_list)
        button_layout.addWidget(self.remove_button)
        # self.move_down_button = QtGui.QToolButton(self)
        # self.move_down_button.setToolTip('Move selected books down the list')
        # self.move_down_button.setIcon(QIcon(I('arrow-down.png')))
        # self.move_down_button.clicked.connect(self.books_table.move_rows_down)
        # button_layout.addWidget(self.move_down_button)
        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        button_layout.addItem(spacerItem1)

        if show_all_reasons:
            self.reason_edit = EditWithComplete(self)
            self.reason_edit.lineEdit().mcompleter.model().set_items = \
                partial(complete_model_set_items_kludge,
                        self.reason_edit.lineEdit().mcompleter.model())
            
            items = ['']+rejectreasons
            self.reason_edit.update_items_cache(items)
            self.reason_edit.show_initial_value('')
            self.reason_edit.set_separator(None)
            self.reason_edit.setToolTip("This will be added to whatever note you've set for each URL above.")
            
            horz = QHBoxLayout()
            label = QLabel("Add this reason to all URLs added:")
            label.setToolTip("This will be added to whatever note you've set for each URL above.")
            horz.addWidget(label)
            horz.addWidget(self.reason_edit)
            horz.insertStretch(-1)
            layout.addLayout(horz)
                    
        options_layout = QHBoxLayout()

        if show_delete:
            self.deletebooks = QCheckBox('Delete Books (including books without FanFiction URLs)?',self)
            self.deletebooks.setToolTip("Delete the selected books after adding them to the Rejected URLs list.")
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
        return self.rejects_table.get_reject_list()

    def get_reason_text(self):
        return unicode(self.reason_edit.currentText()).strip()
    
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
            self.reason_edit = EditWithComplete(self)

            self.reason_edit.lineEdit().mcompleter.model().set_items = \
                partial(complete_model_set_items_kludge,
                        self.reason_edit.lineEdit().mcompleter.model())
            
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
    
