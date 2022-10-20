# -*- coding: utf-8 -*-

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2021, Jim Miller'
__docformat__ = 'restructuredtext en'

import logging
logger = logging.getLogger(__name__)

import copy

from calibre.gui2.ui import get_gui

# pulls in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre_plugins.fanficfare_plugin import __version__ as plugin_version
from calibre_plugins.fanficfare_plugin.common_utils import get_library_uuid

SKIP=_('Skip')
ADDNEW=_('Add New Book')
UPDATE=_('Update EPUB if New Chapters')
UPDATEALWAYS=_('Update EPUB Always')
OVERWRITE=_('Overwrite if Newer')
OVERWRITEALWAYS=_('Overwrite Always')
CALIBREONLY=_('Update Calibre Metadata from Web Site')
CALIBREONLYSAVECOL=_('Update Calibre Metadata from Saved Metadata Column')
collision_order=[SKIP,
                 ADDNEW,
                 UPDATE,
                 UPDATEALWAYS,
                 OVERWRITE,
                 OVERWRITEALWAYS,
                 CALIBREONLY,
                 CALIBREONLYSAVECOL,]

# best idea I've had for how to deal with config/pref saving the
# collision name in english.
SAVE_SKIP='Skip'
SAVE_ADDNEW='Add New Book'
SAVE_UPDATE='Update EPUB if New Chapters'
SAVE_UPDATEALWAYS='Update EPUB Always'
SAVE_OVERWRITE='Overwrite if Newer'
SAVE_OVERWRITEALWAYS='Overwrite Always'
SAVE_CALIBREONLY='Update Calibre Metadata Only'
SAVE_CALIBREONLYSAVECOL='Update Calibre Metadata Only(Saved Column)'
save_collisions={
    SKIP:SAVE_SKIP,
    ADDNEW:SAVE_ADDNEW,
    UPDATE:SAVE_UPDATE,
    UPDATEALWAYS:SAVE_UPDATEALWAYS,
    OVERWRITE:SAVE_OVERWRITE,
    OVERWRITEALWAYS:SAVE_OVERWRITEALWAYS,
    CALIBREONLY:SAVE_CALIBREONLY,
    CALIBREONLYSAVECOL:SAVE_CALIBREONLYSAVECOL,
    SAVE_SKIP:SKIP,
    SAVE_ADDNEW:ADDNEW,
    SAVE_UPDATE:UPDATE,
    SAVE_UPDATEALWAYS:UPDATEALWAYS,
    SAVE_OVERWRITE:OVERWRITE,
    SAVE_OVERWRITEALWAYS:OVERWRITEALWAYS,
    SAVE_CALIBREONLY:CALIBREONLY,
    SAVE_CALIBREONLYSAVECOL:CALIBREONLYSAVECOL,
    }

anthology_collision_order=[UPDATE,
                           UPDATEALWAYS,
                           OVERWRITEALWAYS]


# Show translated strings, but save the same string in prefs so your
# prefs are the same in different languages.
YES=_('Yes, Always')
SAVE_YES='Yes'
YES_IF_IMG=_('Yes, if EPUB has a cover image')
SAVE_YES_IF_IMG='Yes, if img'
YES_UNLESS_IMG=_('Yes, unless FanFicFare found a cover image')
SAVE_YES_UNLESS_IMG='Yes, unless img'
YES_UNLESS_SITE=_('Yes, unless found on site')
SAVE_YES_UNLESS_SITE='Yes, unless site'
NO=_('No')
SAVE_NO='No'
prefs_save_options = {
    YES:SAVE_YES,
    SAVE_YES:YES,
    YES_IF_IMG:SAVE_YES_IF_IMG,
    SAVE_YES_IF_IMG:YES_IF_IMG,
    YES_UNLESS_IMG:SAVE_YES_UNLESS_IMG,
    SAVE_YES_UNLESS_IMG:YES_UNLESS_IMG,
    NO:SAVE_NO,
    SAVE_NO:NO,
    YES_UNLESS_SITE:SAVE_YES_UNLESS_SITE,
    SAVE_YES_UNLESS_SITE:YES_UNLESS_SITE,
    }
updatecalcover_order=[YES,YES_IF_IMG,NO]
gencalcover_order=[YES,YES_UNLESS_IMG,NO]
do_wordcount_order=[YES,YES_UNLESS_SITE,NO]

PREFS_NAMESPACE = 'FanFicFarePlugin'
PREFS_KEY_SETTINGS = 'settings'

# Set defaults used by all.  Library specific settings continue to
# take from here.
default_prefs = {}
default_prefs['last_saved_version'] = (0,0,0)
default_prefs['personal.ini'] = get_resources('plugin-example.ini')
default_prefs['cal_cols_pass_in'] = False
default_prefs['rejecturls'] = '' # removed, but need empty default for fallback
default_prefs['rejectreasons'] = '''Sucked
Boring
Dup from another site'''
default_prefs['reject_always'] = False
default_prefs['reject_delete_default'] = True

