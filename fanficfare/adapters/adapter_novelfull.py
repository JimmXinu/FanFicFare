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
        return r"https?://%s/(?P<name>.+).html?" % re.escape(self.getSiteDomain())

    def extractChapterUrlsAndMetadata(self):
        data = self.get_request(self.url)

        soup = self.make_soup(data)

        self.story.setMetadata("title", soup.select_one("h3.title").text)
        self.story.setMetadata(
            "author",
            " ".join(
                s.text for s in soup.find("h3", text="Author:").fetchNextSiblings()
            ),
        )
        self.story.setMetadata("authorId", self.story.getMetadata("author"))

        status = soup.find("a", href=re.compile("status")).text

        if status == "Completed":
            self.story.setMetadata("status", "Completed")

        cover_url = soup.find("div", class_="book").find("img").attrs["src"]
        self.setCoverImage(self.url, urlparse.urljoin(self.url, cover_url))

        self._crawl_chapters(self.url)

        self.setDescription(
            self.url, soup.select_one("div.desc-text").get_text(separator="\n")
        )

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
        chapter_header = content.find(text=re.compile(r"Chapter \d+:"))

        if chapter_header:
            chapter_header.decompose()

        # Remove generic end-text added to all books

        for extra in content.find_all(attrs={"align": "left"}):
            extra.decompose()

        return self.utf8FromSoup(url, content)
