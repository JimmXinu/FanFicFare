"""Shared helpers for the incremental-update offline tests.

Served by StagedSiteAdapter (a BaseSiteAdapter stub backed by in-memory
chapter lists/content) so no network fetching takes place.
"""
import io
import os
import re
import zipfile
from datetime import datetime

from bs4 import BeautifulSoup

from fanficfare.adapters.base_adapter import BaseSiteAdapter
from fanficfare.configurable import Configuration
from fanficfare.epubutils import get_update_data
from fanficfare.htmlcleanup import stripHTML
from fanficfare.writers.writer_epub import EpubWriter


class FakeSiteAdapter(BaseSiteAdapter):
    SITE = 'example.com'

    @classmethod
    def getSiteDomain(cls):
        return cls.SITE

    @classmethod
    def getConfigSection(cls):
        return cls.SITE

    def getConfigSections(cls):
        return [cls.SITE]

    def getSiteURLPattern(self):
        return '^http://' + self.SITE

    def normalize_chapterurl(self, url):
        return url

    def extractChapterUrlsAndMetadata(self):
        self.story.setMetadata('storyId', '12345')
        self.story.setMetadata('title', 'Test Story')
        self.story.setMetadata('author', 'Test Author')
        self.story.setMetadata('authorId', '12345')
        self.story.setMetadata('authorUrl', 'http://example.com/user/profile/12345')
        self.story.setMetadata('langcode', 'en')
        self.story.setMetadata('publisher', 'example.com')
        self.story.setMetadata('datePublished', datetime(2020, 1, 1))
        self.story.setMetadata('dateUpdated', datetime(2020, 1, 1))
        self.story.setMetadata('status', 'In-Progress')
        self.story.setMetadata('description', 'A test story.')
        self.story.setMetadata('category', 'General')
        self.story.setMetadata('rating', 'General Audiences')
        self.story.setMetadata('words', '100')
        for title, url in self.site_chapters:
            self.add_chapter(title, url)

    def getChapterTextNum(self, url, index):
        return '<p>new chapter content for %s</p>' % url


class StagedSiteAdapter(FakeSiteAdapter):
    def getChapterTextNum(self, url, index):
        return self.content[url]


def make_adapter(old_urls, site_chapters, tmp_path, include_images='false',
                 oldimgs=None):
    configuration = Configuration(['example.com'], "EPUB", lightweight=True)
    configuration.read(os.path.join(
        os.path.dirname(__file__), '..', '..', 'fanficfare', 'defaults.ini'))
    personal = tmp_path / 'personal.ini'
    personal.write_text(
        '[defaults]\n'
        'update_preserve_deleted_chapters:true\n'
        'include_images:%s\n' % (include_images))
    configuration.read(str(personal))

    adapter = FakeSiteAdapter(
        configuration, STORY_URL)
    adapter.site_chapters = site_chapters
    adapter.oldchaptersmap = {}
    for old_url in old_urls:
        adapter.oldchaptersmap[old_url] = BeautifulSoup(
            '<h3>%s</h3><p>old body %s</p>' % (old_url, old_url),
            'html.parser')
    adapter.oldchaptersdata = None
    adapter.oldimgs = oldimgs
    return adapter


OLD_URLS = ['http://example.com/story/ch/1',
            'http://example.com/story/ch/2',
            'http://example.com/story/ch/3',
            'http://example.com/story/ch/4',
            'http://example.com/story/ch/5']

# Site now has B, D (surviving) plus new F. A, C, E were deleted.
SITE_CHAPTERS = [('B title', 'http://example.com/story/ch/2'),
                 ('D title', 'http://example.com/story/ch/4'),
                 ('F title', 'http://example.com/story/ch/6')]


STORY_URL = 'http://example.com/story/12345-test-story'
CH = 'http://example.com/story/ch/%d'


def staged_config(tmp_path):
    configuration = Configuration(['example.com'], 'EPUB', lightweight=True)
    configuration.read(os.path.join(
        os.path.dirname(__file__), '..', '..', 'fanficfare', 'defaults.ini'))
    personal = tmp_path / 'personal.ini'
    personal.write_text(
        '[defaults]\n'
        'update_preserve_deleted_chapters:true\n'
        'include_images:false\n')
    configuration.read(str(personal))
    return configuration


def chapters_for(content):
    return [('Chapter %d' % n, CH % n) for n in sorted(content)]


def staged_download(configuration, content):
    adapter = StagedSiteAdapter(configuration, STORY_URL)
    adapter.site_chapters = chapters_for(content)
    adapter.content = {CH % n: html for n, html in content.items()}
    adapter.getStory()
    out = io.BytesIO()
    EpubWriter(adapter.configuration, adapter).writeStory(outstream=out)
    return out.getvalue()


def staged_update(configuration, working, content):
    adapter = StagedSiteAdapter(configuration, STORY_URL)
    adapter.site_chapters = chapters_for(content)
    adapter.content = {CH % n: html for n, html in content.items()}
    (adapter.oldchapters, adapter.oldimgs, adapter.oldcover,
     adapter.calibrebookmark, adapter.logfile, adapter.oldchaptersmap,
     adapter.oldchaptersdata) = get_update_data(io.BytesIO(working))[2:9]
    adapter.getStory()
    out = io.BytesIO()
    EpubWriter(adapter.configuration, adapter).writeStory(outstream=out)
    return out.getvalue()


def read_chapters(epub_bytes):
    zf = zipfile.ZipFile(io.BytesIO(epub_bytes))
    out = []
    for n in sorted(n for n in zf.namelist()
                    if re.match(r'^OEBPS/file\d+\.xhtml$', n)):
        soup = BeautifulSoup(zf.read(n).decode('utf-8'), 'html.parser')
        url = soup.find('meta', attrs={'name': 'chapterurl'})['content']
        out.append((url, stripHTML(soup.find('body'))))
    return out