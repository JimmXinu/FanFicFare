#!/usr/bin/python
# Copyright(c) 2009 Andrew Chatham and Vijay Pandurangan

import re
import sys
import StringIO
import urllib

from BeautifulSoup import BeautifulSoup

class HtmlProcessor:
  WHITESPACE_RE = re.compile(r'\s')
  # Look for </blockquote  <p>
  BAD_TAG_RE = re.compile(r'<[^>]+<', re.MULTILINE)

  def __init__(self, html, unfill=0):
    self.unfill = unfill
    html = self._ProcessRawHtml(html)
    self._soup = BeautifulSoup(html)
    if self._soup.title:
      self.title = self._soup.title.contents[0]
    else:
      self.title = None

  def _ProcessRawHtml(self, html):
    new_html, count = HtmlProcessor.BAD_TAG_RE.subn('<', html)
    if count:
      print >>sys.stderr, 'Replaced %d bad tags' % count
    return new_html

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
      del anchor['href']
      anchor['filepos'] = '%.10d' % anchor_num
      anchor_num += 1
            
  def _ReplaceAnchorStubs(self):
    # TODO: Browsers allow extra whitespace in the href names.
    # use __str__ instead of prettify--it inserts extra spaces.
    assembled_text = self._soup.__str__('utf8')
    del self._soup # shouldn't touch this anymore
    for anchor_num, original_ref in self._anchor_references:
      ref = urllib.unquote(original_ref[1:]) # remove leading '#'
      # Find the position of ref in the utf-8 document.
      # TODO(chatham): Using regexes and looking for name= would be better.
      newpos = assembled_text.rfind(ref.encode('utf-8'))
      if newpos == -1:
        print >>sys.stderr, 'Could not find anchor "%s"' % original_ref
        continue
      newpos += len(ref) + 2  # don't point into the middle of the <a name> tag
      old_filepos = 'filepos="%.10d"' % anchor_num
      new_filepos = 'filepos="%.10d"' % newpos
      assert assembled_text.find(old_filepos) != -1
      assembled_text = assembled_text.replace(old_filepos, new_filepos, 1)
    return assembled_text

  def _FixPreTags(self):
    '''Replace <pre> tags with HTML-ified text.'''
    pres = self._soup.findAll('pre')
    for pre in pres:
      pre.replaceWith(self._FixPreContents(str(pre.contents[0])))

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
