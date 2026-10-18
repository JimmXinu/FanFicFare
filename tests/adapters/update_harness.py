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
from fanficfare.epubutils import get_fff_chapter_data, get_update_data
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
                 oldimgs=None, olddata=None, mark_new='false'):
    configuration = Configuration(['example.com'], "EPUB", lightweight=True)
    configuration.read(os.path.join(
        os.path.dirname(__file__), '..', '..', 'fanficfare', 'defaults.ini'))
    personal = tmp_path / 'personal.ini'
    personal.write_text(
        '[defaults]\n'
        'update_preserve_deleted_chapters:true\n'
        'update_check_recent_chapters:0\n'
        'mark_new_chapters:%s\n'
        'include_images:%s\n' % (mark_new, include_images))
    configuration.read(str(personal))

    adapter = FakeSiteAdapter(
        configuration, STORY_URL)
    adapter.site_chapters = site_chapters
    adapter.oldchaptersmap = {}
    for old_url in old_urls:
        adapter.oldchaptersmap[old_url] = BeautifulSoup(
            '<h3>%s</h3><p>old body %s</p>' % (old_url, old_url),
            'html.parser')
    # olddata: optional {url: {...}} shaped like the datamaps a real
    # epubutils.get_update_data() read-back builds.  None means no chapter
    # data at all, which is what the read-back yields for an epub with
    # neither fff_chapter_data nor the per-field chaptertitle metas.
    adapter.oldchaptersdata = olddata
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


def staged_config(tmp_path, recent='0', mark_new='false', extra=''):
    """Staged-test Configuration.

    mark_new: value for mark_new_chapters ('false'/'true'/'latestonly').
        Off by default, which is why no staged test has ever produced a
        '(new)' mark before.
    extra: extra '[defaults]' lines appended verbatim, e.g. to install a
        custom chapter_start template.
    """
    configuration = Configuration(['example.com'], 'EPUB', lightweight=True)
    configuration.read(os.path.join(
        os.path.dirname(__file__), '..', '..', 'fanficfare', 'defaults.ini'))
    personal = tmp_path / 'personal.ini'
    personal.write_text(
        '[defaults]\n'
        'update_preserve_deleted_chapters:true\n'
        'update_check_recent_chapters:%s\n'
        'mark_new_chapters:%s\n'
        'include_images:false\n%s' % (recent, mark_new, extra))
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
     adapter.oldchaptersdata) = \
        get_update_data(io.BytesIO(working))[2:9]
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


def chapter_body_num(epub_bytes, num):
    """Raw xhtml of the chapter whose <meta name="chapterurl"> is CH % num,
    or None if that chapter is not in the epub.

    Matches by parsing, not by substring: unnew_chapters_epub()
    re-serialises the chapters it touches through html5lib, which reorders
    attributes, so '<meta name="chapterurl" content="..."' is not reliable
    once a book has been unnewed.
    """
    zf = zipfile.ZipFile(io.BytesIO(epub_bytes))
    for n in sorted(n for n in zf.namelist()
                    if re.match(r'^OEBPS/file\d+\.xhtml$', n)):
        data = zf.read(n).decode('utf-8')
        soup = BeautifulSoup(data, 'html.parser')
        tag = soup.find('meta', attrs={'name': 'chapterurl'})
        if tag is not None and tag['content'] == CH % num:
            return data
    return None


def chapter_meta(epub_bytes, num):
    """Parsed per-chapter metadata for chapter num, as read back out of a
    written epub: the per-field metas, the rendered chapter heading, and
    the fff_chapter_data json (empty dict for a pre-4.62.13 book).

    Assert against this rather than raw xhtml: unnew_chapters_epub()
    re-serialises the chapters it touches through html5lib, which reorders
    attributes and reformats whitespace, so byte comparisons are useless.
    """
    data = chapter_body_num(epub_bytes, num)
    assert data is not None, 'chapter %d not found in epub' % num
    soup = BeautifulSoup(data, 'html.parser')

    def meta_content(name):
        tag = soup.find('meta', attrs={'name': name})
        return tag['content'] if tag else None

    heading = soup.select_one('.fff_chapter_title')
    title_tag = soup.find('title')
    return {
        'url': meta_content('chapterurl'),
        'chaptertitle': meta_content('chaptertitle'),
        'origchapter': meta_content('chapterorigtitle'),
        'h3': heading.get_text() if heading is not None else None,
        'title': title_tag.get_text() if title_tag is not None else None,
        'data': get_fff_chapter_data(soup),
    }


CHAPTER_DATA_META_RE = re.compile(
    r'<meta name="fff_chapter_data".*?</meta>', re.S)


def strip_chapter_data_meta(epub_bytes):
    """epub_bytes with the fff_chapter_data meta tag removed from every
    chapter, modelling a book last written before 4.62.13.

    Everything else is left alone, so get_update_data() still finds the
    chapter urls through the per-field <meta name="chapterurl"> tag --
    exactly as it does for a real pre-4.62.13 epub.
    """
    src = zipfile.ZipFile(io.BytesIO(epub_bytes))
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename.endswith('.xhtml'):
                text = data.decode('utf-8')
                data = CHAPTER_DATA_META_RE.sub('', text).encode('utf-8')
            dst.writestr(info, data)
    return out.getvalue()
