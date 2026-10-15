from urllib.error import URLError, HTTPError

from django.http import JsonResponse

from discovery.services.openlibrary import OpenLibraryProvider
from discovery.services.googlebooks import GoogleBooksProvider
from discovery.services.gutenberg import GutenbergProvider
from discovery.services.aggregator import SearchAggregator


def search_books(request):

    query = request.GET.get("q", "").strip()
    access = request.GET.get("access", "").strip().lower()
    source = request.GET.get("source", "openlibrary").strip().lower()

    # Validate pagination
    try:
        page = int(request.GET.get("page", "1"))

        if page < 1 or page > 100:
            raise ValueError

    except ValueError:
        return JsonResponse(
            {"error": "Page must be between 1 and 100"},
            status=400
        )

    # Validate query
    if not query:
        return JsonResponse(
            {"error": "Search query is required"},
            status=400
        )

    if len(query) > 200:
        return JsonResponse(
            {"error": "Search query is too long"},
            status=400
        )

    # Validate source
    if source not in ("openlibrary", "all"):
        return JsonResponse(
            {"error": "Invalid search source"},
            status=400
        )

    # Select provider
    if source == "all":

        provider = SearchAggregator([
            OpenLibraryProvider(),
            GoogleBooksProvider(),
            GutenbergProvider(),
        ])

    else:
        provider = OpenLibraryProvider()

    # Execute search
    try:
        result = provider.search(query, access, page)

    except (URLError, HTTPError, TimeoutError, ValueError):
        return JsonResponse(
            {
                "error": (
                    "Book search providers unavailable"
                    if source == "all"
                    else "Open Library unavailable"
                )
            },
            status=502
        )

    return JsonResponse(result)