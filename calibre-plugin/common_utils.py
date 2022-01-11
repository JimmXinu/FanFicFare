# -*- coding: utf-8 -*-

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import six

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake <grant.drake@gmail.com>, 2018, Jim Miller'
__docformat__ = 'restructuredtext en'

import os
from contextlib import contextmanager
from PyQt5.Qt import (QApplication, Qt, QIcon, QPixmap, QLabel, QDialog, QHBoxLayout,
                      QTableWidgetItem, QFont, QLineEdit, QComboBox,
                      QVBoxLayout, QDialogButtonBox, QStyledItemDelegate, QDateTime,
                      QTextEdit, QListWidget, QAbstractItemView, QCursor)

from calibre.constants import iswindows, DEBUG
from calibre.gui2 import UNDEFINED_QDATETIME, gprefs, info_dialog
from calibre.gui2.actions import menu_action_unique_name
from calibre.gui2.keyboard import ShortcutConfig
from calibre.utils.config import config_dir
from calibre.utils.date import now, format_date, qt_to_dt, UNDEFINED_DATE
from fanficfare.six import text_type as unicode

# Global definition of our plugin name. Used for common functions that require this.
plugin_name = None
# Global definition of our plugin resources. Used to share between the xxxAction and xxxBase
# classes if you need any zip images to be displayed on the configuration dialog.
plugin_icon_resources = {}


def set_plugin_icon_resources(name, resources):
    '''
    Set our global store of plugin name and icon resources for sharing between
    the InterfaceAction class which reads them and the ConfigWidget
    if needed for use on the customization dialog for this plugin.
    '''
    global plugin_icon_resources, plugin_name
    plugin_name = name
    plugin_icon_resources = resources


def get_icon(icon_name):
    '''
    Retrieve a QIcon for the named image from the zip file if it exists,
    or if not then from Calibre's image cache.
    '''
    if icon_name:
        pixmap = get_pixmap(icon_name)
        if pixmap is None:
            # Look in Calibre's cache for the icon
            return QIcon(I(icon_name))
        else:
            return QIcon(pixmap)
    return QIcon()


def get_pixmap(icon_name):
    '''
    Retrieve a QPixmap for the named image
    Any icons belonging to the plugin must be prefixed with 'images/'
    '''
    global plugin_icon_resources, plugin_name

    if not icon_name.startswith('images/'):
        # We know this is definitely not an icon belonging to this plugin
        pixmap = QPixmap()
        pixmap.load(I(icon_name))
        return pixmap

    # Check to see whether the icon exists as a Calibre resource
    # This will enable skinning if the user stores icons within a folder like:
    # ...\AppData\Roaming\calibre\resources\images\Plugin Name\
    if plugin_name:
        local_images_dir = get_local_images_dir(plugin_name)
        local_image_path = os.path.join(local_images_dir, icon_name.replace('images/', ''))
        if os.path.exists(local_image_path):
            pixmap = QPixmap()
            pixmap.load(local_image_path)
            return pixmap

    # As we did not find an icon elsewhere, look within our zip resources
    if icon_name in plugin_icon_resources:
        pixmap = QPixmap()
        pixmap.loadFromData(plugin_icon_resources[icon_name])
        return pixmap
    return None


def get_local_images_dir(subfolder=None):
    '''
    Returns a path to the user's local resources/images folder
    If a subfolder name parameter is specified, appends this to the path
    '''
    images_dir = os.path.join(config_dir, 'resources/images')
    if subfolder:
        images_dir = os.path.join(images_dir, subfolder)
    if iswindows:
        images_dir = os.path.normpath(images_dir)
    return images_dir


def create_menu_item(ia, parent_menu, menu_text, image=None, tooltip=None,
                     shortcut=(), triggered=None, is_checked=None):
    '''
    Create a menu action with the specified criteria and action
    Note that if no shortcut is specified, will not appear in Preferences->Keyboard
    This method should only be used for actions which either have no shortcuts,
    or register their menus only once. Use create_menu_action_unique for all else.
    '''
    if shortcut is not None:
        if len(shortcut) == 0:
            shortcut = ()
        else:
            shortcut = shortcut
    ac = ia.create_action(spec=(menu_text, None, tooltip, shortcut),
        attr=menu_text)
    if image:
        ac.setIcon(get_icon(image))
    if triggered is not None:
        ac.triggered.connect(triggered)
    if is_checked is not None:
        ac.setCheckable(True)
        if is_checked:
            ac.setChecked(True)

    parent_menu.addAction(ac)
    return ac


