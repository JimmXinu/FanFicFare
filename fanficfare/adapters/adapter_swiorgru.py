# -*- coding: utf-8 -*-

from __future__ import absolute_import
import datetime
import logging
logger = logging.getLogger(__name__)
import re, sys
from .. import translit


from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter,  makeDate


def getClass():
    return SwiOrgRuAdapter


logger = logging.getLogger(__name__)

class SwiOrgRuAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False
        storyId = self.parsedUrl.path.split('/',)[3]
        self.story.setMetadata('storyId', storyId)

        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/mlp-fim/story/'+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','swi')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%b %d, %Y"


    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        return 'www.swi.org.ru'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://" + cls.getSiteDomain() + "/mlp-fim/story/11341/ http://" + cls.getSiteDomain() + "/mlp-fim/story/11341/chapter1.html"

    def getSiteURLPattern(self):
        return r"http://" + re.escape(self.getSiteDomain() + "/mlp-fim/story/")+r"\d+"

    def extractChapterUrlsAndMetadata(self):
        url=self.url
        logger.debug("URL: "+url)
        try:
            data = self._fetchUrl(url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        title = soup.find('h1')

        self.story.setMetadata('title', stripHTML(title))
        logger.debug("Title: (%s)"%self.story.getMetadata('title'))

        author_title = soup.find('strong', text = re.compile("Автор: "))
        if author_title == None:
            logger.info('author_title no found... exiting')
            sys.exit()

        author = author_title.next_sibling

        self.story.setMetadata('authorId', author.text) # Author's name is unique
        self.story.setMetadata('authorUrl','http://'+self.host + author['href'])
        self.story.setMetadata('author',author.text)
        logger.debug("Author: (%s)"%self.story.getMetadata('author'))
        
        chapters_header = soup.find('h2', text = re.compile("Главы:"))
        if chapters_header==None:
            logger.info('chapters_header no found... exiting')
            sys.exit()

        chapters_table = chapters_header.next_sibling.next_sibling

        chapters=chapters_table.findAll('a', href=re.compile(r'/mlp-fim/story/'+self.story.getMetadata('storyId')+"/chapter\d+"))
        self.story.setMetadata('numChapters', len(chapters))
        logger.debug("numChapters: (%s)"%str(self.story.getMetadata('numChapters')))

        for x in range(0,len(chapters)):
                chapter=chapters[x]
                churl='http://'+self.host+chapter['href']
                self.add_chapter(chapter,churl)

        self.story.setMetadata('language','Russian')

    # grab the text for an individual chapter.
    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
        soup = self.make_soup(self._fetchUrl(url))
        chapter = soup.find('div', {'id' : 'content'})
        
        chapter_header = chapter.find('h1', id = re.compile("chapter"))
        if not chapter_header == None:
            chapter_header.decompose()

        if chapter == None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,chapter)