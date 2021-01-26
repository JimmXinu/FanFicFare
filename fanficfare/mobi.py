#!/usr/bin/python

# -*- coding: utf-8 -*-
# Copyright(c) 2009 Andrew Chatham and Vijay Pandurangan
# Changes Copyright 2018 FanFicFare team
from __future__ import absolute_import

import struct
import time
import random
import logging

# py2 vs py3 transition
from .six import ensure_binary
from io import BytesIO

logger = logging.getLogger(__name__)

from .mobihtml import HtmlProcessor

# http://wiki.mobileread.com/wiki/MOBI
# http://membres.lycos.fr/microfirst/palm/pdb.html

encoding = {
  'UTF-8' : 65001,
  'latin-1' : 1252,
}

languages = {"en-us" : 0x0409,
             "sv"    : 0x041d,
             "fi"    : 0x000b,
             "en"    : 0x0009,
             "en-gb" : 0x0809}

class _SubEntry:
  def __init__(self, pos, html_data):
    self.pos = pos
    self.html = HtmlProcessor(html_data)
    self.title = self.html.title
    self._name = 'mobi_article_%d' % pos
    if not self.title:
      self.title = 'Article %d' % self.pos

  def TocLink(self):
    return '<a href="#%s_MOBI_START">%.80s</a>' % (self._name, self.title)

  def Anchor(self):
    return '<a name="%s_MOBI_START">' % self._name

  def Body(self):
    return self.html.RenameAnchors(self._name + '_')

class Converter:
  def __init__(self, refresh_url='', title='Unknown', author='Unknown', publisher='Unknown'):
    self._header = Header()
    self._header.SetTitle(title)
    self._header.SetAuthor(author)
    self._header.SetPublisher(publisher)
    self._refresh_url = refresh_url

  def ConvertString(self, s):
    out = BytesIO()
    self._ConvertStringToFile(s, out)
    return out.getvalue()

  def ConvertStrings(self, html_strs):
    out = BytesIO()
    self._ConvertStringsToFile(html_strs, out)
    return out.getvalue()

  def ConvertFile(self, html_file, out_file):
    self._ConvertStringToFile(open(html_file,'rb').read(),
                              open(out_file, 'wb'))

  def ConvertFiles(self, html_files, out_file):
    html_strs = [open(f,'rb').read() for f in html_files]
    self._ConvertStringsToFile(html_strs, open(out_file, 'wb'))

  def MakeOneHTML(self, html_strs):
    """This takes a list of HTML strings and returns a big HTML file with
    all contents consolidated.  It constructs a table of contents and adds
    anchors within the text
    """
    title_html = []
    toc_html = []
    body_html = []

    ## This gets broken by html5lib/bs4fixed being helpful, but we'll
    ## fix it inside mobihtml.py
    PAGE_BREAK = '<mbp:pagebreak/>'

    # pull out the title page, assumed first html_strs.
    htmltitle = html_strs[0]
    entrytitle = _SubEntry(1, htmltitle)
    title_html.append(entrytitle.Body())

    title_html.append(PAGE_BREAK)
    toc_html.append(PAGE_BREAK)
    toc_html.append('<a name="TOCTOP"><h3>Table of Contents</h3><br />')

    for pos, html in enumerate(html_strs[1:]):
      entry = _SubEntry(pos+1, html)
      toc_html.append('%s<br />' % entry.TocLink())

      # give some space between bodies of work.
      body_html.append(PAGE_BREAK)

      body_html.append(entry.Anchor())

      body_html.append(entry.Body())

    # TODO: this title can get way too long with RSS feeds. Not sure how to fix
    # cheat slightly and use the <a href> code to set filepos in references.
    header = '''<html>
<head>
<title>Bibliorize %s GMT</title>
  <guide>
    <reference href="#TOCTOP" type="toc" title="Table of Contents"/>
  </guide>
</head>
<body>
''' % time.ctime(time.time())

    footer = '</body></html>'
    # logger.debug("header:%s"%header)
    # logger.debug("title_html:%s"%title_html)
    # logger.debug("toc_html:%s"%toc_html)
    # logger.debug("body_html:%s"%body_html)
    # logger.debug("footer:%s"%footer)
    all_html = header + '\n'.join(title_html + toc_html + body_html) + footer
    #print "%s" % all_html.encode('utf8')
    return all_html

  def _ConvertStringsToFile(self, html_strs, out_file):
    try:
      tmp = self.MakeOneHTML(html_strs)
      self._ConvertStringToFile(tmp, out_file)
    except Exception as e:
      raise
      logger.error('Error %s', e)
      # logger.debug('Details: %s' % html_strs)

  def _ConvertStringToFile(self, html_data, out):
    html = HtmlProcessor(html_data)
    data = ensure_binary(html.CleanHtml())

    # collect offsets of '<mbp:pagebreak>' tags, use to make index list.
    # indexlist = [] # list of (offset,length) tuples.
    # not in current use.

    # j=0
    # lastj=0
    # while True:
    #   j=data.find('<mbp:pagebreak>',lastj+10) # plus a bit so we find the next.
    #   if j < 0:
    #     break
    #   indexlist.append((lastj,j-lastj))
    #   print "index offset: %d length: %d" % (lastj,j-lastj)
    #   lastj=j

    records = []
