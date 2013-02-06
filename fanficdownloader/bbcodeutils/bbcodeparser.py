#!/usr/bin/python
# -*- coding: utf-8 -*-
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

class bbcodeparser:
  '''
  This class parses BBCode into a internal structure to allow later processing and
  conversion to HTML.

  The parser tries to fix invalid code (like unclosed tags)

  Useful URLs:
    http://en.wikipedia.org/wiki/BBCode
    http://www.bbcode.org/reference.php

  Example:
    > bbcode = bbcodeparser ()
    > bbcode.parse ('[b]text in bold[/b]').html()
    <b>text in bold</b>

    # dump HTML
    > bbcode.parse ('[p][color=red]text in red').html()
    <p><span style="color:red;">text in red</span></p>

    # dump fixed BBCode
    > bbcode.parse ('[p][color=red]text in red').bbcode()
    [p][color=red]text in red[/color][/p]

    > bbcode.parse ('This [b][i]code[/b] will be fixed[/invalid]').bbcode()
    This [b][i]code[/i][/b] will be fixed

    # dump fixed bbcode
    > str (bbcodeparse ('This [b][i]code[/b] will be fixed[/invalid]'))
    This [b][i]code[/i][/b] will be fixed
  '''
  _bbcode = ''
  _tokens = []

  def __init__ (self, bbcode = '', fixInvalidCode = True):
    ''' Initialize and parse bbcode string (if any is given)
    '''
    self.parse (bbcode, fixInvalidCode)
    return

  def __str__ (self):
    return self.bbcode()

  def parse (self, bbcode = None, fixInvalidCode = True):
    '''
    It will parse and return the token list, trying to fix tags if
    fixInvalidCode is True

    It will return the current object to allow chaining

    Example:
      code = bbcode()
      code.parse ('<b>bold</b>', True) -> 
      code.parse ('<b>bold<i>italics</b>', True) -> internally will add the missing '</i>'
    '''
    if bbcode is not None:
      self._bbcode = bbcode
      self._tokens = self.tokenize (bbcode)
      if fixInvalidCode:
        self._tokens = self.fixWrongTags (self._tokens)

    return self

  # return ALL tokens
  def getTokens (self):
    return self._tokens

  def bbcode (self):
    '''
    Dump BBCode again. This is useful for dumping valid BBCode
    '''
    bbcode = []
    for token in self._tokens:
      if token is None:
        continue

      if isinstance (token, basestring):
        bbcode.append (token.replace (u'[', u'\[').replace (u']', u'\]'))
        continue
      
      tag       = token['tag']  # opening or closing simple tag. e.g: 'b', '/b', '/u', ...
      tagOpener = (u'/' if tag[0] == u'/' else u'')

      if (tagOpener == '/') or ('args' not in token):
        bbcode.append (u'[' + tag + u']')
      else:
        # process args
        argstr = ''

        # the arg with the same name as the tag repersents the '=whatever'
        if tag in token['args']:
          if re.match ('\s|"', token['args'][tag]) is None:
            argstr = u'=' + token['args'][tag]
          else:
            argstr = u'="' + token['args'][tag].replace (u'"', u'\"') + u'"'

        for (k,v) in token['args'].iteritems():
          if k == tag: # already processed
            continue
          argstr += ' ' + k + u'="' + v.replace (u'"', u'\"') + u'"'
          
        bbcode.append (u'[' + tag + argstr + ']')

    return u''.join (bbcode)

  def html (self, allowClassAttr = False, doDeepCopy = True):
    '''
    Convert current parsed code to HTML

    @allowClassAttr
      Is something like [b class="asdf"] allowed?

    @doDeepCopy 
      True:  it does a deep copy of tokens so this list will remain unchanged
      False: tokens will be modified internally, but the output will be produced like 5x faster
             it's a good idea to use False when the string parsed is huge and this is the
             last operation on the string

    Example:
      code = bbcode ('[b]bold[/b]')
      code.html() -> '<b>bold</b>'
    '''
    from bbcode2html import bbcode2html
    return bbcode2html.convertToHTML (self._tokens, allowClassAttr = allowClassAttr, doDeepCopy = doDeepCopy)


  @staticmethod
  def fixWrongTags (inTokenList):
    ''' Add missing tokens that have not been closed properly and try to fix some scenarios
    '''
    opened       = []
    outTokenList = []
    for token in inTokenList:
      # normal string... do nothing
      if isinstance(token, basestring):
        outTokenList.append (token)
      else:
        # if starts with '/' is closing a tag
        if token['tag'][0] == '/':
          while (len (opened) > 0) and (opened[-1] != token['tag'][1:]):
            outTokenList.append ({'tag' : '/' + opened[-1] })
            del opened[-1]

          if len(opened):
            del opened[-1]
            outTokenList.append (token)

        # opening tag
        else:
          # if I open the same tag I opened before, close it, and open it again
          if (len(opened) > 0) and (token['tag'] == opened[-1]):
            outTokenList.append ({'tag' : '/' + opened[-1] })
          else:
            opened.append (token['tag'])
          outTokenList.append (token)

    # close all elements that have not been closed
    while len(opened):
      outTokenList.append ({'tag' : '/' + opened[-1] })
      del opened[-1]

    return outTokenList

  @staticmethod
  def tokenize(code):
    '''
    Tokenize BBCode tags and parameters

    Return the token list using a internal format. See the example:
      [
        { 'tag' : 'p', 'args' : { 'font' : 'arial' } },
        'This is ',
        { 'tag' : 'url', 'args' : {'url' : 'http://www.google.com'} },
        'a link to google',
        { 'tag' : '/url' },
        { 'tag' : '/p' }
      ]
    '''
    re_tags    = re.compile (r'(\[[^]]+\])', re.DOTALL | re.UNICODE)
    re_tagName = re.compile (r'\[([^]=\s]+)([^]]*)\]',  re.DOTALL | re.UNICODE)
    #re_tagArgs = re.compile (r'\s*([^=]*)=(("([^"]+)")|([^\s]+))',  re.DOTALL | re.UNICODE)
    re_tagArgs = re.compile (r'\s*([\w]*)=(("([^"]+)")|([^\s]+))',  re.DOTALL | re.UNICODE)

    # get a unique name and replace escaped braces encode utf8 to
    # prevent CLI/Web from barfing on unicode chars.  Not sure why
    # this even needs to be 'unique' like this, but that's the way
    # they wrote it.
    unique = hashlib.md5(code.encode('utf8')).hexdigest()
    code   = code.replace ('\[', unique+'_OPEN_BRACE')
    code   = code.replace ('\]', unique+'_CLOSE_BRACE')

    splitted = re_tags.split(code)

    outTokenList = []
    for token in splitted:
      if len(token) == 0:
        continue
      
      if token[0] == '[':
        match   = re_tagName.match (token)
        if match:
          tagName = match.group(1)
          tagArgs = match.group(2)
          
          tagToken = { 'tag' : tagName.lower() }
  
          # parse arguments (if any)
          if len(tagArgs) > 0:
            allArgs = re_tagArgs.findall(tagArgs)
  
            tagArgs = {}
            for arg in allArgs:
              # if the argument has no name, use the tagName itself
              argName  = (arg[0] if arg[0] != '' else tagName)
              argValue = (arg[3] if (arg[1][0] == '"') else arg[4])
  
              tagArgs[argName.lower()] = argValue.replace ('\"', '"')
  
            tagToken['args'] = tagArgs
  
          outTokenList.append (tagToken)

        # no match, append the text as it is
        else:
          outTokenList.append (token)
      # append the text as it is
      else:
        outTokenList.append (token)

    # restore escaped braces back (once code is parsed)
    restoredTokenList = []
    for token in outTokenList:
      if isinstance (token, basestring):
        token = token.replace (unique+'_OPEN_BRACE', '[').replace (unique+'_CLOSE_BRACE', ']')
      restoredTokenList.append (token)

    return restoredTokenList

