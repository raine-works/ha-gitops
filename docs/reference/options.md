# Options

## Setup fields

See [Setup](../setup.md): Repository URL, Branch (default `main`) and Folder.

## Configure

Settings → Devices & services → GitOps → **Configure**.

| Option | Default | What it does |
| :--- | :--- | :--- |
| Branch | The one from setup | The branch to follow |
| Check the configuration first | On | Runs Home Assistant's check before reloading. A configuration that fails it is rolled back and nothing reloads |
| Then reload | Everything Home Assistant can reload | **Everything Home Assistant can reload** (`homeassistant.reload_all`), **The chosen integrations**, or **Nothing** (an automation on `gitops_deployed` does it) |
| Integrations to reload | `automation`, `script`, `scene`, `template` | Used with the chosen integrations. Lists integrations that have a `reload` action; other names can be typed |
| Check for pushes every (minutes) | 0 with a webhook URL, 5 without one | 0 means only the webhook, the button or the action. Up to 1440 |

Saving the options reloads the repository's entry.
