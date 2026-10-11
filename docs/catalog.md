# Recipe catalog

The repository has three guided recipes. The other configurations remain as
advanced references from its existing history; they have not all been converted
to the local/Traefik split. Configuration validation does not establish that an
upstream image starts successfully on your hardware.

| Folder | Path | Preparation |
| --- | --- | --- |
| [it-tools](../it-tools/README.md) | Guided: first service | Docker Compose |
| [stirling-pdf](../stirling-pdf/README.md) | Guided: persistent configuration | First-run login |
| [paperless-ngx](../paperless-ngx/README.md) | Guided: stateful stack | Secrets, first user, backup plan |
| `convertx` | Advanced reference: file conversion | Traefik, `proxy` network, `DOMAIN_NAME` |
| `forgejo` | Advanced reference: Git hosting | Traefik, database password, domain, SSH port |
| `gitlab` | Advanced reference: Git hosting | Traefik, domain, `GITLAB_HOME`, SSH port, suitable resources |
| `glance` | Advanced reference: dashboard | `.env` for chosen widgets; review the existing widget configuration |
| `glances` | Advanced reference: system monitoring | Host PID/filesystem access and Docker socket; host-specific behavior |
| `grafana-monitoring` | Advanced reference: metrics | Traefik, domain, exporters, and host-specific Prometheus targets |
| `homepage` | Advanced reference: dashboard | Replace allowed hosts and example service/widget configuration |
| `immich` | Advanced reference: photo library | Storage paths, database variables, domain, and upstream version compatibility |
| `ocr` | Advanced reference: custom image | Build tools, model provisioning, and Traefik; review the application's API |
| `portainer` | Advanced reference: Docker administration | Traefik, domain, Docker socket, first admin account |
| `rustdesk-server` | Advanced reference: remote desktop | Client configuration, server keys, and TCP/UDP ports |
| `speedtest` | Advanced reference: speed monitoring | A newly generated `APP_KEY` in `.env`; review host UID/GID |
| `traefik` | Advanced reference: reverse proxy | [Networking guide](traefik.md), Cloudflare DNS token, domain, and ACME email |
| `wud` | Advanced reference: update monitoring | Docker socket; inspect update notifications before applying changes |
| `wg-show` | Advanced reference: native WireGuard helper | Existing WireGuard installation, permissions, and host-specific setup |

The advanced references may use fixed container names and existing network/host
assumptions. Treat them as material to adapt on a test host before deployment.
Do not run a second copy on your production server without checking those names,
ports, and volume locations.

Use `.env.example` when available. For an older reference without one, list its
required environment variables and create a local `.env` before running it.
Useful upstream starting points:

- [Immich Compose installation](https://docs.immich.app/install/docker-compose/)
- [Homepage installation](https://gethomepage.dev/installation/)
- [Forgejo container installation](https://forgejo.org/docs/latest/admin/installation/docker/)
- [Speedtest Tracker configuration](https://docs.speedtest-tracker.dev/)

Applications and tools that have their own repositories in the operational
workspace are deliberately not copied wholesale into this repository. See
[project ownership](version-control.md#project-ownership).
