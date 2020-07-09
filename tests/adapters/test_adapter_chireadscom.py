import pytest

# from unittest import mock
from unittest.mock import patch # , call, Mock

from fanficfare.six.moves.urllib.error import HTTPError

from fanficfare.adapters.adapter_chireadscom import ChireadsComSiteAdapter as chiread
from fanficfare.configurable import Configuration
from fanficfare import exceptions


@patch('fanficfare.adapters.adapter_chireadscom.ChireadsComSiteAdapter.setDescription')
@patch('fanficfare.adapters.adapter_chireadscom.ChireadsComSiteAdapter.setCoverImage')
class TestExtractChapterUrlsAndMetadata:
    def setup_method(self):
        self.url = 'https://chireads.com/category/translatedtales/some-story/'
        self.configuration = Configuration(["chireads.com"], "EPUB", lightweight=True)
        self.chireads = chiread(self.configuration, self.url)

    def test_raise_404_for_unexistant_story(self, mock_setCoverImage, mock_setDescription):
        # When
        with pytest.raises(exceptions.StoryDoesNotExist):
            self.chireads.extractChapterUrlsAndMetadata()

    @patch('fanficfare.adapters.adapter_chireadscom.ChireadsComSiteAdapter._fetchUrl')
    def test_get_metadata(self, mockFetchUrl, mock_setCoverImage, mock_setDescription, chireads_html_return):
        # Given
        mockFetchUrl.return_value = chireads_html_return

        # When
        self.chireads.extractChapterUrlsAndMetadata()

        # Then
        assert self.chireads.story.getMetadata('title') == 'Shadow Hack'


    @patch('fanficfare.adapters.adapter_chireadscom.ChireadsComSiteAdapter._fetchUrl')
    def test_get_cover_image(self, mockFetchUrl, mock_setCoverImage, mock_setDescription, chireads_html_return):
        # Given
        mockFetchUrl.return_value = chireads_html_return

        # When
        self.chireads.extractChapterUrlsAndMetadata()

        # Then
        mock_setCoverImage.assert_called_with(self.url, 'https://chireads.com/wp-content/uploads/2020/04/Shadow-Hack-2.jpg')


    @patch('fanficfare.adapters.adapter_chireadscom.ChireadsComSiteAdapter._fetchUrl')
    def test_get_autor(self, mockFetchUrl, mock_setCoverImage, mock_setDescription, chireads_html_return):
        # Given
        mockFetchUrl.return_value = chireads_html_return

        # When
        self.chireads.extractChapterUrlsAndMetadata()

        # Then
        assert self.chireads.story.getMetadata('author') == 'Great Lord of Cloudland'
        assert self.chireads.story.getMetadata('authorId') == 'Great Lord of Cloudland'


    @patch('fanficfare.adapters.adapter_chireadscom.ChireadsComSiteAdapter._fetchUrl')
    def test_get_dateUpdated(self, mockFetchUrl, mock_setCoverImage, mock_setDescription, chireads_html_return):
        # Given
        mockFetchUrl.return_value = chireads_html_return

        # When
        self.chireads.extractChapterUrlsAndMetadata()

        # Then
        assert self.chireads.story.getMetadata('dateUpdated') == '2020-06-27'


    @patch('fanficfare.adapters.adapter_chireadscom.ChireadsComSiteAdapter._fetchUrl')
    def test_get_novel_info(self, mockFetchUrl, mock_setCoverImage, mock_setDescription, chireads_html_return):
        # Given
        mockFetchUrl.return_value = chireads_html_return

        # When
        self.chireads.extractChapterUrlsAndMetadata()

        # Then
        expected_intro = "Par coïncidence, Li Yunmu a découvert une super machine de l’ère des ténèbres de l’humanité. À partir de ce moment, sa vie ordinaire ne sera plus jamais la même ! Aptitude ? Talent inné ? Qu’est-ce que c’est ? Ça se mange ? Je n’ai ni aptitude ni compétence innée, mais mon ombre peut monter en niveau en utilisant des Hack. Expérience, points de compétence, prouesse au combat …… .Tous pourraient être Hacké. Même endormi ou fatigué, je pourrais encore améliorer ses compétences. [Ding, ton ombre a tué une fourmi, tu as gagné des points d’expérience et des points d’aptitude.] [Ding, ton ombre a tué une libellule, elle a laissé tomber une boîte dimensionnelle.] Merde, même tuer des insectes peut également augmenter son expérience et obtenir des récompenses.Quoi de mieux !Light novel Shadow Hack en français /Traduction de Shadow Hack en Français / Shadow Hack FrTraduction en français : ZoroBonjour ou bonsoir à tous ! Mon nom est Zoro, j'arrive sur Chiread avec un novel, et quel novel ?! Shadow Hack, du fight, de la chance, du cheaté, et j'en passe. Vraiment, un gros kiff à lire à tout prix !"
        mock_setDescription.assert_called_with(self.url, expected_intro)


    @patch('fanficfare.adapters.adapter_chireadscom.ChireadsComSiteAdapter._fetchUrl')
    def test_get_novel_info(self, mockFetchUrl, mock_setCoverImage, mock_setDescription, chireads_html_return):
        # Given
        mockFetchUrl.return_value = chireads_html_return

        # When
        self.chireads.extractChapterUrlsAndMetadata()

        # Then
        assert self.chireads.get_chapters()[0]['title'] == 'Chapitre 1 – Ombre mystérieuse'
        assert self.chireads.get_chapters()[0]['url'] == 'https://chireads.com/translatedtales/chapitre-1-ombre-mysterieuse/2020/02/08/'
        assert self.chireads.get_chapters()[10]['title'] == 'Chapitre 11 – Bataille injuste'
        assert self.chireads.get_chapters()[10]['url'] == 'https://chireads.com/translatedtales/chapitre-11-bataille-injuste/2020/02/08/'
        assert self.chireads.get_chapters()[100]['title'] == 'Chapitre 101 – La rancune de sœur Noujie'
        assert self.chireads.get_chapters()[100]['url'] == 'https://chireads.com/translatedtales/chapitre-101-la-rancune-de-soeur-noujie/2020/02/08/'


    @patch('fanficfare.adapters.adapter_chireadscom.ChireadsComSiteAdapter._fetchUrl')
    def test_get_novel_info_when_book(self, mockFetchUrl, mock_setCoverImage, mock_setDescription, chireads_html_with_chapters_return):
        # Given
        mockFetchUrl.return_value = chireads_html_with_chapters_return

        # When
        self.chireads.extractChapterUrlsAndMetadata()

        # Then
        assert self.chireads.get_chapters()[0]['title'] == 'Chapitre 01 : Matinée au village'
        assert self.chireads.get_chapters()[0]['url'] == 'https://chireads.com/sur-le-web/chapitre-01-matinee-au-village/2017/08/17/'
        assert self.chireads.get_chapters()[23]['title'] == 'Chapitre 1 : La créature magique, Souris Fantôme'
        assert self.chireads.get_chapters()[23]['url'] == 'https://chireads.com/sur-le-web/chapitre-1-la-creature-magique-souris-fantome/2017/08/18/'


