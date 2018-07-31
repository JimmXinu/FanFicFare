# Software: eFiction
from __future__ import absolute_import
import re

from bs4.element import Tag

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib import parse as urlparse
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter, makeDate
from .. import exceptions


def getClass():
    return Voracity2EficComAdapter


# yields Tag _and_ NavigableString siblings from the given tag. The
# BeautifulSoup findNextSiblings() method for some reasons only returns either
# NavigableStrings _or_ Tag objects, not both.
def _yield_next_siblings(tag):
    sibling = tag.nextSibling
    while sibling:
        yield sibling
        sibling = sibling.nextSibling


class Voracity2EficComAdapter(BaseSiteAdapter):
    SITE_ABBREVIATION = 'voe'
    SITE_DOMAIN = 'voracity2.e-fic.com'

    BASE_URL = 'https://' + SITE_DOMAIN + '/'
    LOGIN_URL = BASE_URL + 'user.php?action=login'
    VIEW_STORY_URL_TEMPLATE = BASE_URL + 'viewstory.php?sid=%d'
    METADATA_URL_SUFFIX = '&index=1'
    AGE_CONSENT_URL_SUFFIX = '&ageconsent=ok&warning=4'

    DATETIME_FORMAT = '%m/%d/%Y'
    REQUIRED_SKIN = 'Simple Elegance'

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        query_data = urlparse.parse_qs(self.parsedUrl.query)
        story_id = query_data['sid'][0]

        self.story.setMetadata('storyId', story_id)
        self._setURL(self.VIEW_STORY_URL_TEMPLATE % int(story_id))
        self.story.setMetadata('siteabbrev', self.SITE_ABBREVIATION)

        self.is_logged_in = False

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

        self.is_logged_in = True

    def _customized_fetch_url(self, url, exception=None, parameters=None):
        if exception:
            try:
                data = self._fetchUrl(url, parameters)
            except HTTPError:
                raise exception(self.url)
        # Just let self._fetchUrl throw the exception, don't catch and
        # customize it.
        else:
            data = self._fetchUrl(url, parameters)

        return self.make_soup(data)

    @staticmethod
    def getSiteDomain():
        return Voracity2EficComAdapter.SITE_DOMAIN

    @classmethod
    def getSiteExampleURLs(cls):
        return cls.VIEW_STORY_URL_TEMPLATE % 1234

    def getSiteURLPattern(self):
        return re.escape(self.VIEW_STORY_URL_TEMPLATE[:-2]).replace('https','https?') + r'\d+$'

    def extractChapterUrlsAndMetadata(self):
        soup = self._customized_fetch_url(self.url + self.METADATA_URL_SUFFIX)

        # Check if the story is for "Registered Users Only", i.e. has adult
        # content. Based on the "is_adult" attributes either login or raise an
        # error.
        errortext_div = soup.find('div', {'class': 'errortext'})
        if errortext_div:
            error_text = ''.join(errortext_div(text=True)).strip()
            if error_text == 'Registered Users Only':
                if not (self.is_adult or self.getConfig('is_adult')):
                    raise exceptions.AdultCheckRequired(self.url)
                self._login()
            else:
                # This case usually occurs when the story doesn't exist, but
                # might potentially be something else, so just raise
                # FailedToDownload exception with the found error text.
                raise exceptions.FailedToDownload(error_text)

        url = ''.join([self.url, self.METADATA_URL_SUFFIX, self.AGE_CONSENT_URL_SUFFIX])
        soup = self._customized_fetch_url(url)

        # If logged in and the skin doesn't match the required skin throw an
        # error
        if self.is_logged_in:
            skin = soup.find('select', {'name': 'skin'}).find('option', selected=True)['value']
            if skin != self.REQUIRED_SKIN:
                raise exceptions.FailedToDownload('Required skin "%s" must be set in preferences' % self.REQUIRED_SKIN)

        pagetitle_div = soup.find('div', id='pagetitle')
        self.story.setMetadata('title', pagetitle_div.a.string)

        author_anchor = pagetitle_div.a.findNextSibling('a')
        url = urlparse.urljoin(self.BASE_URL, author_anchor['href'])
        components = urlparse.urlparse(url)
        query_data = urlparse.parse_qs(components.query)

        self.story.setMetadata('author', author_anchor.string)
        self.story.setMetadata('authorId', query_data['uid'][0])
        self.story.setMetadata('authorUrl', url)

        sort_div = soup.find('div', id='sort')
        self.story.setMetadata('reviews', sort_div('a')[1].string)

        for b_tag in soup.find('div', {'class': 'listbox'})('b'):
            key = b_tag.string.strip(' :')
            try:
                value = b_tag.nextSibling.string.strip()
            # This can happen with some fancy markup in the summary. Just
            # ignore this error and set value to None, the summary parsing
            # takes care of this
            except AttributeError:
                value = None

            if key == 'Summary':
                contents = []
                keep_summary_html = self.getConfig('keep_summary_html')

                for sibling in _yield_next_siblings(b_tag):
                    if isinstance(sibling, Tag):
                        # Encountered next label, break. This method is the
                        # safest and most reliable I could think of. Blame
                        # e-fiction sites that allow their users to include
                        # arbitrary markup into their summaries and the
                        # horrible HTML markup.
                        if sibling.name == 'b' and sibling.findPreviousSibling().name == 'br':
                            break

                        if keep_summary_html:
                            contents.append(self.utf8FromSoup(self.url, sibling))
                        else:
                            contents.append(''.join(sibling(text=True)))
                    else:
                        contents.append(sibling)

                # Remove the preceding break line tag and other crud
                contents.pop()
                contents.pop()
                self.story.setMetadata('description', ''.join(contents))

            elif key == 'Rating':
                self.story.setMetadata('rating', value)

            elif key == 'Category':
                for sibling in b_tag.findNextSiblings(['a', 'br']):
                    if sibling.name == 'br':
                        break
                    self.story.addToList('category', sibling.string)

            # Seems to be always "None" for some reason
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

            elif key == 'Chapter':
                self.story.setMetadata('numChapters', int(value))

            elif key == 'Completed':
                self.story.setMetadata('status', 'Completed' if value == 'Yes' else 'In-Progress')

            elif key == 'Words':
                self.story.setMetadata('numWords', value)

            elif key == 'Read':
                self.story.setMetadata('readings', value)

            elif key == 'Published':
                self.story.setMetadata('datePublished', makeDate(value, self.DATETIME_FORMAT))

            elif key == 'Updated':
                self.story.setMetadata('dateUpdated', makeDate(value, self.DATETIME_FORMAT))

        for b_tag in soup.find('div', id='output').findNextSiblings('b'):
            chapter_anchor = b_tag.a
            title = chapter_anchor.string
            url = urlparse.urljoin(self.BASE_URL, chapter_anchor['href'])
            self.add_chapter(title, url)

    def getChapterText(self, url):
        url += self.AGE_CONSENT_URL_SUFFIX
        soup = self._customized_fetch_url(url)
        return self.utf8FromSoup(url, soup.find('div', id='story'))
