import pytest

from fanficfare.geturls import get_urls_from_html, get_urls_from_text

AO3 = 'https://archiveofourown.org/works/12345'
FFNET = 'https://www.fanfiction.net/s/1234567/1/Some-Title'


def test_plain_urls():
    text = 'One %s and two %s' % (AO3, FFNET)
    assert get_urls_from_text(text) == [AO3, FFNET]


@pytest.mark.parametrize('text', [
    'see (%s).',  # parenthesized link at the end of a sentence
    'see (%s)',
    'see [link](%s)',  # markdown
    'see %s.',
    'see %s, and more',
    'see <%s>',
    'is it %s?',
])
def test_surrounding_punctuation_is_not_part_of_url(text):
    assert get_urls_from_text(text % FFNET) == [FFNET]


def test_same_story_is_listed_once():
    text = '%s/chapters/678 and %s' % (AO3, AO3)
    # longest URL for the story is kept unless normalized
    assert get_urls_from_text(text) == [AO3 + '/chapters/678']
    assert get_urls_from_text(text, normalize=True) == [AO3]


def test_unsupported_urls_are_ignored():
    assert get_urls_from_text('https://example.com/story/1 and %s' % AO3) == [AO3]


def test_bytes_input():
    assert get_urls_from_text(('link: %s' % AO3).encode('utf8')) == [AO3]


def test_urls_from_html():
    html = '<a href="%s">abs</a> <a href="/works/4444">rel</a> <a href="https://example.com/">no</a>' % AO3
    assert get_urls_from_html(html, url='https://archiveofourown.org/users/me') == [
        AO3,
        'https://archiveofourown.org/works/4444',
    ]
