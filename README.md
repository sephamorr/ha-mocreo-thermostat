# Mocreo Thermostat for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A clean, local-polling Home Assistant custom integration for the **MOCREO ST7-CL** Bluetooth Thermostat / Temperature Controller.

---

## Features

- **Local Bluetooth Control**: Uses Home Assistant's native Bluetooth stack—works seamlessly with onboard Bluetooth adapters and [ESPHome Bluetooth Proxies](https://esphome.io/components/bluetooth_proxy.html) across your home.
- **Relay Controls**:
  - **Relay Low Setpoint** (`number` entity, in °C, step 0.1): lower temperature threshold.
  - **Relay High Setpoint** (`number` entity, in °C, step 0.1): upper temperature threshold.
  - **Working Mode** (`select` entity): switch between **Heating** and **Cooling** modes.
- **Configurable Polling**: Configurable refresh interval (default: **3600s / 1 hour**) to synchronize state while keeping Bluetooth connection slots free for other devices.
- **Robust Retries & Read-back Verification**: Built-in multi-attempt retries with backoff and write verification on the device to handle transient Bluetooth interference reliably.

---

## Temperature Telemetry

The MOCREO ST7-CL broadcasts live probe temperature continuously in its passive BLE advertisement packets. This integration intentionally omits active temperature telemetry polling to keep GATT connection times to an absolute minimum and avoid blocking other Bluetooth devices.

To receive live temperature readings in Home Assistant, use the [Passive BLE Monitor](https://github.com/custom-components/ble_monitor) integration, which decodes ST7-CL broadcast packets passively without opening a connection.

---

## Installation

### Via HACS (Recommended)

1. Open **HACS** in Home Assistant.
2. Click the three dots in the top right corner and choose **Custom repositories**.
3. Add Repository URL: `https://github.com/sephamorr/ha-mocreo-thermostat`
4. Type: **Integration**
5. Click **Add**, find **Mocreo Thermostat**, and click **Download**.
6. Restart Home Assistant.

### Manual Installation

1. Download the `custom_components/mocreo_thermostat` folder from this repository.
2. Copy it into your Home Assistant directory under `<config>/custom_components/mocreo_thermostat`.
3. Restart Home Assistant.

---

## Configuration

1. In Home Assistant, navigate to **Settings** → **Devices & Services** → **Add Integration**.
2. Search for **Mocreo Thermostat**.
3. Select your discovered ST7-CL device from the list (or choose *Enter address manually* and enter your device MAC / CoreBluetooth UUID).
4. Configure your desired background polling interval (default: `3600` seconds).

### Changing Polling Interval

Click **Configure** on the integration entry in **Devices & Services** to change the background poll interval at any time.

---

## Technical Details

The MOCREO ST7-CL uses the vendor's `FF10` GATT service:
- **Service UUID**: `0000ff10-0000-1000-8000-00805f9b34fb`
- **Query Characteristic**: `0000ff12-0000-1000-8000-00805f9b34fb` (Notify / Write)
- **Settings Characteristic**: `0000ff13-0000-1000-8000-00805f9b34fb` (Write)

When setpoints or mode are updated, the integration writes the 11-byte command payload to `FF13`, queries `FF12` to confirm the device accepted the update, and immediately releases the BLE connection.

---

## License

MIT © [Alexander Dewing](https://github.com/sephamorr)
