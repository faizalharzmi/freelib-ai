# Architecture

FreeLib AI is a synchronous Django 5.2 application. Django templates render the public UI; `/api/search/` returns JSON. The same `run_search` service invokes a compiled LangGraph pipeline. Provider adapters make live HTTP requests, normalize metadata, and never create book rows. The Ollama-compatible adapter handles all LLM calls. PostgreSQL contains Django authentication/session tables and operational logs only.

The production Compose project contains `web` and its own PostgreSQL `db`. The web container can join an external Docker network to reach the configured AI service. Its database uses a separate private Compose network. The application port binds to loopback by default and can be served through a reverse proxy.

Before AI ranking, a conservative relevance gate compares the reader's request and AI-interpreted topic with each provider title and description. It removes obvious catalog false positives, including government budget records returned for "AI governance". Only the filtered records reach the ranking prompt and results page; no book data is persisted. A search can legitimately return zero books after filtering.

Failure behavior: malformed AI output stops recommendations; each failed provider is logged and partial results are displayed when possible. An all-provider failure returns a 502 API response or a UI retry message. External links are selected from provider metadata and constrained to provider domains.
