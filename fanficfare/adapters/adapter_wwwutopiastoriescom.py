# -*- coding: utf-8 -*-

# Copyright 2012 Fanficdownloader team, 2020 FanFicFare team
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
####################################################################################################
### Adapted by GComyn on November 28, 2016
### Updated on November 29, 2016
###     Corrected for no author name.
###     Added check to see if the story has been removed by author
###
### Updated on December 18, 2016
###     Updated format as per linter, and added documentation
####################################################################################################
from __future__ import absolute_import
'''
This site is much link fictionmania, in that there is only one chapter per
story, so we only have the one url to get information from.
We get the category from the author's page
'''
import logging
logger = logging.getLogger(__name__)
import re

from bs4.element import Comment

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.parse import quote

from .base_adapter import BaseSiteAdapter, makeDate

def getClass():
    return WWWUtopiastoriesComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class WWWUtopiastoriesComAdapter(BaseSiteAdapter):

    ################################################################################################
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/')[-1].replace('.html',''))


        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/code/show_story/recid/' +
            self.story.getMetadata('storyId') + '.html')

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','gaggedutopia')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%m/%d/%Y"


    ################################################################################################
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.utopiastories.com'

    ################################################################################################
    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/code/show_story/recid/1234.html"

    ################################################################################################
    def getSiteURLPattern(self):
        return r"https?"+re.escape("://"+self.getSiteDomain())+r"/code/show_story(.asp)?/recid/\d+(.html)?$"

    ################################################################################################
    def extractChapterUrlsAndMetadata(self):
        ''' Getting the chapter list and the meta data, plus 'is adult' checking. '''

        ## This is an adult site, so if they have not set their is_adult in the personal.ini, it will
        ## fail
        if not (self.is_adult or self.getConfig("is_adult")):
            raise exceptions.AdultCheckRequired(
                'This is an adult site. You need to be an adult to download from here.')

        url = self.url
        logger.debug("URL: "+url)

        data = self.get_request(url)

        if "Latest Stories" in data:
            raise exceptions.StoryDoesNotExist("The url '{0}' is not on site '{1}'".format(
                url, self.getSiteDomain()))
        elif "The author as requested this story be removed from publication." in data:
            raise exceptions.StoryDoesNotExist(
                "{0} says: The author as requested this story be removed from publication.".format(
                    self.getSiteDomain()))

        soup = self.make_soup(data)


        ## Title
        a = unicode(soup.find('title')).replace(":: GaggedUtopia's Story Archive",'').strip()
        self.story.setMetadata('title',stripHTML(a))

        # Find the chapters:
        ## This site is a 1 story/page site, so I'm setting the chapter to the entered url and
        # the status to complete
        self.add_chapter('',url)
        self.story.setMetadata('status', 'Completed')


        for detail in soup.findAll('li'):
            det = unicode(detail).replace(u"\xa0",'')
            heading = stripHTML(det).split(' - ')[0]
            text = stripHTML(det).replace(heading+' - ','')
            # logger.debug(heading)
            # logger.debug(text)
            if 'Author' in heading:
                a = detail.find('a')
                if 'mailto' in unicode(a):
                    self.story.setMetadata('authorId','0000000000')
                    self.story.setMetadata('authorUrl',self.url)
                    self.story.setMetadata('author','Unknown')
                    self.story.setMetadata('category','Unknown')
                else:
                    self.story.setMetadata('authorId',a['href'].split('/')[2])
                    self.story.setMetadata('author',a.string)
                    self.story.setMetadata('authorUrl','http://'+self.host+'/'+
                                           a['href'].replace('../..','code'))
            elif 'Story Codes' in heading:
                tags = text.replace('Story Codes - ','')
                for tag in tags.split(', '):
                    self.story.addToList('eroticatags',tag)
            elif 'Post Date' in heading:
                self.story.setMetadata('datePublished', makeDate(text, self.dateformat))
            elif 'Rating' in heading:
                ## this is a numerical rating for the story.
                ## [ 4.49 actual/195 vote(s) ]
                self.story.setMetadata('siterating_votes',text[2:-2])
                self.story.setMetadata('siterating',text.split(' ')[1])
            elif 'Site Rank' in heading:
                ## This is a numerical value that shows where in the list of stories
                ## the current story is ranked
                ## 333 of 2955
                self.story.setMetadata('siterank_of',text)
                self.story.setMetadata('siterank',text.split(' ')[0])
            elif 'Unique Views' in heading:
                ## This is the number of times the story has bee viewed.
                self.story.setMetadata('views',text)
            elif 'PDF Download' in heading:
                ## This is a link to download the PDF.
                pass

        ## The only way to get the category is from the author's page, but if there is no author to
        ## get, we can't set it.
        if self.story.getMetadata('author') != 'Unknown':
            adata = self.get_request(self.story.getMetadata('authorUrl'))
            asoup = self.make_soup(adata)
            storyblock = asoup.find('a',href=re.compile(r"/code/show_story/recid/"+
                self.story.getMetadata('storyId')))
            if storyblock != None:
                td = storyblock.findNext('td')
                self.story.setMetadata('category',td.string)

        # since the 'story' is one page, I am going to save the soup here, so we can use iter
        # to get the story text in the getChapterText function, instead of having to retrieve
        # it again.
        self.html = soup

    ################################################################################################
    def getChapterText(self, url):
        ''' grab the text for an individual chapter. '''

        logger.debug('Using the html retrieved previously from: %s' % url)

        story = self.html.findAll('table')[0].findAll('td')[0].find('div')

        if None == story:
            raise exceptions.FailedToDownload(
                "Error downloading Chapter: %s!  Missing required element!" % url)

        ## Removing the scripts, tables, links and divs from the story
        for tag in (story.findAll('script') + story.findAll('table') + story.findAll('a') +
            story.findAll('div')):
            tag.extract()

       #strip comments from story
        [comment.extract() for comment in story.findAll(text=lambda text:isinstance(text, Comment))]

        return self.utf8FromSoup(url,story)
