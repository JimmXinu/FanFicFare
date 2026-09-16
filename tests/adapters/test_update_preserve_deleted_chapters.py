"""Offline tests for preserved-deleted-chapter handling of the
incremental-update feature.

Everything is served by the shared staged adapters in update_harness so
no network fetching takes place.
"""
import io
import re
import zipfile

from bs4 import BeautifulSoup

from fanficfare.writers.writer_epub import EpubWriter

from tests.adapters.update_harness import (CH, OLD_URLS, SITE_CHAPTERS,
                                           FakeSiteAdapter, make_adapter,
                                           read_chapters, staged_config,
                                           staged_download, staged_update)


def test_preserved_deleted_written_chapters_have_required_keys(tmp_path):
    adapter = make_adapter(OLD_URLS, SITE_CHAPTERS, tmp_path)
    adapter.getStory()

    urls = [ch['url'] for ch in adapter.story.chapters]
    assert urls == OLD_URLS + ['http://example.com/story/ch/6']

    # Regression: every chapter dict must carry the keys that
    # Story.getChapters() reads unconditionally (the real-world run
    # crashed here with KeyError: 'new').
    for expected_key in ('new', 'number', 'index04', 'index',
                         'origtitle', 'toctitle'):
        for ch in adapter.story.chapters:
            assert expected_key in ch, (expected_key, ch['url'])


def test_update_counters_preserve_no_reupload(tmp_path):
    adapter = make_adapter(OLD_URLS, SITE_CHAPTERS, tmp_path)
    adapter.getStory()

    # No reupload-detection: the one new chapter is a pure addition.
    assert adapter.story.chapter_written_count == 6
    assert adapter.story.chapter_added_count == 1


def test_getChapters_with_preserved_deleted_chapters(tmp_path):
    adapter = make_adapter(OLD_URLS, SITE_CHAPTERS, tmp_path)
    adapter.getStory()

    chapters = adapter.story.getChapters(fortoc=True)
    assert [c['url'] for c in chapters] == \
        OLD_URLS + ['http://example.com/story/ch/6']


def test_write_epub_with_preserved_deleted_chapters(tmp_path):
    adapter = make_adapter(OLD_URLS, SITE_CHAPTERS, tmp_path)
    adapter.getStory()

    writer = EpubWriter(adapter.configuration, adapter)
    writer.writeStory(outstream=io.BytesIO())

    # Writing again (like an update run) must also succeed.
    writer = EpubWriter(adapter.configuration, adapter)
    writer.writeStory(outstream=io.BytesIO())


def test_preserved_deleted_chapter_images_preserved(tmp_path):
    # A preserved (deleted-from-site) chapter that contains an image.
    # The real update path hands us the old soup with img src already
    # reset to longdesc (the original URL) by epubutils.get_update_data,
    # plus adapter.oldimgs holding the old epub's image bytes keyed by
    # that longdesc URL -- so re-processing must find the image in the
    # store and NOT try to re-download it.
    img_url = 'https://img.example.com/pic.jpg'
    old_chapters = {'http://example.com/story/ch/1':
                    '<h3>Chapter One</h3><p>old body</p>'
                    '<img alt="pic" src="%s" longdesc="%s"/>'
                    % (img_url, img_url)}
    old_imgs = {img_url: ('OEBPS/images/pic.jpg', b'\xff\xd8fakejpeg')}

    adapter = make_adapter(list(old_chapters), SITE_CHAPTERS, tmp_path,
                           include_images='true', oldimgs=old_imgs)
    adapter.oldchaptersmap = {u: BeautifulSoup(html, 'html.parser')
                              for u, html in old_chapters.items()}
    adapter.getStory()

    out = io.BytesIO()
    writer = EpubWriter(adapter.configuration, adapter)
    writer.writeStory(outstream=out)

    zf = zipfile.ZipFile(io.BytesIO(out.getvalue()))
    chaps = [n for n in zf.namelist() if n.startswith('OEBPS/file')
             and n.endswith('.xhtml')]
    img_files = [n for n in zf.namelist() if n.startswith('OEBPS/images/')]
    assert img_files, 'preserved chapter image was not written to epub'
    assert any('<img' in zf.read(c).decode('utf-8', 'replace')
               for c in chaps), \
        'preserved chapter image tag was dropped from html'
    # src rewritten to the local stored file -- not a remote URL.
    preserved_body = zf.read(chaps[0]).decode('utf-8', 'replace')
    for c in chaps:
        body = zf.read(c).decode('utf-8', 'replace')
        if '<img' in body:
            preserved_body = body
            break
    assert 'src="images/' in preserved_body
    # longdesc keeps the original URL (by design), but src must point at
    # the local stored file -- not the remote URL.
    srcs = re.findall(r'src="([^"]+)"', preserved_body)
    assert srcs and all(s.startswith('images/') for s in srcs), \
        'img src must be rewritten to local stored file'


