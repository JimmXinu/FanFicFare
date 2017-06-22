# -*- coding: utf-8 -*-

# Copyright 2013 Fanficdownloader team, 2015 FanFicFare team
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

import logging
logger = logging.getLogger(__name__)
import re
import urllib2

#
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return StoriesOnlineNetAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class StoriesOnlineNetAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        logger.debug("StoriesOnlineNetAdapter.__init__ - url='%s'" % url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2].split(':')[0])
        if 'storyInfo' in self.story.getMetadata('storyId'):
            self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])

        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/s/'+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev',self.getSiteAbbrev())

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y-%m-%d"

    @classmethod
    def getSiteAbbrev(self):
        return 'strol'

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'storiesonline.net'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/s/1234 http://"+cls.getSiteDomain()+"/s/1234:4010"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain())+r"/(s|library)/(storyInfo.php\?id=)?(?P<id>\d+)((:\d+)?(;\d+)?$|(:i)?$)?"

    ## Login seems to be reasonably standard across eFiction sites.
    def needToLoginCheck(self, data):
        if self.needToLogin \
                or 'Free Registration' in data \
                or "Invalid Password!" in data \
                or "Invalid User Name!" in data \
                or "Log In" in data \
                or "Access to unlinked chapters requires" in data:
            self.needToLogin = True
        return self.needToLogin

    def performLogin(self, url):
        params = {}

        if self.password:
            params['theusername'] = self.username
            params['thepassword'] = self.password
        else:
            params['theusername'] = self.getConfig("username")
            params['thepassword'] = self.getConfig("password")
        params['rememberMe'] = '1'
        params['page'] = 'http://'+self.getSiteDomain()+'/'
        params['submit'] = 'Login'

        loginUrl = 'https://' + self.getSiteDomain() + '/sol-secure/login.php'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['theusername']))

        d = self._fetchUrl(loginUrl, params,usecache=False)

        if "My Account" not in d : #Member Account
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['theusername']))
            raise exceptions.FailedToLogin(url,params['theusername'])
            return False
        else:
            return True

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def doExtractChapterUrlsAndMetadata(self, get_cover=True):

        # index=1 makes sure we see the story chapter index.  Some
        # sites skip that for one-chapter stories.
        url = self.url
        logger.debug("URL: "+url)

        self.needToLogin = False
        try:
            data = self._fetchUrl(url+":i")
        except urllib2.HTTPError, e:
            if e.code in (404, 410):
                raise exceptions.StoryDoesNotExist("Code: %s: %s"%(e.code,self.url))
            elif e.code == 401:
                self.needToLogin = True
                data = ''
            else:
                raise e

        if self.needToLoginCheck(data):
            # need to log in for this one.
            self.performLogin(url)
            try:
                data = self._fetchUrl(url+":i",usecache=False)
            except urllib2.HTTPError, e:
                if e.code in (404, 410):
                    raise exceptions.StoryDoesNotExist("Code: %s: %s"%(e.code,self.url))
                elif e.code == 401:
                    self.needToLogin = True
                    data = ''
                else:
                    raise e

        if "Access denied. This story has not been validated by the adminstrators of this site." in data:
            raise exceptions.AccessDenied(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")
        elif "Error! The story you're trying to access is being filtered by your choice of contents filtering." in data:
            raise exceptions.FailedToDownload(self.getSiteDomain() +" says: Error! The story you're trying to access is being filtered by your choice of contents filtering.")
        elif "Error! Daily Limit Reached" in data or "Sorry! You have reached your daily limit of" in data:
            raise exceptions.FailedToDownload(self.getSiteDomain() +" says: Error! Daily Limit Reached")

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)
        #print data

        # Now go hunting for all the meta data and the chapter list.

        ## Title
        a = soup.find('h1')
        self.story.setMetadata('title',stripHTML(a))

        # Find authorid and URL from... author url.
        nav_section = soup.find('nav')
        for a in nav_section.findAll('a', {'rel' : 'author'}):
            self.story.addToList('authorId',a['href'].split('/')[2])
            self.story.addToList('authorUrl','http://'+self.host+a['href'])
            self.story.addToList('author',stripHTML(a).replace("'s Page",""))

        # The rest of the metadata is within the article tag.
        soup = soup.find('article')

        # Find the chapters:
        chapters = soup.findAll('a', href=re.compile(r'^/s/'+self.story.getMetadata('storyId')+":\d+(/.*)?$"))
        if len(chapters) != 0:
            logger.debug("Number of chapters: {0}".format(len(chapters)))
            for chapter in chapters:
                # just in case there's tags, like <i> in chapter titles.
                self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+chapter['href']))
        else:
            self.chapterUrls.append((self.story.getMetadata('title'),'http://'+self.host+'/s/'+self.story.getMetadata('storyId')))

        self.story.setMetadata('numChapters',len(self.chapterUrls))

        self.getStoryMetadataFromAuthorPage()

        # Some books have a cover in the index page.
        # Samples are:
        #     http://storiesonline.net/s/11999
        #     http://storiesonline.net/s/10823
        if get_cover:
            # logger.debug("Looking for the cover image...")
            cover_url = ""
            img = soup.find('img')
            if img:
                cover_url=img['src']
            # logger.debug("cover_url: %s"%cover_url)
            if cover_url:
                self.setCoverImage(url,cover_url)

        # Remove all the metadata elements to leave and preamble text. This is usually 
        # a notice or a forward.
        if len(self.chapterUrls) > 1:
            header = soup.find('header')
            header.extract()
        else:
            soup = soup.find('header')
        # Remove some tags based on their class or id
        elements_to_remove = ['#det-link', '#s-details', '#index-list', '#s-title', '#s-auth', '.copy']
        if not self.getConfig('include_images'):
            elements_to_remove.append('img')
        for element_name in elements_to_remove:
            elements = soup.select(element_name)
            for element in elements:
                element.extract()
        if len(soup.contents ) > 0 and (len(soup.text.strip()) > 0 or len(soup.find_all('img')) > 0):
            self.story.setMetadata('notice', self.utf8FromSoup(url, soup))


    def getStoryMetadataFromAuthorPage(self):
        # surprisingly, the detailed page does not give enough details, so go to author's page
        story_row = self.findStoryRow('tr')
        self.has_universes = False

        title_cell = story_row.find('td', {'class' : 'lc2'})
        for cat in title_cell.findAll('div', {'class' : 'typediv'}):
            self.story.addToList('genre',cat.text)

        # in lieu of word count.
        self.story.setMetadata('size', story_row.find('td', {'class' : 'num'}).text)

        score = story_row.findNext('th', {'class' : 'ynum'}).text
        if score != '-':
            self.story.setMetadata('score', score)

        description_element = story_row.findNext('td', {'class' : 'lc4'})

        self.parseDescriptionField(description_element)
        
        self.parseOtherAttributes(description_element)


    def findStoryRow(self, row_class='tr'):
        page=0
        story_found = False
        while not story_found:
            page = page + 1
            try:
                data = self._fetchUrl(self.story.getList('authorUrl')[0] + "/" + unicode(page))
            except urllib2.HTTPError, e:
                if e.code == 404:
                    raise exceptions.FailedToDownload("Story not found in Author's list--change Listings Theme back to Classic")
            asoup = self.make_soup(data)

            story_row = asoup.find(row_class, {'id' : 'sr' + self.story.getMetadata('storyId')})
            if story_row:
                logger.debug("Found story row on page %d" % page)
                story_found = True
                self.has_universes = "/universes" in data
                break
            
        return story_row


    def parseDescriptionField(self, description_element):
        # Parse the description field for the series or universe and the 
        # actual description.
        
        desc = description_element.contents[0]
        try:
            a = description_element.find('a', href=re.compile(r"/series/\d+/.*"))
            # logger.debug("Looking for series - a='{0}'".format(a))
            if a:
                # if there's a number after the series name, series_contents is a two element list:
                # [<a href="...">Title</a>, u' (2)']
                series_contents = a.parent.contents
                i = 0 if len(series_contents) == 1 else series_contents[1].strip(' ()')
                seriesUrl = 'http://'+self.host+a['href']
                self.story.setMetadata('seriesUrl',seriesUrl)
                series_name = stripHTML(a)
                # logger.debug("Series name= %s" % series_name)
                series_soup = self.make_soup(self._fetchUrl(seriesUrl))
                if series_soup:
                    # logger.debug("Retrieving Series - looking for name")
                    series_name = stripHTML(series_soup.find('h1', {'id' : 'ptitle'}))
                    series_name = re.sub(r' . a series by.*$','',series_name)
                    # logger.debug("Series name: '%s'" % series_name)
                self.setSeries(series_name, i)
                desc = description_element.contents[2]
                # Check if series is in a universe
                if self.has_universes:
                    universe_url = self.story.getList('authorUrl')[0]  + "&type=uni"
                    universes_soup = self.make_soup(self._fetchUrl(universe_url) )
                    # logger.debug("Universe url='{0}'".format(universe_url))
                    if universes_soup:
                        universes = universes_soup.findAll('div', {'class' : 'ser-box'})
                        # logger.debug("Number of Universes: %d" % len(universes))
                        for universe in universes:
                            # logger.debug("universe.find('a')={0}".format(universe.find('a')))
                            # The universe id is in an "a" tag that has an id but nothing else. It is the first tag.
                            # The id is prefixed with the letter "u".
                            universe_id = universe.find('a')['id'][1:]
                            # logger.debug("universe_id='%s'" % universe_id)
                            universe_name = stripHTML(universe.find('div', {'class' : 'ser-name'})).partition(' ')[2]
                            # logger.debug("universe_name='%s'" % universe_name)
                            # If there is link to the story, we have the right universe
                            story_a = universe.find('a', href=re.compile('/s/'+self.story.getMetadata('storyId')))
                            if story_a:
                                # logger.debug("Story is in a series that is in a universe! The universe is '%s'" % universe_name)
                                self.story.setMetadata("universe", universe_name)
                                self.story.setMetadata('universeUrl','http://'+self.host+ '/library/universe.php?id=' + universe_id)
                                break
                    else:
                        logger.debug("No universe page")
        except:
            raise
            pass
        try:
            a = description_element.find('a', href=re.compile(r"/universe/\d+/.*"))
            # logger.debug("Looking for universe - a='{0}'".format(a))
            if a:
                self.story.setMetadata("universe",stripHTML(a))
                desc = description_element.contents[2]
                # Assumed only one universe, but it does have a URL--use universeHTML
                universe_name = stripHTML(a)
                universeUrl = 'http://'+self.host+a['href']
                # logger.debug("Retrieving Universe - about to get page - universeUrl='{0}".format(universeUrl))
                universe_soup = self.make_soup(self._fetchUrl(universeUrl))
                logger.debug("Retrieving Universe - have page")
                if universe_soup:
                    logger.debug("Retrieving Universe - looking for name")
                    universe_name = stripHTML(universe_soup.find('h1', {'id' : 'ptitle'}))
                    universe_name = re.sub(r' . A Universe from the Mind.*$','',universe_name)
                    # logger.debug("Universes name: '{0}'".format(universe_name))

                self.story.setMetadata('universeUrl',universeUrl)
                # logger.debug("Setting universe name: '{0}'".format(universe_name))
                self.story.setMetadata('universe',universe_name)
                if self.getConfig("universe_as_series"):
                    self.setSeries(universe_name, 0)
                    self.story.setMetadata('seriesUrl',universeUrl)
            else:
                logger.debug("Do not have a universe")
        except:
            raise
            pass

        self.setDescription('http://'+self.host+'/s/'+self.story.getMetadata('storyId'),desc)


    def parseOtherAttributes(self, other_attribute_element):
        for b in other_attribute_element.findAll('b'):
            #logger.debug('Getting metadata: "%s"' % b)
            label = b.text
            if label in ['Posted:', 'Concluded:', 'Updated:']:
                value = b.findNext('noscript').text
                #logger.debug('Have a date field label: "%s", value: "%s"' % (label, value))
            else:
                value = b.nextSibling
            #logger.debug('label: "%s", value: "%s"' % (label, value))

            if 'Sex' in label:
                self.story.setMetadata('rating', value)
            if 'Score' in label and value != '-':
                self.story.setMetadata('score', value)

            if 'Tags' in label or 'Codes' in label:
                for code in re.split(r'\s*,\s*', value.strip()):
                    self.story.addToList('sitetags', code)
            if 'Genre' in label:
                for code in re.split(r'\s*,\s*', value.strip()):
                    self.story.addToList('genre', code)
            
            if 'Posted' in label:
                self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))
            if 'Concluded' in label:
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))
            if 'Updated' in label:
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))
        
        status = other_attribute_element.find('span', {'class':'ab'})
        if status != None:
            if 'Incomplete and Inactive' in status.text:
                self.story.setMetadata('status', 'Incomplete')
            else:
                self.story.setMetadata('status', 'In-Progress')
            if "Last Activity" in status.text:
                # date is passed as a timestamp and converted in JS.
                value = status.findNext('noscript').text
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))
        else:
            self.story.setMetadata('status', 'Completed')


    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))

        # The story text is wrapped in article tags. Most of the page header and
        # footer are outside of this.
        chaptertag = soup.find('article')

        # some big chapters are split over several pages
        pager = chaptertag.find('div', {'class' : 'pager'})

        self.cleanPage(chaptertag)

        if pager != None:

            urls=pager.findAll('a')
            urls=urls[:len(urls)-1]
            # logger.debug("pager urls:%s"%urls)
            pager.extract()

            for ur in urls:
                soup = self.make_soup(self._fetchUrl("http://"+self.getSiteDomain()+ur['href']))

                pagetag = soup.find('article')

                self.cleanPage(pagetag)

                for tag in pagetag.contents[1:]:
                    chaptertag.append(tag)


        if None == chaptertag:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,chaptertag)

    def cleanPage(self,pagetag):
        "Consolidate 'page' clean up code so it can be called."
