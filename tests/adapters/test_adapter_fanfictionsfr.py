import pytest

from unittest.mock import MagicMock, patch

from fanficfare.adapters.adapter_fanfictionsfr import FanfictionsFrSiteAdapter as fanfictionsfr
from fanficfare.exceptions import FailedToDownload

from tests.adapters.generic_adapter_test import GenericAdapterTestExtractChapterUrlsAndMetadata, GenericAdapterTestGetChapterText
from tests.conftest import fanfictionsfr_story_html_return, fanfictionsfr_html_chapter_return, fanfictionsfr_suspended_story_html_return

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
        
    @patch('fanficfare.adapters.adapter_fanfictionsfr.FanfictionsFrSiteAdapter.get_request')
    def test_raises_exception_when_fic_is_suspended(self, mockget_request):
        # Given
        mockget_request.return_value = fanfictionsfr_suspended_story_html_return

        # When
        with pytest.raises(FailedToDownload) as exc_info:
            self.adapter.extractChapterUrlsAndMetadata()

        # Then
        assert str(exc_info.value) == "Failed to download the fanfiction, most likely because it is suspended."

class TestGetChapterText(GenericAdapterTestGetChapterText):
    def setup_method(self):
        self.expected_data = SPECIFIC_TEST_DATA

        super().setup_method(
            SPECIFIC_TEST_DATA['adapter'],
            SPECIFIC_TEST_DATA['url'],
            SPECIFIC_TEST_DATA['sections'],
            SPECIFIC_TEST_DATA['specific_path_adapter'],
            SPECIFIC_TEST_DATA['chapter_fixture'])

    @patch('fanficfare.adapters.adapter_fanfictionsfr.FanfictionsFrSiteAdapter.get_request')
    def test_it_handles_zipped_chapters(self, mockget_request_redirected):
        expected_sentences = [
            "Elle a écrite avant la reprise de next gen –Shippuuden maintenant-, quand on ne savait encore rien de l’évolution des personnages.",
            "\" Commandant, il faudrait que vous me suiviez à l'infirmerie… \"",
            "Mais il ne craquera pas, car il est un ninja de Konoha, et que s'effondrer serait trahir.",
        ]

        # Given
        zip_file_path = "tests/fixtures_fanfictionsfr_zipfic.zip"  # Replace with the path to your zip file
        with open(zip_file_path, 'rb') as f:
            zip_data = f.read()  # Read the zip file as binary data

        redirected_response_mock = MagicMock()
        redirected_response_mock.content = zip_data
        redirected_response_mock.headers = {'Content-Type': 'application/zip'}
        mockget_request_redirected.return_value = (redirected_response_mock, "https://fanfictions.fr/fanfictions/naruto/232_crise/683_kiba/telecharger_pdf.html")

        # When
        response = self.adapter.getChapterText("https://fanfictions.fr/fanfictions/naruto/232_crise/683_kiba/lire.html")

        # Then
        for p in expected_sentences:
            assert p in response
