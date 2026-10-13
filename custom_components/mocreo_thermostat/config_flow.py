"""Config flow and options flow for Mocreo Thermostat."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_ADDRESS,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

MANUAL_ADDRESS_KEY = "manual"


class MocreoThermostatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mocreo Thermostat."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""
        self._discovered_devices: dict[str, bluetooth.BluetoothServiceInfoBleak] = {}
        self._discovery_info: BluetoothServiceInfoBleak | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            chosen = user_input[CONF_ADDRESS]
            if chosen == MANUAL_ADDRESS_KEY:
                return await self.async_step_manual()

            address = chosen
            await self.async_set_unique_id(address.lower())
            self._abort_if_unique_id_configured()

            discovered = self._discovered_devices.get(address)
            name = (discovered.name if discovered else None) or f"Mocreo ST7-CL ({address[-5:]})"
            poll_interval = user_input.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)

            return self.async_create_entry(
                title=name,
                data={
                    CONF_ADDRESS: address,
                    CONF_POLL_INTERVAL: poll_interval,
                },
            )

        # Scan for nearby connectable devices
        discovered_infos = bluetooth.async_discovered_service_info(
            self.hass, connectable=True
        )

        devices_list: dict[str, str] = {}
        for info in discovered_infos:
            name = info.name or ""
            # Identify MOCREO devices by name or manufacturer ID
            is_mocreo = (
                name.startswith("MOCREO")
                or name.startswith("ST7")
                or 0x8501 in info.manufacturer_data
                or 0x004A in info.manufacturer_data
            )
            if is_mocreo:
                self._discovered_devices[info.address] = info
                devices_list[info.address] = f"{name or 'MOCREO'} ({info.address})"

        if not devices_list:
            return await self.async_step_manual()

        devices_list[MANUAL_ADDRESS_KEY] = "Enter address manually..."

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(devices_list),
                    vol.Optional(
                        CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL
                    ): vol.All(vol.Coerce(int), vol.Range(min=30, max=86400)),
                }
            ),
            errors=errors,
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual address entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip()
            await self.async_set_unique_id(address.lower())
            self._abort_if_unique_id_configured()

            poll_interval = user_input.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
            return self.async_create_entry(
                title=f"Mocreo ST7-CL ({address[-5:]})",
                data={
                    CONF_ADDRESS: address,
                    CONF_POLL_INTERVAL: poll_interval,
                },
            )

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): str,
                    vol.Optional(
                        CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL
                    ): vol.All(vol.Coerce(int), vol.Range(min=30, max=86400)),
                }
            ),
            errors=errors,
        )

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle discovery via Home Assistant Bluetooth scanner."""
        await self.async_set_unique_id(discovery_info.address.lower())
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info

        self.context["title_placeholders"] = {
            "name": discovery_info.name or f"Mocreo ST7-CL ({discovery_info.address[-5:]})"
        }
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery of Bluetooth device."""
        assert self._discovery_info is not None

        if user_input is not None:
            poll_interval = user_input.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
            return self.async_create_entry(
                title=self._discovery_info.name or f"Mocreo ST7-CL ({self._discovery_info.address[-5:]})",
                data={
                    CONF_ADDRESS: self._discovery_info.address,
                    CONF_POLL_INTERVAL: poll_interval,
                },
            )

        return self.async_show_form(
            step_id="bluetooth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL
                    ): vol.All(vol.Coerce(int), vol.Range(min=30, max=86400)),
                }
            ),
            description_placeholders={
                "name": self._discovery_info.name or "Mocreo ST7-CL",
                "address": self._discovery_info.address,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get options flow handler."""
        return MocreoThermostatOptionsFlow(config_entry)


class MocreoThermostatOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Mocreo Thermostat."""

    def __init__(self, config_entry: config_entries.ConfigEntry | None = None) -> None:
        """Initialize options flow."""
        if config_entry is not None:
            self._config_entry = config_entry

    @property
    def _entry(self) -> config_entries.ConfigEntry:
        """Return the config entry."""
        return getattr(self, "config_entry", getattr(self, "_config_entry", None))

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        entry = self._entry
        current_poll_interval = entry.options.get(
            CONF_POLL_INTERVAL,
            entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POLL_INTERVAL, default=current_poll_interval
                    ): vol.All(vol.Coerce(int), vol.Range(min=30, max=86400)),
                }
            ),
        )
