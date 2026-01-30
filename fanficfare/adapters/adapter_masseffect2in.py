# -*- coding: utf-8 -*-

# Copyright 2019 FanFicFare team
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

from __future__ import absolute_import, unicode_literals
import bs4
import datetime
import logging
import re
from itertools import takewhile

from ..htmlcleanup import removeEntities, stripHTML
from .. import exceptions as exceptions
# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves import zip as izip

from .base_adapter import BaseSiteAdapter, makeDate


logger = logging.getLogger(__name__)


def getClass():
    """Returns adapter class defined in this module."""
    return MassEffect2InAdapter


class ParsingError(Exception):
    """Indicates an error while parsing web page content."""
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message

    def __str__(self):
        return self.message


class MassEffect2InAdapter(BaseSiteAdapter):
    """
    Provides support for MassEffect2.in site as story source.
    Can be used as a template for sites build upon Ucoz.com engine (until no base class extracted).
    Specializations:
        1) Russian content (date format, genre names, etc.);
        2) original `E.R.A.T.I.N.G.' rating scale, used by masseffect2.in
           and some affiliated sites, denoted with images;
        3) editor signatures an an option to remove them.
    """

    WORD_PATTERN = re.compile(r'\w+', re.UNICODE)
    DOCUMENT_ID_PATTERN = re.compile(r'\d+-\d+-\d+-\d+')
    SITE_LANGUAGE = u'Russian'

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.story.setMetadata('siteabbrev', 'me2in')
        self.story.setMetadata('storyId', self._getDocumentId(self.url))

        self._setURL(self._makeDocumentUrl(self.story.getMetadata('storyId')))

        self._chapters = {}
        self._parsingConfiguration = None

    # Must be @staticmethod, not @classmethod!
    @staticmethod
    def getSiteDomain():
        return 'www.masseffect2.in'

    @classmethod
    def getSiteExampleURLs(cls):
        return u' '.join([cls._makeDocumentUrl('19-1-0-1234'),
                          cls._makeDocumentUrl('24-1-0-4321')])

    def getSiteURLPattern(self):
        return r'https?://(?:www\.)?masseffect2.in/publ/' + self.DOCUMENT_ID_PATTERN.pattern

    def extractChapterUrlsAndMetadata(self):
        """Extracts chapter URLs and story metadata.  Actually downloads all
        chapters, which is not exactly right, but necessary due to technical
        limitations of the site."""

        def followChapters(starting, forward=True):
            if forward:
                url = starting.getNextChapterUrl()
            else:
                url = starting.getPreviousChapterUrl()
            if url:
                url = self._makeDocumentUrl(self._getDocumentId(url))
                following = self._makeChapter(url)
                # Do not follow links to related, but different stories (prequels or sequels).
                try:
                    if not following.isFromStory(starting.getHeading()):
                        return
                except Exception as e:
                    logger.info("Failure to parse page, stop stepping through pages: %s"%e)
                    return
                if forward:
                    yield following
                for chapter in followChapters(following, forward):
                    yield chapter
                if not forward:
                    yield following

        startingChapter = self._makeChapter(self.url)

        # We only have one date for each chapter and assume the oldest one
        # to be publication date and the most recent one to be update date.
        datePublished = datetime.datetime.max
        dateUpdated = datetime.datetime.min
        wordCount = 0
        storyInProgress = False

        chapters = \
            list(followChapters(startingChapter, forward=False)) + \
            [startingChapter] + \
            list(followChapters(startingChapter, forward=True))

        headings = [chapter.getHeading() for chapter in chapters]
        largestCommonPrefix = _getLargestCommonPrefix(*headings)
        prefixLength = len(largestCommonPrefix)
        storyTitleEnd, chapterTitleStart = prefixLength, prefixLength
        match = re.search(r'[:.\s]*(?P<chapter>глава\s+)?$', largestCommonPrefix, re.IGNORECASE | re.UNICODE)
        if match:
            storyTitleEnd -= len(match.group())
            label = match.group('chapter')
            if label:
                chapterTitleStart -= len(label)
        storyTitle = largestCommonPrefix[:storyTitleEnd]
        self.story.setMetadata('title', storyTitle)

        garbagePattern = re.compile(r'(?P<start>^)?[:.\s]*(?(start)|$)', re.UNICODE)

        for chapter in chapters:
            url = chapter.getUrl()
            self._chapters[url] = chapter
            logger.debug(u"Processing chapter `%s'.", url)

            try:
                authorName = chapter.getAuthorName()
                if authorName:
                    self.story.extendList('author', [authorName])
                    authorId = chapter.getAuthorId()
                    if authorId:
                        authorUrl = 'https://%s/index/%s' % (self.getSiteDomain(), authorId)
                    else:
                        authorId = u''
                        authorUrl = u''
                    self.story.extendList('authorId', [authorId])
                    self.story.extendList('authorUrl', [authorUrl])

                if not self.story.getMetadataRaw('rating'):
                    ratingTitle = chapter.getRatingTitle()
                    if ratingTitle:
                        self.story.setMetadata('rating', ratingTitle)

                if not self.story.getMetadata('description'):
                    summary = chapter.getSummary()
                    if summary:
                        self.story.setMetadata('description', summary)

                datePublished = min(datePublished, chapter.getDate())
                dateUpdated = max(dateUpdated, chapter.getDate())

                self.story.extendList('genre', chapter.getGenres())
                self.story.extendList('characters', chapter.getCharacters())
                self.story.extendList('ships', chapter.getPairings())

                wordCount += self._getWordCount(chapter.getTextElement())

                # Chapter status usually represents the story status, so we want the last chapter status.
                # Some chapters may have no status attribute.
                chapterInProgress = chapter.isInProgress()
                if chapterInProgress is not None:
                    storyInProgress = chapterInProgress

                # If any chapter is adult, consider the whole story adult.
                if chapter.isAdult():
                    self.story.setMetadata('is_adult', True)
                    warning = chapter.getWarning()
                    if warning:
                        self.story.extendList('warnings', [warning])

                chapterTitle = re.sub(garbagePattern, u'', chapter.getHeading()[chapterTitleStart:])
                self.add_chapter(chapterTitle, url)
            except ParsingError as error:
                raise exceptions.FailedToDownload(u"Failed to download chapter `%s': %s" % (url, error))

        # Some metadata are handled separately due to format conversions.
        self.story.setMetadata('status', 'In-Progress' if storyInProgress else 'Completed')
        self.story.setMetadata('datePublished', datePublished)
        self.story.setMetadata('dateUpdated', dateUpdated)
        self.story.setMetadata('numWords', unicode(wordCount))

        # Site-specific metadata.
        self.story.setMetadata('language', self.SITE_LANGUAGE)

    def getChapterText(self, url):
        """Grabs the text for an individual chapter."""
        if url not in self._chapters:
            raise exceptions.FailedToDownload(u"No chapter `%s' present!" % url)
        chapter = self._chapters[url]
        return self.utf8FromSoup(url, chapter.getTextElement())

    def _makeChapter(self, url):
        """Creates a chapter object given a URL."""
        document = self.make_soup(self.get_request(url))
        chapter = Chapter(self._getParsingConfiguration(), url, document)
        return chapter

    def _getWordCount(self, element):
        """Returns word count in plain text extracted from chapter body."""
        text = stripHTML(element)
        count = len(re.findall(self.WORD_PATTERN, text))
        return count

    def _getParsingConfiguration(self):
        if not self._parsingConfiguration:
            self._parsingConfiguration = {}

            adultRatings = self.getConfigList('adult_ratings')
            if not adultRatings:
                raise exceptions.PersonalIniFailed(
                    u"Missing `adult_ratings' setting", u"MassEffect2.in", u"?")
            adultRatings = set(adultRatings)
            self._parsingConfiguration['adultRatings'] = adultRatings

            ratingTitleDescriptions = self.getConfigList('rating_titles')
            if ratingTitleDescriptions:
                ratingTitles = {}
                for ratingDescription in ratingTitleDescriptions:
                    parts = ratingDescription.split(u'=')
                    if len(parts) < 2:
                        logger.warning(
                            u"Invalid `rating_titles' setting, missing `=' in `%s'."
                            % ratingDescription)
                        continue
                    labels = parts[:-1]
                    title = parts[-1]
                    for label in labels:
                        ratingTitles[label] = title
                        # Duplicate label aliasing in adult rating set.
                        if label in adultRatings:
                            adultRatings.add(*labels)
                self._parsingConfiguration['adultRatings'] = list(adultRatings)
                self._parsingConfiguration['ratingTitles'] = ratingTitles
            else:
                raise exceptions.PersonalIniFailed(
                    u"Missing `rating_titles' setting", u"MassEffect2.in", u"?")

            self._parsingConfiguration['excludeEditorSignature'] = \
                self.getConfig('exclude_editor_signature', False)

        return self._parsingConfiguration

    def _getDocumentId(self, url):
        """Extract document ID from MassEffect2.in URL."""
        match = re.search(self.DOCUMENT_ID_PATTERN, url)
        if not match:
            raise ValueError(u"Failed to extract document ID from `'" % url)
        documentId = url[match.start():match.end()]
        return documentId

    @classmethod
    def _makeDocumentUrl(cls, documentId):
        """Make a chapter URL given a document ID."""
        return 'https://%s/publ/%s' % (cls.getSiteDomain(), documentId)


