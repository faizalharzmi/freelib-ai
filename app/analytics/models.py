from django.db import models


class SearchLog(models.Model):
    query = models.TextField()
    search_type = models.CharField(max_length=30, default='keyword')
    total_results = models.IntegerField(default=0)
    duration_ms = models.IntegerField(default=0)
    status = models.CharField(max_length=24, default='ok')
    error_type = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.query[:100]


class AIExecutionLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    operation = models.CharField(max_length=32)
    duration_ms = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=24)
    error_type = models.CharField(max_length=80, blank=True)


class ProviderRequestLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    provider = models.CharField(max_length=32)
    duration_ms = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=24)
    result_count = models.PositiveIntegerField(default=0)
    error_type = models.CharField(max_length=80, blank=True)
