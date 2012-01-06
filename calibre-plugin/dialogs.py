#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2011, Jim Miller'
__docformat__ = 'restructuredtext en'

import traceback

from PyQt4 import QtGui
from PyQt4.Qt import (QDialog, QTableWidget, QMessageBox, QVBoxLayout, QHBoxLayout, QGridLayout,
                      QPushButton, QProgressDialog, QString, QLabel, QCheckBox, QIcon,
                      QTextEdit, QLineEdit, QInputDialog, QComboBox, QClipboard, QVariant,
                      QProgressDialog, QTimer, QDialogButtonBox, QPixmap, Qt,QAbstractItemView )

from calibre.gui2 import error_dialog, warning_dialog, question_dialog, info_dialog
from calibre.gui2.dialogs.confirm_delete import confirm

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
        
class NotGoingToDownload(Exception):
    def __init__(self,error,icon='dialog_error.png'):
        self.error=error
        self.icon=icon

    def __str__(self):
        return self.error
    
class AddNewDialog(SizePersistedDialog):

    def __init__(self, gui, prefs, icon, url_list_text):
        SizePersistedDialog.__init__(self, gui, 'FanFictionDownLoader plugin:add new dialog')
        self.gui = gui

        self.setMinimumWidth(300)
        self.l = QVBoxLayout()
        self.setLayout(self.l)

        self.setWindowTitle('FanFictionDownLoader')
        self.setWindowIcon(icon)

        self.l.addWidget(QLabel('Story URL(s), one per line:'))
        self.url = QTextEdit(self)
        self.url.setToolTip('URLs for stories, one per line.\nWill take URLs from clipboard, but only valid URLs.')
        self.url.setLineWrapMode(QTextEdit.NoWrap)
        self.url.setText(url_list_text)
        self.l.addWidget(self.url)
        
        # self.ffdl_button = QPushButton(
        #     'Download Stories', self)
        # self.ffdl_button.setToolTip('Start download(s).')
        # self.ffdl_button.clicked.connect(self.ffdl)
        # # if there's already URL(s), focus 'go' button
        # if url_list_text:
        #     self.ffdl_button.setFocus()
        # self.l.addWidget(self.ffdl_button)

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
        label.setBuddy(self.fileform)
        horz.addWidget(self.fileform)
        self.l.addLayout(horz)

        horz = QHBoxLayout()
        label = QLabel('If Story Already Exists?')
        label.setToolTip("What to do if there's already an existing story with the same title and author.")
        horz.addWidget(label)
        self.collision = QComboBox(self)
        # add collision options
        for o in collision_order:
            self.collision.addItem(o)

        self.collision.setCurrentIndex(self.collision.findText(prefs['collision']))
        # self.collision.setToolTip(OVERWRITE+' will replace the existing story.\n'+
        #                           UPDATE+' will download new chapters only and add to existing EPUB.\n'+
        #                           ADDNEW+' will create a new story with the same title and author.\n'+
        #                           SKIP+' will not download existing stories.\n'+
        #                           CALIBREONLY+' will not download stories, but will update Calibre metadata.')
        label.setBuddy(self.collision)
        horz.addWidget(self.collision)
        self.l.addLayout(horz)

        self.updatemeta = QCheckBox('Update Calibre &Metadata?',self)
        self.updatemeta.setToolTip('Update metadata for story in Calibre from web site?')
        self.updatemeta.setChecked(prefs['updatemeta'])
        self.l.addWidget(self.updatemeta)

        # self.onlyoverwriteifnewer = QCheckBox('Only Overwrite Story if Newer',self)
        # self.onlyoverwriteifnewer.setToolTip("Don't overwrite existing book unless the story on the web site is newer.\n"+
        #                                      "From the same day counts as 'newer' because the sites don't give update time.")
        # self.onlyoverwriteifnewer.setChecked(prefs['onlyoverwriteifnewer'])
        # self.l.addWidget(self.onlyoverwriteifnewer)
        
        # horz = QHBoxLayout()
        # self.about_button = QPushButton('About', self)
        # self.about_button.clicked.connect(self.about)
        # horz.addWidget(self.about_button)
        # self.conf_button = QPushButton(
        #         'Configure this plugin', self)
        # self.conf_button.clicked.connect(self.config)
        # horz.addWidget(self.conf_button)
        # self.l.addLayout(horz)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.l.addWidget(button_box)
        
        if url_list_text:
            button_box.button(QDialogButtonBox.Ok).setFocus()
        
        self.resize_dialog()
        #self.resize(self.sizeHint())

    def get_ffdl_options(self):
        return {
            'fileform': unicode(self.fileform.currentText()),
            'collision': unicode(self.collision.currentText()),
            'updatemeta': unicode(self.updatemeta.isChecked()),
            }

    def get_urlstext(self):
        return unicode(self.url.toPlainText())
        
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
    def __init__(self, gui,
                 book_list,
                 options,
                 metadata_function,
                 startdownload_function):
        QProgressDialog.__init__(self,
                                 "Fetching metadata for stories...",
                                 QString(), 0, len(book_list), gui)
        self.setWindowTitle("Downloading metadata for stories")
        self.setMinimumWidth(500)
        self.gui = gui
        self.book_list = book_list
        self.options = options
        self.metadata_function = metadata_function
        self.startdownload_function = startdownload_function
        self.i = 0
        
        ## self.do_loop does QTimer.singleShot on self.do_loop also.
        ## A weird way to do a loop, but that was the example I had.
        QTimer.singleShot(0, self.do_loop)
        self.exec_()

    def updateStatus(self):
        self.setLabelText("Fetched metadata for %d of %d"%(self.i+1,len(self.book_list)))
        self.setValue(self.i+1)
        print(self.labelText())

    def do_loop(self):
        print("self.i:%d"%self.i)

        if self.i == 0:
            self.setValue(0)

        book = self.book_list[self.i]
        try:
            ## collision spec passed into getadapter by partial from ffdl_plugin
            ## no retval only if it exists, but collision is SKIP
            self.metadata_function(book)
            
        except NotGoingToDownload as d:
            book['good']=False
            book['comment']=unicode(d)
            book['icon'] = d.icon

        except Exception as e:
            book['good']=False
            book['comment']=unicode(e)
            print("%s:%s"%(book,unicode(e)))
            # XXX trace for not-expected exceptions
            #traceback.print_exc()
            
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
        self.startdownload_function(self.book_list)

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
        return self.sort_key < other.sort_key