class Chapter(object):
    """Represents a lazily-parsed chapter of a story."""
    def __init__(self, configuration, url, document):
        self._configuration = configuration
        self._url = url
        self._document = document
        # Lazy-loaded:
        self._heading = None
        self._date = None
        self._author = None
        self._attributes = None
        self._textElement = None
        self._infoBar = None

    def getHeading(self):
        return self._extractHeading()

    def getSummary(self):
        attributes = self.__getAttributes()
        if 'summary' in attributes:
            return attributes['summary']

    def getAuthorId(self):
        author = self._getAuthor()
        if author:
            return author['id']

    def getAuthorName(self):
        author = self._getAuthor()
        if author:
            return author['name']

    def getDate(self):
        return self.__getDate()

    def getRatingTitle(self):
        attributes = self.__getAttributes()
        if 'rating' in attributes:
            return attributes['rating']['title']

    def isAdult(self):
        attributes = self.__getAttributes()
        if 'rating' in attributes and attributes['rating']['isAdult']:
            return True
        if 'warning' in attributes:
            return True
        return False

    def getWarning(self):
        attributes = self.__getAttributes()
        if 'warning' in attributes:
            return attributes['warning']

    def getCharacters(self):
        return self._getListAttribute('characters')

    def getPairings(self):
        return self._getListAttribute('pairings')

    def getGenres(self):
        return self._getListAttribute('genres')

    def isInProgress(self):
        attributes = self.__getAttributes()
        if 'isInProgress' in attributes:
            return attributes['isInProgress']

    def getUrl(self):
        return self._url

    def getTextElement(self):
        return self._getTextElement()

    def getPreviousChapterUrl(self):
        link = self._document.find('a', {'title': u'Предыдущая глава'})
        if link:
            return link['href']

    def getNextChapterUrl(self):
        link = self._document.find('a', {'title': u'Следующая глава'})
        if link:
            return link['href']

    def isFromStory(self, storyTitle, prefixThreshold=-1):
        """Check if this chapter is from a story different from the given one.
        Prefix threshold specifies how long common story title prefix shall be
        for chapters from one story: negative value means implementation-defined
        optimum, zero inhibits the check, and positive value adjusts threshold."""

        def getFirstWord(string):
            match = re.search(r'^\s*\w+', string, re.UNICODE)
            return string[match.start():match.end()]

        thisStoryTitle = self.getHeading()
        if prefixThreshold != 0:
            if prefixThreshold < 0:
                prefixThreshold = min(
                    len(getFirstWord(storyTitle)), len(getFirstWord(thisStoryTitle)))
            else:
                prefixThreshold = min(
                    prefixThreshold, len(storyTitle), len(thisStoryTitle))
            result = len(_getLargestCommonPrefix(storyTitle, thisStoryTitle)) >= prefixThreshold
            return result
        else:
            return storyTitle != thisStoryTitle

    def _getListAttribute(self, name):
        """Return an attribute value as a list or an empty list if the attribute is absent."""
        attributes = self.__getAttributes()
        if name in attributes:
            return attributes[name]
        return []

    def _extractHeading(self):
        """Extract header text from the document."""
        return stripHTML(self._document.find('h1', {'itemprop': 'headline'}).string)

    def __getHeading(self):
        """Lazily parse and return heading."""
        if not self._heading:
            self._heading = self._extractHeading()
        return self._heading

    def _getAuthor(self):
        """Lazily parse and return author's information."""
        if not self._author:
            self._author = self._parseAuthor()
        return self._author

    def _parseAuthor(self):
        """Locate and parse chapter author's information to a dictionary with author's `id' and `name'."""
        try:
            authorLink = self._document \
                .find('span', {'class': 'glyphicon-user'}) \
                .findNextSibling('a')
        except AttributeError:
            raise ParsingError(u'Failed to locate author link.')
        match = re.search(r'(8-\d+)', authorLink['onclick'])
        if not match:
            raise ParsingError(u'Failed to extract author ID.')
        authorId = match.group(0)
        authorName = stripHTML(authorLink.text)
        return {
            'id': authorId,
            'name': authorName
        }

    def __getDate(self):
        """Lazily parse chapter date."""
        if not self._date:
            self._date = self._parseDate()
        return self._date

    def _parseDate(self):
        """Locate and parse chapter date."""
        try:
            dateText = self._document.find('time', {'itemprop': 'dateCreated'}).text
            dateText = dateText.replace(u'\n', u'')
            dateText = dateText.strip()
        except AttributeError:
            raise ParsingError(u'Failed to locate date.')

        # The site uses Europe/Moscow (MSK, UTC+0300) server time.
        def todayInMoscow():
            now = datetime.datetime.now() + datetime.timedelta(hours=3)
            today = datetime.datetime(now.year, now.month, now.day)
            return today

        def parseDateText(text):
            if text == u'Вчера':
                return todayInMoscow() - datetime.timedelta(days=1)
            elif text == u'Сегодня':
                return todayInMoscow()
            else:
                return makeDate(text, '%d.%m.%Y, %H:%M')

        date = parseDateText(dateText)
        return date

    def _getInfoBarElement(self):
        """Locate informational bar element, containing chapter date and author, on the page."""
        if not self._infoBar:
            self._infoBar = self._document.find('td', {'class': 'eDetails2'})
            if not self._infoBar:
                raise ParsingError(u'No informational bar found.')
        return self._infoBar

    def __getAttributes(self):
        """Lazily parse attributes."""
        if not self._attributes:
            self._attributes = self._parseAttributes()
        return self._attributes

    def _parseAttributes(self):
        """Parse chapter attribute block and return it as a dictionary with standard entries."""

        attributes = {}
        attributesText = u''
        try:
            starter = self._document.find('div', {'class': 'gad'})
            for item in starter.nextSiblingGenerator():
                if isinstance(item, bs4.Tag) and (item.name in ['div', 'p']):
                    starter = item
                    break
            bound = starter.findNextSibling('div', {'class': 'clearfix'})

            def processElement(element):
                """Return textual representation an *inline* element of chapter attribute block."""
                result = u''
                if isinstance(element, bs4.Tag):
                    if element.name == 'br':
                        result += u"\n"
                    elif element.name == 's':
                        result += u"<s>%s</s>" % stripHTML(element)
                    else:
                        result += stripHTML(element)
                else:
                    result += removeEntities(element)
                return result

            elements = starter.nextGenerator()
            for element in elements:
                if isinstance(element, bs4.Tag):
                    if element == bound:
                        break
                    else:
                        if element.name in ('div', 'p'):
                            attributesText += u"\n"
                            for child in element.childGenerator():
                                attributesText += processElement(child)
                            continue
                attributesText += processElement(element)

            elements = starter.nextGenerator()
            for element in elements:
                if isinstance(element, bs4.Tag):
                    if element == bound:
                        break
                    elif element.name == 'img':
                        rating = self._parseRatingFromImage(element)
                        if rating:
                            attributes['rating'] = rating
                            break
        except AttributeError or TypeError:
            raise ParsingError(u'Failed to locate and collect attributes.')

        separators = u"\r\n :;."
        freestandingText = u''
        for line in attributesText.split(u'\n'):
            if line.count(u':') != 1:
                freestandingText += line
                continue
            key, value = line.split(u':', 1)
            key = key.strip(separators).lower()
            value = value.strip().strip(separators)
            parsed = self._parseAttribute(key, value)
            for parsedKey, parsedValue in parsed.items():
                attributes[parsedKey] = parsedValue

        freestandingText = freestandingText.strip()
        if 'summary' not in attributes and freestandingText:
            attributes['summary'] = freestandingText

        if 'rating' not in attributes:
            logger.warning(u"Failed to locate or recognize rating for `%s'!", self.getUrl())

        return attributes

    # Most, but not all, URLs of rating icons match this.
    RATING_LABEL_PATTERN = re.compile(r'/(?P<rating>[ERATINnG]+)\.png$')

    def _parseRatingFromImage(self, element):
        """Given an image element, try to parse story rating from it."""
        if not element.has_attr('src'):
            return
        source = element['src']
        if 'REITiNG' in source:
            match = re.search(self.RATING_LABEL_PATTERN, source)
            if not match:
                return
            label = match.group('rating')
            if label in self._configuration['ratingTitles']:
                return {
                    'label': label,
                    'title': self._configuration['ratingTitles'][label],
                    'isAdult': label in self._configuration['adultRatings']
                }
            else:
                logger.warning(u"No title found for rating label `%s'!" % label)
        # TODO: conduct a research on such abnormal URLs.
        elif '/_fr/10/1360399.png' in source:
            label = 'Nn'
            return {
                'label': 'Nn',
                'title': self._configuration['ratingTitles'][label],
                'isAdult': label in self._configuration['adultRatings']
            }

    # Various `et cetera' and `et al' forms in Russian texts.
    # Intended to be used with whole strings!
    ETC_PATTERN = re.compile(
        r'''[и&]\s(?:
              (?:т\.?\s?[пд]?\.?)|
              (?:др(?:угие|\.)?)|
              (?:пр(?:очие|\.)?)|
              # Note: identically looking letters `K' and `o'
              # below are from Latin and Cyrillic alphabets.
              (?:ко(?:мпания)?|[KК][oо°])
            )$
        ''',
        re.IGNORECASE + re.UNICODE + re.VERBOSE)

    # `Author's Notes' and its variants in Russian.
    ANNOTATION_PATTERN = re.compile(r'аннотация|описание|(?:(?:за|при)мечание\s)?(?:от\s)?автора', re.UNICODE)

    def _parseAttribute(self, key, value):
        """
        Parse a single a single record in chapter attributes for chapter metadata.
        Return a dictionary of canonical attributes and values (i. e. multiple attributes may be discovered).
        """

        def refineCharacter(name):
            """Refines character name from stop-words and distortions."""
            strippedName = name.strip()
            nameOnly = re.sub(self.ETC_PATTERN, u'', strippedName)
            # TODO: extract canonical name (even ME-specific?).
            canonicalName = nameOnly
            return canonicalName

        if re.match(u'жанры?', key, re.UNICODE):
            genres = [ u.strip() for u in re.split(u'[,;/]', value) ]
            return {'genres': genres}
        elif key == u'статус':
            isInProgress = value == u'в процессе'
            return {'isInProgress': isInProgress}
        elif key == u'персонажи':
            participants = [ refineCharacter(x) for x in re.split(u'[,;]', value) ]
            characters = []
            pairings = []
            for participant in participants:
                if u'/' in participant:
                    pairings.append(participant)
                else:
                    characters.append(participant)
            return {
                'characters': characters,
                'pairings': pairings
            }
        elif key == u'предупреждение':
            return {'warning': value}
        elif re.match(self.ANNOTATION_PATTERN, key):
            if not value.endswith(u'.'):
                value += u'.'
            # Capitalize would make value[1:] lowercase, which we don't want.
            value = value[:1].upper() + value[1:]
            return {'summary': value}
        else:
            logger.info(u"Unrecognized attribute `%s' ignored.", key)
            return {}

    def _getTextElement(self):
        """Locate chapter body text element on the page."""
        if not self._textElement:
            self._textElement = self.__collectTextElements()
        return self._textElement

    def __collectTextElements(self):
        """Return all elements containing parts of chapter text (which may be
        <p>aragraphs, <div>isions or plain text nodes) under a single root."""
        starter = self._document.find('div', {'itemprop': 'articleBody'})
        if starter is None:
            # FIXME: This will occur if the method is called more than once.
            # The reason is elements appended to `root' are removed from the document.
            # BS 4.4 implements cloning via `copy.copy()', but supporting it for BS 4.3
            # would be error-prone (due to relying on BS internals) and is not needed.
            if self._textElement:
                logger.debug(u"You may not call this function more than once!")
            raise ParsingError(u'Failed to locate text.')
        collection = [starter]
        for element in starter.childGenerator():
            if element is None:
                break
            collection.append(element)
        root = bs4.Tag(name='td')
        for element in collection:
            root.append(element)

        if self._configuration['excludeEditorSignature']:
            root = self._excludeEditorSignature(root)

        return root

    # Editor signature always starts with something like this.
    SIGNED_PATTERN = re.compile(r'отредактирова(?:но|ла?)[:.\s]', re.IGNORECASE + re.UNICODE)

    def _excludeEditorSignature(self, root):
        """Exclude editor signature from within `root' element."""
        for stringNode in root.find_all(string=True):
            if re.match(self.SIGNED_PATTERN, textNode.string):
                editorLink = textNode.findNext('a')
                if editorLink:
                    editorLink.extract()
                # Seldom editor link has inner formatting, which is sibling DOM-wise.
                editorName = textNode.findNext('i')
                if editorName:
                    editorName.extract()
                textNode.extract()
                # We could try removing container element, but there is a risk
                # of removing text ending with it.  Better play safe here.
                break
        return root


def _getLargestCommonPrefix(*args):
    """Returns largest common prefix of all unicode arguments, ignoring case.
    :rtype : unicode
    """
    toLower = lambda xs: [ x.lower() for x in xs ]
    allSame = lambda xs: len(set(toLower(xs))) == 1
    return u''.join([i[0] for i in takewhile(allSame, izip(*args))])
