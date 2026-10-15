from django.contrib import admin
from .models import AIExecutionLog, ProviderRequestLog, SearchLog


class ReadOnlyLogAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SearchLog)
class SearchLogAdmin(ReadOnlyLogAdmin):
    list_display = ('query', 'search_type', 'total_results', 'duration_ms', 'status', 'created_at')
    search_fields = ('query',)
    list_filter = ('search_type', 'status', 'created_at')


@admin.register(AIExecutionLog)
class AIExecutionLogAdmin(ReadOnlyLogAdmin):
    list_display = ('created_at', 'operation', 'status', 'duration_ms', 'error_type')
    list_filter = ('operation', 'status', 'created_at')


@admin.register(ProviderRequestLog)
class ProviderRequestLogAdmin(ReadOnlyLogAdmin):
    list_display = ('created_at', 'provider', 'status', 'result_count', 'duration_ms', 'error_type')
    list_filter = ('provider', 'status', 'created_at')
