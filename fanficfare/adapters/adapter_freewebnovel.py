from __future__ import absolute_import
import logging
import re

# py2 vs py3 transition
from ..six.moves.urllib import parse as urlparse

from .base_adapter import BaseSiteAdapter


logger = logging.getLogger(__name__)


def getClass():
    return FreeWebNovelSiteAdapter


class FreeWebNovelSiteAdapter(BaseSiteAdapter):
    @staticmethod
    def getSiteDomain():
        return "freewebnovel.com"

    def getSiteURLPattern(self):
        # https://freewebnovel.com/novel/the-bee-dungeon
        return r"https?://%s/novel/(?P<story_id>[^/]+)" % re.escape(self.getSiteDomain())


    @classmethod
    def getSiteExampleURLs(cls):
        return "https://freewebnovel.com/novel/a-story-name"


    def __init__(self, configuration, url):
        super(FreeWebNovelSiteAdapter, self).__init__(configuration, url)

        story_id = re.match(self.getSiteURLPattern(), url).group('story_id')
        self.story.setMetadata('storyId', story_id)

        self._setURL("https://%s/novel/%s" % (self.getSiteDomain(), story_id))

        self.story.setMetadata('siteabbrev', 'freweb')

    def extractChapterUrlsAndMetadata(self):
        data = self.get_request(self.url)

        soup = self.make_soup(data)

        self.story.setMetadata("title", soup.select_one("h3.tit").text)



        #loo = soup.select('span[title="Author"] + div > a', href=re.compile("/author/"))
        #print("==============Author   44  ======================")
        #print(loo)

        for author in soup.select('span[title="Author"] + div > a', href=re.compile("/author/")

        ):
            #print(author.text)
            self.story.addToList("authorId", author.text)
            self.story.addToList(
                "authorUrl", urlparse.urljoin(self.url, author.attrs["href"])
            )
            self.story.addToList("author", author.text)


        #status = soup.find("a", href=re.compile("status")).text
        #span_tag =  soup.find("span" , title="Status")
        #print (span_tag)
        #print(span_tag.next_element)
        #print(span_tag.next_sibling)
        #print(soup.select('span[title="Status"]'))
        #print(soup.select('span[title="Status"] + div'))
        #print(soup.select('span[title="Status"] + div > a'))
        #print (soup.select_one('span[title="Status"] + div a'))
        status = soup.select_one('span[title="Status"] + div a').text

        #print (status)
        if status == "Completed":
            self.story.setMetadata("status", "Completed")
        else:
            self.story.setMetadata("status", "In-Progress")

        # <input type="hidden" id="rateVal" value="8.6">
        rating = soup.find("input", id="rateVal")
        logger.debug(rating)
        if rating:
            self.story.setMetadata("averrating", rating['value'])

        cover_url = soup.find("div", class_="pic").find("img").attrs["src"]
        self.setCoverImage(self.url, urlparse.urljoin(self.url, cover_url))

        self._crawl_chapters(self.url)

        #print (soup.select_one("h4.abstract + div.txt"))
        self.setDescription(self.url, soup.select_one("h4.abstract + .txt"))

        for genre in soup.find(class_="m-imgtxt").find_all("a", href=re.compile("/genre/")):
            self.story.addToList("genre", genre.text)

        #print(self)
        #print ("-----------------")
        #print(self.story)

    def _crawl_chapters(self, url):
        data = self.get_request(url)
        soup = self.make_soup(data)

        for a in soup.select('div[class="m-newest2"]  ul.ul-list5 a'):
            self.add_chapter(a.attrs["title"], urlparse.urljoin(url, a.attrs["href"]))

        next_page = soup.select_one("#ul-list5 .next a")

        if next_page:
            self._crawl_chapters(urlparse.urljoin(url, next_page.attrs["href"]))

    def getChapterText(self, url):
        data = self.get_request(url)
        soup = self.make_soup(data)

        content = soup.find(id="article")

        # Remove chapter header if present
        chapter_header = content.find(["p", "h4"], string=re.compile(r"Chapter \d+:"))

        if chapter_header:
            chapter_header.decompose()

        # Remove generic end-text added to all books

        for extra in content.find_all(attrs={"align": "left"}):
            extra.decompose()

        return self.utf8FromSoup(url, content)
