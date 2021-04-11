#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__ = 'GPL v3'
__copyright__ = '2016, Jim Miller, 2011, Grant Drake <grant.drake@gmail.com>'
__docformat__ = 'restructuredtext en'

'''
A lot of this is lifted from Count Pages plugin by Grant Drake (with
some changes from davidfor.)
'''

import logging
logger = logging.getLogger(__name__)

import re

from calibre.ebooks.oeb.iterator import EbookIterator
try:
    from .fanficfare.six import text_type as unicode
except:
    from fanficfare.six import text_type as unicode

RE_HTML_BODY = re.compile(u'<body[^>]*>(.*)</body>', re.UNICODE | re.DOTALL | re.IGNORECASE)
RE_STRIP_MARKUP = re.compile(u'<[^>]+>', re.UNICODE)


def get_word_count(book_path):
    '''
    Estimate a word count
    '''
    from calibre.utils.localization import get_lang

    iterator = _open_epub_file(book_path)

    lang = iterator.opf.language
    lang = get_lang() if not lang else lang
    count = _get_epub_standard_word_count(iterator, lang)

    return count

def _open_epub_file(book_path, strip_html=False):
    '''
    Given a path to an EPUB file, read the contents into a giant block of text
    '''
    iterator = EbookIterator(book_path)
    iterator.__enter__(only_input_plugin=True, run_char_count=True,
            read_anchor_map=False)
    return iterator

def _get_epub_standard_word_count(iterator, lang='en'):
    '''
    This algorithm counts individual words instead of pages
    '''

    book_text = _read_epub_contents(iterator, strip_html=True)

    try:
        from calibre.spell.break_iterator import count_words
        wordcount = count_words(book_text, lang)
        logger.debug('\tWord count - count_words method:%s'%wordcount)
    except:
        try: # The above method is new and no-one will have it as of 08/01/2016. Use an older method for a beta.
            from calibre.spell.break_iterator import split_into_words_and_positions
            wordcount = len(split_into_words_and_positions(book_text, lang))
            logger.debug('\tWord count - split_into_words_and_positions method:%s'%wordcount)
        except:
            from calibre.utils.wordcount import get_wordcount_obj
            wordcount = get_wordcount_obj(book_text)
            wordcount = wordcount.words
            logger.debug('\tWord count - old method:%s'%wordcount)

    return wordcount

def _read_epub_contents(iterator, strip_html=False):
    '''
    Given an iterator for an ePub file, read the contents into a giant block of text
    '''
    book_files = []
    for path in iterator.spine:
        with open(path, 'rb') as f:
            html = f.read().decode('utf-8', 'replace')
            if strip_html:
                html = unicode(_extract_body_text(html)).strip()
                #print('FOUND HTML:', html)
        book_files.append(html)
    return ''.join(book_files)

def _extract_body_text(data):
    '''
    Get the body text of this html content wit any html tags stripped
    '''
    body = RE_HTML_BODY.findall(data)
    if body:
        return RE_STRIP_MARKUP.sub('', body[0]).replace('.','. ')
    return ''
