from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone
from .models import AIExecutionLog, ProviderRequestLog, SearchLog


@staff_member_required
def dashboard(request):
    searches = SearchLog.objects.all()
    today = timezone.localdate()
    context = {
        'total_searches': searches.count(),
        'searches_today': searches.filter(created_at__date=today).count(),
        'average_duration': round(searches.aggregate(v=Avg('duration_ms'))['v'] or 0),
        'ai_count': AIExecutionLog.objects.count(),
        'ai_failures': AIExecutionLog.objects.filter(status='error').count(),
        'top_queries': searches.values('query').annotate(count=Count('id')).order_by('-count')[:10],
        'daily': searches.annotate(day=TruncDate('created_at')).values('day').annotate(count=Count('id')).order_by('-day')[:14],
        'providers': ProviderRequestLog.objects.values('provider').annotate(
            requests=Count('id'), failures=Count('id', filter=Q(status='error')),
            average_ms=Avg('duration_ms'),
        ).order_by('provider'),
    }
    return render(request, 'analytics/dashboard.html', context)
