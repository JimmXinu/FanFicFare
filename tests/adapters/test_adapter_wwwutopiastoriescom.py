"""Offline tests for the utopiastories.com domain change: old
www.utopiastories.com URLs must keep working and still find books
saved with them in the Calibre library."""
import re

import pytest

from fanficfare import adapters

NEW_URL = 'https://utopiastories.com/code/show_story.asp/recid/10039.html'


@pytest.mark.parametrize('url', [
    'http://www.utopiastories.com/code/show_story.asp/recid/10039.html',
    'https://www.utopiastories.com/code/show_story/recid/10039.html',
    NEW_URL,
    'utopiastories.com/code/show_story/recid/10039',
])
def test_normalizes_to_new_domain(url):
    assert adapters.getNormalStoryURL(url) == NEW_URL


@pytest.mark.parametrize('identifier,found', [
    ('https://www.utopiastories.com/code/show_story.asp/recid/10039.html', True),
    ('http://www.utopiastories.com/code/show_story.asp/recid/10039.html', True),
    (NEW_URL, True),
    ('https://utopiastories.com/code/show_story.asp/recid/100391.html', False),
])
def test_url_search_finds_old_www_urls(identifier, found):
    search = adapters.get_url_search(NEW_URL)
    # identifiers:"~ur(i|l):~<regexp>"
    regexp = re.search(r':~(\^.*)"$', search).group(1)
    assert bool(re.search(regexp, identifier)) == found
