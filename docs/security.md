# Security

- **The webhook secret.** A request is only accepted if it is signed with the secret (or carries it as GitLab's token). Anything else gets `401`. The secret is generated per repository and shown once, during setup.
- **Deploy keys.** The SSH key is made for one repository, kept in `/config/.gitops/<key id>/` with owner-only permissions, and never leaves Home Assistant. Add it as a read-only deploy key. Removing the repository from GitOps deletes the key.
- **Host keys.** The first connection to a Git host is accepted and recorded in that folder's `known_hosts`. Later connections must match.
- **What a push can change.** A deploy puts the branch's files in your configuration folder and reloads. Anyone who can push to the followed branch can change your Home Assistant configuration. Protect the branch. The configuration check catches a broken configuration, not a harmful one.
- **Reserved folders.** A repository is never cloned over Home Assistant's own folders (`custom_components`, `www`, `.storage` and the others listed in [Setup](setup.md)).
- **Git runs without prompts.** Git is started with terminal prompts off and a time limit of 120 seconds per command.
