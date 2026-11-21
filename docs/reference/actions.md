# Actions

## `gitops.deploy`

Pulls the branch and deploys it now. Every repository when none is given.

| Field | What it takes |
| :--- | :--- |
| `config_entry_id` | One repository's config entry (optional) |

An unknown or unloaded id raises "No loaded GitOps repository with that id".

The action can answer. Called with a response, it returns what each deploy did, by config entry:

```yaml
deploys:
  <entry id>:
    status: deployed
    reason: action
    at: "2026-11-21T10:00:00+00:00"
    commit: "…"
    previous: "…"
    subject: "…"
    changed: ["automations/porch.yaml"]
    error: null
```

If a deploy is already running for that repository, the call doesn't wait: the response status is `running`, and one more deploy runs after the current one.
