from __future__ import absolute_import
import logging
import re

# py2 vs py3 transition
from ..six.moves.urllib import parse as urlparse

from .base_adapter import BaseSiteAdapter


logger = logging.getLogger(__name__)


def getClass():
    return NovelFullSiteAdapter


class NovelFullSiteAdapter(BaseSiteAdapter):
    @staticmethod
    def getSiteDomain():
        return "novelfull.com"

    def getSiteURLPattern(self):
        return r"https?://%s/(index\.php/)?(?P<story_id>.+?)(/.*)?\.html?" % re.escape(self.getSiteDomain())

    def __init__(self, configuration, url):
        super(NovelFullSiteAdapter, self).__init__(configuration, url)

        story_id = re.match(self.getSiteURLPattern(), url).group('story_id')
        self.story.setMetadata('storyId', story_id)

        self._setURL("https://%s/%s.html" % (self.getSiteDomain(), story_id))

        self.story.setMetadata('siteabbrev', 'nvlfl')

    def extractChapterUrlsAndMetadata(self):
        data = self.get_request(self.url)

        soup = self.make_soup(data)

        self.story.setMetadata("title", soup.select_one("h3.title").text)

        for author in soup.find("h3", string="Author:").fetchNextSiblings(
            "a", href=re.compile("/author/")
        ):
            self.story.addToList("authorId", author.text)
            self.story.addToList(
                "authorUrl", urlparse.urljoin(self.url, author.attrs["href"])
            )
            self.story.addToList("author", author.text)

        status = soup.find("a", href=re.compile("status")).text

        if status == "Completed":
            self.story.setMetadata("status", "Completed")
        else:
            self.story.setMetadata("status", "In-Progress")

        # <input type="hidden" id="rateVal" value="8.6">
        rating = soup.find("input", id="rateVal")
        logger.debug(rating)
        if rating:
            self.story.setMetadata("averrating", rating['value'])

        cover_url = soup.find("div", class_="book").find("img").attrs["src"]
        self.setCoverImage(self.url, urlparse.urljoin(self.url, cover_url))

        self._crawl_chapters(self.url)

        self.setDescription(self.url, soup.select_one("div.desc-text"))

        for genre in soup.find(class_="info").find_all("a", href=re.compile("/genre/")):
            self.story.addToList("genre", genre.text)

    def _crawl_chapters(self, url):
        data = self.get_request(url)
        soup = self.make_soup(data)

        for a in soup.select("ul.list-chapter a"):
            self.add_chapter(a.attrs["title"], urlparse.urljoin(url, a.attrs["href"]))

        next_page = soup.select_one("#list-chapter .next a")

        if next_page:
            self._crawl_chapters(urlparse.urljoin(url, next_page.attrs["href"]))

    def getChapterText(self, url):
        data = self.get_request(url)
        soup = self.make_soup(data)

        content = soup.find(id="chapter-content")

        # Remove chapter header if present
        chapter_header = content.find(["p", "h3"], string=re.compile(r"Chapter \d+:"))

        if chapter_header:
            chapter_header.decompose()

        # Remove generic end-text added to all books

        for extra in content.find_all(attrs={"align": "left"}):
            extra.decompose()

        return self.utf8FromSoup(url, content)
