# Changelog

## 0.1.0

- A repository per config entry: SSH with a generated deploy key, or HTTPS; a branch; a folder
  under `/config`.
- Deploys on a webhook push (GitHub, GitLab, Gitea, Forgejo; its secret checked), a poll, at
  startup when behind, the Deploy button or `gitops.deploy`.
- Home Assistant's configuration check before reloading; a failing configuration is rolled back.
- Reloads everything, chosen integrations, or nothing; `gitops_deployed` / `gitops_deploy_failed`
  events; Status and Last deploy sensors.
