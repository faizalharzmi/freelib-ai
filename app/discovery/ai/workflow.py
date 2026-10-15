"""Grounded LangGraph pipeline. No provider book data is persisted."""
import json
import time
from typing import TypedDict
from langgraph.graph import END, START, StateGraph
from analytics.models import ProviderRequestLog
from discovery.ai.cerdaslab_client import AIServiceError, CerdasLabClient
from discovery.ai.relevance import filter_relevant_books
from discovery.services.catalog import CLIENTS


class SearchState(TypedDict, total=False):
    query: str
    page: int
    plan: dict
    intent: dict
    terms: list[str]
    selected: list[str]
    raw_books: list[dict]
    books: list[dict]
    failures: list[str]


def understand(state):
    result = CerdasLabClient().complete_json('plan',
        'Return only JSON. intent must be an OBJECT with topic, level, language, book_type, access '
        '(string or null). search_terms must be an ARRAY of 1 to 3 strings. providers must be an '
        'ARRAY chosen from openlibrary, gutendex, googlebooks, doab. Example for a different '
        'request, "basic astronomy": {"intent":{"topic":"astronomy","level":"beginner",'
        '"language":null,"book_type":null,"access":null},"search_terms":["beginner astronomy"],'
        '"providers":["openlibrary","googlebooks"]}. Interpret only the actual request below; '
        'use null when unstated. Actual request: ' + json.dumps(state['query']))
    intent = result.get('intent')
    allowed = ('topic', 'level', 'language', 'book_type', 'access')
    if not isinstance(intent, dict) or any(k not in intent for k in allowed) or any(
        v is not None and not isinstance(v, str) for v in intent.values()
    ):
        raise AIServiceError('Invalid query understanding')
    return {'intent': {k: intent[k] for k in allowed}, 'plan': result}


def strategy(state):
    result = state['plan']
    terms = result.get('search_terms')
    providers = result.get('providers')
    if not isinstance(terms, list) or not 1 <= len(terms) <= 3 or any(not isinstance(t, str) or not t.strip() or len(t) > 100 for t in terms):
        raise AIServiceError('Invalid search strategy')
    if not isinstance(providers, list) or not providers or any(p not in CLIENTS for p in providers):
        raise AIServiceError('Invalid provider selection')
    return {'terms': terms, 'selected': list(dict.fromkeys(providers))}


def select_providers(state):
    return {'selected': [p for p in state['selected'] if p in CLIENTS]}


def fetch(state):
    books = []
    failures = []
    for name in state['selected']:
        started = time.monotonic()
        status, count, error_type = 'ok', 0, ''
        try:
            result = CLIENTS[name].search(state['terms'][0], state['page'])
            if not isinstance(result, list):
                raise ValueError('Invalid provider results')
            books.extend(result)
            count = len(result)
        except Exception as exc:
            status, error_type = 'error', type(exc).__name__
            failures.append(name)
        finally:
            ProviderRequestLog.objects.create(provider=name, duration_ms=int((time.monotonic()-started)*1000),
                status=status, result_count=count, error_type=error_type)
    return {'raw_books': books, 'failures': failures}


def normalize(state):
    # Adapters normalize at their boundaries; keep only complete attributed records.
    return {'books': [b for b in state['raw_books'] if b and b.get('id') and b.get('title') and b.get('provider_url')]}


def verify_access(state):
    books = []
    for book in state['books']:
        b = dict(book)
        if b.get('access_status') not in ('public', 'public_domain_us', 'public_domain', 'open_access_catalog'):
            b['read_url'] = None
            b['download_url'] = None
        if b.get('access_status') == 'open_access_catalog':
            b['download_url'] = None
        books.append(b)
    return {'books': books}


def deduplicate(state):
    seen = set()
    books = []
    for book in state['books']:
        isbn = str(book.get('isbn') or '').replace('-', '').replace(' ', '')
        identity = ('isbn', isbn) if len(isbn) == 13 and isbn.isdigit() else ('id', book['id'])
        if identity not in seen:
            seen.add(identity)
            books.append(book)
    return {'books': books}


def rank(state):
    relevant_books = filter_relevant_books(state['query'], state.get('intent'), state['books'])
    if not relevant_books:
        return {'books': []}
    candidates = [{'id': b['id'], 'title': b['title'], 'authors': b['authors'],
                   'description': (b.get('description') or '')[:150], 'language': b.get('language')}
                  for b in relevant_books[:12]]
    result = CerdasLabClient().complete_json('rank',
        'Select only directly relevant books, then rank up to three of these exact IDs. '
        'Return JSON key recommendations: '
        'list of at most three objects {id, evidence}. Evidence must be an exact nonempty substring of the '
        'supplied title or description, max 100 characters. Never add books. Request: ' +
        json.dumps(state['query']) + ' Books: ' + json.dumps(candidates, ensure_ascii=False))
    rows = result.get('recommendations')
    if rows is None:
        rows = result.get('list')  # Observed output from the deployed CerdasLab model.
    if not isinstance(rows, list):
        raise AIServiceError('Invalid ranking')
    candidate_ids = {b['id'] for b in candidates}
    by_id = {b['id']: b for b in relevant_books if b['id'] in candidate_ids}
    ranked, used = [], set()
    for row in rows:
        if not isinstance(row, dict) or row.get('id') not in by_id or row['id'] in used:
            continue  # Reject hallucinated or repeated IDs without hiding real provider results.
        book = dict(by_id[row['id']])
        evidence = row.get('evidence')
        if not isinstance(evidence, str) or not evidence or len(evidence) > 100 or not any(
            evidence.casefold() in str(book.get(k) or '').casefold() for k in ('title', 'description')):
            evidence = book['title'][:100]
        book['reason'] = 'AI ranked this provider result using: ' + evidence
        used.add(row['id'])
        ranked.append(book)
    # Only metadata-verified books remain visible after the AI-ranked subset.
    if not ranked:
        raise AIServiceError('AI did not rank any retrieved book')
    ranked.extend(b for b in relevant_books if b['id'] not in used)
    return {'books': ranked}


def recommend(state):
    return {'books': state['books']}


def build_graph():
    graph = StateGraph(SearchState)
    for name, fn in [('understand', understand), ('strategy', strategy), ('select_providers', select_providers),
                     ('fetch', fetch), ('normalize', normalize), ('verify_access', verify_access),
                     ('deduplicate', deduplicate), ('rank', rank), ('recommend', recommend)]:
        graph.add_node(name, fn)
    order = ['understand', 'strategy', 'select_providers', 'fetch', 'normalize',
             'verify_access', 'deduplicate', 'rank', 'recommend']
    graph.add_edge(START, order[0])
    for first, second in zip(order, order[1:]):
        graph.add_edge(first, second)
    graph.add_edge(order[-1], END)
    return graph.compile()


SEARCH_GRAPH = build_graph()
