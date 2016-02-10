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

import time
import logging
logger = logging.getLogger(__name__)
import re
import urllib2


from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return FineStoriesComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class FineStoriesComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2].split(':')[0])
        if 'storyInfo' in self.story.getMetadata('storyId'):
            self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])

        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/s/storyInfo.php?id='+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','fnst')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y-%m-%d"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'finestories.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/s/1234 http://"+cls.getSiteDomain()+"/s/1234:4010 http://"+cls.getSiteDomain()+"/library/storyInfo.php?id=1234"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain())+r"/(s|library)?/(storyInfo.php\?id=)?\d+(:\d+)?(;\d+)?$"

    ## Login seems to be reasonably standard across eFiction sites.
    def needToLoginCheck(self, data):
        if 'Free Registration' in data \
                or "Invalid Password!" in data \
                or "Invalid User Name!" in data:
            return True
        else:
            return False

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

        loginUrl = 'http://' + self.getSiteDomain() + '/login.php'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['theusername']))

        d = self._fetchUrl(loginUrl, params)

        if "My Account" not in d : #Member Account
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['theusername']))
            raise exceptions.FailedToLogin(url,params['theusername'])
            return False
        else:
            return True

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        # index=1 makes sure we see the story chapter index.  Some
        # sites skip that for one-chapter stories.
        url = self.url
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        if self.needToLoginCheck(data):
            # need to log in for this one.
            self.performLogin(url)
            data = self._fetchUrl(url)

        if "Access denied. This story has not been validated by the adminstrators of this site." in data:
            raise exceptions.AccessDenied(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.

        ## Title
        a = soup.find('a', href=re.compile(r'/s/'+self.story.getMetadata('storyId')))
        self.story.setMetadata('title',stripHTML(a))

        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"/a/\w+"))
        self.story.setMetadata('authorId',a['href'].split('/')[2])
        self.story.setMetadata('authorUrl','http://'+self.host+a['href'])
        self.story.setMetadata('author',a.text)

        # Find the chapters:
        chapters = soup.findAll('a', href=re.compile(r'/s/'+self.story.getMetadata('storyId')+":\d+$"))
        if len(chapters) != 0:
            for chapter in chapters:
                # just in case there's tags, like <i> in chapter titles.
                self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+chapter['href']))
        else:
            self.chapterUrls.append((self.story.getMetadata('title'),'http://'+self.host+'/s/'+self.story.getMetadata('storyId')))

        self.story.setMetadata('numChapters',len(self.chapterUrls))

        # surprisingly, the detailed page does not give enough details, so go to author's page

        skip=0
        i=0
        while i == 0:
            asoup = self.make_soup(self._fetchUrl(self.story.getMetadata('authorUrl')+"&skip="+unicode(skip)))

            tds = asoup.findAll('td', {'class' : 'lc2'})
            for lc2 in tds:
                if lc2.find('a', href=re.compile(r'/s/'+self.story.getMetadata('storyId'))):
                    i=1
                    break
                if tds[len(tds)-1] == lc2:
                    skip=skip+10

        for cat in lc2.findAll('div', {'class' : 'typediv'}):
            self.story.addToList('category',cat.text)

        self.story.setMetadata('size', lc2.findNext('td', {'class' : 'num'}).text)

        lc4 = lc2.findNext('td', {'class' : 'lc4'})

        try:
            a = lc4.find('a', href=re.compile(r"/library/show_series.php\?id=\d+"))
            i = a.parent.text.split('(')[1].split(')')[0]
            self.setSeries(a.text, i)
            self.story.setMetadata('seriesUrl','http://'+self.host+a['href'])
        except:
            pass
        try:
            a = lc4.find('a', href=re.compile(r"/library/universe.php\?id=\d+"))
            self.story.addToList("category",a.text)
        except:
            pass

        for a in lc4.findAll('span', {'class' : 'help'}) + lc4.findAll('script'):
            a.extract()

        self.setDescription('http://'+self.host+'/s/'+self.story.getMetadata('storyId'),lc4.text.split('[More Info')[0])

        for b in lc4.findAll('b'):
            label = b.text
            value = b.nextSibling

            if 'For Age' in label:
                self.story.setMetadata('rating', value)

            if 'Tags' in label:
                for genre in value.split(', '):
                    self.story.addToList('genre',genre)

            ## Site uses a <script> to inject timestamp in locale plus <noscript> general version.
            if 'Posted' in label:
                value = b.find_next_sibling('noscript')
                if '(' in value:
                    date = makeDate(stripHTML(value.split(' (')[0]), self.dateformat)
                else:
                    date = makeDate(stripHTML(value), self.dateformat)
                self.story.setMetadata('datePublished', date)
                self.story.setMetadata('dateUpdated', date)

            if 'Concluded' in label or 'Updated' in label:
                value = b.find_next_sibling('noscript')
                if '(' in value:
                    date = makeDate(stripHTML(value.split(' (')[0]), self.dateformat)
                else:
                    date = makeDate(stripHTML(value), self.dateformat)
                self.story.setMetadata('dateUpdated', date)

        status = lc4.find('span', {'class' : 'ab'})
        if  status != None:
            self.story.setMetadata('status', 'In-Progress')
            if "Last Activity" in status.text:
                self.story.setMetadata('dateUpdated', makeDate(status.text.split('Activity: ')[1].split(')')[0], self.dateformat))
        else:
            self.story.setMetadata('status', 'Completed')


    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))

        div = soup.find('article')

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        # some big chapters are split over several pages
        pager = div.find('span', {'class' : 'pager'})
        if pager != None:
            urls=pager.findAll('a')
            urls=urls[:len(urls)-1]

            for ur in urls:
                soup = self.make_soup(self._fetchUrl("http://"+self.getSiteDomain()+ur['href']))

                div1 = soup.find('article')

                #print("div.contents:%s"%(div.contents,))
                # appending next section
                last=div.findAll('p')
                next=div1.find('span', {'class' : 'conTag'}).nextSibling
                last[len(last)-1]=last[len(last)-1].append(next)

                self.clean_chapter(div1)
                #print("div.contents:%s"%(div.contents,))
                for t in div1.contents:
                    div.append(t)

        self.clean_chapter(div)

        return self.utf8FromSoup(url,div)
    def clean_chapter(self,art):
        # discard included chapter heading.
        # discard included date
        # discard share block
        # continued/continues
        # discard next link
        for tag in art.find_all('h2') + \
                art.find_all('div', class_="date") + \
                art.find_all('div', class_="vform") + \
                art.find_all('span', class_="conTag") + \
                art.find_all('h3', class_="end"):
            tag.extract()

        # remove pager blocks.
        for pager in art.find_all('span', class_="pager"):
            # remove br tags before and after pager.
            #print("br list prev: %s"%len(pager.find_previous_siblings('br')))
            #print("br list next: %s"%len(pager.find_next_siblings('br')))
            for tag in pager.find_next_siblings('br')[:2] + pager.find_previous_siblings('br')[:2]:
                tag.extract()
            pager.extract()
