# Stirling PDF

A browser interface for PDF operations. This recipe introduces login and
persistent configuration after the stateless IT Tools recipe.

## Run locally

From this directory:

```sh
docker compose up -d
```

Open <http://localhost:8082>. Login is enabled in the shared service definition.
Follow the image's first-run login instructions and change its initial password.
See [Stirling PDF documentation](https://docs.stirlingpdf.com/) for the version
you run. No environment file is required for the default setup.

View startup logs with `docker compose logs --tail 100`. Stop with
`docker compose down`.

## Keep your configuration

The ignored `stirling-data/` directory contains:

| Directory | Purpose |
| --- | --- |
| `configs/` | Application and login configuration |
| `tessdata/` | OCR language files |
| `pipeline/` | Pipeline files |
| `logs/` | Application logs |

Keep a separate backup of the configuration and files you depend on. These files
are not recovered by cloning Git.

Copy `.env.example` to `.env` to customize the browser port, locale, or timezone.

## Add a domain later

Follow [Traefik and HTTPS](../docs/traefik.md). The hostname is `pdf.DOMAIN_NAME`;
the internal service port is 8080. [Jenkins checks](../ci/README.md) are optional.
