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

import time
import logging
logger = logging.getLogger(__name__)
import re
import urllib2
import cookielib as cl

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

# Search for XXX comments--that's where things are most likely to need changing.

# This function is called by the downloader in all adapter_*.py files
# in this dir to register the adapter class.  So it needs to be
# updated to reflect the class below it.  That, plus getSiteDomain()
# take care of 'Registering'.
def getClass():
    return PortkeyOrgAdapter # XXX

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class PortkeyOrgAdapter(BaseSiteAdapter): # XXX

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.decode = ["Windows-1252",
                       "utf8"] # 1252 is a superset of iso-8859-1.
                               # Most sites that claim to be
                               # iso-8859-1 (and some that claim to be
                               # utf8) are really windows-1252.
        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False
        
        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])
        logger.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
        
        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/story/'+self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','prtky') # XXX

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d/%m/%y" # XXX
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'fanfiction.portkey.org' # XXX

    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/story/1234"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/story/")+r"\d+(/\d+)?$"

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        url = self.url
        logger.debug("URL: "+url)

        # portkey screws around with using a different URL to set the
        # cookie and it's a pain.  So... cheat!
        if self.is_adult or self.getConfig("is_adult"):
            cookieproc = urllib2.HTTPCookieProcessor()
            cookie = cl.Cookie(version=0, name='verify17', value='1',
                               port=None, port_specified=False,
                               domain=self.getSiteDomain(), domain_specified=False, domain_initial_dot=False,
                               path='/', path_specified=True,
                               secure=False,
                               expires=time.time()+10000,
                               discard=False,
                               comment=None,
                               comment_url=None,
                               rest={'HttpOnly': None},
                               rfc2109=False)
            cookieproc.cookiejar.set_cookie(cookie)
            self.opener = urllib2.build_opener(cookieproc)        

        try:
            data = self._fetchUrl(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        if "You must be over 18 years of age to view it" in data: # XXX 
            raise exceptions.AdultCheckRequired(self.url)
            
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)
        #print data

        # Now go hunting for all the meta data and the chapter list.
        
        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"/profile/\d+"))
        #print("======a:%s"%a)
        self.story.setMetadata('authorId',a['href'].split('/')[-1])
        self.story.setMetadata('authorUrl','http://'+self.host+a['href'])
        self.story.setMetadata('author',a.string)

        ## Going to get the rest from the author page.
        authsoup = bs.BeautifulSoup(self._fetchUrl(self.story.getMetadata('authorUrl')))
        
        ## Title
        titlea = authsoup.find('a', href=re.compile(r'/story/'+self.story.getMetadata('storyId')+"$"))
        self.story.setMetadata('title',stripHTML(titlea))
        metablock = titlea.parent
        
        # Find the chapters:
        for chapter in soup.find('select',{'name':'select5'}).findAll('option', {'value':re.compile(r'/story/'+self.story.getMetadata('storyId')+"/\d+$")}):
            # just in case there's tags, like <i> in chapter titles.
            chtitle = stripHTML(chapter)
            if not chtitle:
                chtitle = "(Untitled Chapter)"
            self.chapterUrls.append((chtitle,'http://'+self.host+chapter['value']))
            
        if len(self.chapterUrls) == 0:
            self.chapterUrls.append((stripHTML(self.story.getMetadata('title')),url))

        self.story.setMetadata('numChapters',len(self.chapterUrls))

        # eFiction sites don't help us out a lot with their meta data
        # formating, so it's a little ugly.

        # utility method
        def defaultGetattr(d,k):
            try:
                return d[k]
            except:
                return ""
        # <SPAN class="dark-small-bold">Contents:</SPAN> <SPAN class="small-grey">NC17 </SPAN> 
        # <SPAN class="dark-small-bold">Published: </SPAN><SPAN class="small-grey">12/11/07</SPAN>
        # <SPAN class="dark-small-bold"><BR>
        # Description:</SPAN> <SPAN class="small-black">A special book helps Harry tap into the power the Dark Lord knows not.  Of course it’s a book on sex magic and rituals… but Harry’s not complaining.  Spurned on by the ghost of a pervert founder, Harry leads his friends in the hunt for Voldemort’s Horcruxes.
        # EROTIC COMEDY!  Loads of crude humor and sexual situations!
        # </SPAN>
        labels = metablock.findAll('span',{'class':'dark-small-bold'})
        for labelspan in labels:
            value = labelspan.findNext('span').string
            label = stripHTML(labelspan)
