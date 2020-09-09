import pytest

from unittest.mock import patch

from fanficfare.adapters.adapter_wuxiaworldsite import WuxiaWorldSiteSiteAdapter as adapter_for_tests
from datetime import datetime

from tests.adapters.generic_adapter_test import GenericAdapterTestExtractChapterUrlsAndMetadata, GenericAdapterTestGetChapterText
from tests.conftest import wuxiaworldsite_html_return, wuxiaworldsite_html_chapter_return

SPECIFIC_TEST_DATA = {
    'adapter': adapter_for_tests,
    'url': 'https://wuxiaworld.site/novel/some-story',
    'sections': ["wuxiaworld.site"],
    'specific_path_adapter': 'adapter_wuxiaworldsite.WuxiaWorldSiteSiteAdapter',

    'title': 'The Tutorial Is Too Hard',
    'cover_image': 'https://wuxiaworld.site/wp-content/uploads/2019/04/the-tutorial-is-too-hard-193x278.jpg',
    'author': 'Gandara',
    'authorId': 'gandara',
    'dateUpdated': datetime.utcnow().strftime('%Y-%m-%d'),
    'intro': "Read The Tutorial Is Too Hard Novel at WuxiaWorld.Site On a normal boring day, a message appears, inviting him to a Tutorial. A tale about Lee Ho Jae and his escape from the Tutorial. But he just happened to choose the hardest possible difficulty: Hell. Disclaimer:Neither the picture nor the content belongs to me. They are uploaded here, not for any bad purpose but for entertainment only. Disclaimer:If this novel is yours, please let us share this novel to everyone else and send us your credit. We display your credit to this novel! If you don’t please tell us too, We respect your decision.",
    'expected_chapters': {
        0:   {'title': 'Chapter 1',
              'url': 'https://wuxiaworld.site/novel/the-tutorial-is-too-hard/chapter-1'},
        10:  {'title': 'Chapter 11',
              'url': 'https://wuxiaworld.site/novel/the-tutorial-is-too-hard/chapter-11'},
        100: {'title': 'Chapter 101',
              'url': 'https://wuxiaworld.site/novel/the-tutorial-is-too-hard/chapter-101'},
        190: {'title': 'Chapter 191  -  Tutorial 35th Floor (10) (part 1)',
              'url': 'https://wuxiaworld.site/novel/the-tutorial-is-too-hard/chapter-191'},
        191: {'title': 'Chapter 191B - Tutorial 35th Floor (10) (part 2)',
              'url': 'https://wuxiaworld.site/novel/the-tutorial-is-too-hard/chapter-191b'},
    },
    'list_chapters_fixture': wuxiaworldsite_html_return,

    'chapter_url': 'https://wuxiaworld.site/novel/the-tutorial-is-too-hard/chapitre-1-some-title/2020/02/08/',
    'expected_sentences': [
        "Life is a series of choices.",
        "I always loved novels and cartoons. I’ve dreamt of those fantasy-like events happening to me.",
        "[Will you enter the Tutorial world?]",
        "[Choose the Tutorial difficulty. Depending on the difficulty, the dangers of the Tutorial stages increase along with the growth rate and reward.]"
    ],
    'chapter_fixture': wuxiaworldsite_html_chapter_return,
}


class TestExtractChapterUrlsAndMetadata(GenericAdapterTestExtractChapterUrlsAndMetadata):
    def setup_method(self):
        self.expected_data = SPECIFIC_TEST_DATA

        super().setup_method(
            SPECIFIC_TEST_DATA['adapter'],
            SPECIFIC_TEST_DATA['url'],
            SPECIFIC_TEST_DATA['sections'],
            SPECIFIC_TEST_DATA['specific_path_adapter'],
            SPECIFIC_TEST_DATA['list_chapters_fixture'])


class TestGetChapterText(GenericAdapterTestGetChapterText):
    def setup_method(self):
        self.expected_data = SPECIFIC_TEST_DATA

        super().setup_method(
            SPECIFIC_TEST_DATA['adapter'],
            SPECIFIC_TEST_DATA['url'],
            SPECIFIC_TEST_DATA['sections'],
            SPECIFIC_TEST_DATA['specific_path_adapter'],
            SPECIFIC_TEST_DATA['chapter_fixture'])

