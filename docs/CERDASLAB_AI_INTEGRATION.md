# AI integration

The app connects to an Ollama-compatible service configured through `CERDASLAB_AI_BASE_URL`, `CERDASLAB_AI_MODEL`, and `CERDASLAB_AI_TIMEOUT`. It does not deploy Ollama or download a model.

`CerdasLabClient.complete_json` posts to `/api/chat` using `stream:false`, JSON output and temperature zero. The adapter logs operation, duration and failure type without storing prompts or responses. Invalid JSON, timeouts, and unavailable models raise `AIServiceError`. The workflow validates required JSON fields and ranking IDs/evidence separately.

The query-understanding and search-strategy LangGraph nodes share one structured `plan` inference, reducing requests to the configured service. Before ranking, the application checks retrieved provider titles and descriptions against the reader's topic. This conservative gate removes obvious false positives, while the `rank` inference selects up to three IDs from the remaining records. Both AI responses have a 256-token generation cap; unsupported IDs or reasons are rejected. Other metadata-matched records remain visible after the ranked subset.
