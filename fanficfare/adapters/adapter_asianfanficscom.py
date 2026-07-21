#  -*- coding: utf-8 -*-

from __future__ import absolute_import
import logging
logger = logging.getLogger(__name__)
import re
import json
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions
from ..six.moves.urllib import parse as urlparse

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
        self.dateformat = "%b %d, %Y"

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
        data = self.get_request(urlparse.urljoin(url,"/login"),usecache=False)
        # logger.debug(data)
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
        csrf_token_search = '<input type="hidden" name="csrf_token" value="'
        params['csrf_token'] = data[data.index(csrf_token_search)+len(csrf_token_search):]
        params['csrf_token'] = params['csrf_token'][:params['csrf_token'].index('"')]

        # logger.debug(params)
        loginUrl = urlparse.urljoin(url,'/htmx/login')
        logger.info("Will now login to URL (%s) as (%s)" % (loginUrl, params['username']))

        data = self.post_request(loginUrl, params, referer=url)
        if self.loginNeededCheck(data):
            logger.info('Failed to login to URL %s as %s' % (loginUrl, params['username']))
            raise exceptions.FailedToLogin(url,params['username'])
        # logger.debug(data)
        return data

    def loginNeededCheck(self,data):
        return '<a href="/login"' in data

    def doStorySubscribe(self, url, soup):
        subHref = soup.find('a',{'id':'subscribe'})
        if subHref:
            if check:
                return False
            else:
                return soup
        else:
            return False

    def doAgeVerify(self,url,soup):
        verify_age = soup.select_one('a[href="/htmx/story/verify_age"]')
        # logger.debug(verify_age)
        if verify_age:
            if self.is_adult or self.getConfig("is_adult"):
                data = self.get_request(urlparse.urljoin(url, verify_age['href']),referer=url)
                soup = self.make_soup(data)
                # logger.debug(data)
            else:
                raise exceptions.AdultCheckRequired(url)
        return soup

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def doExtractChapterUrlsAndMetadata(self,get_cover=True):
        url = self.url
        logger.info("url: "+url)
        soup = None
        try:
            data = self.get_request(url)
            soup = self.make_soup(data)
        except exceptions.HTTPErrorFFF as e:
            if e.status_code != 404:
                raise
            data = self.decode_data(e.data)

        if not soup or self.loginNeededCheck(data):
            # always login if not already to avoid lots of headaches
            self.performLogin(url,data)
            # refresh website after logging in
            data = self.get_request(url,usecache=False)
            soup = self.make_soup(data)

        soup = self.doAgeVerify(url,soup)

        # logger.debug(data)
        # subscription check
        if ">Please subscribe to read further chapters.</div>" in data:
            raise exceptions.FailedToDownload("This story is only available to subscribers. You can subscribe manually on the web site -- auto_sub setting isn't working right now.")
            ## I *think* subscribe wants additional http headers, probably:
            ## HX-Current-URL https://www.asianfanfics.com/story/view/9999/title
            ## HX-Request true
            ## X-CSRF-Token 2hiP5...sOMg==

            # if self.getConfig("auto_sub"):
            #     # POST https://www.asianfanfics.com/htmx/story/subscribe/1476340
            #     sub_data = self.post_request(urlparse.urljoin(url,"/htmx/story/subscribe/%s"%self.story.getMetadata('storyId')),
            #                                  referer=url)
            #     if "<span>Subscribed</span>" not in sub_data:
            #         raise exceptions.FailedToDownload("Error when subscribing to story. This usually means a change in the website code.")
            #     else:
            #         data = self.get_request(url,usecache=False)
            #         soup = self.make_soup(data)
            # else:
            #     raise exceptions.FailedToDownload("This story is only available to subscribers. You can subscribe manually on the web site, or set auto_sub:true in personal.ini.")

        ## Title
        a = soup.find('h1')
        self.story.setMetadata('title',stripHTML(a))

        # Find authorid and URL from... author url.
        mainmeta = soup.find('header', {'class': 'flow-root'})
        alist = mainmeta.find('span', string='by')
        alist = alist.parent.find_all('a', href=re.compile(r"/profile/u/[^/]+"))
        for a in alist:
            self.story.addToList('authorId',a['href'].split('/')[-1])
            self.story.addToList('authorUrl','https://'+self.host+a['href'])
            self.story.addToList('author',a.text)

        for chapter in soup.select('aside a[data-toc-chapter]'):
            chtext = stripHTML(chapter)
            if chtext != 'Foreword':
                self.add_chapter(chtext,urlparse.urljoin(url,chapter['href']))

        # story status
        a = mainmeta.find('span', string='Completed')
        if a:
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        # story description
        try:
            ## div hx-get="/htmx/story/1307594/QkOAr2opXwTAgPxL"
            desc_div = soup.select_one('div[hx-get^="/htmx/story/%s/"]'%self.story.getMetadata('storyId'))
            # logger.debug(desc_div)
            if desc_div:
                desc_data = self.get_request(urlparse.urljoin(url,desc_div['hx-get']),
                                             referer=url)
                # logger.debug(desc_data)
                desc_soup = self.make_soup(desc_data)
                self.setDescription(url,desc_soup.select_one("div#story-description"))
        except Exception as e:
            logger.info("Failed to get story description: %s"%e)

        # story tags
        for tag in mainmeta.select('a[href^="/browse/tag/"]'):
            self.story.addToList('tags', stripHTML(tag))

        ## Characters are all in *one* entry because site doesn't make
        ## it a list and authors can enter what they like.  I've seen:
        ## "X | Y" "X, Y" "X and Y"
        t = soup.find('span',string='Characters:')
        # logger.debug(t)
        if t:
            self.story.addToList('characters', t.nextSibling)

        times = soup.select('time') # only two <time> tags, published and updated.
        if times:
            self.story.setMetadata('datePublished', makeDate(stripHTML(times[0]), self.dateformat))
            self.story.setMetadata('dateUpdated', makeDate(stripHTML(times[-1]), self.dateformat))

        # word count
        t = soup.find('span', string='Total word count:')
        if t:
            self.story.setMetadata('numWords', int(t.nextSibling))

        # upvote, subs, and views
        # upvote is a link, use to find all three.
        a = mainmeta.select_one('a[href^="/story/voters"]')
        if a:
            for span in a.parent.select('span,a'):
                span = stripHTML(span)
                # logger.debug(span)
                if 'votes' in span:
                    self.story.setMetadata('upvotes', span.split()[0])
                if 'subscribers' in span:
                    self.story.setMetadata('subscribers', span.split()[0])
                if 'views' in span:
                    self.story.setMetadata('views', span.split()[0])
                if 'comments' in span:
                    self.story.setMetadata('comments', span.split()[0])

        # cover art in the form of a div before chapter content
        if get_cover:
            cover_img = mainmeta.select_one('img')
            if cover_img:
                self.setCoverImage(url,cover_img['src'])

    # grab the text for an individual chapter
    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)

        data = self.get_request(url)
        soup = self.make_soup(data)
        # logger.debug(data)

        soup = self.doAgeVerify(url,soup)

        ## <div hx-get="/htmx/chapter/5215288/2fWXxZQwbxi2u0oi"
        chap_div = soup.select_one('div[hx-get^="/htmx/chapter/"]')
        # logger.debug(chap_div)
        if chap_div:
            chap_data = self.get_request(urlparse.urljoin(url,chap_div['hx-get']),
                                         referer=url)
            # logger.debug(chap_data)
            chap_soup = self.make_soup(chap_data)

        content = chap_soup.find('div', {'id': 'user-submitted-body'})

        if self.getConfig('inject_chapter_image'):
            logger.debug("Injecting chapter image")
            imgdiv = soup.select_one('div#bodyText img').parent
            if imgdiv:
                content.insert(0, "\n")
                content.insert(0, imgdiv)
                content.insert(0, "\n")

        return self.utf8FromSoup(url,content)