#            print("\nlabel:%s\nlabel:%s\nvalue:%s\n"%(labelspan,label,value))

            if 'Description' in label:
                self.setDescription(url,value)

            if 'Contents' in label:
                self.story.setMetadata('rating', value)

            if 'Words' in label:
                self.story.setMetadata('numWords', value)

            # if 'Categories' in label:
            #     cats = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=categories'))
            #     catstext = [cat.string for cat in cats]
            #     for cat in catstext:
            #         self.story.addToList('category',cat.string)

            # if 'Characters' in label:
            #     chars = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=characters'))
            #     charstext = [char.string for char in chars]
            #     for char in charstext:
            #         self.story.addToList('characters',char.string)

            if 'Genre' in label:
                # genre is typo'ed on the site--it falls between the
                # dark-small-bold label and dark-small-bold content
                # spans.
                svalue = ""
                value = labelspan.nextSibling
                while not defaultGetattr(value,'class') == 'dark-small-bold':
                    svalue += str(value)
                    value = value.nextSibling
                    
                for genre in svalue.split("/"):
                    genre = genre.strip()
                    if genre != 'None':
                        self.story.addToList('genre',genre)

            ## Not all sites use Warnings, but there's no harm to
            ## leaving it in.  Check to make sure the type_id number
            ## is correct, though--it's site specific.
            # if 'Warnings' in label:
            #     warnings = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=class&type_id=2')) # XXX
            #     warningstext = [warning.string for warning in warnings]
            #     self.warning = ', '.join(warningstext)
            #     for warning in warningstext:
            #         self.story.addToList('warnings',warning.string)

            if 'Status' in label:
                if 'Completed' in value:
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')

            if 'Published' in label:
                self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))
            
            if 'Updated' in label:
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))

        # try:
        #     # Find Series name from series URL.
        #     a = metablock.find('a', href=re.compile(r"viewseries.php\?seriesid=\d+"))
        #     series_name = a.string
        #     series_url = 'http://'+self.host+'/'+a['href']

        #     # use BeautifulSoup HTML parser to make everything easier to find.
        #     seriessoup = bs.BeautifulSoup(self._fetchUrl(series_url))
        #     storyas = seriessoup.findAll('a', href=re.compile(r'^viewstory.php\?sid=\d+$'))
        #     i=1
        #     for a in storyas:
        #         if a['href'] == ('viewstory.php?sid='+self.story.getMetadata('storyId')):
        #             self.setSeries(series_name, i)
        #             break
        #         i+=1            
        # except:
        #     # I find it hard to care if the series parsing fails
        #     pass
            
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)
        data = self._fetchUrl(url)
        soup = bs.BeautifulStoneSoup(data,
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.

        #print("soup:%s"%soup)
        tag = soup.find('td', {'class' : 'story'})
        if tag == None and "<center><b>Chapter does not exist!</b></center>" in data:
            print("Chapter is missing at: %s"%url)
            return  self.utf8FromSoup(url,bs.BeautifulStoneSoup("<div><p><center><b>Chapter does not exist!</b></center></p><p>Chapter is missing at: <a href='%s'>%s</a></p></div>"%(url,url)))
        tag.name='div' # force to be a div to avoid problems with nook.

        centers = tag.findAll('center')
        # first two and last two center tags are some script, 'report
        # story', 'report story' and an ad.
        centers[0].extract()
        centers[1].extract()
        centers[-1].extract()
        centers[-2].extract()

        if None == tag:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return self.utf8FromSoup(url,tag)
