import xml.etree.ElementTree as ET

from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


BASE_URL = "https://www.gutenberg.org"

USER_AGENT = (
    "FreeLibAI/0.1 "
    "(+mailto:faizal.harzmi@gmail.com)"
)

NS = {
    "atom": "http://www.w3.org/2005/Atom",
}


def fetch_xml(url):
    """
    Fetch and parse Gutenberg OPDS XML.
    """

    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/atom+xml",
        }
    )

    with urlopen(request, timeout=15) as response:
        return ET.fromstring(response.read())


def get_book_id(opds_url):
    """
    Extract Gutenberg book ID from OPDS URL.
    """

    filename = opds_url.rstrip("/").split("/")[-1]

    if not filename.endswith(".opds"):
        return None

    book_id = filename.removesuffix(".opds")

    return book_id if book_id.isdigit() else None


def normalize_book(book_id, root):
    """
    Convert Gutenberg OPDS book into FreeLib AI format.
    """

    entries = root.findall("atom:entry", NS)

    if not entries:
        return None

    # Multiple OPDS entries may represent the same book.
    entry = entries[0]

    title = entry.findtext(
        "atom:title",
        namespaces=NS
    )

    authors = []

    for author in entry.findall("atom:author", NS):
        name = author.findtext("atom:name", namespaces=NS)

        if name and name not in authors:
            authors.append(name)

    cover_url = None
    has_fulltext = False

    for item in entries:

        for link in item.findall("atom:link", NS):

            rel = link.get("rel", "")
            mime = link.get("type", "")
            href = link.get("href")

            if not href:
                continue

            if rel == "http://opds-spec.org/image/thumbnail":
                cover_url = urljoin(BASE_URL, href)

            if (
                rel == "http://opds-spec.org/acquisition"
                and mime == "application/epub+zip"
            ):
                has_fulltext = True

    return {
        "id": f"gutenberg-{book_id}",
        "title": title,
        "authors": authors,
        "year": None,
        "cover_url": cover_url,
        "source": "Project Gutenberg",
        "book_url": f"{BASE_URL}/ebooks/{book_id}",
        "ebook_access": "public",
        "has_fulltext": has_fulltext,
    }


class GutenbergProvider:

    def search(
        self,
        query: str,
        access: str,
        page: int
    ) -> dict:

        # The observed OPDS search page contains 26 entries.
        page_size = 26

        params = urlencode({
            "query": query,
            "start_index": (page - 1) * page_size,
        })

        url = (
            f"{BASE_URL}/ebooks/search.opds/"
            f"?{params}"
        )

        root = fetch_xml(url)

        books = []
        seen_ids = set()

        for entry in root.findall("atom:entry", NS):

            opds_url = entry.findtext(
                "atom:id",
                namespaces=NS
            )

            if not opds_url:
                continue

            book_id = get_book_id(opds_url)

            # Skip catalog entries such as Subjects.
            if not book_id:
                continue

            if book_id in seen_ids:
                continue

            detail_root = fetch_xml(opds_url)

            book = normalize_book(book_id, detail_root)

            if not book:
                continue

            if not book["has_fulltext"]:
                continue

            seen_ids.add(book_id)
            books.append(book)

            # Limit normalized results per request.
            if len(books) >= 10:
                break

        return {
            "query": query,
            "total": None,
            "returned_count": len(books),
            "books": books,
        }