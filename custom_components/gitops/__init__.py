"""GitOps: keep a folder of Home Assistant's configuration in step with a Git branch.

A push (GitHub's or GitLab's webhook, checked against its secret), a poll, the Deploy button or
`gitops.deploy` brings the folder up to the branch, checks the configuration, and reloads.
"""

from datetime import timedelta
import hashlib
import hmac
import json
import logging
import shutil
from typing import Any

from aiohttp import web
import probatio

from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_CONFIG_ENTRY_ID, Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_KEY_ID,
    CONF_POLL_MINUTES,
    CONF_SECRET,
    CONF_WEBHOOK_ID,
    DOMAIN,
    KEYS_FOLDER,
    SERVICE_DEPLOY,
)
from .deploy import Deployer
from .git import GitError

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.BUTTON, Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type GitOpsConfigEntry = ConfigEntry[Deployer]


def push_branch(headers: Any, body: bytes, secret: str) -> tuple[bool, str | None]:
    """Whether a webhook request is genuine, and the branch it pushed (None: not a push).

    GitHub signs the body with the secret (X-Hub-Signature-256), GitLab sends the secret itself
    (X-Gitlab-Token); Gitea and Forgejo sign like GitHub.
    """
    signature = headers.get("X-Hub-Signature-256") or headers.get("X-Gitea-Signature")
    if signature:
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        genuine = hmac.compare_digest(signature.removeprefix("sha256="), expected)
    elif token := headers.get("X-Gitlab-Token"):
        genuine = hmac.compare_digest(token, secret)
    else:
        genuine = False
    if not genuine:
        return False, None
    event = (
        headers.get("X-GitHub-Event")
        or headers.get("X-Gitea-Event")
        or headers.get("X-Gitlab-Event")
        or ""
    ).lower()
    if event not in ("push", "push hook"):
        return True, None
    try:
        ref = json.loads(body or b"{}").get("ref") or ""
    except ValueError:
        return True, None
    return True, ref.removeprefix("refs/heads/") if ref.startswith(
        "refs/heads/"
    ) else None


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """The deploy action."""

    async def deploy(call: ServiceCall) -> ServiceResponse:
        entries: list[GitOpsConfigEntry] = hass.config_entries.async_loaded_entries(
            DOMAIN
        )
        if entry_id := call.data.get(ATTR_CONFIG_ENTRY_ID):
            entries = [e for e in entries if e.entry_id == entry_id]
            if not entries:
                raise ServiceValidationError("No loaded GitOps repository with that id")
        results = {}
        for entry in entries:
            results[entry.entry_id] = (
                await entry.runtime_data.async_deploy("action")
            ).as_dict()
        return {"deploys": results}

    hass.services.async_register(
        DOMAIN,
        SERVICE_DEPLOY,
        deploy,
        schema=probatio.Schema({probatio.Optional(ATTR_CONFIG_ENTRY_ID): cv.string}),
        supports_response=SupportsResponse.OPTIONAL,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: GitOpsConfigEntry) -> bool:
    """Set up a repository: its webhook, its poll, and a catch-up once Home Assistant runs."""
    deployer = entry.runtime_data = Deployer(hass, entry)

    async def handle_webhook(
        hass: HomeAssistant, webhook_id: str, request: web.Request
    ) -> web.Response:
        body = await request.read()
        genuine, branch = push_branch(request.headers, body, entry.data[CONF_SECRET])
        if not genuine:
            _LOGGER.warning(
                "Refused a GitOps webhook call with a wrong or missing secret"
            )
            return web.Response(status=401)
        if branch is not None and branch == deployer.repo.branch:
            entry.async_create_background_task(
                hass, deployer.async_deploy("push"), f"gitops deploy {entry.title}"
            )
            return web.Response(status=202)
        return web.Response(status=200)

    webhook.async_register(
        hass,
        DOMAIN,
        f"GitOps: {entry.title}",
        entry.data[CONF_WEBHOOK_ID],
        handle_webhook,
        allowed_methods=["POST"],
    )
    entry.async_on_unload(
        lambda: webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])
    )

    async def catch_up(reason: str) -> None:
        """Deploy when the folder isn't the branch's latest (a push missed while down)."""
        try:
            behind = not deployer.repo.cloned or await deployer.async_behind()
        except GitError as error:
            _LOGGER.warning("Couldn't reach %s: %s", entry.title, error)
            return
        if behind:
            await deployer.async_deploy(reason)

    async def at_started(_hass: HomeAssistant) -> None:
        entry.async_create_background_task(
            hass, catch_up("startup"), f"gitops catch-up {entry.title}"
        )

    entry.async_on_unload(async_at_started(hass, at_started))

    if minutes := entry.options.get(CONF_POLL_MINUTES, 0):

        async def poll(_now: Any) -> None:
            if not deployer.running:
                await catch_up("poll")

        entry.async_on_unload(
            async_track_time_interval(hass, poll, timedelta(minutes=minutes))
        )

    entry.async_on_unload(entry.add_update_listener(_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _options_updated(hass: HomeAssistant, entry: GitOpsConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: GitOpsConfigEntry) -> bool:
    """Stop its webhook, poll and entities."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete its deploy key; the folder and its files stay (they're the configuration)."""
    if key_id := entry.data.get(CONF_KEY_ID):
        await hass.async_add_executor_job(
            shutil.rmtree, hass.config.path(KEYS_FOLDER, key_id), True
        )
