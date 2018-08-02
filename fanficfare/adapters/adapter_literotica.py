# -*- coding: utf-8 -*-

# Copyright 2013 Fanficdownloader team, 2018 FanFicFare team
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

from bs4.element import Comment
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib import parse as urlparse
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter, makeDate

class LiteroticaSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        logger.debug("LiteroticaComAdapter:__init__ - url='%s'" % url)

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','litero')

        # normalize to first chapter.  Not sure if they ever have more than 2 digits.
        storyId = self.parsedUrl.path.split('/',)[2]
        # replace later chapters with first chapter but don't remove numbers
        # from the URL that disambiguate stories with the same title.
        storyId = re.sub("-ch-?\d\d", "", storyId)
        self.story.setMetadata('storyId', storyId)

        ## accept m(mobile)url, but use www.
        url = re.sub("^(www|german|spanish|french|dutch|italian|romanian|portuguese|other)\.i",
                              "\1",
                              url)

        ## strip ?page=...
        url = re.sub("\?page=.*$", "", url)

        ## set url
        self._setURL(url)

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%m/%d/%y"

    @staticmethod
    def getSiteDomain():
        return 'literotica.com'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.literotica.com',
                'www.i.literotica.com',
                'german.literotica.com',
                'german.i.literotica.com',
                'spanish.literotica.com',
                'spanish.i.literotica.com',
                'french.literotica.com',
                'french.i.literotica.com',
                'dutch.literotica.com',
                'dutch.i.literotica.com',
                'italian.literotica.com',
                'italian.i.literotica.com',
                'romanian.literotica.com',
                'romanian.i.literotica.com',
                'portuguese.literotica.com',
                'portuguese.i.literotica.com',
                'other.literotica.com',
                'other.i.literotica.com']

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://www.literotica.com/s/story-title https://www.literotica.com/s/story-title http://portuguese.literotica.com/s/story-title http://german.literotica.com/s/story-title"

    def getSiteURLPattern(self):
        return r"https?://(www|german|spanish|french|dutch|italian|romanian|portuguese|other)(\.i)?\.literotica\.com/s/([a-zA-Z0-9_-]+)"

    def getCategories(self, soup):
        if self.getConfig("use_meta_keywords"):
            categories = soup.find("meta", {"name":"keywords"})['content'].split(', ')
            categories = [c for c in categories if not self.story.getMetadata('title') in c]
            if self.story.getMetadata('author') in categories:
                categories.remove(self.story.getMetadata('author'))
            logger.debug("Meta = %s" % categories)
            for category in categories:
    #            logger.debug("\tCategory=%s" % category)
#                 self.story.addToList('category', category.title())
                self.story.addToList('eroticatags', category.title())

    def extractChapterUrlsAndMetadata(self):
        """
        NOTE: Some stories can have versions,
              e.g. /my-story-ch-05-version-10
        NOTE: If two stories share the same title, a running index is added,
              e.g.: /my-story-ch-02-1
        Strategy:
            * Go to author's page, search for the current story link,
            * If it's in a tr.root-story => One-part story
                * , get metadata and be done
            * If it's in a tr.sl => Chapter in series
                * Search up from there until we find a tr.ser-ttl (this is the
                story)
                * Gather metadata
                * Search down from there for all tr.sl until the next
                tr.ser-ttl, foreach
                    * Chapter link is there
        """

        if not (self.is_adult or self.getConfig("is_adult")):
            raise exceptions.AdultCheckRequired(self.url)

        logger.debug("Chapter/Story URL: <%s> " % self.url)

        try:
            data1 = self._fetchUrl(self.url)
            soup1 = self.make_soup(data1)
            #strip comments from soup
            [comment.extract() for comment in soup1.findAll(text=lambda text:isinstance(text, Comment))]
        except HTTPError as e:
            if e.code in [404, 410]:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        if "This submission is awaiting moderator's approval" in data1:
            raise exceptions.StoryDoesNotExist("This submission is awaiting moderator's approval. %s"%self.url)

        # author
        a = soup1.find("span", "b-story-user-y")
        self.story.setMetadata('authorId', urlparse.parse_qs(a.a['href'].split('?')[1])['uid'][0])
        authorurl = a.a['href']
        if authorurl.startswith('//'):
            authorurl = self.parsedUrl.scheme+':'+authorurl
        self.story.setMetadata('authorUrl', authorurl)
        self.story.setMetadata('author', a.text)

        # get the author page
        try:
            dataAuth = self._fetchUrl(authorurl)
            soupAuth = self.make_soup(dataAuth)
            #strip comments from soup
            [comment.extract() for comment in soupAuth.findAll(text=lambda text:isinstance(text, Comment))]
