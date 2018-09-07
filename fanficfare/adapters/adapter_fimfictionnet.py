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
import time
from datetime import date, datetime
import logging
logger = logging.getLogger(__name__)
import re
import json

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError
from ..six.moves import http_cookiejar as cl

from .base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return FimFictionNetSiteAdapter

class FimFictionNetSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','fimficnet')
        self.story.setMetadata('storyId', self.parsedUrl.path.split('/',)[2])
        self._setURL("https://"+self.getSiteDomain()+"/story/"+self.story.getMetadata('storyId')+"/")
        self.is_adult = False

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        # FYI, not the only format used in this file.
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
        return "https://www.fimfiction.net/story/1234/story-title-here https://www.fimfiction.net/story/1234/ https://www.fimfiction.com/story/1234/1/ https://mobile.fimfiction.net/story/1234/1/story-title-here/chapter-title-here"

    def getSiteURLPattern(self):
        return r"https?://(www|mobile)\.fimfiction\.(net|com)/story/\d+/?.*"

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    def set_adult_cookie(self):
        cookie = cl.Cookie(version=0, name='view_mature', value='true',
                           port=None, port_specified=False,
                           domain=self.getSiteDomain(), domain_specified=False, domain_initial_dot=False,
                           path='/', path_specified=True,
                           secure=False,
                           expires=time.time()+10000,
                           discard=False,
                           comment=None,
                           comment_url=None,
                           rest={'HttpOnly': None},
                           rfc2109=False)
        self.get_configuration().get_cookiejar().set_cookie(cookie)

    def performLogin(self, url):
        params = {}
        if self.password:
            params['username'] = self.username
            params['password'] = self.password
        else:
            params['username'] = self.getConfig("username")
            params['password'] = self.getConfig("password")
        params['keep_logged_in'] = '1'

        if params['username'] and params['password']:
            loginUrl = 'https://' + self.getSiteDomain() + '/ajax/login'
            logger.info("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                                params['username']))
            d = self._postUrl(loginUrl, params)
            if "signing_key" not in d :
                logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                                 params['username']))
                raise exceptions.FailedToLogin(url,params['username'])

    def doExtractChapterUrlsAndMetadata(self,get_cover=True):

        if self.is_adult or self.getConfig("is_adult"):
            self.set_adult_cookie()

        ## Only needed with password protected stories, which you have
        ## to have logged into in the website using this account.
        self.performLogin(self.url)

        ##---------------------------------------------------------------------------------------------------
        ## Get the story's title page. Check if it exists.

        try:
            # don't use cache if manual is_adult--should only happen
            # if it's an adult story and they don't have is_adult in ini.
            data = self.do_fix_blockquotes(self._fetchUrl(self.url,
                                                          usecache=(not self.is_adult)))
            soup = self.make_soup(data)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        if "Warning: mysql_fetch_array(): supplied argument is not a valid MySQL result resource" in data:
            raise exceptions.StoryDoesNotExist(self.url)

        if "This story has been marked as having adult content. Please click below to confirm you are of legal age to view adult material in your country." in data:
            raise exceptions.AdultCheckRequired(self.url)

        ##----------------------------------------------------------------------------------------------------
        ## Extract metadata

        storyContentBox = soup.find('div', {'class':'story_content_box'})

        # Title
        title = storyContentBox.find('a', {'class':re.compile(r'.*\bstory_name\b.*')})
        self.story.setMetadata('title',stripHTML(title))

        # Author
        author = soup.find('div', {'class':'info-container'}).find('a')
        self.story.setMetadata("author", stripHTML(author))
        # /user/288866/Stryker-Shadowpony-Blade
        self.story.setMetadata("authorId", author['href'].split('/')[2])
        self.story.setMetadata("authorUrl", "https://%s/user/%s/%s" % (self.getSiteDomain(),
                                                                       self.story.getMetadata('authorId'),
                                                                       self.story.getMetadata('author')))

        #Rating text is replaced with full words for historical compatibility after the site changed
        #on 2014-10-27
        rating = stripHTML(storyContentBox.find('a', {'class':re.compile(r'.*\bcontent-rating-.*')}))
        rating = rating.replace("E", "Everyone").replace("T", "Teen").replace("M", "Mature")
        self.story.setMetadata("rating", rating)

        # Chapters
        for chapter in soup.find('ul',{'class':'chapters'}).find_all('a',{'class':'chapter-title'}):
            self.add_chapter(chapter, 'https://'+self.host+chapter['href'])


        # Status
        # In the case of Fimfiction, possible statuses are 'Completed', 'Incomplete', 'On Hiatus' and 'Cancelled'
        # For the sake of bringing it in line with the other adapters, 'Incomplete' becomes 'In-Progress'
        # and 'Complete' becomes 'Completed'. 'Cancelled' and 'On Hiatus' are passed through, it's easy now for users
        # to change/remove if they want with replace_metadata
        status = stripHTML(storyContentBox.find('span', {'class':re.compile(r'.*\bcompleted-status-.*')}))
        status = status.replace("Incomplete", "In-Progress").replace("Complete", "Completed")
        self.story.setMetadata("status", status)

        # Word count
        wordCountText = stripHTML(storyContentBox.find('div', {'class':'chapters-footer'}).find('div', {'class':'word_count'}))
        self.story.setMetadata("numWords", re.sub(r'[^0-9]', '', wordCountText))

        # Cover image
        if get_cover:
            storyImage = storyContentBox.find('img', {'class':'lazy-img'})
            if storyImage:
                coverurl = storyImage['data-fullsize']
                # try setting from data-fullsize, if fails, try using data-src
                if self.setCoverImage(self.url,coverurl)[0] == "failedtoload":
                    coverurl = storyImage['data-src']
                    self.setCoverImage(self.url,coverurl)

                coverSource = storyImage.parent.find('a', {'class':'source'})
                if coverSource:
                    self.story.setMetadata('coverSourceUrl', coverSource['href'])
                    # There's no text associated with the cover source
                    # link, so just reuse the URL. Makes it clear it's
                    # an external link leading outside of the fanfic
                    # site, at least.
                    self.story.setMetadata('coverSource', coverSource['href'])

        # fimf has started including extra stuff inside the description div.
        # specifically, the prequel link
        description = storyContentBox.find("span", {"class":"description-text"})
        description.name='div' # change to div, technically, spans
                               # aren't supposed to contain <p>'s.
        descdivstr = u"%s"%description # string, but not stripHTML'ed
        #The link to the prequel is embedded in the description text, so erring
        #on the side of caution and wrapping this whole thing in a try block.
        #If anything goes wrong this probably wasn't a valid prequel link.
        try:
            if "This story is a sequel to" in stripHTML(description):
                link = description.find('a') # assume first link.
                self.story.setMetadata("prequelUrl", 'https://'+self.host+link["href"])
                self.story.setMetadata("prequel", stripHTML(link))
                if not self.getConfig('keep_prequel_in_description',False):
                    hrstr=u"<hr/>"
                    descdivstr = u'<div class="description">'+descdivstr[descdivstr.index(hrstr)+len(hrstr):]
        except:
            logger.info("Prequel parsing failed...")
        self.setDescription(self.url,descdivstr)

        # Find the newest and oldest chapter dates
        storyData = storyContentBox.find('ul', {'class':'chapters'})
        oldestChapter = None
        newestChapter = None
        self.newestChapterNum = None # save for comparing during update.
        # Scan all chapters to find the oldest and newest, on
        # FiMFiction it's possible for authors to insert new chapters
        # out-of-order or change the dates of earlier ones by editing
        # them--That WILL break epub update.
        for index, chapterDate in enumerate(storyData.find_all('span', {'class':'date'})):
            chapterDate = self.ordinal_date_string_to_date(chapterDate.contents[1])
            if oldestChapter == None or chapterDate < oldestChapter:
                oldestChapter = chapterDate
            if newestChapter == None or chapterDate > newestChapter:
                newestChapter = chapterDate
                self.newestChapterNum = index

        if newestChapter is None:
            #this will only be true when updating metadata for stories that have 0 chapters
            #there is a "last modified" date given on the page, extract it and use that.
            moddatetag = storyContentBox.find('span', {'class':'last_modified'})
            if not moddatetag is None:
                newestChapter = self.ordinal_date_string_to_date(moddatetag('span')[1].text)

        # Date updated
        self.story.setMetadata("dateUpdated", newestChapter)

        # Date published
        # falls back to oldest chapter date for stories that haven't been officially published yet
        pubdatetag = storyContentBox.find('span', {'class':'approved-date'})
        if pubdatetag is None:
            if oldestChapter is None:
                #this will only be true when updating metadata for stories that have 0 chapters
                #and that have never been officially published - a rare occurrence. Fall back to last
                #modified date as the publication date, it's all that we've got.
                self.story.setMetadata("datePublished", newestChapter)
            else:
                self.story.setMetadata("datePublished", oldestChapter)
        else:
            pubDate = self.date_span_tag_to_date(pubdatetag)
            self.story.setMetadata("datePublished", pubDate)

        # Characters
        tags = storyContentBox.find("ul", {"class":"story-tags"})
        for character in tags.find_all("a", {"class":"tag-character"}):
            self.story.addToList("characters", stripHTML(character))
        for genre in tags.find_all("a", {"class":"tag-genre"}):
            self.story.addToList("genre", stripHTML(genre))
        for series in tags.find_all("a", {"class":"tag-series"}):
            #using 'fandoms' as the identifier to standardize with archiveofourown.org
            self.story.addToList("fandoms", stripHTML(series))
        for warning in tags.find_all("a", {"class":"tag-warning"}):
            self.story.addToList("warnings", stripHTML(warning))
        for content in tags.find_all("a", {"class":"tag-content"}):
            self.story.addToList("content", stripHTML(content))

        # Likes and dislikes
        storyToolbar = soup.find('div', {'class':'story-top-toolbar'})
        likes = storyToolbar.find('span', {'class':'likes'})
        if not likes is None:
            self.story.setMetadata("likes", stripHTML(likes))
        dislikes = storyToolbar.find('span', {'class':'dislikes'})
        if not dislikes is None:
            self.story.setMetadata("dislikes", stripHTML(dislikes))

        # Highest view for a chapter and total views
        viewSpan = storyToolbar.find('span', {'title':re.compile(r'.*\btotal views\b.*')})
        viewResults = re.search('([0-9]*) views \/ ([0-9]*)', viewSpan['title'].replace(',',''))
        self.story.setMetadata("views", viewResults.group(1))
        self.story.setMetadata("total_views", viewResults.group(2))

        # Comment count
        commentSpan = storyToolbar.find('span', {'title':re.compile(r'.*\bcomments\b.*')})
        self.story.setMetadata("comment_count", re.sub(r'[^0-9]', '', stripHTML(commentSpan)))

        # Short description
        descriptionMeta = soup.find('meta', {'property':'og:description'})
        self.story.setMetadata("short_description", stripHTML(descriptionMeta['content']))

        #groups
        groupButton = soup.find('button', {'data-click':'showAll'})
        if groupButton != None and groupButton.find('i', {'class':'fa-search-plus'}):
            groupResponse = self._fetchUrl("https://www.fimfiction.net/ajax/stories/%s/groups" % (self.story.getMetadata("storyId")))
            groupData = json.loads(groupResponse)
            groupList = self.make_soup(groupData["content"])
        else:
            groupList = soup.find('ul', {'id':'story-groups-list'})

        if not (groupList == None):
            for groupContent in groupList.find_all('a'):
                self.story.addToList("groupsUrl", 'https://'+self.host+groupContent["href"])
                groupName = groupContent.find('span', {"class":"group-name"})
                if groupName != None:
                    self.story.addToList("groups",stripHTML(groupName).replace(',', ';'))
                else:
                    self.story.addToList("groups",stripHTML(groupContent).replace(',', ';'))

        #sequels
        for header in soup.find_all('h1', {'class':'header-stories'}):
            # I don't know why using text=re.compile with find() wouldn't work, but it didn't.
            if header.text.startswith('Sequels'):
                sequelContainer = header.parent
                for sequel in sequelContainer.find_all('a', {'class':'story_link'}):
                    self.story.addToList("sequelsUrl", 'https://'+self.host+sequel["href"])
                    self.story.addToList("sequels", stripHTML(sequel).replace(',', ';'))

        #author last login
        userPageHeader = soup.find('div', {'class':'user-page-header'})
        if not userPageHeader == None:
            infoContainer = userPageHeader.find('ul', {'class':'mini-info-box'})
            listItems = infoContainer.find_all('li')
            lastLoginString = stripHTML(listItems[1])
            lastLogin = None
            if "online" in lastLoginString:
                lastLogin = date.today()
            elif "offline" in lastLoginString:
                lastLogin = self.date_span_tag_to_date(listItems[1])
            self.story.setMetadata("authorLastLogin", lastLogin)

    def date_span_tag_to_date(self, containingtag):
        ## <span data-time="1435421997" title="Saturday 27th of June 2015 @4:19pm">Jun 27th, 2015</span>
        ## No timezone adjustment is done.
        span = containingtag.find('span',{'data-time':re.compile(r'^\d+$')})
        if span != None:
            return datetime.fromtimestamp(float(span['data-time']))
        ## Sometimes, for reasons that are unclear, data-time is not present. Parse the date out of the title instead.
        else:
            span = containingtag.find('span', title=True)
            dateRegex = re.search('([a-zA-Z ]+)([0-9]+)(st of|th of|nd of|rd of)([a-zA-Z ]+[0-9]+)', span['title'])
            dateString = dateRegex.group(2) + dateRegex.group(4)
            return makeDate(dateString, "%d %B %Y")

    def ordinal_date_string_to_date(self, datestring):
        datestripped=re.sub(r"(\d+)(st|nd|rd|th)", r"\1", datestring.strip())
        return makeDate(datestripped, self.dateformat)

    def hookForUpdates(self,chaptercount):
        if self.oldchapters and len(self.oldchapters) > self.newestChapterNum:
            logger.info("Existing epub has %s chapters\nNewest chapter is %s.  Discarding old chapters from there on."%(len(self.oldchapters), self.newestChapterNum+1))
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

        soup = self.make_soup(data)

        data = self.do_fix_blockquotes(data)

        if self.getConfig("include_author_notes",True):
            soup = self.make_soup(data).find_all('div', {'class':re.compile(r'(.*\bauthors-note\b.*|.*\bchapter-body\b.*)')})
            if soup == None:
                raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
            chapter_divs = [unicode(div) for div in soup]
            soup = self.make_soup(" ".join(chapter_divs))
        else:
            soup = self.make_soup(data).find('div', {'id' : 'chapter-body'})
            if soup == None:
                raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,soup)
