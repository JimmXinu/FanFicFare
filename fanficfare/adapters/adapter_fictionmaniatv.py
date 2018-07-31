from __future__ import absolute_import
import re
# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib import parse as urlparse
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter, makeDate


def getClass():
    return FictionManiaTVAdapter


def _get_query_data(url):
    components = urlparse.urlparse(url)
    query_data = urlparse.parse_qs(components.query)
    return dict((key, data[0]) for key, data in query_data.items())


class FictionManiaTVAdapter(BaseSiteAdapter):
    SITE_ABBREVIATION = 'fmt'
    SITE_DOMAIN = 'fictionmania.tv'

    BASE_URL = 'https://' + SITE_DOMAIN + '/stories/'
    READ_TEXT_STORY_URL_TEMPLATE = BASE_URL + 'readtextstory.html?storyID=%s'
    DETAILS_URL_TEMPLATE = BASE_URL + 'details.html?storyID=%s'

    DATETIME_FORMAT = '%m/%d/%Y'
    ALTERNATIVE_DATETIME_FORMAT = '%m/%d/%y'

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        query_data = urlparse.parse_qs(self.parsedUrl.query)
        story_id = query_data['storyID'][0]

        self.story.setMetadata('storyId', story_id)
        self._setURL(self.READ_TEXT_STORY_URL_TEMPLATE % story_id)
        self.story.setMetadata('siteabbrev', self.SITE_ABBREVIATION)

        # Always single chapters, probably should use the Anthology feature to
        # merge chapters of a story
        self.story.setMetadata('numChapters', 1)

    def _customized_fetch_url(self, url, exception=None, parameters=None):
        if exception:
            try:
                data = self._fetchUrl(url, parameters)
            except HTTPError:
                raise exception(self.url)
        # Just let self._fetchUrl throw the exception, don't catch and
        # customize it.
        else:
            data = self._fetchUrl(url, parameters)

        return self.make_soup(data)

    @staticmethod
    def getSiteDomain():
        return FictionManiaTVAdapter.SITE_DOMAIN

    @classmethod
    def getSiteExampleURLs(cls):
        return cls.READ_TEXT_STORY_URL_TEMPLATE % 1234

    def getSiteURLPattern(self):
        return r'https?' + re.escape(self.BASE_URL[len('https'):]) + '(readtextstory|readxstory|details)\.html\?storyID=\d+$'

    def extractChapterUrlsAndMetadata(self):
        url = self.DETAILS_URL_TEMPLATE % self.story.getMetadata('storyId')
        soup = self._customized_fetch_url(url)

        keep_summary_html = self.getConfig('keep_summary_html')
        for row in soup.find('table')('tr'):
            cells = row('td')
            key = cells[0].b.string.strip(':')
            try:
                value = cells[1].string
            except AttributeError:
                value = None

            if key == 'Title':
                self.story.setMetadata('title', value)
                self.add_chapter(value, self.url)

            elif key == 'File Name':
                self.story.setMetadata('fileName', value)

            elif key == 'File Size':
                self.story.setMetadata('fileSize', value)

            elif key == 'Author':
                element = cells[1].a
                self.story.setMetadata('author', element.string)
                query_data = _get_query_data(element['href'])
                self.story.setMetadata('authorId', query_data['word'])
                self.story.setMetadata('authorUrl', urlparse.urljoin(url, element['href']))

            elif key == 'Date Added':
                try:
                    date = makeDate(value, self.DATETIME_FORMAT)
                except ValueError:
                    date = makeDate(value, self.ALTERNATIVE_DATETIME_FORMAT)
                self.story.setMetadata('datePublished', date)

            elif key == 'Old Name':
                self.story.setMetadata('oldName', value)

            elif key == 'New Name':
                self.story.setMetadata('newName', value)

            ## I've encountered a few storyies that have None as the
            ## value for Other Names [GComyn]
            elif key == 'Other Names' and value != None:
                for name in value.split(', '):
                    self.story.addToList('characters', name)

            # I have no clue how the rating system works, if you are reading
            # transgender fanfiction, you are probably an adult.
            elif key == 'Rating':
                self.story.setMetadata('rating', value)

            elif key == 'Complete':
                self.story.setMetadata('status', 'Completed' if value == 'Complete' else 'In-Progress')

            elif key == 'Categories':
                for element in cells[1]('a'):
                    self.story.addToList('category', element.string)

            elif key == 'Key Words':
                for element in cells[1]('a'):
                    self.story.addToList('keyWords', element.string)

            elif key == 'Age':
                element = cells[1].a
                self.story.setMetadata('mainCharactersAge', element.string)

            elif key == 'Synopsis':
                element = cells[1]

                # Replace td with div to avoid possible strange formatting in
                # the ebook later on
                element.name = 'div'

                if keep_summary_html:
                    self.story.setMetadata('description', unicode(element))
                else:
                    self.story.setMetadata('description', element.get_text(strip=True))

            elif key == 'Reads':
                self.story.setMetadata('readings', value)

    def getChapterText(self, url):
        soup = self._customized_fetch_url(url)
        element = soup.find('pre')
        element.name = 'div'

        # The story's content is contained in a <pre> tag, probably taken 1:1
        # from the source text file. A simple replacement of all newline
        # characters with a break line tag should take care of formatting.

        # While wrapping in paragraphs would be possible, it's too much work,
        # I'd rather display the story 1:1 like it was found in the pre tag.
        content = unicode(element)
        content = content.replace('\n', '<br/>')

        if self.getConfig('non_breaking_spaces'):
            return content.replace(' ', '&nbsp;')

        ## Normally, getChapterText should use self.utf8FromSoup(),
        ## but this is converting from plain(ish) text. -- JM
        return content
