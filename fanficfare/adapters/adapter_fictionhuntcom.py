# -*- coding: utf-8 -*-

# Copyright 2022 FanFicFare team
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

from __future__ import absolute_import
import logging
logger = logging.getLogger(__name__)
import re
from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML

# py2 vs py3 transition

from .base_adapter import BaseSiteAdapter,  makeDate

ampfandoms = ["A Falcone & Driscoll Investigation",
              "Alias Smith & Jones",
              "Atelier Escha & Logy",
              "Austin & Ally",
              "Baby & Me/赤ちゃんと僕",
              "Barney & Friends",
              "Between Love & Goodbye",
              "Beyond Good & Evil",
              "Bill & Ted's Excellent Adventure/Bogus Journey",
              "BLACK & WHITE",
              "Bonnie & Clyde",
              "Brandy & Mr. Whiskers",
              "Brothers & Sisters",
              "Bucket & Skinner's Epic Adventures",
              "Calvin & Hobbes",
              "Cats & Dogs",
              "Command & Conquer",
              "Devil & Devil",
              "Dharma & Greg",
              "Dicky & Dawn",
              "Drake & Josh",
              "Edgar & Ellen",
              "Franklin & Bash",
              "Gabby Duran & The Unsittables",
              "Girls und Panzer/ガールズ&パンツァー",
              "Gnomeo & Juliet",
              "Grim Adventures of Billy & Mandy",
              "Half & Half/ハーフ・アンド・ハーフ",
              "Hansel & Gretel",
              "Hatfields & McCoys",
              "High & Low - The Story of S.W.O.R.D.",
              "Home & Away",
              "Hudson & Rex",
              "Huntik: Secrets & Seekers",
              "Imagine Me & You",
              "Jekyll & Hyde",
              "Jonathan Strange & Mr. Norrell",
              "Knight's & Magic/ナイツ＆マジック",
              "Law & Order: Los Angeles",
              "Law & Order: Organized Crime",
              "Lilo & Stitch",
              "Locke & Key",
              "Lockwood & Co.",
              "Lost & Found Music Studios",
              "Lu & Og",
              "Me & My Brothers",
              "Melissa & Joey",
              "Mickey Mouse & Friends",
              "Mike & Molly",
              "Mike, Lu & Og",
              "Miraculous: Tales of Ladybug & Cat Noir",
              "Mork & Mindy",
              "Mount&Blade",
              "Mr. & Mrs. Smith",
              "Mr. Peabody & Sherman",
              "Muhyo & Roji",
              "Nicky, Ricky, Dicky & Dawn",
              "Oliver & Company",
              "Ozzy & Drix",
              "Panty & Stocking with Garterbelt/パンティ＆ストッキングwithガーターベルト",
              "Penryn & the End of Days",
              "Prep & Landing",
              "Prince & Hero/王子とヒーロー",
              "Prince & Me",
              "Puzzle & Dragons",
              "Ren & Stimpy Show",
              "Rizzoli & Isles",
              "Romeo & Juliet",
              "Rosemary & Thyme",
              "Sam & Cat",
              "Sam & Max",
              "Sapphire & Steel",
              "Scott & Bailey",
              "Shakespeare & Hathaway: Private Investigators",
              "Soul Nomad & the World Eaters",
              "Superman & Lois",
              "Tiger & Bunny/タイガー＆バニー",
              "Trains & Automobiles",
              "Upin & Ipin",
              "Wallace & Gromit",
              "Witch & Wizard",
              "Wolverine & the X-Men",
              "Yotsuba&!/よつばと！",
              "Young & Hungry",
              ]


class FictionHuntComSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','fichunt')

        ## new types:
        ## https://fictionhunt.com/stories/7edm248/the-last-of-his-kind/chapters/1
        ## https://fictionhunt.com/stories/89kzg4z/the-last-of-his-kind-new
        ## old type:
        ## http://fictionhunt.com/read/12411643/1
        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            # logger.debug(m.groupdict())
            self.story.setMetadata('storyId',m.group('id'))
            if m.group('type') == "stories": # newer URL
                # normalized story URL.
                self._setURL("https://"+self.getSiteDomain()\
                                 +"/stories/"+self.story.getMetadata('storyId')+"/"+ (m.group('title') or ""))
            else:
                self._setURL("https://"+self.getSiteDomain()\
                                 +"/read/"+self.story.getMetadata('storyId')+"/1")
            # logger.debug(self.url)
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y-%m-%d %H:%M:%S"

    @staticmethod
    def getSiteDomain():
        return 'fictionhunt.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://fictionhunt.com/stories/1a1a1a/story-title http://fictionhunt.com/read/1234/1"

    def getSiteURLPattern(self):
        ## https://fictionhunt.com/stories/7edm248/the-last-of-his-kind/chapters/1
        ## https://fictionhunt.com/stories/89kzg4z/the-last-of-his-kind-new
        ## http://fictionhunt.com/read/12411643/1
        return r"https?://(www.)?fictionhunt.com/(?P<type>read|stories)/(?P<id>[0-9a-z]+)(/(?P<title>[^/]+))?(/|/[^/]+)*/?$"

    def needToLoginCheck(self, data):
        ## FH is apparently reporting "Story has been removed" for all
        ## chapters when not logged in now.
        if 'https://fictionhunt.com/login' in data:
          return True
        else:
          return False

    def performLogin(self, url):
        params = {}

        if self.password:
            params['identifier'] = self.username
            params['password'] = self.password
        else:
            params['identifier'] = self.getConfig("username")
            params['password'] = self.getConfig("password")
        params['remember'] = 'on'

        loginUrl = 'https://' + self.getSiteDomain() + '/login'

        if not params['identifier']:
            logger.info("This site requires login.")
            raise exceptions.FailedToLogin(url,params['identifier'])

        ## need to pull empty login page first to get authenticity_token
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['identifier']))
        soup = self.make_soup(self.get_request(loginUrl,usecache=False))
        params['_token']=soup.find('input', {'name':'_token'})['value']

        d = self.post_request(loginUrl, params, usecache=False)
        # logger.debug(d)

        if self.needToLoginCheck(d):
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['identifier']))
            raise exceptions.FailedToLogin(url,params['identifier'])
            return False
        else:
            return True

    def doExtractChapterUrlsAndMetadata(self,get_cover=True):

        # fetch the chapter.  From that we will get almost all the
        # metadata and chapter list

        url = self.url
        data = self.get_request(url)

        ## As per #784, site isn't requiring login anymore.
        ## Login check commented since we've seen it toggle before.
        # if self.needToLoginCheck(data):
        #     self.performLogin(url)
        #     data = self.get_request(url,usecache=False)

        soup = self.make_soup(data)
        ## detect old storyUrl, switch to new storyUrl:
        canonlink = soup.find('link',rel='canonical')
        if canonlink:
            # logger.debug(canonlink)
            canonlink = re.sub(r"/chapters/\d+","",canonlink['href'])
            # logger.debug(canonlink)
            self._setURL(canonlink)
            url = self.url
            data = self.get_request(url)
            soup = self.make_soup(data)
        else:
            # in case title changed
            self._setURL(soup.select_one("div.Story__details a")['href'])
            url = self.url

        # logger.debug(data)
        self.story.setMetadata('title',stripHTML(soup.find('h1',{'class':'Story__title'})))

        summhead = soup.find('h5',text='Summary')
        self.setDescription(url,summhead.find_next('div'))

        ## author:
        autha = soup.find('div',{'class':'StoryContents__meta'}).find('a') # first a in StoryContents__meta
        self.story.setMetadata('authorId',autha['href'].split('/')[4])
        self.story.setMetadata('authorUrl',autha['href'])
        self.story.setMetadata('author',autha.string)

        updlab = soup.find('label',text='Last Updated:')
        if updlab:
            update = updlab.find_next('time')['datetime']
            self.story.setMetadata('dateUpdated', makeDate(update, self.dateformat))

        publab = soup.find('label',text='Published:')
        if publab:
            pubdate = publab.find_next('time')['datetime']
            self.story.setMetadata('datePublished', makeDate(pubdate, self.dateformat))

        ## need author page for some metadata.
        authsoup = None
        authpagea = autha
        authstorya = None

        ## Rating and exact word count doesn't appear on the summary
        ## page, try to get from author page.

        ## find story url, might need to spin through author's pages.
        while authpagea and not authstorya:
            authsoup = self.make_soup(self.get_request(authpagea['href']))
            authpagea = authsoup.find('a',{'rel':'next'})
            # CSS selectors don't allow : or / unquoted, which
            # BS4(and dependencies) didn't used to enforce.
            authstorya = authsoup.select_one('h4.Story__item-title a[href="%s"]'%self.url)

        if not authstorya:
            raise exceptions.FailedToDownload("Error finding %s on author page(s)" % self.url)

        meta = authstorya.find_parent('li').find('div',class_='Story__meta-info')
        meta=meta.text.split()
        self.story.setMetadata('numWords',meta[meta.index('words')-1])
        self.story.setMetadata('rating',meta[meta.index('Rating:')+1])
        # logger.debug(meta)

        # Find original ffnet URL
        a = soup.find('a', text="Source")
        self.story.setMetadata('origin',stripHTML(a))
        self.story.setMetadata('originUrl',a['href'])

        datesdiv = soup.find('div',{'class':'dates'})
        if stripHTML(datesdiv.find('label')) == 'Completed' : # first label is status.
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        for a in soup.select("div.genres a"):
            self.story.addToList('genre',stripHTML(a))

        for a in soup.select("section.characters li.Tags__item a"):
            self.story.addToList('characters',stripHTML(a))

        for a in soup.select('a[href*="pairings="]'):
            self.story.addToList('ships',stripHTML(a).replace("+","/"))

        for a in soup.select('div.Story__type a[href*="fandoms="]'):
            # logger.debug(a)
            fandomstr=stripHTML(a).replace(' Fanfiction','').strip()
            # logger.debug("'%s'"%fandomstr)
            ## haven't thought of a better way to detect and *not*
            ## split on fandoms with a '&' in them.
            for ampfandom in ampfandoms:
                if ampfandom in fandomstr:
                    self.story.addToList('category',ampfandom)
                    fandomstr = fandomstr.replace(ampfandom,'')
            for fandom in fandomstr.split('&'):
                if fandom:
                    self.story.addToList('category',fandom)

        ## Currently no 'Original' stories on the site, but does list
        ## it as a search type.  Set extratags: and uncomment this if
        ## and when.
        # if self.story.getList('category'):
        #     self.story.addToList('category', 'FanFiction')
        # else:
        #     self.story.addToList('category', 'Original')

        for chapli in soup.select('ul.StoryContents__chapters li'):
            self.add_chapter(stripHTML(chapli.select_one('span.chapter-title')),chapli.select_one('a')['href'])

        if self.num_chapters() == 0:
            raise exceptions.FailedToDownload("Story at %s has no chapters." % self.url)

    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
        data = self.get_request(url)

        soup = self.make_soup(data)

        div = soup.find('div', {'class' : 'StoryChapter__text'})

        return self.utf8FromSoup(url,div)

def getClass():
    return FictionHuntComSiteAdapter
