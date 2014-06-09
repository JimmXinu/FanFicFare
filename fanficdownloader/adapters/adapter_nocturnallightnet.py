import re
import urllib2
import urlparse

from .. import BeautifulSoup

from base_adapter import BaseSiteAdapter, makeDate
from .. import exceptions


def getClass():
    return NocturnalLightNetAdapter


# yields Tag _and_ NavigableString siblings from the given tag. The
# BeautifulSoup findNextSiblings() method for some reasons only returns either
# NavigableStrings _or_ Tag objects, not both.
def _yield_next_siblings(tag):
    sibling = tag.nextSibling
    while sibling:
        yield sibling
        sibling = sibling.nextSibling


class NocturnalLightNetAdapter(BaseSiteAdapter):
    SITE_ABBREVIATION = 'nln'
    SITE_DOMAIN = 'nocturnal-light.net'
    BASE_URL = 'http://' + SITE_DOMAIN + '/fanfiction/'
    STORY_URL_TEMPLATE = BASE_URL + 'story/%s'
    AUTHORS_URL_TEMPLATE = BASE_URL + 'authors/%s'

    DATETIME_FORMAT = '%m-%d-%y'

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        url_tokens = self.parsedUrl.path.split('/')
        story_id = url_tokens[url_tokens.index('story') + 1]

        self.story.setMetadata('storyId', story_id)
        self._setURL(self.STORY_URL_TEMPLATE % story_id)
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
        return NocturnalLightNetAdapter.SITE_DOMAIN

    @classmethod
    def getSiteExampleURLs(cls):
        return cls.STORY_URL_TEMPLATE % 1234

    def getSiteURLPattern(self):
        return re.escape(self.STORY_URL_TEMPLATE[:-2]) + r'\d+.*$'

    def extractChapterUrlsAndMetadata(self):
        soup = self._customized_fetch_url(self.url)

        # Since no 404 error code we have to raise the exception ourselves.
        # A title that is just 'by' indicates that there is no author name
        # and no story title available.
        if soup.title.string.strip() == 'by':
            raise exceptions.StoryDoesNotExist(self.url)

        # "storycontent" is found in a single-chapter story
        author_anchor = soup.find('div', id=lambda id: id in ('main', 'storycontent')).h1.a
        self.story.setMetadata('author', author_anchor.string)

        url_tokens = author_anchor['href'].split('/')
        author_id = url_tokens[url_tokens.index('authors')+1]
        self.story.setMetadata('authorId', author_id)
        self.story.setMetadata('authorUrl', self.AUTHORS_URL_TEMPLATE % author_id)

        chapter_anchors = soup('a', href=lambda href: href and href.startswith('/fanfiction/story/'))
        for chapter_anchor in chapter_anchors:
            url = urlparse.urljoin(self.BASE_URL, chapter_anchor['href'])
            self.chapterUrls.append((chapter_anchor.string, url))

        author_url = urlparse.urljoin(self.BASE_URL, author_anchor['href'])
        soup = self._customized_fetch_url(author_url)
        story_id = self.story.getMetadata('storyId')
        for listbox in soup('div', {'class': 'listbox'}):
            url_tokens = listbox.a['href'].split('/')
            # Found the div containing the story's metadata; break the loop and
            # parse the element
            if story_id == url_tokens[url_tokens.index('story')+1]:
                break
        else:
            raise exceptions.FailedToDownload(self.url)

        title = listbox.a.string
        self.story.setMetadata('title', title)

        # No chapter anchors found in the original story URL, so the story has
        # only a single chapter.
        if not chapter_anchors:
            self.chapterUrls.append((title, self.url))

        for b_tag in listbox('b'):
            key = b_tag.string.strip(':')
            try:
                value = b_tag.nextSibling.string.replace('&bull;', '').strip(': ')
            # This can happen with some fancy markup in the summary. Just
            # ignore this error and set value to None, the summary parsing
            # takes care of this
            except AttributeError:
                value = None

            if key == 'Summary':
                contents = []
                keep_summary_html = self.getConfig('keep_summary_html')

                for sibling in _yield_next_siblings(b_tag):
                    if isinstance(sibling, BeautifulSoup.Tag):
                        if sibling.name == 'b' and sibling.findPreviousSibling().name == 'br':
                            break

                        if keep_summary_html:
                            contents.append(self.utf8FromSoup(author_url, sibling))
                        else:
                            contents.append(''.join(sibling(text=True)))
                    else:
                        contents.append(sibling)

                # Pop last break line tag
                contents.pop()
                self.story.setMetadata('description', ''.join(contents))

            elif key == 'Category':
                for sibling in b_tag.findNextSiblings(['a', 'b']):
                    if sibling.name == 'b':
                        break

                    self.story.addToList('category', sibling.string)

            elif key == 'Rating':
                self.story.setMetadata('rating', value)

            elif key == 'Chapters':
                self.story.setMetadata('numChapters', int(value))

                # Also parse reviews number which lies right after the chapters
                # section
                reviews_anchor = b_tag.findNextSibling('a')
                reviews = reviews_anchor.string.split(' ')[1].strip('()')
                self.story.setMetadata('reviews', reviews)

            elif key == 'Completed':
                self.story.setMetadata('status', 'Completed' if value == 'Yes' else 'In-Progress')

            elif key == 'Date Added':
                self.story.setMetadata('datePublished', makeDate(value, self.DATETIME_FORMAT))

            elif key == 'Last Updated':
                self.story.setMetadata('dateUpdated', makeDate(value, self.DATETIME_FORMAT))

            elif key == 'Read':
                self.story.setMetadata('readings', value.split()[0])

        if self.story.getMetadata('rating') == 'NC-17' and not (self.is_adult or self.getConfig('is_adult')):
            raise exceptions.AdultCheckRequired(self.url)

    def getChapterText(self, url):
        soup = self._customized_fetch_url(url)
        return self.utf8FromSoup(url, soup.find('div', id='storytext'))