#    title = html.title
#    if title:
#      self._header.SetTitle(title)
    record_id = 1
    # logger.debug("len(data):%s"%len(data))
    for start_pos in range(0, len(data), Record.MAX_SIZE):
      end = min(len(data), start_pos + Record.MAX_SIZE)
      record_data = data[start_pos:end]
      records.append(self._header.AddRecord(record_data, record_id))
      # logger.debug("HTML Record %03d: (size:%d) [[%s ... %s]]" % ( record_id, len(record_data), record_data[:20], record_data[-20:] ))
      record_id += 1
    self._header.SetImageRecordIndex(record_id)
    records[0:0] = [self._header.MobiHeader()]

    header, rec_offset = self._header.PDBHeader(len(records))
    out.write(ensure_binary(header))
    for record in records:
      record.WriteHeader(out, rec_offset)
      # logger.debug("rec_offset: %d len(record.data): %d" % (rec_offset,len(record.data)))
      rec_offset += (len(record.data)+1) # plus one for trailing null

    # Write to nuls for some reason
    out.write(b'\0\0')
    for record in records:
      record.WriteData(out)
      out.write(b'\0')
      # needs a trailing null, I believe it indicates zero length 'overlap'.
      # otherwise, the readers eat the last char of each html record.
      # Calibre writes another 6-7 bytes of stuff after that, but we seem
      # to be getting along without it.

class Record:
  MAX_SIZE = 4096
  INDEX_LEN = 8
  _unique_id_seed = 28  # should be arbitrary, but taken from MobiHeader

  # TODO(chatham): Record compression doesn't look that hard.

  def __init__(self, data, record_id):
    assert len(data) <= self.MAX_SIZE
    self.data = data
    if record_id != 0:
      self._id = record_id
    else:
      Record._unique_id_seed += 1
      self._id = 0

  def __repr__(self):
    return 'Record: id=%d len=%d' % (self._id, len(self.data))

  def _SetUniqueId(self):
    Record._unique_id_seed += 1
    # TODO(chatham): Wraparound crap
    self._id = Record._unique_id_seed

  def WriteData(self, out):
    out.write(ensure_binary(self.data))

  def WriteHeader(self, out, rec_offset):
    attributes =  64 # dirty?
    header = struct.pack('>IbbH',
                         rec_offset,
                         attributes,
                         0, self._id)
    assert len(header) == Record.INDEX_LEN
    out.write(ensure_binary(header))

EXTH_HEADER_FIELDS = {
  'author' : 100,
  'publisher' : 101,
}

