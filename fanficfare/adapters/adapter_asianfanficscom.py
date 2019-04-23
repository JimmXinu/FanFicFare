#  -*- coding: utf-8 -*-

from __future__ import absolute_import
import logging
logger = logging.getLogger(__name__)
import re
import json
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter,  makeDate

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
            self._setURL('https://' + self.getSiteDomain() + '/story/view/'+self.story.getMetadata('storyId'))
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
        return "https://"+cls.getSiteDomain()+"/story/view/123456 https://"+cls.getSiteDomain()+"/story/view/123456/story-title-here https://"+cls.getSiteDomain()+"/story/view/123456/1"

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
                    loginUrl = 'https://' + self.getSiteDomain() + '/account/mark_over_18'
                    self._fetchUrl(loginUrl)
                else:
                    params = {}
                    params['csrf_aff_token'] = check.find('input',{'name':'csrf_aff_token'})['value']
                    params['is_of_age'] = '1'
                    params['current_url'] = '/story/view/' + self.story.getMetadata('storyId')
                    loginUrl = 'https://' + self.getSiteDomain() + '/account/toggle_age'
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

    def doSubCheck(self, url, soup):
        check = soup.find('div',{'class':'click-to-read-full'})
        if check:
            logger.debug("Subscription required to get all HTML tags")
            #does not work when using https - 403
            subUrl = 'http://' + self.getSiteDomain() + soup.find('a',{'id':'subscribe'})['href']
            self._fetchUrl(subUrl)
            data = self._fetchUrl(url,usecache=False)
            soup = self.make_soup(data)
            check = soup.find('div',{'class':'click-to-read-full'})
            if check:
                raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
            else:
                return soup
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

        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        # it is best to log in whenever possible, unless already logged in from cache..
        loginCheck = soup.find('div',{'id':'login'})
        if self.password or self.getConfig("password") and loginCheck:
            self.performLogin(url,soup)
            data = self._fetchUrl(url,usecache=False)
            soup = self.make_soup(data)
        elif "Logout" not in data:
            logger.info('Note: Logging in is highly recommended, as this website censors text and removes certain HTML tags if not logged in.')

        # adult check
        self.checkSoup = self.doAdultCheck(url,soup)
        if self.checkSoup:
            soup = self.checkSoup

        # subscription check
        loginCheck = soup.find('div',{'id':'login'})
        if self.getConfig("auto_sub") and not loginCheck:
            self.subSoup = self.doSubCheck(url,soup)
            if self.subSoup:
                soup = self.subSoup

        ## Title
        a = soup.find('h1', {'id': 'story-title'})
        self.story.setMetadata('title',stripHTML(a))

        # Find authorid and URL from... author url.
        mainmeta = soup.find('footer', {'class': 'main-meta'})
        alist = mainmeta.find('span', text='Author(s)')
        alist = alist.parent.findAll('a', href=re.compile(r"/profile/view/\d+"))
        for a in alist:
            self.story.addToList('authorId',a['href'].split('/')[-1])
            self.story.addToList('authorUrl','https://'+self.host+a['href'])
            self.story.addToList('author',a.text)

        newestChapter = None
        self.newestChapterNum = None
        # Find the chapters:
        chapters=soup.find('select',{'name':'chapter-nav'})
        chapters=chapters.findAll('option')
        self.story.setMetadata('numChapters',len(chapters))
        for index, chapter in enumerate(chapters):
            if chapter.text != 'Foreword': # skip the foreword
                self.add_chapter(chapter.text,'https://' + self.getSiteDomain() + chapter['value']) # note: AFF cuts off chapter names in list. this gets kind of fixed later on

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
        jsonlink = soup.find('link',href=re.compile(r'/api/forewords/[0-9]+/foreword_[0-9a-z]+.json'))
        fore_json = json.loads(self._fetchUrl(jsonlink['href']))
        content = self.make_soup(fore_json['post']).find('body') # BS4 adds <html><body> if not present.
        a = content.find('div', {'id':'story-description'})
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

        # word count
        a = soup.find('span', text='Total Word Count')
        if a:
            a = a.find_next('span')
            self.story.setMetadata('numWords', int(a.text.split()[0]))

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

        try:
            # https://www.asianfanfics.com/api/chapters/4791923/chapter_46d32e413d1a702a26f7637eabbfb6f3.json
            jsonlink = soup.find('link',href=re.compile(r'/api/chapters/[0-9]+/chapter_[0-9a-z]+.json'))
            chap_json = json.loads(self._fetchUrl(jsonlink['href']))
            content = self.make_soup(chap_json['post']).find('body') # BS4 adds <html><body> if not present.
            content.name='div' # change body to a div.
            if self.getConfig('inject_chapter_title'):
                # the dumbest workaround ever for the abbreviated chapter titles from before
                logger.debug("Injecting full-length chapter title")
                newTitle = soup.find('h1', {'id' : 'chapter-title'}).text
                newTitle = self.make_soup('<h3>%s</h3>' % (newTitle)).find('body') # BS4 adds <html><body> if not present.
                newTitle.name='div' # change body to a div.
                newTitle.append(content)
                return self.utf8FromSoup(url,newTitle)
            else:
                return self.utf8FromSoup(url,content)
        except Exception as e:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s %s!" % (url,e))
