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

        element = soup.find('div', {'class': 'desc_creator'})
        if element:
            a = element('a')[1]
            self.story.setMetadata('author', a.get_text())
            self.story.setMetadata('authorId', get_url_path_segments(a['href'])[0])
            self.story.setMetadata('authorUrl', urlparse.urljoin(self.url, a['href']))

        # Multiple authors
        else:
            element = soup.find('div', id='qheadx')
            for a in element('div', recursive=False)[1]('a'):
                author = a.get_text()
                if not a.get_text():
                    continue

                self.story.addToList('author', author)
                self.story.addToList('authorId', get_url_path_segments(a['href'])[0])
                self.story.addToList('authorUrl', urlparse.urljoin(self.url, a['href']))
            else:
                self.story.setMetadata('author','Anonymous')
                self.story.setMetadata('authorUrl','http://www.quotev.com')
                self.story.setMetadata('authorId','0')


        self.setDescription(self.url, soup.find('div', id='qdesct'))
        self.setCoverImage(self.url, urlparse.urljoin(self.url, soup.find('img', {'class': 'logo'})['src']))

        for a in soup.find('div', {'class': 'tag'})('a'):
            if a['href'] == '#':
                continue

            self.story.addToList('category', a.get_text())

        elements = soup('span', {'class': 'q_time'})
        self.story.setMetadata('datePublished', datetime.datetime.fromtimestamp(float(elements[0]['ts'])))
        if len(elements) > 1:
            self.story.setMetadata('dateUpdated', datetime.datetime.fromtimestamp(float(elements[1]['ts'])))

        for a in soup.find('div', id='rselect')('a'):
            self.chapterUrls.append((a.get_text(), urlparse.urljoin(self.url, a['href'])))

        self.story.setMetadata('numChapters', len(self.chapterUrls))

        element = soup.find('div', {'class': 't'})('div', recursive=False)[1].div
        data = filter(None, (x.strip() for x in element.get_text().split(u'\xb7')))
        if 'completed' in data:
            self.story.setMetadata('status', 'Completed')
            data.remove('completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        for datum in data:
            parts = datum.split()
            # Not a valid metadatum
            if not len(parts) == 2:
                continue

            key, value = parts
            self.story.setMetadata(key, value.replace(',', '').replace('.', ''))

        self.story.setMetadata('favorites', soup.find('div', id='favqn').get_text())
        element = soup.find('a', id='comment_btn').span
        self.story.setMetadata('comments', element.get_text() if element else 0)

    def getChapterText(self, url):
        data = self._fetchUrl(url)
        soup = self.make_soup(data)

        element = soup.find('div', id='restxt')
        for a in element('a'):
            a.unwrap()

        return self.utf8FromSoup(url, element)
