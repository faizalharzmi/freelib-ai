# Reverse engineering guide for a Laravel engineer

Study in this order:

1. `app/config/urls.py`: Django `path()` is the equivalent of Laravel `routes/web.php` and `routes/api.php`.
2. `app/discovery/forms.py` and `web.py`: forms handle validation; view functions are comparable to small Laravel controller actions. Follow `home`, `search`, then `run_search`.
3. `app/templates/`: Django templates play Blade's role; `{% url %}`, `{% if %}`, and `{{ value }}` render server-side HTML.
4. `app/discovery/ai/workflow.py`: `SearchState` is a Python `TypedDict` describing keys passed between LangGraph nodes. `StateGraph.add_node` and `add_edge` compose a workflow/state machine. Follow each node in order and inspect what dictionary it returns.
5. `app/discovery/services/catalog.py`: Python classes implement HTTP provider adapters. `urllib.request` fills the role often handled by Laravel's HTTP client. `basic_book` normalizes different API shapes to one transient structure.
6. `app/discovery/ai/cerdaslab_client.py`: one service owns Ollama calls, similar to a Laravel service class. The Django views import it indirectly through the graph rather than using a service container.
7. `app/analytics/models.py`, `migrations/`, `admin.py`: Django ORM models/migrations are analogous to Eloquent and Laravel migrations. Admin model registration provides read-only operational lists.
8. `app/config/settings.py`, `Dockerfile`, `compose.yaml`: settings come from environment variables; `pip` requirements replace Composer's dependencies, and Gunicorn serves Django behind the private endpoint.

Python syntax to notice: indentation defines blocks; `None` corresponds to PHP `null`; lists and dictionaries resemble PHP indexed and associative arrays; `try/except/finally` handles failures; type hints describe expected values but do not enforce them at runtime. `@staff_member_required` and `@admin.register` are decorators, similar in purpose to Laravel middleware/registration helpers. Run `python manage.py test discovery analytics` and use the mocked workflow test to trace one complete request before trying a live provider and Ollama search.
