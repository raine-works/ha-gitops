# GitOps for Home Assistant

Keep your Home Assistant configuration in a Git repository and deploy it by pushing. GitOps keeps a
folder of `/config` in step with a branch: every push brings it up to date, Home Assistant's own
configuration check runs, and what changed is reloaded. A configuration that doesn't pass the check
is rolled back before anything reloads.

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg?style=for-the-badge)](LICENSE)

## What it does

- **Clones and pulls** the branch into a folder under `/config` (your `configuration.yaml` includes
  from it: `homeassistant: !include my-home/config.yaml`, `packages: !include_dir_named my-home/packages`…).
  The repository is the source of truth: edits made to its files in Home Assistant are discarded on
  the next deploy (files the repository doesn't track are left alone).
- **Private repositories** over SSH: it makes a deploy key for you to add (read-only is enough).
  Public ones work over HTTPS with nothing to add.
- **Deploys on push** through a webhook (GitHub, GitLab, Gitea, Forgejo), checked against its secret.
  Without an external URL it checks for pushes every few minutes instead. It also catches up at
  startup with any push it missed.
- **Checks the configuration first** (what Developer tools → Check configuration runs). When the
  check fails, the folder goes back to the commit it had, nothing reloads, and a notification shows
  the errors.
- **Reloads** everything Home Assistant can reload, the integrations you pick, or nothing.
- **Tells your automations**: `gitops_deployed` (with the commit, its subject, the files that
  changed) and `gitops_deploy_failed`, for whatever else a deploy should do: refresh dashboards,
  reload a config entry, restart for a change that needs it.

Entities per repository: **Status** (deployed, up to date, failed, rolled back, deploying; the last
deploy's commit, changed files and error as attributes), **Last deploy**, and a **Deploy** button.
Action: `gitops.deploy` (one repository, or all), answering what each deploy did.

## Installation

1. In HACS, add `https://github.com/raine-works/ha-gitops` as a custom repository (Integration),
   install **GitOps**, and restart Home Assistant.
2. Settings → Devices & services → Add integration → **GitOps**: the repository URL, its branch, and
   the folder to keep it in.
3. For an SSH URL, add the deploy key it shows to the repository (GitHub: Settings → Deploy keys).
4. Add the webhook it shows (GitHub: Settings → Webhooks; content type `application/json`, the push
   event only, the secret it gives). The secret is shown once.
5. Include the folder from `configuration.yaml`, then restart once. Every push after that deploys.

## Example: after each deploy

```yaml
triggers:
  - trigger: event
    event_type: gitops_deployed
actions:
  - action: frontend.reload_themes
  - if: "{{ trigger.event.data.changed | select('match', 'custom_components/') | list | count > 0 }}"
    then:
      - action: persistent_notification.create
        data:
          message: "{{ trigger.event.data.subject }} changed an integration: restart to load it."
```

## Notes

- Needs `git`, which Home Assistant's container (and Home Assistant OS) ships.
- Deploy keys live in `/config/.gitops/` (with their `known_hosts`); removing the repository from
  GitOps deletes its key, never the folder.
- One deploy at a time per repository; pushes arriving meanwhile become one more deploy after it.

## License

MIT: see [LICENSE](LICENSE).
