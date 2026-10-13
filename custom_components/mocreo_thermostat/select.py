"""Select platform for Mocreo ST7-CL working mode."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODE_MAP_TO_BYTE, MODES
from .coordinator import MocreoThermostatCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entity for Mocreo ST7-CL."""
    coordinator: MocreoThermostatCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MocreoRelayModeSelect(coordinator)])


class MocreoRelayModeSelect(CoordinatorEntity[MocreoThermostatCoordinator], SelectEntity):
    """Select entity controlling Heating Mode vs Cooling Mode."""

    _attr_has_entity_name = True
    _attr_name = "Mode"
    _attr_icon = "mdi:thermostat"
    _attr_options = MODES

    def __init__(self, coordinator: MocreoThermostatCoordinator) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_relay_mode"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=coordinator.name,
            manufacturer="MOCREO",
            model="ST7-CL",
            connections={(dr.CONNECTION_BLUETOOTH, coordinator.address)},
        )

    @property
    def current_option(self) -> str | None:
        """Return the current selected mode."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.mode_name

    async def async_select_option(self, option: str) -> None:
        """Change the selected mode."""
        if self.coordinator.data is None:
            raise HomeAssistantError("Thermostat data not available")

        mode_byte = MODE_MAP_TO_BYTE.get(option)
        if mode_byte is None:
            raise HomeAssistantError(f"Unsupported mode option: {option}")

        await self.coordinator.async_set_relay_limits(
            low=self.coordinator.data.relay_low,
            high=self.coordinator.data.relay_high,
            mode=mode_byte,
        )
