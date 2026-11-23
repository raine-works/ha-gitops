"""Constants for GitOps."""

DOMAIN = "gitops"

CONF_URL = "url"
CONF_BRANCH = "branch"
CONF_FOLDER = "folder"
CONF_KEY_ID = "key_id"
CONF_WEBHOOK_ID = "webhook_id"
CONF_SECRET = "secret"

# Options
CONF_RELOAD = "reload"
CONF_RELOAD_DOMAINS = "reload_domains"
CONF_POLL_MINUTES = "poll_minutes"

RELOAD_ALL = "all"
RELOAD_DOMAINS = "domains"
RELOAD_NONE = "none"

DEFAULT_BRANCH = "main"
DEFAULT_RELOAD_DOMAINS = ["automation", "script", "scene", "template"]

EVENT_DEPLOYED = "gitops_deployed"
EVENT_FAILED = "gitops_deploy_failed"

SERVICE_DEPLOY = "deploy"

# Where deploy keys and known hosts are kept: /config/.gitops/<key id>/
KEYS_FOLDER = ".gitops"

# Top-level folders of /config that belong to Home Assistant or its integrations: a repo is never
# cloned over one
RESERVED_FOLDERS = frozenset(
    {
        ".cloud",
        ".gitops",
        ".storage",
        "blueprints",
        "custom_components",
        "deps",
        "image",
        "media",
        "themes",
        "tts",
        "www",
    }
)

STATUS_DEPLOYED = "deployed"
STATUS_UNCHANGED = "unchanged"
STATUS_FAILED = "failed"
STATUS_ROLLED_BACK = "rolled_back"
STATUS_RUNNING = "running"
STATUSES = [
    STATUS_DEPLOYED,
    STATUS_UNCHANGED,
    STATUS_FAILED,
    STATUS_ROLLED_BACK,
    STATUS_RUNNING,
]
