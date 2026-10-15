# Server architecture

The production deployment uses a web container, a dedicated PostgreSQL service and volume, an external Docker network for AI inference, and a reverse proxy for HTTPS. The database stays on the application's private Compose network. The web service binds to loopback by default; the reverse proxy forwards public requests to it.

The current public endpoint is [https://freelib.cerdaslab.com](https://freelib.cerdaslab.com).
