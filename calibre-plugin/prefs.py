#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2015, Jim Miller'
__docformat__ = 'restructuredtext en'

import logging
logger = logging.getLogger(__name__)

import copy

from calibre.utils.config import JSONConfig
from calibre.gui2.ui import get_gui

from calibre_plugins.fanficfare_plugin.dialogs import UPDATE
from calibre_plugins.fanficfare_plugin.common_utils import get_library_uuid

# if don't have any settings for FanFicFarePlugin, copy from
# predecessor FanFictionDownLoaderPlugin.
FFDL_PREFS_NAMESPACE = 'FanFictionDownLoaderPlugin'
PREFS_NAMESPACE = 'FanFicFarePlugin'
PREFS_KEY_SETTINGS = 'settings'

# Set defaults used by all.  Library specific settings continue to
# take from here.
default_prefs = {}
default_prefs['personal.ini'] = get_resources('plugin-example.ini')
default_prefs['rejecturls'] = ''
default_prefs['rejectreasons'] = '''Sucked
Boring
Dup from another site'''
default_prefs['reject_always'] = False

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
default_prefs['collision'] = UPDATE
default_prefs['deleteotherforms'] = False
default_prefs['adddialogstaysontop'] = False
default_prefs['includeimages'] = False
default_prefs['lookforurlinhtml'] = False
default_prefs['checkforseriesurlid'] = True
default_prefs['checkforurlchange'] = True
default_prefs['injectseries'] = False
default_prefs['smarten_punctuation'] = False
default_prefs['show_est_time'] = False

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
default_prefs['wordcountmissing'] = False

default_prefs['errorcol'] = ''
default_prefs['custom_cols'] = {}
default_prefs['custom_cols_newonly'] = {}
default_prefs['allow_custcol_from_ini'] = True

default_prefs['std_cols_newonly'] = {}

default_prefs['imapserver'] = ''
default_prefs['imapuser'] = ''
default_prefs['imappass'] = ''
default_prefs['imapsessionpass'] = False
default_prefs['imapfolder'] = 'INBOX'
default_prefs['imapmarkread'] = True

def set_library_config(library_config,db):
    db.prefs.set_namespaced(PREFS_NAMESPACE,
                            PREFS_KEY_SETTINGS,
                            library_config)

def get_library_config(db):
    library_id = get_library_uuid(db)
    library_config = None

    if library_config is None:
        #print("get prefs from db")
        library_config = db.prefs.get_namespaced(PREFS_NAMESPACE,
                                                 PREFS_KEY_SETTINGS)
        
        # if don't have any settings for FanFicFarePlugin, copy from
        # predecessor FanFictionDownLoaderPlugin.
        if library_config is None:
            logger.info("Attempting to read settings from predecessor--FFDL")
            library_config = db.prefs.get_namespaced(FFDL_PREFS_NAMESPACE,
                                                     PREFS_KEY_SETTINGS)
        if library_config is None:
            # defaults.
            logger.info("Using default settings")
            library_config = copy.deepcopy(default_prefs)
            
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

