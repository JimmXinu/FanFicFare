# -*- coding: utf-8 -*-

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2015, Jim Miller'
__docformat__ = 'restructuredtext en'

from io import StringIO

import logging
logger = logging.getLogger(__name__)

from calibre_plugins.fanficfare_plugin.fanficfare import adapters, exceptions
from calibre_plugins.fanficfare_plugin.fanficfare.configurable import Configuration
from calibre_plugins.fanficfare_plugin.prefs import prefs
from .fanficfare.six.moves import configparser

def get_fff_personalini():
    return prefs['personal.ini']

def get_fff_config(url,fileform="epub",personalini=None):
    if not personalini:
        personalini = get_fff_personalini()
    sections=['unknown']
    try:
        sections = adapters.getConfigSectionsFor(url)
    except Exception as e:
        logger.debug("Failed trying to get ini config for url(%s): %s, using section %s instead"%(url,e,sections))
    configuration = Configuration(sections,fileform)
    configuration.readfp(StringIO(get_resources("plugin-defaults.ini").decode('utf-8')))
    configuration.readfp(StringIO(personalini.decode('utf-8')))

    return configuration

def get_fff_adapter(url,fileform="epub",personalini=None):
    return adapters.getAdapter(get_fff_config(url,fileform,personalini),url)

def test_config(initext):
    try:
        configini = get_fff_config("test1.com?sid=555",
                                    personalini=initext)
        errors = configini.test_config()
    except configparser.ParsingError as pe:
        errors = pe.errors

    return errors
