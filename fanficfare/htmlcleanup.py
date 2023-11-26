# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2018 FanFicFare team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from __future__ import absolute_import
import logging
logger = logging.getLogger(__name__)

import re

# py2 vs py3 transition
from .six import text_type as unicode
from .six import string_types as basestring
from .six import ensure_text
from .six import unichr

def _unirepl(match):
    "Return the unicode string for a decimal number"
    if match.group(1).startswith('x'):
        radix=16
        s = match.group(1)[1:]
    else:
        radix=10
        s = match.group(1)
    try:
        value = int(s, radix)
        retval = "%s%s"%(unichr(value),match.group(2))
    except:
        # This way, at least if there's more of entities out there
        # that fail, it doesn't blow the entire download.
        logger.warning("Numeric entity translation failed, skipping: &#x%s%s"%(match.group(1),match.group(2)))
        retval = ""
    return retval

def _replaceNumberEntities(data):
    # The same brokenish entity parsing in SGMLParser that inserts ';'
    # after non-entities will also insert ';' incorrectly after number
    # entities, including part of the next word if it's a-z.
    # "Don't&#8212ever&#8212do&#8212that&#8212again," becomes
    # "Don't&#8212e;ver&#8212d;o&#8212;that&#8212a;gain,"
    # Also need to allow for 5 digit decimal entities &#27861;
    # Last expression didn't allow for 2 digit hex correctly: &#xE9;
    p = re.compile(r'&#(x[0-9a-fA-F]{,4}|[0-9]{,5})([0-9a-fA-F]*?);')
    return p.sub(_unirepl, data)

def _replaceNotEntities(data):
    # not just \w or \S.  regexp from c:\Python25\lib\sgmllib.py
    # (or equiv), SGMLParser, entityref
    p = re.compile(r'&([a-zA-Z][-.a-zA-Z0-9]*);')
    return p.sub(r'&\1', data)

def stripHTML(soup, remove_all_entities=True):
    if isinstance(soup,basestring):
        retval = removeEntities(re.sub(r'<[^>]+>','',"%s" % soup),
                                remove_all_entities=remove_all_entities).strip()
    else:
        # bs4 already converts all the entities to UTF8 chars.
        retval = soup.get_text(strip=True)
        if not remove_all_entities:
            # put basic 3 entities back
            if '&' in retval and '&amp;' not in retval:
                # check in case called more than once.
                retval = retval.replace('&','&amp;')
            retval = retval.replace('<','&lt;').replace('>','&gt;')
    # some change in the python3 branch started making &nbsp; '\xc2\xa0'
    # instead of ' '
    return ensure_text(retval).replace(u'\xc2\xa0',' ').strip()

def conditionalRemoveEntities(value):
    if isinstance(value,basestring):
        return removeEntities(value).strip()
    else:
        return value

def removeAllEntities(text):
    # Remove &lt; &lt; and &amp; also
    return removeEntities(text, remove_all_entities=True)

def removeEntities(text, space_only=False, remove_all_entities=False):
    # keeps &amp;, &lt; and &gt; when remove_all_entities=False
    if text is None:
        return u""

    if not isinstance(text,basestring):
        text = unicode(text)

    try:
        t = text
    except (UnicodeEncodeError,UnicodeDecodeError) as e:
        try:
            t = text.encode ('ascii', 'xmlcharrefreplace')
        except (UnicodeEncodeError,UnicodeDecodeError) as e:
            t = text
    text = t
    # replace numeric versions of [&<>] with named versions,
    # then replace named versions with actual characters,
    text = re.sub(r'&#0*38;','&amp;',text)
    text = re.sub(r'&#0*60;','&lt;',text)
    text = re.sub(r'&#0*62;','&gt;',text)

    # replace remaining &#000; entities with unicode value, such as &#039; -> '
    text = _replaceNumberEntities(text)

    # replace several named entities with character, such as &mdash; -> -
    # reverse sort will put entities with ; before the same one without, when valid.
    for e in reversed(sorted(entities.keys())):
        v = entities[e]
        if space_only and re.match(r"^[^\s]$", v, re.UNICODE | re.S):
            # if not space
            continue
        try:
            text = text.replace(e, v)
        except UnicodeDecodeError as ex:
            # for the pound symbol
            text = text.replace(e, v.decode('utf-8'))

    # SGMLParser, and in turn, BeautifulStoneSoup doesn't parse
    # entities terribly well and inserts (;) after something that
    # it thinks might be an entity.  AT&T becomes AT&T; All of my
    # attempts to fix this by changing the input to
    # BeautifulStoneSoup break something else instead.  But at
    # this point, there should be *no* real entities left, so find
    # these not-entities and removing them here should be safe.
    text = _replaceNotEntities(text)

    if remove_all_entities:
        text = text.replace('&lt', '<').replace('&gt', '>').replace('&amp;', '&')
    else:
        # &lt; &gt; and &amp; are the only html entities allowed in xhtml, put those back.
        # They come out as &lt because _replaceNotEntities removes the ';'.
        text = text.replace('&', '&amp;').replace('&amp;lt', '&lt;').replace('&amp;gt', '&gt;')
    return text

## Currently used(optionally) by adapter_novelonlinefullcom and
## adapter_wwwnovelallcom only.  I hesitate to put the option in
## base_adapter.make_soup for all adapters due to concerns about it
## maybe breaking metadata parsing as it changes tags.
def fix_excess_space(text):
    # For easier extra space removing (when combining p an br)
    text = removeEntities(text, space_only=True)

    # Sometimes we don't have even tags like <p> or <br/>, so lets create <p> instead of two new_line
    text = re.sub(r"\n[ \s]*\n", "\n<p>", text, flags=re.UNICODE)

    # Combining all consequence of p and br to one <p>
    # bs4 will create </p> on his own, so don't worry
    text = re.sub(r"[ \s]*(</?p\b[^>]*>[ \s]*|<br\b[^>]*>[ \s]*)+", "\n<p>", text, flags=re.UNICODE)

    return text

import unicodedata
ZALGO_CHAR_CATEGORIES = ['Mn', 'Me']
def reduce_zalgo(text,max_zalgo=1):
    # borrows from https://stackoverflow.com/questions/22277052/how-can-zalgo-text-be-prevented
    # Also applies unicodedata.normalize('NFD')
    # See: https://docs.python.org/2/library/unicodedata.html#unicodedata.normalize
    lineout=[]
    count=0
    for c in unicodedata.normalize('NFD', text):
        if unicodedata.category(c) not in ZALGO_CHAR_CATEGORIES:
            lineout.append(c)
            count=0
        else:
            if count < max_zalgo:
                lineout.append(c)
            count+=1
    return ''.join(lineout)

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
         #'&gt;' : '>',
         #'&GT;' : '>',
         #'&GT' : '>',
         #'&gt' : '>',
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
         #'&lt;' : '<',
         #'&LT;' : '<',
         #'&LT' : '<',
         #'&lt' : '<',
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
