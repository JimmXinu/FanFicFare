# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2020 FanFicFare team
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

from __future__ import absolute_import
import datetime
import logging
logger = logging.getLogger(__name__)
import re
from .. import translit


from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition

from .base_adapter import BaseSiteAdapter,  makeDate


def getClass():
    return FicBookNetAdapter


logger = logging.getLogger(__name__)

class FicBookNetAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])


        # normalized story URL.
        self._setURL('https://' + self.getSiteDomain() + '/readfic/'+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','fbn')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d %m %Y"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'ficbook.net'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/readfic/12345 https://"+cls.getSiteDomain()+"/readfic/93626/246417#part_content"

    def getSiteURLPattern(self):
        return r"https?://"+re.escape(self.getSiteDomain()+"/readfic/")+r"\d+"

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):
        url=self.url
        logger.debug("URL: "+url)
        data = self.get_request(url)

        soup = self.make_soup(data)

        adult_div = soup.find('div',id='adultCoverWarning')
        if adult_div:
            if self.is_adult or self.getConfig("is_adult"):
                adult_div.extract()
            else:
                raise exceptions.AdultCheckRequired(self.url)


        ## Title
        a = soup.find('section',{'class':'chapter-info'}).find('h1')
        # kill '+' marks if present.
        sup = a.find('sup')
        if sup:
            sup.extract()
        self.story.setMetadata('title',stripHTML(a))
        logger.debug("Title: (%s)"%self.story.getMetadata('title'))

        # Find authorid and URL from... author url.
        # assume first avatar-nickname -- there can be a second marked 'beta'.
        a = soup.find('a',{'class':'creator-nickname'})
        self.story.setMetadata('authorId',a.text) # Author's name is unique
        self.story.setMetadata('authorUrl','https://'+self.host+a['href'])
        self.story.setMetadata('author',a.text)
        logger.debug("Author: (%s)"%self.story.getMetadata('author'))

        # Find the chapters:
        pubdate = None
        chapters = soup.find('ul', {'class' : 'list-of-fanfic-parts'})
        if chapters != None:
            for chapdiv in chapters.findAll('li', {'class':'part'}):
                chapter=chapdiv.find('a',href=re.compile(r'/readfic/'+self.story.getMetadata('storyId')+r"/\d+#part_content$"))
                churl='https://'+self.host+chapter['href']
                self.add_chapter(chapter,churl)

                datespan = chapdiv.find('span')
                if pubdate == None and datespan:
                    pubdate = translit.translit(stripHTML(datespan))
                update = translit.translit(stripHTML(datespan))
        else:
            self.add_chapter(self.story.getMetadata('title'),url)
            self.story.setMetadata('numChapters',1)
            pubdate=translit.translit(stripHTML(soup.find('div',{'class':'title-area'}).find('span')))
            update=pubdate

        logger.debug("numChapters: (%s)"%self.story.getMetadata('numChapters'))

        if not ',' in pubdate:
            pubdate=datetime.date.today().strftime(self.dateformat)
        if not ',' in update:
            update=datetime.date.today().strftime(self.dateformat)
        pubdate=pubdate.split(',')[0]
        update=update.split(',')[0]

        fullmon = {"yanvarya":"01", u"января":"01",
           "fievralya":"02", u"февраля":"02",
           "marta":"03", u"марта":"03",
           "aprielya":"04", u"апреля":"04",
           "maya":"05", u"мая":"05",
           "iyunya":"06", u"июня":"06",
           "iyulya":"07", u"июля":"07",
           "avghusta":"08", u"августа":"08",
           "sentyabrya":"09", u"сентября":"09",
           "oktyabrya":"10", u"октября":"10",
           "noyabrya":"11", u"ноября":"11",
           "diekabrya":"12", u"декабря":"12" }

        for (name,num) in fullmon.items():
            if name in pubdate:
                pubdate = pubdate.replace(name,num)
            if name in update:
                update = update.replace(name,num)

        self.story.setMetadata('dateUpdated', makeDate(update, self.dateformat))
        self.story.setMetadata('datePublished', makeDate(pubdate, self.dateformat))
        self.story.setMetadata('language','Russian')

        ## after site change, I don't see word count anywhere.
        # pr=soup.find('a', href=re.compile(r'/printfic/\w+'))
        # pr='https://'+self.host+pr['href']
        # pr = self.make_soup(self.get_request(pr))
        # pr=pr.findAll('div', {'class' : 'part_text'})
        # i=0
        # for part in pr:
        #     i=i+len(stripHTML(part).split(' '))
        # self.story.setMetadata('numWords', unicode(i))


        dlinfo = soup.find('div',{'class':'fanfic-main-info'})

        i=0
        fandoms = dlinfo.find('div').findAll('a', href=re.compile(r'/fanfiction/\w+'))
        for fandom in fandoms:
            self.story.addToList('category',fandom.string)
            i=i+1
        if i > 1:
            self.story.addToList('genre', u'Кроссовер')

        tags = soup.find('div',{'class':'tags'})
        if tags:
            for genre in tags.findAll('a',href=re.compile(r'/tags/')):
                self.story.addToList('genre',stripHTML(genre))

        ratingdt = dlinfo.find('div',{'class':re.compile(r'badge-rating-.*')})
        self.story.setMetadata('rating', stripHTML(ratingdt.find('span')))

        # meta=table.findAll('a', href=re.compile(r'/ratings/'))
        # i=0
        # for m in meta:
        #     if i == 0:
        #         self.story.setMetadata('rating', stripHTML(m))
        #         i=1
        #     elif i == 1:
        #         if not "," in m.nextSibling:
        #             i=2
        #         self.story.addToList('genre', m.find('b').text)
        #     elif i == 2:
        #         self.story.addToList('warnings', m.find('b').text)

        if dlinfo.find('div', {'class':'badge-status-finished'}):
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        paircharsdt = soup.find('strong',text='Пэйринг и персонажи:')
        # site keeps both ships and indiv chars in /pairings/ links.
        if paircharsdt:
            for paira in paircharsdt.find_next('div').find_all('a', href=re.compile(r'/pairings/')):
                if 'pairing-highlight' in paira['class']:
                    self.story.addToList('ships',stripHTML(paira))
                    chars=stripHTML(paira).split('/')
                    for char in chars:
                        self.story.addToList('characters',char)
                else:
                    self.story.addToList('characters',stripHTML(paira))

        summary=soup.find('div', itemprop='description')
        self.setDescription(url,summary)
        #self.story.setMetadata('description', summary.text)

    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self.get_request(url))

        chapter = soup.find('div', {'id' : 'content'})
        if chapter == None: ## still needed?
            chapter = soup.find('div', {'class' : 'public_beta_disabled'})

        if None == chapter:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,chapter)
