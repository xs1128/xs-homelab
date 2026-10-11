# Getting started

Begin with IT Tools. It has no database or credentials. Add persistent services
after you are comfortable reading logs and stopping containers.

## Everyday commands

Run commands inside the service directory:

```sh
docker compose up -d
docker compose ps
docker compose logs --tail 100
docker compose down
```

`down` removes containers and the project network. Bind-mounted files stay on
disk. Named volumes also stay unless you explicitly use `down --volumes`.

## Settings

Each guided recipe includes `.env.example`. IT Tools and Stirling PDF have local
defaults; copying the file is optional. Paperless requires its secrets to be set.

```sh
cp .env.example .env
```

Edit `.env` before starting Paperless. Generate a different random value for each
secret with `openssl rand -hex 32`. Keep `.env` out of Git. Changing a PostgreSQL
password in this file after initialization does not change the database's stored
password; database credentials must be changed through PostgreSQL as well.

`PORT` changes the browser port. For Paperless, also update `PAPERLESS_LOCAL_URL`
to the full address you will use. `BIND_ADDRESS` controls the host interface.

## Using a remote server

The guided recipes default to `127.0.0.1`. Forward the relevant browser port from
the server to your computer. For IT Tools:

```sh
ssh -L 8080:127.0.0.1:8080 your-user@your-server
```

Open <http://localhost:8080> on your computer. For LAN access instead, set
`BIND_ADDRESS` to your server's LAN address in `.env`. Use the LAN address in the
browser and, for Paperless, in `PAPERLESS_LOCAL_URL`. IT Tools has no login, so
choose its listening interface with that behavior in mind.

## Storage and backups

IT Tools is stateless. Stirling PDF stores configuration and supporting files in
`stirling-data/`. Paperless stores documents, exports, incoming files, and database
state in the directories listed in its README. These directories are ignored by
Git. A Git clone restores configuration, not your documents or database.

Use the application's export/backup procedure and a separate copy outside the
server. Test a restore before relying on the backup. A live copy of PostgreSQL's
data directory is not a replacement for a consistent database backup.

## Updates

Read the upstream release notes and make a backup before updating a stateful
service. Change the image tag or digest if you pinned it, then run:

```sh
docker compose pull
docker compose up -d
docker compose logs --tail 100
```

These commands apply to local mode. In Traefik mode, include the same explicit
`-f docker-compose.yml -f compose.traefik.yml` arguments used to start the service.

## Troubleshooting

- **Port already in use:** choose another `PORT` in `.env`; update the browser URL.
- **A required variable is missing:** copy and edit `.env.example` in that service directory.
- **The browser cannot connect:** check `docker compose ps` and logs; first startup may take time.
- **An external `proxy` network is missing:** you selected an advanced recipe or Traefik mode. The guided local mode does not need it.

Technical references: [Compose overrides](https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/)
and [Compose environment interpolation](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/).
