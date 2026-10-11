# xs-homelab

Homelab recipes with a simple first run and an optional path to domains, HTTPS,
monitoring, and continuous integration.

Start with one service. You do not need Traefik, a domain, or Jenkins for the
three guided recipes below. Each recipe explains its storage and how to stop it.

## Start here

Install Docker with the Compose plugin. On Linux, use Docker Engine; on macOS,
use Docker Desktop or OrbStack. Run `docker compose version` to check Compose.

```sh
git clone https://github.com/xs1128/xs-homelab.git
cd xs-homelab/it-tools
docker compose up -d
```

Open <http://localhost:8080>. Then try another guided recipe:

| Recipe | What you learn | Local address |
| --- | --- | --- |
| [IT Tools](it-tools/README.md) | Start, inspect, and stop a stateless service | <http://localhost:8080> |
| [Stirling PDF](stirling-pdf/README.md) | Login and persistent configuration | <http://localhost:8082> |
| [Paperless](paperless-ngx/README.md) | Secrets, a database, document storage, and backups | <http://localhost:8083> |

The local recipes bind to your computer's loopback address. For a remote server,
see [remote access](docs/getting-started.md#using-a-remote-server).

## Choose the next step

- [Getting started](docs/getting-started.md): configuration, logs, updates, and storage.
- [Traefik and HTTPS](docs/traefik.md): add a domain to a guided recipe.
- [Optional Jenkins checks](ci/README.md): validate configuration before deployment.
- [All recipes](docs/catalog.md): guided services and existing advanced references.
- [What belongs in Git](docs/version-control.md): source, secrets, storage, and project ownership.

## How the guided recipes work

```text
it-tools/
├── README.md                    # Run the service first
├── docker-compose.yml           # Shared service definition
├── docker-compose.override.yml  # Local browser access; loaded automatically
├── compose.traefik.yml           # Optional domain and HTTPS routing
└── .env.example                 # Documented settings without real credentials
```

Running `docker compose up -d` loads the base and local override. The advanced
instructions select the base and Traefik file explicitly, so they do not publish
the local browser port. Both modes use the same storage paths and project name.

## Existing homelabs

This is a learning checkout, not an automatic migration of an existing server.
The three guided recipes use `xs-homelab-*` project names and no fixed container
names. Bind-mounted files live beside their Compose files. They create fresh
state in this checkout rather than attaching to a deployment in another checkout.
Host ports can still conflict with existing services.

The other stacks retain their earlier configurations and may have fixed
container names, external networks, or host-specific settings. Read their catalog
entries before running them. Keep your current deployment checkout in place until
you deliberately plan a migration and test a restore.

## Validate changes

```sh
python3 scripts/validate.py
```

Requires Python 3.9+ and Docker Compose. Validation renders configuration with
temporary dummy settings. It does not start containers, pull images, connect to
Docker Engine, or use production `.env` files. It checks both guided modes and
the syntax of all other Compose recipes. Runtime behavior remains a separate
check on a test host.

Upstream application versions follow the tags already used in this repository.
Some tags are moving tags. For a reproducible deployment, choose and test explicit
versions or digests; this restructuring does not upgrade the applications.
