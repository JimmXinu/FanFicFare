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
logger = logging.getLogger(__name__)
import re
import urllib2
import cookielib as cl
import json

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return FimFictionNetSiteAdapter

class FimFictionNetSiteAdapter(BaseSiteAdapter):
    
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','fimficnet')
        self.story.setMetadata('storyId', self.parsedUrl.path.split('/',)[2])
        self._setURL("http://"+self.getSiteDomain()+"/story/"+self.story.getMetadata('storyId')+"/")
        self.is_adult = False
        
        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d %b %Y"
            
    @staticmethod
    def getSiteDomain():
        return 'www.fimfiction.net'

    @classmethod
    def getAcceptDomains(cls):
        # mobile.fimifction.com isn't actually a valid domain, but we can still get the story id from URLs anyway
        return ['www.fimfiction.net','mobile.fimfiction.net', 'www.fimfiction.com', 'mobile.fimfiction.com']

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://www.fimfiction.net/story/1234/story-title-here http://www.fimfiction.net/story/1234/ http://www.fimfiction.com/story/1234/1/ http://mobile.fimfiction.net/story/1234/1/story-title-here/chapter-title-here"

    def getSiteURLPattern(self):
        return r"https?://(www|mobile)\.fimfiction\.(net|com)/story/\d+/?.*"
        
    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True
    
    def doExtractChapterUrlsAndMetadata(self,get_cover=True):
        
        if self.is_adult or self.getConfig("is_adult"):
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
            self.cookiejar.set_cookie(cookie)

        ##---------------------------------------------------------------------------------------------------
        ## Get the story's title page. Check if it exists.

        try:
            data = self.do_fix_blockquotes(self._fetchUrl(self.url))
            soup = bs.BeautifulSoup(data)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e
        
        if "Warning: mysql_fetch_array(): supplied argument is not a valid MySQL result resource" in data:
            raise exceptions.StoryDoesNotExist(self.url)

        if "This story has been marked as having adult content. Please click below to confirm you are of legal age to view adult material in your country." in data:
            raise exceptions.AdultCheckRequired(self.url)
        
        if self.password:
            params = {}
            params['password'] = self.password
            data = self._postUrl(self.url, params)
            soup = bs.BeautifulSoup(data)

        if not (soup.find('form', {'id' : 'password_form'}) == None):
            if self.getConfig('fail_on_password'):
                raise exceptions.FailedToDownload("%s requires story password and fail_on_password is true."%self.url)
            else:
                raise exceptions.FailedToLogin(self.url,"Story requires individual password",passwdonly=True)

        ##----------------------------------------------------------------------------------------------------
        ## Extract metadata

        storyContentBox = soup.find('div', {'class':'story_content_box'})

        # Title
        title = storyContentBox.find('a', {'class':re.compile(r'.*\bstory_name\b.*')})
        self.story.setMetadata('title',stripHTML(title))

        # Author
        author = storyContentBox.find('span', {'class':'author'})
        self.story.setMetadata("author", stripHTML(author))
        #No longer seems to be a way to access Fimfiction's internal author ID
        self.story.setMetadata("authorId", self.story.getMetadata("author"))
        self.story.setMetadata("authorUrl", "http://%s/user/%s" % (self.getSiteDomain(), stripHTML(author)))

        #Rating text is replaced with full words for historical compatibility after the site changed
        #on 2014-10-27
        rating = stripHTML(storyContentBox.find('a', {'class':re.compile(r'.*\bcontent-rating-.*')}))
        rating = rating.replace("E", "Everyone").replace("T", "Teen").replace("M", "Mature")
        self.story.setMetadata("rating", rating)

        # Chapters
        for chapter in storyContentBox.findAll('a',{'class':'chapter_link'}):
            self.chapterUrls.append((stripHTML(chapter), 'http://'+self.host+chapter['href']))

        self.story.setMetadata('numChapters',len(self.chapterUrls))

        # Status
        # In the case of Fimfiction, possible statuses are 'Completed', 'Incomplete', 'On Hiatus' and 'Cancelled'
        # For the sake of bringing it in line with the other adapters, 'Incomplete' becomes 'In-Progress'
        # and 'Complete' becomes 'Completed'. 'Cancelled' and 'On Hiatus' are passed through, it's easy now for users
        # to change/remove if they want with replace_metadata
        status = stripHTML(storyContentBox.find('span', {'class':re.compile(r'.*\bcompleted-status-.*')}))
        status = status.replace("Incomplete", "In-Progress").replace("Complete", "Completed")
        self.story.setMetadata("status", status)

        # Genres and Warnings
        # warnings were folded into general categories in the 2014-10-27 site update
        categories = storyContentBox.findAll('a', {'class':re.compile(r'.*\bstory_category\b.*')})
        for category in categories:
            category = stripHTML(category)
            if category == "Gore" or category == "Sex":
                self.story.addToList('warnings', category)
            else:
                self.story.addToList('genre', category)

        # Word count
        wordCountText = stripHTML(storyContentBox.find('li', {'class':'bottom'}).find('div', {'class':'word_count'}))
        self.story.setMetadata("numWords", re.sub(r'[^0-9]', '', wordCountText))

        # Cover image
        storyImage = storyContentBox.find('div', {'class':'story_image'})
        if storyImage:
            coverurl = storyImage.find('a')['href']
            if coverurl.startswith('//'): # fix for img urls missing 'http:'
                coverurl = "http:"+coverurl
            if get_cover:
                self.setCoverImage(self.url,coverurl)

            coverSource = storyImage.find('a', {'class':'source'})
            if coverSource:
                self.story.setMetadata('coverSourceUrl', coverSource['href'])
                #There's no text associated with the cover source link, so just
                #reuse the URL. Makes it clear it's an external link leading
                #outside of the fanfic site, at least.
                self.story.setMetadata('coverSource', coverSource['href'])

        # fimf has started including extra stuff inside the description div.
        descdivstr = u"%s"%storyContentBox.find("div", {"class":"description"})
        hrstr=u"<hr />"
        descdivstr = u'<div class="description">'+descdivstr[descdivstr.index(hrstr)+len(hrstr):]
        self.setDescription(self.url,descdivstr)

        # Find the newest and oldest chapter dates
        storyData = storyContentBox.find('div', {'class':'story_data'})
        oldestChapter = None
        newestChapter = None
        self.newestChapterNum = None # save for comparing during update.
        # Scan all chapters to find the oldest and newest, on
        # FiMFiction it's possible for authors to insert new chapters
        # out-of-order or change the dates of earlier ones by editing
        # them--That WILL break epub update.
        for index, chapterDate in enumerate(storyData.findAll('span', {'class':'date'})):
            dateString=re.sub(r"(\d+)(st|nd|rd|th)",r"\1",chapterDate.contents[1].strip())
            chapterDate = makeDate(dateString,self.dateformat)
            if oldestChapter == None or chapterDate < oldestChapter:
                oldestChapter = chapterDate
            if newestChapter == None or chapterDate > newestChapter:
                newestChapter = chapterDate
                self.newestChapterNum = index

        # Date updated
        self.story.setMetadata("dateUpdated", newestChapter)

        # Date published
        # falls back to oldest chapter date for stories that haven't been officially published yet
        pubdatetag = storyContentBox.find('span', {'class':'date_approved'})
        if pubdatetag is None:
            self.story.setMetadata("datePublished", oldestChapter)            
        else:
            pubdateraw = pubdatetag('span')[1].text
            datestripped=re.sub(r"(\d+)(st|nd|rd|th)",r"\1",pubdateraw.strip())
            pubDate = makeDate(datestripped,self.dateformat)
            self.story.setMetadata("datePublished", pubDate)

        # Characters
        chars = storyContentBox.find("div", {"class":"extra_story_data"})
        for character in chars.findAll("a", {"class":"character_icon"}):
            self.story.addToList("characters", character['title'])

        # Likes and dislikes
        storyToolbar = soup.find('div', {'class':'story-toolbar'})
        likes = storyToolbar.find('span', {'class':'likes'})
        if not likes is None:
            self.story.setMetadata("likes", stripHTML(likes))
        dislikes = storyToolbar.find('span', {'class':'dislikes'})
        if not dislikes is None:
            self.story.setMetadata("dislikes", stripHTML(dislikes))

        # Highest view for a chapter and total views
        viewSpan = storyToolbar.find('span', {'title':re.compile(r'.*\btotal views\b.*')})
        self.story.setMetadata("views", re.sub(r'[^0-9]', '', stripHTML(viewSpan)))
        self.story.setMetadata("total_views", re.sub(r'[^0-9]', '', viewSpan['title']))

        # Comment count
        commentSpan = storyToolbar.find('span', {'title':re.compile(r'.*\bcomments\b.*')})
        self.story.setMetadata("comment_count", re.sub(r'[^0-9]', '', stripHTML(commentSpan)))

        # Short description
        descriptionMeta = soup.find('meta', {'property':'og:description'})
        self.story.setMetadata("short_description", stripHTML(descriptionMeta['content']))

        #groups
        if soup.find('button', {'id':'button-view-all-groups'}):
            groupResponse = self._fetchUrl("http://www.fimfiction.net/ajax/groups/story_groups_list.php?story=%s" % (self.story.getMetadata("storyId")))
            groupData = json.loads(groupResponse)
            groupList = bs.BeautifulSoup(groupData["content"])
        else:
            groupList = soup.find('ul', {'id':'story-groups-list'})

        if not (groupList == None):
            for groupName in groupList.findAll('a'):
                self.story.addToList("groupsUrl", 'http://'+self.host+groupName["href"]) 
                self.story.addToList("groups",stripHTML(groupName).replace(',', ';'))

        #sequels
        sequelStoryHeader = soup.find('h1', {'class':'header-stories'}, text="Sequels")
        if not sequelStoryHeader == None:
            sequelContainer = sequelStoryHeader.parent.parent
            for sequel in sequelContainer.findAll('a', {'class':'story_link'}):
                self.story.addToList("sequelsUrl", 'http://'+self.host+sequel["href"]) 
                self.story.addToList("sequels", stripHTML(sequel).replace(',', ';'))
                
        #The link to the prequel is embedded in the description text, so erring
        #on the side of caution and wrapping this whole thing in a try block.
        #If anything goes wrong this probably wasn't a valid prequel link.
        try:
            description = soup.find('div', {'class':'description'})
            firstHR = description.find("hr")
            nextSib = firstHR.nextSibling
            if "This story is a sequel to" in nextSib.string:
                link = nextSib.nextSibling
                if link.name == "a":
                    self.story.setMetadata("prequelUrl", 'http://'+self.host+link["href"])
                    self.story.setMetadata("prequel", stripHTML(link))
        except:
            pass
        
    def hookForUpdates(self,chaptercount):
        if self.oldchapters and len(self.oldchapters) > self.newestChapterNum:
            print("Existing epub has %s chapters\nNewest chapter is %s.  Discarding old chapters from there on."%(len(self.oldchapters), self.newestChapterNum+1))
            self.oldchapters = self.oldchapters[:self.newestChapterNum]
        return len(self.oldchapters)

    def do_fix_blockquotes(self,data):
        if self.getConfig('fix_fimf_blockquotes'):
            # <p class="double"><blockquote>
            # </blockquote></p>
            # include > in re groups so there's always something in the group.
            data = re.sub(r'<p([^>]*>\s*)<blockquote([^>]*>)',r'<blockquote\2<p\1',data)
            data = re.sub(r'</blockquote(>\s*)</p>',r'</p\1</blockquote>',data)
        return data
        
    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)

        data = self._fetchUrl(url)

        soup = bs.BeautifulSoup(data)
        if not (soup.find('form', {'id' : 'password_form'}) == None):
            if self.password:
                params = {}
                params['password'] = self.password
                data = self._postUrl(url, params)
            else:
                print("Chapter %s needed password but no password was present" % url)

        data = self.do_fix_blockquotes(data)

        soup = bs.BeautifulSoup(data,selfClosingTags=('br','hr')).find('div', {'class' : 'chapter_content'})
        if soup == None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,soup)