#         logger.debug("cleanPage start: {0}".format(pagetag))

        # Strip te header section
        tag = pagetag.find('header')
        if tag:
            #logger.debug("remove before header: {0}".format(tag))
            tag.extract()

        # some big chapters are split over several pages
        # remove FIRST pager and everything before it.
        tag = pagetag.find('div', {'class' : 'pager'})
        while tag != None:
            # logger.debug("remove before pager: {0}".format(tag))
            prev = tag.previousSibling
            tag.extract()
            tag = prev

        # Find the "Continues" marker on the current page and
        # remove everything after that.  This is actually
        # effecting the *previous* 'page'.  EXCEPT!--they are
        # putting a 'conTag' at the *top* now, too.  So this
        # was nuking every page but the first and last.  Now
        # only if 'Continues'
        for contag in pagetag.findAll('span', {'class' : 'conTag'}):
            # remove everything after continues...
            if 'Continuation' in contag.text:
                tag = contag
                while tag != None:
                    # logger.debug("remove before Continuation: {0}".format(tag))
                    prev = tag.previousSibling
                    tag.extract()
                    tag = prev
            elif 'Continues' in contag.text:
                tag = contag
                while tag != None:
                    # logger.debug("remove after Continues: {0}".format(tag))
                    nxt = tag.nextSibling
                    tag.extract()
                    tag = nxt

        # some big chapters are split over several pages
        # remove LAST pager and everything before it.
        # Only needed on last page.
        tag = pagetag.find('div', {'class' : 'pager'})
        while tag != None:
            # logger.debug("remove after pager: {0}".format(tag))
            nxt = tag.nextSibling
            tag.extract()
            tag = nxt

        # If it is a chapter, there are dates at the start for when it was posted or modified. These plus
        # everything before them can be discarded.
        postedDates = pagetag.findAll('div', {'class' : 'date'})
        if postedDates:
            a = postedDates[0].previousSibling
            while a != None:
                # logger.debug("before dates: {0}".format(a))
                b = a.previousSibling
                a.extract()
                a = b
            for a in pagetag.findAll('div', {'class' : 'date'}):
                a.extract()

        # Kill the vote form and everything after it.
        a = pagetag.find('div', {'class' : 'vform'})
        # logger.debug("Chapter end= '{0}'".format(a))
        while a != None:
            b = a.nextSibling
            a.extract()
            a=b

        # For chapters, remove next chapter link and everything after it
        a = pagetag.find('h3', {'class' : 'end'})
        # logger.debug("Chapter end= '{0}'".format(a))
        while a != None:
            b = a.nextSibling
            a.extract()
            a=b

