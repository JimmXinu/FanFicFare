# -*- coding: utf-8 -*-

# Copyright 2023 FanFicFare team
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
from ..htmlcleanup import stripHTML
from .. import exceptions
from .base_adapter import BaseSiteAdapter, makeDate
import re
import logging
logger = logging.getLogger(__name__)

def getClass():
    return SoFurryComAdapter

class SoFurryComAdapter(BaseSiteAdapter):
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.username = self.getConfig("username")
        self.password = self.getConfig("password")
        self.dateformat = "%Y-%m-%d %H:%M:%S"
        self.story.setMetadata('siteabbrev','sf')
        self.story.setMetadata('status', 'Completed')
        # self.story.setMetadata('language', "English")
        self.chaptered = None
        self.is_adult = self.getConfig("is_adult")

    @staticmethod
    def getSiteDomain():
        return 'sofurry.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/s/z1V1z3Zn"

    def _setURL(self,url):
        match = re.search(self.getSiteURLPattern(), url)
        if not match:
            raise exceptions.InvalidStoryURL(url, self.getSiteDomain(), self.getSiteExampleURLs())
        self.is_story_url = bool(match.group('story_url'))
        if match.group('story_url'):
            self.story.setMetadata('storyId', match.group('story_id'))
            url = match.group('story_url')
        else:
            self.story.setMetadata('storyId', match.group('folder_id'))
            url = match.group('folder_url')
        
        super(SoFurryComAdapter, self)._setURL(url)

    def getSiteURLPattern(self):
        return r"(?P<folder_url>https?://"+re.escape(self.getSiteDomain())+r"/u/.+/f/(?P<folder_id>[a-zA-Z0-9]+))|(?P<story_url>https?://"+re.escape(self.getSiteDomain())+r"/s/(?P<story_id>[a-zA-Z0-9]+))(?=[?#\s]|$)"

    def adultCheck(self, url, soup):
        if soup.find('div', {'class': 'hazard-bar'}):
            if not self.is_adult:
                raise exceptions.AdultCheckRequired(url)
            token = soup.find('meta', {'name':'csrf-token'}).get('content')
            logger.debug(token)
            d = self.post_request(url+"/ackAdult", {"_token": token})
            soup = self.make_soup(d)
        return soup

    def performLogin(self, url, soup):
        params = {}
        params['_token'] = soup.find('meta', {'name':'csrf-token'}).get('content')
        if self.password:
            params['email'] = self.username
            params['password'] = self.password
        else:
            params['email'] = self.getConfig("username")
            params['password'] = self.getConfig("password")

        loginUrl = 'https://' + self.getSiteDomain() + '/login'
        logger.info("Will now login to URL (%s) as (%s)" % (loginUrl, params['email']))

        d = self.post_request(loginUrl, params)

        if 'src="/img/user/' not in d :
            logger.info("Failed to login to URL %s as %s" % (loginUrl, params['email']))
            raise exceptions.FailedToLogin(url,params['email'])

    def doExtractChapterUrlsAndMetadata(self,get_cover=True):
        # self.story.setMetadata('storyId',m.group('id'))
        logger.info("url: "+self.url)

        data = self.get_request(self.url,usecache=True)
        soup = self.make_soup(data)
        if (self.getConfig("always_login") and 'src="/img/user/' not in data):
            self.performLogin(self.url, soup)
            data = self.get_request(self.url,usecache=False)
            soup = self.make_soup(data)

        soup = self.adultCheck(self.url, soup)

        if self.is_story_url:
            self.story.setMetadata('author', stripHTML(soup.select_one('h3.username')))
            self.story.setMetadata('authorUrl', soup.select_one('#submission-author-link').get('href'))
            self.story.setMetadata('authorId', stripHTML(soup.select_one('h6.handle')))
        else:
            self.story.setMetadata('author', stripHTML(soup.select_one('#username')))
            self.story.setMetadata('authorUrl', soup.select_one('span[class="fas fa-user"]').parent.get('href'))
            self.story.setMetadata('authorId', stripHTML(soup.select_one('#handle')))

        story_tags = []

        if not self.is_story_url:
            chapter_grid = soup.select_one('div.submissiongrid')
            if not chapter_grid:
                self.performLogin(self.url, soup)
                soup = self.make_soup(self.get_request(self.url,usecache=False))

            chapters = soup.select_one('div.submissiongrid').select('div.submission.writing')
            for chapter in reversed(chapters):
                chap_title = stripHTML(chapter.find('div', {'class':'title'}))
                chap_url = chapter.find('a', {'class':'sublink'}).get('href')
                logger.debug(chap_title)
                logger.debug(chap_url)
                self.add_chapter(chap_title,chap_url)
                chap_tags = stripHTML(chapter.find('div', {'class':'tags'}))
                logger.debug(chap_tags)
                story_tags.extend(chap_tags.split(', '))

            self.story.extendList('genre', list(set(story_tags)))

            title_tag = soup.select_one('span.fa-folder-open').parent
            title = [t.strip() for t in title_tag.contents if isinstance(t, str)][-1]
            self.story.setMetadata('title', title)
            soup = self.make_soup(self.get_request(self.get_chapter(-1, 'url'),usecache=True)) 
            raw_dateUpdated = soup.select_one('div.row.statistics').find('span', {'data-toggle':'tooltip'})
            dateUpdated = re.search(r'Published on (.+)', raw_dateUpdated.get('title'))
            self.story.setMetadata('dateUpdated', makeDate(dateUpdated.group(1), self.dateformat))

            soup = self.make_soup(self.get_request(self.get_chapter(0, 'url'),usecache=True))
            raw_date_posted = soup.select_one('div.row.statistics').find('span', {'data-toggle':'tooltip'})
            date_posted = re.search(r'Published on (.+)', raw_date_posted.get('title'))
            self.story.setMetadata('datePublished', makeDate(date_posted.group(1), self.dateformat))
            logger.debug(self.story.getMetadata('datePublished'))
            return

        title = stripHTML(soup.select_one('span[data-hide-on="subedit"]'))
        self.story.setMetadata('title', title)

        oneshot = True
        ul_chapters = soup.select_one('ul.fa-ul')
        if ul_chapters:
            oneshot = False
            logger.debug("Chapters present")
            self.chaptered = soup.find_all('div', {'class':'story-content-holder'})
            for chapter in ul_chapters.find_all('a'):
                chapter_url = chapter.get('href')
                logger.debug(self.url+chapter_url)
                chapter_title = re.sub(r'[\n ] +', r' ', stripHTML(chapter))
                logger.debug(chapter_title)
                self.add_chapter(chapter_title,self.url+chapter_url)
            logger.debug("Tags/Chapters %d/%d", len(self.chaptered), len(self.get_chapters()))
            if len(self.chaptered) != len(self.get_chapters()):
                logger.debug("Chapters and content mismatch")
                ul_chapters.decompose()
                self.chaptered = None
                self.chapterUrls = []
                oneshot = True

        if oneshot:
            oneshot_chapter_title_html = soup.select_one('#chapter-0')
            if oneshot_chapter_title_html == None:
                oneshot_chapter_title_html = soup.select_one('.story-content-holder > .my-2')
            logger.debug(oneshot_chapter_title_html)
            if not oneshot_chapter_title_html or not stripHTML(oneshot_chapter_title_html):
                oneshot_chapter_title = title
            else:
                oneshot_chapter_title = stripHTML(oneshot_chapter_title_html)
            self.add_chapter(oneshot_chapter_title,self.url)

        div_chap_tags = soup.find('div', {'class':'row tags'})
        story_tags.extend([stripHTML(tag) for tag in div_chap_tags.find_all('a', {'class':'tag'})])
        self.story.extendList('genre', list(set(story_tags)))

        raw_date_posted = soup.select_one('div.row.statistics').find('span', {'data-toggle':'tooltip'})
        date_posted = re.search(r'Published on (.+)', raw_date_posted.get('title'))
        self.story.setMetadata('datePublished', makeDate(date_posted.group(1), self.dateformat))
        logger.debug(self.story.getMetadata('datePublished'))

        self.story.extendList('rating', [stripHTML(tag) for tag in soup.select_one('div.row.col-12 > h5').select('span')])
        logger.debug(self.story.getMetadata('rating'))

        self.setDescription(self.url, soup.select_one('div.description.w-100 > div.w-100'))

        if get_cover:
            img_tag = soup.select_one('.img-container > img:nth-child(1)')
            if img_tag:
                self.setCoverImage(self.url,img_tag['src'])

    def getChapterTextNum(self, url, index):
        logger.debug('Getting chapter '+url)
        if self.chaptered:
            logger.debug("Index "+str(index))
            chapter = self.chaptered[index]
            return self.utf8FromSoup(url,chapter)

        data = self.get_request(url,usecache=True)
        soup = self.make_soup(data)
        soup = self.adultCheck(url, soup)
        chapter = soup.select_one('div[class="content-holder"]')

        if self.is_story_url or not self.getConfig("include_description_in_chapters", False):
            return self.utf8FromSoup(url,chapter)

        desc = soup.select_one('div.description.w-100 > div.w-100')
        if desc:
            description_div_tag = soup.new_tag('div', attrs={'class': 'fff_chapter_notes fff_head_notes'})
            description_b_tag = soup.new_tag('b')
            description_b_tag.string = 'Description:'
            description_blockquote_tag = soup.new_tag('blockquote')
            description_blockquote_tag.append(desc)
            description_div_tag.append(description_b_tag)
            description_div_tag.append(description_blockquote_tag)
            description_div_tag.append(soup.new_tag('hr'))
            chapter.insert(0, description_div_tag)

        return self.utf8FromSoup(url,chapter)

    def before_get_urls_from_page(self,url,normalize):
        if self.password and self.getConfig("always_login"):
            soup = self.make_soup(self.get_request(url,usecache=False))
            self.performLogin(url, soup)