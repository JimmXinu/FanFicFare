import pytest
from unittest.mock import patch
from fanficfare.configurable import Configuration
from fanficfare import exceptions


class GenericAdapterTestExtractChapterUrlsAndMetadata:
    def setup_method(self, adapter, url, sections, path_adapter, adapter_fixture):
        self.url = url
        self.configuration = Configuration(sections, "EPUB", lightweight=True)
        self.adapter = adapter(self.configuration, self.url)
        self.path_adapter = path_adapter
        self.fixture = adapter_fixture

    @pytest.fixture(autouse=True)
    def setup_env(self):
        with patch(f'fanficfare.adapters.{self.path_adapter}.setDescription') as mock_setDescription, \
             patch(f'fanficfare.adapters.{self.path_adapter}.setCoverImage') as mock_setCoverImage, \
             patch(f'fanficfare.adapters.{self.path_adapter}.get_request') as mockget_request:

            self.mock_setCoverImage = mock_setCoverImage
            self.mock_setDescription = mock_setDescription
            self.mockget_request = mockget_request

            self.mockget_request.return_value = self.fixture

            yield

    def test_get_metadata(self):
        # When
        self.adapter.extractChapterUrlsAndMetadata()

        # Then
        assert self.adapter.story.getMetadata('title') == self.expected_data['title']

    def test_get_cover_image(self):
        # When
        self.adapter.extractChapterUrlsAndMetadata()

        # Then
        self.mock_setCoverImage.assert_called_with(self.url, self.expected_data['cover_image'])

    def test_get_autor(self):
        # When
        self.adapter.extractChapterUrlsAndMetadata()

        # Then
        assert self.adapter.story.getMetadata('author') == self.expected_data['author']
        assert self.adapter.story.getMetadata('authorId') == self.expected_data['authorId']

    def test_get_dateUpdated(self):
        # When
        self.adapter.extractChapterUrlsAndMetadata()

        # Then
        assert self.adapter.story.getMetadata('dateUpdated') == self.expected_data['dateUpdated']

    def test_get_novel_intro(self):
        # When
        self.adapter.extractChapterUrlsAndMetadata()

        # Then
        self.mock_setDescription.assert_called_with(self.url, self.expected_data['intro'])

    def test_get_novel_info(self):
        # When
        self.adapter.extractChapterUrlsAndMetadata()

        # Then
        expected_chapters = self.expected_data['expected_chapters']
        calculated_chapters = self.adapter.get_chapters()
        for num_chapter in expected_chapters:
            assert calculated_chapters[num_chapter]['title'] == expected_chapters[num_chapter]['title']
            assert calculated_chapters[num_chapter]['url'] == expected_chapters[num_chapter]['url']


class GenericAdapterTestGetChapterText:
    def setup_method(self, adapter, url, sections, path_adapter, adapter_fixture):
        self.url = url
        self.configuration = Configuration(sections, "EPUB", lightweight=True)
        self.adapter = adapter(self.configuration, self.url)
        self.path_adapter = path_adapter
        self.fixture = adapter_fixture

    @pytest.fixture(autouse=True)
    def setup_env(self):
        with patch(f'fanficfare.adapters.{self.path_adapter}.setDescription') as mock_setDescription, \
             patch(f'fanficfare.adapters.{self.path_adapter}.setCoverImage') as mock_setCoverImage, \
             patch(f'fanficfare.adapters.{self.path_adapter}.get_request') as mockget_request:

            mockget_request.return_value = self.fixture

            yield

    def test_get_metadata(self):
        # When
        response = self.adapter.getChapterText(self.expected_data['chapter_url'])

        # Then
        for p in self.expected_data['expected_sentences']:
            assert p in response
