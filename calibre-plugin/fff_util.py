# -*- coding: utf-8 -*-

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2020, Jim Miller'
__docformat__ = 'restructuredtext en'

from functools import reduce

from io import StringIO

import logging
logger = logging.getLogger(__name__)

from fanficfare import adapters
from fanficfare.configurable import Configuration
from calibre_plugins.fanficfare_plugin.prefs import prefs
from fanficfare.six import ensure_text
from fanficfare.six.moves import configparser
from fanficfare.six.moves import collections_abc

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
    configuration.readfp(StringIO(ensure_text(get_resources("plugin-defaults.ini"))))
    configuration.readfp(StringIO(ensure_text(personalini)))

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


class OrderedSet(collections_abc.MutableSet):

    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, next = self.map.pop(key)
            prev[2] = next
            next[1] = prev

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)

def get_common_elements(ll):
    ## returns a list of elements common to all lists in ll
    ## https://www.tutorialspoint.com/find-common-elements-in-list-of-lists-in-python
    return list(reduce(lambda i, j: i & j, (OrderedSet(n) for n in ll)))
