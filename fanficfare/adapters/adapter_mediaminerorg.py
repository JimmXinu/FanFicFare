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

from __future__ import absolute_import
import logging
logger = logging.getLogger(__name__)
import re
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode

from .base_adapter import BaseSiteAdapter,  makeDate

class MediaMinerOrgSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','mm')

        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        urltitle='urltitle'
        cattitle='cattitle'
        if m:
            if m.group('id1'):
                self.story.setMetadata('storyId',m.group('id1'))
                urltitle=m.group('urltitle1')
            elif m.group('id2'):
                self.story.setMetadata('storyId',m.group('id2'))
                urltitle=m.group('urltitle2')
            elif m.group('id3'):
                self.story.setMetadata('storyId',m.group('id3'))
            elif m.group('id4'):
                self.story.setMetadata('storyId',m.group('id4'))
                cattitle=m.group('cattitle4')
                urltitle=m.group('urltitle4')
            elif m.group('id5'):
                self.story.setMetadata('storyId',m.group('id5'))
                cattitle=m.group('cattitle5')
                urltitle=m.group('urltitle5')
            else:
                raise InvalidStoryURL(url,
                                      self.getSiteDomain(),
                                      self.getSiteExampleURLs())

            # normalized story URL.
            self._setURL('https://' + self.getSiteDomain() + '/fanfic/s/'+cattitle+'/'+urltitle+'/'+self.story.getMetadata('storyId'))
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%B %d, %Y %H:%M"

    @staticmethod
    def getSiteDomain():
        return 'www.mediaminer.org'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/fanfic/s/category-name/story-title/123456 https://"+cls.getSiteDomain()+"/fanfic/c/category-name/story-title/123456/987612"

    def getSiteURLPattern(self):
        ## old urls
        ## https://www.mediaminer.org/fanfic/view_st.php/76882
        ## new urls
        ## https://www.mediaminer.org/fanfic/s/ghosts-from-the-past/72
        ## https://www.mediaminer.org/fanfic/c/ghosts-from-the-past/chapter-2/72/174
        ## https://www.mediaminer.org/fanfic/s/robtech-final-missions/61553
        ## https://www.mediaminer.org/fanfic/c/robtech-final-missions/robotech-final-missions-oneshot/61553/189830
        ## even newer urls
        ## https://www.mediaminer.org/fanfic/s/gundam-wing-fan-fiction/the-preventer-operatives/171000
        ## https://www.mediaminer.org/fanfic/c/gundam-wing-fan-fiction/the-preventer-operatives/171000/608822
        ## email urls:
        ## https://www.mediaminer.org/fanfic/view_ch.php/161297/626395?utm_source=add_chapter&utm_medium=email
        ## author page urls:
        ## https://www.mediaminer.org/fanfic/view_st.php?id=145608&submit=View
        return r"https?://"+re.escape(self.getSiteDomain())+r"/fanfic/"+\
            r"((s/(?P<cattitle4>[^/]+)/(?P<urltitle4>[^/]+)/(?P<id4>\d+))|"+\
            r"((c/(?P<cattitle5>[^/]+)/(?P<urltitle5>[^/]+)/(?P<id5>\d+))/\d+)|"+\
            r"(s/(?P<urltitle1>[^/]+)/(?P<id1>\d+))|"+\
            r"((c/(?P<urltitle2>[^/]+)/[^/]+/(?P<id2>\d+))/\d+)|"+\
            r"(view_(st|ch)\.php(/|\?id=)(?P<id3>\d+)))"

    # Override stripURLParameters so the id parameter won't get stripped
    @classmethod
    def stripURLParameters(cls, url):
        return url


    def extractChapterUrlsAndMetadata(self):

        url = self.url
        logger.debug("URL: "+url)

        data = self.get_request(url) # w/o trailing / gets 'chapter list' page even for one-shots.

        soup = self.make_soup(data)

        ## title:
        ## <h1 id="post-title">A, A' Fan Fiction &#10095; Mmmmm</h1>
        titletext = unicode(stripHTML(soup.find("h1",{"id":"post-title"})))
        titletext = titletext[titletext.index(u'❯')+2:]
        # print("title:(%s)"%titletext)
        self.story.setMetadata('title',titletext)

        # [ A - All Readers ], strip '[ ' ' ]'
        ## Above title because we remove the smtxt font to get title.
        smtxt = soup.find("div",{"id":"post-rating"})
        if not smtxt:
            logger.error("can't find rating")
            raise exceptions.StoryDoesNotExist(self.url)
        else:
            rating = smtxt.string[2:-2]
            self.story.setMetadata('rating',rating)

        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"/user_info.php/\d+"))
        self.story.setMetadata('authorId',a['href'].split('/')[-1])
        self.story.setMetadata('authorUrl','https://'+self.host+a['href'])
        self.story.setMetadata('author',a.string)

        # save date from first for later.
        firstdate=None

        # Find the chapters - one-shot now have chapter list, too.
        chap_p = soup.find('p',{'style':'margin-left:10px;'})
        for (atag,aurl,name) in [ (x,x['href'],stripHTML(x)) for x in chap_p.find_all('a') ]:
            self.add_chapter(name,'https://'+self.host+aurl)


        # category
        # <a href="/fanfic/src.php/a/567">Ranma 1/2</a>
        for a in soup.findAll('a',href=re.compile(r"^/fanfic/a/")):
            self.story.addToList('category',a.string)

        # genre
        # <a href="/fanfic/src.php/g/567">Ranma 1/2</a>
        for a in soup.findAll('a',href=re.compile(r"^/fanfic/src.php/g/")):
            self.story.addToList('genre',a.string)

        metastr = stripHTML(soup.find("div",{"class":"post-meta"}))

        # Latest Revision: February 07, 2015 15:21 PST
        m = re.match(r".*?(?:Latest Revision|Uploaded On): ([a-zA-Z]+ \d\d, \d\d\d\d \d\d:\d\d)",metastr)
        if m:
            self.story.setMetadata('dateUpdated', makeDate(m.group(1), self.dateformat))
            # site doesn't give date published on index page.
            # set to updated, change in chapters below.
            # self.story.setMetadata('datePublished',
            #                        self.story.getMetadataRaw('dateUpdated'))

        # Words: 123456
        m = re.match(r".*?\| Words: (\d+) \|",metastr)
        if m:
            self.story.setMetadata('numWords', m.group(1))

        # Summary: ....
        m = re.match(r".*?Summary: (.*)$",metastr)
        if m:
            self.setDescription(url, m.group(1))
            #self.story.setMetadata('description', m.group(1))

        # completed
        m = re.match(r".*?Status: Completed.*?",metastr)
        if m:
            self.story.setMetadata('status','Completed')
        else:
            self.story.setMetadata('status','In-Progress')

        return

    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        data = self.get_request(url)
        soup = self.make_soup(data)

        # print("data:%s"%data)
        headerstr = stripHTML(soup.find('div',{'class':'post-meta'}))

        m = re.match(r".*?Uploaded On: ([a-zA-Z]+ \d\d, \d\d\d\d \d\d:\d\d)",headerstr)
        if m:
            date = makeDate(m.group(1), self.dateformat)
            if not self.story.getMetadataRaw('datePublished') or date < self.story.getMetadataRaw('datePublished'):
                self.story.setMetadata('datePublished', date)

        chapter = soup.find('div',{'id':'fanfic-text'})

        return self.utf8FromSoup(url,chapter)

def getClass():
    return MediaMinerOrgSiteAdapter

