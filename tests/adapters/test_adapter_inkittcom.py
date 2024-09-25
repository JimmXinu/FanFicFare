import pytest

from unittest.mock import patch

from fanficfare.adapters.adapter_inkittcom import InkittComSiteAdapter as inkittcom
from fanficfare.exceptions import FailedToDownload
from fanficfare.epubutils import make_soup

from tests.adapters.generic_adapter_test import GenericAdapterTestExtractChapterUrlsAndMetadata, GenericAdapterTestGetChapterText
from tests.conftest import inkittcom_story_html_return, inkittcom_story_api_return, inkittcom_html_chapter_return, inkittcom_story_patreon_return, inkittcom_story_patreon_api_return, inkittcom_story_not_a_fic_return

SPECIFIC_TEST_DATA = {
    'adapter': inkittcom,
    'url': 'https://www.inkitt.com/stories/drama/1176584',
    'sections': ["www.inkitt.com"],
    'specific_path_adapter': 'adapter_inkittcom.InkittComSiteAdapter',

    'title': 'Finding me',
    'cover_image': 'https://cdn-gcs.inkitt.com/vertical_storycovers/ipad_0b625cc419c6a8b7b59efd6fa28fdc77.jpg',
    'author': 'kyliet',
    'authorId': '3028573',
    'dateUpdated': '2024-09-19',
    'intro': make_soup("""<p class="story-summary">Parker was the only girl in her family. Her mother was convinced she was a boy so had decided her name while she was in the womb. Her mother and her three brothers all called her Parker even before she was born so the name stuck. Parker takes care of her family. She cooks and cleans for her brothers when her parents are off travelling the world. At 18 she has never so much as kissed a boy let alone had a boyfriend. She doesn't have time for it between studying, working and looking after her brothers. She didn't mind, that's what families did apparently. As her graduation draws near her parents and brothers promise to be there. She is excited to finally be finishing high school. She had been accepted to university on the other side of the country but was reluctant to accept because it would mean leaving behind her family. Parker's brothers are working in the family business since there dad retired to travel with there mother. Leon is 26, Jude is 23 and Tanner is 22. They are play boys and are loving life. They have no responsibilitIes at home because Parker takes care of them. They forget all about her graduation until the day after it occurs as do her parents. They vow to make it up to her but when she doesn't come home they know they have made the biggest mistake of there lives. Parker is hurt by her family. Her brothers friend, who had seen everything that had been ha</p>""").p,
    'expected_chapters': {
        0:   {'title': 'Authors note',
              'url': 'https://www.inkitt.com/stories/drama/1176584/chapters/1'},
        10:  {'title': 'Chapter 9',
              'url': 'https://www.inkitt.com/stories/drama/1176584/chapters/11'},
        28: {'title': 'Epilogue',
              'url': 'https://www.inkitt.com/stories/drama/1176584/chapters/29'},
    },
    'list_chapters_fixture': inkittcom_story_html_return,

    'chapter_url': 'https://www.inkitt.com/stories/drama/1176584/chapters/3',
    'expected_sentences': [
        "Parker looked up from her paper and stopped reading.",
        "William reminded himself that tonight was about Parker and making it special for her.",
        "\"Ok Parks, I'm taking you to dinner to celebrate and you are going to tell me about this uni offer\" William said before driving to the restaurant.",
        "William pulled up in front of the bus stop and rolled the window down. \"Little Jones, hop in. I am taking you out to dinner to celebrate\" William called out."
    ],
    'chapter_fixture': inkittcom_html_chapter_return,

    'datePublished': '2024-01-29',
    'status': 'Complete',
    'genre': 'Drama',
    'warnings': 'ableism, assault, child abuse, domestic violence, drug use overdose, racism, suicide',
    'language': 'English',
    'averrating': '4.8',
    'writing_style_rating': '4.6',
    'technical_writing_rating': '4.3',
    'plot_rating': '4.8',
    'storynote': 'This story is unedited and contains racism',
    'rating': '18+'
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

        self.configuration.validEntries.extend(['averrating', 'writing_style_rating', 'technical_writing_rating', 'plot_rating', 'storynote'])

    @pytest.fixture(autouse=True)
    def setup_env(self):
        with patch(f'fanficfare.adapters.{self.path_adapter}.setDescription') as mock_setDescription, \
             patch(f'fanficfare.adapters.{self.path_adapter}.setCoverImage') as mock_setCoverImage, \
             patch(f'fanficfare.adapters.{self.path_adapter}.post_request') as mockpost_request, \
             patch(f'fanficfare.adapters.{self.path_adapter}.get_request') as mockget_request:

            self.mock_setCoverImage = mock_setCoverImage
            self.mock_setDescription = mock_setDescription
            self.mockget_request = mockget_request
            self.mockpost_request = mockpost_request

            self.mockpost_request.return_value = None
            self.mockget_request.side_effect = [inkittcom_story_html_return, inkittcom_story_api_return]

            yield
        
    def test_get_cover_image(self):
        # When
        self.adapter.extractChapterUrlsAndMetadata()

        # Then
        self.mock_setCoverImage.assert_called_with(self.url, self.expected_data['cover_image'])

    def test_get_published_date(self):
        # When
        self.adapter.extractChapterUrlsAndMetadata()

        # Then
        assert self.adapter.story.getMetadata('datePublished') == self.expected_data['datePublished']

    def test_get_status(self):
        # When
        self.adapter.extractChapterUrlsAndMetadata()

        # Then
        assert self.adapter.story.getMetadata('status') == self.expected_data['status']

    def test_get_genre(self):
        # When
        self.adapter.extractChapterUrlsAndMetadata()

        # Then
        assert self.adapter.story.getMetadata('genre') == self.expected_data['genre']

    def test_get_warnings(self):
        # When
        self.adapter.extractChapterUrlsAndMetadata()

        # Then
        assert self.adapter.story.getMetadata('warnings') == self.expected_data['warnings']

    def test_get_language(self):
        # When
        self.adapter.extractChapterUrlsAndMetadata()

        # Then
        assert self.adapter.story.getMetadata('language') == self.expected_data['language']

    def test_get_agerating(self):
        # When
        self.adapter.extractChapterUrlsAndMetadata()

        # Then
        assert self.adapter.story.getMetadata('rating') == self.expected_data['rating']

    def test_get_ratings(self):
        # When
        self.adapter.extractChapterUrlsAndMetadata()

        # Then
        assert self.adapter.story.getMetadata('averrating') == self.expected_data['averrating']
        assert self.adapter.story.getMetadata('writing_style_rating') == self.expected_data['writing_style_rating']
        assert self.adapter.story.getMetadata('technical_writing_rating') == self.expected_data['technical_writing_rating']
        assert self.adapter.story.getMetadata('plot_rating') == self.expected_data['plot_rating']

    def test_get_storynote(self):
        # When
        self.adapter.extractChapterUrlsAndMetadata()

        # Then
        assert self.adapter.story.getMetadata('storynote') == self.expected_data['storynote']

    @patch('fanficfare.adapters.adapter_inkittcom.InkittComSiteAdapter.get_request')
    def test_raises_fic_patreon_exclusive(self, mockget_request):
        # Given
        mockget_request.side_effect = [inkittcom_story_patreon_return, inkittcom_story_patreon_api_return]

        # When
        with pytest.raises(FailedToDownload) as exc_info:
            self.adapter.extractChapterUrlsAndMetadata()

        # Then
        assert str(exc_info.value) == "Downloading books for patrons only is unsupported."

    @patch('fanficfare.adapters.adapter_inkittcom.InkittComSiteAdapter.get_request')
    def test_raises_story_not_fic(self, mockget_request):
        # Given
        mockget_request.return_value = inkittcom_story_not_a_fic_return

        # When
        with pytest.raises(FailedToDownload) as exc_info:
            self.adapter.extractChapterUrlsAndMetadata()

        # Then
        assert str(exc_info.value) == "The book is not considered a fanfiction."
        

class TestGetChapterText(GenericAdapterTestGetChapterText):
    def setup_method(self):
        self.expected_data = SPECIFIC_TEST_DATA

        super().setup_method(
            SPECIFIC_TEST_DATA['adapter'],
            SPECIFIC_TEST_DATA['url'],
            SPECIFIC_TEST_DATA['sections'],
            SPECIFIC_TEST_DATA['specific_path_adapter'],
            SPECIFIC_TEST_DATA['chapter_fixture'])

