# Entities and events

Each repository is a device, named after the repository, with these entities.

## Status sensor

An enum sensor with the state of the latest deploy.

| State | Meaning |
| :--- | :--- |
| `deployed` | The folder moved to a new commit and it was reloaded |
| `unchanged` | Up to date; nothing to do |
| `failed` | Fetching failed, or a rollback failed |
| `rolled_back` | The configuration check failed and the folder went back |
| `running` | A deploy is in progress |

Attributes of the last deploy: `commit`, `previous`, `subject`, `reason`, `changed` (the first 50 files), `changed_count`, `error`.

## Last deploy sensor

A timestamp sensor: when the folder last changed (a `deployed` result). Attribute: `commit`.

## Deploy button

Pulls the branch and deploys it now (reason `button`).

## Events

`gitops_deployed` fires when a deploy moved the folder to a new commit and it passed the check. `gitops_deploy_failed` fires when a deploy failed or was rolled back. Both carry:

| Field | Meaning |
| :--- | :--- |
| `entry_id` | The repository's config entry |
| `repository` | The repository URL |
| `branch` | The followed branch |
| `folder` | The folder under `/config` |
| `status` | `deployed`, `failed` or `rolled_back` |
| `reason` | `push`, `poll`, `startup`, `button` or `action` |
| `at` | When it ran (ISO 8601) |
| `commit` | The new commit |
| `previous` | The commit before (empty on the first clone) |
| `subject` | The commit's first line |
| `changed` | The files that differ from the previous commit (empty on the first clone) |
| `error` | The errors, for a failure |

Deploys that change nothing fire no event.