#            logger.debug(soupAuth)
        except HTTPError as e:
            if e.code in [404, 410]:
                raise exceptions.StoryDoesNotExist(authorurl)
            else:
                raise e

        ## Find link to url in author's page
        ## site has started using //domain.name/asdf urls remove https?: from front
        ## site has started putting https back on again.
        storyLink = soupAuth.find('a', href=re.compile(r'(https?:)?'+re.escape(self.url[self.url.index(':')+1:])))
#         storyLink = soupAuth.find('a', href=self.url)#[self.url.index(':')+1:])

        if storyLink is not None:
            # pull the published date from the author page
            # default values from single link.  Updated below if multiple chapter.
            logger.debug("Found story on the author page.")
            date = storyLink.parent.parent.findAll('td')[-1].text
            self.story.setMetadata('datePublished', makeDate(date, self.dateformat))
            self.story.setMetadata('dateUpdated',makeDate(date, self.dateformat))

        if storyLink is not None:
            urlTr = storyLink.parent.parent
            if "sl" in urlTr['class']:
                isSingleStory = False
            else:
                isSingleStory = True
        else:
            raise exceptions.FailedToDownload("Couldn't find story <%s> on author's page <%s>" % (self.url, authorurl))

        if isSingleStory:
            self.story.setMetadata('title', storyLink.text.strip('/'))
            logger.debug('Title: "%s"' % storyLink.text.strip('/'))
            self.setDescription(authorurl, urlTr.findAll("td")[1].text)
            self.story.addToList('category', urlTr.findAll("td")[2].text)
#             self.story.addToList('eroticatags', urlTr.findAll("td")[2].text)
            date = urlTr.findAll('td')[-1].text
            self.story.setMetadata('datePublished', makeDate(date, self.dateformat))
            self.story.setMetadata('dateUpdated',makeDate(date, self.dateformat))
            self.add_chapter(storyLink.text, self.url)
            averrating = stripHTML(storyLink.parent)
            ## title (0.00)
            averrating = averrating[averrating.rfind('(')+1:averrating.rfind(')')]
            try:
                self.story.setMetadata('averrating', float(averrating))
            except:
                pass
#             self.story.setMetadata('averrating',averrating)
        # parse out the list of chapters
        else:
            seriesTr = urlTr.previousSibling
            while 'ser-ttl' not in seriesTr['class']:
                seriesTr = seriesTr.previousSibling
            m = re.match("^(?P<title>.*?):\s(?P<numChapters>\d+)\sPart\sSeries$", seriesTr.find("strong").text)
            self.story.setMetadata('title', m.group('title'))
            seriesTitle = m.group('title')

            ## Walk the chapters
            chapterTr = seriesTr.nextSibling
            dates = []
            descriptions = []
            ratings = []
            chapters = []
            while chapterTr is not None and 'sl' in chapterTr['class']:
                description = "%d. %s" % (len(descriptions)+1,stripHTML(chapterTr.findAll("td")[1]))
                description = stripHTML(chapterTr.findAll("td")[1])
                chapterLink = chapterTr.find("td", "fc").find("a")
                if self.getConfig('chapter_categories_use_all'):
                    self.story.addToList('category', chapterTr.findAll("td")[2].text)
                self.story.addToList('eroticatags', chapterTr.findAll("td")[2].text)
                pub_date = makeDate(chapterTr.findAll('td')[-1].text, self.dateformat)
                dates.append(pub_date)
                chapterTr = chapterTr.nextSibling
                
                chapter_title = chapterLink.text
                if self.getConfig("clean_chapter_titles"):
                    logger.debug('\tChapter Name: "%s"' % chapterLink.string)
                    logger.debug('\tChapter Name: "%s"' % chapterLink.text)
                    if chapterLink.text.lower().startswith(seriesTitle.lower()):
                        chapter = chapterLink.text[len(seriesTitle):].strip()
                        logger.debug('\tChapter: "%s"' % chapter)
                        if chapter == '':
                            chapter_title = 'Chapter %d' % (self.num_chapters() + 1)
                        else:
                            separater_char = chapter[0]
                            logger.debug('\tseparater_char: "%s"' % separater_char)
                            chapter = chapter[1:].strip() if separater_char in [":", "-"] else chapter
                            logger.debug('\tChapter: "%s"' % chapter)
                            if chapter.lower().startswith('ch.'):
                                chapter = chapter[len('ch.'):].strip()
                                try:
                                    chapter_title = 'Chapter %d' % int(chapter)
                                except:
                                    chapter_title = 'Chapter %s' % chapter
                            elif chapter.lower().startswith('pt.'):
                                chapter = chapter[len('pt.'):]
                                try:
                                    chapter_title = 'Part %d' % int(chapter)
                                except:
                                    chapter_title = 'Part %s' % chapter
                            elif separater_char in [":", "-"]:
                                chapter_title = chapter
    
                # pages include full URLs.
                chapurl = chapterLink['href']
                if chapurl.startswith('//'):
                    chapurl = self.parsedUrl.scheme + ':' + chapurl
                logger.debug("Chapter URL: " + chapurl)
                logger.debug("Chapter Title: " + chapter_title)
                logger.debug("Chapter description: " + description)
                chapters.append((chapter_title, chapurl, description, pub_date))
