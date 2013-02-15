#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2013, Jim Miller'
__docformat__ = 'restructuredtext en'

from StringIO import StringIO

from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader import adapters, exceptions
from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader.configurable import Configuration
from calibre_plugins.fanfictiondownloader_plugin.config import (prefs)

def get_ffdl_personalini():
    if prefs['includeimages']:
        # this is a cheat to make it easier for users.
        return '''[epub]
include_images:true
keep_summary_html:true
make_firstimage_cover:true
''' + prefs['personal.ini']
    else:
        return prefs['personal.ini']

def get_ffdl_config(url,fileform="EPUB",personalini=None):
    if not personalini:
        personalini = get_ffdl_personalini()
    site='unknown'
    try:
        site = adapters.getConfigSectionFor(url)
    except Exception as e:
        print("Failed trying to get ini config for url(%s): %s, using section [%s] instead"%(url,e,site))
    configuration = Configuration(site,fileform)
    configuration.readfp(StringIO(get_resources("plugin-defaults.ini")))
    configuration.readfp(StringIO(personalini))

    return configuration

def get_ffdl_adapter(url,fileform="EPUB",personalini=None):
    return adapters.getAdapter(get_ffdl_config(url,fileform,personalini),url)
    
