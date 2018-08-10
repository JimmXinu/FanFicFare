# -*- coding: utf-8 -*-

# Copyright 2013 Fanficdownloader team, 2018 FanFicFare team
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
import codecs
import bs4 as bs

# py2 vs py3 transition
from .six import text_type as unicode
from .six.moves import range

from . import HtmlTagStack as stack
from . import exceptions as exceptions

def logdebug(s):
    # uncomment for debug output
    # logger.debug(s)
    pass

was_run_marker=u'FFF_replace_br_with_p_has_been_run'
def replace_br_with_p(body):
    if was_run_marker in body:
        # logger.debug("replace_br_with_p previously applied, skipping.")
        return body

    # Ascii character (and Unicode as well) xA0 is a non-breaking space, ascii code 160.
    # However, Python Regex does not recognize it as a whitespace, so we'll be changing it to a regular space.
    # .strip() so "\n<div>" at beginning is also recognized.
    body = body.replace(u'\xa0', u' ').strip()

    if body.find('>') == -1 or body.rfind('<') == -1:
        return body

    # logdebug(u'---')
    # logdebug(u'BODY start.: ' + body[:4000])
    # logdebug(u'--')
    # logdebug(u'BODY end...: ' + body[-250:])
    # logdebug(u'BODY.......: ' + body)
    # logdebug(u'---')

    # clean breaks (<br />), removing whitespaces between them.
    body = re.sub(r'\s*<br[^>]*>\s*', r'<br />', body)

    # change surrounding div to a p and remove attrs Top surrounding
    # tag in all cases now should be div, to just strip the first and
    # last tags.
    if is_valid_block(body) and body.find('<div') == 0:
        body = body[body.index('>')+1:body.rindex('<')].strip()

    # BS is doing some BS on entities, meaning &lt; and &gt; are turned into < and >... a **very** bad idea in html.
    body = re.sub(r'&(.+?);', r'XAMP;\1;', body)

    body = soup_up_div(u'<div>' + body + u'</div>')

    body = body[body.index('>')+1:body.rindex('<')]

    # Find all existing blocks with p, pre and blockquote tags, we need to shields break tags inside those.
    # This is for "lenient" mode, however it is also used to clear break tags before and after the block elements.
    blocksRegex = re.compile(r'(\s*<br\ />\s*)*\s*<(pre|p|blockquote|table)([^>]*)>(.+?)</\2>\s*(\s*<br\ />\s*)*', re.DOTALL)
    body = blocksRegex.sub(r'\n<\2\3>\4</\2>\n', body)

    # if aggressive mode = true
        # blocksRegex = re.compile(r'(\s*<br\ */*>\s*)*\s*<(pre)([^>]*)>(.+?)</\2>\s*(\s*<br\ */*>\s*)*', re.DOTALL)
        # In aggressive mode, we also check breakes inside blockquotes, meaning we can get orphaned paragraph tags.
        # body = re.sub(r'<blockquote([^>]*)>(.+?)</blockquote>', r'<blockquote\1><p>\2</p></blockquote>', body, re.DOTALL)
    # end aggressive mode

    blocks = blocksRegex.finditer(body)
    # For our replacements to work, we need to work backwards, so we reverse the iterator.
    blocksList = []
    for match in blocks:
        blocksList.insert(0, match)

    for match in blocksList:
        group4 =  match.group(4).replace(u'<br />', u'{br /}')
        body = body[:match.start(4)] + group4 + body[match.end(4):]

    # change surrounding div to a p and remove attrs Top surrounding
    # tag in all cases now should be div, to just strip the first and
    # last tags.
    # body = u'<p>' + body + u'</p>'

    # Nuke div tags surrounding a HR tag.
    body = re.sub(r'<div[^>]+>\s*<hr[^>]+>\s*</div>', r'\n<hr />\n', body)

    # So many people add formatting to their HR tags, and ePub does not allow those, we are supposed to use css.
    # This nukes the hr tag attributes.
    body = re.sub(r'\s*<hr[^>]+>\s*', r'\n<hr />\n', body)

    # Remove leading and trailing breaks from HR tags
    body = re.sub(r'\s*(<br\ \/>)*\s*<hr\ \/>\s*(<br\ \/>)*\s*', r'\n<hr />\n', body)
    # Nuking breaks leading paragraps that may be in the body. They are eventually treated as <p><br /></p>
    body = re.sub(r'\s*(<br\ \/>)+\s*<p', r'\n<p></p>\n<p', body)
    # Nuking breaks trailing paragraps that may be in the body. They are eventually treated as <p><br /></p>
    body = re.sub(r'</p>\s*(<br\ \/>)+\s*', r'</p>\n<p></p>\n', body)

    # logdebug(u'--- 2 ---')
    # logdebug(u'BODY start.: ' + body[:250])
    # logdebug(u'--')
    # logdebug(u'BODY end...: ' + body[-250:])
    # logdebug(u'BODY.......: ' + body)
    # logdebug(u'--- 2 ---')

    # Because a leading or trailing non break tag will break the following code, we have to mess around rather badly for a few lines.
    body = body.replace(u'[',u'&squareBracketStart;')
    body = body.replace(u']',u'&squareBracketEnd;')
    body = body.replace(u'<br />',u'[br /]')

    breaksRegexp = [
        re.compile(r'([^\]])(\[br\ \/\])([^\[])'),
        re.compile(r'([^\]])(\[br\ \/\]){2}([^\[])'),
        re.compile(r'([^\]])(\[br\ \/\]){3}([^\[])'),
        re.compile(r'([^\]])(\[br\ \/\]){4}([^\[])'),
        re.compile(r'([^\]])(\[br\ \/\]){5}([^\[])'),
        re.compile(r'([^\]])(\[br\ \/\]){6}([^\[])'),
        re.compile(r'([^\]])(\[br\ \/\]){7}([^\[])'),
        re.compile(r'([^\]])(\[br\ \/\]){8}([^\[])'),
        re.compile(r'(\[br\ \/\]){9,}')]

    breaksCount = [
        len(breaksRegexp[0].findall(body)),
        len(breaksRegexp[1].findall(body)),
        len(breaksRegexp[2].findall(body)),
        len(breaksRegexp[3].findall(body)),
        len(breaksRegexp[4].findall(body)),
        len(breaksRegexp[5].findall(body)),
        len(breaksRegexp[6].findall(body)),
        len(breaksRegexp[7].findall(body))]

    breaksMax = 0
    breaksMaxIndex = 0;

    for i in range(1,len(breaksCount)):
        if breaksCount[i] >= breaksMax:
            breaksMax = breaksCount[i]
            breaksMaxIndex = i

    lines = body.split(u'[br /]')
    contentLines = 0;
    contentLinesSum = 0;
    longestLineLength = 0;
    averageLineLength = 0;

    for line in lines:
        lineLen = len(line.strip())
        if lineLen > 0:
            contentLines += 1
            contentLinesSum += lineLen
            if lineLen > longestLineLength:
                longestLineLength = lineLen

    if contentLines == 0:
        contentLines = 1

    averageLineLength = contentLinesSum/contentLines

    logdebug(u'---')
    logdebug(u'Lines.............: ' + unicode(len(lines)))
    logdebug(u'contentLines......: ' + unicode(contentLines))
    logdebug(u'contentLinesSum...: ' + unicode(contentLinesSum))
    logdebug(u'longestLineLength.: ' + unicode(longestLineLength))
    logdebug(u'averageLineLength.: ' + unicode(averageLineLength))
    logdebug(u'---')
    logdebug(u'breaksMaxIndex....: ' + unicode(breaksMaxIndex))
    logdebug(u'len(breaksCount)-1: ' + unicode(len(breaksCount)-1))
    logdebug(u'breaksMax.........: ' + unicode(breaksMax))

    if breaksMaxIndex == len(breaksCount)-1 and breaksMax < 2:
        breaksMaxIndex = 0
        breaksMax = breaksCount[0]

    logdebug(u'---')
    logdebug(u'breaks 1: ' + unicode(breaksCount[0]))
    logdebug(u'breaks 2: ' + unicode(breaksCount[1]))
    logdebug(u'breaks 3: ' + unicode(breaksCount[2]))
    logdebug(u'breaks 4: ' + unicode(breaksCount[3]))
    logdebug(u'breaks 5: ' + unicode(breaksCount[4]))
    logdebug(u'breaks 6: ' + unicode(breaksCount[5]))
    logdebug(u'breaks 7: ' + unicode(breaksCount[6]))
    logdebug(u'breaks 8: ' + unicode(breaksCount[7]))
    logdebug(u'----')
    logdebug(u'max found: ' + unicode(breaksMax))
    logdebug(u'max Index: ' + unicode(breaksMaxIndex))
    logdebug(u'----')

    if breaksMaxIndex > 0 and breaksCount[0] > breaksMax and averageLineLength < 90:
        body = breaksRegexp[0].sub(r'\1 \n\3', body)

    # Find all instances of consecutive breaks less than otr equal to the max count use most often
    #  replase those tags to inverted p tag pairs, those with more connsecutive breaks are replaced them with a horisontal line
    for i in range(len(breaksCount)):
        # if i > 0 or breaksMaxIndex == 0:
        if i <= breaksMaxIndex:
            logdebug(unicode(i) + u' <= breaksMaxIndex (' + unicode(breaksMaxIndex) + u')')
            body = breaksRegexp[i].sub(r'\1</p>\n<p>\3', body)
        elif i == breaksMaxIndex+1:
            logdebug(unicode(i) + u' == breaksMaxIndex+1 (' + unicode(breaksMaxIndex+1) + u')')
            body = breaksRegexp[i].sub(r'\1</p>\n<p><br/></p>\n<p>\3', body)
        else:
            logdebug(unicode(i) + u' > breaksMaxIndex+1 (' + unicode(breaksMaxIndex+1) + u')')
            body = breaksRegexp[i].sub(r'\1</p>\n<hr />\n<p>\3', body)

    body = breaksRegexp[8].sub(r'</p>\n<hr />\n<p>', body)

    # Reverting the square brackets
    body = body.replace(u'[', u'<')
    body = body.replace(u']', u'>')
    body = body.replace(u'&squareBracketStart;', u'[')
    body = body.replace(u'&squareBracketEnd;', u']')

    body = body.replace(u'{p}', u'<p>')
    body = body.replace(u'{/p}', u'</p>')

    # If for some reason, a third break makes its way inside the paragraph, preplace that with the empty paragraph for the additional linespaing.
    body = re.sub(r'<p>\s*(<br\ \/>)+', r'<p><br /></p>\n<p>', body)

    # change empty p tags to include a br to force spacing.
    body = re.sub(r'<p>\s*</p>', r'<p><br/></p>', body)

    # Clean up hr tags, and add inverted p tag pairs
    body = re.sub(r'(<div[^>]+>)*\s*<hr\ \/>\s*(</div>)*', r'\n<hr />\n', body)

    # Clean up hr tags, and add inverted p tag pairs
    body = re.sub(r'\s*<hr\ \/>\s*', r'</p>\n<hr />\n<p>', body)

    # Because the previous regexp may cause trouble if the hr tag already had a p tag pair around it, w nee dot repair that.
    # Repeated opening p tags are condenced to one. As we added the extra leading opening p tags, we can safely assume that
    #  the last in such a chain must be the original. Lets keep its attributes if they are there.
    body = re.sub(r'\s*(<p[^>]*>\s*)+<p([^>]*)>\s*', r'\n<p\2>', body)
    # Repeated closing p tags are condenced to one
    body = re.sub(r'\s*(<\/\s*p>\s*){2,}', r'</p>\n', body)

    # superflous cleaning, remove whitespaces traling opening p tags. These does affect formatting.
    body = re.sub(r'\s*<p([^>]*)>\s*', r'\n<p\1>', body)
    # superflous cleaning, remove whitespaces leading closing p tags. These does not affect formatting.
    body = re.sub(r'\s*</p>\s*', r'</p>\n', body)

    # Remove empty tag pairs
    body = re.sub(r'\s*<(\S+)[^>]*>\s*</\1>', r'', body)

    body = body.replace(u'{br /}', u'<br />')
    body = re.sub(r'XAMP;(.+?);', r'&\1;', body)
    body = body.strip()

    # re-wrap in div tag.
    body = u'<div id="' +was_run_marker+ u'">\n' + body + u'</div>\n'
    # return body after tag_sanitizer with 'replace_br_with_p done' marker.
    ## marker included twice becaues the comment & id could each be
    ## removed by different 'clean ups'.  I hope it's less likely both
    ## will be.
    return u'<!-- ' +was_run_marker+ u' -->\n' + tag_sanitizer(body)

