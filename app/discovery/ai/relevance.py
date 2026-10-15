"""Conservative metadata gate for AI-planned searches.

Provider search APIs can return books whose titles have no connection to the
reader's topic. The AI still plans and ranks the search; this gate prevents
obviously unrelated records from reaching the ranking prompt or the UI.
"""
import re
import unicodedata


STOPWORDS = {
    'a', 'an', 'and', 'about', 'at', 'book', 'books', 'beginner', 'beginners',
    'discover', 'find', 'for', 'free', 'from', 'guide', 'guides', 'i', 'in',
    'introduction', 'learn', 'learning', 'of', 'on', 'open', 'read', 'reading',
    'recommend', 'show', 'the', 'to', 'understand', 'want', 'with',
}

ALIASES = {
    'governance': {'governance', 'governing', 'governed', 'oversight', 'regulation', 'regulatory', 'policy'},
    'ethics': {'ethics', 'ethical'},
    'safety': {'safety', 'safe'},
}


def _normalized(value):
    value = unicodedata.normalize('NFKD', str(value or '').casefold())
    value = ''.join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r'[^a-z0-9]+', ' ', value)
    value = re.sub(r'\bartificial intelligence\b', 'ai', value)
    value = re.sub(r'\bmachine learning\b', 'machine_learning', value)
    return ' '.join(value.split())


def _concepts(query, intent):
    terms = _normalized(query).split()
    if not any(term not in STOPWORDS for term in terms):
        terms = _normalized((intent or {}).get('topic')).split()
    concepts = []
    for term in terms:
        if term in STOPWORDS:
            continue
        concept = next((name for name, variants in ALIASES.items() if term in variants), term)
        if concept not in concepts:
            concepts.append(concept)
    return concepts


def _matches(concept, words):
    return bool((ALIASES.get(concept) or {concept}) & words)


def filter_relevant_books(query, intent, books):
    concepts = _concepts(query, intent)
    if not concepts:
        return books
    relevant = []
    for book in books:
        title_words = set(_normalized(book.get('title')).split())
        all_words = title_words | set(_normalized(book.get('description')).split())
        title_hits = {concept for concept in concepts if _matches(concept, title_words)}
        all_hits = {concept for concept in concepts if _matches(concept, all_words)}

        # Acronym and policy searches need evidence for both the domain and
        # the requested aspect. This rejects generic government records for
        # "AI governance" and generic AI books without governance content.
        if 'ai' in concepts and len(concepts) > 1:
            keep = 'ai' in all_hits and bool(all_hits - {'ai'}) and bool(title_hits)
        elif 'machine_learning' in concepts and any(c in concepts for c in ('governance', 'ethics', 'safety')):
            keep = 'machine_learning' in all_hits and bool(all_hits & {'governance', 'ethics', 'safety'}) and bool(title_hits)
        else:
            keep = bool(title_hits) or (len(concepts) == 1 and bool(all_hits))
        if keep:
            relevant.append(book)
    return relevant