class TestGetChapterText:
    def setup_method(self):
        self.url = 'https://chireads.com/category/translatedtales/some-story/'
        self.chapter_url = 'https://chireads.com/translatedtales/chapitre-1-some-title/2020/02/08/'
        self.configuration = Configuration(["chireads.com"], "EPUB", lightweight=True)
        self.chireads = chiread(self.configuration, self.url)

    @patch('fanficfare.adapters.adapter_chireadscom.ChireadsComSiteAdapter._fetchUrl')
    def test_get_metadata(self, mockFetchUrl, chireads_html_chapter_return):
        # Given
        mockFetchUrl.return_value = chireads_html_chapter_return

        # When
        response = self.chireads.getChapterText(self.chapter_url)

        # Then
        expected = [
            "Dans une petite pièce chaude, alors que Li Yunmu avait allumé son ordinateur, cette phrase est soudainement apparue devant lui.",
            "Un véritable ordinateur de l’ère sombre aurait certainement un prix de départ de pièces de la cinquième dimension.",
            "Comment un citoyen aussi vulgaire que lui-même pourrait-il avoir les qualifications nécessaires pour accéder aux pièces de la cinquième dimension de l’Alliance ?",
            "À ce moment, la silhouette de Li Yunmu est devenue sans vie !"
        ]
        for p in expected:
            assert p in response