class UpdateExistingDialog(SizePersistedDialog):
    def __init__(self, gui, header, prefs, icon, books,
                 save_size_name='FanFictionDownLoader plugin:update list dialog'):
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
        label.setBuddy(self.fileform)
        options_layout.addWidget(self.fileform)
        
        label = QLabel('Update Mode:')
        label.setToolTip("What sort of update to perform.  May set default from plugin configuration.")
        options_layout.addWidget(label)
        self.collision = QComboBox(self)
        for o in collision_order:
            if o not in [ADDNEW,SKIP]:
                self.collision.addItem(o)
        self.collision.setCurrentIndex(self.collision.findText(prefs['collision']))
        # self.collision.setToolTip('Overwrite will replace the existing story.  Add New will create a new story with the same title and author.')
        label.setBuddy(self.collision)
        options_layout.addWidget(self.collision)

        self.updatemeta = QCheckBox('Update Calibre &Metadata?',self)
        self.updatemeta.setToolTip('Update metadata for story in Calibre from web site?  May set default from plugin configuration.')
        self.updatemeta.setChecked(prefs['updatemeta'])
        options_layout.addWidget(self.updatemeta)
                
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        options_layout.addWidget(button_box)
        
        layout.addLayout(options_layout)
        
        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()
        self.books_table.populate_table(books)
        
    def remove_from_list(self):
        self.books_table.remove_selected_rows()

    def get_books(self):
        return self.books_table.get_books()

    def get_ffdl_options(self):
        return {
            'fileform': unicode(self.fileform.currentText()),
            'collision': unicode(self.collision.currentText()),
            'updatemeta': unicode(self.updatemeta.isChecked()),
            }

class DisplayStoryListDialog(SizePersistedDialog):
    def __init__(self, gui, header, prefs, icon, books,
                 label_text='',
                 save_size_name='FanFictionDownLoader plugin:display list dialog'):
        SizePersistedDialog.__init__(self, gui, save_size_name)
        # UpdateExistingDialog.__init__(self, gui, header, prefs, icon, books,
        #                               save_size_name='FanFictionDownLoader plugin:display list dialog')

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
        
        self.setItem(row, 2, AuthorTableWidgetItem(book['author'], book['author_sort']))
        
        url_cell = ReadOnlyTableWidgetItem(book['url'])
        #url_cell.setData(Qt.UserRole, QVariant(book['url']))
        self.setItem(row, 3, url_cell)
        
        comment_cell = ReadOnlyTableWidgetItem(book['comment'])
        #comment_cell.setData(Qt.UserRole, QVariant(book))
        self.setItem(row, 4, comment_cell)

    # def get_calibre_ids(self):
    #     ids = []
    #     for row in range(self.rowCount()):
    #         ids.append(self.item(row, 1).data(Qt.UserRole).toPyObject())
    #     return ids

    # def get_urls(self):
    #     urls = []
    #     for row in range(self.rowCount()):
    #         urls.append(self.item(row, 2).data(Qt.UserRole).toPyObject())
    #     return urls

    def get_books(self):
        books = []
        #print("=========================\nbooks:%s"%self.books)
        for row in range(self.rowCount()):
            rnum = self.item(row, 1).data(Qt.UserRole).toPyObject()
            #print("get_books rnum:%s"%rnum)
            book = self.books[rnum]
            #if book['good']:
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
