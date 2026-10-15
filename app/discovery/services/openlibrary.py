import json
from urllib.parse import urlencode
from urllib.request import urlopen


def normalize_book(book):
    """
    Convert Open Library book to FreeLib AI format.
    """

    cover_id = book.get("cover_i")

    return {
        "id": book.get("key"),
        "title": book.get("title"),
        "authors": book.get("author_name", []),
        "year": book.get("first_publish_year"),
        "cover_url": (
            f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
            if cover_id else None
        ),
        "source": "Open Library",
        "book_url": (
            f"https://openlibrary.org{book['key']}"
            if book.get("key") else None
        ),
        "ebook_access": book.get("ebook_access"),
        "has_fulltext": book.get("has_fulltext", False),
    }


def search_books(query, access, page):
    """
    Search and normalize books from Open Library.
    """

    search_query = query

    if access == "public":
        search_query = f"({query}) AND ebook_access:public"

    params = urlencode({
        "q": search_query,
        "limit": 10,
        "page": page,
        "fields": (
            "key,title,author_name,cover_i,"
            "first_publish_year,ebook_access,has_fulltext"
        ),
    })

    url = f"https://openlibrary.org/search.json?{params}"

    with urlopen(url, timeout=15) as response:
        data = json.load(response)

    books = []

    for book in data.get("docs", []):
        if access == "public" and book.get("ebook_access") != "public":
            continue

        books.append(normalize_book(book))

    return {
        "query": query,
        "total": data.get("numFound", 0),
        "returned_count": len(books),
        "books": books,
    }

class OpenLibraryProvider:
    """
    Open Library implementation of BookProvider.
    """

    def search(
        self,
        query: str,
        access: str,
        page: int
    ) -> dict:
        return search_books(query, access, page)