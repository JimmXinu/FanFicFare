# -*- coding: utf-8 -*-

# Copyright 2013 Fanficdownloader team
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

import logging
logger = logging.getLogger(__name__)
import re

from . import exceptions as exceptions

def replace_br_with_p(body):

    # Ascii character (and Unicode as well) xA0 is a non-breaking space, ascii code 160.
    # However, Python Regex does not recognize it as a whitespace, so we'll be changing it to a reagular space.
    body = body.replace(u'\xa0', u' ')

    if body.find('>') == -1 or body.rfind("<") == -1:
        return body

    # change surrounding div to a p and remove attrs Top surrounding
    # tag in all cases now should be div, to just strip the first and
    # last tags.
    body = u'<p>'+body[body.index('>')+1:body.rindex("<")]+u'</p>'

    # Nuke div tags surrounding a HR tag.
    body = re.sub(r'<div[^>]+>\s*<hr[^>]+>\s*</div>', r'\n<hr />\n', body)

    # So many people add formatting to their HR tags, and ePub does not allow those, we are supposed to use css.
    # This nukes the hr tag attributes.
    body = re.sub(r'\s*<hr[^>]+>\s*', r'\n<hr />\n', body)

    # Need to look at BeautifulSoup to see if it'll even return breaks that aren't properly formatted (<br />).
    body = re.sub(r'\s*<br[^>]*>\s*', r'<br />', body)

    # Remove leading and trailing breaks from HR tags
    body = re.sub(r'\s*(<br\ \/>)*\s*<hr\ \/>\s*(<br\ \/>)*\s*', r'\n<hr />\n', body)
    # Nuking breaks leading paragraps that may be in the body. They are eventually treated as <p><br /></p>
    body = re.sub(r'\s*(<br\ \/>)+\s*<p', r'\n<p></p>\n<p', body)
    # Nuking breaks trailing paragraps that may be in the body. They are eventually treated as <p><br /></p>
    body = re.sub(r'</p>\s*(<br\ \/>)+\s*', r'</p>\n<p></p>\n', body)

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

    for i in range(len(breaksCount)):
        if breaksCount[i] > breaksMax:
            breaksMax = breaksCount[i]
            breaksMaxIndex = i

    # Find all instances of consecutive breaks less than otr equal to the max count use most often
    #  replase those tags to inverted p tag pairs, those with more connsecutive breaks are replaced them with a horisontal line
    for i in range(len(breaksCount)):
        if i <= breaksMaxIndex:
            body = breaksRegexp[i].sub(r'\1</p>\n<p>\3', body)
        else:
            body = breaksRegexp[i].sub(r'\1</p>\n<hr />\n<p>\3', body)

    body = breaksRegexp[8].sub(r'</p>\n<hr />\n<p>', body)

    # Reverting the square brackets
    body = body.replace(u'[', u'<')
    body = body.replace(u']', u'>')
    body = body.replace(u'&squareBracketStart;', u'[')
    body = body.replace(u'&squareBracketEnd;', u']')

    # If for some reason, a third break makes its way inside the paragraph, preplace that with the empty paragraph for the additional linespaing.
    body = re.sub(r'<p>\s*(<br\ \/>)+', r'<p><br /></p>\n<p>', body)

    # change empty p tags to include a br to force spacing.
    body = re.sub(r'<p>\s*</p>', r'<p><br/></p>', body)

    # Clean up hr tags, and add inverted p tag pairs
    body = re.sub(r'\s*<hr\ \/>\s*', r'</p>\n<hr />\n<p>', body)

    # Because the previous regexp may cause trouble if the hr tag already had a p tag pair around it, w nee dot repair that.
    # Repeated opening p tags are condenced to one. As we added the extra leading opening p tags, we can safely assume that
    #  the last in such a chain must be the original. Lets keep its attributes if they are there.
    body = re.sub(r'\s*(<p[^>]*>\s*)+<p([^>]*)>\s*', r'\n<p\2>', body)
    # Repeated closing p tags are condenced to one
    body = re.sub(r'\s*(<\/\s*p>\s*){2,}', r'</p>\n', body)

    # superflous cleaning, remove whitespaces traling opening p tags. These does affect formatting.
    body = re.sub(r'<p([^>]*)>\s*', r'<p\1>', body)
    # superflous cleaning, remove whitespaces leading closing p tags. These does not affect formatting.
    body = re.sub(r'\s*</p>', r'</p>', body)

    # Remove empty tag pairs
    body = re.sub(r'\s*<(\S+)[^>]*>\s*</\1>', r'', body)

    # re-wrap in div tag.
    body = u'<div>\n' + body + u'\n</div>'

    return body 

