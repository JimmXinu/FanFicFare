from __future__ import absolute_import
from datetime import timedelta
import re

import logging
logger = logging.getLogger(__name__)

from bs4 import BeautifulSoup
from ..htmlcleanup import stripHTML

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib import parse as urlparse
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter, makeDate
from .. import exceptions


def getClass():
    return BloodshedverseComAdapter


def _get_query_data(url):
    components = urlparse.urlparse(url)
    query_data = urlparse.parse_qs(components.query)
    return dict((key, data[0]) for key, data in query_data.items())


class BloodshedverseComAdapter(BaseSiteAdapter):
    SITE_ABBREVIATION = 'bvc'
    SITE_DOMAIN = 'bloodshedverse.com'

    BASE_URL = 'https://' + SITE_DOMAIN + '/'
    READ_URL_TEMPLATE = BASE_URL + 'stories.php?go=read&no=%s'

    STARTED_DATETIME_FORMAT = '%m/%d/%Y'
    UPDATED_DATETIME_FORMAT = '%m/%d/%Y %I:%M %p'

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        query_data = urlparse.parse_qs(self.parsedUrl.query)
        story_no = query_data['no'][0]

        self.story.setMetadata('storyId', story_no)
        self._setURL(self.READ_URL_TEMPLATE % story_no)
        self.story.setMetadata('siteabbrev', self.SITE_ABBREVIATION)

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
        return BloodshedverseComAdapter.SITE_DOMAIN

    @classmethod
    def getSiteExampleURLs(cls):
        return cls.READ_URL_TEMPLATE % 1234

    def getSiteURLPattern(self):
        return r'https?://' + re.escape(self.SITE_DOMAIN + '/stories.php?go=') + r'(read|chapters)\&(amp;)?no=\d+$'

    # Override stripURLParameters so the "no" parameter won't get stripped
    @classmethod
    def stripURLParameters(cls, url):
        return url

    def extractChapterUrlsAndMetadata(self):
        logger.debug("URL: "+self.url)
        soup = self._customized_fetch_url(self.url)

        # Since no 404 error code we have to raise the exception ourselves.
        # A title that is just 'by' indicates that there is no author name
        # and no story title available.
        if stripHTML(soup.title) == 'by':
            raise exceptions.StoryDoesNotExist(self.url)

        for option in soup.find('select', {'name': 'chapter'}):
            title = stripHTML(option)
            url = self.READ_URL_TEMPLATE % option['value']
            self.add_chapter(title, url)

        # Reset the storyId to be the first chapter no.  Needed
        # because emails contain link to later chapters instead.
        query_data = urlparse.parse_qs(self.get_chapter(0,'url'))
        story_no = query_data['no'][0]

        self.story.setMetadata('storyId', story_no)
        self._setURL(self.READ_URL_TEMPLATE % story_no)
        logger.info("updated storyId:%s"%story_no)
        logger.info("updated storyUrl:%s"%self.url)

        story_no = self.story.getMetadata('storyId')
        # Get the URL to the author's page and find the correct story entry to
        # scrape the metadata
        author_url = urlparse.urljoin(self.url, soup.find('a', {'class': 'headline'})['href'])
        soup = self._customized_fetch_url(author_url)

        # Ignore first list_box div, it only contains the author information
        for list_box in soup('div', {'class': 'list_box'})[1:]:
            url = list_box.find('a', {'class': 'fictitle'})['href']
            query_data = _get_query_data(url)

            # Found the div containing the story's metadata; break the loop and
            # parse the element
            if query_data['no'] == story_no:
                break
        else:
            raise exceptions.FailedToDownload(self.url)

        title_anchor = list_box.find('a', {'class': 'fictitle'})
        self.story.setMetadata('title', stripHTML(title_anchor))

        author_anchor = title_anchor.findNextSibling('a')
        self.story.setMetadata('author', stripHTML(author_anchor))
        self.story.setMetadata('authorId', _get_query_data(author_anchor['href'])['who'])
        self.story.setMetadata('authorUrl', urlparse.urljoin(self.url, author_anchor['href']))

        list_review = list_box.find('div', {'class': 'list_review'})
        reviews = stripHTML(list_review.a).split(' ', 1)[0]
        self.story.setMetadata('reviews', reviews)

        summary_div = list_box.find('div', {'class': 'list_summary'})
        if not self.getConfig('keep_summary_html'):
            summary = ''.join(summary_div(text=True))
        else:
            summary = self.utf8FromSoup(author_url, summary_div)

        self.story.setMetadata('description', summary)

        # I'm assuming this to be the category, not sure what else it could be
        first_listinfo = list_box.find('div', {'class': 'list_info'})
        self.story.addToList('category', stripHTML(first_listinfo.a))

        for list_info in first_listinfo.findNextSiblings('div', {'class': 'list_info'}):
            for b_tag in list_info('b'):
                key = b_tag.string.strip(': ')
                # Strip colons from the beginning, superfluous spaces and minus
                # characters from the end, and possibly trailing commas from
                # the warnings if only one is present
                value = b_tag.nextSibling.string.strip(': -,')

                if key == 'Genre':
                    for genre in value.split(', '):
                        # Ignore the "none" genre
                        if not genre == 'none':
                            self.story.addToList('genre', genre)

                elif key == 'Rating':
                    self.story.setMetadata('rating', value)

                elif key == 'Complete':
                    self.story.setMetadata('status', 'Completed' if value == 'Yes' else 'In-Progress')

                elif key == 'Warning':
                    for warning in value.split(', '):
                        # The string here starts with ", " before the actual list
                        # of values sometimes, so check for an empty warning
                        # and ignore the "none" warning.
                        if not warning or warning == 'none':
                            continue

                        self.story.addToList('warnings', warning)

                elif key == 'Chapters':
                    self.story.setMetadata('numChapters', int(value))

                elif key == 'Words':
                    # Apparently only numChapters need to be an integer for
                    # some strange reason. Remove possible ',' characters as to
                    # not confuse the codebase down the line
                    self.story.setMetadata('numWords', value.replace(',', ''))

                elif key == 'Started':
                    self.story.setMetadata('datePublished', makeDate(value, self.STARTED_DATETIME_FORMAT))

                elif key == 'Updated':
                    date = makeDate(value, self.UPDATED_DATETIME_FORMAT)
                    # ugly %p(am/pm) hack moved into makeDate so other sites can use it.
                    self.story.setMetadata('dateUpdated', date)

        if self.story.getMetadata('rating') == 'NC-17' and not (self.is_adult or self.getConfig('is_adult')):
            raise exceptions.AdultCheckRequired(self.url)

    def getChapterText(self, url):
        soup = self._customized_fetch_url(url)
        storytext_div = soup.find('div', {'class': 'tl'})
        storytext_div = storytext_div.find('div', {'class': ''})

        if self.getConfig('strip_text_links'):
            for anchor in storytext_div('a', {'class': 'FAtxtL'}):
                anchor.replaceWith(anchor.string)

        return self.utf8FromSoup(url, storytext_div)
