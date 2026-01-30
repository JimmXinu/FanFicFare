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
import logging, time
logger = logging.getLogger(__name__)
import re, math

from hashlib import sha256
from base64 import urlsafe_b64encode as b64encode

from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six.moves import http_cookiejar as cl
from ..six.moves.urllib.parse import urlparse
from ..six import text_type as unicode

from .base_adapter import BaseSiteAdapter, makeDate

def getClass():
    return SyosetuComAdapter

def getEntry(soup, *args):
    for arg in args:
            target = soup.find('dt', string=arg)
            if target is not None:
                    return target.findNext('dd')
    return None

class SyosetuComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.story.setMetadata('siteabbrev', 'syosetu')
        self.story.setMetadata('language', 'Japanese')

        splitPath = self.path.split('/')
        self.storyId = splitPath[-2] if (splitPath[-1] == '') else splitPath[-1]
        self.story.setMetadata('storyId', self.storyId)

        self._setURL('https://' + self.host + '/' + self.storyId + '/')

        self.is_adult = False

    @staticmethod
    def getSiteDomain():
        return 'syosetu.com'

    @classmethod
    def getAcceptDomains(cls):
        return [
            'ncode.syosetu.com',
            'novel18.syosetu.com',
            'mypage.syosetu.com',
            'xmypage.syosetu.com',
        ]

    @classmethod
    def getSiteExampleURLs(cls):
        return ("https://ncode.syosetu.com/n1234ab/ "
                +"https://novel18.syosetu.com/n1234a "
                +"https://ncode.syosetu.com/novelview/infotop/ncode/n1234ab "
                +"https://novel18.syosetu.com/novelview/infotop/ncode/n1234a/")

    def getSiteURLPattern(self):
        return r"^https?://(ncode|novel18)\.syosetu\.com/(novelview/infotop/ncode/)?n[0-9]+[a-z]+/?$"

    def set_adult_cookie(self):
        cookie = cl.Cookie(version=0, name='over18', value='yes',
                           port=None, port_specified=False,
                           domain=self.getSiteDomain(), domain_specified=False, domain_initial_dot=False,
                           path='/', path_specified=True,
                           secure=False,
                           expires=time.time()+10000,
                           discard=False,
                           comment=None,
                           comment_url=None,
                           rest={'HttpOnly': None},
                           rfc2109=False)
        self.get_configuration().get_cookiejar().set_cookie(cookie)

    def performLogin(self, url):
        params = {}
        if self.password:
            params['narouid'] = self.username
            params['pass'] = self.password
        else:
            params['narouid'] = self.getConfig('username')
            params['pass'] = self.getConfig('password')

        if params['narouid'] and params['pass']:
            loginUrl = 'https://syosetu.com/login/login/'
            logger.info("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                                params['narouid']))
            d = self.post_request(loginUrl, params)
            if 'href="https://syosetu.com/login/logout/"' not in d:
                logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                                 params['narouid']))
                raise exceptions.FailedToLogin(url,params['narouid'])

    def extractChapterUrlsAndMetadata(self):
        """
        Oneshots are located at /n1234ab/

        Serials are located at /n1234ab/#/ (# is a non-padded number,
        like 1, 2, ..., 394). Serials can have a single chapter.

        Most metadata is located at /novelview/infotop/ncode/n1234ab/

        Chapter publish and update times are located at /n1234ab/?p=#
        paginated in groups of 100
        """

        if self.is_adult or self.getConfig('is_adult'):
            self.set_adult_cookie()

        # self.performLogin(self.url)

        infoUrl = 'https://' + self.host + '/novelview/infotop/ncode/' + self.storyId + '/'
        # don't use cache if manual is_adult--should only happen
        # if it's an adult story and they don't have is_adult in ini.
        (infoData,infoRurl) = self.get_request_redirected(infoUrl,
                                                          usecache=(not self.is_adult))
        # IDs for general (adult) stories redirect to ncode (novel18)
        # despite IDs being shared, stories can't be age-restricted automatically
        if infoUrl != infoRurl:
            infoUrl = infoRurl
            self.host = urlparse(infoRurl).netloc
            self._setURL('https://' + self.host + '/' + self.storyId + '/')

        if (self.host.split('.')[0] == 'novel18'):
            if not (self.is_adult or self.getConfig("is_adult")):
                raise exceptions.AdultCheckRequired(self.url)

        # Did not find story. (Invalid ID)
        if '投稿済作品が見つかりません。' in infoData:
            raise exceptions.StoryDoesNotExist(self.url)

        # Story has been deleted.
        if 'この作品は作者によって削除されました。' in infoData:
            raise exceptions.StoryDoesNotExist(self.url)

        if self.getConfig('always_login') and 'href="https://syosetu.com/login/input/"' in infoData:
            self.performLogin(self.url)
            infoData = self.get_request(infoUrl, usecache=False)

        infoSoup = self.make_soup(infoData)

        # Title

        title = infoSoup.find('a', href=self.url).text.strip()
        self.story.setMetadata('title', title)

        # Author

        # the author URL can always be found at the bottom of the page
        # differs between ncode and novel18
        authorUrl = (infoSoup.find('a', string='作者マイページ')
                     or infoSoup.find('a', string='作者Xマイページ'))['href']
        self.story.setMetadata('authorUrl', authorUrl)

        authorId = urlparse(authorUrl).path.split('/')[1]
        self.story.setMetadata('authorId', authorId)

        authorElement = getEntry(infoSoup, '作者名')
        author = authorElement.text.strip()
        try:
            if authorElement.find('a') is None:
                # when the author isn't linked in the table, a pseudonym has been used
                realAuthor = self.make_soup(self.get_request(authorUrl)).find('title').text.strip()
                if realAuthor != author:
                    author = author + ' (' + realAuthor + ')'
        except:
            logger.info('Author parsing failed, using pseudonym.')
        self.story.setMetadata('author', author)

        # Description

        description = getEntry(infoSoup, 'あらすじ')
        description.name = 'div'
        description['class'] = 'description'
        self.setDescription(self.url, description)

        # Date Published and Updated

        # 2017年 05月16日 17時30分
        published = makeDate(getEntry(infoSoup, '掲載日').text.strip(),
                             '%Y年 %m月%d日 %H時%M分')
        self.story.setMetadata('datePublished', published)

        updated = published
        updateElement = getEntry(infoSoup,
                                 '最終部分掲載日', # last part published (complete)
                                 '最新部分掲載日', # latest part published
                                 '最終更新日', # last update (complete)
                                 '最新掲載日' # last update
                                 )
        if updateElement is not None:
            updated = makeDate(updateElement.text.strip(),
                               '%Y年 %m月%d日 %H時%M分')
        self.story.setMetadata('dateUpdated', updated)

        # Series

        # differs between ncode and novel18
        series = getEntry(infoSoup, 'シリーズ', 'Xシリーズ')
        try:
            if series is not None:
                seriesName = series.text.strip()
                seriesUrl = series.find('a')['href']

                seriesSoup = self.make_soup(self.get_request(seriesUrl))
                alist = seriesSoup.select('.p-series-novellist .p-series-novellist__title a')
                i = 1
                for a in alist:
                    if self.storyId in a['href']:
                        self.setSeries(seriesName, i)
                        self.story.setMetadata('seriesUrl', seriesUrl)
                        break
                    i += 1
        except:
            logger.info('Series parsing failed.')

        # Character count

        # 123,789文字
        numMoji = int(re.sub(r'[^\d]', '', getEntry(infoSoup, '文字数').text.strip()))
        self.story.setMetadata('numWords', numMoji)

        # Status and Chapter count

        noveltype = infoSoup.find('span', {'class':'p-infotop-type__type'})
        if noveltype.text.strip() == '短編':
            numChapters = 1
            oneshot = True
            completed = True
        else:
            # '全1,292エピソード\n'
            numChapters = int(re.sub(r'[^\d]', '', infoSoup.find('span', {'class':'p-infotop-type__allep'}).text.strip()))
            oneshot = False
            completed = True if noveltype == '完結済' else False
        self.story.setMetadata('status', 'Completed' if completed else 'In-Progress')

        # Keywords

        flags = []
        # not sure what it looks like if a work has no tags
        tagsElement = getEntry(infoSoup, 'キーワード')
        for tag in tagsElement.text.split():
            self.story.addToList('freeformtags', tag)

        # Rating, Genre, and Imprint

        if self.host.split('.')[0] == 'novel18':
            rating = 'R18'
            # ミッドナイトノベルズ(大人向け)
            imprint = getEntry(infoSoup, '掲載サイト').text.strip().split('(')[0]
            self.story.setMetadata('imprint', imprint)
        else:
            rating = 'R15' if 'R15' in flags else 'G'
            # ハイファンタジー〔ファンタジー〕
            fullgenre = getEntry(infoSoup, 'ジャンル').text.strip()
            self.story.setMetadata('fullgenre', fullgenre)
            smallgenre = fullgenre.split('〔')[0]
            self.story.setMetadata('smallgenre', smallgenre)
            biggenre = fullgenre.split('〔')[1][:-1]
            self.story.setMetadata('biggenre', biggenre)
        self.story.setMetadata('rating', rating)

        # Comments, Reviews, Bookmarks, Points

        commentsElement = getEntry(infoSoup, '感想')
        reviewsElement = getEntry(infoSoup, 'レビュー')
        bookmarksElement = getEntry(infoSoup, 'ブックマーク登録')
        ratingPointsElement = getEntry(infoSoup, '総合評価')
        overallPointsElement = getEntry(infoSoup, '評価ポイント')

        # if the story is unlinked from author page, stats will be hidden

        # '\n116件\n\n'
        if commentsElement is not None:
            self.story.setMetadata('comments',
                                   int(re.sub(r'[^\d]', '', commentsElement.next_element.strip())))

        # 171件
        if reviewsElement is not None:
            self.story.setMetadata('reviews',
                                   int(re.sub(r'[^\d]', '', reviewsElement.next_element.strip())))

        # 108,610件
        if bookmarksElement is not None:
            self.story.setMetadata('bookmarks',
                                   int(re.sub(r'[^\d]', '', bookmarksElement.next_element.strip())))

        # 166,944pt or ※非公開
        if (ratingPointsElement is not None and
            ratingPointsElement.text.strip() != '※非公開'):
            self.story.setMetadata('ratingpoints',
                                   int(re.sub(r'[^\d]', '', ratingPointsElement.next_element.strip())))

        # 384,164pt or ※非公開
        if (overallPointsElement is not None and
            overallPointsElement.text.strip() != '※非公開'):
            self.story.setMetadata('overallpoints',
                                   int(re.sub(r'[^\d]', '', overallPointsElement.next_element.strip())))

        # Bookmark metadata

        if self.getConfig("always_login"):
            if infoSoup.find('div', {'data-remodal-id':'setting_bookmark'}) is None:
                self.story.setMetadata('bookmarked', False)
                self.story.setMetadata('subscribed', False)
            else:
                self.story.setMetadata('bookmarked', True)
                modal = infoSoup.find('div', {'data-remodal-id':'setting_bookmark'})

                # bookmark category name
                bookmarkCategory = modal.find('option', {
                    'class':'js-category_select',
                    'selected':'selected'}).text.strip()
                self.story.setMetadata('bookmarkcategory', bookmarkCategory)

                #bookmarkmemo
                if modal.find('input', {'class':'js-bookmark_memo'}).has_attr('value'):
                    self.story.setMetadata('bookmarkmemo',
                                           modal.find('input', {'class':'js-bookmark_memo'})['value'].strip())

                #bookmarkprivate
                self.story.setMetadata('bookmarkprivate',
                                       modal.find('input', {
                                           'class':'bookmark_jyokyo',
                                           'value':'1'}).has_attr('checked'))

                #subscribed
                self.story.setMetadata('subscribed',
                                       modal.find('input', {'name':'isnotice'}).has_attr('checked'))

        if oneshot:
            self.add_chapter(title, self.url)
            logger.debug("Story: <%s>", self.story)
            return

        # serialized story

        prependSectionTitles = self.getConfig('prepend_section_titles', 'firstepisode')

        tocSoups = []
        for n in range(1, int(math.ceil(numChapters/100.0))+1):
            tocPage = self.make_soup(self.get_request(self.url + '?p=%s' % n))
            tocSoups.append(tocPage.find('div',{'class':'p-eplist'}))

        sectionTitle = None
        newSection = False
        for tocSoup in tocSoups:
            for child in tocSoup.findChildren(recursive=False):
                if 'p-eplist__chapter-title' in child['class']:
                    sectionTitle = child.text.strip()
                    newSection = True
                elif 'p-eplist__sublist' in child['class']:
                    epTitle = child.find('a').text.strip()
                    updateElement = child.find('div', {'class':'p-eplist__update'})
                    if updateElement.find('span',{'class':'p-eplist__favep'}) is not None:
                        # a bookmarked story has some extra text added
                        updateElement.next_element.extract()
                        updateElement.next_element.extract()
                    epPublished = updateElement.next_element.strip()
                    epUpdated = ''
                    if updateElement.find('span') is not None:
                        epUpdated = updateElement.find('span')['title'].strip()
                    uniqueKey = b64encode(sha256(('title ' + epTitle +
                                                  ' published ' + epPublished +
                                                  ' updated ' + epUpdated).encode()).digest()).decode()
                    epUrl = 'https://' + self.host + child.find('a')['href'] + '#' + uniqueKey

                    if ((sectionTitle is not None) and
                        ((newSection and prependSectionTitles == 'firstepisode') or
                         prependSectionTitles == 'true')):
                        # bracket with ZWSP to mark presence of the section title
                        epTitle = u'\u200b' + sectionTitle + u'\u3000\u200b' + epTitle

                    self.add_chapter(epTitle, epUrl)
                    newSection = False

        logger.debug("Story: <%s>", self.story)
        return

    def getChapterText(self, url):
        logger.debug('Getting chapter text from <%s>' % url)

        soup = self.make_soup(self.get_request(url))

        divs = soup.find_all('div',{'class':'p-novel__text'})
        text_divs = []
        for div in divs:
            if 'p-novel__text--preface' in div['class']:
                div['class'] = 'novel_p'
            elif 'p-novel__text--afterword' in div['class']:
                div['class'] = 'novel_a'
            else:
                div['class'] = 'novel_honbun'
            if self.getConfig('include_author_notes', True) or div['class'] == 'novel_honbun':
                text_divs.append(unicode(div))
        if not text_divs:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
        soup = self.make_soup(' '.join(text_divs))

        return self.utf8FromSoup(url, soup)

    def before_get_urls_from_page(self,url,normalize):
        # syosetu doesn't show adult series or author pages without the cookie
        if self.getConfig("is_adult"):
            self.set_adult_cookie()

    def get_urls_from_page(self,url,normalize):
        from ..geturls import get_urls_from_html
        # Supporting story page and info page URLs means both links get picked up
        # and return duplicate story IDs without a custom handler.

        # hook for logins, etc.
        self.before_get_urls_from_page(url,normalize)

        # this way it uses User-Agent or other special settings.
        data = self.get_request(url,usecache=False)
        parsedUrlList = get_urls_from_html(self.make_soup(data),
                                           url,
                                           configuration=self.configuration,
                                           normalize=normalize)

        urlList = []
        ncodes = []
        for storyUrl in parsedUrlList:
            parsedUrl = urlparse(storyUrl)
            host = parsedUrl.netloc
            if host in ['ncode.syosetu.com', 'novel18.syosetu.com']:
                splitPath = parsedUrl.path.split('/')
                storyId = splitPath[-2] if (splitPath[-1] == '') else splitPath[-1]
                if storyId not in ncodes:
                    ncodes.append(storyId)
                    urlList.append('https://' + host + '/' + storyId + '/')
            else:
                urlList.append(storyUrl)

        return {'urllist':urlList}
