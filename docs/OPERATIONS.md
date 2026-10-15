# Operations

Use `docker compose --env-file .env.production -f compose.production.yaml ps` and `logs --tail=100 web`. Check application health at its loopback-bound port. Check the database with `docker compose --env-file .env.production -f compose.production.yaml exec db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'`. Check the configured AI service from the web container. Do not publish the Ollama port.

Staff view logs in `/admin/` and aggregates in `/admin/analytics/`. A search with no results can mean a narrow query; the UI reports partial provider failure. A 503 from `/api/search/` means AI unavailable or invalid. A 502 means every selected provider failed. Provider errors are recorded per source. Back up the dedicated PostgreSQL volume before changes that may affect stored logs or authentication.