class Header:
  EPOCH_1904 = 2082844800

  def __init__(self):
    self._length = 0
    self._record_count = 0
    self._title = '2008_2_34'
    self._author = 'Unknown author'
    self._publisher = 'Unknown publisher'
    self._first_image_index = 0

  def SetAuthor(self, author):
    self._author = author.encode('ascii','ignore')

  def SetTitle(self, title):
    # TODO(chatham): Reevaluate whether this needs to be ASCII.
    # maybe just do sys.setdefaultencoding('utf-8')? Problems
    # appending self._title with other things.
    self._title = title.encode('ascii','ignore')

  def SetPublisher(self, publisher):
    self._publisher = publisher.encode('ascii','ignore')

  def AddRecord(self, data, record_id):
    self.max_record_size = max(Record.MAX_SIZE, len(data))
    self._record_count += 1
    # logger.debug("len(data):%s"%len(data))
    self._length += len(data)
    return Record(data, record_id)

  def _ReplaceWord(self, data, pos, word):
    return data[:pos] + struct.pack('>I', word) + data[pos+4:]

  def PalmDocHeader(self):
    compression = 1  # no compression
    unused = 0
    encryption_type = 0  # no ecryption
    records = self._record_count + 1  # the header record itself
    palmdoc_header = struct.pack('>HHIHHHH',
                                 compression,
                                 unused,
                                 self._length,
                                 records,
                                 Record.MAX_SIZE,
                                 encryption_type,
                                 unused)
    assert len(palmdoc_header) == 16
    return palmdoc_header

  def PDBHeader(self, num_records):
    # logger.debug("num_records:%s"%num_records)
    HEADER_LEN = 32+2+2+9*4
    RECORD_INDEX_HEADER_LEN = 6
    RESOURCE_INDEX_LEN = 10

    index_len = RECORD_INDEX_HEADER_LEN + num_records * Record.INDEX_LEN
    rec_offset = HEADER_LEN + index_len + 2
    # logger.debug("index_len:%s"%index_len)
    # logger.debug("rec_offset:%s"%rec_offset)

    short_title = self._title[0:31]
    attributes = 0
    version = 0
    ctime = self.EPOCH_1904 + int(time.time())
    mtime = self.EPOCH_1904 + int(time.time())
    backup_time = self.EPOCH_1904 + int(time.time())
    modnum = 0
    appinfo_offset = 0
    sort_offset = 0
    type = b'BOOK'
    creator = b'MOBI'
    id_seed = 36
    header = struct.pack('>32sHHII',
                         ensure_binary(short_title), attributes, version,
                         ctime, mtime)
    header += struct.pack('>IIII', backup_time, modnum,
                         appinfo_offset, sort_offset)
    header += struct.pack('>4s4sI',
                         type, creator, id_seed)
    next_record = 0  # not used?
    header += struct.pack('>IH', next_record, num_records)
    return header, rec_offset

  def _GetExthHeader(self):
    # They set author, publisher, coveroffset, thumboffset
    data = {'author' : self._author,
            'publisher' : self._publisher,
            }
    # Turn string type names into EXTH typeids.
    r = []
    for key, value in data.items():
      typeid = EXTH_HEADER_FIELDS[key]
      length_encoding_len = 8
      r.append(struct.pack('>LL', typeid, len(value) + length_encoding_len,) + value)
    content = b''.join(r)
    # logger.debug("len(content):%s"%len(content))

    # Pad to word boundary
    while len(content) % 4:
      content += b'\0'
    # logger.debug("len(content):%s"%len(content))
    TODO_mysterious = 12
    exth = b'EXTH' + struct.pack('>LL', len(content) + TODO_mysterious, len(data)) + content
    return exth

  def SetImageRecordIndex(self, idx):
    self._first_image_index = idx

  def MobiHeader(self):
    exth_header = self._GetExthHeader();
    palmdoc_header = self.PalmDocHeader()

    fs = 0xffffffff

    # Record 0
    header_len = 0xE4 # TODO
    mobi_type = 2 # BOOK
    text_encoding = encoding['UTF-8']
    unique_id = random.randint(1, 1<<32)
    creator_version = 4
    reserved = b'%c' % 0xff * 40
    nonbook_index = fs
    # logger.debug("header_len:%s"%header_len)
    # logger.debug("len(palmdoc_header):%s"%len(palmdoc_header))
    # logger.debug("len(exth_header):%s"%len(exth_header))
    full_name_offset = header_len + len(palmdoc_header) + len(exth_header) # put full name after header
    language = languages['en-us']
    unused = 0
    mobi_header = struct.pack('>4sIIIII40sIIIIII',
                              b'MOBI',
                              header_len,
                              mobi_type,
                              text_encoding,
                              unique_id,
                              creator_version,
                              reserved,
                              nonbook_index,
                              full_name_offset,
                              len(self._title),
                              language,
                              fs, fs)
    assert len(mobi_header) == 104 - 16

    unknown_fields = chr(0) * 32
    drm_offset = 0
    drm_count = 0
    drm_size = 0
    drm_flags = 0
    exth_flags = 0x50
    header_end = chr(0) * 64
    mobi_header += struct.pack('>IIIIIII',
                               creator_version,
                               self._first_image_index,
                               fs,
                               unused,
                               fs,
                               unused,
                               exth_flags)
    mobi_header += b'\0' * 112 # TODO: Why this much padding?
    # Set some magic offsets to be 0xFFFFFFF.
    for pos in (0x94, 0x98, 0xb0, 0xb8, 0xc0, 0xc8, 0xd0, 0xd8, 0xdc):
      mobi_header = self._ReplaceWord(mobi_header, pos, fs)

    # 16 bytes?
    padding = b'\0' * 48 * 4 # why?
    total_header = palmdoc_header + mobi_header + exth_header + self._title + padding

    return self.AddRecord(total_header, 0)

if __name__ == '__main__':
  import sys
  m = Converter(title='Testing Mobi', author='Mobi Author', publisher='mobi converter')
  m.ConvertFiles(sys.argv[1:], 'test.mobi')
  #m.ConvertFile(sys.argv[1], 'test.mobi')
