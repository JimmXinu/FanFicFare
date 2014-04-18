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
            apiResponse = urllib2.urlopen("http://www.fimfiction.net/api/story.php?story=%s" % (self.story.getMetadata("storyId"))).read()
            apiData = json.loads(apiResponse)
            
            # Unfortunately, we still need to load the story index
            # page to parse the characters.  And chapters, now, too.
            data = self.do_fix_blockquotes(self._fetchUrl(self.url))
            soup = bs.BeautifulSoup(data)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e
        
        if "Warning: mysql_fetch_array(): supplied argument is not a valid MySQL result resource" in data:
            raise exceptions.StoryDoesNotExist(self.url)

        # Can cause problems if a missing story is referenced in a comment.
        # Shouldn't be needed anyway.
        # if "/images/missing_story.png" in data:
        #     raise exceptions.StoryDoesNotExist(self.url)
        
        if "This story has been marked as having adult content. Please click below to confirm you are of legal age to view adult material in your country." in data:
            raise exceptions.AdultCheckRequired(self.url)
        
        if self.password:
            params = {}
            params['password'] = self.password
            data = self._postUrl(self.url,params)

        if "Enter the password the author set for this story to view it." in data:
            if self.getConfig('fail_on_password'):
                raise exceptions.FailedToDownload("%s requires story password and fail_on_password is true."%self.url)
            else:
                raise exceptions.FailedToLogin(self.url,"Story requires individual password",passwdonly=True)
         
        if "Invalid story id" in apiData.values():
            raise exceptions.StoryDoesNotExist(self.url)
        
        storyMetadata = apiData["story"]    
            
        ## Title
        a = soup.find('a', href=re.compile(r'^/story/'+self.story.getMetadata('storyId')))
        self.story.setMetadata('title',stripHTML(a))
        
        # self.story.setMetadata("title", storyMetadata["title"])
        # if not storyMetadata["title"]:
        #     raise exceptions.FailedToDownload("%s doesn't have a title in the API.  This is a known fimfiction.net bug with titles containing ."%self.url)
        
        self.story.setMetadata("author", storyMetadata["author"]["name"])
        self.story.setMetadata("authorId", storyMetadata["author"]["id"])
        self.story.setMetadata("authorUrl", "http://%s/user/%s" % (self.getSiteDomain(), storyMetadata["author"]["name"]))

        # chapters = [{"chapterTitle": chapter["title"], "chapterURL": chapter["link"]} for chapter in storyMetadata["chapters"]]
        
        # ## this is bit of a kludge based on the assumption all the
        # ## 'bad' chapters will be at the end.
        # ## limit down to the number of chapters reported by chapter_count.
        # chapters = chapters[:storyMetadata["chapter_count"]] 
        
        # for chapter in chapters:
        #     self.chapterUrls.append((chapter["chapterTitle"], chapter["chapterURL"]))
        # self.story.setMetadata("numChapters", len(self.chapterUrls))

        for chapter in soup.findAll('a',{'class':'chapter_link'}):
            self.chapterUrls.append((stripHTML(chapter), 'http://'+self.host+chapter['href']))

        self.story.setMetadata('numChapters',len(self.chapterUrls))
            
        # In the case of fimfiction.net, possible statuses are 'Completed', 'Incomplete', 'On Hiatus' and 'Cancelled'
        # For the sake of bringing it in line with the other adapters, 'Incomplete' becomes 'In-Progress'
        # and 'Complete' beomes 'Completed'. 'Cancelled' seems an important enough (not to mention more strictly true) 
        # status to leave unchanged.
        # Nov2012 - 'On Hiatus' is now passed, too.  It's easy now for users to change/remove if they want
        # with replace_metadata
        status = storyMetadata["status"].replace("Incomplete", "In-Progress").replace("Complete", "Completed")
        self.story.setMetadata("status", status)
        self.story.setMetadata("rating", storyMetadata["content_rating_text"])

        ## Warnings aren't included in the API.
        bottomli = soup.find('li',{'class':'bottom'})
        if bottomli:
            bottomspans = bottomli.findAll('span')
            # the first span in bottom is the rating, obtained above.
            if bottomspans and len(bottomspans) > 1:
                for warning in bottomspans[1:]:
                    self.story.addToList('warnings',warning.string)
                
        
        for category in storyMetadata["categories"]:
            if storyMetadata["categories"][category]:
                self.story.addToList("genre", category) 

        self.story.setMetadata("numWords", str(storyMetadata["words"]))
        
        # fimfic is the first site with an explicit cover image.
        if "image" in storyMetadata.keys():
            if "full_image" in storyMetadata:
                coverurl = storyMetadata["full_image"]
            else:
                coverurl = storyMetadata["image"]
            if coverurl.startswith('//'): # fix for img urls missing 'http:'
                coverurl = "http:"+coverurl

            self.setCoverImage(self.url,coverurl)

        # fimf has started including extra stuff inside the description div.
        descdivstr = "%s"%soup.find("div", {"class":"description"})
        hrstr="<hr />"
        descdivstr = '<div class="description">'+descdivstr[descdivstr.index(hrstr)+len(hrstr):]
        self.setDescription(self.url,descdivstr)

        # Can't trust dates from API anymore I'm told.
        # Dates are in Unix time
        # Take the publish date from the first chapter posted
        # rawDatePublished = storyMetadata["chapters"][0]["date_modified"]
        # self.story.setMetadata("datePublished", datetime.fromtimestamp(rawDatePublished))
        # rawDateUpdated = storyMetadata["date_modified"]
        # self.story.setMetadata("dateUpdated", datetime.fromtimestamp(rawDateUpdated))
        
        oldestChapter = None
        newestChapter = None
        self.newestChapterNum = None # save for comparing during update.
        # Scan all chapters to find the oldest and newest, on
        # FiMFiction it's possible for authors to insert new chapters
        # out-of-order or change the dates of earlier ones by editing
        # them--That WILL break epub update.
        for index, chapterDate in enumerate(soup.findAll('span', {'class':'date'})):
            date=re.sub(r"(\d+)(st|nd|rd|th)",r"\1",chapterDate.contents[1].strip())
            chapterDate = makeDate(date,self.dateformat)
            if oldestChapter == None or chapterDate < oldestChapter:
                oldestChapter = chapterDate
            if newestChapter == None or chapterDate > newestChapter:
                newestChapter = chapterDate
                self.newestChapterNum = index

        self.story.setMetadata("dateUpdated", newestChapter)
        
        pubdatetag = soup.find('span', {'class':'date_approved'})
        if pubdatetag is None:
            self.story.setMetadata("datePublished", oldestChapter)            
        else:
            pubdateraw = pubdatetag('span')[1].text
            datestripped=re.sub(r"(\d+)(st|nd|rd|th)",r"\1",pubdateraw.strip())
            pubDate = makeDate(datestripped,self.dateformat)
            self.story.setMetadata("datePublished", pubDate)
            
        chars = soup.find("div", {"class":"inner_data"})
        # fimfic stopped putting the char name on or around the char
        # icon now for some reason.  Pull it from the image name with
        # some heuristics.
        for character in [character_icon["src"] for character_icon in chars.findAll("img", {"class":"character_icon"})]:
            # //static.fimfiction.net/images/characters/twilight_sparkle.png
            # 5th split /, remove last four, replace _, capitolize every word(title())
            char = character.split('/')[5][:-4].replace('_',' ').title()
            if char == 'Oc':
                char = "OC"
            if char == 'Cmc':
                char = "Cutie Mark Crusaders"
            self.story.addToList("characters", char)
            
        # extra site specific metadata
        extralist = ["likes","dislikes","views","total_views","short_description"]
        for metakey in extralist:
            if metakey in storyMetadata:
                value = storyMetadata[metakey]
                if not isinstance(value,basestring):
                    value = unicode(value)
                self.story.setMetadata(metakey, value)

        ## Groups and sequels code from FaceDeer
        allGroupLists = soup.findAll('ul', {'id':'story_group_list'})
        for groupList in allGroupLists:
            for groupName in groupList.findAll('a', {'href':re.compile('^/group/')}):
                self.story.addToList("groupsUrl", 'http://'+self.host+groupName["href"]) 
                self.story.addToList("groups",stripHTML(groupName).replace(',', ';'))

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

        data = self.do_fix_blockquotes(self._fetchUrl(url))
        soup = bs.BeautifulSoup(data,selfClosingTags=('br','hr')).find('div', {'class' : 'chapter_content'})
        if soup == None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
        return self.utf8FromSoup(url,soup)
        
