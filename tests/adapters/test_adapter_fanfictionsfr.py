import pytest

from unittest.mock import patch

from fanficfare.adapters.adapter_fanfictionsfr import FanfictionsFrSiteAdapter as fanfictionsfr

from tests.adapters.generic_adapter_test import GenericAdapterTestExtractChapterUrlsAndMetadata, GenericAdapterTestGetChapterText
from tests.conftest import fanfictionsfr_story_html_return, fanfictionsfr_html_chapter_return

SPECIFIC_TEST_DATA = {
    'adapter': fanfictionsfr,
    'url': 'https://www.fanfictions.fr/fanfictions/my-little-pony-friendship-is-magic/4798_brasier-annee-zero/chapters.html',
    'sections': ["fanfictions.fr"],
    'specific_path_adapter': 'adapter_fanfictionsfr.FanfictionsFrSiteAdapter',

    'title': 'Brasier Année Zéro',
    'cover_image': None,
    'author': 'Code 44',
    'authorId': '782_code-44',
    'dateUpdated': '2016-11-09',
    'intro': "Des milliers d’années avant l’ère de Twilight Sparkle et de ses camarades, les origines de la guerre entre Discord et la Princesse Celestia.",
    'expected_chapters': {
        0:   {'title': 'Chapitre 1 : Avant propos',
              'url': 'https://fanfictions.fr/fanfictions/my-little-pony-friendship-is-magic/4798_brasier-annee-zero/17166_avant-propos/lire.html'},
        1:  {'title': 'Chapitre 2 : Prologue : Cendres froides',
              'url': 'https://fanfictions.fr/fanfictions/my-little-pony-friendship-is-magic/4798_brasier-annee-zero/17167_prologue-cendres-froides/lire.html'},
        2: {'title': 'Chapitre 3 : Première partie : Fraisil',
              'url': 'https://fanfictions.fr/fanfictions/my-little-pony-friendship-is-magic/4798_brasier-annee-zero/17168_premiere-partie-fraisil/lire.html'},
    },
    'list_chapters_fixture': fanfictionsfr_story_html_return,

    'chapter_url': 'https://www.fanfictions.fr/fanfictions/my-little-pony-friendship-is-magic/4798_brasier-annee-zero/17166_avant-propos/lire.html',
    'expected_sentences': [
        "Des milliers d’années avant l’avènement de Twilight Sparkle et de ses amies, alors qu’Equestria n’était encore qu’une jeune nation, poneys, pégases, et licornes tentent tant bien que mal d’évoluer de concert, à l’époque où l’Unification des trois tribus n’est pas si ancienne.",
        "Voici l’histoire du commencement.",
        "Braiser Année Zéro est une fanfiction inspirée de la série télévisée <em>My Little Pony Friendship is Magic</em>.",
        "Histoire écrite par Code 44. Correction faite par Archy et Code 44."
    ],
    'chapter_fixture': fanfictionsfr_html_chapter_return,
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

