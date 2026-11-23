"""A deploy: bring the folder up to the branch, check the configuration, reload.

One at a time per repository; a push arriving mid-deploy runs one more deploy after it (pushes
coalesce). When the configuration check fails, the folder goes back to the commit it had, nothing
is reloaded, and a notification says why. Every deploy that changes something fires
`gitops_deployed` (a failure `gitops_deploy_failed`), for automations that do the rest (refresh
dashboards, restart something).
"""

import asyncio
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
import logging
from pathlib import Path
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.check_config import async_check_ha_config_file
from homeassistant.util import dt as dt_util

from .const import (
    CONF_BRANCH,
    CONF_FOLDER,
    CONF_KEY_ID,
    CONF_RELOAD,
    CONF_RELOAD_DOMAINS,
    CONF_URL,
    DEFAULT_RELOAD_DOMAINS,
    EVENT_DEPLOYED,
    EVENT_FAILED,
    KEYS_FOLDER,
    RELOAD_ALL,
    RELOAD_DOMAINS,
    STATUS_DEPLOYED,
    STATUS_FAILED,
    STATUS_ROLLED_BACK,
    STATUS_RUNNING,
    STATUS_UNCHANGED,
)
from .git import GitError, Repo

_LOGGER = logging.getLogger(__name__)
CHANGED_SHOWN = 50


@dataclass
class DeployResult:
    """What the last deploy did."""

    status: str
    reason: str
    at: datetime = field(default_factory=dt_util.utcnow)
    commit: str | None = None
    previous: str | None = None
    subject: str | None = None
    changed: list[str] = field(default_factory=list)
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """As event data and an action's response."""
        data = asdict(self)
        data["at"] = self.at.isoformat()
        return data


def repo_for(hass: HomeAssistant, entry: ConfigEntry) -> Repo:
    """The entry's repository (the options' branch over the one it was set up with)."""
    key_id = entry.data.get(CONF_KEY_ID)
    return Repo(
        url=entry.data[CONF_URL],
        branch=entry.options.get(CONF_BRANCH, entry.data[CONF_BRANCH]),
        path=Path(hass.config.path(entry.data[CONF_FOLDER])),
        keys=Path(hass.config.path(KEYS_FOLDER, key_id)) if key_id else None,
    )


