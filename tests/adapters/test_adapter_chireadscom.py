import pytest

from unittest.mock import patch

from fanficfare.adapters.adapter_chireadscom import ChireadsComSiteAdapter as chiread

from tests.adapters.generic_adapter_test import GenericAdapterTestExtractChapterUrlsAndMetadata, GenericAdapterTestGetChapterText
from tests.conftest import chireads_html_return, chireads_html_with_chapters_return, chireads_html_chapter_return

SPECIFIC_TEST_DATA = {
    'adapter': chiread,
    'url': 'https://chireads.com/category/translatedtales/some-story/',
    'sections': ["chireads.com"],
    'specific_path_adapter': 'adapter_chireadscom.ChireadsComSiteAdapter',

    'title': 'Shadow Hack',
    'cover_image': 'https://chireads.com/wp-content/uploads/2020/04/Shadow-Hack-2.jpg',
    'author': 'Great Lord of Cloudland',
    'authorId': 'Great Lord of Cloudland',
    'dateUpdated': '2020-06-27',
    'intro': "Par coïncidence, Li Yunmu a découvert une super machine de l’ère des ténèbres de l’humanité. À partir de ce moment, sa vie ordinaire ne sera plus jamais la même ! Aptitude ? Talent inné ? Qu’est-ce que c’est ? Ça se mange ? Je n’ai ni aptitude ni compétence innée, mais mon ombre peut monter en niveau en utilisant des Hack. Expérience, points de compétence, prouesse au combat …… .Tous pourraient être Hacké. Même endormi ou fatigué, je pourrais encore améliorer ses compétences. [Ding, ton ombre a tué une fourmi, tu as gagné des points d’expérience et des points d’aptitude.] [Ding, ton ombre a tué une libellule, elle a laissé tomber une boîte dimensionnelle.] Merde, même tuer des insectes peut également augmenter son expérience et obtenir des récompenses.Quoi de mieux !Light novel Shadow Hack en français /Traduction de Shadow Hack en Français / Shadow Hack FrTraduction en français : ZoroBonjour ou bonsoir à tous ! Mon nom est Zoro, j'arrive sur Chiread avec un novel, et quel novel ?! Shadow Hack, du fight, de la chance, du cheaté, et j'en passe. Vraiment, un gros kiff à lire à tout prix !",
    'expected_chapters': {
        0:   {'title': 'Chapitre 1 – Ombre mystérieuse',
              'url': 'https://chireads.com/translatedtales/chapitre-1-ombre-mysterieuse/2020/02/08/'},
        10:  {'title': 'Chapitre 11 – Bataille injuste',
              'url': 'https://chireads.com/translatedtales/chapitre-11-bataille-injuste/2020/02/08/'},
        100: {'title': 'Chapitre 101 – La rancune de sœur Noujie',
              'url': 'https://chireads.com/translatedtales/chapitre-101-la-rancune-de-soeur-noujie/2020/02/08/'},
    },
    'list_chapters_fixture': chireads_html_return,

    'chapter_url': 'https://chireads.com/translatedtales/chapitre-1-some-title/2020/02/08/',
    'expected_sentences': [
        "Dans une petite pièce chaude, alors que Li Yunmu avait allumé son ordinateur, cette phrase est soudainement apparue devant lui.",
        "Un véritable ordinateur de l’ère sombre aurait certainement un prix de départ de pièces de la cinquième dimension.",
        "Comment un citoyen aussi vulgaire que lui-même pourrait-il avoir les qualifications nécessaires pour accéder aux pièces de la cinquième dimension de l’Alliance ?",
        "À ce moment, la silhouette de Li Yunmu est devenue sans vie !"
    ],
    'chapter_fixture': chireads_html_chapter_return,
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

    @patch('fanficfare.adapters.adapter_chireadscom.ChireadsComSiteAdapter.get_request')
    def test_get_novel_info_when_book(self, mockget_request):
        # Given
        mockget_request.return_value = chireads_html_with_chapters_return

        # When
        self.adapter.extractChapterUrlsAndMetadata()

        # Then
        assert self.adapter.get_chapters()[0]['title'] == 'Chapitre 01 : Matinée au village'
        assert self.adapter.get_chapters()[0]['url'] == 'https://chireads.com/sur-le-web/chapitre-01-matinee-au-village/2017/08/17/'
        assert self.adapter.get_chapters()[23]['title'] == 'Chapitre 1 : La créature magique, Souris Fantôme'
        assert self.adapter.get_chapters()[23]['url'] == 'https://chireads.com/sur-le-web/chapitre-1-la-creature-magique-souris-fantome/2017/08/18/'


class TestGetChapterText(GenericAdapterTestGetChapterText):
    def setup_method(self):
        self.expected_data = SPECIFIC_TEST_DATA

        super().setup_method(
            SPECIFIC_TEST_DATA['adapter'],
            SPECIFIC_TEST_DATA['url'],
            SPECIFIC_TEST_DATA['sections'],
            SPECIFIC_TEST_DATA['specific_path_adapter'],
            SPECIFIC_TEST_DATA['chapter_fixture'])

