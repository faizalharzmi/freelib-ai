import time
from django.core import signing
from django.http import Http404, JsonResponse
from django.shortcuts import render
from analytics.models import SearchLog
from discovery.ai.cerdaslab_client import AIServiceError
from discovery.ai.workflow import SEARCH_GRAPH
from discovery.forms import SearchForm


def home(request):
    return render(request, 'discovery/home.html', {'form': SearchForm()})


def run_search(query, page):
    started = time.monotonic()
    status, error_type, count = 'ok', '', 0
    try:
        result = SEARCH_GRAPH.invoke({'query': query, 'page': page})
        count = len(result['books'])
        if result['failures'] and len(result['failures']) == len(result['selected']):
            status = 'provider_error'
        return result
    except AIServiceError as exc:
        status, error_type = 'ai_error', type(exc).__name__
        raise
    finally:
        SearchLog.objects.create(query=query, search_type='ai', total_results=count,
            duration_ms=int((time.monotonic()-started)*1000), status=status, error_type=error_type)


def search(request):
    form = SearchForm(request.GET or None)
    context = {'form': form, 'searched': bool(request.GET)}
    if not request.GET:
        return render(request, 'discovery/results.html', context)
    if form.is_valid():
        try:
            result = run_search(form.cleaned_data['q'], form.cleaned_data.get('page') or 1)
            books = []
            for book in result['books']:
                copy = dict(book)
                copy['detail_token'] = signing.dumps(book, salt='freelib-book')
                books.append(copy)
            context.update(books=books, failures=result['failures'], query=form.cleaned_data['q'])
            if not books and result['failures']:
                context['error'] = 'Book providers are unavailable. Please retry.'
        except AIServiceError:
            context['error'] = 'The CerdasLab AI service is unavailable. Please retry shortly.'
    return render(request, 'discovery/results.html', context)


def api_search(request):
    form = SearchForm(request.GET or None)
    if not form.is_valid():
        return JsonResponse({'error': form.errors.get_json_data()}, status=400)
    try:
        result = run_search(form.cleaned_data['q'], form.cleaned_data.get('page') or 1)
    except AIServiceError:
        return JsonResponse({'error': 'AI service unavailable'}, status=503)
    status = 502 if result['failures'] and len(result['failures']) == len(result['selected']) else 200
    return JsonResponse({'query': result['query'], 'books': result['books'],
        'returned_count': len(result['books']), 'provider_failures': result['failures']}, status=status)


def detail(request):
    token = request.GET.get('token', '')
    if not token or len(token) > 12000:
        raise Http404
    try:
        book = signing.loads(token, salt='freelib-book', max_age=3600)
    except signing.BadSignature:
        raise Http404
    if not isinstance(book, dict) or not book.get('id') or not book.get('provider_url'):
        raise Http404
    return render(request, 'discovery/detail.html', {'book': book})
