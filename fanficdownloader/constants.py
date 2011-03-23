# -*- coding: utf-8 -*-

CSS = '''body { margin-left: 2%; margin-right: 2%; margin-top: 2%; margin-bottom: 2%; text-align: justify; }
pre { font-size: x-small; }
sml { font-size: small; }
h1 { text-align: center; }
h2 { text-align: center; }
h3 { text-align: center; }
h4 { text-align: center; }
h5 { text-align: center; }
h6 { text-align: center; }
h7 { text-align: left; font-size: large; font-weight: bold; }
.CI {
    text-align:center;
    margin-top:0px;
    margin-bottom:0px;
    padding:0px;
    }
.center   {text-align: center;}
.cover    {text-align: center;}
.full     {width: 100%; }
.quarter  {width: 25%; }
.smcap    {font-variant: small-caps;}
.u        {text-decoration: underline;}
.bold     {font-weight: bold;}
'''

MIMETYPE = '''application/epub+zip'''

TITLE_HEADER = '''<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:xlink="http://www.w3.org/1999/xlink"><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
<title>%s - %s</title><link href="stylesheet.css" type="text/css" charset="UTF-8" rel="stylesheet"/></head><body>
<p><h3 id="lnks"><b><a id="StoryLink" href="%s">%s</a></b> by <b><a id="AuthorLink" href="%s">%s</a></b></h3></p>
'''

TITLE_ENTRY = '''<b>%s</b> %s<br />
'''

TITLE_FOOTER = '''
<br /><b>Summary:</b><br />%s<br />
</body></html>
'''

TABLE_TITLE_HEADER = TITLE_HEADER + '''
<table class="full">
'''

TABLE_TITLE_ENTRY = '''<tr><td><b>%s</b></td><td>%s</td></tr>
'''

TABLE_TITLE_FOOTER = '''
</table>
''' + TITLE_FOOTER

CONTAINER = '''<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
'''

CONTENT_START = '''<?xml version="1.0" encoding="utf-8"?>
<package version="2.0" xmlns="http://www.idpf.org/2007/opf"
         unique-identifier="fanficdownloader-uuid">
 <metadata xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
           xmlns:dc="http://purl.org/dc/elements/1.1/"
           xmlns:dcterms="http://purl.org/dc/terms/"
           xmlns:opf="http://www.idpf.org/2007/opf"
           xmlns:calibre="http://calibre.kovidgoyal.net/2009/metadata">
   <dc:identifier id="fanficdownloader-uuid">BookID-Epub-%s</dc:identifier>
   <dc:title>%s</dc:title> 
   <dc:creator opf:role="aut">%s</dc:creator>
   <dc:contributor opf:role="bkp">fanficdownloader [http://fanficdownloader.googlecode.com]</dc:contributor>
   <dc:language>%s</dc:language> 
   <dc:rights></dc:rights>
   <dc:date opf:event="publication">%s</dc:date>
   <dc:date opf:event="creation">%s</dc:date>
   <dc:date opf:event="modification">%s</dc:date>
   <meta name="calibre:timestamp" content="%s"/>
   <dc:description>%s</dc:description>
'''

CONTENT_END_METADATA = '''   <dc:publisher>%s</dc:publisher> 
   <dc:identifier id="BookId">%s</dc:identifier>
   <dc:identifier opf:scheme="URL">%s</dc:identifier>
   <dc:source>%s</dc:source>
   <dc:type>FanFiction</dc:type>
   <meta name="calibre:rating" content="%s"/>
 </metadata>
 <manifest>
  <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
  <item id="style" href="stylesheet.css" media-type="text/css" />
'''

CONTENT_SUBJECT = '''   <dc:subject>%s</dc:subject> 
'''

CONTENT_ITEM = '''  <item id="%s" href="%s" media-type="application/xhtml+xml" />
'''

CONTENT_END_MANIFEST = ''' </manifest>
 <spine toc="ncx">
'''

CONTENT_ITEMREF = '''  <itemref idref="%s" />
'''

CONTENT_END = ''' </spine>
</package>
'''

