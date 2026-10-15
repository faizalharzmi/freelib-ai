# Deployment

Create a production `.env.production` from `.env.example`. Set a unique Django secret, database password, allowed host names, and the URL/model of an Ollama-compatible service. Keep environment files and credentials out of source control.

For local Docker, `docker compose up -d --build` uses `.env` and a dedicated PostgreSQL volume. Open `http://127.0.0.1:8000`. The homepage can start without an AI endpoint, but AI search requires one.

For production, deploy `compose.production.yaml` with the production environment file. Validate configuration with `docker compose --env-file .env.production -f compose.production.yaml config --quiet`, then start the application with `docker compose --env-file .env.production -f compose.production.yaml up -d --build`. The web entrypoint runs migrations and static collection before Gunicorn. The web port binds to loopback by default; configure a reverse proxy and HTTPS certificate for public access. The production Compose file expects an existing Docker network for the configured AI service.

For rollback, stop the web service, restore the preceding source release, and rebuild it. Preserve the PostgreSQL volume and avoid removing unrelated Docker resources.