def is_valid_block(block):
    return unicode(block).find('<') == 0 and unicode(block).find('<!') != 0

def soup_up_div(body):
    blockTags = ['address', 'aside', 'blockquote', 'del', 'div', 'dl', 'fieldset', 'form', 'ins', 'noscript', 'ol', 'p', 'pre', 'table', 'ul']
    recurseTags = ['blockquote', 'div', 'noscript']

    tag = body[:body.index('>')+1]
    tagend = body[body.rindex('<'):]

    body = body.replace(u'<br />', u'[br /]')

    # bs4 insists on wrapping *all* new soups in <html><body> if they
    # don't already have them.  This way we have just the div.
    soup = bs.BeautifulSoup('<div id="soup_up_div">'+body+'</div>','html5lib').find('div',id="soup_up_div")

    body = u''
    lastElement = 1 # 1 = block, 2 = nested, 3 = invalid

    for i in soup.contents[0]:
        if unicode(i).strip().__len__() > 0:
            s = unicode(i)
            if  type(i) == bs.Tag:
                if  i.name in blockTags:
                    if lastElement > 1:
                        body = body.strip(r'\s*(\[br\ \/\]\s*)*\s*')
                        body += u'{/p}'

                    lastElement = 1

                    if i.name in recurseTags:
                        s = soup_up_div(s)

                    body += s.strip() + '\n'
                else:
                    if lastElement == 1:
                        body = body.strip(r'\s*(\[br\ \/\]\s*)*\s*')
                        body += u'{p}'

                    lastElement = 2
                    body += s
            elif type(i) == bs.Comment:
                #body += s
                # skip comments because '<!-- text -->' becomes just 'text'
                pass
            else:
                if lastElement == 1:
                    body = body.strip(r'\s*(\[br\ \/\]\s*)*\s*')
                    body += u'{p}'

                lastElement = 3
                body += s

    if lastElement > 1:
        body = body.strip(r'\s*(\[br\ \/\]\s*)*\s*')
        body += u'{/p}'

    body = body.replace(u'[br /]', u'<br />')

    return tag + body + tagend


