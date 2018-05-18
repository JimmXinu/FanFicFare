#  -*- coding: utf-8 -*-

# Copyright 2014 Fanficdownloader team, 2017 FanFicFare team
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
import urllib.request, urllib.error, urllib.parse
import json

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from .base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return ArchiveOfOurOwnOrgAdapter


logger = logging.getLogger(__name__)

class ArchiveOfOurOwnOrgAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        self.full_work_soup = None
        self.use_full_work_soup = True

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])

        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))

            # normalized story URL.
            self._setURL('https://' + self.getSiteDomain() + '/works/'+self.story.getMetadata('storyId'))
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','ao3')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y-%b-%d"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'archiveofourown.org'

    @classmethod
    def getAcceptDomains(cls):
        return ['archiveofourown.org','download.archiveofourown.org']

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/works/123456 https://"+cls.getSiteDomain()+"/collections/Some_Archive/works/123456 https://"+cls.getSiteDomain()+"/works/123456/chapters/78901"

    def getSiteURLPattern(self):
        # https://archiveofourown.org/collections/Smallville_Slash_Archive/works/159770
        # Discard leading zeros from story ID numbers--AO3 doesn't use them in it's own chapter URLs.
        return r"https?://(download\.)?"+re.escape(self.getSiteDomain())+r"(/collections/[^/]+)?/works/0*(?P<id>\d+)"

    ## Login
    def needToLoginCheck(self, data):
        if 'This work is only available to registered users of the Archive.' in data \
                or "The password or user name you entered doesn't match our records" in data:
            return True
        else:
            return False

    def performLogin(self, url, data):

        params = {}
        if self.password:
            params['user_session[login]'] = self.username
            params['user_session[password]'] = self.password
        else:
            params['user_session[login]'] = self.getConfig("username")
            params['user_session[password]'] = self.getConfig("password")
        params['user_session[remember_me]'] = '1'
        params['commit'] = 'Log in'
        params['utf8'] = '\x2713' # utf8 *is* required now.  hex code works better than actual character for some reason. u'✓'

        # token now comes from meta.
        # <meta name="csrf-token" content="/Li4mJ1w1AENhQq8EPVIklFwCDP5eaTHNRWPlWkehu2d1iuRzgsOHYGCX+uhjmlKnd1A9VisCdqmeTmBmXZkBg=="/>
        #params['authenticity_token'] = data.split('meta name="csrf-token" content="')[1].split('"')[0]
        # authenticity_token now comes from a completely separate json call.
        token_json = json.loads(self._fetchUrl('https://' + self.getSiteDomain() + "/token_dispenser.json"))
        params['authenticity_token'] = token_json['token']

        loginUrl = 'https://' + self.getSiteDomain() + '/user_sessions'
        logger.info("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                            params['user_session[login]']))

        d = self._postUrl(loginUrl, params)
        #logger.info(d)

        if "Successfully logged in" not in d : #Member Account
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['user_session[login]']))
            raise exceptions.FailedToLogin(url,params['user_session[login]'])
            return False
        else:
            return True

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        if self.is_adult or self.getConfig("is_adult"):
            addurl = "?view_adult=true"
        else:
            addurl=""

        metaurl = self.url+addurl
        url = self.url+'/navigate'+addurl
        logger.info("url: "+url)
        logger.info("metaurl: "+metaurl)

        try:
            data = self._fetchUrl(url)
            meta = self._fetchUrl(metaurl)

            if "This work could have adult content. If you proceed you have agreed that you are willing to see such content." in meta:
                raise exceptions.AdultCheckRequired(self.url)

        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        if "Sorry, we couldn&#x27;t find the work you were looking for." in data:
            raise exceptions.StoryDoesNotExist(self.url)

        # need to log in for this one, or always_login.
        if self.needToLoginCheck(data) or \
                ( self.getConfig("always_login") and 'href="/logout"' not in data ):
            ## except don't log in if already logged in (cached
            ## responses in calibre job).  already logged in if
            ## there's no authenticity_token in data.
            self.performLogin(url,data)
            data = self._fetchUrl(url,usecache=False)
            meta = self._fetchUrl(metaurl,usecache=False)

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)
        for tag in soup.findAll('div',id='admin-banner'):
            tag.extract()
        metasoup = self.make_soup(meta)
        for tag in metasoup.findAll('div',id='admin-banner'):
            tag.extract()

        # Now go hunting for all the meta data and the chapter list.

        ## Title
        a = soup.find('a', href=re.compile(r"/works/\d+$"))
        self.story.setMetadata('title',stripHTML(a))

        if self.getConfig("always_login"):
            try:
                self.story.extendList('bookmarktags',
                                      metasoup.find('input',id='bookmark_tag_string')['value'].split(', '))
            except KeyError:
                pass
            self.story.setMetadata('bookmarksummary',
                                   stripHTML(metasoup.find('textarea',id='bookmark_notes')))

        # Find authorid and URL from... author url.
        alist = soup.findAll('a', href=re.compile(r"/users/\w+/pseuds/\w+"))
        if len(alist) < 1: # ao3 allows for author 'Anonymous' with no author link.
            self.story.setMetadata('author','Anonymous')
            self.story.setMetadata('authorUrl','https://archiveofourown.org/')
            self.story.setMetadata('authorId','0')
        else:
            for a in alist:
                self.story.addToList('authorId',a['href'].split('/')[-1])
                self.story.addToList('authorUrl','https://'+self.host+a['href'])
                self.story.addToList('author',a.text)

        byline = metasoup.find('h3',{'class':'byline'})
        if byline:
            self.story.setMetadata('byline',stripHTML(byline))

        # byline:
        # <h3 class="byline heading">
        # Hope Roy [archived by <a href="/users/ssa_archivist/pseuds/ssa_archivist" rel="author">ssa_archivist</a>]
        # </h3>
        # stripped:"Hope Roy [archived by ssa_archivist]"

        m = re.match(r'(?P<author>.*) \[archived by (?P<archivist>.*)\]',stripHTML(byline))
        if( m and
            len(alist) == 1 and
            self.getConfig('use_archived_author') ):
            self.story.setMetadata('author',m.group('author'))

        newestChapter = None
        self.newestChapterNum = None # save for comparing during update.
        # Scan all chapters to find the oldest and newest, on AO3 it's
        # possible for authors to insert new chapters out-of-order or
        # change the dates of earlier ones by editing them--That WILL
        # break epub update.
        # Find the chapters:
        chapters=soup.findAll('a', href=re.compile(r'/works/'+self.story.getMetadata('storyId')+"/chapters/\d+$"))
        self.story.setMetadata('numChapters',len(chapters))
        logger.debug("numChapters: (%s)"%self.story.getMetadata('numChapters'))
        if len(chapters)==1:
            self.chapterUrls.append((self.story.getMetadata('title'),'https://'+self.host+chapters[0]['href']))
        else:
            for index, chapter in enumerate(chapters):
                # strip just in case there's tags, like <i> in chapter titles.
                self.chapterUrls.append((stripHTML(chapter),'https://'+self.host+chapter['href']))
                # (2013-09-21)
                date = stripHTML(chapter.findNext('span'))[1:-1]
                chapterDate = makeDate(date,self.dateformat)
                if newestChapter == None or chapterDate > newestChapter:
                    newestChapter = chapterDate
                    self.newestChapterNum = index

        a = metasoup.find('blockquote',{'class':'userstuff'})
        if a != None:
            self.setDescription(url,a)
            #self.story.setMetadata('description',a.text)

        a = metasoup.find('dd',{'class':"rating tags"})
        if a != None:
            self.story.setMetadata('rating',stripHTML(a.text))

        d = metasoup.find('dd',{'class':"language"})
        if d != None:
            self.story.setMetadata('language',stripHTML(d.text))

        a = metasoup.find('dd',{'class':"fandom tags"})
        fandoms = a.findAll('a',{'class':"tag"})
        for fandom in fandoms:
            self.story.addToList('fandoms',fandom.string)

        a = metasoup.find('dd',{'class':"warning tags"})
        if a != None:
            warnings = a.findAll('a',{'class':"tag"})
            for warning in warnings:
                self.story.addToList('warnings',warning.string)

        a = metasoup.find('dd',{'class':"freeform tags"})
        if a != None:
            genres = a.findAll('a',{'class':"tag"})
            for genre in genres:
                self.story.addToList('freeformtags',genre.string)

        a = metasoup.find('dd',{'class':"category tags"})
        if a != None:
            genres = a.findAll('a',{'class':"tag"})
            for genre in genres:
                if genre != "Gen":
                    self.story.addToList('ao3categories',genre.string)

        a = metasoup.find('dd',{'class':"character tags"})
        if a != None:
            chars = a.findAll('a',{'class':"tag"})
            for char in chars:
                self.story.addToList('characters',char.string)

        a = metasoup.find('dd',{'class':"relationship tags"})
        if a != None:
            ships = a.findAll('a',{'class':"tag"})
            for ship in ships:
                self.story.addToList('ships',ship.string)

        a = metasoup.find('dd',{'class':"collections"})
        if a != None:
            collections = a.findAll('a')
            for collection in collections:
                self.story.addToList('collections',collection.string)

        stats = metasoup.find('dl',{'class':'stats'})
        dt = stats.findAll('dt')
        dd = stats.findAll('dd')
        for x in range(0,len(dt)):
            label = dt[x].text
            value = dd[x].text

            if 'Words:' in label:
                self.story.setMetadata('numWords', value)

            if 'Comments:' in label:
                self.story.setMetadata('comments', value)

            if 'Kudos:' in label:
                self.story.setMetadata('kudos', value)

            if 'Hits:' in label:
                self.story.setMetadata('hits', value)

            if 'Bookmarks:' in label:
                self.story.setMetadata('bookmarks', value)

            if 'Chapters:' in label:
                if value.split('/')[0] == value.split('/')[1]:
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')


            if 'Published' in label:
                self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))

            if 'Updated' in label:
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))

            if 'Completed' in label:
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))


        # Find Series name from series URL.
        ddseries = metasoup.find('dd',{'class':"series"})

        if ddseries:
            for i, a in enumerate(ddseries.findAll('a', href=re.compile(r"/series/\d+"))):
                series_name = stripHTML(a)
                series_url = 'https://'+self.host+a['href']
                series_index = int(stripHTML(a.previousSibling).replace(', ','').split(' ')[1]) # "Part # of" or ", Part #"
                self.story.setMetadata('series%02d'%i,"%s [%s]"%(series_name,series_index))
                self.story.setMetadata('series%02dUrl'%i,series_url)
                if i == 0:
                    self.setSeries(series_name, series_index)
                    self.story.setMetadata('seriesUrl',series_url)

    def hookForUpdates(self,chaptercount):
        if self.oldchapters and len(self.oldchapters) > self.newestChapterNum:
            logger.info("Existing epub has %s chapters\nNewest chapter is %s.  Discarding old chapters from there on."%(len(self.oldchapters), self.newestChapterNum+1))
            self.oldchapters = self.oldchapters[:self.newestChapterNum]
        return len(self.oldchapters)

    ## Normalize chapter URLs because a) site has changed from http to
    ## https and b) in case of title change.  That way updates to
    ## existing stories don't re-download all chapters.
    def normalize_chapterurl(self,url):
        url = re.sub(r"https?://("+self.getSiteDomain()+"/works/\d+/chapters/\d+)(\?view_adult=true)?$",
                     r"https://\1",url)
        return url

    # grab the text for an individual chapter.
    def getChapterTextNum(self, url, index):
        ## FYI: Chapter urls used to include ?view_adult=true in each
        ## one.  With cookiejar being passed now, that's not
        ## necessary.  However, there is a corner case with plugin--If
        ## a user-required story is attempted after gathering metadata
        ## for one that needs adult, but not user AND the user doesn't
        ## enter a valid user, the is_adult cookie from before can be
        ## lost.
        logger.debug('Getting chapter text for: %s index: %s' % (url,index))

        save_chapter_soup = self.make_soup('<div class="story"></div>')
        ## use the div because the full soup will also have <html><body>.
        ## need save_chapter_soup for .new_tag()
        save_chapter=save_chapter_soup.find('div')

        whole_dl_soup = chapter_dl_soup = None

        if self.use_full_work_soup and self.getConfig("use_view_full_work",True) and len(self.chapterUrls) > 1:
            logger.debug("USE view_full_work")
            ## Assumed view_adult=true was cookied during metadata
            if not self.full_work_soup:
                self.full_work_soup = self.make_soup(self._fetchUrl(self.url+"?view_full_work=true"))

            whole_dl_soup = self.full_work_soup
            chapter_dl_soup = whole_dl_soup.find('div',{'id':'chapter-%s'%(index+1)})
            if not chapter_dl_soup:
                self.use_full_work_soup = False
                logger.warn("chapter-%s not found in view_full_work--ending use_view_full_work"%(index+1))
        if not chapter_dl_soup:
            whole_dl_soup = chapter_dl_soup = self.make_soup(self._fetchUrl(url))
            if None == chapter_dl_soup:
                raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        exclude_notes=self.getConfigList('exclude_notes')

        def append_tag(elem,tag,string):
            '''bs4 requires tags be added separately.'''
            new_tag = save_chapter_soup.new_tag(tag)
            new_tag.string=string
            elem.append(new_tag)

        ## These are the over-all work's 'Notes at the beginning'.
        ## They only appear on the first chapter in individual chapter
        ## pages and before chapter-1 div.  Appending removes
        ## headnotes from whole_dl_soup, so be sure to only do it on
        ## the first chapter.
        if 'authorheadnotes' not in exclude_notes and index == 0:
            headnotes = whole_dl_soup.find('div', {'class' : "preface group"}).find('div', {'class' : "notes module"})
            if headnotes != None:
                ## Also include ul class='associations'.
                ulassoc = headnotes.find('ul', {'class' : "associations"})
                headnotes = headnotes.find('blockquote', {'class' : "userstuff"})
                if headnotes != None or ulassoc != None:
                    append_tag(save_chapter,'b',"Author's Note:")
                if ulassoc != None:
                    # fix relative links--all examples so far have been.
                    for alink in ulassoc.find_all('a'):
                        if 'http' not in alink['href']:
                            alink['href']='https://' + self.getSiteDomain() + alink['href']
                    save_chapter.append(ulassoc)
                if headnotes != None:
                    save_chapter.append(headnotes)

        ## Can appear on every chapter
        if 'chaptersummary' not in exclude_notes:
            chapsumm = chapter_dl_soup.find('div', {'id' : "summary"})
            if chapsumm != None:
                chapsumm = chapsumm.find('blockquote')
                append_tag(save_chapter,'b',"Summary for the Chapter:")
                save_chapter.append(chapsumm)

        ## Can appear on every chapter
        if 'chapterheadnotes' not in exclude_notes:
            chapnotes = chapter_dl_soup.find('div', {'id' : "notes"})
            if chapnotes != None:
                chapnotes = chapnotes.find('blockquote')
                if chapnotes != None:
                    append_tag(save_chapter,'b',"Notes for the Chapter:")
                    save_chapter.append(chapnotes)

        text = chapter_dl_soup.find('div', {'class' : "userstuff module"})
        chtext = text.find('h3', {'class' : "landmark heading"})
        if chtext:
            chtext.extract()
        save_chapter.append(text)

        ## Can appear on every chapter
        if 'chapterfootnotes' not in exclude_notes:
            chapfoot = chapter_dl_soup.find('div', {'class' : "end notes module", 'role' : "complementary"})
            if chapfoot != None:
                chapfoot = chapfoot.find('blockquote')
                append_tag(save_chapter,'b',"Notes for the Chapter:")
                save_chapter.append(chapfoot)

        ## These are the over-all work's 'Notes at the end'.
        ## They only appear on the last chapter in individual chapter
        ## pages and after chapter-# div.  Appending removes
        ## headnotes from whole_dl_soup, so be sure to only do it on
        ## the last chapter.
        if 'authorfootnotes' not in exclude_notes and index+1 == len(self.chapterUrls):
            footnotes = whole_dl_soup.find('div', {'id' : "work_endnotes"})
            if footnotes != None:
                footnotes = footnotes.find('blockquote')
                if footnotes:
                    append_tag(save_chapter,'b',"Author's Note:")
                    save_chapter.append(footnotes)

        if 'inspiredlinks' not in exclude_notes and index+1 == len(self.chapterUrls):
            inspiredlinks = whole_dl_soup.find('div', {'id' : "children"})
            if inspiredlinks != None:
                if inspiredlinks:
                    inspiredlinks.find('h3').name='b' # don't want a big h3 at the end.
                    # fix relative links--all examples so far have been.
                    for alink in inspiredlinks.find_all('a'):
                        if 'http' not in alink['href']:
                            alink['href']='https://' + self.getSiteDomain() + alink['href']
                    save_chapter.append(inspiredlinks)

        return self.utf8FromSoup(url,save_chapter)
