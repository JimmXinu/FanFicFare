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
import re, json

from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six.moves import http_cookiejar as cl

from .base_adapter import BaseSiteAdapter, makeDate

def getClass():
    return KakuyomuJpAdapter

genres = {
    'FANTASY': '異世界ファンタジー',
    'ACTION': '現代ファンタジー',
    'SF': 'SF',
    'LOVE_STORY': '恋愛',
    'ROMANCE': 'ラブコメ',
    'DRAMA': '現代ドラマ',
    'HORROR': 'ホラー',
    'MYSTERY': 'ミステリー',
    'NONFICTION': 'エッセイ・ノンフィクション',
    'HISTORY': '歴史・時代・伝奇',
    'CRITICISM': '創作論・評論',
    'OTHERS': '詩・童話・その他',
    'FAN_FICTION': '二次創作',
}

class KakuyomuJpAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.story.setMetadata('siteabbrev', 'kakuyomu')
        self.story.setMetadata('language', 'Japanese')

        self.storyId = self.path.split('/')[-1]
        self.story.setMetadata('storyId', self.storyId)

    @staticmethod
    def getSiteDomain():
        return 'kakuyomu.jp'

    @classmethod
    def getSiteExampleURLs(cls):
        return ("https://kakuyomu.jp/works/12341234123412341234")

    def getSiteURLPattern(self):
        return r"^https?://kakuyomu\.jp/works/[0-9]+$"

    def extractChapterUrlsAndMetadata(self):
        data = self.get_request(self.url)

        # Page could not be found
        if 'お探しのページは見つかりませんでした' in data:
            raise exceptions.StoryDoesNotExist(self.url)

        soup = self.make_soup(data)
        info = json.loads(soup.find(id='__NEXT_DATA__').contents[0])['props']['pageProps']['__APOLLO_STATE__']

        workKey = 'Work:%s' % self.storyId

        # Title
        self.story.setMetadata('title', info[workKey]['title'])

        # Author
        authorKey = info[workKey]['author']['__ref']
        self.story.setMetadata('authorId', authorKey.split(':')[1])
        self.story.setMetadata('authorUrl', 'https://kakuyomu.jp/users/%s' % info[authorKey]['name'])
        self.story.setMetadata('author', info[authorKey]['activityName'])

        # Description
        self.setDescription(self.url, info[workKey]['introduction'])
        self.story.setMetadata('catchphrase', info[workKey]['catchphrase'])

        # Date Published and Updated
        # 2024-01-01T03:00:12Z
        self.story.setMetadata('datePublished',
                               makeDate(info[workKey]['publishedAt'], '%Y-%m-%dT%H:%M:%SZ'))
        self.story.setMetadata('dateUpdated',
                               makeDate(info[workKey]['editedAt'], '%Y-%m-%dT%H:%M:%SZ'))

        # Character count
        self.story.setMetadata('numWords', info[workKey]['totalCharacterCount'])

        # Status
        completed = info[workKey]['serialStatus'] == 'COMPLETED'
        self.story.setMetadata('status', 'Completed' if completed else 'In-Progress')

        # Warnings
        rating = 'G'
        if info[workKey]['isCruel']:
            rating = 'R15'
            self.story.addToList('warnings', '残酷描写有り')
        if info[workKey]['isViolent']:
            rating = 'R15'
            self.story.addToList('warnings', '暴力描写有り')
        if info[workKey]['isSexual']:
            rating = 'R15'
            self.story.addToList('warnings', '性描写有り')

        # Tags
        for tag in info[workKey]['tagLabels']:
            if re.match(r'[RrＲ].?[1１][5５]', tag) is None:
                self.story.addToList('freeformtags', tag)
            else:
                rating = 'R15'

        # Rating
        self.story.setMetadata('rating', rating)

        # Genre
        self.story.setMetadata('genre', genres[info[workKey]['genre']])

        if info[workKey]['genre'] == 'FAN_FICTION':
            fandomKey = info[workKey]['fanFictionSource']['__ref']
            self.story.addToList('fandoms', info[fandomKey]['title'])

        # Ratings, Comments, Etc.
        self.story.setMetadata('reviews', info[workKey]['reviewCount'])
        self.story.setMetadata('points', info[workKey]['totalReviewPoint'])
        self.story.setMetadata('comments', info[workKey]['totalPublicEpisodeCommentCount'])
        self.story.setMetadata('views', info[workKey]['totalReadCount'])
        self.story.setMetadata('follows', info[workKey]['totalFollowers'])
        self.story.setMetadata('collections', len(info[workKey]['publicWorkCollections']))
        self.story.setMetadata('events', info[workKey]['totalWorkContestCount'] + info[workKey]['totalUserEventCount'])
        self.story.setMetadata('published', info[workKey]['hasPublication'])

        # visitorWorkFollowing
        # workReviewByVisitor

        # Chapters, Episodes

        # TOC nodes are in a list
        # each have a list of named episodes
        # each can have a named chapter
        # named chapters can be at depth 1 or 2
        # episodes might be empty (premium subscription)

        prependSectionTitles = self.getConfig('prepend_section_titles', 'firstepisode')

        numEpisodes = 0
        titles = []
        nestingLevel = 0
        newSection = False
        for tocNodeRef in info[workKey]['tableOfContents']:
            tocNode = info[tocNodeRef['__ref']]

            if tocNode['chapter'] is not None:
                chapter = info[tocNode['chapter']['__ref']]
                while chapter['level'] <= nestingLevel:
                    titles.pop()
                    nestingLevel -= 1
                titles.append(chapter['title'])
                nestingLevel = chapter['level']
                newSection = True
            else:
                titles = []
                nestingLevel = 0
                newSection = False

            for episodeRef in tocNode['episodeUnions']:
                if not episodeRef['__ref'].startswith('EmptyEpisode'):
                    numEpisodes += 1
                    episode = info[episodeRef['__ref']]
                    epUrl = 'https://kakuyomu.jp/works/' + self.storyId + '/episodes/' + episode['id']
                    epTitle = episode['title']

                    if ((len(titles) > 0) and
                        ((newSection and prependSectionTitles == 'firstepisode') or
                         prependSectionTitles == 'true')):
                        titles.append(epTitle)
                        # bracket with ZWSP to mark presence of section titles
                        epTitle = u'\u200b' + u'\u3000\u200b'.join(titles)
                        titles.pop()

                    self.add_chapter(epTitle, epUrl)
                newSection = False

        logger.debug("Story: <%s>", self.story)
        return

    def getChapterText(self, url):
        logger.debug('Getting chapter text from <%s>' % url)

        soup = self.make_soup(self.get_request(url))
        soup = soup.find('div', {'class':'widget-episodeBody js-episode-body'})
        if soup is None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
        soup.attrs = {'class':'episode-body'}

        return self.utf8FromSoup(url, soup)