def test_preserved_deleted_chapter_keeps_title(tmp_path):
    # Regression: a preserved (deleted-from-site) chapter must keep its
    # real title.  epubutils.get_update_data strips the leading
    # fff_chapter_title h3 from the stored soup, so the preserve path
    # must fall back to the <meta name="chaptertitle"> in
    # oldchaptersdata instead of the URL slug.  Without the fix the
    # preserved "Chapter 2" would come back as the slug "2".
    config = staged_config(tmp_path)

    s0 = {1: '<p>chapter 1: a [[INIT]]</p>',
          2: '<p>chapter 2: b [[INIT]]</p>',
          3: '<p>chapter 3: c [[INIT]]</p>'}
    initial = staged_download(config, s0)

    def chapter_body_num(epub_bytes, num):
        zf = zipfile.ZipFile(io.BytesIO(epub_bytes))
        for n in sorted(n for n in zf.namelist()
                        if re.match(r'^OEBPS/file\d+\.xhtml$', n)):
            data = zf.read(n).decode('utf-8')
            if '<meta name="chapterurl" content="%s"' % (CH % num) in data:
                return data
        return None

    assert '<h3 class="fff_chapter_title">Chapter 2</h3>' in \
        chapter_body_num(initial, 2)

    # Second update: site deletes ch1 and ch2 (keeps ch3, adds ch4).
    s1 = {3: s0[3], 4: '<p>chapter 4: d [[NEW1]]</p>'}
    updated = staged_update(config, initial, s1)

    # ch2 is preserved from the deleted chapter and keeps its title.
    body2 = chapter_body_num(updated, 2)
    assert body2 is not None, 'deleted chapter was not preserved'
    assert '<h3 class="fff_chapter_title">Chapter 2</h3>' in body2, \
        'preserved chapter title was slug-ified'
    assert '<meta name="chaptertitle" content="Chapter 2" />' in body2


