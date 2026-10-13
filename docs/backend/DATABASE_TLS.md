# PostgreSQL TLS

PostgreSQL connections verify the server certificate and hostname using the operating system's trusted certificate authorities. For a private CA, set `DATABASE_SSL_CA_FILE` to a PEM CA bundle trusted for that database server.

The application passes a verified SSL context to asyncpg. URL `sslmode` options do not disable verification; other connection query options remain intact. A missing or invalid CA file fails initialization before a database connection is opened.

For an existing server with a self-signed certificate, configure its trusted CA before restarting with this change. Do not disable verification to resolve certificate errors. SQLite requires no TLS configuration.

`GET /health/config` and `GET /health/db-debug` require an authenticated admin. Their responses show the database dialect and readiness without connection credentials, query parameters or local file paths. Regular `/health` checks remain available for startup/readiness monitoring.

The database debug probe uses the same verified PostgreSQL TLS settings as normal connections, limits the connection/query probe to five seconds, and disposes of its temporary engine on success, failure or cancellation. Failed probes return HTTP 503 with a generic error. URL classification uses the scheme, so a PostgreSQL password or database name containing `sqlite` cannot select SQLite behavior or disable TLS.
