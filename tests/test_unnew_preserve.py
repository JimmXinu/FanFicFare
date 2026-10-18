"""Offline tests for 'Remove New Chapter Marks' (unnew) combined with
update_preserve_deleted_chapters.

unnew_chapters_epub() lives in fanficfare.epubutils and is a pure
zip-in/zip-out function -- no adapter, no config, no Calibre -- so these
tests drive it directly on epub bytes built by the shared staged harness.

Context: JimmXinu/FanFicFare#1434, "Remove New Chapter Marks Leaves Last
Occurrence".  unnew used to require the chapter heading to match the
<meta name="chaptertitle"> *exactly*, so a custom heading carrying a
suffix -- notably the trailing space and ${preserved_chapter_mark} that
preserved chapters produce -- never matched and the '(new)' mark stayed.
That was fixed upstream in f6a8af7e ("Fixing Unnew for #1434"); the
tests here pin the fixed behaviour.
"""
import io

from fanficfare.epubutils import unnew_chapters_epub

from tests.adapters.update_harness import (CH, chapter_meta, staged_config,
                                           staged_download, staged_update)

# The chapter_start template from the #1434 report: same as FFF's default
# plus ${preserved_chapter_mark} in the heading.  configparser needs
# continuation lines indented, hence the join.
PRESERVED_MARK_HEADING_START = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>${chapter}</title>
<link href="stylesheet.css" type="text/css" rel="stylesheet"/>
<meta name="chapterurl" content="${url}" />
<meta name="chapterorigtitle" content="${origchapter}" />
<meta name="chaptertoctitle" content="${tocchapter}" />
<meta name="chaptertitle" content="${chapter}" />
</head>
<body class="fff_chapter">
<h3 class="fff_chapter_title">${chapter} ${preserved_chapter_mark}</h3>
"""

PRESERVED_MARK_EXTRA = 'chapter_start:' + ''.join(
    '\n    ' + line for line in PRESERVED_MARK_HEADING_START.splitlines()) + '\n'


def unnew(epub_bytes):
    """Run unnew_chapters_epub over epub_bytes.

    Returns (changed, epub_bytes).  Note unnew only writes its output
    when it actually changed something, so the buffer is empty when
    changed is False -- pass the original through in that case so callers
    can inspect the book either way.
    """
    out = io.BytesIO()
    changed = unnew_chapters_epub(io.BytesIO(epub_bytes), out)
    return changed, (out.getvalue() if changed else epub_bytes)


def new_chapter_then_deleted(tmp_path, extra=''):
    """Three staged passes producing a book where chapter 6 is both
    marked new *and* preserved:

    pass 1  download ch1..ch5 -- nothing is marked, a first download
            never marks (base_adapter: mark_new = bool(oldchapters))
    pass 2  update with ch6 added  -- ch6 is marked '(new)'
    pass 3  update with ch6 removed from the site -- ch6 is preserved
            and keeps its '(new)' mark
    """
    config = staged_config(tmp_path, mark_new='true', extra=extra)
    first = {n: '<p>chapter %d body [[V0]]</p>' % n for n in range(1, 6)}
    second = dict(first)
    second[6] = '<p>chapter 6 body [[NEW]]</p>'
    third = {n: second[n] for n in range(1, 6)}

    epub = staged_download(config, first)
    epub = staged_update(config, epub, second)
    return staged_update(config, epub, third)


def test_chapter_is_marked_new_then_preserved(tmp_path):
    """Precondition for every test below: the fixture really does end up
    with a preserved chapter that is still marked new.  If this stops
    holding, the tests after it are vacuous."""
    epub = new_chapter_then_deleted(tmp_path)

    marked = chapter_meta(epub, 6)
    assert marked['data']['mark_new'] is True
    assert marked['data']['preserved_chapter_mark'] == '(Preserved Deleted Chapter)'
    assert marked['chaptertitle'] == '(new) Chapter 6'


def test_unnew_unmarks_preserved_new_chapter(tmp_path):
    """A preserved chapter that was marked new can be unmarked, and the
    '(Preserved Deleted Chapter)' marker survives the unnew."""
    epub = new_chapter_then_deleted(tmp_path)

    changed, result = unnew(epub)
    assert changed is True

    unmarked = chapter_meta(result, 6)
    assert unmarked['data']['mark_new'] is False
    assert unmarked['chaptertitle'] == 'Chapter 6'
    assert unmarked['origchapter'] == 'Chapter 6'
    assert unmarked['h3'] == 'Chapter 6'
    # the preserve marker is not a '(new)' mark and must not be touched
    assert unmarked['data']['preserved_chapter_mark'] == \
        '(Preserved Deleted Chapter)'


def test_unnew_unmarks_preserved_new_chapter_with_mark_in_heading(tmp_path):
    """The exact shape from #1434: a custom chapter_start that appends
    ${preserved_chapter_mark} to the heading.

    Before f6a8af7e unnew compared the heading to chaptertitle with '==',
    so the trailing space (the marker expands to '' on chapters that are
    not preserved) meant the match failed and '(new)' was left in place.
    """
    epub = new_chapter_then_deleted(tmp_path, extra=PRESERVED_MARK_EXTRA)

    marked = chapter_meta(epub, 6)
    assert marked['h3'] == '(new) Chapter 6 (Preserved Deleted Chapter)'
    # chapters that are not preserved expand the marker to '', which is
    # where the trailing space comes from
    assert chapter_meta(epub, 1)['h3'] == 'Chapter 1 '

    changed, result = unnew(epub)
    assert changed is True

    unmarked = chapter_meta(result, 6)
    assert unmarked['data']['mark_new'] is False
    assert unmarked['chaptertitle'] == 'Chapter 6'
    # only the '(new)' part is replaced -- the preserved marker and the
    # trailing space it implies are left alone
    assert unmarked['h3'] == 'Chapter 6 (Preserved Deleted Chapter)'


def test_unnew_leaves_unmarked_chapters_untouched(tmp_path):
    """Only the marked chapter changes; the rest keep their metadata."""
    epub = new_chapter_then_deleted(tmp_path)
    before = {n: chapter_meta(epub, n) for n in range(1, 6)}

    changed, result = unnew(epub)
    assert changed is True

    for n in range(1, 6):
        assert chapter_meta(result, n) == before[n]


def test_unnew_is_noop_when_nothing_is_marked(tmp_path):
    """A book with no '(new)' chapters is left byte-identical, and unnew
    reports that it changed nothing."""
    config = staged_config(tmp_path, mark_new='true')
    content = {n: '<p>chapter %d body [[V0]]</p>' % n for n in range(1, 4)}
    epub = staged_download(config, content)

    changed, result = unnew(epub)
    assert changed is False
    assert result == epub
