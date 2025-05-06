# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2021 FanFicFare team
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

from .base_adapter import BaseSiteAdapter,  makeDate

class FictionAlleyArchiveOrgSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','fa')
        self.is_adult=False

        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            # normalized story URL.
            url = "https://"+self.getSiteDomain()+"/authors/"+m.group('auth')+"/"+m.group('id')+".html"
            self._setURL(url)
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())
        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%m/%d/%Y"

    def _setURL(self,url):
        # logger.debug("set URL:%s"%url)
        super(FictionAlleyArchiveOrgSiteAdapter, self)._setURL(url)
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('authorId',m.group('auth'))
            self.story.setMetadata('storyId',m.group('id'))

    @staticmethod
    def getSiteDomain():
        return 'www.fictionalley-archive.org'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.fictionalley-archive.org',
                'www.fictionalley.org']

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/authors/drt/DA.html https://"+cls.getSiteDomain()+"/authors/drt/JOTP01a.html"

    @classmethod
    def getURLDomain(cls):
        return 'https://' + cls.getSiteDomain()

    def getSiteURLPattern(self):
        # http://www.fictionalley-archive.org/authors/drt/DA.html
        # http://www.fictionalley-archive.org/authors/drt/JOTP01a.html
        return r"https?://www.fictionalley(-archive)?.org/authors/(?P<auth>[a-zA-Z0-9_]+)/(?P<id>[a-zA-Z0-9_]+)\.html"

    def extractChapterUrlsAndMetadata(self):

        ## could be either chapter list page or one-shot text page.
        logger.debug("URL: "+self.url)

        (data,rurl) = self.get_request_redirected(self.url)
        if rurl != self.url:
            self._setURL(rurl)
            logger.debug("set to redirected url:%s"%self.url)
        soup = self.make_soup(data)

        # If chapter list page, get the first chapter to look for adult check
        chapterlinklist = soup.select('h5.mb-1 > a')
        # logger.debug(chapterlinklist)

        if not chapterlinklist:
            # no chapter list, it's either a chapter URL or a single chapter story
            # <nav aria-label="Chapter Navigation">
            #  <a class="page-link" href="/authors/mz_xxo/HPATOTFI.html">Index</a>
            storya = soup.select_one('nav[aria-label="Chapter Navigation"] a')
            # logger.debug(storya)
            if storya:
                ## multi chapter story
                self._setURL(self.getURLDomain()+storya['href'])
                logger.debug("Normalizing to URL: "+self.url)
                # ## title's right there...
                # self.story.setMetadata('title',stripHTML(storya))
                data = self.get_request(self.url)
                soup = self.make_soup(data)
                chapterlinklist = soup.select('h5.mb-1 > a')
                # logger.debug(chapterlinklist)
            else:
                ## single chapter story.
                # logger.debug("Single chapter story")
                pass

        self.story.setMetadata('title',stripHTML(soup.select_one('h1')))

        ## authorid already set.
        ## <h1 class="title" align="center">Just Off The Platform II by <a href="http://www.fictionalley.org/authors/drt/">DrT</a></h1>
        authora=soup.select_one('h1 + h3 > a')
        self.story.setMetadata('author',stripHTML(authora))
        self.story.setMetadata('authorUrl',self.getURLDomain()+authora['href'])

        if chapterlinklist:
            # Find the chapters:
            for chapter in chapterlinklist:
                listitem = chapter.parent.parent.parent
                # logger.debug(listitem)
                # date
                date = stripHTML(listitem.select_one('small.text-nowrap'))
                chapterDate = makeDate(date,self.dateformat)
                wordshits = listitem.select('span.font-weight-normal')
                chap_data = {
                    'date':chapterDate.strftime(self.getConfig("datechapter_format",self.getConfig("datePublished_format","%Y-%m-%d"))),
                    'words':stripHTML(wordshits[0]),
                    'hits':stripHTML(wordshits[1]),
                    'summary':stripHTML(listitem.select_one('p.my-2')),
                    }
                # logger.debug(chap_data)
                self.add_chapter(chapter,self.getURLDomain()+chapter['href'], chap_data)
        else:
            self.add_chapter(self.story.getMetadata('title'),self.url)

        cardbody = soup.select_one('div.card-body')

        searchs_to_meta = (
            # sitetype, ffftype, islist
            ('Rating', 'rating', False),
            ('House', 'house', True),
            ('Character', 'characters', True),
            ('Genre', 'genre', True),
            ('Era', 'era', True),
            ('Spoiler', 'spoilers', True),
            ('Ship', 'ships', True),
            )
        for (sitetype,ffftype, islist) in searchs_to_meta:
            # logger.debug((sitetype,ffftype, islist))
            tags = cardbody.select('a[href^="/stories?Include.%s"]'%sitetype)
            # logger.debug(tags)
            if tags:
                if islist:
                    self.story.extendList(ffftype, [ stripHTML(a) for a in tags ])
                else:
                    self.story.setMetadata(ffftype, stripHTML(tags[0]))


        # Published: 09/26/2003 Updated: 04/13/2004 Words: 14,268 Chapters: 5 Hits: 743
        badgeinfos = cardbody.select('div.badge-info')
        # logger.debug(badgeinfos)
        for badge in badgeinfos:
            txt = stripHTML(badge)
            (key,val)=txt.split(':')
            # logger.debug((key,val))
            if key in ( 'Published', 'Updated'):
                date = makeDate(val,self.dateformat)
                self.story.setMetadata('date'+key,date)
            elif key in ('Hits'):
                self.story.setMetadata(key.lower(),val)
            elif key == 'Words':
                self.story.setMetadata('numWords',val)

        summary = soup.find('dt',string='Story Summary:')
        if summary:
            summary = summary.find_next_sibling('dd')
            summary.name='div'
            self.setDescription(self.url,summary)

        return

    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        data = self.get_request(url)
        soup = self.make_soup(data)

        # this may be a brittle way to get the chapter text.
        # Site doesn't give a lot of hints.
        chaptext = soup.select_one('main#content div:not([class])')

        # not sure how, but we can get html, etc tags still in some
        # stories.  That breaks later updates because it confuses
        # epubutils.py
        # Yes, this still applies to fictionalley-archive.

        for tag in chaptext.find_all('head') + chaptext.find_all('meta') + chaptext.find_all('script'):
            tag.extract()

        for tag in chaptext.find_all('body') + chaptext.find_all('html'):
            tag.name = 'div'

        if self.getConfig('include_author_notes'):
            row = chaptext.find_previous_sibling('div',class_='row')
            logger.debug(row)
            andt = row.find('dt',string="Author's Note:")
            logger.debug(andt)
            if andt:
                chaptext.insert(0,andt.parent.extract())
            # post notes aren't as structured(?)
            for div in chaptext.find_next_siblings('div',class_='row'):
                chaptext.append(div.extract())

        # logger.debug(chaptext)
        return self.utf8FromSoup(url,chaptext)

def getClass():
    return FictionAlleyArchiveOrgSiteAdapter
