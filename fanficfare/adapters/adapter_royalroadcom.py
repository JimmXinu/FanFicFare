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
import contextlib
from datetime import datetime
import logging
import re
from .. import exceptions as exceptions
from ..dateutils import parse_relative_date_string
from ..htmlcleanup import stripHTML

from .base_adapter import BaseSiteAdapter

logger = logging.getLogger(__name__)


def getClass():
    return RoyalRoadAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class RoyalRoadAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only fiction/1234
        self.story.setMetadata('storyId',re.match(r'/fiction/(\d+)(/.*)?$',self.parsedUrl.path).groups()[0])


        # normalized story URL.
        self._setURL('https://' + self.getSiteDomain() + '/fiction/'+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','rylrdl')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = '%d/%m/%Y %H:%M:%S %p'

    def make_date(self, parenttag):
        # locale dates differ but the timestamp is easily converted
        timetag = parenttag.find('time')
        if timetag.has_attr('unixtime'):
            ts = timetag['unixtime']
            return datetime.fromtimestamp(float(ts))
        else:
            ## site has gone to crappy resolution "XX
            ## (min/day/month/year/etc) ago" dating
            return parse_relative_date_string(timetag.text)

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        # changed from royalroadl.com
        return 'www.royalroad.com'

    @classmethod
    def getAcceptDomains(cls):
        return ['royalroad.com','royalroadl.com','www.royalroadl.com']

    @classmethod
    def getConfigSections(cls):
        "Only needs to be overriden if has additional ini sections."
        return ['royalroadl.com',cls.getSiteDomain()]

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://www.royalroad.com/fiction/3056"

    def getSiteURLPattern(self):
        return "https?"+re.escape("://")+r"(www\.|)royalroadl?\.com/fiction/\d+(/.*)?$"

    def make_soup(self,data):
        soup = super(RoyalRoadAdapter, self).make_soup(data)
        self.handle_spoilers(soup)
        return soup

    def handle_spoilers(self,topsoup):
        '''
        Modifies tag given as required to do spoiler changes.
        '''
        if self.getConfig('remove_spoilers'):
            for div in topsoup.find_all('div',class_='spoiler'):
                div.extract()
        elif self.getConfig('legend_spoilers'):
            for div in topsoup.find_all('div',class_='spoiler'):
                div.name='fieldset'
                legend = topsoup.new_tag('legend')
                smalltext = div.find('div',class_='smalltext')
                if smalltext:
                    legend.string = stripHTML(smalltext)
                    smalltext.extract()
                div.insert(0,legend)
                for inner in div.find_all('div',class_='spoiler-inner'):
                    del inner['style']
                #div.button.extract()

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        url = self.url
        logger.debug("URL: "+url)

        data = self.get_request(url)

        soup = self.make_soup(data)
        # print data

        # site has taken to presenting a *page* that says 404 while
        # still returning an HTTP 200 code.
        div404 = soup.find('div',{'class':'number'})
        if div404 and stripHTML(div404) == '404':
            raise exceptions.StoryDoesNotExist(self.url)

        ## Title
        title = soup.select_one('.fic-header h1[property=name]').text
        self.story.setMetadata('title',title)

        # Find authorid and URL from... author url.
        mt_card_social = soup.find(None,{'class':'mt-card-social'})
        author_link = mt_card_social('a')[-1]
        if author_link:
            authorId = author_link['href'].rsplit('/', 1)[1]
            self.story.setMetadata('authorId', authorId)
            self.story.setMetadata('authorUrl','https://'+self.host+'/user/profile/'+authorId)

        self.story.setMetadata('author',soup.find(attrs=dict(property="books:author"))['content'])


        chapters = soup.find('table',{'id':'chapters'}).find('tbody')
        tds = [tr.findAll('td')[0] for tr in chapters.findAll('tr')]
        for td in tds:
            chapterUrl = 'https://' + self.getSiteDomain() + td.a['href']
            self.add_chapter(td.text, chapterUrl)


        # this is forum based so it's a bit ugly
        description = soup.find('div', {'property': 'description', 'class': 'hidden-content'})
        self.setDescription(url,description)

        dates = [tr.findAll('td')[1] for tr in chapters.findAll('tr')]
        self.story.setMetadata('dateUpdated', self.make_date(dates[-1]))
        self.story.setMetadata('datePublished', self.make_date(dates[0]))

        for a in soup.find_all('a',{'property':'genre'}): # not all stories have genre
            genre = stripHTML(a)
            if not "Unspecified" in genre:
                self.story.addToList('genre',genre)

        for label in [stripHTML(a) for a in soup.find_all('span', {'class':'label'})]:
            if 'COMPLETED' == label:
                self.story.setMetadata('status', 'Completed')
            elif 'ONGOING' == label:
                self.story.setMetadata('status', 'In-Progress')
            elif 'HIATUS' == label:
                self.story.setMetadata('status', 'Hiatus')
            elif 'STUB' == label:
                self.story.setMetadata('status', 'Stub')
            elif 'DROPPED' == label:
                self.story.setMetadata('status', 'Dropped')
            elif 'Fan Fiction' == label:
                self.story.addToList('category', 'FanFiction')
            elif 'Original' == label:
                self.story.addToList('category', 'Original')

        # 'rating' in FFF speak means G, PG, Teen, Restricted, etc.
        # 'stars' is used instead for RR's 1-5 stars rating.
        stars=soup.find(attrs=dict(property="books:rating:value"))['content']
        self.story.setMetadata('stars',stars)
        logger.debug("stars:(%s)"%self.story.getMetadata('stars'))

        warning = soup.find('strong',text='Warning')
        if warning != None:
            for li in warning.find_next('ul').find_all('li'):
                self.story.addToList('warnings',stripHTML(li))

        # get cover
        img = soup.find(None,{'class':'row fic-header'}).find('img')
        if img:
            cover_url = img['src']
            self.setCoverImage(url,cover_url)
                    # some content is show as tables, this will preserve them

        itag = soup.find('i',title='Story Length')
        if itag and itag.has_attr('data-content'):
            # "calculated from 139,112 words"
            m = re.search(r"calculated from (?P<words>[0-9,]+) words",itag['data-content'])
            if m:
                self.story.setMetadata('numWords',m.group('words'))

    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        ## httplib max headers removed Jan 2021--not seeing it
        ## anymore, they probably fixed their site.  See
        ## https://github.com/JimmXinu/FanFicFare/pull/174 for
        ## original details.
        soup = self.make_soup(self.get_request(url))

        div = soup.find('div',{'class':"chapter-inner chapter-content"})

        # TODO: these stories often have tables in, but these wont render correctly
        # defaults.ini output CSS now outlines/pads the tables, at least. 

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        if self.getConfig("include_author_notes",True):
            # collect both first, changing div for frontnote first
            # causes confusion in the tree.
            frontnote = div.find_previous('div', {'class':'author-note-portlet'})
            endnote = div.find_next('div', {'class':'author-note-portlet'})
            if frontnote:
                # move frontnote into chapter text div.
                div.insert(0,frontnote.extract())
            if endnote:
                # move endnote into chapter text div.
                div.append(endnote.extract())

        return self.utf8FromSoup(url,div)
