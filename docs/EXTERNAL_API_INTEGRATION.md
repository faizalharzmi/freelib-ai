# External book APIs

`catalog.py` has one client per source. All use 10-second HTTP timeouts and normalized transient dictionaries.

- Open Library: `/search.json`; `ebook_access=public` plus `has_fulltext=true` allows a provider reading link. It does not imply a verified download.
- Gutendex: `/books/`; only `copyright=false` records are included, explicitly labeled public domain in the US. EPUB links from Gutenberg domains are surfaced when present.
- Google Books: Books v1 volumes; only `publicDomain=true` and `viewability=ALL_PAGES` are included. Download links require the API's EPUB/PDF download URL. Country-dependent access remains labeled.
- DOAB: documented `/rest/search` endpoint with `expand=metadata`; the DOAB record link is supplied, but a direct download is not claimed from metadata alone. The endpoint returned 403 from both the Mac and production server on 15 October 2026. This provider is reported as failed while successful providers still return results.

The official interfaces are [Open Library Search](https://openlibrary.org/dev/docs/api/search), [Gutendex API](https://github.com/garethbjohnson/gutendex/blob/master/readme.md), [Google Books volumes](https://developers.google.com/books/docs/v1/reference/volumes), and [DOAB search](https://www.doabooks.org/en/article/api-search-doab).