def is_end_tag(tag):
    return re.match(r'</([^\ >]+)>', tag) != None

def is_comment_tag(tag):
    return re.match(r'<\!\-\-([^>]+)>', tag) != None

def is_closed_tag(tag):
    return re.match(r'<(.+?)/>', tag) != None

def tag_sanitizer(html):
    blockTags = ['address', 'blockquote', 'del', 'div', 'dl', 'fieldset', 'form', 'ins', 'noscript', 'ol', 'pre', 'table', 'ul']

    body = u''
    tags = re.findall(r'(<[^>]+>)([^<]*)', html)

    for rTag in tags:
        name = stack.get_tag_name(rTag[0])
        is_end = is_end_tag(rTag[0])
        is_closed = is_closed_tag(rTag[0]) or is_comment_tag(rTag[0])

        # is_comment = is_comment_tag(rTag[0])
        # logdebug(u'%s >  isEnd: %s >  isClosed: %s >  isComment: %s'%(name, unicode(is_end), unicode(is_closed), unicode(is_comment)))
        # logdebug(u'> %s%s\n'%(rTag[0], rTag[1]))

        if name in blockTags:
            body += rTag[0]
            body += rTag[1]
        elif name == u'p':
            if is_end:
                body += stack.spool_end()
                body += rTag[0]
                body += rTag[1]
            elif is_closed:
                body += rTag[0]
                body += rTag[1]
            else:
                body += rTag[0]
                body += stack.spool_start()
                body += rTag[1]
        else:
            if is_end:
                t = stack.get_last()
                tn = stack.get_tag_name(t)
                rTn = stack.get_tag_name(rTag[0])
                if tn == rTn:
                    body += rTag[0]
                    stack.pop()
            elif not is_closed:
                stack.push(rTag[0])
                body += rTag[0]
            else:
                body += rTag[0]

            body += rTag[1]
    stack.flush()
    return body
