# -*- coding: utf-8 -*-

# Copyright 2020 FanFicFare team
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
from bs4.element import Tag
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return SilmarillionWritersGuildOrgAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class SilmarillionWritersGuildOrgAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])

        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/archive/home/viewstory.php?sid='+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','swg')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%B %d, %Y"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.silmarillionwritersguild.org'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/archive/home/viewstory.php?sid=123"

    def getSiteURLPattern(self):
        return r"https?://"+re.escape(self.getSiteDomain()+"/archive/home/viewstory.php?sid=")+r"\d+$"

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    ## Getting the chapter list and the meta data
    def extractChapterUrlsAndMetadata(self):

        url = self.url
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        # Now go hunting for all the meta data and the chapter list.

        ## Title and author

        # find story header
        a = soup.find('h6')

        titleLinks = a.find_all('a')
        authorLink= titleLinks[1]

        self.story.setMetadata('authorId',authorLink['href'].split('=')[1])
        self.story.setMetadata('authorUrl','https://'+self.host+'/archive/home/'+authorLink['href'])
        self.story.setMetadata('author',authorLink.string)

        self.story.setMetadata('title',a.find('strong').find('a').get_text())

        # Site does some weird stuff with pagination on series view and will only display 25 stories per page of results
        # Therefor to get accurate index for series, we fetch all sub-pages of series and parse for valid story urls and add to a list,
        # Then find first instance of current story url and use the number of loop itteration for index

        # This is pretty slow but ehh it works

        try:
            # Find Series name from series URL.
            a = soup.find('a', href=re.compile(r"viewseries.php\?seriesid=\d+"))
            if a:
                seriesName = a.string
                seriesUrl = 'https://'+self.host+'/archive/home/'+a['href']

                self.story.setMetadata('seriesUrl',seriesUrl)

                #logger.debug("Series Url: "+seriesUrl)

                # Get Series page and convert to soup
                seriesPageSoup = self.make_soup(self._fetchUrl(seriesUrl+"&offset=0"))
                ## &offset=0 is the same as the first page, by adding
                ## that, the page cache will save us from fetching it
                ## twice in the loop below.

                # Find Series page sub-pages
                seriesPageUrlList = []
                seriesStoryList = []
                for i in seriesPageSoup.findAll('a', href=re.compile(r"viewseries.php\?seriesid=\d+&offset=\d+$")):
                    # Don't include url from next button, is another http request and parse + could cause more bugs!
                    if i.string != '[Next]':
                        seriesPageUrlList.append(i)

                #get urls from all subpages and append to list
                i=1
                for seriesPagePageUrl in seriesPageUrlList:
                    seriesPagePageSoup = self.make_soup(self._fetchUrl('https://'+self.host+'/archive/home/'+seriesPagePageUrl['href']))
                    storyHeaders = seriesPagePageSoup.findAll('h5')
                    ## can't just search for story URLs, some story
                    ## descs also contain story URLs.  Looks like only
                    ## story titles are <h5>.
                    for storyHeader in storyHeaders:
                        seriesPagePageStoryUrl = storyHeader.find('a',href=re.compile(r'^viewstory.php\?sid=\d+$'))
                        if seriesPagePageStoryUrl['href'] == ('viewstory.php?sid='+self.story.getMetadata('storyId')):
                            #logger.debug("Series Name: "+ seriesName)
                            #logger.debug("Series Index: "+i)
                            self.setSeries(seriesName, i)
                            raise StopIteration("Break out of series parsing loops")
                        i+=1

        except StopIteration:
            # break out of both loops, don't need to fetch further
            # pages after story found.
            pass
        except Exception as e:
            logger.warning("series parsing failed(%s)"%e)
            pass

        # Find the chapters by regexing urls
        chapters=soup.findAll('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+r"&chapter=\d+$"))

        if len(chapters)==1:
            self.add_chapter(self.story.getMetadata('title'),'https://'+self.host+'/archive/home/'+chapters[0]['href'])
        else:
            for chapter in chapters:
                # logger.debug("Added Chapter: "+chapter.string)
                self.add_chapter(chapter,'https://'+self.host+'/archive/home/'+chapter['href'])

	# find the details section for the work, will hopefully make parsing metadata a bit easier

        workDetails = soup.find('div', {'id' : 'general'}).find('div', {'id' : 'general'})

        # some metadata can be retrieved through regexes so will do that to try and avoid a janky mess.

        #get characters
        try:
            charList = workDetails.findAll('a', href=re.compile(r'browse.php\?type=characters'+r"&charid=\d+$"))
            for char in charList:
                self.story.addToList('characters',char.string)

        except Exception as e:
            logger.warning("character parsing failed(%s)"%e)

        #get warnings
        try:
            warnList = workDetails.findAll('a', href=re.compile(r'browse.php\?type=class&type_id=2'+r"&classid=\d+$"))
            for warn in warnList:
                self.story.addToList('warnings', warn.string)

        except Exception as e:
            logger.warning("warning parsing failed(%s)"%e)

        #get genres
        try:
            genresList = workDetails.findAll('a', href=re.compile(r'browse.php\?type=class&type_id=1'+r"&classid=\d+$"))
            for genre in genresList:
                self.story.addToList('genre', genre.string)

        except Exception as e:
            logger.warning("genre parsing failed(%s)"%e)

        # no convenient way to extract remaining metadata so bodge it by finding relevant identifier string and using next element as the data source

        #get summary by finding identifier, then itterating until next identifier is found and using data between the two as the summary
        try:
            summaryStart = workDetails.find('strong',text='Summary: ')
            currentElement = summaryStart.parent.next_sibling
            summaryValue = ""
            while not isinstance(currentElement,Tag) or currentElement.name != 'strong':
                summaryValue += unicode(currentElement)
                currentElement = currentElement.next_sibling
                #logger.debug(summaryValue)
            self.setDescription(url,summaryValue)
        except Exception as e:
            logger.warning("summary parsing failed(%s) -- This can be caused by bad HTML in story description."%e)


        #get rating
        try:
            rating = workDetails.find('strong',text='Rated:').next_sibling.string
            self.story.setMetadata('rating', rating)
        except Exception as e:
            logger.warning("rating parsing failed(%s) -- This can be caused by bad HTML in story description."%e)

        #get completion status and correct for consistency with other adapters
        try:
            if (workDetails.find('strong',text='Completed:').next_sibling.string).lower() == "yes":
                status="Completed"

            else:
                status="In-Progress"

            self.story.setMetadata('status', status)
        except Exception as e:
            logger.warning("status parsing failed(%s) -- This can be caused by bad HTML in story description."%e)

        #get wordcount
        try:
            wordCount = workDetails.find('strong',text='Word count:').next_sibling.string
            self.story.setMetadata('numWords', wordCount)
        except Exception as e:
            logger.warning("wordcount parsing failed(%s) -- This can be caused by bad HTML in story description."%e)

        #get published date, this works for some reason yet doesn't without the spaces in it
        try:
            datePublished = workDetails.find('strong',text=' Published: ').next_sibling.string
            self.story.setMetadata('datePublished', makeDate(datePublished, self.dateformat))

        except Exception as e:
            logger.warning("datePublished parsing failed(%s) -- This can be caused by bad HTML in story description."%e)

        #get updated date
        try:
            dateUpdated = workDetails.find('strong',text='Updated:').next_sibling.string
            self.story.setMetadata('dateUpdated', makeDate(dateUpdated, self.dateformat))

        except Exception as e:
            logger.warning("dateUpdated parsing failed(%s) -- This can be caused by bad HTML in story description."%e)

    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        data = self._fetchUrl(url)
        soup = self.make_soup(data)

        # No convenient way to get story without the rest of the page, so get whole page and strip unneeded sections

        contentParent = soup.find('div', {'id' : 'maincontent'}).find('div', {'id' : 'general'})

        contentParent.find('p').decompose() # remove page header
        contentParent.find_all('div',id='general')[2].decompose() #remove page footer
        contentParent.find_all('div',id='general')[0].decompose() #remove chapter select etc.

        contentParent.name='div'

        #error on failure
        if None == contentParent:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,contentParent)
