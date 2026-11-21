# Troubleshooting

## A deploy was rolled back

The Status sensor reads **Rolled back**, and a notification titled "GitOps: (the repository) not deployed" lists the errors Home Assistant's check found. The `error` attribute of the sensor has the same text. Fix the configuration in the repository and push again. The folder is back on the previous commit meanwhile and nothing was reloaded.

## "Couldn't read the branch"

Setup couldn't reach the remote. For SSH, check that the deploy key is on the repository. For a branch error, the message says the repository has no branch with that name.

## Pushes don't deploy

- Look at the webhook's recent deliveries on the Git host. `401` means the secret is wrong. `200` means the push was to another branch than the one followed. `202` means it worked.
- Without an external URL in Home Assistant the webhook URL can't be reached from outside. Set a poll interval in the options (5 minutes is the default then) or give Home Assistant an external URL.
- Press the **Deploy** button to check that deploying itself works.

## "Pick a folder under /config"

The folder is absolute, outside `/config`, starts with a dot, or starts with a folder Home Assistant owns. See [Setup](setup.md).

## "That folder already has other files in it"

GitOps only clones into an empty or missing folder, or one that already holds a clone of the same URL. Move the files away or pick another folder.

## My edits in Home Assistant vanished

By design: each deploy makes the tracked files match the branch. Edit them in the repository. Untracked files are left alone.

## A change didn't take effect

The reload didn't include it, or it can't be reloaded. Check the **Then reload** option, or restart Home Assistant (see [How a deploy works](how-it-works.md)).

## The log

Failures are logged by the `custom_components.gitops` logger. A reload that fails is logged as "domain.action failed after a deploy".
