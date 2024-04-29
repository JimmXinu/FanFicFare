# -*- coding: utf-8 -*-

# Copyright 2013 Fanficdownloader team, 2020 FanFicFare team
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

from .base_adapter import BaseSiteAdapter, makeDate

LANG_LIST = ('www','german','spanish','french','dutch','italian','romanian','portuguese','other')
LANG_RE = r"(?P<lang>" + r"|".join(LANG_LIST) + r")"

class LiteroticaSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        logger.debug("LiteroticaComAdapter:__init__ - url='%s'" % url)

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','litero')

        # Used to try to normalize storyId to first chapter, but there
        # are stories where the first chapter has '-ch-01' and stories
        # where first chapter doesn't have '-ch-'.
        # Now just rely on extractChapterUrlsAndMetadata to reset
        # storyId to first chapter link.

        ## DON'T normalize to www.literotica.com--keep for language,
        ## which will be set in _setURL(url).  Also, multi-chapter
        ## have been keeping the language when 'normalizing' to first
        ## chapter.
        url = re.sub(r"^(https?://)"+LANG_RE+r"(\.i)?",
                     r"\1\2",
                     url)
        url = url.replace('/beta/','/') # to allow beta site URLs.

        ## strip ?page=...
        url = re.sub(r"\?page=.*$", "", url)

        ## set url
        self._setURL(url)

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%m/%d/%Y"

    @staticmethod
    def getSiteDomain():
        return 'literotica.com'

    @classmethod
    def getAcceptDomains(cls):
        return [ x + '.' + cls.getSiteDomain() for x in LANG_LIST ] + [ x + '.i.' + cls.getSiteDomain() for x in LANG_LIST ]

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://www.literotica.com/s/story-title https://www.literotica.com/series/se/9999999 https://www.literotica.com/s/story-title https://www.literotica.com/i/image-or-comic-title https://www.literotica.com/p/poem-title http://portuguese.literotica.com/s/story-title http://german.literotica.com/s/story-title"

    def getSiteURLPattern(self):
        # also https://www.literotica.com/series/se/80075773
        # /s/ for story, /i/ for image/comic, /p/ for poem
        return r"https?://"+LANG_RE+r"(\.i)?\.literotica\.com/((beta/)?[sip]/([a-zA-Z0-9_-]+)|series/se/(?P<storyseriesid>[a-zA-Z0-9_-]+))"

    def _setURL(self,url):
        # logger.debug("set URL:%s"%url)
        super(LiteroticaSiteAdapter, self)._setURL(url)
        m = re.match(self.getSiteURLPattern(),url)
        lang = m.group('lang')
        if lang not in ('www','other'):
            self.story.setMetadata('language',lang.capitalize())
        # reset storyId
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[-1])
        # logger.debug("language:%s"%self.story.getMetadata('language'))

    def extractChapterUrlsAndMetadata(self):
        """
        In April 2024, site introduced significant changes, including
        adding a 'Story Series' page and link to it in each chapter.
        But not all stories, one-shots don't have 'Story Series'.

        literotica has 'Story Series' & 'Story'.  FFF calls them 'Story' & 'Chapters'
        See https://github.com/JimmXinu/FanFicFare/issues/1058#issuecomment-2078490037

        So /series/se/ will be the story URL for multi chapters but
        keep individual 'chapter' URL for one-shots.
        """
        logger.debug("Chapter/Story URL: <%s> " % self.url)

        if not (self.is_adult or self.getConfig("is_adult")):
            raise exceptions.AdultCheckRequired(self.url)

        (data,rurl) = self.get_request_redirected(self.url)
        # logger.debug(data)
        ## for language domains
        self._setURL(rurl)
        logger.debug("set opened url:%s"%self.url)
        soup = self.make_soup(data)

        if "This submission is awaiting moderator's approval" in data:
            raise exceptions.StoryDoesNotExist("This submission is awaiting moderator's approval. %s"%self.url)

        ## not series URL, assumed to be a chapter.  Look for Story
        ## Info block of post-beta page.  I don't think it should happen?
        if '/series/se' not in self.url:
            if not soup.select_one('div.page__aside'):
                raise exceptions.FailedToDownload("Missing Story Info block, Beta turned off?")

            storyseriestag = soup.select_one('a.bn_av')
            # logger.debug("Story Series Tag:%s"%storyseriestag)

            if storyseriestag:
                self._setURL(storyseriestag['href'])
                data = self.get_request(storyseriestag['href'])
                # logger.debug(data)
                soup = self.make_soup(data)
                # logger.debug(soup)
            else:
                logger.debug("One-shot")

        isSingleStory = '/series/se' not in self.url

        ## common between one-shots and multi-chapters

        # title
        self.story.setMetadata('title', stripHTML(soup.select_one('h1')))
        # logger.debug(self.story.getMetadata('title'))

        # author
        ## XXX This is still the author URL like:
        ## https://www.literotica.com/stories/memberpage.php?uid=999999&page=submissions
        ## because that's what's on the page.  It redirects to the /authors/ page.
        ## Only way I know right now to get the /authors/ is to make
        ## the req and look at the redirect.
        ## Should change to /authors/ if/when it starts appearing.
        ## Assuming it's in the same place.
        authora = soup.find("a", class_="y_eU")
        authorurl = authora['href']
        if authorurl.startswith('//'):
            authorurl = self.parsedUrl.scheme+':'+authorurl
        # logger.debug(authora)
        # logger.debug(authorurl)
        self.story.setMetadata('author', stripHTML(authora))
        self.story.setMetadata('authorUrl', authorurl)
        if '?' in authorurl:
            self.story.setMetadata('authorId', urlparse.parse_qs(authorurl.split('?')[1])['uid'][0])
        elif '/authors/' in authorurl:
            self.story.setMetadata('authorId', authorurl.split('/')[-1])
        else: # if all else fails
            self.story.setMetadata('authorId', stripHTML(authora))

        self.story.extendList('eroticatags', [ stripHTML(t).title() for t in soup.select('div#tabpanel-tags a.av_as') ])

        ## look first for 'Series Introduction', then Info panel short desc
        ## series can have either, so put in common code.
        introtag = soup.select_one('div.bp_rh p')
        descdiv = soup.select_one('div#tabpanel-info div.bn_B')
        if introtag and stripHTML(introtag):
            # make sure there's something in the tag.
            self.setDescription(self.url,introtag)
        elif descdiv and stripHTML(descdiv):
            # make sure there's something in the tag.
            self.setDescription(self.url,descdiv)
        else:
            ## Only for backward compatibility with 'stories' that
            ## don't have an intro or short desc.
            descriptions = []
            for i, chapterdesctag in enumerate(soup.select('p.br_rk')):
                # get rid of category link
                chapterdesctag.a.decompose()
                descriptions.append("%d. %s" % (i + 1, stripHTML(chapterdesctag)))
            self.setDescription(authorurl,"<p>"+"</p>\n<p>".join(descriptions)+"</p>")

        if isSingleStory:
            ## one-shots don't *display* date info, but they have it
            ## hidden in <script>
            ## shows _date_approve "date_approve":"01/31/2024"

            ## multichap also have "date_approve", but they have
            ## several and they're more than just the story chapters.
            date = re.search(r'"date_approve":"(\d\d/\d\d/\d\d\d\d)"',data)
            if date:
                dateval = makeDate(date.group(1), self.dateformat)
                self.story.setMetadata('datePublished', dateval)
                self.story.setMetadata('dateUpdated', dateval)

            ## one-shots assumed completed.
            self.story.setMetadata('status','Completed')

            # Add the category from the breadcumb.
            self.story.addToList('category', soup.find('div', id='BreadCrumbComponent').findAll('a')[1].string)

            ## one-shot chapter
            self.add_chapter(self.story.getMetadata('title'), self.url)

        else:
            ## Multi-chapter stories.  AKA multi-part 'Story Series'.
            bn_antags = soup.select('div#tabpanel-info p.bn_an')
            # logger.debug(bn_antags)
            if bn_antags:
                dates = []
                for datetag in bn_antags[:2]:
                    datetxt = stripHTML(datetag)
                    # remove 'Started:' 'Updated:'
                    # Assume can't use 'Started:' 'Updated:' (vs [0] or [1]) because of lang localization
                    datetxt = datetxt[datetxt.index(':')+1:]
                    dates.append(datetxt)
                # logger.debug(dates)
                self.story.setMetadata('datePublished', makeDate(dates[0], self.dateformat))
                self.story.setMetadata('dateUpdated', makeDate(dates[1], self.dateformat))

            ## bn_antags[2] contains "The author has completed this series." or "The author is still actively writing this series."
            ## I won't be surprised if this breaks later because of lang localization
            if "completed" in stripHTML(bn_antags[-1]):
                self.story.setMetadata('status','Completed')
            else:
                self.story.setMetadata('status','In-Progress')

            ## category from chapter list
            self.story.extendList('category',[ stripHTML(t) for t in soup.select('a.br_rl') ])

            storytitle = self.story.getMetadata('title').lower()
            chapter_name_type = None
            for chapteratag in soup.select('a.br_rj'):
                chapter_title = stripHTML(chapteratag)
                # logger.debug('\tChapter: "%s"' % chapteratag)
                if self.getConfig("clean_chapter_titles"):
                    # strip trailing ch or pt before doing the chapter clean.
                    # doesn't remove from story title metadata
                    storytitle = re.sub(r'^(.*?)( (ch|pt))?$',r'\1',storytitle)
                    if chapter_title.lower().startswith(storytitle):
                        chapter = chapter_title[len(storytitle):].strip()
                        # logger.debug('\tChapter: "%s"' % chapter)
                        if chapter == '':
                            chapter_title = 'Chapter %d' % (self.num_chapters() + 1)
                            # Sometimes the first chapter does not have type of chapter
                            if self.num_chapters() == 0:
                                # logger.debug('\tChapter: first chapter without chapter type')
                                chapter_name_type = None
                        else:
                            separater_char = chapter[0]
                            # logger.debug('\tseparater_char: "%s"' % separater_char)
                            chapter = chapter[1:].strip() if separater_char in [":", "-"] else chapter
                            # logger.debug('\tChapter: "%s"' % chapter)
                            if chapter.lower().startswith('ch.'):
                                chapter = chapter[len('ch.'):].strip()
                                try:
                                    chapter_title = 'Chapter %d' % int(chapter)
                                except:
                                    chapter_title = 'Chapter %s' % chapter
                                chapter_name_type = 'Chapter' if chapter_name_type is None else chapter_name_type
                                # logger.debug('\tChapter: chapter_name_type="%s"' % chapter_name_type)
                            elif chapter.lower().startswith('pt.'):
                                chapter = chapter[len('pt.'):].strip()
                                try:
                                    chapter_title = 'Part %d' % int(chapter)
                                except:
                                    chapter_title = 'Part %s' % chapter
                                chapter_name_type = 'Part' if chapter_name_type is None else chapter_name_type
                                # logger.debug('\tChapter: chapter_name_type="%s"' % chapter_name_type)
                            elif separater_char in [":", "-"]:
                                chapter_title = chapter
                                # logger.debug('\tChapter: taking chapter text as whole')

                # /series/se does include full URLs current.
                chapurl = chapteratag['href']

                # logger.debug("Chapter URL: " + chapurl)
                self.add_chapter(chapter_title, chapurl)

            # <img src="https://uploads.literotica.com/series/cover/813-1695143444-desktop-x1.jpg" alt="Series cover">
            coverimg = soup.select_one('img[alt="Series cover"]')
            if coverimg:
                self.setCoverImage(self.url,coverimg['src'])

        #### Attempting averrating from JS metadata.
        try:
            state_start="state='"
            state_end="'</script>"
            i = data.index(state_start)
            if i:
                state = data[i+len(state_start):data.index(state_end,i)].replace("\\'","'").replace("\\\\","\\")
                if state:
                    # logger.debug(state)
                    import json
                    json_state = json.loads(state)
                    # logger.debug(json.dumps(json_state, sort_keys=True,indent=2, separators=(',', ':')))
                    all_rates = []
                    ## one-shot
                    if 'story' in json_state:
                        all_rates = [ float(json_state['story']['data']['rate_all']) ]
                    ## series
                    elif 'series' in json_state:
                        all_rates = [ float(x['rate_all']) for x in json_state['series']['works'] ]
                    if all_rates:
                        self.story.setMetadata('averrating', sum(all_rates) / len(all_rates))
        except Exception as e:
            logger.debug("Processing JSON to find averrating failed. (%s)"%e)

        ## Features removed because not supportable by new site form:
        ## averrating metadata entry
        ## order_chapters_by_date option
        ## use_meta_keywords option
        return

    def getPageText(self, raw_page, url):
        # logger.debug('Getting page text')
