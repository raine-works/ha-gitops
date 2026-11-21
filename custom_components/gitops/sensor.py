"""What the last deploy did: its status, and when, with the commit and what changed."""

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GitOpsConfigEntry
from .const import STATUS_RUNNING, STATUSES
from .deploy import CHANGED_SHOWN
from .entity import GitOpsEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GitOpsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """The status and last deploy sensors."""
    async_add_entities(
        [
            DeployStatus(entry.runtime_data, "status"),
            LastDeploy(entry.runtime_data, "last_deploy"),
        ]
    )


class DeployStatus(GitOpsEntity, SensorEntity):
    """Deployed, unchanged, failed, rolled back, or running."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUSES

    @property
    def native_value(self) -> str | None:
        """The sensor's value."""
        if self.deployer.running:
            return STATUS_RUNNING
        return self.deployer.last.status if self.deployer.last else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """About the last deploy."""
        last = self.deployer.last
        if last is None:
            return {}
        return {
            "commit": last.commit,
            "previous": last.previous,
            "subject": last.subject,
            "reason": last.reason,
            "changed": last.changed[:CHANGED_SHOWN],
            "changed_count": len(last.changed),
            "error": last.error,
        }


class LastDeploy(GitOpsEntity, SensorEntity):
    """When the folder last changed."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, *args: Any) -> None:
        """Never deployed yet."""
        super().__init__(*args)
        self._at: datetime | None = None

    @property
    def native_value(self) -> datetime | None:
        """The sensor's value."""
        last = self.deployer.last
        if last is not None and last.status == "deployed":
            self._at = last.at
        return self._at

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """About the last deploy."""
        last = self.deployer.last
        return {"commit": last.commit} if last and last.commit else {}
