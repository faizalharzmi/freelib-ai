import xml.etree.ElementTree as ET
from discovery.services.gutenberg import GutenbergProvider
from unittest.mock import patch
from django.test import TestCase
from unittest.mock import MagicMock
from discovery.services.googlebooks import GoogleBooksProvider
from unittest.mock import Mock
from discovery.services.aggregator import SearchAggregator
from urllib.error import HTTPError, URLError

class BookSearchTests(TestCase):

    def test_search_requires_query(self):
        response = self.client.get("/api/books/")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            "Search query is required"
        )

    def test_invalid_page(self):
        response = self.client.get(
            "/api/books/",
            {"q": "python", "page": 0}
        )

        self.assertEqual(response.status_code, 400)

    @patch("discovery.views.OpenLibraryProvider")

    def test_public_book_search(self, mock_search):

        mock_search.return_value.search.return_value  = {
            "query": "python",
            "total": 1,
            "returned_count": 1,
            "books": [
                {
                    "id": "/works/OL123W",
                    "title": "Python Programming",
                    "authors": ["Test Author"],
                    "ebook_access": "public",
                    "source": "Open Library",
                }
            ],
        }

        response = self.client.get(
            "/api/books/",
            {
                "q": "python",
                "access": "public",
                "page": 1,
            }
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data["query"], "python")
        self.assertEqual(data["returned_count"], 1)
        self.assertEqual(
            data["books"][0]["ebook_access"],
            "public"
        )

        mock_search.return_value.search.assert_called_once_with(
            "python",
            "public",
            1
        )

    @patch("discovery.views.SearchAggregator")
    def test_multi_library_search(self, mock_aggregator):

        mock_aggregator.return_value.search.return_value = {
            "query": "python",
            "total": None,
            "returned_count": 3,
            "books": [
                {
                    "id": "ol-123",
                    "source": "Open Library",
                },
                {
                    "id": "google-456",
                    "source": "Google Books",
                },
                {
                    "id": "gutenberg-789",
                    "source": "Project Gutenberg",
                },
            ],
        }

        response = self.client.get(
            "/api/books/",
            {
                "q": "python",
                "access": "public",
                "source": "all",
                "page": 1,
            }
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data["returned_count"], 3)
        self.assertIsNone(data["total"])

        mock_aggregator.return_value.search.assert_called_once_with(
            "python", "public", 1
        )

class GoogleBooksProviderTests(TestCase):

    @patch("discovery.services.googlebooks.urlopen")
    def test_public_book_search(self, mock_urlopen):

        import io
        import json

        api_response = {
            "totalItems": 1,
            "items": [
                {
                    "id": "book123",
                    "volumeInfo": {
                        "title": "Python Programming",
                        "authors": ["Example Author"],
                        "publishedDate": "2020",
                    },
                    "accessInfo": {
                        "publicDomain": True,
                        "viewability": "ALL_PAGES",
                    },
                }
            ],
        }

        mock_urlopen.return_value.__enter__.return_value = (
            io.BytesIO(json.dumps(api_response).encode())
        )

        with patch.dict(
            "os.environ",
            {"GOOGLE_BOOKS_API_KEY": "test-key"}
        ):
            result = GoogleBooksProvider().search(
                "python", "public", 1
            )

        self.assertEqual(result["returned_count"], 1)
        self.assertEqual(result["books"][0]["source"], "Google Books")
        self.assertEqual(result["books"][0]["ebook_access"], "public")

    @patch("discovery.services.googlebooks.urlopen")
    def test_non_public_book_filtered(self, mock_urlopen):

        import io
        import json

        api_response = {
            "totalItems": 1,
            "items": [
                {
                    "id": "book456",
                    "volumeInfo": {"title": "Restricted Book"},
                    "accessInfo": {
                        "publicDomain": False,
                        "viewability": "ALL_PAGES",
                    },
                }
            ],
        }

        mock_urlopen.return_value.__enter__.return_value = (
            io.BytesIO(json.dumps(api_response).encode())
        )

        with patch.dict(
            "os.environ",
            {"GOOGLE_BOOKS_API_KEY": "test-key"}
        ):
            result = GoogleBooksProvider().search(
                "python", "public", 1
            )

        self.assertEqual(result["returned_count"], 0)

    @patch("discovery.services.googlebooks.urlopen")
    def test_pagination(self, mock_urlopen):

        import io
        import json
        from urllib.parse import parse_qs, urlparse

        mock_urlopen.return_value.__enter__.return_value = (
            io.BytesIO(json.dumps({"totalItems": 0, "items": []}).encode())
        )

        with patch.dict(
            "os.environ",
            {"GOOGLE_BOOKS_API_KEY": "test-key"}
        ):
            GoogleBooksProvider().search("python", "public", 2)

        requested_url = mock_urlopen.call_args.args[0]
        params = parse_qs(urlparse(requested_url).query)

        self.assertEqual(params["startIndex"], ["10"])
        self.assertEqual(params["maxResults"], ["10"])

