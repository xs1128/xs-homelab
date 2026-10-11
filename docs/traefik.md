# Optional Traefik and HTTPS

Use the local guided recipe first. This path adds a domain and HTTPS to the same
service definition. It assumes you understand which services should be reachable
from the internet or your private network.

## Prerequisites

- A Traefik instance reachable by your clients on HTTPS port 443.
- A shared Docker network, normally named `proxy`.
- A domain with a DNS record pointing clients to that Traefik instance.
- A `websecure` entrypoint and a `myresolver` certificate resolver.

The existing `traefik/docker-compose.yml` is an advanced reference using Cloudflare
DNS challenges. Its `.env` needs `DOMAIN_NAME`, `ACME_EMAIL`, and
`CF_DNS_API_TOKEN`. Create the external `proxy` network before starting that stack.
Adapt its dashboard access and host ports to your setup. It retains the historical
dashboard configuration, so review it before exposing the stack publicly.
See [Traefik's Docker provider documentation](https://doc.traefik.io/traefik/reference/install-configuration/providers/docker/).

If Traefik is already deployed, inspect its entrypoints, resolver, and network
names instead of starting a second instance. Set `PROXY_NETWORK` to its network
name in the recipe's `.env`; edit the entrypoint/resolver labels if yours differ.

## Select routed mode

In a guided recipe directory, copy `.env.example` to `.env` if you have not already
done so. Set `DOMAIN_NAME` to your actual domain. Preserve existing Paperless
secrets. The three hostnames are `tools.DOMAIN_NAME`, `pdf.DOMAIN_NAME`, and
`paperless.DOMAIN_NAME`.

```sh
docker compose -f docker-compose.yml -f compose.traefik.yml config --quiet
docker compose -f docker-compose.yml -f compose.traefik.yml up -d
```

These explicit files omit `docker-compose.override.yml`. The guided web service
has no published browser port in routed mode. Traefik reaches its internal port
through the shared network. Paperless keeps its database/broker on its private
network; only the web service joins `proxy`.

## Read the labels

| Label | What it tells Traefik |
| --- | --- |
| `traefik.enable` | Discover this service |
| `traefik.docker.network` | Choose the network used to reach it |
| `routers.*.rule` | Match the requested hostname |
| `routers.*.entrypoints` | Accept traffic on `websecure` |
| `routers.*.tls` | Use TLS for the router |
| `routers.*.tls.certresolver` | Obtain certificates with `myresolver` |
| `services.*.loadbalancer.server.port` | Reach the application's internal port |

The service-specific Traefik file keeps these settings out of the beginner's
default configuration.

## Continue using the same mode

Include the explicit file arguments for `logs`, `exec`, `pull`, and `down`:

```sh
docker compose -f docker-compose.yml -f compose.traefik.yml logs --tail 100
docker compose -f docker-compose.yml -f compose.traefik.yml down
```

Switching access modes within this checkout uses the same project identity and
bind mounts. To return to local mode, run `docker compose up -d`. Paperless's URL
changes with the selected mode; update bookmarks accordingly.

Compose merges list fields such as ports rather than automatically removing them.
Keep local and routed overlays separate. See [Docker's merge rules](https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/).
