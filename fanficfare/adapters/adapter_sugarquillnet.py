# -*- coding: utf-8 -*-

# Copyright 2012 Fanficdownloader team, 2018 FanFicFare team
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
#############################################################################
### Adapted by GComyn
### Original - November 23, 2016
### Updateed - November 24,2016
###         Fixed chapter determination. Some stories had another form in the
###         first chapter, so had to change that section.
#############################################################################
### Updateed - November 25,2016
###         some of the stories have extra formatting that makes the heuristics
###         take a long gime to process. I've removed as much of the extra
###         formatting as I thought I could.
#############################################################################
from __future__ import absolute_import
import logging
logger = logging.getLogger(__name__)
import re
import sys

from bs4.element import Comment
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter, makeDate

def getClass():
    return SugarQuillNetAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class SugarQuillNetAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only storyid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])

        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/read.php?storyid='+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','sq')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%m/%d/%y"


    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.sugarquill.net'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/read.php?storyid=1234"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/read.php?storyid=")+r"\d+"

    ## Getting the chapter list and the meta data
    def extractChapterUrlsAndMetadata(self):

        # index=1 makes sure we see the story chapter index.  Some
        # sites skip that for one-chapter stories.
        url = self.url+'&chapno=1'
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(url)
            else:
                raise e

        if "Invalid storyid or chapno" in data:
            raise exceptions.AccessDenied(self.getSiteDomain() +" says: Invalid storyid or chapno.")

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        # Now go hunting for all the meta data and the chapter list.

        ## Title
        a = soup.find('b',text='Story').nextSibling.string.strip(':').strip()
        self.story.setMetadata('title',a)

        # Find authorid and URL from... author url.
        a = soup.find('b',text='Author').nextSibling.nextSibling
        self.story.setMetadata('authorId',a['href'].split('id=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',a.string.replace("(Professors' Bookshelf)",'').strip())

        # Find the chapters:
        chapters = soup.find('select',{'name':'chapno'}).findAll('option')
        for chapter in chapters:
            if chapter.string == 'Default':
                chapter.string = 'Chapter 1'
            self.add_chapter(chapter.string, '{0}&chapno={1}'.format(self.url,chapter['value']))


        ## This site doesn't have much metadata, so we will get what we can.
        ## The metadata is all on the author's page, so we have to get it to parse.
        author_Url = self.story.getMetadata('authorUrl').replace('&amp;','&')
        logger.debug('Getting the author page: {0}'.format(author_Url))
        try:
            adata = self._fetchUrl(author_Url)
        except HTTPError as e:
            if e.code in 404:
                raise exceptions.StoryDoesNotExist("Author Page: Code: 404. {0}".format(author_Url))
            elif e.code == 410:
                raise exceptions.StoryDoesNotExist("Author Page: Code: 410. {0}".format(author_Url))
            else:
                raise e

        if 'Invalid authorid' in adata:
            raise exceptions.StoryDoesNotExist('{0} says: Invalid authorid'.format(self.getSiteDomain()))

        asoup = self.make_soup(adata)

        lc2 = asoup.find('a', href=re.compile(r'read.php\?storyid='+self.story.getMetadata('storyId')))
        lc2 = lc2.findPrevious('table')
        summry = stripHTML(lc2.find('td',{'class':'highlightcolor2'})).strip()
        self.setDescription(url,summry)

        lupdt = lc2.findAll('td',{'class':'highlightcolor1'})[1].string.replace('Last updated','').strip()
        self.story.setMetadata('dateUpdated', makeDate(lupdt, self.dateformat))

        self._setURL('http://' + self.getSiteDomain() + '/read.php?storyid='+self.story.getMetadata('storyId')+'&chapno=1')
        ## and that is all of the metadata that is on this site...

    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))

        chap = soup.find('td',{'class':'content_pane'})

        if chap == None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        ## some chapters have a table at the beginning, which we shall remove.
        for tag in chap.findAll('table'):
            #tag.extract()
            tag.decompose()

        ## some stories have extra formatting... going to try to remove as much as possible.
        for tag in chap.findAll('style') + chap.findAll("o:p"):
            #tag.extract()
            tag.decompose()

        #strip comments from soup
        [comment.extract() for comment in chap.findAll(text=lambda text:isinstance(text, Comment))]

        ## these tags seem to cause the h
        for tag in chap.findAll('o:smarttagtype'):
            tag.name = 'span'
            tag.attrs = None     #delte all attributes

        for tag in chap.findAll('p') + chap.findAll('b') + chap.findAll('i') + chap.findAll('em') + chap.findAll('strong') + chap.findAll('span'):
            tag.attrs = None     #delte all attributes
            if tag.string == '=':
                tag.replace_with("'")

        for tag in chap.findAll('span'):
            tag.attrs = None     #delte all attributes
            if tag.findAll(True) == None:
                if tag.string == '=':
                    tag.replace_with("'")

        chap.name = 'div' # don't want a bare <td> without a table.
        return self.utf8FromSoup(url,chap)
