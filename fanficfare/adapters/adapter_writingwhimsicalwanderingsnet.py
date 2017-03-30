# -*- coding: utf-8 -*-

# Copyright 2012 Fanficdownloader team, 2017 FanFicFare team
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

# Software: eFiction
import time
import logging
logger = logging.getLogger(__name__)
import re
import urllib2
import sys

from bs4.element import Comment
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter, makeDate

def getClass():
    return WritingWhimsicalwanderingsNetAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class WritingWhimsicalwanderingsNetAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])


        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/viewstory.php?sid='+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','wwnet')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%m/%d/%y"


    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'writing.whimsicalwanderings.net'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/viewstory.php?sid=")+r"\d+$"

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        # index=1 makes sure we see the story chapter index.  Some
        # sites skip that for one-chapter stories.
        url = self.url+'&index=1'
        logger.debug("URL: "+url)
        if self.is_adult or self.getConfig("is_adult"):
            addurl = '&ageconsent=ok&warning=4'
        else:
            addurl= ''
            
        try:
            data = self._fetchUrl(url+addurl)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(url)
            else:
                raise e

        if "Access denied. This story has not been validated by the adminstrators of this site." in data:
            raise exceptions.AccessDenied(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        # Now go hunting for all the meta data and the chapter list.

        ## Title
        a = soup.find('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"$"))
        self.story.setMetadata('title',stripHTML(a))

        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"viewuser.php\?uid=\d+"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+a['href'])
        self.story.setMetadata('author',a.string)

        # Find the chapters:
        for chapter in soup.findAll('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"&chapter=\d+$")):
            # just in case there's tags, like <i> in chapter titles.
            self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+'/'+chapter['href']))

        self.story.setMetadata('numChapters',len(self.chapterUrls))

		## This site's metadata is not very well formatted... so we have to cludge a bit..
		## The only ones I see that are, are Relationships and Warnings... 
        ## However, the categories, characters, and warnings are all links, so we can get them easier
        
        ## Categories don't have a proper label, but do use links, so...
        cats = soup.findAll('a',href=re.compile(r'browse.php\?type=categories'))
        catstext = [cat.string for cat in cats]
        for cat in catstext:
            if cat != None:
                self.story.addToList('category',cat.string)
        ## Characters don't have a proper label, but do use links, so...
        chars = soup.findAll('a',href=re.compile(r'browse.php\?type=characters'))
        charstext = [char.string for char in chars]
        for char in charstext:
            if char != None:
                self.story.addToList('characters',char.string)
        ## Warnings do have a proper label, but we will use links anyway
        warnings = soup.findAll('a',href=re.compile(r'browse.php\?type=class&type_id=2'))
        warningstext = [warning.string for warning in warnings]
        for warning in warningstext:
            if warning != None:
                self.story.addToList('warnings',warning.string)
        
        ## Relationships do have a proper label, but we will use links anyway
        ## this is actually tag information ... m/f, gen, m/m and such.
        ## so I'm putting them in the extratags section.
        relationships = soup.findAll('a',href=re.compile(r'browse.php\?type=class&type_id=1'))
        relationshipstext = [relationship.string for relationship in relationships]
        for relationship in relationshipstext:
            if relationship != None:
                self.story.addToList('ships',relationship.string)

        ## I know I'm replacing alot of <br>'s here, but I want to make sure that they are all
        ## the same, so we can split the string correctly.
        metad = soup.find('div',{'class':'listbox'})
        metad = str(metad.renderContents()).replace('\n',' ').replace('<br>','|||||||').replace('<br/>','|||||||').replace('<br />','|||||||').strip()
        while '||||||||' in metad:
            metad = metad.replace('||||||||','|||||||')
        metad = stripHTML(metad)
        
        for mdata in metad.split('|||||||'):
            mdata = mdata.strip()
            if mdata.startswith('Summary:'):
                self.setDescription(url,mdata[8:].strip())
            elif mdata.startswith('Rating'):
                temp = mdata[:mdata.find('[')].replace('Rating:','')
                self.story.setMetadata('rating', temp)
            elif mdata.startswith('Series'):
                pass
            elif mdata.startswith('Chapters'):
                temp = mdata.split('Completed:')[1]
                if 'Yes' in stripHTML(temp):
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')
            elif mdata.startswith('Word Count'):
                self.story.setMetadata('numWords',mdata.replace('Word Count:','').strip())
            elif mdata.startswith('Published'):
                temp = mdata.split('Updated:')
                self.story.setMetadata('datePublished', makeDate(temp[0].replace('Published:','').strip(), self.dateformat))
                self.story.setMetadata('dateUpdated', makeDate(temp[1].strip(), self.dateformat))
        # Find Series name from series URL.
        a = soup.find('a', href=re.compile(r"viewseries.php\?seriesid=\d+"))
        if a != None:
            series_name = a.string
            try:
                series_url = 'http://'+self.host+'/'+a['href']

                # use BeautifulSoup HTML parser to make everything easier to find.
                seriessoup = self.make_soup(self._fetchUrl(series_url))
                # can't use ^viewstory...$ in case of higher rated stories with javascript href.
                storyas = seriessoup.findAll('a', href=re.compile(r'viewstory.php\?sid=\d+'))
                i=1
                for a in storyas:
                    # skip 'report this' and 'TOC' links
                    if 'contact.php' not in a['href'] and 'index' not in a['href']:
                        if a['href'] == ('viewstory.php?sid='+self.story.getMetadata('storyId')):
                            self.setSeries(series_name, i)
                            self.story.setMetadata('seriesUrl',series_url)
                            break
                        i+=1

            except:
                self.setSeries(series_name,0)
                pass
        
        storynotes = soup.find('blockquote')
        if storynotes != None:
            storynotes = stripHTML(storynotes).replace('Story Notes:','')
            self.story.setMetadata('storynotes',storynotes)

    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))

        div = soup.find('div', {'id' : 'story'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,div)
