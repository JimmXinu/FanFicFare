#  -*- coding: utf-8 -*-

import time
import logging
logger = logging.getLogger(__name__)
import re
import urllib2

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return AsianFanFicsComAdapter


logger = logging.getLogger(__name__)

class AsianFanFicsComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = ""
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[3])

        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))

            # normalized story URL.
            self._setURL('http://' + self.getSiteDomain() + '/story/view/'+self.story.getMetadata('storyId'))
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','asnff')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y-%b-%d"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.asianfanfics.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/story/view/123456 http://"+cls.getSiteDomain()+"/story/view/123456/story-title-here http://"+cls.getSiteDomain()+"/story/view/123456/1"

    def getSiteURLPattern(self):
        return r"https?://"+re.escape(self.getSiteDomain())+r"/story/view/0*(?P<id>\d+)"

    def performLogin(self, url, soup):
        params = {}
        if self.password:
            params['username'] = self.username
            params['password'] = self.password
        else:
            params['username'] = self.getConfig("username")
            params['password'] = self.getConfig("password")
        params['from_url'] = url
        params['csrf_aff_token'] = soup.find('input',{'name':'csrf_aff_token'})['value']
        loginUrl = 'https://' + self.getSiteDomain() + '/login/index'
        logger.info("Will now login to URL (%s) as (%s)" % (loginUrl, params['username']))

        d = self._postUrl(loginUrl, params, usecache=False)

        if params['username'] not in d: # check if username is mentioned in output (logged in as, var visitorName, etc.)
            logger.info("Failed to login to URL %s as %s" % (loginUrl, params['username']))
            raise exceptions.FailedToLogin(url,params['username'])
            return False
        else:
            return True

    def doAdultCheck(self, url, soup):
        check = soup.find('form',{'action':'/account/toggle_age'})
        if check:
            logger.debug("Found adult check")
            if self.is_adult or self.getConfig("is_adult"):
                contentFilter = check.find('a',{'href':'/account/mark_over_18'}) #two different types of adult checks
                if contentFilter:
                    loginUrl = 'http://' + self.getSiteDomain() + '/account/mark_over_18'
                    self._fetchUrl(loginUrl)
                else:
                    params = {}
                    params['csrf_aff_token'] = check.find('input',{'name':'csrf_aff_token'})['value']
                    params['is_of_age'] = '1'
                    params['current_url'] = '/story/view/' + self.story.getMetadata('storyId')
                    loginUrl = 'http://' + self.getSiteDomain() + '/account/toggle_age'
                    self._postUrl(loginUrl,params)

                data = self._fetchUrl(url,usecache=False)
                soup = self.make_soup(data)
                if "Are you over 18 years old" in data:
                    raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
                else:
                    return soup
            else:
                raise exceptions.AdultCheckRequired(self.url)
        else:
            return False

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def doExtractChapterUrlsAndMetadata(self,get_cover=True):
        url = self.url
        logger.info("url: "+url)

        try:
            data = self._fetchUrl(url)

        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        # it is best to log in whenever possible, unless already logged in from cache..
        if self.password or self.getConfig("password") and "Logout" not in data:
            self.performLogin(url,soup)
            data = self._fetchUrl(url,usecache=False)
            soup = self.make_soup(data)
        else:
            logger.info('Note: Logging in is highly recommended, as this website censors text if not logged in.')

        # adult check
        self.checkSoup = self.doAdultCheck(url,soup)
        if self.checkSoup:
            soup = self.checkSoup

        ## Title
        a = soup.find('h1', {'id': 'story-title'})
        self.story.setMetadata('title',stripHTML(a))

        # Find authorid and URL from... author url.
        mainmeta = soup.find('footer', {'class': 'main-meta'})
        alist = mainmeta.find('span', text='Author(s)')
        alist = alist.parent.findAll('a', href=re.compile(r"/profile/view/\d+"))
        for a in alist:
            self.story.addToList('authorId',a['href'].split('/')[-1])
            self.story.addToList('authorUrl','http://'+self.host+a['href'])
            self.story.addToList('author',a.text)

        newestChapter = None
        self.newestChapterNum = None
        # Find the chapters:
        chapters=soup.find('select',{'name':'chapter-nav'})
        chapters=chapters.findAll('option')
        self.story.setMetadata('numChapters',len(chapters))
        for index, chapter in enumerate(chapters):
            if chapter.text != 'Foreword': # skip the foreword
                self.chapterUrls.append((stripHTML(chapter.text),'http://' + self.getSiteDomain() + chapter['value'])) # note: AFF cuts off chapter names in list. this gets kind of fixed later on
        # find timestamp
        a = soup.find('span', text='Updated')
        if a == None:
            a = soup.find('span', text='Published') # use published date if work was never updated
        a = a.parent.find('time')
        chapterDate = makeDate(a['datetime'],self.dateformat)
        if newestChapter == None or chapterDate > newestChapter:
            newestChapter = chapterDate
            self.newestChapterNum = index

        # story status
        a = mainmeta.find('span', text='Completed')
        if a:
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        # story description
        a = soup.find('div', {'id':'story-description'})
        if a:
            self.setDescription(url,a)

        # story tags
        a = mainmeta.find('span',text='Tags')
        if a:
            tags = a.parent.findAll('a')
            for tag in tags:
                self.story.addToList('tags', tag.text)

        # story tags
        a = mainmeta.find('span',text='Characters')
        if a:
            self.story.addToList('characters', a.nextSibling)

        # published on
        a = soup.find('span', text='Published')
        a = a.parent.find('time')
        self.story.setMetadata('datePublished', makeDate(a['datetime'], self.dateformat))

        # updated on
        a = soup.find('span', text='Updated')
        if a:
            a = a.parent.find('time')
            self.story.setMetadata('dateUpdated', makeDate(a['datetime'], self.dateformat))

        # upvote, subs, and views
        a = soup.find('div',{'class':'title-meta'})
        spans = a.findAll('span', recursive=False)
        self.story.addToList('upvotes', re.search('\(([^)]+)', spans[0].find('span').text).group(1))
        self.story.addToList('subscribers', re.search('\(([^)]+)', spans[1].find('span').text).group(1))
        if enumerate(spans) == 2: # views can be private
            self.story.addToList('views', spans[2].find('span').text.split()[0])

        # cover art in the form of a div before chapter content
        if get_cover:
            cover_url = ""
            a = soup.find('div',{'id':'bodyText'})
            a = a.find('div',{'class':'text-center'})
            if a:
                cover_url = a.find('img')['src']
                if a:
                    self.setCoverImage(url,cover_url)

    # grab the text for an individual chapter
    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)

        data = self._fetchUrl(url)
        soup = self.make_soup(data)

        # have to do adult check here as well because individual chapters can be marked as mature
        if not self.checkSoup:
            self.checkSoup = self.doAdultCheck(url,soup)
            if self.checkSoup:
                soup = self.checkSoup

        # grab contents
        content = soup.find('div', {'id': 'user-submitted-body'})
        if content:
            if self.getConfig('inject_chapter_title'):
                logger.debug("Injecting full-length chapter title")
                newTitle = soup.find('h1', {'id' : 'chapter-title'}).text
                newTitle = self.make_soup('<h3>%s</h3>' % (newTitle)) # the dumbest workaround ever for the abbreviated chapter titles from before
                newTitle.append(content)
                return self.utf8FromSoup(url,newTitle)
            else:
                return self.utf8FromSoup(url,content)
        else:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
