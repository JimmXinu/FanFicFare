# -*- coding: utf-8 -*-
"""get_update_data(epub) reads an existing epub back for updates.

Historical ffdl/TtH epubs carry the chapter title as the first <h3> or
<h2> of the body; FFF strips that leading tag on read-back.  That
heuristic must NOT also eat mid-body author headings (e.g. a
"Status Sheet" <h2>) -- only a heading that is the first content of the
body is a presumed chapter title.
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


LEADING_H2 = ('<html><head><meta name="chapterurl" content="http://t/1"/></head>'
              '<body><h2>Chapter 1</h2><p>story</p></body></html>')
LEADING_H3 = ('<html><head><meta name="chapterurl" content="http://t/2"/></head>'
              '<body><h3 class="title">Chapter 2</h3><p>story2</p></body></html>')
MID_H2 = ('<html><head><meta name="chapterurl" content="http://t/3"/></head>'
          '<body><p>lead</p><h2>Status Sheet</h2><hr/><p>[USER: X]</p>'
          '<p>tail</p></body></html>')
MID_H3 = ('<html><head><meta name="chapterurl" content="http://t/4"/></head>'
          '<body><p>a</p><h3>Mid Note</h3><p>b</p></body></html>')


def test_leading_title_headings_are_stripped():
    """ffdl/TtH chapter-title <h2>/<h3> that starts the body is dropped."""
    map_ = _read_back([LEADING_H2, LEADING_H3])
    assert _body_text(map_['http://t/1']) == 'story'
    assert _body_text(map_['http://t/2']) == 'story2'


def test_mid_body_headings_are_preserved():
    """Author headings inside chapter content survive the read-back."""
    map_ = _read_back([MID_H2, MID_H3])
    assert 'Status Sheet' in _body_text(map_['http://t/3'])
    assert 'Mid Note' in _body_text(map_['http://t/4'])