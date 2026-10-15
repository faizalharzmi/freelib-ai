# Database schema

Django's standard `auth`, `admin`, `contenttypes`, and `sessions` migrations are used. `analytics_searchlog` stores query, search type, result count, duration, status, error type and timestamp. `analytics_aiexecutionlog` stores operation, duration, status, error type and timestamp. `analytics_providerrequestlog` stores provider, duration, status, count, error type and timestamp. No `Book` model, catalog table, result JSON or full AI prompt is stored. See `app/analytics/migrations/` for exact schema history.
