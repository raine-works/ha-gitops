<p align="center"><img src="custom_components/gitops/brand/icon@2x.png" alt="GitOps" width="128"></p>

# GitOps for Home Assistant

Keep your Home Assistant configuration in a Git repository and deploy it by pushing. GitOps keeps a
folder of `/config` in step with a branch: every push brings it up to date, Home Assistant's own
configuration check runs, and what changed is reloaded. A configuration that doesn't pass the check
is rolled back before anything reloads.

[![Home Assistant Marketplace](https://img.shields.io/badge/Home_Assistant-Marketplace-41BDF5.svg?style=for-the-badge)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=raine-works&repository=ha-gitops&category=integration)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg?style=for-the-badge)](LICENSE)

<a href="https://buymeacoffee.com/raineworks"><img src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black" alt="Buy Me a Coffee" /></a>

## Features

- Clones and pulls a branch into a folder under `/config`; the repository is the source of truth.
- Private repositories over SSH with a generated deploy key; public ones over HTTPS.
- Deploys on a push webhook (GitHub, GitLab, Gitea, Forgejo), or by polling without an external URL. Catches up at startup.
- Runs Home Assistant's configuration check first and rolls back a configuration that fails it.
- Reloads everything, chosen integrations, or nothing.
- Fires `gitops_deployed` and `gitops_deploy_failed` for your automations. Status and Last deploy sensors, a Deploy button and a `gitops.deploy` action.

## Installation

[![Open your Home Assistant instance and open this repository in the Home Assistant Marketplace.](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=raine-works&repository=ha-gitops&category=integration)

1. Open the Home Assistant Marketplace (Settings → Marketplace, or the button above). If **GitOps** isn't listed, add `https://github.com/raine-works/ha-gitops` as a custom repository of type Integration.
2. Download **GitOps** and restart Home Assistant.
3. Settings → Devices & services → Add integration → **GitOps**, and follow the steps: the repository, the deploy key (SSH) and the webhook. See [Setup](docs/setup.md).
4. Include the folder from `configuration.yaml`, then restart once. Every push after that deploys.

## Documentation

| Guide | |
| :--- | :--- |
| [Installation](docs/installation.md) | From the Marketplace or by hand |
| [Setup](docs/setup.md) | The repository, deploy key, webhook and folder |
| [How a deploy works](docs/how-it-works.md) | Fetch, check, roll back, reload |
| [Recipes](docs/recipes.md) | Automations after a deploy |
| [Troubleshooting](docs/troubleshooting.md) | When a deploy fails or doesn't start |
| [Security](docs/security.md) | Secrets, keys and what a push can change |
| [Development](docs/development.md) | Tests and releasing |
| [Entities and events](docs/reference/entities-and-events.md) | Sensors, button, events |
| [Actions](docs/reference/actions.md) | `gitops.deploy` |
| [Options](docs/reference/options.md) | Every field |

## Notes

- Needs `git`, which Home Assistant's container (and Home Assistant OS) ships.
- Deploy keys live in `/config/.gitops/` (with their `known_hosts`); removing the repository from
  GitOps deletes its key, never the folder.
- One deploy at a time per repository; pushes arriving meanwhile become one more deploy after it.

## ☕ Support

If you find this project helpful, consider buying me a coffee to support continued
maintenance and development:

<a href="https://buymeacoffee.com/raineworks"><img src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black" alt="Buy Me a Coffee" /></a>

## License

MIT: see [LICENSE](LICENSE).
