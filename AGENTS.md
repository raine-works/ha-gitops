# Agent guidance for ha-gitops

## Raineworks base rules

This repository follows Raineworks' base rules, in [`.raineworks/base.md`](.raineworks/base.md): read them before
changing anything. They're a copy of `base.md` in `raine-works/agents`, kept current by its sync: change them there,
not here. Where this file is more specific, it wins.

@.raineworks/base.md

## This repository

GitOps is a Home Assistant custom integration (`custom_components/gitops`) that keeps a folder of `/config` in step with
a Git branch: on a push webhook (or by polling) it fetches, runs Home Assistant's configuration check, rolls back a
configuration that fails it, and reloads what changed. Layout and file roles:
[docs/development.md](docs/development.md); design: [docs/how-it-works.md](docs/how-it-works.md); threat model:
[docs/security.md](docs/security.md).

- **Check:** `ruff check custom_components`, `ruff format --check custom_components` and `pytest -q` (Python 3.14,
  `requirements-test.txt`); the `Test` workflow runs them, and `Validate` runs hassfest and the Marketplace (HACS)
  validation.
- **Release:** merge the release pull request: `release-pr.yml` (Raineworks' shared Release pull request) keeps one pull request, `Release v<version>`, open on `master` with the next version: major for a breaking change (`type!:`), minor for a `feat`, patch for anything else that ships (a change to `custom_components/`), with
  [CHANGELOG.md](CHANGELOG.md)'s `## Unreleased` entries under that version. When `Test` passes on `master`, the
  `Release` workflow creates `v<version>`. Never bump the version by hand; a change worth noting adds its entry under
  `## Unreleased`.
- A deploy always checks the configuration before reloading and rolls back on failure; keep that order.
- Deploy keys live in `/config/.gitops/` with owner-only permissions and webhook secrets are verified on every request;
  neither is ever logged or shown after setup. Git runs as a subprocess with prompts off and a time limit.
- A repository is never cloned over Home Assistant's own folders (the reserved list is in [docs/setup.md](docs/setup.md)).
- `scripts/render-brand.sh` renders the brand icons from `assets/logo.svg`.
