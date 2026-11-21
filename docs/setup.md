# Setup

GitOps keeps a folder under `/config` in step with a branch of a Git repository. You add one repository at a time; each is a config entry with its own folder, entities and webhook.

Settings → Devices & services → **Add integration** → **GitOps**.

## 1. The repository

| Field | What it takes |
| :--- | :--- |
| Repository URL | SSH (`git@github.com:you/home.git`) for a private repository, or HTTPS for a public one |
| Branch | The branch to follow. Defaults to `main` |
| Folder | A folder under `/config`. When empty, the repository's name (`git@github.com:you/my-home.git` gives `my-home`). A path such as `repos/home` works |

The folder is refused when it:

- is absolute, contains `..`, or is `/config` itself;
- starts with a dot, or starts with one of Home Assistant's own folders: `custom_components`, `www`, `.storage`, `.cloud`, `.gitops`, `blueprints`, `deps`, `image`, `media`, `themes`, `tts`;
- already has files in it and isn't a clone of this URL;
- is already kept by another GitOps repository.

On a public HTTPS URL, GitOps asks the remote for the branch right away and shows the error if it can't read it.

## 2. The deploy key (SSH only)

For an SSH URL, GitOps makes an ed25519 key and shows its public half. Add it to the repository as a read-only deploy key (GitHub: Settings → Deploy keys → Add deploy key; read access is enough), then select **Submit**. GitOps tries the key against the remote and shows the error if that fails.

The key and its `known_hosts` file are kept in `/config/.gitops/<key id>/`. GitOps accepts a host's key the first time it connects.

## 3. The webhook

The last step shows a payload URL and a secret. The secret is shown once, so copy it before you select **Submit**.

On GitHub: Settings → Webhooks → Add webhook.

- Payload URL: the URL shown.
- Content type: `application/json`.
- Secret: the secret shown.
- Events: just the push event.

GitLab takes the same URL, with the secret as its token. Gitea and Forgejo sign requests like GitHub.

The URL is built from Home Assistant's external URL. Without one, the step says so, and GitOps checks for pushes every 5 minutes instead. See [How a deploy works](how-it-works.md).

## 4. Include the folder

GitOps only puts the files in place. Home Assistant has to load them. In `configuration.yaml`, include them from the folder, for example:

```yaml
homeassistant:
  packages: !include_dir_named my-home/packages
```

Restart Home Assistant once. After that, each push deploys.

The first deploy clones the repository. A deploy also runs at startup when the folder is behind the branch, so a push made while Home Assistant was down is caught up.

## Changing the settings later

Settings → Devices & services → GitOps → **Configure** opens the options: branch, the configuration check, what to reload and polling. They are listed in [Options](reference/options.md). Saving them reloads the repository.

## Removing a repository

Delete it under Devices & services. Its deploy key is removed. The folder and its files stay, because they are your configuration.
