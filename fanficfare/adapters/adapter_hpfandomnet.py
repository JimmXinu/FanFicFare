# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2015 FanFicFare team
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

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

# This function is called by the downloader in all adapter_*.py files
# in this dir to register the adapter class.  So it needs to be
# updated to reflect the class below it.  That, plus getSiteDomain()
# take care of 'Registering'.
def getClass():
    return HPFandomNetAdapterAdapter # XXX

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class HPFandomNetAdapterAdapter(BaseSiteAdapter): # XXX

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
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])


        # normalized story URL.
        # XXX Most sites don't have the /eff part.  Replace all to remove it usually.
        self._setURL('http://' + self.getSiteDomain() + '/eff/viewstory.php?sid='+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','hpfdm') # XXX

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y.%m.%d" # XXX

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.hpfandom.net' # XXX

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/eff/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/eff/viewstory.php?sid=")+r"\d+$"

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        url = self.url
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.

        # set first URL
        a = soup.find('a', href=re.compile(r"viewstory.php\?sid=\d+"))
        ## href = "javascript:if (confirm('Slash/het fiction which incorporates sexual situations to a somewhat graphic degree  as well as graphic violent situations.  ')) location = 'viewstory.php?sid=49111&i=1'"
        m = re.match(r'.*?(viewstory.php\?sid=\d+)',a['href'])
        self._setURL('http://'+self.host+'/eff/'+m.group(1))
        if self.parsedUrl.query.split('=',)[1] != self.story.getMetadata('storyId'):
            self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])
            url = self.url
            logger.debug("reset URL: "+url)
            try:
                data = self._fetchUrl(url)
            except urllib2.HTTPError, e:
                if e.code == 404:
                    raise exceptions.StoryDoesNotExist(self.url)
                else:
                    raise e

            # use BeautifulSoup HTML parser to make everything easier to find.
            soup = self.make_soup(data)

#        self.story.setMetadata('storyId', re.compile(self.getSiteURLPattern()).match(a).group('storyId'))

        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"viewuser.php\?uid=\d+"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/eff/'+a['href'])
        self.story.setMetadata('author',a.string)

        ## Going to get the rest from the author page.
        authdata = self._fetchUrl(self.story.getMetadata('authorUrl'))
        # fix a typo in the site HTML so I can find the Characters list.
        authdata = authdata.replace('<td width=10%">','<td width="10%">')

        if "javascript:if (confirm('Slash/het fiction which incorporates sexual situations to a somewhat graphic degree  as well as graphic violent situations.  ')) location = 'viewstory.php?sid=%s&i=1'"%self.story.getMetadata('storyId') in authdata \
                and not (self.is_adult or self.getConfig("is_adult")):
            raise exceptions.AdultCheckRequired(self.url)

        authsoup = self.make_soup(authdata)

        reviewsa = authsoup.find_all('a', href=re.compile(r"reviews\.php\?sid="+self.story.getMetadata('storyId')+r".*"))
        # <table><tr><td><p><b><a ...>
        metablock = reviewsa[0].findParent("table")
        #print("metablock:%s"%metablock)
        self.story.setMetadata('reviews',stripHTML(reviewsa[-1]))

        ## Title
        titlea = metablock.find('a', href=re.compile("viewstory.php"))
        #print("titlea:%s"%titlea)
        if titlea == None:
            raise exceptions.FailedToDownload("Story URL (%s) not found on author's page, can't use chapter URLs"%url)
        self.story.setMetadata('title',stripHTML(titlea))

        total_reads = 0
        # Find the chapters: !!! hpfandom.net differs from every other
        # eFiction site--the sid on viewstory for chapters is
        # *different* for each chapter
        for chapter in soup.findAll('a', {'href':re.compile(r"viewstory.php\?sid=\d+&i=\d+")}):
            m = re.match(r'.*?(viewstory.php\?sid=\d+&i=\d+).*?',chapter['href'])
            # just in case there's tags, like <i> in chapter titles.
            #print("====chapter===%s"%m.group(1))
            self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+'/eff/'+m.group(1)))
            try:
                total_reads += int(stripHTML((chapter.find_parent('tr').find_all('td')[-1])))
            except:
                pass # don't care
        if len(self.chapterUrls) == 0:
            self.chapterUrls.append((stripHTML(self.story.getMetadata('title')),url))

        if total_reads > 0:
            self.story.setMetadata('reads',total_reads)

        self.story.setMetadata('numChapters',len(self.chapterUrls))

        # eFiction sites don't help us out a lot with their meta data
        # formating, so it's a little ugly.

        # utility method
        def defaultGetattr(d,k):
            try:
                return d[k]
            except:
                return ""

        summary = metablock.find("td",{"class":"summary"})
        summary.name='span'
        self.setDescription(url,summary)

        # words & completed in first row of metablock.
        firstrow = stripHTML(metablock.find('tr'))
        # A Mother's Love xx Going Grey 1 (G+) by Kiristeen | Reviews - 18 | Words: 27468 | Completed: Yes
        m = re.match(r".*?\((?P<rating>[^)]+)\).*?Words: (?P<words>\d+).*?Completed: (?P<status>Yes|No)",firstrow)
        if m != None:
            if m.group('rating') != None:
                self.story.setMetadata('rating', m.group('rating'))

            if m.group('words') != None:
                self.story.setMetadata('numWords', m.group('words'))

            if m.group('status') != None:
                if 'Yes' in m.group('status'):
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')


        # <tr><td width="10%" valign="top">Chapters:</td><td width="40%" valign="top">4</td>
        # <td width="10%" valign="top">Published:</td><td width="40%" valign="top">2010.09.29</td></tr>
        # <tr><td width="10%" valign="top">Completed:</td><td width="40%" valign="top">Yes</td><td width="10%" valign="top">Updated:</td><td width="40%" valign="top">2010.10.03</td></tr>
        labels = metablock.findAll('td',{'width':'10%'})
        for td in labels:
            label = td.string
            value = td.nextSibling.string
            #print("\nlabel:%s\nvalue:%s\n"%(label,value))

            if 'Category' in label and value:
                cats = td.parent.findAll('a',href=re.compile(r'categories.php'))
                catstext = [cat.string for cat in cats]
                for cat in catstext:
                    self.story.addToList('category',cat.string)

            if 'Characters' in label and value: # this site can have Character label with no
                                                # values, apparently.  Others as a precaution.
                for char in value.split(','):
                    self.story.addToList('characters',char.strip())

            if 'Genre' in label and value:
                for genre in value.split(','):
                    self.story.addToList('genre',genre.strip())

            if 'Warnings' in label and value:
                for warning in value.split(','):
                    if warning.strip() != 'none':
                        self.story.addToList('warnings',warning.strip())

            if 'Published' in label:
                self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))

            if 'Updated' in label:
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))

    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        data = self._fetchUrl(url)
        # There's no good wrapper around the chapter text. :-/
        # There are, however, tables with width=100% just above and below the real text.
        data = re.sub(r'<table width="100%">.*?</table>','<div name="storybody">',
                      data,count=1,flags=re.DOTALL)

        data = re.sub(r'<table width="100%">.*?</table>','</div>',
                      data,count=1,flags=re.DOTALL)

        soup = self.make_soup(data)

        div = soup.find("div",{'name':'storybody'})
        #print("\n\ndiv:%s\n\n"%div)

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
        return self.utf8FromSoup(url,div)