def create_menu_action_unique(ia, parent_menu, menu_text, image=None, tooltip=None,
                       shortcut=None, triggered=None, is_checked=None, shortcut_name=None,
                       unique_name=None):
    '''
    Create a menu action with the specified criteria and action, using the new
    InterfaceAction.create_menu_action() function which ensures that regardless of
    whether a shortcut is specified it will appear in Preferences->Keyboard
    '''
    orig_shortcut = shortcut
    kb = ia.gui.keyboard
    if unique_name is None:
        unique_name = menu_text
    if not shortcut == False:
        full_unique_name = menu_action_unique_name(ia, unique_name)
        if full_unique_name in kb.shortcuts:
            shortcut = False
        else:
            if shortcut is not None and not shortcut == False:
                if len(shortcut) == 0:
                    shortcut = None
                else:
                    shortcut = shortcut

    if shortcut_name is None:
        shortcut_name = menu_text.replace('&','')

    ac = ia.create_menu_action(parent_menu, unique_name, menu_text, icon=None, shortcut=shortcut,
        description=tooltip, triggered=triggered, shortcut_name=shortcut_name)
    if shortcut == False and not orig_shortcut == False:
        if ac.calibre_shortcut_unique_name in ia.gui.keyboard.shortcuts:
            kb.replace_action(ac.calibre_shortcut_unique_name, ac)
    if image:
        ac.setIcon(get_icon(image))
    if is_checked is not None:
        ac.setCheckable(True)
        if is_checked:
            ac.setChecked(True)
    return ac


def swap_author_names(author):
    if author.find(',') == -1:
        return author
    name_parts = author.strip().partition(',')
    return name_parts[2].strip() + ' ' + name_parts[0]


def get_library_uuid(db):
    try:
        library_uuid = db.library_id
    except:
        library_uuid = ''
    return library_uuid

# Call as ' with busy_cursor:"
@contextmanager
def busy_cursor():
    try:
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        yield
    finally:
        QApplication.restoreOverrideCursor()


class ImageLabel(QLabel):

    def __init__(self, parent, icon_name, size=16):
        QLabel.__init__(self, parent)
        pixmap = get_pixmap(icon_name)
        self.setPixmap(pixmap)
        self.setMaximumSize(size, size)
        self.setScaledContents(True)


class ImageTitleLayout(QHBoxLayout):
    '''
    A reusable layout widget displaying an image followed by a title
    '''
    def __init__(self, parent, icon_name, title, tooltip=None):
        QHBoxLayout.__init__(self)
        title_image_label = QLabel(parent)
        pixmap = get_pixmap(icon_name)
        if pixmap is None:
            pixmap = get_pixmap('library.png')
            # error_dialog(parent, _('Restart required'),
            #              _('You must restart Calibre before using this plugin!'), show=True)
        else:
            title_image_label.setPixmap(pixmap)
        title_image_label.setMaximumSize(32, 32)
        title_image_label.setScaledContents(True)
        self.addWidget(title_image_label)

        title_font = QFont()
        title_font.setPointSize(16)
        shelf_label = QLabel(title, parent)
        shelf_label.setFont(title_font)
        self.addWidget(shelf_label)
        self.insertStretch(-1)

        if tooltip:
            title_image_label.setToolTip(tooltip)
            shelf_label.setToolTip(tooltip)

class SizePersistedDialog(QDialog):
    '''
    This dialog is a base class for any dialogs that want their size/position
    restored when they are next opened.
    '''
    def __init__(self, parent, unique_pref_name):
        QDialog.__init__(self, parent)
        self.unique_pref_name = unique_pref_name
        self.geom = gprefs.get(unique_pref_name, None)
        self.finished.connect(self.dialog_closing)

    def resize_dialog(self):
        if self.geom is None:
            self.resize(self.sizeHint())
        else:
            self.restoreGeometry(self.geom)

    def dialog_closing(self, result):
        self.geom = bytearray(self.saveGeometry())
        gprefs[self.unique_pref_name] = self.geom

