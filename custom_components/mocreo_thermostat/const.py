"""Constants for the Mocreo Thermostat integration."""

DOMAIN = "mocreo_thermostat"

CONF_ADDRESS = "address"
CONF_POLL_INTERVAL = "poll_interval"
DEFAULT_POLL_INTERVAL = 3600  # Default 1 hour polling for battery/GATT slot conservation

# BLE GATT Service and Characteristics
SERVICE_UUID = "0000ff10-0000-1000-8000-00805f9b34fb"
QUERY_UUID = "0000ff12-0000-1000-8000-00805f9b34fb"
SETTINGS_UUID = "0000ff13-0000-1000-8000-00805f9b34fb"

# Query and Response formats
RELAY_QUERY = bytes((3, 2, 1, 9))
RELAY_RESPONSE_LEN = 8
RELAY_RESPONSE_PREFIX = bytes((7, 6, 1))

# Working Mode mapping
MODE_HEATING = "Heating"
MODE_COOLING = "Cooling"
MODE_BYTE_HEATING = 0
MODE_BYTE_COOLING = 1

MODE_MAP_TO_BYTE = {
    MODE_HEATING: MODE_BYTE_HEATING,
    MODE_COOLING: MODE_BYTE_COOLING,
}

MODE_MAP_FROM_BYTE = {
    MODE_BYTE_HEATING: MODE_HEATING,
    MODE_BYTE_COOLING: MODE_COOLING,
}

MODES = [MODE_HEATING, MODE_COOLING]

# Communication parameters
DEFAULT_MAX_RETRIES = 5
DEFAULT_RETRY_BACKOFF = (2.0, 3.0, 5.0, 8.0, 10.0)
DEFAULT_TIMEOUT = 10.0

# Supported temperature range for ST7-CL (Celsius)
MIN_TEMP_C = -40.0
MAX_TEMP_C = 105.0
STEP_TEMP_C = 0.1

PLATFORMS = ["number", "select"]
