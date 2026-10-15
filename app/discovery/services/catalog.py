"""Live provider adapters. Returned dictionaries are transient, never database rows."""
import json
import os
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

TIMEOUT = 10
USER_AGENT = 'FreeLibAI/1.0 (book discovery)'


def safe_url(value, domains):
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    host = (parsed.hostname or '').lower()
    if parsed.scheme != 'https' or parsed.username or parsed.password:
        return None
    if any(host == domain or host.endswith('.' + domain) for domain in domains):
        return value
    return None


def fetch_json(url, headers=None):
    request = Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json', **(headers or {})})
    with urlopen(request, timeout=TIMEOUT) as response:
        data = json.load(response)
    if not isinstance(data, (dict, list)):
        raise ValueError('Invalid provider response')
    return data


def basic_book(identifier, title, authors, source, provider_url, **kwargs):
    if not identifier or not title or not provider_url:
        return None
    return {
        'id': str(identifier), 'title': str(title),
        'authors': [str(a) for a in authors if a], 'source': source,
        'provider_url': provider_url, 'read_url': kwargs.get('read_url'),
        'download_url': kwargs.get('download_url'),
        'cover_url': kwargs.get('cover_url'), 'year': kwargs.get('year'),
        'language': kwargs.get('language'), 'description': kwargs.get('description'),
        'access_status': kwargs.get('access_status', 'unknown'),
        'license': kwargs.get('license'), 'isbn': kwargs.get('isbn'),
        'reason': None,
    }


class OpenLibraryClient:
    name = 'openlibrary'

    def search(self, query, page=1):
        params = urlencode({'q': query, 'limit': 10, 'page': page,
            'fields': 'key,title,author_name,first_publish_year,cover_i,ebook_access,has_fulltext,language,isbn'})
        data = fetch_json('https://openlibrary.org/search.json?' + params)
        if not isinstance(data, dict) or not isinstance(data.get('docs'), list):
            raise ValueError('Invalid Open Library response')
        books = []
        for row in data['docs']:
            key = row.get('key')
            if not isinstance(key, str) or not key.startswith('/works/'):
                continue
            url = safe_url('https://openlibrary.org' + key, ['openlibrary.org'])
            access = row.get('ebook_access')
            books.append(basic_book('ol:' + key, row.get('title'), row.get('author_name') or [],
                'Open Library', url,
                read_url=url if access == 'public' and row.get('has_fulltext') is True else None,
                cover_url=f"https://covers.openlibrary.org/b/id/{row['cover_i']}-M.jpg" if isinstance(row.get('cover_i'), int) else None,
                year=row.get('first_publish_year'),
                language=(row.get('language') or [None])[0],
                access_status='public' if access == 'public' and row.get('has_fulltext') is True else 'unknown',
                isbn=(row.get('isbn') or [None])[0]))
        return [book for book in books if book]


class GutendexClient:
    name = 'gutendex'

    def search(self, query, page=1):
        data = fetch_json('https://gutendex.com/books/?' + urlencode({'search': query, 'page': page}))
        if not isinstance(data, dict) or not isinstance(data.get('results'), list):
            raise ValueError('Invalid Gutendex response')
        books = []
        for row in data['results']:
            identifier = row.get('id')
            if not isinstance(identifier, int) or row.get('copyright') is not False:
                continue
            formats = row.get('formats') or {}
            if not isinstance(formats, dict):
                formats = {}
            download = next((safe_url(v, ['gutenberg.org']) for k, v in formats.items()
                if 'epub' in k and safe_url(v, ['gutenberg.org'])), None)
            url = f'https://www.gutenberg.org/ebooks/{identifier}'
            books.append(basic_book(f'pg:{identifier}', row.get('title'),
                [a.get('name') for a in row.get('authors', []) if isinstance(a, dict)],
                'Project Gutenberg', url, read_url=url, download_url=download,
                cover_url=safe_url(formats.get('image/jpeg'), ['gutenberg.org']),
                language=(row.get('languages') or [None])[0],
                description=(row.get('summaries') or [None])[0],
                access_status='public_domain_us', license='Public domain in the US (Gutendex copyright=false)'))
        return [book for book in books if book]


