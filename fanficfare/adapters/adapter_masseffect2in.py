# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team,
#           2015 FanFicFare team,
#           2015 Dmitry Kozliuk
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

import datetime
import logging
import re
import urllib2
import codecs

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions
from base_adapter import BaseSiteAdapter, makeDate


_logger = logging.getLogger(__name__)


def getClass():
    """Returns adapter class defined in this module."""
    return MassEffect2InAdapter


class ParsingError(Exception):
    """Indicates an error while parsing web page content."""
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message


class MassEffect2InAdapter(BaseSiteAdapter):
    """Provides support for masseffect2.in site as story source.
    Can be used as a template for sites build upon Ucoz.com engine.
    Specializations:
        1) Russian content (date format, genre names, etc.);
        2) original `R.A.T.I.N.G.' rating scale, used by masseffect2.in
           and some affiliated sites."""

    WORD_PATTERN = re.compile(u'\w+', re.UNICODE)

    DOCUMENT_ID_PATTERN = re.compile(u'\d+-\d+-\d+-\d+')

    # Various `et cetera' and `et al' forms in Russian texts.
    # Intended to be used with whole strings!
    ETC_PATTERN = re.compile(
        u'''[и&]\s(?:
              (?:т\.?\s?[пд]\.?)|
              (?:др(?:угие|\.)?)|
              (?:пр(?:очие|\.)?)|
              # Note: identically looking letters `K' and `o'
              # below are from Latin and Cyrillic alphabets.
              (?:ко(?:мпания)?|[KК][oо°])
            )$
        ''',
        re.IGNORECASE + re.UNICODE + re.VERBOSE)

    CHAPTER_NUMBER_PATTERN = re.compile(
        u'''[\.:\s]*
            (?:глава)?  # `Chapter' in Russian.
            \s
            (?P<chapterIndex>\d+)
            (?:
              (?:
                # For `X.Y' and `X-Y' numbering styles:
                [\-\.]|
                # For `Chapter X (part Y)' and similar numbering styles:
                [\.,]?\s
                (?P<brace>\()?
                (?:часть)?      # `Part' in Russian.
                \s
              )
              (?P<partIndex>\d+)
              (?(brace)\))
            )?
            [\.:\s]*
         ''',
        re.IGNORECASE + re.UNICODE + re.VERBOSE)

    PROLOGUE_EPILOGUE_PATTERN = re.compile(
        u'''[\.:\s]*         # Optional separators.
            (пролог|эпилог)  # `Prologue' or `epilogue' in Russian.
            [\.:\s]*         # Optional separators.
         ''',
        re.IGNORECASE + re.UNICODE + re.VERBOSE)

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.decode = ["utf8"]
        self.dateformat = "%d.%m.%Y"

        self.story.setMetadata('siteabbrev', 'me2in')

        self.story.setMetadata('storyId', self._extractDocumentId(self.url))

        self._setURL(self._makeUrl(self.story.getMetadata('storyId')))

        self._transient_metadata = {}

        # Memory cache of document HTML parsing results.  Increases performance
        # drastically, because all downloaded pages are parsed at least twice.
        # FIXME: Can be simplified when BS is updated to 4.4 with cloning.
        self._parsing_cache = {}

    @classmethod
    def _makeUrl(cls, chapterId):
        """Makes a chapter URL given a chapter ID."""
        return 'http://%s/publ/%s' % (cls.getSiteDomain(), chapterId)

    # Must be @staticmethod, not @classmethod!
    @staticmethod
    def getSiteDomain():
        return 'www.masseffect2.in'

    @classmethod
    def getSiteExampleURLs(cls):
        return u' '.join([cls._makeUrl('19-1-0-1234'),
                          cls._makeUrl('24-1-0-4321')])

    def getSiteURLPattern(self):
        return re.escape(self._makeUrl('')) + self.DOCUMENT_ID_PATTERN.pattern

    def use_pagecache(self):
        """Allows use of downloaded page cache.  It is essential for this
        adapter, because the site does not offers chapter URL list, and many
        pages have to be fetched and parsed repeatedly."""
        return True

    def extractChapterUrlsAndMetadata(self):
        """Extracts chapter URLs and story metadata.  Actually downloads all
        chapters, which is not exactly right, but necessary due to technical
        limitations of the site."""

        def followLinks(document, selector):
            """Downloads chapters one by one by locating and following links
            specified by a selector.  Returns chapters' URLs in order they
            were found."""
            block = document\
                .find('td', {'class': 'eDetails1'})\
                .find('div', selector)
            if not block:
                return
            link = block.find('a')
            if not link:
                return
            chapterId = self._extractDocumentId(link['href'])
            url = self._makeUrl(chapterId)
            try:
                chapter = self._loadDocument(url)
            except urllib2.HTTPError, error:
                if error.code == 404:
                    raise exceptions.FailedToDownload(
                        u'Error downloading chapter: %s!' % url)
                raise
            yield url
            for url in followLinks(chapter, selector):
                yield url

        def followPreviousLinks(document):
            """Downloads chapters following `Previous chapter' links.
            Returns a list of chapters' URLs."""
            urls = list(followLinks(document, {'class': 'fl tal'}))
            return list(reversed(urls))

        def followNextLinks(document):
            """Downloads chapters following `Next chapter' links.
            Returns a list of chapters' URLs."""
            return list(followLinks(document, {'class': 'tar fr'}))

        try:
            document = self._loadDocument(self.url)
        except urllib2.HTTPError, error:
            if error.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            raise
        # There is no convenient mechanism to obtain URLs of all chapters
        # other than navigating to previous and next chapters using links
        # located on each chapter page.
        chapters = \
            followPreviousLinks(document) + \
            [self.url] + \
            followNextLinks(document)

        # Transient metadata is updated when parsing each chapter,
        # then converted and saved to story metadata.
        self._transient_metadata = {
            # We only have one date for each chapter and assume the oldest one
            # to be publication date and the most recent one to be update date.
            'datePublished': datetime.datetime.max,
            'dateUpdated': datetime.datetime.min,

            'numWords': 0,

            # We aim at counting chapters, not chapter parts.
            'numChapters': 0
        }

        for url in chapters:
            chapter = self._loadDocument(url)
            _logger.debug(u"Parsing chapter `%s'", url)
            self._parseChapterMetadata(url, chapter)

        # Attributes are handled separately due to format conversions.
        self.story.setMetadata(
            'datePublished', self._transient_metadata['datePublished'])
        self.story.setMetadata(
            'dateUpdated', self._transient_metadata['dateUpdated'])
        self.story.setMetadata(
            'numWords', str(self._transient_metadata['numWords']))
        self.story.setMetadata(
            'numChapters', self._transient_metadata['numChapters'])

    def getChapterText(self, url):
        """Grabs the text for an individual chapter."""
        element = self._getChapterTextElement(url)
        return self.utf8FromSoup(url, element)

    def _parseChapterMetadata(self, url, document):
        try:
            self._parseTitle(url, document)
            infoBar = document.find('td', {'class': 'eDetails2'})
            if not infoBar:
                raise ParsingError(u'No informational bar found.')
            if not self.story.getMetadata('authorId'):
                self._parseAuthor(infoBar)
            self._parseDates(infoBar)
            self._parseTextForWordCount(url)
            self._parseAttributes(document)
        except ParsingError, error:
            raise exceptions.FailedToDownload(
                u"Error parsing `%s'.  %s" % (url, error.message))

    def _parseAttributes(self, document):
        try:
            elements = document \
                .find('div', {'class': 'comm-div'}) \
                .findNextSibling('div', {'class': 'cb'}) \
                .nextGenerator()
            attributesText = u''
            for element in elements:
                if not element:
                    _logger.warning(u'Attribute block not terminated!')
                    break
                if isinstance(element, bs.Tag):
                    # Although deprecated, `has_key()' is required here.
                    if element.name == 'div' and \
                            element.has_key('class') and \
                            element['class'] == 'cb':
                        break
                    elif element.name == 'img':
                        self._parseRatingFromImage(element)
                else:
                    attributesText += stripHTML(element)
        except AttributeError or TypeError:
            raise ParsingError(u'Failed to locate and collect attributes.')

        for record in re.split(u';|\.', attributesText):
            parts = record.split(u':', 1)
            if len(parts) < 2:
                continue
            key = parts[0].strip().lower()
            value = parts[1].strip().strip(u'.')
            self._parseAttribute(key, value)

    def _parseRatingFromImage(self, element):
        """Given an image element, tries to parse story rating from it."""
        # FIXME: This should probably be made adjustable via settings.
        ratings = {
            'E': u'Exempt (18+)',
            'R': u'Restricted (16+)',
            'A': u'Иная история',
            'T': u'To every',
            'I': u'Art house',
            'Nn': u'Новый мир',
            'G': u'О, господи!',
        }
        ratings['IN'] = ratings['A']

        # Although deprecated, `has_key()' is required here.
        if not element.has_key('src'):
            return
        source = element['src']
        if 'REITiNG' not in source:
            return
        match = re.search(u'/(?P<rating>[ERATINnG]+)\.png$', source)
        if not match:
            return
        symbol = match.group('rating')
        if symbol == 'IN':
            symbol = 'A'
        if symbol in ratings:
            rating = ratings[symbol]
            self.story.setMetadata('rating', rating)
            if symbol in ('R', 'E'):
                self.is_adult = True

    def _parseAttribute(self, key, value):
        """Parses a single known attribute value for chapter metadata."""

        def refineCharacter(name):
            """Refines character name from stop-words and distortions."""
            strippedName = name.strip()
            nameOnly = re.sub(self.ETC_PATTERN, u'', strippedName)
            # TODO: extract canonical name (even ME-specific?).
            canonicalName = nameOnly
            return canonicalName

        if key == u'жанр':
            definitions = value.split(u',')
            if len(definitions) > 4:
                _logger.warning(u'Possibly incorrect genre detection!')
            for definition in definitions:
                genres = definition.split(u'/')
                self.story.extendList('genre', genres)
        elif key == u'статус':
            status = 'In-Progress' if value == u'в процессе' else 'Completed'
            self.story.setMetadata('status', status)
        elif key == u'персонажи':
            characters = [refineCharacter(name) for name in value.split(u',')]
            self.story.extendList('characters', characters)
        else:
            _logger.debug(u"Unrecognized attribute `%s'.", key)

    def _parseTextForWordCount(self, url):
        element = self._getChapterTextElement(url)
        text = stripHTML(element)
        count = len(re.findall(self.WORD_PATTERN, text))
        self._transient_metadata['numWords'] += count
        pass

    def _parseDates(self, infoBar):
        try:
            dateText = infoBar \
                .find('i', {'class': 'icon-eye'}) \
                .findPreviousSibling(text=True) \
                .strip(u'| \n')
        except AttributeError:
            raise ParsingError(u'Failed to locate date.')
        date = makeDate(dateText, self.dateformat)
        if date > self._transient_metadata['dateUpdated']:
            self._transient_metadata['dateUpdated'] = date
        if date < self._transient_metadata['datePublished']:
            self._transient_metadata['datePublished'] = date

    def _parseAuthor(self, strip):
        try:
            authorLink = strip \
                .find('i', {'class': 'icon-user'}) \
                .findNextSibling('a')
        except AttributeError:
            raise ParsingError(u'Failed to locate author link.')
        match = re.search(u'(8-\d+)', authorLink['onclick'])
        if not match:
            raise ParsingError(u'Failed to extract author ID.')
        authorId = match.group(0)
        authorUrl = 'http://%s/index/%s' % (self.getSiteDomain(), authorId)
        authorName = stripHTML(authorLink.text)
        self.story.setMetadata('authorId', authorId)
        self.story.setMetadata('authorUrl', authorUrl)
        self.story.setMetadata('author', authorName)

    def _parseTitle(self, url, document):
        try:
            fullTitle = stripHTML(
                document.find('div', {'class': 'eTitle'}).string)
        except AttributeError:
            raise ParsingError(u'Failed to locate title.')
        parsedHeading = self._parseHeading(fullTitle)
        if not self.story.getMetadata('title'):
            self.story.setMetadata('title', parsedHeading['storyTitle'])
        if 'chapterIndex' in parsedHeading:
            self._transient_metadata['numChapters'] = max(
                self._transient_metadata['numChapters'],
                parsedHeading['chapterIndex'])
        else:
            self._transient_metadata['numChapters'] += 1
        self.chapterUrls.append((parsedHeading['chapterTitle'], url))

    def _parseHeading(self, fullTitle):
        """Extracts meaningful parts from full chapter heading with.
        Returns a dictionary containing `storyTitle', `chapterTitle'
        (including numbering if allowed by settings, may be the same as
        `storyTitle' for short stories), `chapterIndex' (optional, may be
        zero), and `partIndex' (optional, chapter part, may be zero).
        When no dedicated chapter title is present, generates one based on
        chapter and part indices.  Correctly handles `prologue' and `epilogue'
        cases."""
        match = re.search(self.CHAPTER_NUMBER_PATTERN, fullTitle)
        if match:
            chapterIndex = int(match.group('chapterIndex'))
            # There are cases with zero chapter or part number (e. g.:
            # numbered prologue, not to be confused with just `Prologue').
            if match.group('partIndex'):
                partIndex = int(match.group('partIndex'))
            else:
                partIndex = None
            chapterTitle = fullTitle[match.end():].strip()
            if chapterTitle:
                if self.getConfig('strip_chapter_numbers', False) \
                        and not self.getConfig('add_chapter_numbers', False):
                    if partIndex is not None:
                        title = u'%d.%d %s' % \
                                (chapterIndex, partIndex, chapterTitle)
                    else:
                        title = u'%d. %s' % (chapterIndex, chapterTitle)
                else:
                    title = chapterTitle
            else:
                title = u'Глава %d' % chapterIndex
                if partIndex:
                    title += u' (часть %d)' % partIndex

            # For seldom found cases like `Story: prologue and chapter 1'.
            storyTitle = fullTitle[:match.start()]
            match = re.search(self.PROLOGUE_EPILOGUE_PATTERN, storyTitle)
            if match:
                matches = list(
                    re.finditer(u'[:\.]', storyTitle))
                if matches:
                    realStoryTitleEnd = matches[-1].start()
                    if realStoryTitleEnd >= 0:
                        storyTitle = storyTitle[:realStoryTitleEnd]
                    else:
                        _logger.warning(
                            u"Title contains `%s', suspected to be part of "
                            u"numbering, but no period (`.') before it.  "
                            u"Full title is preserved." % storyTitle)

            result = {
                'storyTitle': storyTitle,
                'chapterTitle': title,
                'chapterIndex': chapterIndex
            }
            if partIndex is not None:
                result['partIndex'] = partIndex
            return result

        match = re.search(self.PROLOGUE_EPILOGUE_PATTERN, fullTitle)
        if match:
            storyTitle = fullTitle[:match.start()]
            chapterTitle = fullTitle[match.end():].strip()
            matchedText = fullTitle[match.start():match.end()]
            if chapterTitle:
                title = u'%s. %s' % (matchedText, chapterTitle)
            else:
                title = matchedText
            return {
                'storyTitle': storyTitle,
                'chapterTitle': title
            }

        return {
            'storyTitle': fullTitle,
            'chapterTitle': fullTitle
        }

    def _loadDocument(self, url):
        """Fetches URL content and returns its element tree
        with parsing settings tuned for MassEffect2.in."""
        documentId = self._extractDocumentId(url)
        if documentId in self._parsing_cache:
            _logger.debug(u"Memory cache HIT for parsed `%s'", url)
            return self._parsing_cache[documentId]['document']
        else:
            _logger.debug(u"Memory cache MISS for parsed `%s'", url)
            document = bs.BeautifulStoneSoup(
                self._fetchUrl(url), selfClosingTags=('br', 'hr', 'img'))
            self._parsing_cache[documentId] = {'document': document}
            return document

    def _fetchUrl(self, url,
                  parameters=None,
                  usecache=True,
                  extrasleep=None):
        """Fetches URL contents, see BaseSiteAdapter for details.
        Overridden to support on-disk cache when debugging Calibre."""
        from calibre.constants import DEBUG
        if DEBUG:
            import os
            documentId = self._extractDocumentId(url)
            path = u'./cache/%s' % documentId
            if os.path.isfile(path) and os.access(path, os.R_OK):
                _logger.debug(u"On-disk cache HIT for `%s'.", url)
                with codecs.open(path, encoding='utf-8') as input:
                    return input.read()
            else:
                _logger.debug(u"On-disk cache MISS for `%s'.", url)

        content = BaseSiteAdapter._fetchUrl(
            self, url, parameters, usecache, extrasleep)

        if DEBUG:
            import os
            if os.path.isdir(os.path.dirname(path)):
                _logger.debug(u"Caching `%s' content on disk.", url)
                with codecs.open(path, mode='w', encoding='utf-8') as output:
                    output.write(content)

        return content

    def _extractDocumentId(self, url):
        """Extracts document ID from MassEffect2.in URL."""
        match = re.search(self.DOCUMENT_ID_PATTERN, url)
        if not match:
            raise ValueError(u"Failed to extract document ID from `'" % url)
        documentId = url[match.start():match.end()]
        return documentId

    def _getChapterTextElement(self, url):
        """Fetches URL content and extracts an element containing text body.
        Shall be used instead of `__collectTextElements'."""
        documentId = self._extractDocumentId(url)
        document = self._loadDocument(url)
        cache = self._parsing_cache[documentId]
        if 'body' in cache:
            return cache['body']
        else:
            body = self.__collectTextElements(document)
            cache['body'] = body
            return body

    def __collectTextElements(self, document):
        """Returns all elements containing parts of chapter text (which may be
        <p>aragraphs, <div>isions or plain text nodes) under a single root."""
        starter = document.find('div', {'id': u'article'})
        if starter is None:
            # FIXME: This will occur if the method is called more than once.
            # The reason is elements appended to `root' are removed from
            # the document. BS 4.4 implements cloning via `copy.copy()',
            # but supporting it for earlier versions is error-prone
            # (due to relying on BS internals).
            raise ParsingError(u'Failed to locate text.')
        collection = [starter]
        for element in starter.nextSiblingGenerator():
            if element is None:
                break
            if isinstance(element, bs.Tag) and element.name == 'tr':
                break
            collection.append(element)
        root = bs.Tag(document, 'td')
        for element in collection:
            root.append(element)
        return root
