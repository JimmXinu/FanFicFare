#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2019, Jim Miller'
__docformat__ = 'restructuredtext en'

import sys, os
if sys.version_info >= (2, 7):
    import logging
    logger = logging.getLogger(__name__)
    loghandler=logging.StreamHandler()
    loghandler.setFormatter(logging.Formatter("FFF: %(levelname)s: %(asctime)s: %(filename)s(%(lineno)d): %(message)s"))
    logger.addHandler(loghandler)

    from calibre.constants import DEBUG
    if os.environ.get('CALIBRE_WORKER', None) is not None or DEBUG:
        loghandler.setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    else:
        loghandler.setLevel(logging.CRITICAL)
        logger.setLevel(logging.CRITICAL)

# pulls in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

# The class that all Interface Action plugin wrappers must inherit from
from calibre.customize import InterfaceActionBase

# pulled out from FanFicFareBase for saving in prefs.py
__version__ = (3, 10, 8)

## Apparently the name for this class doesn't matter--it was still
## 'demo' for the first few versions.
class FanFicFareBase(InterfaceActionBase):
    '''
    This class is a simple wrapper that provides information about the
    actual plugin class. The actual interface plugin class is called
    InterfacePlugin and is defined in the fff_plugin.py file, as
    specified in the actual_plugin field below.

    The reason for having two classes is that it allows the command line
    calibre utilities to run without needing to load the GUI libraries.
    '''
    name                = 'FanFicFare'
    description         = _('UI plugin to download FanFiction stories from various sites.')
    supported_platforms = ['windows', 'osx', 'linux']
    author              = 'Jim Miller'
    version             = __version__
    minimum_calibre_version = (1, 48, 0)

    #: This field defines the GUI plugin class that contains all the code
    #: that actually does something. Its format is module_path:class_name
    #: The specified class must be defined in the specified module.
    actual_plugin       = 'calibre_plugins.fanficfare_plugin.fff_plugin:FanFicFarePlugin'

    def is_customizable(self):
        '''
        This method must return True to enable customization via
        Preferences->Plugins
        '''
        return True

    def config_widget(self):
        '''
        Implement this method and :meth:`save_settings` in your plugin to
        use a custom configuration dialog.

        This method, if implemented, must return a QWidget. The widget can have
        an optional method validate() that takes no arguments and is called
        immediately after the user clicks OK. Changes are applied if and only
        if the method returns True.

        If for some reason you cannot perform the configuration at this time,
        return a tuple of two strings (message, details), these will be
        displayed as a warning dialog to the user and the process will be
        aborted.

        The base class implementation of this method raises NotImplementedError
        so by default no user configuration is possible.
        '''
        # It is important to put this import statement here rather than at the
        # top of the module as importing the config class will also cause the
        # GUI libraries to be loaded, which we do not want when using calibre
        # from the command line
        from calibre_plugins.fanficfare_plugin.config import ConfigWidget
        return ConfigWidget(self.actual_plugin_)

    def save_settings(self, config_widget):
        '''
        Save the settings specified by the user with config_widget.

        :param config_widget: The widget returned by :meth:`config_widget`.
        '''
        config_widget.save_settings()

        # Apply the changes
        ac = self.actual_plugin_
        if ac is not None:
            ac.apply_settings()

    def load_actual_plugin(self, gui):
        with self: # so the sys.path was modified while loading the
                   # plug impl.
            return InterfaceActionBase.load_actual_plugin(self,gui)

    def cli_main(self,argv):

        with self: # so the sys.path was modified appropriately
            # I believe there's no performance hit loading these here when
            # CLI--it would load everytime anyway.
            from calibre.library import db
            from calibre_plugins.fanficfare_plugin.fanficfare.cli import main as fff_main
            from calibre_plugins.fanficfare_plugin.prefs import PrefsFacade
            from calibre.utils.config import prefs as calibre_prefs
            from optparse import OptionParser

            parser = OptionParser('%prog --run-plugin '+self.name+' -- [options] <storyurl>')
            parser.add_option('--library-path', '--with-library', default=None, help=_('Path to the calibre library. Default is to use the path stored in the settings.'))
            # parser.add_option('--dont-notify-gui', default=False, action='store_true',
            #               help=_('Do not notify the running calibre GUI (if any) that the database has'
            #                      ' changed. Use with care, as it can lead to database corruption!'))

            pargs = [x for x in argv if x.startswith('--with-library') or x.startswith('--library-path')
                     or not x.startswith('-')]
            opts, args = parser.parse_args(pargs)

            fff_prefs = PrefsFacade(db(path=opts.library_path,
                                        read_only=True))

            fff_main(argv[1:],
                     parser=parser,
                     passed_defaultsini=get_resources("fanficfare/defaults.ini"),
                     passed_personalini=fff_prefs["personal.ini"],
                     )
