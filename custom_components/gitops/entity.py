"""A repository's device, which its entities share."""

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import CONF_FOLDER, CONF_URL, DOMAIN
from .deploy import Deployer


class GitOpsEntity(Entity):
    """Follows its repository's deployer."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, deployer: Deployer, key: str) -> None:
        """An entity of the repository's device."""
        self.deployer = deployer
        entry = deployer.entry
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="GitOps",
            model=entry.data[CONF_URL],
            sw_version=entry.data[CONF_FOLDER],
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        """Follow the deployer."""
        self.async_on_remove(
            self.deployer.async_add_listener(self.async_write_ha_state)
        )
