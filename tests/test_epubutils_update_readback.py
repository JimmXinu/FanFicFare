# -*- coding: utf-8 -*-
"""get_update_data(epub) reads an existing epub back for updates.

Modern FFF epubs mark the chapter title with class=fff_chapter_title
(<h3 class="fff_chapter_title">${chapter}</h3> from writer_epub.py); the
maintainer's fix strips exactly that tag on read-back, so any author's
in-chapter heading (e.g. a "Status Sheet" <h2>) always survives.

Older ffdl/TtH epubs have no marker: the title is the first <h2> (TtH)
or <h3> (ffdl) of the body, and only that presumed-title heading is
stripped.  Mid-body headings after it are preserved.
"""
import io
import zipfile

import pytest


def _make_epub_bytes(chapter_bodies):
    """Build a minimal epub (as bytes) containing the given bodies.

    Each body must carry its own <meta name="chapterurl" .../> in the
    head so get_update_data can key it.
    """
    buf = io.BytesIO()
    z = zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED)
    z.writestr('mimetype', 'application/epub+zip')
    z.writestr(
        'META-INF/container.xml',
        '<?xml version="1.0"?>'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        '<rootfiles><rootfile full-path="OEBPS/content.opf" '
        'media-type="application/oebps-package+xml"/></rootfiles></container>')
    manifest = ''.join(
        '<item id="c%d" href="chapter%d.xhtml" media-type="application/xhtml+xml"/>'
        % (i, i) for i in range(len(chapter_bodies)))
    spine = ''.join('<itemref idref="c%d"/>' % i for i in range(len(chapter_bodies)))
    z.writestr(
        'OEBPS/content.opf',
        '<?xml version="1.0" encoding="utf-8"?>'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
        'unique-identifier="u">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        '<dc:identifier id="u">x</dc:identifier><dc:title>t</dc:title></metadata>'
        '<manifest><item id="ncx" href="np.xhtml" media-type="application/x-dtbncx+xml"/>'
        '%s</manifest><spine>%s</spine></package>' % (manifest, spine))
    for i, body in enumerate(chapter_bodies):
        z.writestr('OEBPS/chapter%d.xhtml' % i, body)
    z.writestr('OEBPS/np.xhtml', '<html/>')
    z.close()
    return buf.getvalue()


def _read_back(chapter_bodies):
    """Return the {url: bodysoup} map get_update_data produces."""
    from fanficfare.epubutils import get_update_data
    data = get_update_data(io.BytesIO(_make_epub_bytes(chapter_bodies)))
    return data[7]


def _body_text(soup):
    import re
    return re.sub(r'\s+', ' ', soup.get_text(' ', strip=True))


TITLE_H2 = ('<html><head><meta name="chapterurl" content="http://t/1"/></head>'
            '<body><h2>Chapter 1</h2><p>story</p></body></html>')
TITLE_H3 = ('<html><head><meta name="chapterurl" content="http://t/2"/></head>'
            '<body><h3>Chapter 2</h3><p>story2</p></body></html>')
REAL_WORLD_EXAMPLE = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<html xmlns="http://www.w3.org/1999/xhtml"><head>'
    '<title>chapter title</title>'
    '<link href="stylesheet.css" type="text/css" rel="stylesheet"/>'
    '<meta name="chapterurl" content="https://example.invalid/fiction/story/chapter/1/chapter-title"/>'
    '<meta name="chapterorigtitle" content="chapter title"/>'
    '<meta name="chaptertoctitle" content="chapter title"/>'
    '<meta name="chaptertitle" content="chapter title"/>'
    '</head><body class="fff_chapter">'
    '<h3 class="fff_chapter_title">chapter title</h3>'
    '<div class="chapter-inner chapter-content">'
    '<p class="cnYWJj"><strong><em>lorem ipsum dolor sit amet</em></strong></p>'
    '<p class="cnZGVm">consectetur adipiscing elit sed do eiusmod</p>'
    '<h2>Status Sheet</h2>'
    '<hr/>'
    '<p class="cnZ2hp"><strong><em>lorem ipsum</em></strong></p>'
    '<p class="cnampr">dolor sit amet</p>'
    '<hr/>'
    '<p class="cnc3R1"><strong><em>lorem ipsum</em></strong></p>'
    '</div></body></html>')
LEGACY_MID_H2 = ('<html><head><meta name="chapterurl" content="http://t/4"/></head>'
                 '<body><h3>Chapter 4</h3><p>lead</p><h2>Status Sheet</h2>'
                 '<p>tail</p></body></html>')
LEGACY_SECOND_H3 = ('<html><head><meta name="chapterurl" content="http://t/5"/></head>'
                    '<body><h3>Chapter 5</h3><p>a</p><h3>Mid Note</h3><p>b</p></body></html>')


def test_leading_title_headings_are_stripped():
    """Legacy chapter-title <h2>/<h3> that starts the body is dropped."""
    map_ = _read_back([TITLE_H2, TITLE_H3])
    assert _body_text(map_['http://t/1']) == 'story'
    assert _body_text(map_['http://t/2']) == 'story2'


def test_real_world_chapter_anonymized():
    """Faithful replica of a real epub chapter that exposed the bug.

    Old upstream update read-back stripped both the class-marked title
    <h3> and the mid-body 'Status Sheet' <h2>.  Only the title may go:
    the Status Sheet heading must survive.  Original story text replaced
    by lorem ipsum, the real title by 'chapter title'.
    """
    map_ = _read_back([REAL_WORLD_EXAMPLE])
    txt = _body_text(map_['https://example.invalid/fiction/story/chapter/1/chapter-title'])
    assert 'chapter title' not in txt
    assert 'Status Sheet' in txt
    assert 'lorem ipsum' in txt


def test_legacy_only_first_heading_is_title():
    """In unmarked epubs only the first heading is treated as the title.

    Mid-body author headings that follow the title survive the read-back.
    """
    map_ = _read_back([LEGACY_MID_H2, LEGACY_SECOND_H3])
    t4 = _body_text(map_['http://t/4'])
    assert 'Chapter 4' not in t4
    assert 'Status Sheet' in t4
    t5 = _body_text(map_['http://t/5'])
    assert 'Chapter 5' not in t5
    assert 'Mid Note' in t5