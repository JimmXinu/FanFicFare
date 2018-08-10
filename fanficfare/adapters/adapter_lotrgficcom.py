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
##############################################################################
###  Adapted by GComyn
###  Completed on November, 22, 2016
##############################################################################
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

class LOTRgficComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.story.setMetadata('siteabbrev','lotrgfic')

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])


        # normalized story URL.
        self._setURL('https://' + self.getSiteDomain() + '/viewstory.php?sid='+self.story.getMetadata('storyId'))


    @staticmethod
    def getSiteDomain():
        return 'www.lotrgfic.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return r"https?://"+re.escape(self.getSiteDomain()+"/viewstory.php?sid=")+r"\d+$"

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    def extractChapterUrlsAndMetadata(self):

        if self.is_adult or self.getConfig("is_adult"):
            addurl = "&warning=3"
        else:
            addurl=""

        url = self.url+'&index=1'+addurl
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        if "Content is only suitable for mature adults. May contain explicit language and adult themes. Equivalent of NC-17." in data:
            raise exceptions.AdultCheckRequired(self.url)
        elif "Access denied. This story has not been validated by the adminstrators of this site." in data:
            raise exceptions.AccessDenied(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        ### Main Content for the Table Of Contents page.
        div = soup.find('div',{'id':'maincontent'})
        
        divfooter = div.find('div',{'id':'footer'})
        if divfooter != None:
            divfooter.extract()

        ## Title
        a = div.find('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"$"))
        self.story.setMetadata('title',stripHTML(a))

        # Find authorid and URL from... author url.
        a = div.find('a', href=re.compile(r"viewuser.php"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','https://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',a.string)

        # Find the chapters:
        for chapter in div.findAll('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"&chapter=\d+$")):
            # just in case there's tags, like <i> in chapter titles.
            self.add_chapter(chapter,'https://'+self.host+'/'+chapter['href']+addurl)


        ### Metadata is contained
        
        def defaultGetattr(d,k):
            try:
                return d[k]
            except:
                return ""

        # <span class="label">Rated:</span> NC-17<br /> etc
        ### This site has the metadata formatted all over the place, 
        ### so we have to do some very cludgy programming to get it.
        ### If someone can do it better, please do so, and let us know.
        ## I'm going to leave this section in, so we can get those 
        ## elements that are "formatted correctly".
        labels = soup.findAll('span',{'class':'label'})
        for labelspan in labels:
            value = labelspan.nextSibling
            label = labelspan.string

            if 'Summary' in label:
                ## the summary is not encased in a span label... so we can't do anything here.
                ## I'm going to leave it here just in case.
                ## Everything until the next span class='label'
                svalue = ''
                while value and 'label' not in defaultGetattr(value,'class'):
                    svalue += unicode(value)
                    value = value.nextSibling
                # sometimes poorly formated desc (<p> w/o </p>) leads
                # to all labels being included.
                svalue=svalue[:svalue.find('<span class="label">')]
                self.setDescription(url,svalue)

            if 'Rated' in label:
                self.story.setMetadata('rating', value)

            if 'Word count' in label:
                self.story.setMetadata('numWords', value)

            if 'Categories' in label:
                cats = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=categories'))
                catstext = [cat.string for cat in cats]
                for cat in catstext:
                    self.story.addToList('category',cat.string)

            if 'Characters' in label:
                chars = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=characters'))
                charstext = [char.string for char in chars]
                for char in charstext:
                    self.story.addToList('characters',char.string)

            if 'Genre' in label:
                genres = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=class&type_id=1'))
                genrestext = [genre.string for genre in genres]
                self.genre = ', '.join(genrestext)
                for genre in genrestext:
                    self.story.addToList('genre',genre.string)

            if 'Warnings' in label:
                warnings = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=class&type_id=4'))
                warningstext = [warning.string for warning in warnings]
                self.warning = ', '.join(warningstext)
                for warning in warningstext:
                    self.story.addToList('warnings',warning.string)

            if 'Places' in label:
                places = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=class&type_id=2'))
                placestext = [place.string for place in places]
                self.warning = ', '.join(placestext)
                for place in placestext:
                    self.story.addToList('places',place.string)

            if 'Times' in label:
                times = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=class&type_id=3'))
                timestext = [time.string for time in times]
                self.warning = ', '.join(timestext)
                for time in timestext:
                    self.story.addToList('times',time.string)

            if 'Completed' in label:
                if 'Yes' in value:
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')

            if 'Published' in label:
                self.story.setMetadata('datePublished', makeDate(value.strip(), "%d %b %Y"))

            if 'Updated' in label:
                # there's a stray [ at the end.
                #value = value[0:-1]
                self.story.setMetadata('dateUpdated', makeDate(value.strip(), "%d %b %Y"))

        try:
            # Find Series name from series URL.
            a = soup.find('a', href=re.compile(r"viewseries.php\?seriesid=\d+"))
            series_name = a.string
            series_url = 'https://'+self.host+'/'+a['href']

            # use BeautifulSoup HTML parser to make everything easier to find.
            seriessoup = self_make_soup(self._fetchUrl(series_url))
            storyas = seriessoup.findAll('a', href=re.compile(r'^viewstory.php\?sid=\d+$'))
            i=1
            for a in storyas:
                if a['href'] == ('viewstory.php?sid='+self.story.getMetadata('storyId')):
                    self.setSeries(series_name, i)
                    self.story.setMetadata('seriesUrl',series_url)
                    break
                i+=1

        except:
            # I find it hard to care if the series parsing fails
            pass
        
        ## Now we are going to cludge together the rest of the metadata
        metad = soup.findAll('p',{'class':'smaller'})
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
            
        ### Rating is not enclosed in a label, only in a p tag classed 'smaller' so...
        ratng = metad[0].find('strong').get_text().replace('Rated','').strip()
        self.story.setMetadata('rating', ratng)
        
        ## No we try to get the summary... it's not within it's own 
        ## dedicated tag, so we have to split some hairs..
        ## This may not work every time... but I tested it with 6 stories...
        mdata = metad[0]
        while '<hr/>' not in unicode(mdata.nextSibling):
            mdata = mdata.nextSibling
        self.setDescription(url,mdata.previousSibling.previousSibling.get_text())
        
        ### the rest of the metadata are not in tags at all... so we have to be really cludgy.
        ## we don't need the rest of them, so we get rid of all but the last one
        metad = metad[-1]
        ## we also don't need any of the links in here, so we'll get rid of them as well.
        links = metad.findAll('a')
        for link in links:
            link.extract()
        ## and we've already done the labels, so let's remove them
        labels = metad.findAll('span',{'class':'label'})
        for label in labels:
            label.extract()
        ## now we should only have text and <br>'s... somthing like this:
            #<p class="smaller">Categories:
            #<br/>
            #Characters: , , ,
            #<br/>
            # , <br/> <br/> <br/> None<br/>
            #Challenges: None
            #<br/>
            #Series: None
            #<br/>
            #Chapters: 1 ┬á┬á | ┬á┬á Word count: 200 ┬á┬á | ┬á┬á Read Count: 767
            #<br/>
            #Completed: Yes ┬á┬á | ┬á┬á Updated: 04/27/13 ┬á┬á | ┬á┬á Published: 04/27/13
            #<br/>
            #</p>
        ## we'll have to remove the non-breaking spaces to get this to work.
        metad = unicode(metad).replace(u"\xa0",'').replace('\n','')
        for txt in metad.split('<br/>'):
            if 'Challenges:' in txt:
                txt = txt.replace('Challenges:','').strip()
                self.story.setMetadata('challenges', txt)
            elif 'Series:' in txt:
                txt = txt.replace('Series:','').strip()
                self.story.setMetadata('challenges', txt)
            elif 'Chapters:' in txt:
                for txt2 in txt.split('|'):
                    txt2 = txt2.replace('\n','').strip()
                    if 'Word count:' in txt2:
                        txt2 = txt2.replace('Word count:','').strip()
                        self.story.setMetadata('numWords', value)
                    elif 'Read Count:' in txt2:
                        txt2= txt2.replace('Read Count:','').strip()
                        self.story.setMetadata('readings', value)
            elif 'Completed:' in txt:
                for txt2 in txt.split('|'):
                    txt2 = txt2.strip()
                    if 'Completed:' in txt2:
                        if 'Yes' in txt2:
                            self.story.setMetadata('status', 'Completed')
                        else:
                            self.story.setMetadata('status', 'In-Progress')
                    elif 'Updated:' in txt2:
                        txt2= txt2.replace('Updated:','').strip()
                        self.story.setMetadata('dateUpdated', makeDate(txt2.strip(), "%b/%d/%y"))
                    elif 'Published:' in txt2:
                        txt2= txt2.replace('Published:','').strip()
                        self.story.setMetadata('datePublished', makeDate(txt2.strip(), "%b/%d/%y"))
        

    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        data = self._fetchUrl(url)
        # problems with some stories, but only in calibre.  I suspect
        # issues with different SGML parsers in python.  This is a
        # nasty hack, but it works.
        data = data[data.index("<body"):]

        soup = self.make_soup(data)

        span = soup.find('div', {'id' : 'maincontent'})
        
        # Everything is encased in the maincontent section, so we have
        # to remove as much as we can systematically
        tables = span.findAll('table')
        for table in tables:
            table.extract()
            
        headings = span.findAll('h3')
        for heading in headings:
            heading.extract()
            
        links = span.findAll('a')
        for link in links:
            link.extract()
        
        forms = span.findAll('form')
        for form in forms:
            form.extract()

        divs = span.findAll('div')
        for div in divs:
            div.extract()
        
        if None == span:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,span)

def getClass():
    return LOTRgficComAdapter

