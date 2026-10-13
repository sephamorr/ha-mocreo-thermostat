"""Number platform for Mocreo ST7-CL thermostat."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MAX_TEMP_C, MIN_TEMP_C, STEP_TEMP_C
from .coordinator import MocreoThermostatCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities for Mocreo ST7-CL."""
    coordinator: MocreoThermostatCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            MocreoRelayLowNumber(coordinator),
            MocreoRelayHighNumber(coordinator),
        ]
    )


class _BaseMocreoNumber(CoordinatorEntity[MocreoThermostatCoordinator], NumberEntity):
    """Base class for Mocreo thermostat number entities."""

    _attr_has_entity_name = True
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = MIN_TEMP_C
    _attr_native_max_value = MAX_TEMP_C
    _attr_native_step = STEP_TEMP_C
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: MocreoThermostatCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=coordinator.name,
            manufacturer="MOCREO",
            model="ST7-CL",
            connections={(dr.CONNECTION_BLUETOOTH, coordinator.address)},
        )


class MocreoRelayLowNumber(_BaseMocreoNumber):
    """Number entity controlling the relay lower temperature bound."""

    _attr_name = "Relay Low Setpoint"

    def __init__(self, coordinator: MocreoThermostatCoordinator) -> None:
        """Initialize the relay low number entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_relay_low"

    @property
    def native_value(self) -> float | None:
        """Return current low setpoint value."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.relay_low

    async def async_set_native_value(self, value: float) -> None:
        """Set new low setpoint."""
        if self.coordinator.data is None:
            raise HomeAssistantError("Thermostat data not available")

        current_high = self.coordinator.data.relay_high
        if value >= current_high:
            raise HomeAssistantError(
                f"Relay low setpoint ({value}°C) must be less than high setpoint ({current_high}°C)"
            )

        await self.coordinator.async_set_relay_limits(
            low=value,
            high=current_high,
            mode=self.coordinator.data.mode,
        )


class MocreoRelayHighNumber(_BaseMocreoNumber):
    """Number entity controlling the relay upper temperature bound."""

    _attr_name = "Relay High Setpoint"

    def __init__(self, coordinator: MocreoThermostatCoordinator) -> None:
        """Initialize the relay high number entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_relay_high"

    @property
    def native_value(self) -> float | None:
        """Return current high setpoint value."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.relay_high

    async def async_set_native_value(self, value: float) -> None:
        """Set new high setpoint."""
        if self.coordinator.data is None:
            raise HomeAssistantError("Thermostat data not available")

        current_low = self.coordinator.data.relay_low
        if value <= current_low:
            raise HomeAssistantError(
                f"Relay high setpoint ({value}°C) must be greater than low setpoint ({current_low}°C)"
            )

        await self.coordinator.async_set_relay_limits(
            low=current_low,
            high=value,
            mode=self.coordinator.data.mode,
        )