class EditableTableWidgetItem(QTableWidgetItem):

    def __init__(self, text):
        if text is None:
            text = ''
        QTableWidgetItem.__init__(self, text)
        self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled|Qt.ItemIsEditable)

class ReadOnlyTableWidgetItem(QTableWidgetItem):

    def __init__(self, text):
        if text is None:
            text = ''
        QTableWidgetItem.__init__(self, text)
        self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)


class RatingTableWidgetItem(QTableWidgetItem):

    def __init__(self, rating, is_read_only=False):
        QTableWidgetItem.__init__(self, '')
        self.setData(Qt.DisplayRole, rating)
        if is_read_only:
            self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)


class DateTableWidgetItem(QTableWidgetItem):

    def __init__(self, date_read, is_read_only=False, default_to_today=False):
        if date_read == UNDEFINED_DATE and default_to_today:
            date_read = now()
        if is_read_only:
            QTableWidgetItem.__init__(self, format_date(date_read, None))
            self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
        else:
            QTableWidgetItem.__init__(self, '')
            self.setData(Qt.DisplayRole, QDateTime(date_read))


class NoWheelComboBox(QComboBox):

    def wheelEvent (self, event):
        # Disable the mouse wheel on top of the combo box changing selection as plays havoc in a grid
        event.ignore()


class CheckableTableWidgetItem(QTableWidgetItem):

    def __init__(self, checked=False, is_tristate=False):
        QTableWidgetItem.__init__(self, '')
        self.setFlags(Qt.ItemFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled ))
        if is_tristate:
            self.setFlags(self.flags() | Qt.ItemIsTristate)
        if checked:
            self.setCheckState(Qt.Checked)
        else:
            if is_tristate and checked is None:
                self.setCheckState(Qt.PartiallyChecked)
            else:
                self.setCheckState(Qt.Unchecked)

    def get_boolean_value(self):
        '''
        Return a boolean value indicating whether checkbox is checked
        If this is a tristate checkbox, a partially checked value is returned as None
        '''
        if self.checkState() == Qt.PartiallyChecked:
            return None
        else:
            return self.checkState() == Qt.Checked


class TextIconWidgetItem(QTableWidgetItem):

    def __init__(self, text, icon):
        QTableWidgetItem.__init__(self, text)
        if icon:
            self.setIcon(icon)


class ReadOnlyTextIconWidgetItem(ReadOnlyTableWidgetItem):

    def __init__(self, text, icon):
        ReadOnlyTableWidgetItem.__init__(self, text)
        if icon:
            self.setIcon(icon)


class ReadOnlyLineEdit(QLineEdit):

    def __init__(self, text, parent):
        if text is None:
            text = ''
        QLineEdit.__init__(self, text, parent)
        self.setEnabled(False)


class KeyValueComboBox(QComboBox):

    def __init__(self, parent, values, selected_key):
        QComboBox.__init__(self, parent)
        self.values = values
        self.populate_combo(selected_key)

    def populate_combo(self, selected_key):
        self.clear()
        selected_idx = idx = -1
        for key, value in six.iteritems(self.values):
            idx = idx + 1
            self.addItem(value)
            if key == selected_key:
                selected_idx = idx
        self.setCurrentIndex(selected_idx)

    def selected_key(self):
        for key, value in six.iteritems(self.values):
            if value == unicode(self.currentText()).strip():
                return key


class CustomColumnComboBox(QComboBox):

    def __init__(self, parent, custom_columns, selected_column, initial_items=['']):
        QComboBox.__init__(self, parent)
        self.populate_combo(custom_columns, selected_column, initial_items)

    def populate_combo(self, custom_columns, selected_column, initial_items=['']):
        self.clear()
        self.column_names = initial_items
        if len(initial_items) > 0:
            self.addItems(initial_items)
        selected_idx = 0
        for idx, value in enumerate(initial_items):
            if value == selected_column:
                selected_idx = idx
        for key in sorted(custom_columns.keys()):
            self.column_names.append(key)
            self.addItem('%s (%s)'%(key, custom_columns[key]['name']))
            if key == selected_column:
                selected_idx = len(self.column_names) - 1
        self.setCurrentIndex(selected_idx)

    def get_selected_column(self):
        return self.column_names[self.currentIndex()]


