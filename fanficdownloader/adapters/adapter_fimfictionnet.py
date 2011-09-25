# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team
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

import time
import logging
import re
import urllib2
from datetime import datetime

import fanficdownloader.BeautifulSoup as bs
from fanficdownloader.htmlcleanup import stripHTML
import fanficdownloader.exceptions as exceptions

from base_adapter import BaseSiteAdapter, utf8FromSoup, makeDate

def getClass():
    return FimFictionNetSiteAdapter

class FimFictionNetSiteAdapter(BaseSiteAdapter):
    
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','fimficnet')
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])
        self._setURL("http://"+self.getSiteDomain()+"/story/"+self.story.getMetadata('storyId')+"/")
    
    @staticmethod
    def getSiteDomain():
        return 'www.fimfiction.net'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.fimfiction.net','mobile.fimfiction.net', 'www.fimfiction.com']

    def getSiteExampleURLs(self):
        return "http://www.fimfiction.net/story/1234/story-title-here http://www.fimfiction.net/story/1234/ http://www.fimfiction.com/story/1234/ http://mobile.fimfiction.net/story/1234/"

    def getSiteURLPattern(self):
        return r"http://(www|mobile)\.fimfiction\.(net|com)/story/\d+/?.*"
        
    def extractChapterUrlsAndMetadata(self):
        
        try:
            data = self._fetchUrl(self.url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e
        
        if "Warning: mysql_fetch_array(): supplied argument is not a valid MySQL result resource" in data:
            raise exceptions.StoryDoesNotExist(self.url)
        
        soup = bs.BeautifulSoup(data).find("div", {"class":"content_box post_content_box"})
        
        title, author = [link.text for link in soup.find("h2").findAll("a")]
        self.story.setMetadata("title", title)
        self.story.setMetadata("author", author)
        self.story.setMetadata("authorId", author) # The author's name will be unique
        self.story.setMetadata("authorUrl", "http://%s/user/%s" % (self.getSiteDomain(),author))
        
        self.chapterUrls = [(chapter.text, "http://"+self.getSiteDomain() + chapter['href']) for chapter in soup.findAll("a", "chapter_link")]
        
        self.story.setMetadata('numChapters',len(self.chapterUrls))
        
        for character in [character_icon['title'] for character_icon in soup.findAll("a", {"class":"character_icon"})]:
            self.story.addToList("category", character)
        for category in [category.text for category in soup.find("div", {"class":"categories"}).findAll("a")]:
            self.story.addToList("category", category)
        self.story.addToList("category", "My Little Pony")
        
        
        # The very last list element in the list of chapters contains the status, rating and word count e.g.:
        #
        #    <li>
        #       Incomplete | Rating:
        #       <span style="color:#c78238;">Teen</span>
        #       <div class="word_count"><b>5,203</b>words total</div>
        #    </li>
        #

        status_bar = soup.findAll('li')[-1]
        self.story.setMetadata('status', status_bar.text.split("|")[0].strip())
        self.story.setMetadata('rating', status_bar.span.text)
        self.story.setMetadata('numWords', status_bar.div.b.text)
        
        description_soup = soup.find("div", {"class":"description"})
        # Sometimes the description has an expanding element
        # This removes the ellipsis and the expand button
        try:
            description_soup.span.extract()
            description_soup.a.extract()
        except:
            pass
        self.story.setMetadata('description', description_soup.text)
        
        # Unfortunately, nowhere on the page is the year mentioned. Because we would much rather update the story needlessly
        # than miss an update, we hardcode the year of creation to be 2011 (when the site was created) and the year in which
        # the story was updated to the current one. Nevertheless, it may be prudent to always force an update in defaults.ini

        # Get the date of creation from the first chapter
        datePublished_soup = bs.BeautifulSoup(self._fetchUrl(self.chapterUrls[0][1])).find("div", {"class":"calendar"})
        datePublished_soup.find('span').extract()
        datePublished = makeDate("2011"+datePublished_soup.text, "%Y%b%d")
        self.story.setMetadata("datePublished", datePublished)
        dateUpdated_soup = bs.BeautifulSoup(data).find("div", {"class":"calendar"})
        dateUpdated_soup.find('span').extract()
        dateUpdated = makeDate(str(datetime.now().year)+dateUpdated_soup.text, "%Y%b%d")
        self.story.setMetadata("dateUpdated", dateUpdated)
        
    def getChapterText(self, url):
        logging.debug('Getting chapter text from: %s' % url)
        soup = bs.BeautifulSoup(self._fetchUrl(url),selfClosingTags=('br','hr')).find('div', {'id' : 'chapter_container'})
        if soup == None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
        return utf8FromSoup(soup)
        