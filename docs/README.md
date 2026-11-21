# GitOps documentation

| Guide | |
| :--- | :--- |
| [Installation](installation.md) | Installing the integration from the Home Assistant Marketplace or by hand |
| [Setup](setup.md) | Adding a repository: the deploy key, the webhook, the options, including the configuration to include |
| [How a deploy works](how-it-works.md) | Fetch, check, roll back, reload, and what starts a deploy |
| [Recipes](recipes.md) | Automations that run after a deploy |
| [Troubleshooting](troubleshooting.md) | Failed deploys, webhooks that don't arrive, folders that are refused |
| [Security](security.md) | The webhook secret, deploy keys, what a deploy can change |
| [Development](development.md) | Running the tests and releasing |

| Reference (written from the code) | |
| :--- | :--- |
| [Entities and events](reference/entities-and-events.md) | The Status and Last deploy sensors, the Deploy button, `gitops_deployed` and `gitops_deploy_failed` |
| [Actions](reference/actions.md) | `gitops.deploy` and its response |
| [Options](reference/options.md) | Every setup and Configure field |
