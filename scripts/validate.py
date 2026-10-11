#!/usr/bin/env python3
"""Render recipes with dummy settings; never start services or read live .env files."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
GUIDED = {
    "it-tools": ("it-tools", 80, 18080, "tools"),
    "stirling-pdf": ("stirling-pdf", 8080, 18082, "pdf"),
    "paperless-ngx": ("webserver", 8000, 18083, "paperless"),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def render(directory, settings, env_file, *, routed=False):
    env_file.write_text("".join(f"{key}={value}\n" for key, value in settings.items()))
    # Inherited application variables must not override our dummy env file.
    environment = {
        key: os.environ[key]
        for key in ("PATH", "HOME", "SYSTEMROOT", "TEMP", "TMP", "TMPDIR")
        if key in os.environ
    }
    environment["DOCKER_HOST"] = "unix:///nonexistent/xs-homelab-validation.sock"
    command = ["docker", "compose", "--env-file", str(env_file)]
    if routed:
        command += ["-f", "docker-compose.yml", "-f", "compose.traefik.yml"]
    command += ["config", "--no-env-resolution", "--format", "json"]
    return subprocess.run(
        command, cwd=directory, env=environment, text=True,
        capture_output=True, timeout=30,
    )


def configuration(directory, settings, env_file, *, routed=False):
    result = render(directory, settings, env_file, routed=routed)
    require(result.returncode == 0, f"{directory.name}: {result.stderr.strip()}")
    return json.loads(result.stdout)


def assert_required(directory, settings, env_file, key, *, routed):
    for value in (None, ""):
        invalid = dict(settings)
        if value is None:
            invalid.pop(key, None)
        else:
            invalid[key] = value
        result = render(directory, invalid, env_file, routed=routed)
        require(result.returncode != 0 and key in result.stderr,
                f"{directory.name}: accepted missing/empty {key}")


def bind_mounts(config):
    return sorted(
        (service_name, mount["source"], mount["target"])
        for service_name, service in config["services"].items()
        for mount in service.get("volumes", [])
        if mount["type"] == "bind"
    )


def check_guided(directory, settings, env_file):
    service_name, internal_port, host_port, hostname = GUIDED[directory.name]
    settings = dict(settings, PORT=str(host_port), BIND_ADDRESS="127.0.0.1",
                    PAPERLESS_LOCAL_URL=f"http://localhost:{host_port}")
    # Local mode must work without a domain or external proxy network.
    local_settings = dict(settings)
    local_settings.pop("DOMAIN_NAME")
    local = configuration(directory, local_settings, env_file)
    routed = configuration(directory, settings, env_file, routed=True)
    require(local["name"] == routed["name"] == f"xs-homelab-{directory.name}",
            f"{directory.name}: project identity changed between modes")
    require(not any(net.get("external") for net in local.get("networks", {}).values()),
            f"{directory.name}: local mode requires an external network")
    for service in local["services"].values():
        require("container_name" not in service, "guided recipe has a fixed container name")
        require(not any(key.startswith("traefik.") for key in service.get("labels", {})),
                "local mode unexpectedly enables Traefik")
    ports = local["services"][service_name].get("ports", [])
    require(len(ports) == 1 and ports[0]["target"] == internal_port
            and str(ports[0]["published"]) == str(host_port)
            and ports[0]["host_ip"] == "127.0.0.1",
            f"{directory.name}: local port override did not take effect")
    require(not any(service.get("ports") for service in routed["services"].values()),
            f"{directory.name}: routed mode still publishes host ports")
    labels = routed["services"][service_name]["labels"]
    require(labels["traefik.enable"] == "true", "routed discovery is disabled")
    require(labels["traefik.docker.network"] == settings["PROXY_NETWORK"],
            "Traefik does not use the configured proxy network")
    require(routed["networks"]["proxy"]["name"] == settings["PROXY_NETWORK"]
            and routed["networks"]["proxy"]["external"], "proxy network is not external")
    router = {"it-tools": "it-tools", "stirling-pdf": "stirling-pdf",
              "paperless-ngx": "paperless"}[directory.name]
    require(labels[f"traefik.http.routers.{router}.rule"]
            == f"Host(`{hostname}.{settings['DOMAIN_NAME']}`)", "incorrect routed hostname")
    require(labels[f"traefik.http.services.{router}.loadbalancer.server.port"]
            == str(internal_port), "incorrect internal routing port")
    require(bind_mounts(local) == bind_mounts(routed), "storage paths changed between modes")
    for _, source, _ in bind_mounts(local):
        require(Path(source).is_relative_to(directory),
                f"{directory.name}: bind mount points outside this recipe")
    assert_required(directory, settings, env_file, "DOMAIN_NAME", routed=True)
    if directory.name == "paperless-ngx":
        for config in (local, routed):
            require(config["networks"]["internal"]["internal"], "database network is not private")
            for backend in ("db", "broker"):
                service = config["services"][backend]
                require(not service.get("ports") and set(service["networks"]) == {"internal"},
                        f"{backend} is exposed outside the private network")
            require(config["services"]["db"]["environment"]["POSTGRES_PASSWORD"]
                    == config["services"]["webserver"]["environment"]["PAPERLESS_DBPASS"],
                    "database credentials do not match")
        require(local["services"]["webserver"]["environment"]["PAPERLESS_URL"]
                == settings["PAPERLESS_LOCAL_URL"], "local Paperless URL is incorrect")
        require(routed["services"]["webserver"]["environment"]["PAPERLESS_URL"]
                == f"https://paperless.{settings['DOMAIN_NAME']}", "routed Paperless URL is incorrect")
        for key in ("POSTGRES_PASSWORD", "PAPERLESS_SECRET_KEY"):
            for mode in (False, True):
                assert_required(directory, settings, env_file, key, routed=mode)
    print(f"PASS {directory.name}: local + Traefik, required settings, and storage")


def main():
    with tempfile.TemporaryDirectory(prefix="xs-homelab-validation-") as temporary:
        env_file = Path(temporary) / "compose.env"
        settings = {
            "DOMAIN_NAME": "example.invalid",
            "PROXY_NETWORK": "xs-homelab-test-proxy",
            "POSTGRES_PASSWORD": "fixture-only-database-password",
            "PAPERLESS_SECRET_KEY": "fixture-only-application-key",
            "UPLOAD_LOCATION": "./library", "DB_DATA_LOCATION": "./postgres",
            "DB_PASSWORD": "fixture-only-immich-password",
            "DB_USERNAME": "postgres", "DB_DATABASE_NAME": "immich",
            "CF_DNS_API_TOKEN": "fixture-only-dns-token",
            "ACME_EMAIL": "homelab@example.invalid",
        }
        recipes = sorted(ROOT.glob("*/docker-compose.yml"))
        require(recipes, "No Compose recipes found")
        for compose_file in recipes:
            directory = compose_file.parent
            if directory.name in GUIDED:
                check_guided(directory, settings, env_file)
            else:
                configuration(directory, settings, env_file)
                print(f"PASS {directory.name}: advanced reference syntax")
        print(f"Validated {len(recipes)} recipes; no containers started.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
