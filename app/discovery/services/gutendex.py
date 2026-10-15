import json
from urllib.parse import urlencode
from urllib.request import urlopen


def normalize_book(book):
    """
    Convert Gutendex book into FreeLib AI format.
    """

    book_id = book.get("id")
    formats = book.get("formats") or {}

    has_fulltext = any(
        mime.startswith("text/") or "epub" in mime
        for mime in formats
    )

    return {
        "id": f"gutenberg-{book_id}",
        "title": book.get("title"),
        "authors": [
            author.get("name")
            for author in book.get("authors", [])
        ],
        "year": None,
        "cover_url": formats.get("image/jpeg"),
        "source": "Project Gutenberg",
        "book_url": (
            f"https://www.gutenberg.org/ebooks/{book_id}"
            if book_id is not None else None
        ),
        "ebook_access": "public",
        "has_fulltext": has_fulltext,
    }


class GutendexProvider:

    def search(
        self,
        query: str,
        access: str,
        page: int
    ) -> dict:

        params = urlencode({
            "search": query,
            "page": page,
        })

        url = f"https://gutendex.com/books?{params}"

        with urlopen(url, timeout=15) as response:
            data = json.load(response)

        books = []

        for book in data.get("results", []):

            # Restrict to books marked public domain in the US.
            if book.get("copyright") is not False:
                continue

            books.append(normalize_book(book))

        return {
            "query": query,
            "total": data.get("count", 0),
            "returned_count": len(books),
            "books": books,
        }