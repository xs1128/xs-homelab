# Optional Jenkins checks

You do not need Jenkins to run any guided recipe. The same validation can run on
your computer with `python3 scripts/validate.py`.

`ci/Jenkinsfile` provides an optional pipeline for this repository. It renders
all Compose recipes, checks the guided local/Traefik modes, and verifies required
settings and storage boundaries. It does not install applications or deploy them.

## Configure a job

Use a Jenkins agent labeled `homelab-ci` with Git, Python 3.9+, and the Docker CLI
with Compose installed. The agent needs no Docker Engine socket or production
secrets for these checks.

Create a Pipeline job with **Pipeline script from SCM**, select this repository
and your branch, and set **Script Path** to `ci/Jenkinsfile`. Use your own Jenkins
credentials for source checkout if the repository is private. Webhooks or polling
are optional choices for triggering builds.

The pipeline runs the checked-out validation script and fails on invalid
configuration. It cleans the dedicated job workspace before checkout and after
the run. Keep that workspace separate from a deployed homelab checkout.

These checks do not run application startup, OCR, migrations, real certificate
issuance, or DNS/network connectivity. They also do not scan image vulnerabilities.
Add application tests or image scanning to the repository that owns those concerns.