#         logger.debug(soup)
        raw_page = raw_page.replace('<div class="b-story-body-x x-r15"><div><p>','<div class="b-story-body-x x-r15"><div>')
#         logger.debug("\tChapter text: %s" % raw_page)
        page_soup = self.make_soup(raw_page)
        [comment.extract() for comment in page_soup.findAll(string=lambda text:isinstance(text, Comment))]
        fullhtml = ""
        for aa_ht_div in page_soup.find_all('div', 'aa_ht'):
            if aa_ht_div.div:
                html = unicode(aa_ht_div.div)
                # Strip some starting and ending tags,
                html = re.sub(r'^<div.*?>', r'', html)
                html = re.sub(r'</div>$', r'', html)
                html = re.sub(r'<p></p>$', r'', html)
                fullhtml = fullhtml + html
        # logger.debug('getPageText - fullhtml: %s' % fullhtml)
        return fullhtml

    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        raw_page = self.get_request(url)
        page_soup = self.make_soup(raw_page)
        pages = page_soup.find('div',class_='l_bH')

        fullhtml = ""
        chapter_description = ''
        if self.getConfig("description_in_chapter"):
            chapter_description = page_soup.find("meta", {"name" : "description"})['content']
            # logger.debug("\tChapter description: %s" % chapter_description)
            chapter_description = '<p><b>Description:</b> %s</p><hr />' % chapter_description
        fullhtml += self.getPageText(raw_page, url)
        if pages:
            ## look for highest numbered page, they're not all listed
            ## when there are many.

            last_page_link = pages.find_all('a', class_='l_bJ')[-1]
            last_page_no = int(urlparse.parse_qs(last_page_link['href'].split('?')[1])['page'][0])
            # logger.debug(last_page_no)
            for page_no in range(2, last_page_no+1):
                page_url = url +  "?page=%s" % page_no
                # logger.debug("page_url= %s" % page_url)
                raw_page = self.get_request(page_url)
                fullhtml += self.getPageText(raw_page, url)

#         logger.debug(fullhtml)
        page_soup = self.make_soup(fullhtml)
        fullhtml = self.utf8FromSoup(url, self.make_soup(fullhtml))
        fullhtml = chapter_description + fullhtml
        fullhtml = unicode(fullhtml)

        return fullhtml


def getClass():
    return LiteroticaSiteAdapter
