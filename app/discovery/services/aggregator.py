import json
import re
import socket
import unicodedata

from typing import Any
from urllib.error import HTTPError, URLError

from discovery.services.provider import BookProvider


def normalize_text(value: str) -> str:
    """
    Normalize text for deterministic comparison.
    """

    value = unicodedata.normalize("NFKD", value.casefold())

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = re.sub(r"[^a-z0-9]+", " ", value)

    return " ".join(value.split())

def normalize_author(name: str) -> str:
    """
    Normalize author names for deterministic matching.

    Examples:
        Doyle, Arthur Conan -> arthur conan doyle
        Arthur Conan Doyle -> arthur conan doyle
    """

    if "," in name:
        parts = name.split(",", 1)

        if len(parts) == 2:
            surname = parts[0].strip()
            given_names = parts[1].strip()

            name = f"{given_names} {surname}"

    return normalize_text(name)

def book_identity(book: dict) -> tuple:
    """
    Generate a unique book identity using title and author.
    """

    title = normalize_text(book.get("title") or "")

    authors = book.get("authors") or []

    author = normalize_author(authors[0]) if authors else ""

    return (title, author)


class SearchAggregator:
    """
    Combine results from multiple book providers.

    Features:
    - Multi-provider search
    - External API failure handling
    - Cross-provider deduplication
    """

    def __init__(self, providers: list[BookProvider]):
        self.providers = providers

    def search(
        self,
        query: str,
        access: str,
        page: int,
    ) -> dict[str, Any]:

        books = []
        seen_books = set()

        total = 0
        total_known = True

        successful_providers = 0
        failed_providers = 0

        # Search each configured provider
        for provider in self.providers:

            try:
                result = provider.search(
                    query,
                    access,
                    page
                )

            except (
                HTTPError,
                URLError,
                TimeoutError,
                socket.timeout,
                json.JSONDecodeError,
            ):
                failed_providers += 1
                continue

            successful_providers += 1

            # Deduplicate books across providers
            for book in result["books"]:

                identity = book_identity(book)

                if identity in seen_books:
                    continue

                seen_books.add(identity)
                books.append(book)

            # Calculate total matches
            provider_total = result.get("total")

            if provider_total is None:
                total_known = False
            else:
                total += provider_total

        # All providers unavailable
        if successful_providers == 0:
            raise URLError(
                "All book providers unavailable"
            )

        return {
            "query": query,
            "total": (
                total
                if total_known and failed_providers == 0
                else None
            ),
            "returned_count": len(books),
            "books": books,
        }
