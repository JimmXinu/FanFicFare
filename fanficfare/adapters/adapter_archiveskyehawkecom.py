# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2018 FanFicFare team
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
import logging
logger = logging.getLogger(__name__)
import re
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter,  makeDate


def getClass():
    return ArchiveSkyeHawkeComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class ArchiveSkyeHawkeComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])


        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/story.php?no='+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','ash')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y-%m-%d"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'archive.skyehawke.com'

    @classmethod
    def getAcceptDomains(cls):
        return ['archive.skyehawke.com','www.skyehawke.com']

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://archive.skyehawke.com/story.php?no=1234 http://www.skyehawke.com/archive/story.php?no=1234  http://skyehawke.com/archive/story.php?no=1234"

    def getSiteURLPattern(self):
        return r"https?://(archive|www)\.skyehawke\.com/(archive/)?story\.php\?no=\d+$"

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        url = self.url
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
        # print data

        # Now go hunting for all the meta data and the chapter list.

        ## Title
        a = soup.find('div', {'class':"story border"}).find('span',{'class':'left'})
        title=stripHTML(a).split('"')[1]
        self.story.setMetadata('title',title)

        # Find authorid and URL from... author url.
        author = a.find('a')
        self.story.setMetadata('authorId',author['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+author['href'])
        self.story.setMetadata('author',author.string)

        authorSoup = self.make_soup(self._fetchUrl(self.story.getMetadata('authorUrl')))

        chapter=soup.find('select',{'name':'chapter'}).findAll('option')

        for i in range(1,len(chapter)):
            ch=chapter[i]
            self.add_chapter(ch,ch['value'])


        # eFiction sites don't help us out a lot with their meta data
        # formating, so it's a little ugly.

        box=soup.find('div', {'class': "container borderridge"})
        sum=box.find('span').text
        self.setDescription(url,sum)

        boxes=soup.findAll('div', {'class': "container bordersolid"})
        for box in boxes:
            if box.find('b') != None and box.find('b').text == "History and Story Information":

                for b in box.findAll('b'):
                    if "words" in b.nextSibling:
                        self.story.setMetadata('numWords', b.text)
                    if "archived" in b.previousSibling:
                        self.story.setMetadata('datePublished', makeDate(stripHTML(b.text), self.dateformat))
                    if "updated" in b.previousSibling:
                        self.story.setMetadata('dateUpdated', makeDate(stripHTML(b.text), self.dateformat))
                    if "fandom" in b.nextSibling:
                        self.story.addToList('category', b.text)

                for br in box.findAll('br'):
                    br.replaceWith('split')
                genre=box.text.split("Genre:")[1].split("split")[0]
                if not "Unspecified" in genre:
                    self.story.addToList('genre',genre)


            if box.find('span') != None and box.find('span').text == "WARNING":

                rating=box.findAll('span')[1]
                rating.find('br').replaceWith('split')
                rating=rating.text.replace("This story is rated",'').split('split')[0]
                self.story.setMetadata('rating',rating)
                logger.debug(self.story.getMetadata('rating'))

                warnings=box.find('ol')
                if warnings != None:
                    warnings=warnings.text.replace(']', '').replace('[', '').split('  ')
                    for warning in warnings:
                        self.story.addToList('warnings',warning)


        for asoup in authorSoup.findAll('div', {'class':"story bordersolid"}):
            if asoup.find('a')['href'] == 'story.php?no='+self.story.getMetadata('storyId'):
                if '[ Completed ]' in asoup.text:
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')
                chars=asoup.findNext('div').text.split('Characters')[1].split(']')[0]
                for char in chars.split(','):
                    if not "None" in char:
                        self.story.addToList('characters',char)
                break



    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))

        div = soup.find('div',{'class':"chapter bordersolid"}).findNext('div').findNext('div')

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,div)
