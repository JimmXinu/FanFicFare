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
import urllib

class bbcode2html:
  '''
  This class gets a parsed BBCode and transforms it to valid HTML

  Useful functions of this class:
    html
    convertToHTML

  Example:
    > parser = bbcodeparser ()
    > parser.parse ('[b]bold[/b]')
    > bbcode2html (parser).html()
    <b>bold</b>

    # This is faster for huge strings but changes the parser object internally
    > bbcode2html (parser).html(doDeepCopy = False)
    <b>bold</b>
  '''
  def __init__ (self, parser):
    self._parser = parser
    return

  def html (self, allowClassAttr = False, doDeepCopy = True, parser = None):
    '''
    Convert current parsed code to HTML

    Example:
      code = bbcodeparser ('[b]bold[/b]')
      code.html() -> '<b>bold</b>'
    '''
    if parser is None:
      parser = self._parser

    tokens = parser
    if instanceof (parser, bbcodeparser):
      tokens = parser.getTokens()

    return bbcode2html.convertToHTML (tokens, allowClassAttr = allowClassAttr, doDeepCopy = doDeepCopy)

  @staticmethod
  def htmlString (string):
    toReplace = {
      u'<' : '&lt;',
      u'>' : '&gt;',
      u'"' : "&quot;",
      u'&' : "&amp;"
    }
    for entity in toReplace:
      string = string.replace(entity, toReplace[entity])
    return string

  @staticmethod
  def getValidTags ():
    simpleTags = ['b', 'u', 'i', 'sup', 'sub', 'ul', 'ol', 'li', 'table', 'tr', 'th', 'td', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    validTags = {
      'p'         : { 'color' : 'color', 'size' : 'size', 'font' : 'font' },
      'color'     : { 'color' : 'color' },
      'size'      : { 'size' : 'size' },
      'font'      : { 'font' : 'font' },
      'img'       : { 'alt' : 'alt', 'title' : 'title', 'width' : 'width' , 'height' : 'height', 'img' : 'img'},
      'url'       : { 'href' : 'href', 'url' : 'href', 'link'  : 'href', 'title' : 'title' },
      's'         : { },
      'code'      : { },
      'quote'     : { },
      'list'      : { 'list' : 'type' },
      'email'     : { 'email': 'href'},
      'google'    : { 'google':  'google'},
      'wikipedia' : { 'wikipedia' : 'wikipedia', 'language' : 'language', 'lang' : 'lang'}
    }

    for tag in simpleTags:
      validTags[tag] = { }
    return validTags

  @staticmethod
  def convertToHTML (tokens, allowClassAttr = False, validTags = None, doDeepCopy = True):
    '''
    Convert internally parsed BBCode to XHTML

    @doDeepCopy 
      True:  it does a deep copy of tokens so this list will remain unchanged
      False: tokens will be modified internally, but the output will be produced like 5x faster
             it's a good idea to use False only when this is the last operation
    '''
    # do a deep copy
    if doDeepCopy:
      import copy
      tokens = copy.deepcopy (tokens)

    # filter invalid tags and attributes
    if validTags is None:
      validTags = bbcode2html.getValidTags()    

    bbcode2html._filterInvalidTagsAndAttributes (tokens, validTags, allowClassAttr)
    
    # Start to convert
    index       = 0
    tokenLength = len (tokens)

    # use a list for the output (an order of magnitude faster than using string concatenation)
    htmlList = []
    lastListOpener = []

    while index < tokenLength:

      if isinstance (tokens [index], basestring):
        htmlList.append (bbcode2html.htmlString (tokens [index]))
        index += 1
        continue

      token     = tokens[index] 
      tag       = token['tag']  # opening or closing simple tag. e.g: 'b', '/b', '/u', ...
      tagName   = (tag[1:] if tag[0] == '/' else tag)
      tagOpener = (u'/' if tag[0] == '/' else u'')
      tokenArgs = (token['args'] if 'args' in token else {})

      # opening or closing simple tag COLOR / SIZE
      if (tagName in ['p', 'color', 'size', 'font']): 
        style  = ''
        style += ((u' color: ' + tokenArgs['color'] + u';') if ('color' in tokenArgs) else '')
        style += ((u' font-size: ' + tokenArgs['size'] + u'pt;') if ('size' in tokenArgs) else '')
        style += ((u' font-family: ' + tokenArgs['font'] + u';') if ('font' in tokenArgs) else '')
        style  = style.strip()

        pArgs = {}
        if style != '':
          pArgs ['style'] = style

        if 'class' in tokenArgs:
          pArgs ['class'] = tokenArgs['class']

        if ('args' not in token) and (tagName != 'p'):
          if (tagOpener == '/'): # if closing tag, close it
            htmlList.append (u'</span>')
          index += 1
          continue

        if tagName != 'p':
          tag = tagOpener + u'span'

        htmlList.append (bbcode2html.xml (tag, pArgs))

      # IMG tag
      elif tag == 'img' and (index+2 < tokenLength):
        if 'img' in tokenArgs:
          # has the form of <width>x<height> ?
          sizeMatch = re.match (u'^\s*(\d+)[xX](\d+)\s*$', tokenArgs['img'])
          if sizeMatch is not None:
            tokenArgs['width']  = sizeMatch.group(1)
            tokenArgs['height'] = sizeMatch.group(2)
          # then assume is the alternative text
          else:
            tokenArgs['alt'] = tokenArgs['img']
          del tokenArgs['img']

        # add the source of the image
        tokenArgs ['src'] = tokens[index+1]

        # [img]http://www.whatever.com/pic.jpg[/img]
        htmlList.append (
          bbcode2html.xml ('img', tokenArgs, soloTag=True)
        )
        index += 2 # skip next token and closing tag

      # URL tag
      elif tag == 'url':
        if ('args' not in token) and (index+2 < tokenLength):
          # [url]http://www.google.com[/url]
          htmlList.append (bbcode2html.xml ('a', { 'href' : tokens[index+1] }))
        else:
          # [url=http://www.google.com]Google[/url]
          # [url link=http://www.google.com title="This is Google"]Google[/url]
          htmlList.append (bbcode2html.xml ('a', tokenArgs))
  
      # URL closing tag (sometimes needed)
      elif (tag == '/url') or (tag == '/email'):
        htmlList.append (u'</a>')

      # Email tag
      elif tag == 'email':
        if ('args' not in token) and (index+2 < tokenLength):
          # [email]asdf@asdf.com]
          htmlList.append (bbcode2html.xml ('a', { 'href' : u'mailto:' + tokens[index+1].strip() }))
        else:
          # [email=asdf@asfd.com]john smith[/email]
          if 'href' in tokenArgs:
            tokenArgs['href'] = u'mailto:' + tokenArgs['href']
          htmlList.append (bbcode2html.xml ('a', tokenArgs))
  
      elif tagName == 'list':
        if tagOpener == '/':
          htmlList.append (bbcode2html.xml (u'/' + lastListOpener.pop()))
        else:
          if ('type' not in tokenArgs):
            htmlList.append (bbcode2html.xml (tagOpener + u'ul', tokenArgs))
            lastListOpener.append ('ul')
          else:
            htmlList.append (bbcode2html.xml (tagOpener + u'ol', tokenArgs))
            lastListOpener.append ('ol')

      elif tagName == '*':
        htmlList.append (bbcode2html.xml (tagOpener + u'li', tokenArgs))

      elif (tagName == 's'):
        tokenArgs['style'] =  'text-decoration: line-through;'
        htmlList.append (bbcode2html.xml (tagOpener + u'span', tokenArgs))

      elif (tagName == 'code'):
        htmlList.append (bbcode2html.xml (tagOpener + u'pre', tokenArgs))

      elif (tagName == 'quote'):
        htmlList.append (bbcode2html.xml (tagOpener + u'blockquote', tokenArgs))

      elif (tagName == 'google'):
        htmlList.append (
          bbcode2html.xml (
            tagOpener + u'a', 
            {'href' : 'http://www.google.com/search?q=' + urllib.quote_plus (tokens[index+1])},
            tokens[index+1]
          )
        )
        index += 2

      elif (tagName == 'wikipedia'):
        subdomain = 'www'
        for arg  in ['lang', 'language', 'wikipedia']:
          if arg in tokenArgs:
            subdomain = tokenArgs[arg] 

        htmlList.append (
          bbcode2html.xml (
            tagOpener + u'a', 
            {'href' : 'http://' + subdomain + '.wikipedia.org/wiki/' + tokens[index+1].replace (' ', '_')},
            tokens[index+1]
          )
        )
        index += 2

      elif (tagName in validTags):
        htmlList.append (
          bbcode2html.xml (tag, tokenArgs)
        )

      else:
        # ignore this tag
        pass 

      index += 1

    return ''.join (htmlList)

  @staticmethod
  def _filterInvalidTagsAndAttributes (tokens, validTags, allowClassAttr):
    '''
    Helper function to filter out invalid attributes from the tokens list
    '''
    # add 'class' attribute as valid (mapping 'class' itself)
    if allowClassAttr:
      for attr in validTags:
        validTags[attr]['class'] = 'class'

    # remove invalid attributes from tokens
    for tindex in range(0, len(tokens)):
      if isinstance (tokens[tindex], dict) and ('args' in tokens[tindex]) and (tokens[tindex]['tag'] in validTags):
        validList = validTags[tokens[tindex]['tag']]

        filteredArgs = {}
        for arg in tokens[tindex]['args']:
          if arg in validList:
            # rename the argument
            filteredArgs[validList[arg]] = tokens[tindex]['args'][arg]
          else:
            pass # do not include this arg in the filteredArgs

        tokens[tindex]['args'] = filteredArgs

    return

  @staticmethod
  def xml (tag, attrs = {}, text = None, soloTag = False):
    '''
    Helper function to produce valid XML output
    '''
    xml = u'<' + tag.lower()

    # make sure we sort attributes alphabetically (for deterministic output)
    # Faster but non-deterministic:
    #  for (key, value) in attrs.iteritems():
    #    xml += u' ' + key + u'="' + value + u'"'
    for key in sorted (attrs.keys()):
      xml += u' ' + key + u'="' + attrs[key] + u'"'
      
    # close tag
    if text is None:
      if soloTag:
        xml += u' />'
      else:
        xml += u'>'
    else:
      xml += u'>' + text + u'</' + tag.lower() + '>'

    return xml



