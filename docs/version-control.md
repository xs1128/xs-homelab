# What belongs in Git

Git should contain the instructions and source needed to recreate a service.
Store the service's live state and secrets separately.

| Track | Keep outside Git |
| --- | --- |
| Compose files and Dockerfiles | Production `.env` and credentials |
| `.env.example` with placeholders | Database files and dumps |
| Application/exporter source and tests | Photos, documents, notes, and media |
| Dependency manifests and lockfiles | Generated dependencies, caches, logs, and reports |
| `pyproject.toml` and `.python-version` | Downloaded model weights |
| Dashboards, provisioning, and portable config | TLS private keys, ACME state, server identity keys |
| Backup scripts and recovery instructions | Backup passwords and backup repositories |
| Optional Jenkinsfiles and CI helpers | Machine-specific agent settings and permissions |

The root `.gitignore` protects common local state. Each new recipe should add its
own specific state paths. Do not exclude a source manifest just because a local
runtime generated it. Ignoring a file does not remove an already tracked file or
erase earlier commits; see [Git's ignore documentation](https://git-scm.com/docs/gitignore).

## Project ownership

The operational workspace has many independent repositories. This repository
owns the learning recipes and documentation. An application's existing repository
continues to own its source and application CI. Link to that repository, or use a
published image, when adding an application recipe. Keep one owner per file.

| Operational folders | Treatment here |
| --- | --- |
| `it-tools`, `stirling-pdf`, `paperless-ngx` | Guided recipes already in this Git history |
| `forgejo`, `immich`, `portainer`, `rustdesk-server`, `grafana-monitoring`, `traefik` | Existing advanced recipes; adapt before use |
| `coolify`, `siyuan`, `n8n-compose` | Candidates for sanitized deployment/workflow recipes; keep independent repositories |
| `backup`, `security` | Candidates for portable scripts and operating guides; exclude state and reports |
| `native-services`, `wg-show` | Host-specific tools; preserve source ownership and document platform requirements |
| `big`, `calendar-agent`, `fleet`, `home`, `nthu-homework`, `ocr`, `portal`, `suying` | Independent applications; add deployment recipes and source links where useful. The OCR source already present here remains in history |
| `deepseek-harness`, `omg.dev`, `openship`, `perplexity` | Separate projects; add a relevant integration recipe rather than importing the source trees |
| `research` | Curate homelab material into documentation; keep unrelated research elsewhere |
| `.claude` | Share intentional reusable skills; exclude local settings |
| `.local-service-archive`, `volumes` | Local state; excluded from this learning repository |

## Protect an existing deployment

A change to a recipe here does not update an existing deployment checkout.
Cloning Git does not migrate databases or bind mounts. Deploying from a second
checkout can create a second service or conflict with host ports.

Keep the live checkout and its independent Git repositories in place. To migrate
later, record the current image versions and volume paths, take a consistent
backup, restore on a test host, and then plan the cutover. This repository's
configuration checks never perform that cutover.