TOC_START = '''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="%s"/>
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

# entity list from http://code.google.com/p/doctype/wiki/CharacterEntitiesConsistent
entities = { '&aacute;' : 'á',
             '&Aacute;' : 'Á',
             '&Aacute' : 'Á',
             '&aacute' : 'á',
             '&acirc;' : 'â',
             '&Acirc;' : 'Â',
             '&Acirc' : 'Â',
             '&acirc' : 'â',
             '&acute;' : '´',
             '&acute' : '´',
             '&AElig;' : 'Æ',
             '&aelig;' : 'æ',
             '&AElig' : 'Æ',
             '&aelig' : 'æ',
             '&agrave;' : 'à',
             '&Agrave;' : 'À',
             '&Agrave' : 'À',
             '&agrave' : 'à',
             '&alefsym;' : 'ℵ',
             '&alpha;' : 'α',
             '&Alpha;' : 'Α',
             '&amp;' : '&',
             '&AMP;' : '&',
             '&AMP' : '&',
             '&amp' : '&',
             '&and;' : '∧',
             '&ang;' : '∠',
             '&aring;' : 'å',
             '&Aring;' : 'Å',
             '&Aring' : 'Å',
             '&aring' : 'å',
             '&asymp;' : '≈',
             '&atilde;' : 'ã',
             '&Atilde;' : 'Ã',
             '&Atilde' : 'Ã',
             '&atilde' : 'ã',
             '&auml;' : 'ä',
             '&Auml;' : 'Ä',
             '&Auml' : 'Ä',
             '&auml' : 'ä',
             '&bdquo;' : '„',
             '&beta;' : 'β',
             '&Beta;' : 'Β',
             '&brvbar;' : '¦',
             '&brvbar' : '¦',
             '&bull;' : '•',
             '&cap;' : '∩',
             '&ccedil;' : 'ç',
             '&Ccedil;' : 'Ç',
             '&Ccedil' : 'Ç',
             '&ccedil' : 'ç',
             '&cedil;' : '¸',
             '&cedil' : '¸',
             '&cent;' : '¢',
             '&cent' : '¢',
             '&chi;' : 'χ',
             '&Chi;' : 'Χ',
             '&circ;' : 'ˆ',
             '&clubs;' : '♣',
             '&cong;' : '≅',
             '&copy;' : '©',
             '&COPY;' : '©',
             '&COPY' : '©',
             '&copy' : '©',
             '&crarr;' : '↵',
             '&cup;' : '∪',
             '&curren;' : '¤',
             '&curren' : '¤',
             '&dagger;' : '†',
             '&Dagger;' : '‡',
             '&darr;' : '↓',
             '&dArr;' : '⇓',
             '&deg;' : '°',
             '&deg' : '°',
             '&delta;' : 'δ',
             '&Delta;' : 'Δ',
             '&diams;' : '♦',
             '&divide;' : '÷',
             '&divide' : '÷',
             '&eacute;' : 'é',
             '&Eacute;' : 'É',
             '&Eacute' : 'É',
             '&eacute' : 'é',
             '&ecirc;' : 'ê',
             '&Ecirc;' : 'Ê',
             '&Ecirc' : 'Ê',
             '&ecirc' : 'ê',
             '&egrave;' : 'è',
             '&Egrave;' : 'È',
             '&Egrave' : 'È',
             '&egrave' : 'è',
             '&empty;' : '∅',
             '&emsp;' : ' ',
             '&ensp;' : ' ',
             '&epsilon;' : 'ε',
             '&Epsilon;' : 'Ε',
             '&equiv;' : '≡',
             '&eta;' : 'η',
             '&Eta;' : 'Η',
             '&eth;' : 'ð',
             '&ETH;' : 'Ð',
             '&ETH' : 'Ð',
             '&eth' : 'ð',
             '&euml;' : 'ë',
             '&Euml;' : 'Ë',
             '&Euml' : 'Ë',
             '&euml' : 'ë',
             '&euro;' : '€',
             '&exist;' : '∃',
             '&fnof;' : 'ƒ',
             '&forall;' : '∀',
             '&frac12;' : '½',
             '&frac12' : '½',
             '&frac14;' : '¼',
             '&frac14' : '¼',
             '&frac34;' : '¾',
             '&frac34' : '¾',
             '&frasl;' : '⁄',
             '&gamma;' : 'γ',
             '&Gamma;' : 'Γ',
             '&ge;' : '≥',
             '&gt;' : '>',
             '&GT;' : '>',
             '&GT' : '>',
             '&gt' : '>',
             '&harr;' : '↔',
             '&hArr;' : '⇔',
             '&hearts;' : '♥',
             '&hellip;' : '…',
             '&iacute;' : 'í',
             '&Iacute;' : 'Í',
             '&Iacute' : 'Í',
             '&iacute' : 'í',
             '&icirc;' : 'î',
             '&Icirc;' : 'Î',
             '&Icirc' : 'Î',
             '&icirc' : 'î',
             '&iexcl;' : '¡',
             '&iexcl' : '¡',
             '&igrave;' : 'ì',
             '&Igrave;' : 'Ì',
             '&Igrave' : 'Ì',
             '&igrave' : 'ì',
             '&image;' : 'ℑ',
             '&infin;' : '∞',
             '&int;' : '∫',
             '&iota;' : 'ι',
             '&Iota;' : 'Ι',
             '&iquest;' : '¿',
             '&iquest' : '¿',
             '&isin;' : '∈',
             '&iuml;' : 'ï',
             '&Iuml;' : 'Ï',
             '&Iuml' : 'Ï',
             '&iuml' : 'ï',
             '&kappa;' : 'κ',
             '&Kappa;' : 'Κ',
             '&lambda;' : 'λ',
             '&Lambda;' : 'Λ',
             '&laquo;' : '«',
             '&laquo' : '«',
             '&larr;' : '←',
             '&lArr;' : '⇐',
             '&lceil;' : '⌈',
             '&ldquo;' : '“',
             '&le;' : '≤',
             '&lfloor;' : '⌊',
             '&lowast;' : '∗',
             '&loz;' : '◊',
             '&lrm;' : '‎',
             '&lsaquo;' : '‹',
             '&lsquo;' : '‘',
             '&lt;' : '<',
             '&LT;' : '<',
             '&LT' : '<',
             '&lt' : '<',
             '&macr;' : '¯',
             '&macr' : '¯',
             '&mdash;' : '—',
             '&micro;' : 'µ',
             '&micro' : 'µ',
             '&middot;' : '·',
             '&middot' : '·',
             '&minus;' : '−',
             '&mu;' : 'μ',
             '&Mu;' : 'Μ',
             '&nabla;' : '∇',
             '&nbsp;' : ' ',
             '&nbsp' : ' ',
             '&ndash;' : '–',
             '&ne;' : '≠',
             '&ni;' : '∋',
             '&not;' : '¬',
             '&not' : '¬',
             '&notin;' : '∉',
             '&nsub;' : '⊄',
             '&ntilde;' : 'ñ',
             '&Ntilde;' : 'Ñ',
             '&Ntilde' : 'Ñ',
             '&ntilde' : 'ñ',
             '&nu;' : 'ν',
             '&Nu;' : 'Ν',
             '&oacute;' : 'ó',
             '&Oacute;' : 'Ó',
             '&Oacute' : 'Ó',
             '&oacute' : 'ó',
             '&ocirc;' : 'ô',
             '&Ocirc;' : 'Ô',
             '&Ocirc' : 'Ô',
             '&ocirc' : 'ô',
             '&OElig;' : 'Œ',
             '&oelig;' : 'œ',
             '&ograve;' : 'ò',
             '&Ograve;' : 'Ò',
             '&Ograve' : 'Ò',
             '&ograve' : 'ò',
             '&oline;' : '‾',
             '&omega;' : 'ω',
             '&Omega;' : 'Ω',
             '&omicron;' : 'ο',
             '&Omicron;' : 'Ο',
             '&oplus;' : '⊕',
             '&or;' : '∨',
             '&ordf;' : 'ª',
             '&ordf' : 'ª',
             '&ordm;' : 'º',
             '&ordm' : 'º',
             '&oslash;' : 'ø',
             '&Oslash;' : 'Ø',
             '&Oslash' : 'Ø',
             '&oslash' : 'ø',
             '&otilde;' : 'õ',
             '&Otilde;' : 'Õ',
             '&Otilde' : 'Õ',
             '&otilde' : 'õ',
             '&otimes;' : '⊗',
             '&ouml;' : 'ö',
             '&Ouml;' : 'Ö',
             '&Ouml' : 'Ö',
             '&ouml' : 'ö',
             '&para;' : '¶',
             '&para' : '¶',
             '&part;' : '∂',
             '&permil;' : '‰',
             '&perp;' : '⊥',
             '&phi;' : 'φ',
             '&Phi;' : 'Φ',
             '&pi;' : 'π',
             '&Pi;' : 'Π',
             '&piv;' : 'ϖ',
             '&plusmn;' : '±',
             '&plusmn' : '±',
             '&pound;' : '£',
             '&pound' : '£',
             '&prime;' : '′',
             '&Prime;' : '″',
             '&prod;' : '∏',
             '&prop;' : '∝',
             '&psi;' : 'ψ',
             '&Psi;' : 'Ψ',
             '&quot;' : '"',
             '&QUOT;' : '"',
             '&QUOT' : '"',
             '&quot' : '"',
             '&radic;' : '√',
             '&raquo;' : '»',
             '&raquo' : '»',
             '&rarr;' : '→',
             '&rArr;' : '⇒',
             '&rceil;' : '⌉',
             '&rdquo;' : '”',
             '&real;' : 'ℜ',
             '&reg;' : '®',
             '&REG;' : '®',
             '&REG' : '®',
             '&reg' : '®',
             '&rfloor;' : '⌋',
             '&rho;' : 'ρ',
             '&Rho;' : 'Ρ',
             '&rlm;' : '‏',
             '&rsaquo;' : '›',
             '&rsquo;' : '’',
             '&sbquo;' : '‚',
             '&scaron;' : 'š',
             '&Scaron;' : 'Š',
             '&sdot;' : '⋅',
             '&sect;' : '§',
             '&sect' : '§',
             '&shy;' : '­', # strange optional hyphenation control character, not just a dash
             '&shy' : '­',
             '&sigma;' : 'σ',
             '&Sigma;' : 'Σ',
             '&sigmaf;' : 'ς',
             '&sim;' : '∼',
             '&spades;' : '♠',
             '&sub;' : '⊂',
             '&sube;' : '⊆',
             '&sum;' : '∑',
             '&sup1;' : '¹',
             '&sup1' : '¹',
             '&sup2;' : '²',
             '&sup2' : '²',
             '&sup3;' : '³',
             '&sup3' : '³',
             '&sup;' : '⊃',
             '&supe;' : '⊇',
             '&szlig;' : 'ß',
             '&szlig' : 'ß',
             '&tau;' : 'τ',
             '&Tau;' : 'Τ',
             '&there4;' : '∴',
             '&theta;' : 'θ',
             '&Theta;' : 'Θ',
             '&thetasym;' : 'ϑ',
             '&thinsp;' : ' ',
             '&thorn;' : 'þ',
             '&THORN;' : 'Þ',
             '&THORN' : 'Þ',
             '&thorn' : 'þ',
             '&tilde;' : '˜',
             '&times;' : '×',
             '&times' : '×',
             '&trade;' : '™',
             '&uacute;' : 'ú',
             '&Uacute;' : 'Ú',
             '&Uacute' : 'Ú',
             '&uacute' : 'ú',
             '&uarr;' : '↑',
             '&uArr;' : '⇑',
             '&ucirc;' : 'û',
             '&Ucirc;' : 'Û',
             '&Ucirc' : 'Û',
             '&ucirc' : 'û',
             '&ugrave;' : 'ù',
             '&Ugrave;' : 'Ù',
             '&Ugrave' : 'Ù',
             '&ugrave' : 'ù',
             '&uml;' : '¨',
             '&uml' : '¨',
             '&upsih;' : 'ϒ',
             '&upsilon;' : 'υ',
             '&Upsilon;' : 'Υ',
             '&uuml;' : 'ü',
             '&Uuml;' : 'Ü',
             '&Uuml' : 'Ü',
             '&uuml' : 'ü',
             '&weierp;' : '℘',
             '&xi;' : 'ξ',
             '&Xi;' : 'Ξ',
             '&yacute;' : 'ý',
             '&Yacute;' : 'Ý',
             '&Yacute' : 'Ý',
             '&yacute' : 'ý',
             '&yen;' : '¥',
             '&yen' : '¥',
             '&yuml;' : 'ÿ',
             '&Yuml;' : 'Ÿ',
             '&yuml' : 'ÿ',
             '&zeta;' : 'ζ',
             '&Zeta;' : 'Ζ',
             '&zwj;' : '‍',  # strange spacing control character, not just a space
             '&zwnj;' : '‌',  # strange spacing control character, not just a space
             }

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

HTML_ESC_Definitions = 'HTML_Escape.def'
