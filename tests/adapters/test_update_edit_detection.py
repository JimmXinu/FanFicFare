"""Offline tests for the update-check (edit detection) half of the
incremental-update feature: re-downloading recently-got chapters to
detect author edits, restoring locally-edited chapters, and the
recheck_recent_chapters() gating used by cli/jobs/fff_plugin.

Everything is served by the shared staged adapters in update_harness so
no network fetching takes place.
"""
import io
import re
import zipfile

import pytest

from tests.adapters.update_harness import (CH, STORY_URL,
                                           StagedSiteAdapter, read_chapters,
                                           staged_config, staged_download,
                                           staged_update)


def manipulate_chapter2_text(epub_bytes):
    zf = zipfile.ZipFile(io.BytesIO(epub_bytes))
    names = zf.namelist()
    ch2 = sorted(n for n in names
                 if re.match(r'^OEBPS/file\d+\.xhtml$', n))[1]
    data = zf.read(ch2).decode('utf-8')
    new_body = '<p>chapter 2: b [[LOCAL-EDIT]]</p>'
    data = data.replace('<p>chapter 2: b [[INIT]]</p>', new_body)
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zo:
        for n in names:
            zo.writestr(n, data if n == ch2 else zf.read(n))
    return out.getvalue()


def test_recheck_recent_chapters_predicate(tmp_path):
    # No recent-window set: edit detection is off and the caller gating
    # (cli.py / jobs.py / fff_plugin.py) must not treat the update as
    # needing re-downloads.
    config = staged_config(tmp_path, recent='0')
    assert StagedSiteAdapter(config, STORY_URL).recheck_recent_chapters() is False

    # A recent-chapters window activates edit detection...
    config = staged_config(tmp_path, recent='5')
    assert StagedSiteAdapter(config, STORY_URL).recheck_recent_chapters() is True


def test_staged_update_flow(tmp_path):
    """staged update flow testcase scenario:

    - initial download: site has chapters 1..3 ("a","b","c"), each carrying
      an [[INIT]] marker; epub downloaded and markers verified.
    - first update: site now has 4 chapters -- 1 and 2 unchanged, 3 updated
      ([[UPD1]] marker), 4 brand new ([[NEW1]]).  The working copy is the
      initial epub with chapter 2's text manipulated locally.  Expected:
      ch1 untouched (same content), ch2 restored to the initial version,
      ch3 replaced with the [[UPD1]] content, ch4 appended.
    - second update: site deleted chapters 1 and 2 and added 8 more (5..12,
      each with [[UPD2]]); ch3 kept; ch4 updated ([[UPD2]] marker).  The
      working copy is the first-update epub, unmodified.  Expected: ch1 and
      ch2 preserved despite deletion, ch3 still present, ch4 re-written with
      the [[UPD2]] marker, ch5..12 appended.

      ch4's re-check in the second update is the epub-window case: the
      edit-check window is the last N chapters of the OLD EPUB in reading
      order (not the last N site chapters), so ch4 -- site index 1 with a
      10-chapter site -- is still re-checked because it is the last chapter
      of the 4-chapter epub.
    """
    # Explicit recent window (staged_config defaults to recent='0' to
    # match defaults.ini): this combined test needs edit-checks active.
    config = staged_config(tmp_path, recent='5')

    # initial download: 3 chapters, each marked [[INIT]].
    s0 = {1: '<p>chapter 1: a [[INIT]]</p>',
          2: '<p>chapter 2: b [[INIT]]</p>',
          3: '<p>chapter 3: c [[INIT]]</p>'}
    initial = staged_download(config, s0)
    got = read_chapters(initial)
    assert [u for u, _ in got] == [CH % n for n in (1, 2, 3)]
    for n, (_, text) in zip((1, 2, 3), got):
        assert 'chapter %d' % n in text and '[[INIT]]' in text

    # first update: site gains ch4 (new) and ch3 is edited ([[UPD1]]).
    # Working copy = initial epub with ch2's text manipulated.
    s1 = {1: s0[1],
          2: s0[2],
          3: '<p>chapter 3: c [[UPD1]]</p>',
          4: '<p>chapter 4: d [[NEW1]]</p>'}
    working = manipulate_chapter2_text(initial)
    first = staged_update(config, working, s1)
    got = read_chapters(first)
    assert [u for u, _ in got] == [CH % n for n in (1, 2, 3, 4)]

    # ch1 untouched: same content as the original.
    u1, t1 = got[0]
    assert u1 == CH % 1
    assert 'chapter 1: a [[INIT]]' in t1

    # ch2 locally edited -> restored to the initial version by the update.
    u2, t2 = got[1]
    assert u2 == CH % 2
    assert 'chapter 2: b [[INIT]]' in t2
    assert 'LOCAL-EDIT' not in t2

    # ch3 replaced with the [[UPD1]] content.
    u3, t3 = got[2]
    assert u3 == CH % 3
    assert 'chapter 3: c [[UPD1]]' in t3

    # ch4 appended as a brand new chapter.
    u4, t4 = got[3]
    assert u4 == CH % 4
    assert 'chapter 4: d [[NEW1]]' in t4

    # second update: site deletes ch1/ch2, edits ch4 ([[UPD2]]), adds
    # ch5..12 (each [[UPD2]]).  Working copy = first-update epub, no
    # manipulation.
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
            # preserved despite being deleted on the site.
            assert '[[INIT]]' in text
        elif num == 3:
            # still present, unchanged from the previous stage.
            assert '[[UPD1]]' in text
        elif num == 4:
            # re-checked via the epub-based recent window (site index 1
            # of 10, but last chapter of the 4-chapter epub) -> UPD2.
            assert '[[UPD2]]' in text
        else:
            # brand-new chapters 5..12.
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


