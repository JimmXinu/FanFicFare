# -*- coding: utf-8 -*-

CSS = '''body { margin-left: 5%; margin-right: 5%; margin-top: 5%; margin-bottom: 5%; text-align: justify; }
pre { font-size: x-small; }
h1 { text-align: center; }
h2 { text-align: center; }
h3 { text-align: center; }
h4 { text-align: center; }
h5 { text-align: center; }
h6 { text-align: center; }
.CI {
    text-align:center;
    margin-top:0px;
    margin-bottom:0px;
    padding:0px;
    }
.center   {text-align: center;}
.smcap    {font-variant: small-caps;}
.u        {text-decoration: underline;}
.bold     {font-weight: bold;}
'''

MIMETYPE = '''application/epub+zip'''

CONTAINER = '''<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
'''

CONTENT_START = '''<?xml version="1.0"?>
<package version="2.0" xmlns="http://www.idpf.org/2007/opf"
         unique-identifier="BookID">
 <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"
           xmlns:opf="http://www.idpf.org/2007/opf">
   <dc:title>%s</dc:title> 
   <dc:creator opf:role="aut">%s</dc:creator>
   <dc:language>en-UK</dc:language> 
   <dc:rights></dc:rights>
   <dc:subject>fanfiction</dc:subject> 
   <dc:publisher>sgzmd</dc:publisher> 
   <dc:identifier id="BookID">%s</dc:identifier>
 </metadata>
 <manifest>
  <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
  <item id="style" href="stylesheet.css" media-type="text/css" />
'''

CONTENT_ITEM = '''<item id="%s" href="%s" media-type="application/xhtml+xml" />
'''

CONTENT_END_MANIFEST = '''</manifest>
<spine toc="ncx">
'''

CONTENT_ITEMREF = '''<itemref idref="%s" />
'''

CONTENT_END = '''</spine>
</package>
'''

TOC_START = '''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="sigizmund.com062820072147132"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle>
    <text>%s</text>
  </docTitle>
  <navMap>
'''

TOC_ITEM = '''<navPoint id="%s" playOrder="%d">
  <navLabel>
    <text>%s</text>
  </navLabel>
  <content src="%s"/>
</navPoint>
'''

TOC_END = '''</navMap>
</ncx>
'''

XHTML_START = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>%s</title>
<link href="stylesheet.css" type="text/css" rel="stylesheet" />
</head>
<body>
<div>
<h3>%s</h3>
'''

XHTML_END = '''</div>
</body>
</html>
'''

acceptable_elements = ['a', 'abbr', 'acronym', 'address', 'area', 'b', 'big',
      'blockquote', 'br', 'center', 'cite', 'code', 'col',
      'colgroup', 'dd', 'del', 'dfn', 'dir', 'dl', 'dt', 'em',
      'font', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'i', 
      'ins', 'kbd', 'label', 'li', 'ol', 
      'p', 'pre', 'q', 's', 'samp', 'small', 'span', 'strike',
      'strong', 'sub', 'sup', 'u', 'ul']

acceptable_attributes = ['href']

entities = { '&ndash;' : ' - ', '&mdash;' : ' - ', '&rdquo;' : '"', '&ldquo;' : '"', '&rsquo;' : '\'', 
             '&lsquo;' : '\'', '&quot;' : '"', '&hellip;' : '...', '&amp;' : '&', '&pound;' : '£', '&nbsp;' : ' ' }

FB2_PROLOGUE = '<FictionBook>'
FB2_DESCRIPTION = '''<description>
<title-info>
  <genre>fanfiction</genre>
  <author>
  <first-name></first-name>
  <middle-name></middle-name>
  <last-name>%s</last-name>
  </author>
  <book-title>%s</book-title>
  <lang>eng</lang>
</title-info>
<document-info>
  <author>
  <nickname>sgzmd</nickname>
  </author>
<date value="%s">%s</date>
<id>sgzmd_%s</id>
<version>2.0</version>
</document-info>
</description>'''
