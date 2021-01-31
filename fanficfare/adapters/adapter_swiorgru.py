# -*- coding: utf-8 -*-

from __future__ import absolute_import
import logging
logger = logging.getLogger(__name__)
import re


from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition

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
        self.story.setMetadata('siteabbrev','swiorgru')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y.%m.%d"


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
        data = self.get_request(url)

        soup = self.make_soup(data)

        title = soup.find('h1')
        for tag in title.findAll('sup'):
            tag.extract()

        self.story.setMetadata('title', stripHTML(title.text))
        logger.debug("Title: (%s)"%self.story.getMetadata('title'))

        author_title = soup.find('strong', text = re.compile(u"Автор: "))
        if author_title == None:
            raise exceptions.FailedToDownload("Error downloading page: %s! Missing required author_title element!" % url)

        author = author_title.next_sibling

        self.story.setMetadata('authorId', author.text) # Author's name is unique
        self.story.setMetadata('authorUrl','http://'+self.host + author['href'])
        self.story.setMetadata('author', author.text)
        logger.debug("Author: (%s)"%self.story.getMetadata('author'))

        date_pub = soup.find('em', text = re.compile(r'\d{4}.\d{2}.\d{2}'))
        if not date_pub == None:
            self.story.setMetadata('datePublished', makeDate(date_pub.text, self.dateformat))

        rating_label = soup.find('strong', text = re.compile(u"рейтинг:"))
        if not rating_label == None:
            rating = rating_label.next_sibling.next_sibling
            self.story.setMetadata('rating', stripHTML(rating))

            if not self.is_adult or self.getConfig("is_adult"):
                if "NC-18" in rating:
                    raise exceptions.AdultCheckRequired(self.url)

        characters = soup.findAll('img', src=re.compile(r"/mlp-fim/img/chars/\d+.png"))
        logger.debug("numCharacters: (%s)"%str(len(characters)))

        for x in range(0,len(characters)):
            character=characters[x]
            self.story.addToList('characters', character['title'])

        if soup.find('font', color = r"green", text = u"завершен"):
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        categories_label = soup.find('strong', text = u"категории:")
        if not categories_label == None:
            categories_element = categories_label.next_sibling.next_sibling
            categories = re.findall(r'"(.+?)"', categories_element.text)
            for x in range(0, len(categories)):
                category=categories[x]
                self.story.addToList('category', category)

        chapters_header = soup.find('h2', text = re.compile(u"Главы:"))
        if chapters_header==None:
            raise exceptions.FailedToDownload("Error downloading page: %s! Missing required chapters_header element!" % url)

        chapters_table = chapters_header.next_sibling.next_sibling

        self.story.setMetadata('language','Russian')

        chapters=chapters_table.findAll('a', href=re.compile(r'/mlp-fim/story/'+self.story.getMetadata('storyId')+r"/chapter\d+"))
        self.story.setMetadata('numChapters', len(chapters))
        logger.debug("numChapters: (%s)"%str(self.story.getMetadata('numChapters')))

        for x in range(0,len(chapters)):
                chapter=chapters[x]
                churl='http://'+self.host+chapter['href']
                self.add_chapter(chapter,churl)

    # grab the text for an individual chapter.
    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
        soup = self.make_soup(self.get_request(url))
        chapter = soup.find('div', {'id' : 'content'})

        chapter_header = chapter.find('h1', id = re.compile("chapter"))
        if not chapter_header == None:
            chapter_header.decompose()

        if chapter == None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,chapter)
