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

import time
import logging
logger = logging.getLogger(__name__)
import re
import urllib
import urllib2

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

class MediaMinerOrgSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','mm')
        self.decode = ["Windows-1252",
                       "utf8"] # 1252 is a superset of iso-8859-1.
                               # Most sites that claim to be
                               # iso-8859-1 (and some that claim to be
                               # utf8) are really windows-1252.
        
        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            if m.group('id'):
                self.story.setMetadata('storyId',m.group('id'))
            elif m.group('id2'):
                self.story.setMetadata('storyId',m.group('id2'))
            elif m.group('id3'):
                self.story.setMetadata('storyId',m.group('id2'))
            
            # normalized story URL.
            self._setURL('http://' + self.getSiteDomain() + '/fanfic/view_st.php/'+self.story.getMetadata('storyId'))
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
        return "http://"+cls.getSiteDomain()+"/fanfic/view_st.php/123456 http://"+cls.getSiteDomain()+"/fanfic/view_ch.php/1234123/123444#fic_c"

    def getSiteURLPattern(self):
        ##  http://www.mediaminer.org/fanfic/view_st.php/76882
        ##  http://www.mediaminer.org/fanfic/view_ch.php/167618/594087#fic_c
        ##  http://www.mediaminer.org/fanfic/view_ch.php?submit=View+Chapter&id=105816&cid=357151
        ##  http://www.mediaminer.org/fanfic/view_ch.php?cid=612153&submit=View+Chapter&id=171668
        return re.escape("http://"+self.getSiteDomain())+\
            r"/fanfic/view_(st|ch)\.php"+\
            r"(/(?P<id>\d+)(/\d+(#fic_c)?)?/?|"+\
            r"\?((submit=View(\+| )Chapter|id=(?P<id2>\d+)|cid=\d+)&?)+)"

    # Override stripURLParameters so the id parameter won't get stripped
    @classmethod
    def stripURLParameters(cls, url):
        return url

    def extractChapterUrlsAndMetadata(self):

        url = self.url
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url) # w/o trailing / gets 'chapter list' page even for one-shots.
        except urllib2.HTTPError, e:
            if e.code == 404:
                logger.error("404 on %s"%url)
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        # [ A - All Readers ], strip '[' ']'
        ## Above title because we remove the smtxt font to get title.
        smtxt = soup.find("h3",{"id":"post-rating"})
        if not smtxt:
            logger.error("can't find rating")
            raise exceptions.StoryDoesNotExist(self.url)
        else:
            rating = smtxt.string[1:-1]
            self.story.setMetadata('rating',rating)

        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"/fanfic/src.php/u/\d+"))
        self.story.setMetadata('authorId',a['href'].split('/')[-1])
        self.story.setMetadata('authorUrl','http://'+self.host+a['href'])
        self.story.setMetadata('author',a.string)

        ## Title - Good grief.  Title varies by chaptered, 1chapter and 'type=one shot'--and even 'one-shot's can have titled chapter.
        ## But, if colspan=2, there's no chapter title.
        ## <td class="ffh">Atmosphere: Chapter 1</b> <font class="smtxt">[ P - Pre-Teen ]</font></td>
        ## <td colspan=2 class="ffh">Hearts of Ice <font class="smtxt">[ P - Pre-Teen ]</font></td>
        ## <td colspan=2 class="ffh">Suzaku no Princess <font class="smtxt">[ P - Pre-Teen ]</font></td>
        ## <td class="ffh">The Kraut, The Bartender, and The Drunkard: Chapter 1</b> <font class="smtxt">[ P - Pre-Teen ]</font></td>
        ## <td class="ffh">Betrayal and Justice: A Cold Heart</b> <font size="-1">( Chapter 1 )</font> <font class="smtxt">[ A - All Readers ]</font></td>
        ## <td class="ffh">Question and Answer: Question and Answer</b> <font size="-1">( One-Shot )</font> <font class="smtxt">[ A - All Readers ]</font></td>
        # title = soup.find('td',{'class':'ffh'})
        # for font in title.findAll('font'):
        #     font.extract() # removes 'font' tags from inside the td.        
        # if title.has_attr('colspan'):
        #     titlet = stripHTML(title)
        # else:
        #     ## No colspan, it's part chapter title--even if it's a one-shot.
        #     titlet = ':'.join(stripHTML(title).split(':')[:-1]) # strip trailing 'Chapter X' or chapter title
        self.story.setMetadata('title',stripHTML(soup.find('h1',{'id':'post-title'})))

        # save date from first for later.
        firstdate=None
        
        # Find the chapters - one-shot now have chapter list, too.
        chap_p = soup.find('p',{'style':'margin-left:10px;'})
        for (atag,aurl,name) in [ (x,x['href'],stripHTML(x)) for x in chap_p.find_all('a') ]:
            self.chapterUrls.append((name,'http://'+self.host+'/'+aurl))
            
        self.story.setMetadata('numChapters',len(self.chapterUrls))

        # category
        # <a href="/fanfic/src.php/a/567">Ranma 1/2</a>
        for a in soup.findAll('a',href=re.compile(r"^/fanfic/src.php/a/")):
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

        data = self._fetchUrl(url)
        soup = self.make_soup(data)

        headerstr = stripHTML(soup.find('div',{'class':'post-meta clearfix '}))
        # print("data:%s"%data)
        #header.extract()

        m = re.match(r".*?Uploaded On: ([a-zA-Z]+ \d\d, \d\d\d\d \d\d:\d\d)",headerstr)
        if m:
            date = makeDate(m.group(1), self.dateformat)
            if not self.story.getMetadataRaw('datePublished') or date < self.story.getMetadataRaw('datePublished'):
                self.story.setMetadata('datePublished', date)
                
        chapter = soup.find('div',{'id':'fanfic-text'})
        
        return self.utf8FromSoup(url,chapter)
    
        # chapter=self.make_soup('<div class="story"></div>').find('div')

        # if None == header:
        #     raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        # ## find divs with align=left, those are paragraphs in newer stories.
        # divlist = header.findAllNext('div',{'align':'left'})
        # if divlist:
        #     for div in divlist:
        #         div.name='p' # convert to <p> mediaminer uses div with
        #                      # a margin for paragraphs.
        #         chapter.append(div)
        #         del div['style']
        #         del div['align']
        #     return self.utf8FromSoup(url,chapter)
        
        # else:
        #     logger.debug('Using kludgey text find for older mediaminer story.')
        #     ## Some older mediaminer stories are unparsable with BeautifulSoup.
        #     ## Really nasty formatting.  Sooo... Cheat!  Parse it ourselves a bit first.
        #     ## Story stuff falls between:
        #     data = "<div id='HERE'>" + data[data.find('<div class="adWrap">'):data.find('<div class="addthis_sharing_toolbox">')] +"</div>"
        #     soup = self.make_soup(data)
        #     for tag in soup.findAll('td',{'class':'ffh'}) + \
        #             soup.findAll('div',{'class':'acl'}) + \
        #             soup.findAll('div',{'class':'adWrap'}) + \
        #             soup.findAll('div',{'class':'footer smtxt'}) + \
        #             soup.findAll('table',{'class':'tbbrdr'}):
        #         tag.extract() # remove tag from soup.
                
        #     return self.utf8FromSoup(url,soup)
        

def getClass():
    return MediaMinerOrgSiteAdapter