#                 self.add_chapter(chapter_title, chapurl)
                numrating = stripHTML(chapterLink.parent)
                ## title (0.00)
                numrating = numrating[numrating.rfind('(')+1:numrating.rfind(')')]
                try:
                    ratings.append(float(numrating))
                except:
                    pass

            chapters = sorted(chapters, key=lambda chapter: chapter[3])
            for i, chapter in enumerate(chapters):
                self.add_chapter(chapter[0], chapter[1])
                descriptions.append("%d. %s" % (i + 1, chapter[2]))
            ## Set the oldest date as publication date, the newest as update date
            dates.sort()
            self.story.setMetadata('datePublished', dates[0])
            self.story.setMetadata('dateUpdated', dates[-1])
            self.story.setMetadata('datePublished', chapters[0][3])
            self.story.setMetadata('dateUpdated', chapters[-1][3])
            ## Set description to joint chapter descriptions
            self.setDescription(authorurl,"<p>"+"</p>\n<p>".join(descriptions)+"</p>")

            if len(ratings) > 0:
                self.story.setMetadata('averrating','%4.2f' % (sum(ratings) / float(len(ratings))))

        # normalize on first chapter URL.
        self._setURL(self.get_chapter(0,'url'))

        # reset storyId to first chapter.
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])


        # Add the category from the breadcumb. This might duplicate a category already added.
        self.story.addToList('category', soup1.find('div', 'b-breadcrumbs').findAll('a')[1].string)
        self.getCategories(soup1)

        return


    def getPageText(self, raw_page, url):
        logger.debug('Getting page text')
#         logger.debug(soup)
        raw_page = raw_page.replace('<div class="b-story-body-x x-r15"><div><p>','<div class="b-story-body-x x-r15"><div>')
#         logger.debug("\tChapter text: %s" % raw_page)
        page_soup = self.make_soup(raw_page)
        [comment.extract() for comment in page_soup.findAll(text=lambda text:isinstance(text, Comment))]
        story2 = page_soup.find('div', 'b-story-body-x').div
#         logger.debug('getPageText - story2: %s' % story2)

        fullhtml = unicode(story2)
#         logger.debug(fullhtml)
        # Strip some starting and ending tags,
        fullhtml = re.sub(r'^<div.*?>', r'', fullhtml)
        fullhtml = re.sub(r'</div>$', r'', fullhtml)
        fullhtml = re.sub(r'<p></p>$', r'', fullhtml)
#         logger.debug('getPageText - fullhtml: %s' % fullhtml)
        return fullhtml

    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        raw_page = self._fetchUrl(url)
        page_soup = self.make_soup(raw_page)
        pages = page_soup.find('select', {'name' : 'page'})
        page_nums = [page.text for page in pages.findAll('option')] if pages else 0

        fullhtml = "" 
        self.getCategories(page_soup)
        chapter_description = ''
        if self.getConfig("description_in_chapter"):
            chapter_description = page_soup.find("meta", {"name" : "description"})['content']
            logger.debug("\tChapter description: %s" % chapter_description)
            chapter_description = '<p><b>Description:</b> %s</p><hr />' % chapter_description
        fullhtml += self.getPageText(raw_page, url)
        if pages:
            for page_no in range(2, len(page_nums) + 1):
                page_url = url +  "?page=%s" % page_no
                logger.debug("page_url= %s" % page_url)
                raw_page = self._fetchUrl(page_url)
                fullhtml += self.getPageText(raw_page, url)
        
#         logger.debug(fullhtml)
        page_soup = self.make_soup(fullhtml)
        fullhtml = self.utf8FromSoup(url, self.make_soup(fullhtml))
        fullhtml = chapter_description + fullhtml
        fullhtml = unicode(fullhtml)

        return fullhtml


def getClass():
    return LiteroticaSiteAdapter



