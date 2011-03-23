#!/usr/bin/python
# Copyright(c) 2009 Andrew Chatham and Vijay Pandurangan

    
import StringIO
import struct
import time
import random
import logging

from html import HtmlProcessor

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

def ToHex(s):
  v = ['%.2x' % ord(c) for c in s]
  return ' '.join(v)

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
    out = StringIO.StringIO()
    self._ConvertStringToFile(s, out)
    return out.getvalue()

  def ConvertStrings(self, html_strs):
    out = StringIO.StringIO()
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

    PAGE_BREAK = '<mbp:pagebreak>'

    # pull out the title page, assumed first html_strs.
    htmltitle = html_strs[0]
    entrytitle = _SubEntry(1, htmltitle)
    title_html.append(entrytitle.Body())
    
    toc_html.append(PAGE_BREAK)
    toc_html.append('<h3>Table of Contents</h3><br />')

    for pos, html in enumerate(html_strs[1:]):
      entry = _SubEntry(pos+1, html)
      toc_html.append('%s<br />' % entry.TocLink())

      # give some space between bodies of work.
      body_html.append(PAGE_BREAK)
        
      body_html.append(entry.Anchor())
      
      body_html.append(entry.Body())
      
    # TODO: this title can get way too long with RSS feeds. Not sure how to fix
    header = '<html><head><title>Bibliorize %s GMT</title></head><body>' % time.ctime(
      time.time())

    footer = '</body></html>'
    all_html = header + '\n'.join(title_html + toc_html + body_html) + footer
    #print "%s" % all_html.encode('utf8')
    return all_html

  def _ConvertStringsToFile(self, html_strs, out_file):
    try:
      tmp = self.MakeOneHTML(html_strs)
      self._ConvertStringToFile(tmp, out_file)
    except Exception, e:
      logging.error('Error %s', e)
      logging.debug('Details: %s' % html_strs)

  def _ConvertStringToFile(self, html_data, out):
    html = HtmlProcessor(html_data)
    data = html.CleanHtml()
    records = []
#    title = html.title
#    if title:
#      self._header.SetTitle(title)
    record_id = 1
    for start_pos in range(0, len(data), Record.MAX_SIZE):
      end = min(len(data), start_pos + Record.MAX_SIZE)
      record_data = data[start_pos:end]
      records.append(self._header.AddRecord(record_data, record_id))
      record_id += 1
    self._header.SetImageRecordIndex(record_id)
    records[0:0] = [self._header.MobiHeader()]

    header, rec_offset = self._header.PDBHeader(len(records))
    out.write(header)
    for record in records:
      record.WriteHeader(out, rec_offset)
      rec_offset += len(record.data)

    # Write to nuls for some reason
    out.write('\0\0')
    for record in records:
      record.WriteData(out)

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
    out.write(self.data)

  def WriteHeader(self, out, rec_offset):
    attributes =  64 # dirty?
    header = struct.pack('>IbbH',
                         rec_offset,
                         attributes,
                         0, self._id)
    assert len(header) == Record.INDEX_LEN
    out.write(header)

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
    HEADER_LEN = 32+2+2+9*4
    RECORD_INDEX_HEADER_LEN = 6
    RESOURCE_INDEX_LEN = 10

    index_len = RECORD_INDEX_HEADER_LEN + num_records * Record.INDEX_LEN
    rec_offset = HEADER_LEN + index_len + 2

    short_title = self._title[0:31]
    attributes = 0
    version = 0
    ctime = self.EPOCH_1904 + int(time.time())
    mtime = self.EPOCH_1904 + int(time.time())
    backup_time = self.EPOCH_1904 + int(time.time())
    modnum = 0
    appinfo_offset = 0
    sort_offset = 0
    type = 'BOOK'
    creator = 'MOBI'
    id_seed = 36
    header = struct.pack('>32sHHII',
                         short_title, attributes, version,
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
    content = ''.join(r)

    # Pad to word boundary
    while len(content) % 4:
      content += '\0'
    TODO_mysterious = 12
    exth = 'EXTH' + struct.pack('>LL', len(content) + TODO_mysterious, len(data)) + content
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
    reserved = '%c' % 0xff * 40
    nonbook_index = fs
    full_name_offset = header_len + len(palmdoc_header) + len(exth_header) # put full name after header
    language = languages['en-us']
    unused = 0
    mobi_header = struct.pack('>4sIIIII40sIIIIII',
                              'MOBI',
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
    mobi_header += '\0' * 112 # TODO: Why this much padding?
    # Set some magic offsets to be 0xFFFFFFF.
    for pos in (0x94, 0x98, 0xb0, 0xb8, 0xc0, 0xc8, 0xd0, 0xd8, 0xdc):
      mobi_header = self._ReplaceWord(mobi_header, pos, fs)

    # 16 bytes?
    padding = '\0' * 48 * 4 # why?
    total_header = palmdoc_header + mobi_header + exth_header + self._title + padding

    return self.AddRecord(total_header, 0)

if __name__ == '__main__':
  import sys
  m = Converter(title='Testing Mobi', author='Mobi Author', publisher='mobi converter')
  m.ConvertFiles(sys.argv[1:], 'test.mobi')
  #m.ConvertFile(sys.argv[1], 'test.mobi')