def test_staged_update_flow_update_versus_deletions(tmp_path):
    """scenario update-versus-deletions: edit-check window meets deletions

    The recent-chapters window is over the OLD epub, so a chapter can be
    scheduled for re-check and then vanish from the site before the
    update runs.  Such a chapter must be preserved with its old content,
    not re-downloaded (the loop only re-checks chapters present on the
    site).  Ordering is checked on the full [num, tag] list at each step.

    - the site has 20 chapters (1..20)
    - initial download: all chapters in epub
    - the site deletes chapters (6..15)
    - the site updates chapters (16,18,20)
    - the site adds 10 chapters (21..30)
    - epub update: all preserved, all in correct order, 18 and 20 have the
      new content, 16 is out of check range and retains original content
    - the site updates chapters (28,29)
    - the site deleted chapters (19..28)
    - epub update: all preserved, all in correct order, 29 has the new
      content, 28 is preserved with old content
    """
    config = staged_config(tmp_path, recent='3')

    initial = staged_download(config, _site((range(1, 21), 'INIT')))
    assert _chapter_snapshot(initial) == [(n, 'INIT') for n in range(1, 21)]

    # site deletes 6..15, updates 16/18/20, adds 21..30.  The edit-check
    # window is the old epub's last 3 (18,19,20), so 18/20 pick up the
    # edits, 16 is out of range and keeps its original content, and the
    # deleted 6..15 are preserved in place.
    u1 = staged_update(config, initial,
                       _site((range(1, 6), 'INIT'),
                             ([16], 'UPD1'), ([17], 'INIT'),
                             ([18], 'UPD1'), ([19], 'INIT'), ([20], 'UPD1'),
                             (range(21, 31), 'NEW1')))
    assert _chapter_snapshot(u1) == \
        [(n, 'INIT') for n in range(1, 18)] + \
        [(18, 'UPD1'), (19, 'INIT'), (20, 'UPD1')] + \
        [(n, 'NEW1') for n in range(21, 31)]

    # site updates 29 and deletes 19..28.  28 was in the epub's last-3
    # window but is gone from the site, so it is preserved with its old
    # content instead of re-downloaded; 29 (still on the site) gets the
    # new content; 30 unchanged stays NEW1.
    u2 = staged_update(config, u1,
                       _site((range(1, 6), 'INIT'),
                             ([16], 'UPD1'), ([17], 'INIT'), ([18], 'UPD1'),
                             ([29], 'UPD2'), ([30], 'NEW1')))
    assert _chapter_snapshot(u2) == \
        [(n, 'INIT') for n in range(1, 18)] + \
        [(18, 'UPD1'), (19, 'INIT'), (20, 'UPD1')] + \
        [(n, 'NEW1') for n in range(21, 29)] + \
        [(29, 'UPD2'), (30, 'NEW1')]