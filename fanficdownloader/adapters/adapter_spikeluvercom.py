import re
import urllib2
import urlparse

from .. import BeautifulSoup

from base_adapter import BaseSiteAdapter, makeDate
from .. import exceptions


def getClass():
    return SpikeluverComAdapter


# yields Tag _and_ NavigableString siblings from the given tag. The
# BeautifulSoup findNextSiblings() method for some reasons only returns either
# NavigableStrings _or_ Tag objects, not both.
def _yield_next_siblings(tag):
    sibling = tag.nextSibling
    while sibling:
        yield sibling
        sibling = sibling.nextSibling


class SpikeluverComAdapter(BaseSiteAdapter):
    SITE_ABBREVIATION = 'slc'
    SITE_DOMAIN = 'spikeluver.com'

    BASE_URL = 'http://' + SITE_DOMAIN + '/SpuffyRealm/'
    LOGIN_URL = BASE_URL + 'user.php?action=login'
    VIEW_STORY_URL_TEMPLATE = BASE_URL + 'viewstory.php?sid=%d'
    METADATA_URL_SUFFIX = '&index=1'
    AGE_CONSENT_URL_SUFFIX = '&ageconsent=ok&warning=5'

    DATETIME_FORMAT = '%m/%d/%Y'
    STORY_DOES_NOT_EXIST_ERROR_TEXT = 'That story does not exist on this archive.  You may search for it or return to the home page.'

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        query_data = urlparse.parse_qs(self.parsedUrl.query)
        story_id = query_data['sid'][0]

        self.story.setMetadata('storyId', story_id)
        self._setURL(self.VIEW_STORY_URL_TEMPLATE % int(story_id))
        self.story.setMetadata('siteabbrev', self.SITE_ABBREVIATION)

    def _customized_fetch_url(self, url, exception=None, parameters=None):
        if exception:
            try:
                data = self._fetchUrl(url, parameters)
            except urllib2.HTTPError:
                raise exception(self.url)
        # Just let self._fetchUrl throw the exception, don't catch and
        # customize it.
        else:
            data = self._fetchUrl(url, parameters)

        return BeautifulSoup.BeautifulSoup(data)

    @staticmethod
    def getSiteDomain():
        return SpikeluverComAdapter.SITE_DOMAIN

    @classmethod
    def getSiteExampleURLs(cls):
        return cls.VIEW_STORY_URL_TEMPLATE % 1234

    def getSiteURLPattern(self):
        return re.escape(self.VIEW_STORY_URL_TEMPLATE[:-2]) + r'\d+$'

    def extractChapterUrlsAndMetadata(self):
        soup = self._customized_fetch_url(self.url + self.METADATA_URL_SUFFIX)

        errortext_div = soup.find('div', {'class': 'errortext'})
        if errortext_div:
            error_text = ''.join(errortext_div(text=True)).strip()
            if error_text == self.STORY_DOES_NOT_EXIST_ERROR_TEXT:
                raise exceptions.StoryDoesNotExist(self.url)

        # No additional login is required, just check for adult
        pagetitle_div = soup.find('div', id='pagetitle')
        if pagetitle_div.a['href'].startswith('javascript:'):
            if not(self.is_adult or self.getConfig('is_adult')):
                raise exceptions.AdultCheckRequired(self.url)

        url = ''.join([self.url, self.METADATA_URL_SUFFIX, self.AGE_CONSENT_URL_SUFFIX])
        soup = self._customized_fetch_url(url)

        pagetitle_div = soup.find('div', id='pagetitle')
        self.story.setMetadata('title', pagetitle_div.a.string.strip())

        author_anchor = pagetitle_div.a.findNextSibling('a')
        url = urlparse.urljoin(self.BASE_URL, author_anchor['href'])
        components = urlparse.urlparse(url)
        query_data = urlparse.parse_qs(components.query)

        self.story.setMetadata('author', author_anchor.string.strip())
        self.story.setMetadata('authorId', query_data['uid'])
        self.story.setMetadata('authorUrl', url)

        sort_div = soup.find('div', id='sort')
        self.story.setMetadata('reviews', sort_div('a')[1].string.strip())

        listbox_tag = soup.find('div', {'class': 'listbox'})
        for span_tag in listbox_tag('span'):
            key = span_tag.string.strip(' :')
            try:
                value = span_tag.nextSibling.string.strip()
            # This can happen with some fancy markup in the summary. Just
            # ignore this error and set value to None, the summary parsing
            # takes care of this
            except AttributeError:
                value = None

            if key == 'Summary':
                contents = []
                keep_summary_html = self.getConfig('keep_summary_html')

                for sibling in _yield_next_siblings(span_tag):
                    if isinstance(sibling, BeautifulSoup.Tag):
                        # Encountered next label, break. Not as bad as other
                        # e-fiction sites, let's hope this is enough for proper
                        # parsing.
                        if sibling.name == 'span' and sibling.get('class', None) == 'label':
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

            elif key == 'Rated':
                self.story.setMetadata('rating', value)

            elif key == 'Categories':
                for sibling in span_tag.findNextSiblings(['a', 'br']):
                    if sibling.name == 'br':
                        break

                    self.story.addToList('category', sibling.string.strip())

            # Seems to be always "None" for some reason
            elif key == 'Characters':
                for sibling in span_tag.findNextSiblings(['a', 'br']):
                    if sibling.name == 'br':
                        break
                    self.story.addToList('characters', sibling.string.strip())

            elif key == 'Genres':
                for sibling in span_tag.findNextSiblings(['a', 'br']):
                    if sibling.name == 'br':
                        break

                    self.story.addToList('genre', sibling.string.strip())

            elif key == 'Warnings':
                for sibling in span_tag.findNextSiblings(['a', 'br']):
                    if sibling.name == 'br':
                        break
                    self.story.addToList('warnings', sibling.string.strip())

            # Challenges

            elif key == 'Series':
                a = span_tag.findNextSibling('a')
                if not a:
                    continue
                self.story.setMetadata('series', a.string.strip())
                self.story.setMetadata('seriesUrl', urlparse.urljoin(self.BASE_URL, a['href']))

            elif key == 'Chapters':
                self.story.setMetadata('numChapters', int(value))

            elif key == 'Completed':
                self.story.setMetadata('status', 'Completed' if value == 'Yes' else 'In-Progress')

            elif key == 'Word count':
                self.story.setMetadata('numWords', value)

            elif key == 'Published':
                self.story.setMetadata('datePublished', makeDate(value, self.DATETIME_FORMAT))

            elif key == 'Updated':
                self.story.setMetadata('dateUpdated', makeDate(value, self.DATETIME_FORMAT))

        for p_tag in listbox_tag.findNextSiblings('p'):
            chapter_anchor = p_tag.find('a')
            title = chapter_anchor.string.strip()
            url = urlparse.urljoin(self.BASE_URL, chapter_anchor['href'])
            self.chapterUrls.append((title, url))

    def getChapterText(self, url):
        url += self.AGE_CONSENT_URL_SUFFIX
        soup = self._customized_fetch_url(url)
        return self.utf8FromSoup(url, soup.find('div', id='story'))
