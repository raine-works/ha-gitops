# Changelog

## 1.0.2

- Every deploy runs Home Assistant's configuration check before reloading: the **Check the configuration first** option is gone, and an entry that had it off is checked too.

## 1.0.1

- A new icon, in Raineworks' style: a branch merging back, its merge commit lit in the peach-to-teal gradient, on a black tile.
- The README has the Buy Me a Coffee button.

## 1.0.0

- First stable release.
- Documentation in `docs/`: installation, setup, how a deploy works, recipes, troubleshooting, security, development, and references for entities and events, actions and options.
- Installation steps use the Home Assistant Marketplace (built into Home Assistant 2026.11).

## 0.1.0

- A repository per config entry: SSH with a generated deploy key, or HTTPS; a branch; a folder
  under `/config`.
- Deploys on a webhook push (GitHub, GitLab, Gitea, Forgejo; its secret checked), a poll, at
  startup when behind, the Deploy button or `gitops.deploy`.
- Home Assistant's configuration check before reloading; a failing configuration is rolled back.
- Reloads everything, chosen integrations, or nothing; `gitops_deployed` / `gitops_deploy_failed`
  events; Status and Last deploy sensors.