default_prefs['updatemeta'] = True
default_prefs['bgmeta'] = False
#default_prefs['updateepubcover'] = True # removed in favor of always True Oct 2022
default_prefs['keeptags'] = False
default_prefs['suppressauthorsort'] = False
default_prefs['suppresstitlesort'] = False
default_prefs['authorcase'] = False
default_prefs['titlecase'] = False
default_prefs['setanthologyseries'] = False
default_prefs['mark'] = False
default_prefs['mark_success'] = True
default_prefs['mark_failed'] = True
default_prefs['mark_chapter_error'] = True
default_prefs['showmarked'] = False
default_prefs['autoconvert'] = False
default_prefs['urlsfromclip'] = True
default_prefs['button_instantpopup'] = False
default_prefs['updatedefault'] = True
default_prefs['fileform'] = 'epub'
default_prefs['collision'] = SAVE_UPDATE
default_prefs['deleteotherforms'] = False
default_prefs['adddialogstaysontop'] = False
default_prefs['lookforurlinhtml'] = False
default_prefs['checkforseriesurlid'] = True
default_prefs['auto_reject_seriesurlid'] = False
default_prefs['mark_series_anthologies'] = False
default_prefs['checkforurlchange'] = True
default_prefs['injectseries'] = False
default_prefs['matchtitleauth'] = True
default_prefs['do_wordcount'] = SAVE_YES_UNLESS_SITE
default_prefs['smarten_punctuation'] = False
default_prefs['show_est_time'] = False

default_prefs['send_lists'] = ''
default_prefs['read_lists'] = ''
default_prefs['addtolists'] = False
default_prefs['addtoreadlists'] = False
default_prefs['addtolistsonread'] = False
default_prefs['autounnew'] = False

default_prefs['updatecalcover'] = SAVE_YES_IF_IMG
default_prefs['covernewonly'] = False
default_prefs['gencalcover'] = SAVE_YES_UNLESS_IMG
default_prefs['updatecover'] = False
default_prefs['calibre_gen_cover'] = True
default_prefs['plugin_gen_cover'] = False
default_prefs['gcnewonly'] = True
default_prefs['gc_site_settings'] = {}
default_prefs['allow_gc_from_ini'] = True
default_prefs['gc_polish_cover'] = False

default_prefs['countpagesstats'] = []
default_prefs['wordcountmissing'] = False

default_prefs['errorcol'] = ''
default_prefs['save_all_errors'] = True
default_prefs['savemetacol'] = ''
default_prefs['lastcheckedcol'] = ''
default_prefs['custom_cols'] = {}
default_prefs['custom_cols_newonly'] = {}
default_prefs['allow_custcol_from_ini'] = True

default_prefs['std_cols_newonly'] = {}
default_prefs['set_author_url'] = True
default_prefs['includecomments'] = False
default_prefs['anth_comments_newonly'] = True

default_prefs['imapserver'] = ''
default_prefs['imapuser'] = ''
default_prefs['imappass'] = ''
default_prefs['imapsessionpass'] = False
default_prefs['imapfolder'] = 'INBOX'
default_prefs['imaptags'] = ''
default_prefs['imapmarkread'] = True
default_prefs['auto_reject_from_email'] = False
default_prefs['update_existing_only_from_email'] = False
default_prefs['download_from_email_immediately'] = False

def set_library_config(library_config,db,setting=PREFS_KEY_SETTINGS):
    db.prefs.set_namespaced(PREFS_NAMESPACE,
                            setting,
                            library_config)

def get_library_config(db,setting=PREFS_KEY_SETTINGS,def_prefs=default_prefs):
    library_id = get_library_uuid(db)
    library_config = None

    if library_config is None:
        #print("get prefs from db")
        library_config = db.prefs.get_namespaced(PREFS_NAMESPACE,
                                                 setting)

        if library_config is None:
            # defaults.
            logger.info("Using default settings")
            library_config = copy.deepcopy(def_prefs)

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

    def __init__(self,passed_db=None,setting=PREFS_KEY_SETTINGS,def_prefs=default_prefs):
        self.default_prefs = def_prefs
        self.setting=setting
        self.libraryid = None
        self.current_prefs = None
        self.passed_db=passed_db

    def _get_prefs(self):
        libraryid = get_library_uuid(self._get_db())
        if self.current_prefs == None or self.libraryid != libraryid:
            #print("self.current_prefs == None(%s) or self.libraryid != libraryid(%s)"%(self.current_prefs == None,self.libraryid != libraryid))
            self.libraryid = libraryid
            self.current_prefs = get_library_config(self._get_db(),
                                                    setting=self.setting,
                                                    def_prefs=self.default_prefs)
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
        self['last_saved_version'] = plugin_version
        set_library_config(self._get_prefs(),self._get_db(),setting=self.setting)

prefs = PrefsFacade(setting=PREFS_KEY_SETTINGS,
                    def_prefs=default_prefs)

rejects_data = PrefsFacade(setting="rejects_data",
                           def_prefs={'rejecturls_data':[]})
