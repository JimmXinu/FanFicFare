# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team
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

import datetime
import logging
import re
import urllib2
from urllib import unquote

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter, utf8FromSoup, makeDate

def getClass():
    return GayAuthorsAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class GayAuthorsAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.decode = ["utf8",
                       "Windows-1252"] # 1252 is a superset of iso-8859-1.
                               # Most sites that claim to be
                               # iso-8859-1 (and some that claim to be
                               # utf8) are really windows-1252.
        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False
       
		
        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[3])
        logging.debug("storyId: (%s)"%self.story.getMetadata('storyId'))

        # unqoute, change '_' and ' ' to '-', downcase, and remove non-[a-z0-9-]
        authid = unquote(self.parsedUrl.path.split('/',)[2])
        authid = authid.lower().replace('_','-').replace(' ','-')
        authid = re.sub(r"[^a-z0-9-]","",authid)
        
        self.story.setMetadata('authorId',authid)
        logging.debug("authorId: (%s)"%self.story.getMetadata('authorId'))
        
        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/story/'+self.story.getMetadata('authorId') + '/' + self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','ga')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d %b %Y"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.gayauthors.org'

    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/story/author/storytitle"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/story/")+r".*?/\w+.*?$"

    

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):


        url = self.url
        logging.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e


            
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.
        msoup = soup.find('div', {'class' : 'story'})
        if msoup == None:
            msoup = soup.find('div', {'class' : 'story ispinned'})
        csoup = soup.find('div', {'id' : 'story_chapters'})
        
        ## Title
        a = msoup.find('span', {'class' : 'title'})
        title=a.find('span', {'itemprop' : 'name'})
        self.story.setMetadata('title',title.text)
        try:
            # Find Series name from series URL.
            series = a.find('span',{'class':"description"})
            series_name = series.find('a')
            series_name.extract()
            series_index = int(series.text.split(' ')[1])
            self.setSeries(series_name.text, series_index)
            
        except:
            # I find it hard to care if the series parsing fails
            pass
        
        # Find authorid and URL from... author url.
        a = msoup.find('a', href=re.compile(r'/author/'+self.story.getMetadata('authorId')))
        self.story.setMetadata('authorUrl',a['href'])
        self.story.setMetadata('author',a.text)
		

        # Find the chapters:
        spans=csoup.findAll('span', {'class' : 'desc chapter-info'})
        for span in spans:
            span.extract()
        for chapter in csoup.findAll('a'):
            # just in case there's tags, like <i> in chapter titles.
            a=chapter['href'].split(self.story.getMetadata('author'))
            a=a[0]+self.story.getMetadata('authorId')+a[1]
            self.chapterUrls.append((stripHTML(chapter),a))


        self.story.setMetadata('numChapters',len(self.chapterUrls))
		
        cats = msoup.findAll('a', href=re.compile(r'/browse/list/page__filtertype_0__category\w+$'))
        for cat in cats:
            self.story.addToList('category',cat.text)
		
        genres = msoup.findAll('a', href=re.compile(r'/browse/list/page__filtertype_1__genre\w+$'))
        for genre in genres:
            self.story.addToList('genre',genre.text)
        genres = msoup.findAll('a', href=re.compile(r'/browse/list/page__filtertype_2__tag\w+$'))
        for genre in genres:
            self.story.addToList('genre',genre.text)
			
        status = msoup.find('a', href=re.compile(r'/browse/list/page__filtertype_3__status\w+$'))
        self.story.setMetadata('status',status.text)
		
        rating = msoup.find('a', href=re.compile(r'/browse/list/page__filtertype_4__rating\w+$'))
        self.story.setMetadata('rating',rating.text)
		
        summary = msoup.find('span', {'itemprop' : 'description'})
        self.story.setMetadata('description',summary.text)
	

        stats = msoup.find('dl',{'class':'info'})
        dt = stats.findAll('dt')
        dd = stats.findAll('dd')
        for x in range(0,len(dt)):
            label = dt[x].text
            value = dd[x].text

            if 'Words:' in label:
                self.story.setMetadata('numWords', value)

            if 'Published:' in label:
                date=stripHTML(value.split(' - ')[0])
                if ',' in date:
                    date=datetime.date.today().strftime(self.dateformat)
                self.story.setMetadata('datePublished', makeDate(date, self.dateformat))
				
            if 'Updated:' in label:
                date=stripHTML(value.split(' - ')[0])
                if ',' in date:
                    date=datetime.date.today().strftime(self.dateformat)
                self.story.setMetadata('dateUpdated', makeDate(date, self.dateformat))
            
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logging.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulStoneSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        
        div = soup.find('div', {'id' : 'chapter-content'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return utf8FromSoup(div)
