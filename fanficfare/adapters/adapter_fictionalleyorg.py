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
import urllib
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter,  makeDate

class FictionAlleyOrgSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','fa')
        self.is_adult=False

        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('authorId',m.group('auth'))
            self.story.setMetadata('storyId',m.group('id'))

            # normalized story URL.
            self._setURL(url)
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

    @staticmethod
    def getSiteDomain():
        return 'www.fictionalley.org'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/authors/drt/DA.html http://"+cls.getSiteDomain()+"/authors/drt/JOTP01a.html"

    def getSiteURLPattern(self):
        # http://www.fictionalley.org/authors/drt/DA.html
        # http://www.fictionalley.org/authors/drt/JOTP01a.html
        return re.escape("http://"+self.getSiteDomain())+"/authors/(?P<auth>[a-zA-Z0-9_]+)/(?P<id>[a-zA-Z0-9_]+)\.html"

    def _postFetchWithIAmOld(self,url):
        if self.is_adult or self.getConfig("is_adult"):
            params={'iamold':'Yes',
                    'action':'ageanswer'}
            logger.info("Attempting to get cookie for %s" % url)
            ## posting on list doesn't work, but doesn't hurt, either.
            data = self._postUrl(url,params)
        else:
            data = self._fetchUrl(url)
        return data

    def extractChapterUrlsAndMetadata(self):

        ## could be either chapter list page or one-shot text page.
        url = self.url
        logger.debug("URL: "+url)

        try:
            data = self._postFetchWithIAmOld(url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        chapterdata = data
        # If chapter list page, get the first chapter to look for adult check
        chapterlinklist = soup.findAll('a',{'class':'chapterlink'})
        if chapterlinklist:
            chapterdata = self._postFetchWithIAmOld(chapterlinklist[0]['href'])

        if "Are you over seventeen years old" in chapterdata:
            raise exceptions.AdultCheckRequired(self.url)

        if not chapterlinklist:
            # no chapter list, chapter URL: change to list link.
            # second a tag inside div breadcrumbs
            storya = soup.find('div',{'class':'breadcrumbs'}).findAll('a')[1]
            self._setURL(storya['href'])
            url=self.url
            logger.debug("Normalizing to URL: "+url)
            ## title's right there...
            self.story.setMetadata('title',stripHTML(storya))
            data = self._fetchUrl(url)
            soup = self.make_soup(data)
            chapterlinklist = soup.findAll('a',{'class':'chapterlink'})
        else:
            ## still need title from somewhere.  If chapterlinklist,
            ## then chapterdata contains a chapter, find title the
            ## same way.
            chapsoup = self.make_soup(chapterdata)
            storya = chapsoup.find('div',{'class':'breadcrumbs'}).findAll('a')[1]
            self.story.setMetadata('title',stripHTML(storya))
            del chapsoup

        del chapterdata

        ## authorid already set.
        ## <h1 class="title" align="center">Just Off The Platform II by <a href="http://www.fictionalley.org/authors/drt/">DrT</a></h1>
        authora=soup.find('h1',{'class':'title'}).find('a')
        self.story.setMetadata('author',authora.string)
        self.story.setMetadata('authorUrl',authora['href'])

        if len(chapterlinklist) == 1:
            self.add_chapter(self.story.getMetadata('title'),chapterlinklist[0]['href'])
        else:
            # Find the chapters:
            for chapter in chapterlinklist:
                # just in case there's tags, like <i> in chapter titles.
                self.add_chapter(chapter,chapter['href'])


        ## Go scrape the rest of the metadata from the author's page.
        data = self._fetchUrl(self.story.getMetadata('authorUrl'))
        soup = self.make_soup(data)

        # <dl><dt><a class = "Rid story" href = "http://www.fictionalley.org/authors/aafro_man_ziegod/TMH.html">
        # [Rid] The Magical Hottiez</a> by <a class = "pen_name" href = "http://www.fictionalley.org/authors/aafro_man_ziegod/">Aafro Man Ziegod</a> </small></dt>
        # <dd><small class = "storyinfo"><a href = "http://www.fictionalley.org/ratings.html" target = "_new">Rating:</a> PG-13 - Spoilers: PS/SS, CoS, PoA, GoF, QTTA, FB - 4264 hits - 5060 words<br />
        # Genre: Humor, Romance - Main character(s): None - Ships: None - Era: Multiple Eras<br /></small>
        # Chaos ensues after Witch Weekly, seeking to increase readers, decides to create a boyband out of five seemingly talentless wizards: Harry Potter, Draco Malfoy, Ron Weasley, Neville Longbottom, and Oliver "Toss Your Knickers Here" Wood.<br />
        # <small class = "storyinfo">Published: June 3, 2002 (between Goblet of Fire and Order of Phoenix) - Updated: June 3, 2002</small>
        # </dd></dl>

        storya = soup.find('a',{'href':self.story.getMetadata('storyUrl')})
        storydd = storya.findNext('dd')

        # Rating: PG - Spoilers: None - 2525 hits - 736 words
        # Genre: Humor - Main character(s): H, R - Ships: None - Era: Multiple Eras
        # Harry and Ron are back at it again! They reeeeeeally don't want to be back, because they know what's awaiting them. "VH1 Goes Inside..." is back! Why? 'Cos there are soooo many more couples left to pick on.
        # Published: September 25, 2004 (between Order of Phoenix and Half-Blood Prince) - Updated: September 25, 2004

        ## change to text and regexp find.
        metastr = stripHTML(storydd).replace('\n',' ').replace('\t',' ')

        m = re.match(r".*?Rating: (.+?) -.*?",metastr)
        if m:
            self.story.setMetadata('rating', m.group(1))

        m = re.match(r".*?Genre: (.+?) -.*?",metastr)
        if m:
            for g in m.group(1).split(','):
                self.story.addToList('genre',g)

        m = re.match(r".*?Published: ([a-zA-Z]+ \d\d?, \d\d\d\d).*?",metastr)
        if m:
            self.story.setMetadata('datePublished',makeDate(m.group(1), "%B %d, %Y"))

        m = re.match(r".*?Updated: ([a-zA-Z]+ \d\d?, \d\d\d\d).*?",metastr)
        if m:
            self.story.setMetadata('dateUpdated',makeDate(m.group(1), "%B %d, %Y"))

        m = re.match(r".*? (\d+) words Genre.*?",metastr)
        if m:
            self.story.setMetadata('numWords', m.group(1))

        for small in storydd.findAll('small'):
            small.extract() ## removes the <small> tags, leaving only the summary.
        storydd.name = 'div' ## change tag name else Calibre treats it oddly.
        self.setDescription(url,storydd)
        #self.story.setMetadata('description',stripHTML(storydd))

        return

    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        data = self._fetchUrl(url)
        # find <!-- headerend --> & <!-- footerstart --> and
        # replaced with matching div pair for easier parsing.
        # Yes, it's an evil kludge, but what can ya do?  Using
        # something other than div prevents soup from pairing
        # our div with poor html inside the story text.
        crazy = "crazytagstringnobodywouldstumbleonaccidently"
        data = data.replace('<!-- headerend -->','<'+crazy+' id="storytext">').replace('<!-- footerstart -->','</'+crazy+'>')

        # problems with some stories confusing Soup.  This is a nasty
        # hack, but it works.
        data = data[data.index('<'+crazy+''):]
        # ditto with extra crap at the end.
        data = data[:data.index('</'+crazy+'>')+len('</'+crazy+'>')]

        soup = self.make_soup(data)
        body = soup.findAll('body') ## some stories use a nested body and body
                                    ## tag, in which case we don't
                                    ## need crazytagstringnobodywouldstumbleonaccidently
                                    ## and use the second one instead.
        if len(body)>1:
            text = body[1]
            text.name='div' # force to be a div to avoid multiple body tags.
        else:
            text = soup.find(crazy, {'id' : 'storytext'})
            text.name='div' # change to div tag.

        if not data or not text:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        # not sure how, but we can get html, etc tags still in some
        # stories.  That breaks later updates because it confuses
        # epubutils.py
        for tag in text.findAll('head'):
            tag.extract()

        for tag in text.findAll('body') + text.findAll('html'):
            tag.name = 'div'

        return self.utf8FromSoup(url,text)

def getClass():
    return FictionAlleyOrgSiteAdapter

