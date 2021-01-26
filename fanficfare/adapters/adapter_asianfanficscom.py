#  -*- coding: utf-8 -*-

from __future__ import absolute_import
import logging
logger = logging.getLogger(__name__)
import re
import json
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition

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

    def performLogin(self, url, data):
        params = {}
        if self.password:
            params['username'] = self.username
            params['password'] = self.password
        else:
            params['username'] = self.getConfig("username")
            params['password'] = self.getConfig("password")

        if not params['username']:
            raise exceptions.FailedToLogin(url,params['username'])

        params['from_url'] = url
        # capture token from JS script, not appearing in form now.
        csrf_token_search = 'csrfToken = "'
        params['csrf_aff_token'] = data[data.index(csrf_token_search)+len(csrf_token_search):]
        params['csrf_aff_token'] = params['csrf_aff_token'][:params['csrf_aff_token'].index('"')]

        loginUrl = 'https://' + self.getSiteDomain() + '/login/index'
        logger.info("Will now login to URL (%s) as (%s)" % (loginUrl, params['username']))

        data = self.post_request(loginUrl, params)
        soup = self.make_soup(data)
        if self.loginNeededCheck(data):
            logger.info('Failed to login to URL %s as %s' % (loginUrl, params['username']))
            raise exceptions.FailedToLogin(url,params['username'])

    def loginNeededCheck(self,data):
        return "isLoggedIn = false" in data

    def doStorySubscribe(self, url, soup):
        subHref = soup.find('a',{'id':'subscribe'})
        if subHref:
            #does not work when using https - 403
            subUrl = 'http://' + self.getSiteDomain() + subHref['href']
            self.get_request(subUrl)
            data = self.get_request(url,usecache=False)
            soup = self.make_soup(data)
            check = soup.find('div',{'class':'click-to-read-full'})
            if check:
                return False
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
        data = self.get_request(url)

        soup = self.make_soup(data)

        if self.loginNeededCheck(data):
            # always login if not already to avoid lots of headaches
            self.performLogin(url,data)
            # refresh website after logging in
            data = self.get_request(url,usecache=False)
            soup = self.make_soup(data)

        # subscription check
        # logger.debug(soup)
        subCheck = soup.find('div',{'class':'click-to-read-full'})
        if subCheck and self.getConfig("auto_sub"):
            subSoup = self.doStorySubscribe(url,soup)
            if subSoup:
                soup = subSoup
            else:
                raise exceptions.FailedToDownload("Error when subscribing to story. This usually means a change in the website code.")
        elif subCheck and not self.getConfig("auto_sub"):
            raise exceptions.FailedToDownload("This story is only available to subscribers. You can subscribe manually on the web site, or set auto_sub:true in personal.ini.")

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
        hrefattr=None
        if chapters:
            chapters=chapters.findAll('option')
            hrefattr='value'
        else: # didn't find <select name='chapter-nav', look for alternative
            chapters=soup.find('div',{'class':'widget--chapters'}).findAll('a')
            hrefattr='href'
        for index, chapter in enumerate(chapters):
            if chapter.text != 'Foreword' and 'Collapse chapters' not in chapter.text:
                self.add_chapter(chapter.text,'https://' + self.getSiteDomain() + chapter[hrefattr])
            # note: AFF cuts off chapter names in list. this gets kind of fixed later on


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
        try:
            jsonlink = soup.find('script',string=re.compile(r'/api/forewords/[0-9]+/foreword_[0-9a-z]+.json')).get_text().split('"')[1] # grabs url from quotation marks
            fore_json = json.loads(self.get_request(jsonlink))
            content = self.make_soup(fore_json['post']).find('body') # BS4 adds <html><body> if not present.
            a = content.find('div', {'id':'story-description'})
        except:
            # not all stories have foreward link.
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

        # word count
        a = soup.find('span', text='Total Word Count')
        if a:
            a = a.find_next('span')
            self.story.setMetadata('numWords', int(a.text.split()[0]))

        # upvote, subs, and views
        a = soup.find('div',{'class':'title-meta'})
        spans = a.findAll('span', recursive=False)
        self.story.setMetadata('upvotes', re.search(r'\(([^)]+)', spans[0].find('span').text).group(1))
        self.story.setMetadata('subscribers', re.search(r'\(([^)]+)', spans[1].find('span').text).group(1))
        if len(spans) > 2: # views can be private
            self.story.setMetadata('views', spans[2].text.split()[0])

        # cover art in the form of a div before chapter content
        if get_cover:
            cover_url = ""
            a = soup.find('div',{'id':'bodyText'})
            if a:
                a = a.find('div',{'class':'text-center'})
                if a:
                    cover_url = a.find('img')['src']
                    self.setCoverImage(url,cover_url)

    # grab the text for an individual chapter
    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)

        data = self.get_request(url)
        soup = self.make_soup(data)

        try:
            # <script>var postApi = "https://www.asianfanfics.com/api/chapters/4791923/chapter_46d32e413d1a702a26f7637eabbfb6f3.json";</script>
            jsonlink = soup.find('script',string=re.compile(r'/api/chapters/[0-9]+/chapter_[0-9a-z]+.json')).get_text().split('"')[1] # grabs url from quotation marks
            chap_json = json.loads(self.get_request(jsonlink))
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
            logger.debug("json lookup failed, going on with HTML chapter")
            content = soup.find('div', {'id': 'user-submitted-body'})
            return self.utf8FromSoup(url,content)
