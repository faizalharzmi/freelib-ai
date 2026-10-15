import json
import os

from urllib.parse import urlencode
from urllib.request import urlopen


def normalize_book(book):
    """
    Convert Google Books volume into FreeLib AI format.
    """

    volume = book.get("volumeInfo") or {}
    access = book.get("accessInfo") or {}
    images = volume.get("imageLinks") or {}

    book_id = book.get("id")
    published_date = volume.get("publishedDate", "")

    return {
        "id": f"google-{book_id}",
        "title": volume.get("title"),
        "authors": volume.get("authors", []),
        "year": (
            published_date[:4]
            if published_date else None
        ),
        "cover_url": images.get("thumbnail"),
        "source": "Google Books",
        "book_url": (
            access.get("webReaderLink")
            or volume.get("infoLink")
        ),
        "ebook_access": (
            "public"
            if access.get("publicDomain") is True
            else "free"
        ),
        "has_fulltext": (
            access.get("viewability") == "ALL_PAGES"
        ),
    }


class GoogleBooksProvider:
    """
    Google Books implementation of BookProvider.
    """

    def search(
        self,
        query: str,
        access: str,
        page: int
    ) -> dict:

        api_key = os.environ["GOOGLE_BOOKS_API_KEY"]

        params = urlencode({
            "q": query,
            "filter": "free-ebooks",
            "printType": "books",
            "maxResults": 10,
            "startIndex": (page - 1) * 10,
            "key": api_key,
        })

        url = f"https://www.googleapis.com/books/v1/volumes?{params}"

        with urlopen(url, timeout=15) as response:
            data = json.load(response)

        books = []

        for book in data.get("items", []):
            access_info = book.get("accessInfo") or {}

            # Match existing public-access filter semantics
            if access == "public":
                if access_info.get("publicDomain") is not True:
                    continue

            # Only include fully viewable volumes
            if access_info.get("viewability") != "ALL_PAGES":
                continue

            books.append(normalize_book(book))

        return {
            "query": query,
            "total": data.get("totalItems", 0),
            "returned_count": len(books),
            "books": books,
        }