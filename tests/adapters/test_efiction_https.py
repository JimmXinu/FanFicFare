"""Offline tests for eFiction sites moved to https (and
thehookupzone.net/CriminalMinds to criminal-minds-fiction.com): logins
must go to https directly, since following the http->https redirect
turns the login POST into a GET, and old http URLs must keep working."""
import re

import pytest

from fanficfare import adapters
from fanficfare.configurable import Configuration

MOVED = [
    ('http://thehookupzone.net/CriminalMinds/viewstory.php?sid=12',
     'https://criminal-minds-fiction.com/viewstory.php?sid=12'),
    ('http://tgstorytime.com/viewstory.php?sid=12',
     'https://tgstorytime.com/viewstory.php?sid=12'),
    ('http://ninelivesarchive.com/viewstory.php?sid=12',
     'https://ninelivesarchive.com/viewstory.php?sid=12'),
    ('http://gluttonyfiction.com/viewstory.php?sid=12',
     'https://gluttonyfiction.com/viewstory.php?sid=12'),
    ('http://www.giantessworld.net/viewstory.php?sid=12',
     'https://www.giantessworld.net/viewstory.php?sid=12'),
    ('http://sinful-dreams.com/unicorn/fic/viewstory.php?sid=12',
     'https://sinful-dreams.com/unicorn/fic/viewstory.php?sid=12'),
    ('http://sinful-dreams.com/wicked/temptation/viewstory.php?sid=12',
     'https://sinful-dreams.com/wicked/temptation/viewstory.php?sid=12'),
]


def make_adapter(url):
    configuration = Configuration(adapters.getConfigSectionsFor(url),
                                  'EPUB', lightweight=True)
    return adapters.getAdapter(configuration, url)


@pytest.mark.parametrize('old_url,new_url', MOVED)
def test_old_and_new_story_urls_normalize_to_https(old_url, new_url):
    assert adapters.getNormalStoryURL(old_url) == new_url
    assert adapters.getNormalStoryURL(new_url) == new_url


@pytest.mark.parametrize('old_url,new_url', MOVED)
def test_login_url_is_https(old_url, new_url):
    assert make_adapter(old_url).getLoginUrl().startswith('https://')


@pytest.mark.parametrize('old_url,new_url', MOVED)
def test_old_chapter_urls_match_new_ones(old_url, new_url):
    # Chapter URLs in existing epubs must normalize to the new ones,
    # or updates re-download (or with update_preserve_deleted_chapters
    # duplicate) every chapter.
    adapter = make_adapter(old_url)
    assert adapter.normalize_chapterurl(old_url + '&chapter=2') == \
        new_url + '&chapter=2'


def test_thehookupzone_keeps_old_ini_section():
    url = 'https://criminal-minds-fiction.com/viewstory.php?sid=12'
    assert 'thehookupzone.net' in adapters.getConfigSectionsFor(url)


@pytest.mark.parametrize('identifier,found', [
    ('http://thehookupzone.net/CriminalMinds/viewstory.php?sid=12', True),
    ('https://www.thehookupzone.net/CriminalMinds/viewstory.php?sid=12', True),
    ('https://criminal-minds-fiction.com/viewstory.php?sid=12', True),
    ('https://criminal-minds-fiction.com/viewstory.php?sid=123', False),
])
def test_thehookupzone_url_search_finds_old_urls(identifier, found):
    search = adapters.get_url_search(
        'https://criminal-minds-fiction.com/viewstory.php?sid=12')
    # identifiers:"~ur(i|l):~<regexp>"
    regexp = re.search(r':~(\^.*)"$', search).group(1)
    assert bool(re.search(regexp, identifier)) == found
