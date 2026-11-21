"""Deploy now."""

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GitOpsConfigEntry
from .entity import GitOpsEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GitOpsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """The Deploy button."""
    async_add_entities([DeployButton(entry.runtime_data, "deploy")])


class DeployButton(GitOpsEntity, ButtonEntity):
    """Pull the branch and deploy it now."""

    async def async_press(self) -> None:
        """Deploy now."""
        await self.deployer.async_deploy("button")
