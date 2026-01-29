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
import json

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
        #logger.debug("LiteroticaComAdapter:__init__ - url='%s'" % url)

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
                     r"https://\2",
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
        return "https://www.literotica.com/s/story-title https://www.literotica.com/series/se/9999999 https://www.literotica.com/s/story-title https://www.literotica.com/i/image-or-comic-title https://www.literotica.com/p/poem-title https://portuguese.literotica.com/s/story-title https://german.literotica.com/s/story-title"

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

    ## apply clean_chapter_titles
    def add_chapter(self,chapter_title,url,othermeta={}):
        if self.getConfig("clean_chapter_titles"):
            storytitle = self.story.getMetadataRaw('title').lower()
            chapter_name_type = None
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
        super(LiteroticaSiteAdapter, self).add_chapter(chapter_title,url,othermeta)

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

        ## 2025Feb - domains other than www now use different HTML.
        ## Need to look for two different versions of basically
        ## everything.

        ## not series URL, assumed to be a chapter.  Look for Story
        ## Info block of post-beta page.  I don't think it should happen?
        if '/series/se' not in self.url:
            #logger.debug(data)
            ## looking for /series/se URL to indicate this is a
            ## chapter.
            if not soup.select_one('div.page__aside') and not soup.select_one('div.sidebar') and not soup.select_one('div[class^="_sidebar_"]'):
                raise exceptions.FailedToDownload("Missing Story Info block, Beta turned off?")

            storyseriestag = soup.select_one('a.bn_av')
            if not storyseriestag:
                storyseriestag = soup.select_one('a[class^="_files__link_"]')
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

        if not isSingleStory:
            # Normilize the url?
            state = re.findall(r"prefix\=\"/series/\",state='(.+?)'</script>", data)
            json_state = json.loads(state[0].replace("\\'","'").replace("\\\\","\\"))
            url_series_id = unicode(re.match(self.getSiteURLPattern(),self.url).group('storyseriesid'))
            json_series_id = unicode(json_state['series']['data']['id'])
            if json_series_id != url_series_id:
                res = re.sub(url_series_id, json_series_id, unicode(self.url))
                logger.debug("Normalized url: %s"%res)
                self._setURL(res)

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
        if not authora:
            authora = soup.select_one('a[class^="_author__title"]')
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

        if soup.select('div#tabpanel-tags'):
            # logger.debug("tags1")
            self.story.extendList('eroticatags', [ stripHTML(t).title() for t in soup.select('div#tabpanel-tags a.av_as') ])
        if soup.select('div[class^="_widget__tags_"]'):
            # logger.debug("tags2")
            self.story.extendList('eroticatags', [ stripHTML(t).title() for t in soup.select('div[class^="_widget__tags_"] a[class^="_tags__link_"]') ])
        # logger.debug(self.story.getList('eroticatags'))

        ## look first for 'Series Introduction', then Info panel short desc
        ## series can have either, so put in common code.
        desc = []
        introtag = soup.select_one('div.bp_rh')
        descdiv = soup.select_one('div#tabpanel-info div.bn_B') or \
                  soup.select_one('div[class^="_tab__pane_"] div[class^="_widget__info_"]')
        if introtag and stripHTML(introtag):
            # make sure there's something in the tag.
            # logger.debug("intro %s"%introtag)
            desc.append(unicode(introtag))
        elif descdiv and stripHTML(descdiv):
            # make sure there's something in the tag.
            # logger.debug("desc %s"%descdiv)
            desc.append(unicode(descdiv))
        if not desc or self.getConfig("include_chapter_descriptions_in_summary"):
            ## Only for backward compatibility with 'stories' that
            ## don't have an intro or short desc.
            descriptions = []
            for i, chapterdesctag in enumerate(soup.select('p.br_rk')):
                # remove category link, but only temporarily
                a = chapterdesctag.a.extract()
                descriptions.append("%d. %s" % (i + 1, stripHTML(chapterdesctag)))
                # now put it back--it's used below
                chapterdesctag.append(a)
            desc.append(unicode("<p>"+"</p>\n<p>".join(descriptions)+"</p>"))

        self.setDescription(self.url,u''.join(desc))

        if isSingleStory:
            ## one-shots don't *display* date info, but they have it
            ## hidden in <script>
            ## shows _date_approve "date_approve":"01/31/2024"

            ## multichap also have "date_approve", but they have
            ## several and they're more than just the story chapters.
            date = re.search(r'"date_approve":"(\d\d/\d\d/\d\d\d\d)"',data)
            if not date:
                date = re.search(r'date_approve:"(\d\d/\d\d/\d\d\d\d)"',data)
            if date:
                dateval = makeDate(date.group(1), self.dateformat)
                self.story.setMetadata('datePublished', dateval)
                self.story.setMetadata('dateUpdated', dateval)

            ## one-shots don't have same json data to get aver_rating
            ## from below. This kludge matches the data_approve
            rateall = re.search(r'rate_all:([\d\.]+)',data)
            if rateall:
                self.story.setMetadata('averrating', '%4.2f' % float(rateall.group(1)))

            ## one-shots assumed completed.
            self.story.setMetadata('status','Completed')

            # Add the category from the breadcumb.
            breadcrumbs = soup.find('div', id='BreadCrumbComponent')
            if not breadcrumbs:
                breadcrumbs = soup.select_one('ul[class^="_breadcrumbs_list_"]')
            if not breadcrumbs:
                # _breadcrumbs_18u7l_1
                breadcrumbs = soup.select_one('nav[class^="_breadcrumbs_"]')
            self.story.addToList('category', breadcrumbs.find_all('a')[1].string)

            ## one-shot chapter
            self.add_chapter(self.story.getMetadata('title'), self.url)

        else:
            ## Multi-chapter stories.  AKA multi-part 'Story Series'.
            bn_antags = soup.select('div#tabpanel-info p.bn_an')
            # logger.debug(bn_antags)
            if bn_antags and not self.getConfig("dates_from_chapters"):
                ## Use dates from series metadata unless dates_from_chapters is enabled
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

            for chapteratag in soup.select('a.br_rj'):
                chapter_title = stripHTML(chapteratag)
                # logger.debug('\tChapter: "%s"' % chapteratag)
                # /series/se does include full URLs current.
                chapurl = chapteratag['href']
                # logger.debug("Chapter URL: " + chapurl)
                self.add_chapter(chapter_title, chapurl)

            # <img src="https://uploads.literotica.com/series/cover/813-1695143444-desktop-x1.jpg" alt="Series cover">
            coverimg = soup.select_one('img[alt="Series cover"]')
            if coverimg:
                self.setCoverImage(self.url,coverimg['src'])

        #### Attempting averrating from JS metadata.
        #### also alternate chapters from json
        try:
            state_start="state='"
            state_end="'</script>"
            i = data.index(state_start)
            if i:
                state = data[i+len(state_start):data.index(state_end,i)].replace("\\'","'").replace("\\\\","\\")
                if state:
                    # logger.debug(state)
                    json_state = json.loads(state)
                    # logger.debug(json.dumps(json_state, sort_keys=True,indent=2, separators=(',', ':')))
                    all_rates = []
                    if 'series' in json_state:
                        all_rates = [ float(x['rate_all']) for x in json_state['series']['works'] ]

                        ## Extract dates from chapter approval dates if dates_from_chapters is enabled
                        if self.getConfig("dates_from_chapters"):
                            date_approvals = []
                            for work in json_state['series']['works']:
                                if 'date_approve' in work:
                                    try:
                                        date_approvals.append(makeDate(work['date_approve'], self.dateformat))
                                    except:
                                        pass
                            if date_approvals:
                                # Oldest date is published, newest is updated
                                date_approvals.sort()
                                self.story.setMetadata('datePublished', date_approvals[0])
                                self.story.setMetadata('dateUpdated', date_approvals[-1])
                    if all_rates:
                        self.story.setMetadata('averrating', '%4.2f' % (sum(all_rates) / float(len(all_rates))))

                    ## alternate chapters from JSON
                    if self.num_chapters() < 1:
                        logger.debug("Getting Chapters from series JSON")
                        seriesid = json_state.get('series',{}).get('data',{}).get('id',None)
                        if seriesid:
                            logger.info("Fetching chapter data from JSON")
                            logger.debug(seriesid)
                            series_json = json.loads(self.get_request('https://literotica.com/api/3/series/%s/works'%seriesid))
                            # logger.debug(json.dumps(series_json, sort_keys=True,indent=2, separators=(',', ':')))
                            for chap in series_json:
                                self.add_chapter(chap['title'], 'https://www.literotica.com/s/'+chap['url'])

                                ## Collect tags from series/story page if tags_from_chapters is enabled
                                if self.getConfig("tags_from_chapters"):
                                    self.story.extendList('eroticatags', [ stripHTML(t['tag']).title() for t in chap['tags'] ])


        except Exception as e:
            logger.warning("Processing JSON failed. (%s)"%e)

        ## Features removed because not supportable by new site form:
        ## averrating metadata entry
        ## order_chapters_by_date option
        ## use_meta_keywords option
        return

    def getPageText(self, raw_page, url):
        logger.debug('Getting page text')
        raw_page = raw_page.replace('<div class="b-story-body-x x-r15"><div><p>','<div class="b-story-body-x x-r15"><div>')
        # logger.debug("\tChapter text: %s" % raw_page)
        page_soup = self.make_soup(raw_page)
        [comment.extract() for comment in page_soup.find_all(string=lambda text:isinstance(text, Comment))]
        fullhtml = ""
        for aa_ht_div in page_soup.find_all('div', 'aa_ht') + page_soup.select('div[class^="_article__content_"]'):
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
        if not pages:
            pages = page_soup.select_one('div._pagination_h0sum_1')
        if not pages:
            pages = page_soup.select_one('div.clearfix.panel._pagination_1400x_1')
        if not pages:
            pages = page_soup.select_one('div[class^="panel clearfix _pagination_"]')
        # logger.debug(pages)

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

            last_page_links = pages.find_all('a', class_='l_bJ')
            if not last_page_links:
                last_page_links = pages.select('a[class^="_pagination__item_"]')
            last_page_link = last_page_links[-1]
            last_page_no = int(urlparse.parse_qs(last_page_link['href'].split('?')[1])['page'][0])
            # logger.debug(last_page_no)
            for page_no in range(2, last_page_no+1):
                page_url = url +  "?page=%s" % page_no
                # logger.debug("page_url= %s" % page_url)
                raw_page = self.get_request(page_url)
                fullhtml += self.getPageText(raw_page, url)

        #logger.debug(fullhtml)
        page_soup = self.make_soup(fullhtml)
        fullhtml = self.utf8FromSoup(url, self.make_soup(fullhtml))
        fullhtml = chapter_description + fullhtml
        fullhtml = unicode(fullhtml)

        return fullhtml

    def get_urls_from_page(self,url,normalize):
        from ..geturls import get_urls_from_html

        ## hook for logins, etc.
        self.before_get_urls_from_page(url,normalize)

        # this way it uses User-Agent or other special settings.
        data = self.get_request(url,usecache=False)
        soup = self.make_soup(data)

        page_urls = get_urls_from_html(soup, url, configuration=self.configuration, normalize=normalize)

        if not self.getConfig("fetch_stories_from_api",True):
            logger.debug('fetch_stories_from_api Not enabled')
            return {'urllist': page_urls}

        user_story_list = re.search(r'literotica\.com/authors/.+?/lists\?listid=(?P<list_id>\d+)', url)
        fav_authors = re.search(r'literotica\.com/authors/.+?/favorites', url)
        written = re.search(r'literotica.com/authors/.+?/works/', url)
        logger.debug((bool(user_story_list), bool(fav_authors), bool(written)))

        # If the url is not supported
        if not user_story_list and not fav_authors and not written:
            logger.debug('No supported link. %s', url)
            return {'urllist':page_urls}

        # Grabbing the main list where chapters are contained.
        if user_story_list:
            js_story_list = re.search(r';\$R\[\d+?\]\(\$R\[\d+?\],\$R\[\d+?\]\);\$R\[\d+?\]\(\$R\[\d+?\],\$R\[\d+?\]=\{success:!\d,current_page:(?P<current_page>\d+?),last_page:(?P<last_page>\d+?),total:\d+?,per_page:\d+,(has_series:!\d)?data:\$R\[\d+?\]=\[\$R\[\d+?\]=(?P<data>.+)\}\]\}\);', data) # }] } } });  \$R\[\d+?\]\(\$R\[\d+?\],\$R\[\d+?\]\);\$R\[\d+?]\(\$R\[\d+?\],\$R\[\d+?\]=\{sliders:
            logger.debug('user_story_list ID [%s]'%user_story_list.group('list_id'))
        else:
            js_story_list = re.search(r'\$R\[\d+?\]\(\$R\[\d+?\],\$R\[\d+?\]={current_page:(?P<current_page>\d+?),last_page:(?P<last_page>\d+?),total:\d+?,per_page:\d+,(has_series:!\d,)?data:\$R\[\d+\]=\[\$R\[\d+\]=\{(?!aim)(?P<data>.+)\}\);_\$HY\.r\[', data)

        # In case the regex becomes outdated
        if not js_story_list:
            logger.debug('Failed to grab data from the js.')
            return {'urllist':page_urls}

        user = None
        script_tags = soup.find_all('script')
        for script in script_tags:
            if not script.string:
                continue
            # Getting author from the js.
            user = re.search(r'_\$HY\.r\[\"AuthorQuery\[\\\"(?P<author>.+?)\\\"\]\"\]', script.string)
            if user != None:
                logger.debug("User: [%s]"%user.group('author'))
                break
        else:
            logger.debug('Failed to get a username')
            return {'urllist': page_urls}

        # Extract the current (should be 1) and last page numbers from the js.
        logger.debug("Pages %s/%s"%(js_story_list.group('current_page'), js_story_list.group('last_page')))

        urls = []
        # Necessary to format a proper link as there were no visible data specifying what kind of link that should be.
        cat_to_link = {'adult-comics': 'i', 'erotic-art': 'i', 'illustrated-poetry': 'p', 'erotic-audio-poetry': 'p', 'erotic-poetry': 'p', 'non-erotic-poetry': 'p'}
        stories_found = re.findall(r"category_info:\$R\[.*?type:\".+?\",pageUrl:\"(.+?)\"}.+?,type:\"(.+?)\",url:\"(.+?)\",", js_story_list.group('data'))
        for story in stories_found:
            story_category, story_type, story_url = story
            urls.append('https://www.literotica.com/%s/%s'%(cat_to_link.get(story_category, 's'), story_url))

        # Removes the duplicates
        seen = set()
        urls = [x for x in (page_urls + urls) if not (x in seen or seen.add(x))]
        logger.debug("Found [%s] stories so far."%len(urls))

        # Sometimes the rest of the stories are burried in the js so no fetching in necessery.
        if js_story_list.group('last_page') == js_story_list.group('current_page'):
            return {'urllist': urls}

        user = urlparse.quote(user.group(1))
        logger.debug("Escaped user: [%s]"%user)

        if written:
            category = re.search(r"_\$HY\.r\[\"AuthorSeriesAndWorksQuery\[\\\".+?\\\",\\\"\D+?\\\",\\\"(?P<type>\D+?)\\\"\]\"\]=\$R\[\d+?\]=\$R\[\d+?\]\(\$R\[\d+?\]=\{", data)
        elif fav_authors:
            category = re.search(r"_\$HY\.r\[\"AuthorFavoriteWorksQuery\[\\\".+?\\\",\\\"(?P<type>\D+?)\\\",\d\]\"\]=\$R\[\d+?\]=\$R\[\d+?\]\(\$R\[\d+?\]={", data)

        if not user_story_list and not category:
            logger.debug("Type of works not found")
            return {'urllist': urls}

        last_page = int(js_story_list.group('last_page'))
        current_page = int(js_story_list.group('current_page')) + 1
        # Fetching the remaining urls from api. Can't trust the number given about the pages left from a website. Sometimes even the api returns outdated number of pages.
        while current_page <= last_page:
            i = len(urls)
            logger.debug("Pages %s/%s"%(current_page, int(last_page)))
            if fav_authors:
                jsn = self.get_request('https://literotica.com/api/3/users/{}/favorite/works?params=%7B%22page%22%3A{}%2C%22pageSize%22%3A50%2C%22type%22%3A%22{}%22%2C%22withSeriesDetails%22%3Atrue%7D'.format(user, current_page, category.group('type')))
            elif user_story_list:
                jsn = self.get_request('https://literotica.com/api/3/users/{}/list/{}?params=%7B%22page%22%3A{}%2C%22pageSize%22%3A50%2C%22withSeriesDetails%22%3Atrue%7D'.format(user, user_story_list.group('list_id'), current_page))
            else:
                jsn = self.get_request('https://literotica.com/api/3/users/{}/series_and_works?params=%7B%22page%22%3A{}%2C%22pageSize%22%3A50%2C%22sort%22%3A%22date%22%2C%22type%22%3A%22{}%22%2C%22listType%22%3A%22expanded%22%7D'.format(user, current_page, category.group('type')))

            urls_data = json.loads(jsn)
            last_page = urls_data["last_page"]
            current_page = int(urls_data["current_page"]) + 1
            for story in urls_data['data']:
                #logger.debug('parts' in story)
                if story['url'] and story.get('work_count') == None:
                    urls.append('https://www.literotica.com/%s/%s'%(cat_to_link.get(story["category_info"]["pageUrl"], 's'), str(story['url'])))
                    continue
                # Most of the time series has no url specified and contains all of the story links belonging to the series
                urls.append('https://www.literotica.com/series/se/%s'%str(story['id']))
                for series_story in story['parts']:
                    urls.append('https://www.literotica.com/%s/%s'%(cat_to_link.get(series_story["category_info"]["pageUrl"], 's'), str(series_story['url'])))
            logger.debug("Found [%s] stories."%(len(urls) - i))

        # Again removing duplicates.
        seen = set()
        urls = [x for x in urls if not (x in seen or seen.add(x))]

        logger.debug("Found total of [%s] stories"%len(urls))
        return {'urllist':urls}

def getClass():
    return LiteroticaSiteAdapter
