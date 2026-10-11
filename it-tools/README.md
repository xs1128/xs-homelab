# IT Tools

A collection of browser tools. This is the smallest first recipe: one container,
no database, and no login.

## Run locally

From this directory:

```sh
docker compose up -d
```

Open <http://localhost:8080>. View logs with `docker compose logs --tail 100`.
Stop with `docker compose down`. There is no application storage to back up.

To change the listening port or interface, copy `.env.example` to `.env` and edit
`PORT` or `BIND_ADDRESS`. No environment file is required for the default setup.

## Add a domain later

Follow [Traefik and HTTPS](../docs/traefik.md). The hostname is
`tools.DOMAIN_NAME`, and Traefik forwards to port 80 inside the container.
Routing labels are in `compose.traefik.yml`; the default local mode does not load
them. [CI](../ci/README.md) is optional and has no role in starting the service.
