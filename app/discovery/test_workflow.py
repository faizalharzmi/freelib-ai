from unittest.mock import patch
from django.test import TestCase
from discovery.ai.cerdaslab_client import AIServiceError
from discovery.ai.workflow import SEARCH_GRAPH
from discovery.ai.relevance import filter_relevant_books
from discovery.services.catalog import DOABClient, GoogleBooksClient, GutendexClient, OpenLibraryClient, safe_url
from analytics.models import AIExecutionLog, ProviderRequestLog, SearchLog
from django.contrib.auth import get_user_model
from io import BytesIO
import json


BOOK = {'id': 'pg:1', 'title': 'Practical Python', 'authors': ['A. Writer'],
        'source': 'Project Gutenberg', 'provider_url': 'https://www.gutenberg.org/ebooks/1',
        'read_url': 'https://www.gutenberg.org/ebooks/1', 'download_url': None,
        'cover_url': None, 'year': None, 'language': 'en',
        'description': 'Practical exercises for beginners', 'access_status': 'public_domain_us',
        'license': 'Public domain in the US', 'isbn': None, 'reason': None}


class WorkflowTests(TestCase):
    def test_ai_governance_search_excludes_unrelated_provider_hits(self):
        titles = [
            'AI Governance', 'Oxford Handbook of AI Governance',
            'Regulatory Challenges of AI Governance in the Era of ChatGPT',
            'Scaling AI', 'The English Hymnal',
            'Department of the Interior and Related Agencies Appropriations for Fiscal Year 1994',
        ]
        books = [dict(BOOK, id=str(i), title=title, description=None) for i, title in enumerate(titles)]
        filtered = filter_relevant_books('AI governance', {'topic': 'AI governance'}, books)
        self.assertEqual([book['title'] for book in filtered], titles[:3])

    @patch('discovery.ai.workflow.CLIENTS')
    @patch('discovery.ai.workflow.CerdasLabClient.complete_json')
    def test_unrelated_provider_hit_never_reaches_results(self, ai, clients):
        relevant = dict(BOOK, id='ol:1', title='AI Governance', description=None)
        unrelated = dict(BOOK, id='gb:1', title='The English Hymnal', description=None)
        ai.side_effect = [
            {'intent': {'topic': 'AI governance', 'level': None, 'language': None,
                        'book_type': None, 'access': None},
             'search_terms': ['AI governance'], 'providers': ['openlibrary']},
            {'recommendations': [{'id': 'gb:1', 'evidence': 'The English Hymnal'},
                                 {'id': 'ol:1', 'evidence': 'AI Governance'}]},
        ]
        clients.__contains__.return_value = True
        clients.__getitem__.return_value.search.return_value = [relevant, unrelated]
        result = SEARCH_GRAPH.invoke({'query': 'AI governance', 'page': 1})
        self.assertEqual([book['title'] for book in result['books']], ['AI Governance'])

    @patch('discovery.ai.workflow.CLIENTS')
    @patch('discovery.ai.workflow.CerdasLabClient.complete_json')
    def test_graph_only_ranks_retrieved_book(self, ai, clients):
        ai.side_effect = [
            {'intent': {'topic': 'Python', 'level': 'beginner', 'language': None,
                        'book_type': None, 'access': None},
             'search_terms': ['Python'], 'providers': ['gutendex']},
            {'recommendations': [{'id': 'pg:1', 'evidence': 'Practical Python'}]},
        ]
        clients.__contains__.return_value = True
        clients.__getitem__.return_value.search.return_value = [BOOK]
        result = SEARCH_GRAPH.invoke({'query': 'beginner Python', 'page': 1})
        self.assertEqual([b['id'] for b in result['books']], ['pg:1'])
        self.assertIn('Practical Python', result['books'][0]['reason'])
        self.assertEqual(ai.call_count, 2)
        self.assertEqual(ProviderRequestLog.objects.count(), 1)

    @patch('discovery.ai.workflow.CLIENTS')
    @patch('discovery.ai.workflow.CerdasLabClient.complete_json')
    def test_hallucinated_id_is_rejected(self, ai, clients):
        ai.side_effect = [
            {'intent': {'topic': 'Python', 'level': None, 'language': None,
                        'book_type': None, 'access': None},
             'search_terms': ['Python'], 'providers': ['gutendex']},
            {'recommendations': [{'id': 'made-up', 'evidence': 'Practical Python'}]},
        ]
        clients.__contains__.return_value = True
        clients.__getitem__.return_value.search.return_value = [BOOK]
        with self.assertRaises(AIServiceError):
            SEARCH_GRAPH.invoke({'query': 'Python', 'page': 1})

    @patch('discovery.ai.workflow.CLIENTS')
    @patch('discovery.ai.workflow.CerdasLabClient.complete_json')
    def test_ungrounded_ai_evidence_uses_exact_provider_title(self, ai, clients):
        ai.side_effect = [
            {'intent': {'topic': 'Python', 'level': None, 'language': None,
                        'book_type': None, 'access': None},
             'search_terms': ['Python'], 'providers': ['gutendex']},
            {'recommendations': [{'id': 'pg:1', 'evidence': 'invented exercise content'}]},
        ]
        clients.__contains__.return_value = True
        clients.__getitem__.return_value.search.return_value = [BOOK]
        result = SEARCH_GRAPH.invoke({'query': 'Python', 'page': 1})
        self.assertIn('Practical Python', result['books'][0]['reason'])
        self.assertNotIn('invented exercise content', result['books'][0]['reason'])

    @patch('discovery.ai.workflow.CLIENTS')
    @patch('discovery.ai.workflow.CerdasLabClient.complete_json')
    def test_deployed_model_list_shape_still_validates_ids(self, ai, clients):
        ai.side_effect = [
            {'intent': {'topic': 'Python', 'level': None, 'language': None,
                        'book_type': None, 'access': None},
             'search_terms': ['Python'], 'providers': ['gutendex']},
            {'list': [{'id': 'unknown', 'evidence': 'Unknown'},
                      {'id': 'pg:1', 'evidence': 'Practical Python'}]},
        ]
        clients.__contains__.return_value = True
        clients.__getitem__.return_value.search.return_value = [BOOK]
        result = SEARCH_GRAPH.invoke({'query': 'Python', 'page': 1})
        self.assertEqual([book['id'] for book in result['books']], ['pg:1'])

    @patch('discovery.web.SEARCH_GRAPH.invoke')
    def test_search_page_logs_and_links_to_transient_detail(self, invoke):
        invoke.return_value = {'query': 'Python', 'books': [BOOK], 'failures': [], 'selected': ['gutendex']}
        response = self.client.get('/search/', {'q': 'Python'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Practical Python')
        self.assertEqual(SearchLog.objects.count(), 1)
        from html.parser import HTMLParser
        class LinkParser(HTMLParser):
            def __init__(self):
                super().__init__(); self.links = []
            def handle_starttag(self, tag, attrs):
                if tag == 'a': self.links.append(dict(attrs).get('href', ''))
        parser = LinkParser(); parser.feed(response.content.decode())
        link = next(x for x in parser.links if x.startswith('/book/'))
        detail = self.client.get(link)
        self.assertContains(detail, 'Public domain in the US')

    def test_invalid_query_does_not_execute(self):
        response = self.client.get('/api/search/', {'q': 'x'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(SearchLog.objects.count(), 0)

    def test_no_book_table(self):
        from django.apps import apps
        self.assertFalse(any(model.__name__ == 'Book' for model in apps.get_models()))

    def test_analytics_requires_staff_and_shows_counts(self):
        self.assertEqual(self.client.get('/admin/analytics/').status_code, 302)
        user = get_user_model().objects.create_user('staff', password='secret-test-password', is_staff=True)
        self.client.force_login(user)
        SearchLog.objects.create(query='Python', total_results=1)
        self.assertContains(self.client.get('/admin/analytics/'), 'Total searches: 1')

    @patch.dict('os.environ', {'CERDASLAB_AI_BASE_URL': 'http://ollama:11434', 'CERDASLAB_AI_MODEL': 'test-model'})
    @patch('discovery.ai.cerdaslab_client.urlopen')
    def test_ai_client_records_invalid_output(self, urlopen):
        from discovery.ai.cerdaslab_client import CerdasLabClient
        urlopen.return_value.__enter__.return_value = BytesIO(json.dumps({'message': {'content': 'not json'}}).encode())
        with self.assertRaises(AIServiceError):
            CerdasLabClient().complete_json('understand', 'test')
        self.assertEqual(AIExecutionLog.objects.get().status, 'error')


class ProviderTests(TestCase):
    @patch('discovery.services.catalog.fetch_json')
    def test_openlibrary_does_not_make_borrowed_book_free(self, fetch):
        fetch.return_value = {'docs': [{'key': '/works/OL1W', 'title': 'Borrowed', 'ebook_access': 'borrowable', 'has_fulltext': True}]}
        book = OpenLibraryClient().search('borrowed')[0]
        self.assertIsNone(book['read_url'])
        self.assertIsNone(book['download_url'])

    @patch('discovery.services.catalog.fetch_json')
    def test_google_preview_excluded(self, fetch):
        fetch.return_value = {'items': [{'id': 'abc', 'volumeInfo': {'title': 'Preview'},
            'accessInfo': {'viewability': 'PARTIAL', 'publicDomain': False}}]}
        self.assertEqual(GoogleBooksClient().search('preview'), [])

    @patch('discovery.services.catalog.fetch_json')
    def test_gutendex_requires_explicit_us_public_domain(self, fetch):
        fetch.return_value = {'results': [{'id': 1, 'title': 'Unknown', 'copyright': None},
            {'id': 2, 'title': 'Public', 'copyright': False, 'formats': {'application/epub+zip': 'https://www.gutenberg.org/ebooks/2.epub'}}]}
        books = GutendexClient().search('public')
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0]['id'], 'pg:2')
        self.assertTrue(books[0]['download_url'])

    @patch('discovery.services.catalog.fetch_json')
    def test_doab_provider_page_only(self, fetch):
        fetch.return_value = [{'handle': '20.500.12854/1', 'metadata': [
            {'key': 'dc.title', 'value': 'Open Book'}, {'key': 'dc.rights', 'value': 'CC BY'}]}]
        book = DOABClient().search('open')[0]
        self.assertEqual(book['title'], 'Open Book')
        self.assertIsNone(book['download_url'])

    def test_rejects_unsafe_external_links(self):
        self.assertIsNone(safe_url('javascript:alert(1)', ['gutenberg.org']))
        self.assertIsNone(safe_url('https://gutenberg.org.evil.test/a', ['gutenberg.org']))
