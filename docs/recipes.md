# Recipes

Both events carry the same data: see [Entities and events](reference/entities-and-events.md).

## After each deploy

Reload the themes, and say when an integration changed and needs a restart.

```yaml
triggers:
  - trigger: event
    event_type: gitops_deployed
actions:
  - action: frontend.reload_themes
  - if: "{{ trigger.event.data.changed | select('match', 'custom_components/') | list | count > 0 }}"
    then:
      - action: persistent_notification.create
        data:
          message: "{{ trigger.event.data.subject }} changed an integration: restart to load it."
```

## Tell your phone when a deploy fails

```yaml
triggers:
  - trigger: event
    event_type: gitops_deploy_failed
actions:
  - action: notify.mobile_app_my_phone
    data:
      title: "Deploy {{ trigger.event.data.status }}"
      message: "{{ trigger.event.data.error }}"
```

Replace `notify.mobile_app_my_phone` with your own notify action.

## Only for one repository

The events carry the folder, so an automation can look at it:

```yaml
conditions:
  - "{{ trigger.event.data.folder == 'my-home' }}"
```

## Reload nothing, do it yourself

Set **Then reload** to **Nothing** in the options and call the reloads you want from an automation on `gitops_deployed`.