class GoogleBooksClient:
    name = 'googlebooks'

    def search(self, query, page=1):
        params = {'q': query, 'filter': 'free-ebooks', 'printType': 'books',
                  'maxResults': 10, 'startIndex': (page - 1) * 10}
        if os.environ.get('GOOGLE_BOOKS_API_KEY'):
            params['key'] = os.environ['GOOGLE_BOOKS_API_KEY']
        data = fetch_json('https://www.googleapis.com/books/v1/volumes?' + urlencode(params))
        if not isinstance(data, dict) or not isinstance(data.get('items', []), list):
            raise ValueError('Invalid Google Books response')
        books = []
        for row in data.get('items', []):
            volume = row.get('volumeInfo') or {}
            access = row.get('accessInfo') or {}
            if not isinstance(volume, dict) or not isinstance(access, dict):
                continue
            public = access.get('publicDomain') is True and access.get('viewability') == 'ALL_PAGES'
            if not public:
                continue
            identifier = row.get('id')
            if not isinstance(identifier, str) or not identifier.isalnum():
                continue
            url = safe_url(access.get('webReaderLink'), ['google.com', 'googleapis.com']) or f'https://books.google.com/books?id={identifier}'
            pdf = (access.get('pdf') or {}).get('downloadLink')
            epub = (access.get('epub') or {}).get('downloadLink')
            books.append(basic_book('gb:' + identifier, volume.get('title'), volume.get('authors') or [],
                'Google Books', url, read_url=url,
                download_url=safe_url(epub, ['google.com', 'googleapis.com']) or safe_url(pdf, ['google.com', 'googleapis.com']),
                cover_url=safe_url((volume.get('imageLinks') or {}).get('thumbnail'), ['google.com', 'googleapis.com']),
                year=(volume.get('publishedDate') or '')[:4] or None,
                language=volume.get('language'), description=volume.get('description'),
                access_status='public_domain', license='Public domain in API access country',
                isbn=next((i.get('identifier') for i in volume.get('industryIdentifiers', []) if i.get('type') == 'ISBN_13'), None)))
        return [book for book in books if book]


class DOABClient:
    name = 'doab'

    def search(self, query, page=1):
        params = urlencode({'query': query, 'expand': 'metadata', 'limit': 10, 'offset': (page - 1) * 10})
        data = fetch_json('https://directory.doabooks.org/rest/search?' + params)
        if not isinstance(data, list):
            raise ValueError('Invalid DOAB response')
        books = []
        for row in data:
            if not isinstance(row, dict):
                continue
            fields = {}
            for field in row.get('metadata') or []:
                if isinstance(field, dict) and field.get('key') and field.get('value'):
                    fields.setdefault(field['key'], []).append(field['value'])
            handle = row.get('handle')
            if not handle or not isinstance(handle, str):
                continue
            url = safe_url('https://directory.doabooks.org/handle/' + handle, ['doabooks.org'])
            books.append(basic_book('doab:' + handle, (fields.get('dc.title') or [row.get('name')])[0],
                fields.get('dc.contributor.author') or fields.get('dc.creator') or [],
                'DOAB', url, read_url=url,
                year=(fields.get('dc.date.issued') or [None])[0],
                language=(fields.get('dc.language.iso') or [None])[0],
                description=(fields.get('dc.description.abstract') or [None])[0],
                access_status='open_access_catalog',
                license=(fields.get('dc.rights.uri') or fields.get('dc.rights') or [None])[0],
                isbn=(fields.get('dc.identifier.isbn') or [None])[0]))
        return [book for book in books if book]


CLIENTS = {client.name: client for client in (OpenLibraryClient(), GutendexClient(), GoogleBooksClient(), DOABClient())}
