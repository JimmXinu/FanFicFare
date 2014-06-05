import re
import urllib2
import urlparse

from .. import BeautifulSoup

from base_adapter import BaseSiteAdapter, makeDate
from .. import exceptions


def getClass():
    return Voracity2EficComAdapter


class Voracity2EficComAdapter(BaseSiteAdapter):
    SITE_DOMAIN = 'voracity2.e-fic.com'
    BASE_URL = 'http://' + SITE_DOMAIN
    LOGIN_URL = BASE_URL + '/user.php?action=login'
    VIEW_STORY_URL_TEMPLATE = BASE_URL + '/viewstory.php?sid=%d'
    METADATA_URL_SUFFIX = '&index=1'
    AGE_CONSENT_URL_SUFFIX = '&ageconsent=ok&warning=4'
    DATETIME_FORMAT = '%m/%d/%Y'

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        query_data = urlparse.parse_qs(self.parsedUrl.query)
        story_id = query_data['sid'][0]

        self.story.setMetadata('storyId', story_id)
        self._setURL(self.VIEW_STORY_URL_TEMPLATE % int(story_id))
        self.story.setMetadata('siteabbrev', 'voe')

    def _login(self):
        # Apparently self.password is only set when login fails, i.e.
        # the FailedToLogin exception is raised, so the adapter gets new
        # login data and tries again
        if self.password:
            password = self.password
            username = self.username
        else:
            username = self.getConfig('username')
            password = self.getConfig('password')

        parameters = {
            'penname': username,
            'password': password,
            'submit': 'Submit'}

        class CustomizedFailedToLogin(exceptions.FailedToLogin):
            def __init__(self, url, passwdonly=False):
                # Use username variable from outer scope
                exceptions.FailedToLogin.__init__(self, url, username, passwdonly)

        soup = self._customized_fetch_url(self.LOGIN_URL, CustomizedFailedToLogin, parameters)
        div = soup.find('div', id='useropts')
        if not div:
            raise CustomizedFailedToLogin(self.LOGIN_URL)

    def _customized_fetch_url(self, url, exception, parameters=None):
        try:
            data = self._fetchUrl(url, parameters)
        except urllib2.HTTPError:
            raise exception(self.url)

        return BeautifulSoup.BeautifulSoup(data)

    @staticmethod
    def getSiteDomain():
        return Voracity2EficComAdapter.SITE_DOMAIN

    @classmethod
    def getSiteExampleURLs(cls):
        return cls.VIEW_STORY_URL_TEMPLATE % 1234

    def getSiteURLPattern(self):
        return re.escape(self.VIEW_STORY_URL_TEMPLATE[:-2]) + r'\d+$'

    def extractChapterUrlsAndMetadata(self):
        soup = self._customized_fetch_url(self.url + self.METADATA_URL_SUFFIX, exceptions.StoryDoesNotExist)

        # Check if the story is for "Registered Users Only", i.e. has adult
        # content. Based on the "is_adult" attributes either login or raise an
        # error.
        div = soup.find('div', {'class': 'errortext'})
        if div and div.contents[0] == 'Registered Users Only':
            if not (self.is_adult or self.getConfig('is_adult')):
                raise exceptions.AdultCheckRequired(self.url)
            self._login()

        url = ''.join([self.url, self.METADATA_URL_SUFFIX, self.AGE_CONSENT_URL_SUFFIX])
        soup = self._customized_fetch_url(url, exceptions.StoryDoesNotExist)

        pagetitle_div = soup.find('div', id='pagetitle')
        self.story.setMetadata('title', pagetitle_div.a.string)

        author_anchor = pagetitle_div.a.findNextSibling('a')
        url = urlparse.urljoin(self.BASE_URL, author_anchor['href'])
        components = urlparse.urlparse(url)
        query_data = urlparse.parse_qs(components.query)

        self.story.setMetadata('author', author_anchor.string)
        self.story.setMetadata('authorId', query_data['uid'])
        self.story.setMetadata('authorUrl', url)

        metadata = {}
        for b_tag in soup.find('div', {'class': 'listbox'})('b'):
            key = b_tag.string.strip()[:-1]
            value = b_tag.nextSibling.string.strip()

            if key == 'Category':
                for sibling in b_tag.findNextSiblings(['a', 'br']):
                    if sibling.name == 'br':
                        break
                    self.story.addToList('category', sibling.string)

            elif key == 'Characters':
                for sibling in b_tag.findNextSiblings(['a', 'br']):
                    if sibling.name == 'br':
                        break
                    self.story.addToList('characters', sibling.string)

            elif key == 'Series':
                a = b_tag.findNextSibling('a')
                if not a:
                    continue
                self.story.setMetadata('series', a.string)
                self.story.setMetadata('seriesUrl', urlparse.urljoin(self.BASE_URL, a['href']))

            else:
                metadata[key] = value

        self.story.setMetadata('description', metadata['Summary'])
        self.story.setMetadata('rating', metadata['Rating'])
        self.story.setMetadata('numChapters', int(metadata['Chapter']))
        self.story.setMetadata('status', 'Completed' if metadata['Completed'] == 'Yes' else 'In-Progress')
        self.story.setMetadata('numWords', metadata['Words'])
        self.story.setMetadata('datePublished', makeDate(metadata['Published'], self.DATETIME_FORMAT))
        self.story.setMetadata('dateUpdated', makeDate(metadata['Updated'], self.DATETIME_FORMAT))

        for b_tag in soup.find('div', id='output').findNextSiblings('b'):
            chapter_anchor = b_tag.a
            title = chapter_anchor.string
            url = urlparse.urljoin(self.BASE_URL, chapter_anchor['href'])
            self.chapterUrls.append((title, url))

    def getChapterText(self, url):
        url += self.AGE_CONSENT_URL_SUFFIX
        soup = self._customized_fetch_url(url, exceptions.FailedToDownload)
        return self.utf8FromSoup(url, soup.find('div', id='story'))
