"""DataUpdateCoordinator for Mocreo ST7-CL thermostat."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_POLL_INTERVAL
from .device import MocreoThermostatData, MocreoThermostatDevice

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class MocreoThermostatCoordinator(DataUpdateCoordinator[MocreoThermostatData]):
    """Coordinator to manage polling and state for a Mocreo ST7-CL thermostat."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        address: str,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
    ) -> None:
        """Initialize coordinator."""
        self.entry = entry
        self.address = address
        self.device = MocreoThermostatDevice(hass, address, name=entry.title)
        self._lock = asyncio.Lock()

        super().__init__(
            hass,
            _LOGGER,
            name=entry.title or f"Mocreo ST7-CL {address}",
            update_interval=timedelta(seconds=poll_interval),
        )

    async def _async_update_data(self) -> MocreoThermostatData:
        """Poll the device for relay settings."""
        async with self._lock:
            try:
                low, high, mode = await self.device.read_relay_settings()
            except Exception as err:
                raise UpdateFailed(f"Error communicating with {self.name}: {err}") from err

            return MocreoThermostatData(
                relay_low=low,
                relay_high=high,
                mode=mode,
            )

    async def async_set_relay_limits(
        self, low: float, high: float, mode: int
    ) -> None:
        """Write new relay limits and mode to device, then update coordinator."""
        async with self._lock:
            try:
                actual_low, actual_high, actual_mode = (
                    await self.device.write_relay_settings(low, high, mode)
                )
            except Exception as err:
                _LOGGER.error("%s: failed to set relay limits: %s", self.name, err)
                raise

            self.data = MocreoThermostatData(
                relay_low=actual_low,
                relay_high=actual_high,
                mode=actual_mode,
            )
            self.async_update_listeners()