class KeyboardConfigDialog(SizePersistedDialog):
    '''
    This dialog is used to allow editing of keyboard shortcuts.
    '''
    def __init__(self, gui, group_name):
        SizePersistedDialog.__init__(self, gui, 'FanFicFare plugin:Keyboard shortcut dialog')
        self.gui = gui
        self.setWindowTitle(_('Keyboard shortcuts'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.keyboard_widget = ShortcutConfig(self)
        layout.addWidget(self.keyboard_widget)
        self.group_name = group_name

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.commit)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()
        self.initialize()

    def initialize(self):
        self.keyboard_widget.initialize(self.gui.keyboard)
        self.keyboard_widget.highlight_group(self.group_name)

    def commit(self):
        self.keyboard_widget.commit()
        self.accept()


class DateDelegate(QStyledItemDelegate):
    '''
    Delegate for dates. Because this delegate stores the
    format as an instance variable, a new instance must be created for each
    column. This differs from all the other delegates.
    '''
    def __init__(self, parent):
        QStyledItemDelegate.__init__(self, parent)
        self.format = 'dd MMM yyyy'

    def displayText(self, val, locale):
        d = val.toDateTime()
        if d <= UNDEFINED_QDATETIME:
            return ''
        return format_date(qt_to_dt(d, as_utc=False), self.format)

    def createEditor(self, parent, option, index):
        qde = QStyledItemDelegate.createEditor(self, parent, option, index)
        qde.setDisplayFormat(self.format)
        qde.setMinimumDateTime(UNDEFINED_QDATETIME)
        qde.setSpecialValueText(_('Undefined'))
        qde.setCalendarPopup(True)
        return qde

    def setEditorData(self, editor, index):
        val = index.model().data(index, Qt.DisplayRole).toDateTime()
        if val is None or val == UNDEFINED_QDATETIME:
            val = now()
        editor.setDateTime(val)

    def setModelData(self, editor, model, index):
        val = editor.dateTime()
        if val <= UNDEFINED_QDATETIME:
            model.setData(index, UNDEFINED_QDATETIME, Qt.EditRole)
        else:
            model.setData(index, QDateTime(val), Qt.EditRole)

class PrefsViewerDialog(SizePersistedDialog):

    def __init__(self, gui, namespace):
        SizePersistedDialog.__init__(self, gui, _('Prefs Viewer dialog'))
        self.setWindowTitle(_('Preferences for: ')+namespace)

        self.gui = gui
        self.db = gui.current_db
        self.namespace = namespace
        self._init_controls()
        self.resize_dialog()

        self._populate_settings()

        if self.keys_list.count():
            self.keys_list.setCurrentRow(0)

    def _init_controls(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        ml = QHBoxLayout()
        layout.addLayout(ml, 1)

        self.keys_list = QListWidget(self)
        self.keys_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.keys_list.setFixedWidth(150)
        self.keys_list.setAlternatingRowColors(True)
        ml.addWidget(self.keys_list)
        self.value_text = QTextEdit(self)
        self.value_text.setReadOnly(True)
        ml.addWidget(self.value_text, 1)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        self.clear_button = button_box.addButton(_('Clear'), QDialogButtonBox.ResetRole)
        self.clear_button.setIcon(get_icon('trash.png'))
        self.clear_button.setToolTip(_('Clear all settings for this plugin'))
        self.clear_button.clicked.connect(self._clear_settings)

        if DEBUG:
            self.edit_button = button_box.addButton(_('Edit'), QDialogButtonBox.ResetRole)
            self.edit_button.setIcon(get_icon('edit_input.png'))
            self.edit_button.setToolTip(_('Edit settings.'))
            self.edit_button.clicked.connect(self._edit_settings)

            self.save_button = button_box.addButton(_('Save'), QDialogButtonBox.ResetRole)
            self.save_button.setIcon(get_icon('save.png'))
            self.save_button.setToolTip(_('Save setting for this plugin'))
            self.save_button.clicked.connect(self._save_settings)
            self.save_button.setEnabled(False)
        layout.addWidget(button_box)

    def _populate_settings(self):
        self.keys_list.clear()
        ns_prefix = self._get_ns_prefix()
        keys = sorted([k[len(ns_prefix):] for k in six.iterkeys(self.db.prefs)
                       if k.startswith(ns_prefix)])
        for key in keys:
            self.keys_list.addItem(key)
        self.keys_list.setMinimumWidth(self.keys_list.sizeHintForColumn(0))
        self.keys_list.currentRowChanged[int].connect(self._current_row_changed)

    def _current_row_changed(self, new_row):
        if new_row < 0:
            self.value_text.clear()
            return
        key = unicode(self.keys_list.currentItem().text())
        val = self.db.prefs.get_namespaced(self.namespace, key, '')
        self.value_text.setPlainText(self.db.prefs.to_raw(val))

    def _get_ns_prefix(self):
        return 'namespaced:%s:'% self.namespace

    def _edit_settings(self):
        from calibre.gui2.dialogs.confirm_delete import confirm
        message = '<p>' + _('Are you sure you want to edit settings in this library for this plugin?') + '</p>' \
                  + '<p>' + _('The FanFicFare team does not support hand edited configurations.') + '</p>'
        if confirm(message, self.namespace+'_edit_settings', self):
            self.save_button.setEnabled(True)
            self.edit_button.setEnabled(False)
            self.value_text.setReadOnly(False)

    def _save_settings(self):
        from calibre.gui2.dialogs.confirm_delete import confirm
        message = '<p>' + _('Are you sure you want to save this setting in this library for this plugin?') + '</p>' \
                  + '<p>' + _('Any settings in other libraries or stored in a JSON file in your calibre plugins folder will not be touched.') + '</p>' \
                  + '<p>' + _('You must restart calibre afterwards.') + '</p>'
        if not confirm(message, self.namespace+'_save_settings', self):
            return
        ns_prefix = self._get_ns_prefix()
        key = unicode(self.keys_list.currentItem().text())
        self.db.prefs.set_namespaced(self.namespace, key,
                                     self.db.prefs.raw_to_object(self.value_text.toPlainText()))
        d = info_dialog(self, 'Settings saved',
                        '<p>' + _('All settings for this plugin in this library have been saved.') + '</p>' \
                        + '<p>' + _('Please restart calibre now.') + '</p>',
                        show_copy_button=False)
        b = d.bb.addButton(_('Restart calibre now'), d.bb.AcceptRole)
        b.setIcon(QIcon(I('lt.png')))
        d.do_restart = False
        def rf():
            d.do_restart = True
        b.clicked.connect(rf)
        d.set_details('')
        d.exec_()
        b.clicked.disconnect()
        self.close()
        if d.do_restart:
            self.gui.quit(restart=True)

    def _clear_settings(self):
        from calibre.gui2.dialogs.confirm_delete import confirm
        message = '<p>' + _('Are you sure you want to clear your settings in this library for this plugin?') + '</p>' \
                  + '<p>' + _('Any settings in other libraries or stored in a JSON file in your calibre plugins folder will not be touched.') + '</p>' \
                  + '<p>' + _('You must restart calibre afterwards.') + '</p>'
        if not confirm(message, self.namespace+'_clear_settings', self):
            return
        ns_prefix = self._get_ns_prefix()
        keys = [k for k in six.iterkeys(self.db.prefs) if k.startswith(ns_prefix)]
        for k in keys:
            del self.db.prefs[k]
        self._populate_settings()
        d = info_dialog(self, 'Settings deleted',
                        '<p>' + _('All settings for this plugin in this library have been cleared.') + '</p>' \
                        + '<p>' + _('Please restart calibre now.') + '</p>',
                        show_copy_button=False)
        b = d.bb.addButton(_('Restart calibre now'), d.bb.AcceptRole)
        b.setIcon(QIcon(I('lt.png')))
        d.do_restart = False
        def rf():
            d.do_restart = True
        b.clicked.connect(rf)
        d.set_details('')
        d.exec_()
        b.clicked.disconnect()
        self.close()
        if d.do_restart:
            self.gui.quit(restart=True)
