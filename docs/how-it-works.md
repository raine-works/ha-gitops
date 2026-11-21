# How a deploy works

One deploy at a time runs per repository. A push that arrives while a deploy runs becomes one more deploy after it, however many arrive.

## What starts a deploy

Each deploy has a reason, shown in the Status sensor's `reason` attribute and in the events.

| Reason | When |
| :--- | :--- |
| `push` | The webhook received a push to the followed branch |
| `poll` | The poll found the remote ahead of the folder (only when a poll interval is set) |
| `startup` | Home Assistant started and the folder was missing or behind the branch |
| `button` | The **Deploy** button was pressed |
| `action` | `gitops.deploy` was called |

The button and the action always run a deploy. A webhook, poll or startup catch-up deploys when there is something new.

### The webhook

The webhook accepts POST requests and checks them against the secret:

- GitHub, Gitea and Forgejo: the body is signed with HMAC-SHA256 (`X-Hub-Signature-256` or `X-Gitea-Signature`).
- GitLab: `X-Gitlab-Token` carries the secret.

A request with a wrong or missing secret gets `401` and a warning in the log. A genuine push to the followed branch gets `202` and starts a deploy. Any other genuine request (another event, another branch) gets `200` and does nothing.

### Polling

With a poll interval above 0, GitOps checks the remote every N minutes and deploys when the branch has moved. Skipped while a deploy runs.

## The steps

1. **Fetch.** The first time, GitOps clones the branch into the folder (it refuses a folder that has files and isn't a clone). After that it fetches the branch and resets the folder to it. Edits made to tracked files in Home Assistant are discarded. Files the repository doesn't track are left alone. If the repository URL changed, the clone's `origin` is updated.
2. **Compare.** If the commit is the one already checked out, the deploy is `unchanged` and nothing else happens.
3. **Check.** Unless turned off in the options, GitOps runs Home Assistant's own configuration check (the one Developer tools → Check configuration runs).
4. **Roll back.** If the check reports errors, the folder is reset to the commit it had before, nothing is reloaded, `gitops_deploy_failed` is fired and a notification shows the errors. The status is `rolled_back`. If going back fails too, the status is `failed` and the error says so. On a first deploy there is no earlier commit to go back to.
5. **Reload.** Depending on the options: everything Home Assistant can reload (`homeassistant.reload_all`), the chosen integrations (each one's `reload` action, if it has one), or nothing. A reload that fails is logged and the rest go on.
6. **Announce.** `gitops_deployed` is fired, and the failure notification from an earlier deploy is dismissed.

If fetching fails (the remote can't be reached, the branch is gone), the status is `failed`, the folder is left as it was and `gitops_deploy_failed` is fired.

Some changes can't be reloaded, such as a new custom integration or a new YAML dashboard. Use [an automation on `gitops_deployed`](recipes.md) to notify yourself or restart.
