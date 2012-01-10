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
import cookielib as cl

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter, utf8FromSoup, makeDate

def getClass():
    return FimFictionNetSiteAdapter

class FimFictionNetSiteAdapter(BaseSiteAdapter):
    
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','fimficnet')
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])
        self._setURL("http://"+self.getSiteDomain()+"/story/"+self.story.getMetadata('storyId')+"/")
        self.is_adult = False
        
    @staticmethod
    def getSiteDomain():
        return 'www.fimfiction.net'

    @classmethod
    def getAcceptDomains(cls):
        # mobile.fimifction.com isn't actually a valid domain, but we can still get the story id from URLs anyway
        return ['www.fimfiction.net','mobile.fimfiction.net', 'www.fimfiction.com', 'mobile.fimfiction.com']

    def getSiteExampleURLs(self):
        return "http://www.fimfiction.net/story/1234/story-title-here http://www.fimfiction.net/story/1234/ http://www.fimfiction.com/story/1234/1/ http://mobile.fimfiction.net/story/1234/1/story-title-here/chapter-title-here"

    def getSiteURLPattern(self):
        return r"http://(www|mobile)\.fimfiction\.(net|com)/story/\d+/?.*"
        
    def extractChapterUrlsAndMetadata(self):
        
        if self.is_adult or self.getConfig("is_adult"):
            cookieproc = urllib2.HTTPCookieProcessor()
            cookie = cl.Cookie(version=0, name='view_mature', value='true',
                               port=None, port_specified=False,
                               domain=self.getSiteDomain(), domain_specified=False, domain_initial_dot=False,
                               path='/story', path_specified=True,
                               secure=False,
                               expires=time.time()+10000,
                               discard=False,
                               comment=None,
                               comment_url=None,
                               rest={'HttpOnly': None},
                               rfc2109=False)
            cookieproc.cookiejar.set_cookie(cookie)
            self.opener = urllib2.build_opener(cookieproc)
        
        try:
            data = self._fetchUrl(self.url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e
        
        if "Warning: mysql_fetch_array(): supplied argument is not a valid MySQL result resource" in data:
            raise exceptions.StoryDoesNotExist(self.url)
        
        if "This story has been marked as having adult content." in data:
            raise exceptions.AdultCheckRequired(self.url)
        
        soup = bs.BeautifulSoup(data).find("div", {"class":"content_box post_content_box"})

        titleheader = soup.find("h2")
        title = titleheader.find("a", href=re.compile(r'^/story/')).text
        author = titleheader.find("a", href=re.compile(r'^/user/')).text
        self.story.setMetadata("title", title)
        self.story.setMetadata("author", author)
        self.story.setMetadata("authorId", author) # The author's name will be unique
        self.story.setMetadata("authorUrl", "http://%s/user/%s" % (self.getSiteDomain(),author))
        
        chapterDates = []

        for chapter in soup.findAll("a", {"class":"chapter_link"}):
            chapterDates.append(chapter.span.extract().text.strip("()"))
            self.chapterUrls.append((chapter.text.strip(), "http://"+self.getSiteDomain() + chapter['href']))
        
        self.story.setMetadata('numChapters',len(self.chapterUrls))
        
        for character in [character_icon['title'] for character_icon in soup.findAll("a", {"class":"character_icon"})]:
            self.story.addToList("characters", character)
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
        # In the case of fimfiction.net, possible statuses are 'Completed', 'Incomplete', 'On Hiatus' and 'Cancelled'
        # For the sake of bringing it in line with the other adapters, 'Incomplete' and 'On Hiatus' become 'In-Progress'
        # and 'Complete' beomes 'Completed'. 'Cancelled' seems an important enough (not to mention more strictly true) 
        # status to leave unchanged.
        status = status_bar.text.split("|")[0].strip().replace("Incomplete", "In-Progress").replace("On Hiatus", "In-Progress").replace("Complete", "Completed")
        self.story.setMetadata('status', status)
        self.story.setMetadata('rating', status_bar.span.text)
        # This way is less elegant, perhaps, but more robust in face of format changes.
        numWords = status_bar.find("div",{"class":"word_count"}).b.text
        self.story.setMetadata('numWords', numWords)
        
        description_soup = soup.find("div", {"class":"description"})
        # Sometimes the description has an expanding element
        # This removes the ellipsis and the expand button
        try:
            description_soup.find('span', {"id":re.compile(r"description_more_elipses_\d+")}).extract() # Web designer can't spell 'ellipsis'
            description_soup.find('a', {"class":"more"}).extract()
        except:
            pass
        self.story.setMetadata('description', description_soup.text)
        
        # Unfortunately, nowhere on the page is the year mentioned. Because we would much rather update the story needlessly
        # than miss an update, we hardcode the year of creation and update to be 2011.

        # Get the date of creation from the first chapter
        datePublished_text = chapterDates[0]
        day, month = datePublished_text.split()
        day = re.sub(r"[^\d.]+", '', day)
        datePublished = makeDate("2011"+month+day, "%Y%b%d")
        self.story.setMetadata("datePublished", datePublished)
        dateUpdated_soup = bs.BeautifulSoup(data).find("div", {"class":"calendar"})
        dateUpdated_soup.find('span').extract()
        dateUpdated = makeDate("2011"+dateUpdated_soup.text, "%Y%b%d")
        self.story.setMetadata("dateUpdated", dateUpdated)
        
    def getChapterText(self, url):
        logging.debug('Getting chapter text from: %s' % url)
        soup = bs.BeautifulSoup(self._fetchUrl(url),selfClosingTags=('br','hr')).find('div', {'id' : 'chapter_container'})
        if soup == None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
        return utf8FromSoup(soup)
        