def test_staged_update_flow(tmp_path):
    """staged update flow testcase scenario:

    - initial download: site has chapters 1..3 ("a","b","c"), each carrying
      an [[INIT]] marker; epub downloaded and markers verified.
    - first update: site now has 4 chapters -- 1 and 2 unchanged, 3 updated
      ([[UPD1]] marker), 4 brand new ([[NEW1]]).  The working copy is the
      initial epub, unmodified.  Expected: ch1 and ch2 untouched, ch3 keeps
      its old [[INIT]] content (the site edit is not adopted), ch4 appended.
    - second update: site deleted chapters 1 and 2 and added 8 more (5..12,
      each with [[UPD2]]); ch3 kept; ch4 updated ([[UPD2]] marker).  The
      working copy is the first-update epub, unmodified.  Expected: ch1 and
      ch2 preserved despite deletion, ch3 still present with its old [[INIT]]
      content, ch4 still present with its previous [[NEW1]] content, ch5..12
      appended.

      Identity is checked by comparing content (markers), and with edit
      checks not yet implemented the previously-downloaded chapter is
      authoritative, so the site's updated content must not appear.
    """
    config = staged_config(tmp_path)

    s0 = {1: '<p>chapter 1: a [[INIT]]</p>',
          2: '<p>chapter 2: b [[INIT]]</p>',
          3: '<p>chapter 3: c [[INIT]]</p>'}
    initial = staged_download(config, s0)
    got = read_chapters(initial)
    assert [u for u, _ in got] == [CH % n for n in (1, 2, 3)]
    for n, (_, text) in zip((1, 2, 3), got):
        assert 'chapter %d' % n in text and '[[INIT]]' in text

    # first update: site gains ch4 (new) and ch3 is edited ([[UPD1]]).
    s1 = {1: s0[1],
          2: s0[2],
          3: '<p>chapter 3: c [[UPD1]]</p>',
          4: '<p>chapter 4: d [[NEW1]]</p>'}
    first = staged_update(config, initial, s1)
    got = read_chapters(first)
    assert [u for u, _ in got] == [CH % n for n in (1, 2, 3, 4)]
    for url, text in got:
        num = int(url.rsplit('/', 1)[1])
        if num in (1, 2):
            assert '[[INIT]]' in text and '[[UPD1]]' not in text, \
                'chapter %d was rewritten despite being unchanged' % num
        elif num == 3:
            assert '[[INIT]]' in text and '[[UPD1]]' not in text, \
                'ch3 adopted the site edit instead of keeping old content'
        else:
            assert 'chapter 4: d [[NEW1]]' in text

    # second update: site deletes ch1/ch2, keeps ch3, edits ch4 ([[UPD2]]),
    # and adds ch5..12 (each [[UPD2]]).  Working copy = first-update epub.
    s2 = {3: s1[3],
          4: '<p>chapter 4: d [[UPD2]]</p>'}
    s2.update({n: '<p>chapter %d: %s [[UPD2]]</p>' % (n, chr(96 + n))
               for n in range(5, 13)})
    second = staged_update(config, first, s2)
    got = read_chapters(second)
    assert [u for u, _ in got] == [CH % n for n in range(1, 13)]
    for url, text in got:
        num = int(url.rsplit('/', 1)[1])
        if num in (1, 2):
            assert '[[INIT]]' in text and '[[UPD2]]' not in text, \
                'deleted chapter %d was not preserved' % num
        elif num == 3:
            assert '[[INIT]]' in text and '[[UPD1]]' not in text, \
                'ch3 adopted the site edit instead of keeping old content'
        elif num == 4:
            assert '[[NEW1]]' in text and '[[UPD2]]' not in text, \
                'ch4 adopted the site edit instead of keeping old content'
        else:
            assert 'chapter %d:' % num in text and '[[UPD2]]' in text
def _site(*groups):
    """Build a site content dict from (nums, tag) groups.

    Chapter number n maps to url CH % n and body 'chapter n [[TAG]]'.
    Surviving chapters keep their tag between updates so their content
    is byte-identical and no edit-detection re-download is triggered.
    """
    content = {}
    for nums, tag in groups:
        for n in nums:
            content[n] = '<p>chapter %d [[%s]]</p>' % (n, tag)
    return content


def _chapter_snapshot(epub_bytes):
    """[(num, tag), ...] in epub reading order (== final written order).

    read_chapters() yields chapters in OEBPS/fileN.xhtml order, and the
    writer renumbers chapters before writing, so this gives the exact
    final chapter order of the epub -- enabling strict order assertions.
    """
    return [(int(url.rsplit('/', 1)[1]),
             re.search(r'\[\[([^\]]+)\]\]', text).group(1))
            for url, text in read_chapters(epub_bytes)]


