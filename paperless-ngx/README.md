# Paperless

Document management with a PostgreSQL database and a Valkey broker. Try this after
you understand persistent storage and `.env` settings.

## Run locally

From this directory:

```sh
cp .env.example .env
```

Edit `.env`. Replace `POSTGRES_PASSWORD` and `PAPERLESS_SECRET_KEY` with two
different random values. Generate each with `openssl rand -hex 32`. The domain
settings are only needed for Traefik mode.

```sh
docker compose up -d
docker compose logs --tail 100 webserver
```

Wait for database initialization and migrations to finish. Create your first
login interactively:

```sh
docker compose exec webserver python manage.py createsuperuser
```

Open <http://localhost:8083>. If you change `PORT` or use a remote/LAN address,
also change `PAPERLESS_LOCAL_URL` to match your browser's full URL.

Stop the stack with `docker compose down`. The database and broker have no
published host ports and do not join the shared Traefik network.

## Storage

All paths are relative to this recipe directory and are ignored by Git:

| Directory | Purpose |
| --- | --- |
| `data/` | Search index and application data |
| `media/` | Original and archived documents |
| `consume/` | Documents waiting to be imported |
| `export/` | Exported documents and metadata |
| `pgdata/` | PostgreSQL database |
| `redisdata/` | Broker state |

Use Paperless's document exporter and a consistent database backup. Keep the
secrets needed for recovery in a separate secure backup. Verify a restore on a
test host. See the [Paperless administration documentation](https://docs.paperless-ngx.com/administration/).

Changing the database password in `.env` after the first run does not change the
password already stored in PostgreSQL. See [settings](../docs/getting-started.md#settings).

## Add a domain later

Follow [Traefik and HTTPS](../docs/traefik.md). The hostname is
`paperless.DOMAIN_NAME`. The Traefik file sets `PAPERLESS_URL` to the HTTPS address
and routes to internal port 8000. The same database and document paths are used
in both modes. Include the explicit Compose file arguments when creating users
or running other commands in Traefik mode.

[Jenkins configuration checks](../ci/README.md) are optional; they do not test
document OCR, database migrations, or application startup.
