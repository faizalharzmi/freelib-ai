# Project structure

- `app/config/`: Django settings, WSGI entrypoint, top-level routes.
- `app/discovery/forms.py`: natural-language input limits.
- `app/discovery/web.py`: public and JSON request handlers; transient signed book details.
- `app/discovery/ai/cerdaslab_client.py`: Ollama request/response adapter.
- `app/discovery/ai/workflow.py`: LangGraph state and nodes.
- `app/discovery/services/catalog.py`: four live provider adapters and safe URL helper.
- `app/discovery/services/*.py`: older `/api/books/` keyword-search implementation retained for compatibility.
- `app/discovery/static/`, `app/templates/`: CerdasLab-inspired CSS, JavaScript and Django templates.
- `app/analytics/`: operational models, admin lists, and staff dashboard.
- `compose.yaml`: isolated local Docker project. `compose.production.yaml`:
  deployed server configuration; `Dockerfile` is shared.
- `.env.example`: configuration names without secrets.