def test_staged_update_flow_mixed_deletions_1(tmp_path):
    """scenario mixed-deletions-1: chapters deleted in the middle and at
    the end

    Ordering is verified explicitly: every step asserts the full ordered
    [num, tag] list of the resulting epub, not mere membership.

    - the site has 20 chapters (1..20)
    - initial download: all chapters in epub
    - the site deletes chapters (6..15)
    - (first) epub update: all preserved, all in correct order
    - the site adds 10 chapters (21..30)
    - (second) epub update: all 20 preserved, all 10 new, all in correct order
    - the site deleted chapters (19..28)
    - (third) epub update: all 30 preserved, all in correct order
    - the site adds 5 chapters (31..35)
    - epub update: all 30 preserved, all 5 new, all in correct order
    - the site deleted all but the first 5 chapters (only 1..5 remain on the site)
    - epub update: all 35 preserved, all in correct order
    """
    config = staged_config(tmp_path)

    initial = staged_download(config, _site((range(1, 21), 'INIT')))
    assert _chapter_snapshot(initial) == [(n, 'INIT') for n in range(1, 21)]

    # site deletes 6..15.
    u1 = staged_update(config, initial,
                       _site((range(1, 6), 'INIT'), (range(16, 21), 'INIT')))
    assert _chapter_snapshot(u1) == [(n, 'INIT') for n in range(1, 21)]

    # site adds 21..30.
    u2 = staged_update(config, u1,
                       _site((range(1, 6), 'INIT'), (range(16, 21), 'INIT'),
                             (range(21, 31), 'NEW1')))
    assert _chapter_snapshot(u2) == \
        [(n, 'INIT') for n in range(1, 21)] + \
        [(n, 'NEW1') for n in range(21, 31)]

    # site deletes 19..28.
    u3 = staged_update(config, u2,
                       _site((range(1, 6), 'INIT'), (range(16, 19), 'INIT'),
                             (range(29, 31), 'NEW1')))
    assert _chapter_snapshot(u3) == \
        [(n, 'INIT') for n in range(1, 21)] + \
        [(n, 'NEW1') for n in range(21, 31)]

    # site adds 31..35.
    u4 = staged_update(config, u3,
                       _site((range(1, 6), 'INIT'), (range(16, 19), 'INIT'),
                             (range(29, 31), 'NEW1'), (range(31, 36), 'NEW2')))
    assert _chapter_snapshot(u4) == \
        [(n, 'INIT') for n in range(1, 21)] + \
        [(n, 'NEW1') for n in range(21, 31)] + \
        [(n, 'NEW2') for n in range(31, 36)]

    # site deletes all but the first 5 chapters (1..5 remain).
    u5 = staged_update(config, u4, _site((range(1, 6), 'INIT')))
    assert _chapter_snapshot(u5) == \
        [(n, 'INIT') for n in range(1, 21)] + \
        [(n, 'NEW1') for n in range(21, 31)] + \
        [(n, 'NEW2') for n in range(31, 36)]


def test_staged_update_flow_mixed_deletions_2(tmp_path):
    """scenario mixed-deletions-2: same sequence of deletions, but fewer
    updates, same consistent preservation

    Multiple site changes are batched into each epub update.  Ordering
    verified via the full ordered [num, tag] list at each step.

    - the site has 20 chapters (1..20)
    - initial download: all chapters in epub
    - the site deletes chapters (6..15)
    - the site adds 10 chapters (21..30)
    - epub update: all 20 preserved, all 10 new, all in correct order
    - the site deleted chapters (19..28)
    - the site adds 5 chapters (31..35)
    - epub update: all 30 preserved, all 5 new, all in correct order
    - (we can skip the final update, already covered in mixed-deletions-1)
    """
    config = staged_config(tmp_path)

    initial = staged_download(config, _site((range(1, 21), 'INIT')))
    assert _chapter_snapshot(initial) == [(n, 'INIT') for n in range(1, 21)]

    # site deletes 6..15 and adds 21..30 before this update.
    u1 = staged_update(config, initial,
                       _site((range(1, 6), 'INIT'), (range(16, 21), 'INIT'),
                             (range(21, 31), 'NEW1')))
    assert _chapter_snapshot(u1) == \
        [(n, 'INIT') for n in range(1, 21)] + \
        [(n, 'NEW1') for n in range(21, 31)]

    # site deletes 19..28 and adds 31..35 before this update.
    u2 = staged_update(config, u1,
                       _site((range(1, 6), 'INIT'), (range(16, 19), 'INIT'),
                             (range(29, 31), 'NEW1'), (range(31, 36), 'NEW2')))
    assert _chapter_snapshot(u2) == \
        [(n, 'INIT') for n in range(1, 21)] + \
        [(n, 'NEW1') for n in range(21, 31)] + \
        [(n, 'NEW2') for n in range(31, 36)]


