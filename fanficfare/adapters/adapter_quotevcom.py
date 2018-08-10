#  -*- coding: utf-8 -*-

from __future__ import absolute_import
import re
import datetime

from .. import exceptions
# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib import parse as urlparse
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter
from ..htmlcleanup import stripHTML

SITE_DOMAIN = 'quotev.com'
STORY_URL_TEMPLATE = 'https://www.quotev.com/story/%s'


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
        pattern = pattern.replace(r'https', r'https?')
        pattern = pattern.replace(r'www\.', r'(www\.)?')
        return pattern

    def use_pagecache(self):
        return True

    def extractChapterUrlsAndMetadata(self):
        try:
            data = self._fetchUrl(self.url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist("Code: %s: %s"%(e.code,self.url))
            else:
                raise #exceptions.FailedToDownload(self.url)

        soup = self.make_soup(data)

        element = soup.find('div', {'class': 'result'})
        if not element:
            raise exceptions.StoryDoesNotExist(self.url)

        title = element.find('h1')
        self.story.setMetadata('title', title.get_text())
        
        authdiv = soup.find('div', {'class':"quizAuthorList"})
        if authdiv:
            for a in authdiv.find_all('a'):
                self.story.addToList('author', a.get_text())
                self.story.addToList('authorId', a['href'].split('/')[-1])
                self.story.addToList('authorUrl', urlparse.urljoin(self.url, a['href']))
        if not self.story.getList('author'):
            self.story.addToList('author','Anonymous')
            self.story.addToList('authorUrl','https://www.quotev.com')
            self.story.addToList('authorId','0')

        self.setDescription(self.url, soup.find('div', id='qdesct'))
        imgmeta = soup.find('meta',{'property':"og:image" })
        if imgmeta:
            self.coverurl = self.setCoverImage(self.url, urlparse.urljoin(self.url, imgmeta['content']))[1]

        for a in soup.find_all('a', {'href': re.compile(SITE_DOMAIN+'/stories/c/')}):
            self.story.addToList('category', a.get_text())

        for a in soup.find_all('a', {'href': re.compile(SITE_DOMAIN+'/search/')}):
            self.story.addToList('searchtags', a.get_text())

        elements = soup.find_all('span', {'class': 'q_time'})
        self.story.setMetadata('datePublished', datetime.datetime.fromtimestamp(float(elements[0]['ts'])))
        if len(elements) > 1:
            self.story.setMetadata('dateUpdated', datetime.datetime.fromtimestamp(float(elements[1]['ts'])))

        metadiv = elements[0].parent.parent
        # print stripHTML(metadiv)
        if u'· completed ·' in stripHTML(metadiv):
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')        

        data = filter(None, (x.strip() for x in stripHTML(metadiv).split(u'\xb7')))

        for datum in data:
            parts = datum.split()
            if len(parts) < 2 or parts[1] not in self.getConfig('extra_valid_entries'):
                continue

            key, value = parts[1], parts[0]
            self.story.setMetadata(key, value.replace(',', '').replace('.', ''))

        favspans = soup.find('a',{'id':'fav_btn'}).find_all('span')
        if len(favspans) > 1:
            self.story.setMetadata('favorites', stripHTML(favspans[-1]).replace(',', ''))
            
        commentspans = soup.find('a',{'id':'comment_btn'}).find_all('span')
        #print("commentspans:%s"%commentspans)
        if len(commentspans) > 0:
            self.story.setMetadata('comments', stripHTML(commentspans[0]).replace(',', ''))

        for a in soup.find('div', id='rselect')('a'):
            if 'javascript' not in a['href']:
                self.add_chapter(a.get_text(), urlparse.urljoin(self.url, a['href']))

        
    def getChapterText(self, url):
        data = self._fetchUrl(url)
        soup = self.make_soup(data)

        rescontent = soup.find('div', id='rescontent')
        
        # attempt to find and include chapter specific images.
        img = soup.find('div',{'id':'quizHeader'}).find('img')
        #print("img['src'](%s) != self.coverurl(%s)"%(img['src'],self.coverurl))
        if img['src'] != self.coverurl:
            rescontent.insert(0,img)
        
        for a in rescontent('a'):
            a.unwrap()

        return self.utf8FromSoup(url, rescontent)
