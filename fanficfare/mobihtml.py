#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright(c) 2009 Andrew Chatham and Vijay Pandurangan
# Changes Copyright 2018 FanFicFare team

## This module is used by mobi.py exclusively.
## Renamed Jul 2018 to avoid conflict with other 'html' packages
from __future__ import absolute_import

import re
import sys
import logging

# py2 vs py3 transition
from .six.moves.urllib.parse import unquote
from .six import text_type as unicode
from .six import binary_type as bytes
from .six import ensure_binary

# import bs4
# BeautifulSoup = bs4.BeautifulSoup
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class HtmlProcessor:
  WHITESPACE_RE = re.compile(r'\s')
  # Look for </blockquote  <p>
  #BAD_TAG_RE = re.compile(r'<[^>]+<', re.MULTILINE)

  def __init__(self, html, unfill=0):
    self.unfill = unfill
#    html = self._ProcessRawHtml(html)
    self._soup = BeautifulSoup(html,'html5lib')
    # logger.debug(html)
    ## mobi format wants to find this <guide> tag inside <head>.
    ## html5lib, on the other hand, moved it to <body>.  So we'll move
    ## it back.
    guide = self._soup.find('guide')
    if guide:
      self._soup.head.append(guide)
    # logger.debug(self._soup)
    if self._soup.title.contents:
      self.title = self._soup.title.contents[0]
    else:
      self.title = None

  # Unnecessary with BS4
  # def _ProcessRawHtml(self, html):
  #   new_html, count = HtmlProcessor.BAD_TAG_RE.subn('<', html)
  #   if count:
  #     print >>sys.stderr, 'Replaced %d bad tags' % count
  #   return new_html

  def _StubInternalAnchors(self):
    '''Replace each internal anchor with a fixed-size filepos anchor.

    Looks for every anchor with <a href="#myanchor"> and replaces that
    with <a filepos="00000000050">. Stores anchors in self._anchor_references'''
    self._anchor_references = []
    anchor_num = 0
    # anchor links
    anchorlist = self._soup.findAll('a', href=re.compile('^#'))
    # treat reference tags like a tags for TOCTOP.
    anchorlist.extend(self._soup.findAll('reference', href=re.compile('^#')))
    for anchor in anchorlist:
      self._anchor_references.append((anchor_num, anchor['href']))
      anchor['filepos'] = '%.10d' % anchor_num
      # logger.debug("Add anchor: %s %s"%((anchor_num, anchor)))
      del anchor['href']
      anchor_num += 1

  def _ReplaceAnchorStubs(self):
    # TODO: Browsers allow extra whitespace in the href names.

    assembled_text = ensure_binary(unicode(self._soup))
    # html5lib/bs4 creates close tags for <mbp:pagebreak>
    assembled_text = assembled_text.replace(b'<mbp:pagebreak>',b'<mbp:pagebreak/>')
    assembled_text = assembled_text.replace(b'</mbp:pagebreak>',b'')

    del self._soup # shouldn't touch this anymore
    for anchor_num, original_ref in self._anchor_references:
      ref = unquote(original_ref[1:]) # remove leading '#'
      # Find the position of ref in the utf-8 document.
      # TODO(chatham): Using regexes and looking for name= would be better.
      newpos = assembled_text.find(b'name="'+ensure_binary(ref)) # .encode('utf-8')
      if newpos == -1:
        logger.warn('Could not find anchor "%s"' % original_ref)
        continue
      # instead of somewhere slightly *after* the <a> tag pointed to,
      # let's go right in front of it instead by looking for the page
      # break before it.
      newpos = assembled_text.rfind(b'<',0,newpos)
      # logger.debug("Anchor Pos: %s %s '%s|%s'"%((anchor_num, newpos,assembled_text[newpos-15:newpos],assembled_text[newpos:newpos+15])))
      old_filepos = b'filepos="%.10d"' % anchor_num
      new_filepos = b'filepos="%.10d"' % newpos
      assert assembled_text.find(old_filepos) != -1
      assembled_text = assembled_text.replace(old_filepos, new_filepos, 1)
    return assembled_text

  def _FixPreTags(self):
    '''Replace <pre> tags with HTML-ified text.'''
    pres = self._soup.findAll('pre')
    for pre in pres:
      pre.replaceWith(self._FixPreContents(unicode(pre.contents[0])))

  def _FixPreContents(self, text):
    if self.unfill:
      line_splitter = '\n\n'
      line_joiner = '<p>'
    else:
      line_splitter = '\n'
      line_joiner = '<br>'
    lines = []
    for line in text.split(line_splitter):
      lines.append(self.WHITESPACE_RE.subn('&nbsp;', line)[0])
    return line_joiner.join(lines)

  def _RemoveUnsupported(self):
    '''Remove any tags which the kindle cannot handle.'''
    # TODO(chatham): <link> tags to script?
    unsupported_tags = ('script', 'style')
    for tag_type in unsupported_tags:
      for element in self._soup.findAll(tag_type):
        element.extract()

  def RenameAnchors(self, prefix):
    '''Rename every internal anchor to have the given prefix, then
    return the contents of the body tag.'''
    for anchor in self._soup.findAll('a', href=re.compile('^#')):
      anchor['href'] = '#' + prefix + anchor['href'][1:]
    for a in self._soup.findAll('a'):
      if a.get('name'):
        a['name'] = prefix + a['name']

    # TODO(chatham): figure out how to fix this. sometimes body comes out
    # as NoneType.
    content = []
    if self._soup.body is not None:
      content = [unicode(c) for c in self._soup.body.contents]
    return '\n'.join(content)

  def CleanHtml(self):
    # TODO(chatham): fix_html_br, fix_html
    self._RemoveUnsupported()
    self._StubInternalAnchors()
    self._FixPreTags()
    return self._ReplaceAnchorStubs()


if __name__ == '__main__':
  FILE ='/tmp/documentation.html'
  #FILE = '/tmp/multipre.html'
  FILE = '/tmp/view.html'
  import codecs
  d = open(FILE).read()
  h = HtmlProcessor(d)
  s = h.CleanHtml()
  #print s