def test_staged_update_flow_mixed_deletions_3(tmp_path):
    """scenario mixed-deletions-3: different sequence, no re-upload detection

    Chapters are already missing from the site before the initial
    download, and later deletions are always offset by additions; no
    chapter is ever re-uploaded.  Ordering verified via the full ordered
    [num, tag] list at each step.

    - the site has 20 chapters (1..20)
    - the site deleted 1..3
    - initial download: chapters 4..20 are in epub
    - the site adds 10 chapters (21..30)
    - epub update: chapters 4..30 in epub, in order
    - the site deleted 10 (4..13) and adds 10 chapters (31..40)
    - epub update: chapters 4..40 in epub, in order
    - the site deleted 5 in the middle (21..25) and adds 3 chapters (41..43)
    - epub update: chapters 4..43 in epub, in order
    - the site deleted all chapters except numbers 16, 18, 26 and 42
    - epub update: chapters 4..43 in epub, in order
    """
    config = staged_config(tmp_path)

    initial = staged_download(config, _site((range(4, 21), 'INIT')))
    assert _chapter_snapshot(initial) == [(n, 'INIT') for n in range(4, 21)]

    # site adds 21..30.
    u1 = staged_update(config, initial,
                       _site((range(4, 21), 'INIT'), (range(21, 31), 'NEW1')))
    assert _chapter_snapshot(u1) == \
        [(n, 'INIT') for n in range(4, 21)] + \
        [(n, 'NEW1') for n in range(21, 31)]

    # site deletes 4..13 and adds 31..40.
    u2 = staged_update(config, u1,
                       _site((range(14, 21), 'INIT'), (range(21, 31), 'NEW1'),
                             (range(31, 41), 'NEW2')))
    assert _chapter_snapshot(u2) == \
        [(n, 'INIT') for n in range(4, 21)] + \
        [(n, 'NEW1') for n in range(21, 31)] + \
        [(n, 'NEW2') for n in range(31, 41)]

    # site deletes 21..25 and adds 41..43.
    u3 = staged_update(config, u2,
                       _site((range(14, 21), 'INIT'), (range(26, 31), 'NEW1'),
                             (range(31, 41), 'NEW2'), (range(41, 44), 'NEW3')))
    assert _chapter_snapshot(u3) == \
        [(n, 'INIT') for n in range(4, 21)] + \
        [(n, 'NEW1') for n in range(21, 31)] + \
        [(n, 'NEW2') for n in range(31, 41)] + \
        [(n, 'NEW3') for n in range(41, 44)]

    # site keeps only chapters 16, 18, 26 and 42.
    u4 = staged_update(config, u3,
                       _site(([16], 'INIT'), ([18], 'INIT'),
                             ([26], 'NEW1'), ([42], 'NEW2')))
    assert _chapter_snapshot(u4) == \
        [(n, 'INIT') for n in range(4, 21)] + \
        [(n, 'NEW1') for n in range(21, 31)] + \
        [(n, 'NEW2') for n in range(31, 41)] + \
        [(n, 'NEW3') for n in range(41, 44)]
