#  -*- coding: utf-8 -*-

# Copyright 2021 FanFicFare team
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
import re
# py2 vs py3 transition
from ..six.moves.urllib.parse import urlparse

from .base_adapter import BaseSiteAdapter, makeDate
from fanficfare.htmlcleanup import stripHTML
from .. import exceptions as exceptions
from fanficfare.dateutils import parse_relative_date_string

logger = logging.getLogger(__name__)


def getClass():
    return DeviantArtComSiteAdapter


class DeviantArtComSiteAdapter(BaseSiteAdapter):
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev', 'dac')

        self.username = 'NoneGiven'
        self.password = ''
        self.is_adult = False

        match = re.match(self.getSiteURLPattern(), url)
        if not match:
            raise exceptions.InvalidStoryURL(url, self.getSiteDomain(), self.getSiteExampleURLs())

        story_id = match.group('id')
        author = match.group('author')
        self.story.setMetadata('author', author)
        self.story.setMetadata('authorId', author)
        self.story.setMetadata('authorUrl', 'https://www.deviantart.com/' + author)
        self._setURL(url)

    @staticmethod
    def getSiteDomain():
        return 'www.deviantart.com'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.deviantart.com']

    @classmethod
    def getProtocol(self):
        return 'https'

    @classmethod
    def getSiteExampleURLs(cls):
        return 'https://%s/<author>/art/<work-name>' % cls.getSiteDomain()

    def getSiteURLPattern(self):
        return r'https?://www\.deviantart\.com/(?P<author>[^/]+)/art/(?P<id>[^/]+)/?'

    def performLogin(self, url):
        if self.username and self.username != 'NoneGiven':
            username = self.username
        else:
            username = self.getConfig('username')

        # logger.debug("\n\nusername:(%s)\n\n"%username)
        if not username:
            logger.info("Login Required for URL %s" % url)
            raise exceptions.FailedToLogin(url,username)

        data = self.get_request_raw('https://www.deviantart.com/users/login', referer=url, usecache=False)
        data = self.decode_data(data)
        soup = self.make_soup(data)
        params = {
            'referer': 'https://www.deviantart.com/_sisu/do/signin', # soup.find('input', {'name': 'referer'})['value'],
            'referer_type': soup.find('input', {'name': 'referer_type'})['value'],
            'csrf_token': soup.find('input', {'name': 'csrf_token'})['value'],
            'challenge': soup.find('input', {'name': 'challenge'})['value'],
            'lu_token': soup.find('input', {'name': 'lu_token'})['value'],
            'remember': 'on',
            'username': username
        }

        loginUrl = 'https://' + self.getSiteDomain() + '/_sisu/do/step2'
        logger.debug('Will now login to deviantARt as (%s)' % username)

        result = self.post_request(loginUrl, params, usecache=False)
        soup = self.make_soup(result)
        if not soup.find('input', {'name': 'lu_token2'}):
            logger.info("Login Failed for URL %s (no lu_token2 found)" % url)
            raise exceptions.FailedToLogin(url,username)

        params = {
            'referer': 'https://www.deviantart.com/_sisu/do/signin', # soup.find('input', {'name': 'referer'})['value'],
            'referer_type': soup.find('input', {'name': 'referer_type'})['value'],
            'csrf_token': soup.find('input', {'name': 'csrf_token'})['value'],
            'challenge': soup.find('input', {'name': 'challenge'})['value'],
            'lu_token': soup.find('input', {'name': 'lu_token'})['value'],
            'lu_token2': soup.find('input', {'name': 'lu_token2'})['value'],
            'remember': 'on',
            'username': ''
        }

        if self.password:
            params['password'] = self.password
        else:
            params['password'] = self.getConfig('password')

        # logger.debug("\n\nparams['password']:(%s)\n\n"%params['password'])
        loginUrl = 'https://' + self.getSiteDomain() + '/_sisu/do/signin'
        logger.debug('Will now send password to deviantARt')

        result = self.post_request(loginUrl, params, usecache=False)

        if 'Log In | DeviantArt' in result:
            logger.error('Failed to login to deviantArt as %s' % username)
            raise exceptions.FailedToLogin('https://www.deviantart.com', username)
        else:
            return True

    def requiresLogin(self, data):
        return '</a> has limited the viewing of this artwork to members of the DeviantArt community only' in data

    def isLoggedIn(self, data):
        return '<form id="logout-form" action="https://www.deviantart.com/users/logout" method="POST">' in data

    def isWatchersOnly(self, data):
        return '>Watchers-Only Deviation<' in data

    def requiresMatureContentEnabled(self, data):
        return (
            '>This content is intended for mature audiences<' in data
            or '>This deviation is intended for mature audiences<' in data
            or '>This filter hides content that may be inappropriate for some viewers<' in data
            or '>May contain sensitive content<' in data
            or '>Log in to view<' in data
            or '>This deviation has been labeled as containing themes not suitable for all deviants.<' in data
        )

    def extractChapterUrlsAndMetadata(self):
        logger.debug('URL: %s', self.url)

        data = self.get_request(self.url)
        soup = self.make_soup(data)

        ## story can require login outright, or it can show up as
        ## watchers-only or mature-enabled without the same 'requires
        ## login' strings.
        if self.requiresLogin(data) or ( not self.isLoggedIn(data) and
                                         (self.isWatchersOnly(data) or
                                          self.requiresMatureContentEnabled(data)) ):
            if self.performLogin(self.url):
                data = self.get_request(self.url, usecache=False)
                soup = self.make_soup(data)

        ## Check watchers only and mature enabled again, separately,
        ## after login because they can still apply after login.
        if self.isWatchersOnly(data):
            raise exceptions.FailedToDownload(
                'Deviation is only available for watchers.' +
                'You must watch this author before you can download it.'
                )
        if self.requiresMatureContentEnabled(data):
            raise exceptions.FailedToDownload(
                'Deviation is set as mature, you must go into your account ' +
                'and enable showing of mature content.'
                )

        appurl = soup.select_one('meta[property="og:url"]')['content']
        if appurl:
            story_id = urlparse(appurl).path.lstrip('/')
        else:
            logger.debug("Looking for JS story id")
            ## after login, this is only found in a JS block.  Dunno why.
            ## F875A309-B0DB-860E-5079-790D0FBE5668
            match = re.match(r'\\"deviationUuid\\":\\"(?P<id>[A-Z0-9-]+)\\",',data)
            if match:
                story_id = match.group('id')
            else:
                raise exceptions.FailedToDownload('Failed to find Story ID.')
        self.story.setMetadata('storyId', story_id)

        title = soup.select_one('h1').get_text()
        self.story.setMetadata('title', stripHTML(title))

        ## dA has no concept of status
        # self.story.setMetadata('status', 'Completed')

        pubdate = soup.select_one('time').get_text()

        # Maybe do this better, but this works
        try:
            self.story.setMetadata('datePublished', makeDate(pubdate, '%b %d, %Y'))
        except:
            self.story.setMetadata('datePublished', parse_relative_date_string(pubdate))

        # do description here if appropriate

        story_tags = soup.select('a[href^="https://www.deviantart.com/tag"] span')
        if story_tags is not None:
            for tag in story_tags:
                self.story.addToList('genre', tag.get_text())

        self.add_chapter(title, self.url)

    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s', url)
        data = self.get_request(url)
        # logger.debug(data)
        soup = self.make_soup(data)

        # remove comments section to avoid false matches
        comments = soup.select_one('[data-hook=comments_thread]')
        if comments:
            comments.decompose()
        # previous search not always found in some stories.
        # <div id="comments"></div> inside the real containing
        # div seems more common
        commentsdiv = soup.select_one('div#comments')
        if commentsdiv:
            commentsdiv.parent.decompose()

        # three different 'content' tags to look for.
        # This is the current in Oct 2024
        content = soup.select_one('[data-editor-viewer="1"]')

        if content is None:
            # older story? I can't find any of this style in Oct2024
            content = soup.select_one('[data-id="rich-content-viewer"]')

        if content is None:
            # olderer story, but used by some older (2018) posts
            content = soup.select_one('.legacy-journal')

        if content is None:
            raise exceptions.FailedToDownload(
                'Could not find story text. Please open a bug with the URL %s' % self.url
                )

        return self.utf8FromSoup(url, content)
