# FreeLib AI

FreeLib AI is an AI-assisted book discovery application. Production: [https://freelib.cerdaslab.com](https://freelib.cerdaslab.com).

## Run locally with Docker

```sh
docker compose up -d --build
docker compose ps
```

Open <http://127.0.0.1:8000>. `compose.yaml` runs an isolated local PostgreSQL database. It reads local secrets from `.env`, which is ignored by Git and Docker build context.

AI search requires an Ollama-compatible service. Configure its URL and model through `CERDASLAB_AI_BASE_URL` and `CERDASLAB_AI_MODEL` in your local `.env`. Without an available AI endpoint, search recommendations are unavailable. See [deployment notes](docs/DEPLOYMENT.md).

To stop only this local project:

```sh
docker compose stop
```

Do not use `docker compose down -v`; that removes the local PostgreSQL volume.
