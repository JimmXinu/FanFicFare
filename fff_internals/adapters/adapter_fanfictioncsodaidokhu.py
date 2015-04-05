# coding=utf-8

import re
import urllib2
import urlparse

from .. import BeautifulSoup

from base_adapter import BaseSiteAdapter, makeDate
from .. import exceptions


_SOURCE_CODE_ENCODING = 'utf-8'


def getClass():
    return FanfictionCsodaidokHuAdapter


def _get_query_data(url):
    components = urlparse.urlparse(url)
    query_data = urlparse.parse_qs(components.query)
    return dict((key, data[0]) for key, data in query_data.items())


# yields Tag _and_ NavigableString siblings from the given tag. The
# BeautifulSoup findNextSiblings() method for some reasons only returns either
# NavigableStrings _or_ Tag objects, not both.
def _yield_next_siblings(tag):
    sibling = tag.nextSibling
    while sibling:
        yield sibling
        sibling = sibling.nextSibling


class FanfictionCsodaidokHuAdapter(BaseSiteAdapter):
    _SITE_DOMAIN = 'fanfiction.csodaidok.hu'
    _BASE_URL = 'http://' + _SITE_DOMAIN + '/'
    _VIEW_STORY_URL_TEMPLATE = _BASE_URL + 'viewstory.php?sid=%s'
    _VIEW_CHAPTER_URL_TEMPLATE = _VIEW_STORY_URL_TEMPLATE + '&chapter=%s'

    _STORY_DOES_NOT_EXIST_PAGE_TITLE = 'Cím:  Szerző:'
    _DATE_FORMAT = '%Y.%m.%d'
    _SITE_LANGUAGE = 'Hungarian'

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        query_data = urlparse.parse_qs(self.parsedUrl.query)
        story_id = query_data['sid'][0]

        self.story.setMetadata('storyId', story_id)
        self._setURL(self._VIEW_STORY_URL_TEMPLATE % story_id)
        self.story.setMetadata('siteabbrev', self._SITE_DOMAIN)
        self.story.setMetadata('language', self._SITE_LANGUAGE)

    def _customized_fetch_url(self, url, exception=None, parameters=None):
        if exception:
            try:
                data = self._fetchUrl(url, parameters)
            except urllib2.HTTPError:
                raise exception(self.url)
        # Just let self._fetchUrl throw the exception, don't catch and
        # customize it.
        else:
            data = self._fetchUrl(url, parameters)

        return BeautifulSoup.BeautifulSoup(data)

    @staticmethod
    def getSiteDomain():
        return FanfictionCsodaidokHuAdapter._SITE_DOMAIN

    @classmethod
    def getSiteExampleURLs(cls):
        return cls._VIEW_STORY_URL_TEMPLATE % 1234

    def getSiteURLPattern(self):
        return re.escape(self._VIEW_STORY_URL_TEMPLATE[:-2]) + r'\d+$'

    def extractChapterUrlsAndMetadata(self):
        soup = self._customized_fetch_url(self.url + '&chapter=1')

        element = soup.find('div', id='pagetitle')
        page_title = ''.join(element(text=True)).encode(_SOURCE_CODE_ENCODING)
        if page_title == self._STORY_DOES_NOT_EXIST_PAGE_TITLE:
            raise exceptions.StoryDoesNotExist(self.url)

        author_url = urlparse.urljoin(self.url, element.a['href'])

        story_id = self.story.getMetadata('storyId')
        element = soup.find('select', {'name': 'chapter'})
        if element:
            for option in element('option'):
                title = option.string
                url = self._VIEW_CHAPTER_URL_TEMPLATE % (story_id, option['value'])
                self.chapterUrls.append((title, url))

        soup = self._customized_fetch_url(author_url)
        story_id = self.story.getMetadata('storyId')

        for listbox_div in soup('div', {'class': lambda klass: klass and 'listbox' in klass}):
            a = listbox_div.div.a
            if not a['href'].startswith('viewstory.php?sid='):
                continue

            query_data = _get_query_data(a['href'])
            if query_data['sid'] == story_id:
                break
        else:
            raise exceptions.FailedToDownload(self.url)

        title = ''.join(a(text=True))
        self.story.setMetadata('title', title)
        if not self.chapterUrls:
            self.chapterUrls.append((title, self.url))

        element = a.findNextSibling('a')
        self.story.setMetadata('author', element.string)
        query_data = _get_query_data(element['href'])
        self.story.setMetadata('authorId', query_data['uid'])
        self.story.setMetadata('authorUrl', author_url)

        element = element.findNextSibling('span')
        rating = element.nextSibling.strip(' [')

        if rating.encode(_SOURCE_CODE_ENCODING) != 'Korhatár nélkül':
            self.story.setMetadata('rating', rating)

        if rating == '18':
            raise exceptions.AdultCheckRequired(self.url)

        element = element.findNextSiblings('a')[1]
        self.story.setMetadata('reviews', element.string)

        sections = listbox_div('div', {'class': lambda klass: klass and klass in ['content', 'tail']})
        for section in sections:
            for element in section('span', {'class': 'classification'}):
                key = element.string.encode(_SOURCE_CODE_ENCODING).strip(' :')
                try:
                    value = element.nextSibling.string.encode(_SOURCE_CODE_ENCODING).strip()
                except AttributeError:
                    value = None

                if key == 'Tartalom':
                    contents = []
                    keep_summary_html = self.getConfig('keep_summary_html')

                    for sibling in _yield_next_siblings(element):
                        if isinstance(sibling, BeautifulSoup.Tag):
                            if sibling.name == 'span' and sibling.get('class', None) == 'classification':
                                break

                            if keep_summary_html:
                                contents.append(self.utf8FromSoup(author_url, sibling))
                            else:
                                contents.append(''.join(sibling(text=True)))
                        else:
                            contents.append(sibling)
                    self.story.setMetadata('description', ''.join(contents))

                elif key == 'Kategória':
                    for sibling in element.findNextSiblings(['a', 'span']):
                        if sibling.name == 'span':
                            break

                        self.story.addToList('category', sibling.string)

                elif key == 'Szereplők':
                    for name in value.split(', '):
                        self.story.addToList('characters', name)

                elif key == 'Műfaj':
                    if value != 'Nincs':
                        self.story.setMetadata('genre', value)

                elif key == 'Figyelmeztetés':
                    if value != 'Nincs':
                        for warning in value.split(', '):
                            self.story.addToList('warnings', warning)

                elif key == 'Kihívás':
                    if value != 'Nincs':
                        self.story.setMetadata('challenge', value)

                elif key == 'Sorozat':
                    if value != 'Nincs':
                        self.story.setMetadata('series', value)

                elif key == 'Fejezetek':
                    self.story.setMetadata('numChapters', int(value))

                elif key == 'Befejezett':
                    self.story.setMetadata('status', 'Completed' if value == 'Nem' else 'In-Progress')

                elif key == 'Szavak száma':
                    self.story.setMetadata('numWords', value)

                elif key == 'Feltöltve':
                    self.story.setMetadata('datePublished', makeDate(value, self._DATE_FORMAT))

                elif key == 'Frissítve':
                    self.story.setMetadata('dateUpdated', makeDate(value, self._DATE_FORMAT))

    def getChapterText(self, url):
        soup = self._customized_fetch_url(url)
        contents = []

        notes_div = soup.find('div', id='notes')
        if notes_div:
            contents.append(self.utf8FromSoup(url, notes_div))
            story_div = notes_div.findNextSibling('div')
        else:
            element = soup.find('div', {'class': 'jumpmenu'})
            story_div = element.findNextSibling('div')

        contents.append(self.utf8FromSoup(url, story_div.span))
        return ''.join(contents)
