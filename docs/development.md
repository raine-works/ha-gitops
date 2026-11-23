# Development

The integration is in `custom_components/gitops`:

| File | What it holds |
| :--- | :--- |
| `__init__.py` | Setup, the webhook handler, polling, startup catch-up, the `deploy` action |
| `config_flow.py` | The setup flow and the options flow |
| `deploy.py` | The deploy: sync, check, roll back, reload, events |
| `git.py` | Git run as a subprocess, deploy key generation |
| `sensor.py`, `button.py`, `entity.py` | The entities |
| `const.py`, `services.yaml`, `strings.json`, `translations/en.json` | Constants and text |

## Tests and lint

The workflow in `.github/workflows/test.yaml` runs, with Python 3.14:

```bash
pip install -r requirements-test.txt
ruff check custom_components
ruff format --check custom_components
pytest -q
```

A virtual environment works the same: `python3.14 -m venv .venv && .venv/bin/pip install -r requirements-test.txt`.

`.github/workflows/validate.yaml` runs hassfest and the Marketplace repository validation, from images pinned by digest. Weekly, the Image pins workflow (`.github/workflows/image-pins.yml`, Raineworks' shared one) checks those pins against their tags and opens a pull request moving any that moved.

## Brand images

`scripts/render-brand.sh` renders `custom_components/gitops/brand/icon.png` and `icon@2x.png` from `assets/logo.svg` with headless Chrome.

## Releasing

Bump `version` in `custom_components/gitops/manifest.json` and add a [changelog](../CHANGELOG.md) entry. When the change reaches `master` and the Test workflow passes, the Release workflow creates the GitHub release `v<version>` with generated notes, if that tag doesn't exist yet.
