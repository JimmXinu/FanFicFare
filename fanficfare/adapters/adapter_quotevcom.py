import re
import urlparse
import urllib2
import datetime

from .. import exceptions
from base_adapter import BaseSiteAdapter

SITE_DOMAIN = 'quotev.com'
STORY_URL_TEMPLATE = 'http://www.quotev.com/story/%s'


def getClass():
    return QuotevComAdapter


def get_url_path_segments(url):
    return tuple(filter(None, url.split('/')[3:]))


# TODO: Possibly add pages/readers/reads/favorites
class QuotevComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        story_id = get_url_path_segments(url)[1]
        self._setURL(STORY_URL_TEMPLATE % story_id)
        self.story.setMetadata('storyId', story_id)
        self.story.setMetadata('siteabbrev', SITE_DOMAIN)

    @staticmethod
    def getSiteDomain():
        return SITE_DOMAIN

    @classmethod
    def getSiteExampleURLs(cls):
        return STORY_URL_TEMPLATE % '1234'

    def getSiteURLPattern(self):
        pattern = re.escape(STORY_URL_TEMPLATE.rsplit('%', 1)[0]) + r'(.+?)($|&|/)'
        pattern = pattern.replace(r'http\:', r'https?\:')
        pattern = pattern.replace(r'https?\:\/\/www\.', r'https?\:\/\/(www\.)?')
        return pattern

    def use_pagecache(self):
        return True

    def extractChapterUrlsAndMetadata(self):
        try:
            data = self._fetchUrl(self.url)
        except urllib2.HTTPError:
            raise exceptions.FailedToDownload(self.url)

        soup = self.make_soup(data)

        element = soup.find('div', {'class': 'result_head'})
        if not element:
            raise exceptions.StoryDoesNotExist(self.url)

        self.story.setMetadata('title', element.find('span', recursive=False).get_text())

        element = soup.find('div', {'class': 'desc_creator'})('a')[1]
        self.story.setMetadata('author', element.get_text())
        self.story.setMetadata('authorId', get_url_path_segments(element['href'])[0])
        self.story.setMetadata('authorUrl', urlparse.urljoin(self.url, element['href']))
        self.setDescription(self.url, self.utf8FromSoup(self.url, soup.find('div', id='qdesct')))
        self.setCoverImage(self.url, urlparse.urljoin(self.url, soup.find('img', {'class': 'logo'})['src']))

        for a in soup.find('div', {'class': 'tag'})('a'):
            if a['href'] == '#':
                continue

            self.story.addToList('category', a.get_text())

        self.story.setMetadata(
            'status', 'Completed' if 'completed' in
            soup.find('div', {'class': 't'})('div', recursive=False)[1].div.get_text()
            else 'In-Progress'
        )

        elements = soup('span', {'class': 'q_time'})
        self.story.setMetadata('datePublished', datetime.datetime.fromtimestamp(float(elements[0]['ts'])))
        self.story.setMetadata('dateUpdated', datetime.datetime.fromtimestamp(float(elements[1]['ts'])))

        for a in soup.find('div', id='rselect')('a'):
            self.chapterUrls.append((a.get_text(), urlparse.urljoin(self.url, a['href'])))

        self.story.setMetadata('numChapters', len(self.chapterUrls))

    def getChapterText(self, url):
        data = self._fetchUrl(url)
        soup = self.make_soup(data)

        element = soup.find('div', id='restxt')
        for a in element('a'):
            a.unwrap()

        return self.utf8FromSoup(url, element)