class GutenbergProviderTests(TestCase):

    @patch("discovery.services.gutenberg.fetch_xml")
    def test_gutenberg_search(self, mock_fetch):

        search_xml = """
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>Subjects</title>
                <id>
                    https://www.gutenberg.org/ebooks/subjects/search.opds/
                </id>
            </entry>
            <entry>
                <title>The Adventures of Sherlock Holmes</title>
                <id>https://www.gutenberg.org/ebooks/1661.opds</id>
            </entry>
        </feed>
        """

        detail_xml = """
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <id>urn:gutenberg:1661:2</id>
                <title>The Adventures of Sherlock Holmes</title>
                <author>
                    <name>Doyle, Arthur Conan</name>
                </author>
                <link
                    rel="http://opds-spec.org/acquisition"
                    type="application/epub+zip"
                    href="/ebooks/1661.epub"
                />
            </entry>
        </feed>
        """

        mock_fetch.side_effect = [
            ET.fromstring(search_xml),
            ET.fromstring(detail_xml),
        ]

        result = GutenbergProvider().search(
            "sherlock holmes",
            "public",
            1
        )

        self.assertEqual(result["returned_count"], 1)

        book = result["books"][0]

        self.assertEqual(book["id"], "gutenberg-1661")
        self.assertEqual(
            book["title"],
            "The Adventures of Sherlock Holmes"
        )
        self.assertEqual(
            book["authors"],
            ["Doyle, Arthur Conan"]
        )
        self.assertTrue(book["has_fulltext"])

        self.assertEqual(mock_fetch.call_count, 2)

    @patch("discovery.services.gutenberg.fetch_xml")
    def test_empty_search_results(self, mock_fetch):

        mock_fetch.return_value = ET.fromstring(
            '<feed xmlns="http://www.w3.org/2005/Atom"/>'
        )

        result = GutenbergProvider().search(
            "unknown book",
            "public",
            1
        )

        self.assertEqual(result["returned_count"], 0)
        self.assertEqual(result["books"], [])
        self.assertIsNone(result["total"])

class SearchAggregatorTests(TestCase):

    def test_combine_three_providers(self):

        books = [
            {
                "id": "ol-123",
                "title": "Think Python",
                "authors": ["Allen Downey"],
                "source": "Open Library",
            },
            {
                "id": "google-456",
                "title": "Python Programming",
                "authors": ["John Smith"],
                "source": "Google Books",
            },
            {
                "id": "gutenberg-789",
                "title": "Learning Python",
                "authors": ["Jane Doe"],
                "source": "Project Gutenberg",
            },
        ]

        providers = []

        for book in books:
            provider = Mock()

            provider.search.return_value = {
                "query": "python",
                "total": 10,
                "returned_count": 1,
                "books": [book],
            }

            providers.append(provider)

        aggregator = SearchAggregator(providers)

        result = aggregator.search("python", "public", 1)

        self.assertEqual(result["total"], 30)
        self.assertEqual(result["returned_count"], 3)

        self.assertEqual(
            [book["source"] for book in result["books"]],
            [
                "Open Library",
                "Google Books",
                "Project Gutenberg",
            ]
        )

        for provider in providers:
            provider.search.assert_called_once_with(
                "python", "public", 1
            )

    def test_unknown_provider_total(self):

        provider = Mock()

        provider.search.return_value = {
            "query": "python",
            "total": None,
            "returned_count": 1,
            "books": [
                {
                    "id": "gutenberg-123",
                    "title": "Python Programming",
                    "source": "Project Gutenberg",
                }
            ],
        }

        aggregator = SearchAggregator([provider])

        result = aggregator.search("python", "public", 1)

        self.assertIsNone(result["total"])
        self.assertEqual(result["returned_count"], 1)

    def test_partial_provider_failure(self):

        working = Mock()
        working.search.return_value = {
            "query": "python",
            "total": 10,
            "returned_count": 1,
            "books": [
                {
                    "id": "ol-123",
                    "title": "Think Python",
                    "source": "Open Library",
                }
            ],
        }

        failing = Mock()
        failing.search.side_effect = HTTPError(
            url="https://example.com",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=None,
        )

        aggregator = SearchAggregator([working, failing])

        result = aggregator.search("python", "public", 1)

        self.assertEqual(result["returned_count"], 1)
        self.assertIsNone(result["total"])

        working.search.assert_called_once()
        failing.search.assert_called_once()

    def test_all_providers_failed(self):

        first = Mock()
        first.search.side_effect = URLError("Unavailable")

        second = Mock()
        second.search.side_effect = URLError("Unavailable")

        aggregator = SearchAggregator([first, second])

        with self.assertRaises(URLError):
            aggregator.search("python", "public", 1)

    def test_duplicate_books_removed(self):

        first = Mock()
        first.search.return_value = {
            "query": "sherlock",
            "total": 1,
            "books": [
                {
                    "id": "ol-123",
                    "title": "The Hound of the Baskervilles",
                    "authors": ["Arthur Conan Doyle"],
                    "source": "Open Library",
                }
            ],
        }

        second = Mock()
        second.search.return_value = {
            "query": "sherlock",
            "total": 1,
            "books": [
                {
                    "id": "google-456",
                    "title": "The Hound of the Baskervilles",
                    "authors": ["Arthur Conan Doyle"],
                    "source": "Google Books",
                }
            ],
        }

        aggregator = SearchAggregator([first, second])

        result = aggregator.search("sherlock", "public", 1)

        self.assertEqual(result["returned_count"], 1)
        self.assertEqual(result["books"][0]["id"], "ol-123")

    def test_author_name_format_deduplication(self):

        first = Mock()
        first.search.return_value = {
            "query": "sherlock",
            "total": 1,
            "books": [
                {
                    "id": "ol-123",
                    "title": "A Study in Scarlet",
                    "authors": ["Arthur Conan Doyle"],
                    "source": "Open Library",
                }
            ],
        }

        second = Mock()
        second.search.return_value = {
            "query": "sherlock",
            "total": 1,
            "books": [
                {
                    "id": "gutenberg-244",
                    "title": "A Study in Scarlet",
                    "authors": ["Doyle, Arthur Conan"],
                    "source": "Project Gutenberg",
                }
            ],
        }

        aggregator = SearchAggregator([first, second])

        result = aggregator.search("sherlock", "public", 1)

        self.assertEqual(result["returned_count"], 1)
        self.assertEqual(result["books"][0]["id"], "ol-123")