"""Low-level BLE communication and protocol encoding for Mocreo ST7-CL."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
import math
from typing import TYPE_CHECKING, Any

from bleak.exc import BleakError

try:
    from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
    HAVE_BLEAK_RETRY = True
except ImportError:
    from bleak import BleakClient as BleakClientWithServiceCache
    establish_connection = None
    HAVE_BLEAK_RETRY = False

from homeassistant.components import bluetooth

from .const import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_BACKOFF,
    DEFAULT_TIMEOUT,
    MAX_TEMP_C,
    MIN_TEMP_C,
    MODE_MAP_FROM_BYTE,
    QUERY_UUID,
    RELAY_QUERY,
    RELAY_RESPONSE_LEN,
    RELAY_RESPONSE_PREFIX,
    SERVICE_UUID,
    SETTINGS_UUID,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def decode_i16(data: bytes, offset: int) -> int:
    """Decode a signed 16-bit little-endian integer from data at offset."""
    return int.from_bytes(data[offset : offset + 2], "little", signed=True)


def encode_i16(value: float) -> bytes:
    """Encode a temperature value in Celsius to 2-byte signed LE centi-degrees."""
    raw_value = round(value * 100)
    if not -32768 <= raw_value <= 32767:
        raise ValueError(f"Temperature {value}°C is out of 16-bit range")
    return raw_value.to_bytes(2, "little", signed=True)


@dataclass
class MocreoThermostatData:
    """Thermostat state parsed from device GATT queries."""

    relay_low: float
    relay_high: float
    mode: int

    @property
    def mode_name(self) -> str:
        """Return friendly name of current mode."""
        return MODE_MAP_FROM_BYTE.get(self.mode, f"Unknown ({self.mode})")


class MocreoThermostatDevice:
    """Client for connecting to and interacting with a Mocreo ST7-CL thermostat."""

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        name: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        """Initialize the device client."""
        self.hass = hass
        self.address = address
        self.name = name or address
        self.timeout = timeout
        self.max_retries = max_retries

    async def _query_relay_internal(
        self, client: Any, notifications: asyncio.Queue[bytes]
    ) -> tuple[float, float, int]:
        """Send relay query on QUERY_UUID and await matching response notification."""
        while not notifications.empty():
            notifications.get_nowait()

        _LOGGER.debug("%s: sending relay query on %s", self.name, QUERY_UUID)
        await client.write_gatt_char(QUERY_UUID, RELAY_QUERY, response=True)

        deadline = asyncio.get_running_loop().time() + self.timeout
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise TimeoutError(f"{self.name}: timed out awaiting relay query response")
            try:
                data = await asyncio.wait_for(notifications.get(), remaining)
            except TimeoutError as err:
                raise TimeoutError(
                    f"{self.name}: timed out awaiting relay query response"
                ) from err

            if len(data) == RELAY_RESPONSE_LEN and data.startswith(RELAY_RESPONSE_PREFIX):
                low = decode_i16(data, 3) / 100.0
                high = decode_i16(data, 5) / 100.0
                mode = data[7]
                _LOGGER.debug(
                    "%s: received relay settings: low=%s, high=%s, mode=%s",
                    self.name,
                    low,
                    high,
                    mode,
                )
                return low, high, mode

            _LOGGER.debug("%s: ignoring unrelated notification %s", self.name, data.hex())

    async def _execute_with_retry(self, operation: Any) -> Any:
        """Connect to device with retry and run operation."""
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            _LOGGER.debug(
                "%s: BLE operation attempt %d/%d", self.name, attempt, self.max_retries
            )

            ble_device = bluetooth.async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
            if ble_device is None:
                last_error = RuntimeError(f"Device {self.address} not reachable by Bluetooth")
                _LOGGER.debug("%s: device not found in Bluetooth cache", self.name)
            else:
                notifications: asyncio.Queue[bytes] = asyncio.Queue()

                def on_notification(_sender: Any, data: bytearray) -> None:
                    notifications.put_nowait(bytes(data))

                client = None
                try:
                    if HAVE_BLEAK_RETRY and establish_connection is not None:
                        client = await establish_connection(
                            BleakClientWithServiceCache,
                            ble_device,
                            self.name,
                            max_attempts=1,
                        )
                    else:
                        from bleak import BleakClient

                        client = BleakClient(ble_device, timeout=self.timeout)
                        await client.connect()

                    if client.services.get_service(SERVICE_UUID) is None:
                        raise RuntimeError(f"Service {SERVICE_UUID} not found on device")

                    await client.start_notify(QUERY_UUID, on_notification)
                    try:
                        return await operation(client, notifications)
                    finally:
                        try:
                            await client.stop_notify(QUERY_UUID)
                        except Exception:  # noqa: BLE001
                            pass

                except (BleakError, OSError, TimeoutError, RuntimeError) as err:
                    last_error = err
                    _LOGGER.debug(
                        "%s: BLE attempt %d failed: %s", self.name, attempt, err
                    )
                finally:
                    if client is not None and client.is_connected:
                        try:
                            await client.disconnect()
                        except Exception:  # noqa: BLE001
                            pass

            if attempt < self.max_retries:
                backoff = (
                    DEFAULT_RETRY_BACKOFF[attempt - 1]
                    if attempt <= len(DEFAULT_RETRY_BACKOFF)
                    else DEFAULT_RETRY_BACKOFF[-1]
                )
                _LOGGER.debug("%s: waiting %ss before retry", self.name, backoff)
                await asyncio.sleep(backoff)

        raise RuntimeError(
            f"Failed communicating with {self.name} after {self.max_retries} attempts: {last_error}"
        ) from last_error

    async def read_relay_settings(self) -> tuple[float, float, int]:
        """Read relay low setpoint, high setpoint, and mode from device."""
        return await self._execute_with_retry(self._query_relay_internal)

    async def write_relay_settings(
        self, low: float, high: float, mode: int
    ) -> tuple[float, float, int]:
        """Write relay setpoints and mode to device, then verify with read-back."""
        if low >= high:
            raise ValueError(f"Lower setpoint ({low}°C) must be less than upper ({high}°C)")
        if not 0 <= mode <= 255:
            raise ValueError("Relay mode must be a valid byte (0 or 1)")

        low_wire = encode_i16(low)
        high_wire = encode_i16(high)
        command = (
            bytes((12, 5, 32))
            + low_wire
            + high_wire
            + bytes((5, 17, mode, 0, 16, 39))
        )

        async def _write_op(
            client: Any, notifications: asyncio.Queue[bytes]
        ) -> tuple[float, float, int]:
            _LOGGER.debug("%s: writing relay command to %s: %s", self.name, SETTINGS_UUID, command.hex())
            await client.write_gatt_char(SETTINGS_UUID, command, response=True)
            # Verify readback
            actual_low, actual_high, actual_mode = await self._query_relay_internal(
                client, notifications
            )
            expected_low = decode_i16(low_wire, 0) / 100.0
            expected_high = decode_i16(high_wire, 0) / 100.0
            if (actual_low, actual_high, actual_mode) != (expected_low, expected_high, mode):
                raise RuntimeError(
                    f"Write verification mismatch: expected ({expected_low}, {expected_high}, {mode}), "
                    f"got ({actual_low}, actual_high={actual_high}, mode={actual_mode})"
                )
            return actual_low, actual_high, actual_mode

        return await self._execute_with_retry(_write_op)