class Deployer:
    """Deploys one repository."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Nothing deployed yet."""
        self.hass = hass
        self.entry = entry
        self.last: DeployResult | None = None
        self.running = False
        self._lock = asyncio.Lock()
        self._again: str | None = None
        self._listeners: list[Callable[[], None]] = []

    @property
    def repo(self) -> Repo:
        """The repository as the entry has it now."""
        return repo_for(self.hass, self.entry)

    @property
    def notification_id(self) -> str:
        """Its failure notification."""
        return f"gitops_{self.entry.entry_id}"

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Call listener on every change; returns its removal."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    @callback
    def _updated(self) -> None:
        for listener in list(self._listeners):
            listener()

    async def async_deploy(self, reason: str) -> DeployResult:
        """Deploy now, or once more after the deploy that's running."""
        if self._lock.locked():
            self._again = reason
            return DeployResult(STATUS_RUNNING, reason)
        async with self._lock:
            self.running = True
            self._updated()
            try:
                result = await self._deploy(reason)
                while self._again is not None:
                    reason, self._again = self._again, None
                    result = await self._deploy(reason)
            finally:
                self.running = False
                self._updated()
            return result

    async def async_behind(self) -> bool:
        """Whether the remote branch has moved past what's checked out."""
        repo = self.repo
        return await repo.remote_head() != await repo.head()

    async def _deploy(self, reason: str) -> DeployResult:
        repo = self.repo
        previous: str | None = None
        try:
            previous = await repo.head()
            commit = await repo.sync()
        except (GitError, OSError) as error:
            return self._failed(
                DeployResult(
                    STATUS_FAILED, reason, previous=previous, error=str(error)
                ),
                "Couldn't update the folder from the repository; it was left as it was.",
            )
        if commit == previous:
            return self._done(
                DeployResult(STATUS_UNCHANGED, reason, commit=commit, previous=previous)
            )

        result = DeployResult(
            STATUS_DEPLOYED,
            reason,
            commit=commit,
            previous=previous,
            subject=await self._quietly(repo.subject(commit)),
            changed=(await self._quietly(repo.changed(previous, commit)) or [])
            if previous
            else [],
        )

        # Always check before reloading, and roll back a configuration that
        # fails: reloading an unchecked one can take Home Assistant down.
        errors = await self._check()
        if errors:
            result.status = STATUS_ROLLED_BACK
            result.error = "\n".join(errors)
            if previous:
                try:
                    await repo.reset(previous)
                except GitError as error:
                    result.status = STATUS_FAILED
                    result.error += (
                        f"\n\nGoing back to {previous[:7]} failed too: {error}"
                    )
            return self._failed(
                result,
                f"The configuration at {commit[:7]} doesn't pass Home Assistant's check"
                + (f", so the folder went back to {previous[:7]}" if previous else "")
                + "; nothing was reloaded.",
            )

        await self._reload()
        return self._done(result)

    @staticmethod
    async def _quietly(work: Any) -> Any:
        try:
            return await work
        except GitError:
            return None

    async def _check(self) -> list[str]:
        """Home Assistant's own configuration check (what Developer tools' Check runs)."""
        try:
            config = await async_check_ha_config_file(self.hass)
        except Exception as error:  # noqa: BLE001
            return [f"The check itself failed: {error}"]
        return [
            f"{err.domain}: {err.message}" if err.domain else err.message
            for err in config.errors
        ]

    async def _reload(self) -> None:
        mode = self.entry.options.get(CONF_RELOAD, RELOAD_ALL)
        if mode == RELOAD_ALL:
            await self._call("homeassistant", "reload_all")
        elif mode == RELOAD_DOMAINS:
            for domain in self.entry.options.get(
                CONF_RELOAD_DOMAINS, DEFAULT_RELOAD_DOMAINS
            ):
                if self.hass.services.has_service(domain, "reload"):
                    await self._call(domain, "reload")

    async def _call(self, domain: str, service: str) -> None:
        """A reload; one failing (an invalid file) never stops the rest."""
        try:
            await self.hass.services.async_call(domain, service, blocking=True)
        except Exception:
            _LOGGER.exception("%s.%s failed after a deploy", domain, service)

    def _event_data(self, result: DeployResult) -> dict[str, Any]:
        return {
            "entry_id": self.entry.entry_id,
            "repository": self.entry.data[CONF_URL],
            "branch": self.repo.branch,
            "folder": self.entry.data[CONF_FOLDER],
            **result.as_dict(),
        }

    def _done(self, result: DeployResult) -> DeployResult:
        self.last = result
        if result.status == STATUS_DEPLOYED:
            persistent_notification.async_dismiss(self.hass, self.notification_id)
            self.hass.bus.async_fire(EVENT_DEPLOYED, self._event_data(result))
            _LOGGER.info(
                "Deployed %s (%s) into %s",
                result.commit and result.commit[:7],
                result.reason,
                self.entry.data[CONF_FOLDER],
            )
        self._updated()
        return result

    def _failed(self, result: DeployResult, summary: str) -> DeployResult:
        self.last = result
        self.hass.bus.async_fire(EVENT_FAILED, self._event_data(result))
        persistent_notification.async_create(
            self.hass,
            f"{summary}\n\n```\n{(result.error or '')[:1500]}\n```",
            title=f"GitOps: {self.entry.title} not deployed",
            notification_id=self.notification_id,
        )
        _LOGGER.warning("Deploy of %s failed: %s", self.entry.title, result.error)
        self._updated()
        return result
