#!/usr/bin/python
# -*- coding: UTF-8 -*-
#
# Author:        Pau Sanchez (contact@pausanchez.com)
# Version:       v1.0
# Last Modified: 2010/09/15
# 
# For the latest version check out:
#   http://www.codigomanso.com/en/projects
# 
# My blog:
#   http://www.codigomanso.com/en/  - English Version
#   http://www.codigomanso.com/es/  - Spanish Version
#

import sys
import os
import re
import hashlib

class bbcodebuilder:
  '''
  This class helps to build BBCode programmatically.

  The function names are used as the tag name, then the first parameter
  is the string that goes inside the tags and any extra parameter is 
  appended as a parameter to the tag

  Examples:
    > bbcode = bbcodebuilder()  # create a instance!

    > print bbcode.b ('bold')
    [b]bold[/b]

    > print bbcode.color ('this goes in red', 'red')
    [color=red]this goes in red[/color]

    > print bbcode.url ('Google', 'http://www.google.com')
    [url=http://www.google.com]Google[/url]
    
    > print bbcode.alist('item 1', 'item 2')
    [list=a]
      [*]item 1
      [*]item 2
    [/list]


  This solution is based on the recipe found on:
    http://code.activestate.com/recipes/576831-simple-bbcode-support/
  '''

  def __getattr__(self, name):
    '''
    This is a generic getter that returns a function which gets the first parameter
    as the string that goes between the tags, and extra parameters as tag parameters.

    The name of the attribute is used as the tag name
    '''
    class bbcodebuilder_helper:
      def __init__(self, name):
        self._name = name

      def __call__(self, string, *args):
        return u'[{0}{1}]{2}[/{0}]'.format(self._name, (u'=' + u','.join(map(str, args))) if args else u'', string)
    
    return bbcodebuilder_helper (name)

  def list(self, *items):
    return u'[list]' + u''.join(map(lambda item: u"\n  [*]" + item, items)) + u"\n[/list]"

  def nlist(self, *items):
    return u'[list=1]' + u''.join(map(lambda item: u"\n  [*]" + item, items)) + u"\n[/list]"

  def alist(self, *items):
    return u'[list=a]' + u''.join(map(lambda item: u"\n  [*]" + item, items)) + u"\n[/list]"


