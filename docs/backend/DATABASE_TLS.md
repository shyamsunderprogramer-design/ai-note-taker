# PostgreSQL TLS

PostgreSQL connections verify the server certificate and hostname using the operating system's trusted certificate authorities. For a private CA, set `DATABASE_SSL_CA_FILE` to a PEM CA bundle trusted for that database server.

The application passes a verified SSL context to asyncpg. URL `sslmode` options do not disable verification; other connection query options remain intact. A missing or invalid CA file fails initialization before a database connection is opened.

For an existing server with a self-signed certificate, configure its trusted CA before restarting with this change. Do not disable verification to resolve certificate errors. SQLite requires no TLS configuration.
