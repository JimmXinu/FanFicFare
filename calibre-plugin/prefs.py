#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2013, Jim Miller'
__docformat__ = 'restructuredtext en'

import copy

from calibre.utils.config import JSONConfig
from calibre.gui2.ui import get_gui

from calibre_plugins.fanfictiondownloader_plugin.dialogs import OVERWRITE
from calibre_plugins.fanfictiondownloader_plugin.common_utils import get_library_uuid
PREFS_NAMESPACE = 'FanFictionDownLoaderPlugin'
PREFS_KEY_SETTINGS = 'settings'

# Set defaults used by all.  Library specific settings continue to
# take from here.
default_prefs = {}
default_prefs['personal.ini'] = get_resources('plugin-example.ini')
default_prefs['rejecturls'] = ''
default_prefs['rejectreasons'] = '''Sucked
Boring
Dup from another site'''

default_prefs['updatemeta'] = True
default_prefs['updatecover'] = False
default_prefs['updateepubcover'] = False
default_prefs['keeptags'] = False
default_prefs['suppressauthorsort'] = False
default_prefs['suppresstitlesort'] = False
default_prefs['mark'] = False
default_prefs['showmarked'] = False
default_prefs['autoconvert'] = False
default_prefs['urlsfromclip'] = True
default_prefs['updatedefault'] = True
default_prefs['fileform'] = 'epub'
default_prefs['collision'] = OVERWRITE
default_prefs['deleteotherforms'] = False
default_prefs['adddialogstaysontop'] = False
default_prefs['includeimages'] = False
default_prefs['lookforurlinhtml'] = False
default_prefs['checkforseriesurlid'] = True
default_prefs['checkforurlchange'] = True
default_prefs['injectseries'] = False
default_prefs['smarten_punctuation'] = False

default_prefs['send_lists'] = ''
default_prefs['read_lists'] = ''
default_prefs['addtolists'] = False
default_prefs['addtoreadlists'] = False
default_prefs['addtolistsonread'] = False

default_prefs['gcnewonly'] = False
default_prefs['gc_site_settings'] = {}
default_prefs['allow_gc_from_ini'] = True
default_prefs['gc_polish_cover'] = False

default_prefs['countpagesstats'] = []

default_prefs['errorcol'] = ''
default_prefs['custom_cols'] = {}
default_prefs['custom_cols_newonly'] = {}
default_prefs['allow_custcol_from_ini'] = True

default_prefs['std_cols_newonly'] = {}

# This is where all preferences for this plugin *were* stored
# Remember that this name (i.e. plugins/fanfictiondownloader_plugin) is also
# in a global namespace, so make it as unique as possible.
# You should always prefix your config file name with plugins/,
# so as to ensure you dont accidentally clobber a calibre config file
old_prefs = JSONConfig('plugins/fanfictiondownloader_plugin')

def set_library_config(library_config,db):
    db.prefs.set_namespaced(PREFS_NAMESPACE,
                            PREFS_KEY_SETTINGS,
                            library_config)

def get_library_config(db):
    library_id = get_library_uuid(db)
    library_config = None
    # Check whether this is a configuration needing to be migrated
    # from json into database.  If so: get it, set it, rename it in json.
    if library_id in old_prefs:
        #print("get prefs from old_prefs")
        library_config = old_prefs[library_id]
        set_library_config(library_config,db)
        old_prefs["migrated to library db %s"%library_id] = old_prefs[library_id]
        del old_prefs[library_id]

    if library_config is None:
        #print("get prefs from db")
        library_config = db.prefs.get_namespaced(PREFS_NAMESPACE, PREFS_KEY_SETTINGS,
                                                 copy.deepcopy(default_prefs))
    return library_config

# fake out so I don't have to change the prefs calls anywhere.  The
# Java programmer in me is offended by op-overloading, but it's very
# tidy.
class PrefsFacade():
    def _get_db(self):
        if self.passed_db:
            return self.passed_db
        else:
            # In the GUI plugin we want current db so we detect when
            # it's changed.  CLI plugin calls need to pass db in.
            return get_gui().current_db
    
    def __init__(self,passed_db=None):
        self.default_prefs = default_prefs
        self.libraryid = None
        self.current_prefs = None
        self.passed_db=passed_db
        
    def _get_prefs(self):
        libraryid = get_library_uuid(self._get_db())
        if self.current_prefs == None or self.libraryid != libraryid:
            #print("self.current_prefs == None(%s) or self.libraryid != libraryid(%s)"%(self.current_prefs == None,self.libraryid != libraryid))
            self.libraryid = libraryid
            self.current_prefs = get_library_config(self._get_db())
        return self.current_prefs
        
    def __getitem__(self,k):            
        prefs = self._get_prefs()
        if k not in prefs:
            # pulls from default_prefs.defaults automatically if not set
            # in default_prefs
            return self.default_prefs[k]
        return prefs[k]

    def __setitem__(self,k,v):
        prefs = self._get_prefs()
        prefs[k]=v
        # self._save_prefs(prefs)

    def __delitem__(self,k):
        prefs = self._get_prefs()
        if k in prefs:
            del prefs[k]

    def save_to_db(self):
        set_library_config(self._get_prefs(),self._get_db())
        
prefs = PrefsFacade()

