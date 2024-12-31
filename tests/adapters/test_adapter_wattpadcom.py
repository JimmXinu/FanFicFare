import pytest
from unittest.mock import patch
from fanficfare.exceptions import HTTPErrorFFF

from fanficfare.adapters.adapter_wattpadcom import WattpadComAdapter as wattpadcom
from tests.adapters.generic_adapter_test import GenericAdapterTestExtractChapterUrlsAndMetadata, GenericAdapterTestGetChapterText
from tests.conftest import wattpadcom_api_story_return, wattpadcom_api_chapter_return, wattpadcom_api_getcategories_return

SPECIFIC_TEST_DATA = {
    'adapter': wattpadcom,
    'url': 'https://www.wattpad.com/story/173080052-the-kids-aren%27t-alright',
    'sections': ["wattpad.com"],
    'specific_path_adapter': 'adapter_wattpadcom.WattpadComAdapter',

    'title': 'The Kids Aren\'t Alright',
    'cover_image': 'https://img.wattpad.com/cover/173080052-512-k768737.jpg',
    'author': 'bee_mcd',
    'authorId': 'bee_mcd',
    'datePublished': '2019-01-02',
    'dateUpdated': '2024-01-22',
    'intro': "The year is 1988, and Finn, Ronan, Becca and Jasper are spending the summer at a reformatory camp located deep in the Alaskan wilderness. The camp, named Lightlake, is the last chance the teens have to get their lives back on track, but changing for the better isn't easy - and especially not at a place like Lightlake, where secrets outnumber the campers and myths have a way of coming to life.\n\nThis story is now free on Wattpad. \n\n[[word count: 200,000-250,000 words]]",
    'expected_chapters': {
        0:   {'title': 'Chapter 1: Finn',
              'url': 'https://www.wattpad.com/675342676-the-kids-aren%27t-alright-chapter-1-finn',
              'date': '2019-01-02 03:02:00'},
        10:  {'title': 'Chapter 11: Jasper',
              'url': 'https://www.wattpad.com/675347689-the-kids-aren%27t-alright-chapter-11-jasper'},
        76: {'title': 'Sneak Peak of Book #2, "Kids These Days"',
              'url': 'https://www.wattpad.com/807690860-the-kids-aren%27t-alright-sneak-peak-of-book-2-kids'},
    },
    'list_chapters_fixture': wattpadcom_api_story_return,

    'chapter_url': 'https://www.wattpad.com/675344459-the-kids-aren%27t-alright-chapter-3-ronan',
    'expected_sentences': [
        "We end up stopping at a newspaper stand a few blocks away.",
        "\"We can go somewhere else if it bothers you so much. I'll call a cab.\"",
        "\"I'll see you tomorrow,\" I say to him as he climbs the stairs to the front door. \"We can catch a Mets game—\""
    ],
    'chapter_fixture': wattpadcom_api_chapter_return,

    'status': 'Completed',
    'category': 'Teen Fiction',
    'genre': '80s, adventure, alaska, camps, comedy, drama, foundfamily, friends, humor, lake, lgbt, magic, mystery, myth, novel, psychic, retro, summer, summercamp, teen, teenfiction, texttospeech, wilderness, youngadult, yukon',
    'language': 'English',
    'rating': '',
    'reads': '1206132',
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

        self.configuration.validEntries.extend(['reads'])

    @pytest.fixture(autouse=True)
    def setup_env(self):
        with patch(f'fanficfare.adapters.{self.path_adapter}.setDescription') as mock_setDescription, \
             patch(f'fanficfare.adapters.{self.path_adapter}.setCoverImage') as mock_setCoverImage, \
             patch(f'fanficfare.adapters.{self.path_adapter}.get_request') as mockget_request:

            self.mock_setCoverImage = mock_setCoverImage
            self.mock_setDescription = mock_setDescription
            self.mockget_request = mockget_request

            if wattpadcom.CATEGORY_DEFs == None:
                self.mockget_request.side_effect = [wattpadcom_api_getcategories_return, self.fixture]
            else:
                self.mockget_request.return_value = self.fixture

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
        assert self.adapter.story.getMetadata('reads') == self.expected_data['reads']

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

    def test_get_agerating(self):
        # When
        self.adapter.extractChapterUrlsAndMetadata()

        # Then
        assert self.adapter.story.getMetadata('category') == self.expected_data['category']

    @patch('fanficfare.adapters.adapter_wattpadcom.WattpadComAdapter.get_request')
    def test_get_category_when_req_fails(self, mockget_request):
        # Given
        mockget_request.side_effect = [HTTPErrorFFF(self.expected_data['url'], 403, 'Client Error'), wattpadcom_api_story_return]
        wattpadcom.CATEGORY_DEFs = None

        # When
        self.adapter.extractChapterUrlsAndMetadata()

        # Then
        assert self.adapter.story.getMetadata('category') == self.expected_data['category']


class TestGetChapterText(GenericAdapterTestGetChapterText):
    def setup_method(self):
        self.expected_data = SPECIFIC_TEST_DATA

        super().setup_method(
            SPECIFIC_TEST_DATA['adapter'],
            SPECIFIC_TEST_DATA['url'],
            SPECIFIC_TEST_DATA['sections'],
            SPECIFIC_TEST_DATA['specific_path_adapter'],
            SPECIFIC_TEST_DATA['chapter_fixture'])

    @pytest.fixture(autouse=True)
    def setup_env(self):
        with patch(f'fanficfare.adapters.{self.path_adapter}.setDescription') as mock_setDescription, \
             patch(f'fanficfare.adapters.{self.path_adapter}.setCoverImage') as mock_setCoverImage, \
             patch(f'fanficfare.adapters.{self.path_adapter}.get_request') as mockget_request:

            mockget_request.side_effect = [wattpadcom_api_story_return, self.fixture]

            yield

    def test_get_metadata(self):
        # When
        self.adapter.extractChapterUrlsAndMetadata()
        response = self.adapter.getChapterText(self.expected_data['chapter_url'])

        # Then
        for p in self.expected_data['expected_sentences']:
            assert p in response
