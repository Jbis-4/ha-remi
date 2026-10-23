# Home Assistant Remi Integration

> **Unofficial** Home Assistant integration for the [UrbanHello Remi](https://www.urbanhello.com/) smart alarm clock.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

This is a community-maintained integration and is **not affiliated with or endorsed by UrbanHello**.

---

## Features

- **Sensors**: Room temperature, WiFi signal strength, firmware version, IP address, current face
- **Binary Sensors**: Online status, alive status, firmware update available
- **Select**: Clock face (Off / Awake / Sleepy / Semi-Awake / Smiley), clock format (12h / 24h), music mode
- **Number**: Volume, noise alert threshold
- **Switch**: Per-alarm enable/disable toggles (one switch per alarm)
- **Lights**: Brightness (dimmable), night light (RGB), background color (RGB)
- **Alarm CRUD**: Create, update and delete alarms via HA services

---

## Requirements

- Home Assistant 2024.1 or newer
- An UrbanHello account (username + password from the Remi app)

---

## Installation

### Via HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** → **⋮** → **Custom repositories**
3. Add `https://github.com/timoa/ha-remi` as an **Integration**
4. Search for **Remi** and install it
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/urbanhello_remi_unofficial/` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

---

## Configuration

1. Go to **Settings → Integrations → Add Integration**
2. Search for **Remi**
3. Enter your UrbanHello account **username** and **password**
4. The integration will authenticate and discover your Remi device automatically

---

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| Temperature | Sensor | Room temperature (°C) |
| WiFi Signal | Sensor | RSSI in dBm |
| Firmware Version | Sensor | Current firmware version |
| IP Address | Sensor | Local IP address |
| Current Face | Sensor | Active face name |
| Online | Binary Sensor | Device online status |
| Alive | Binary Sensor | Device alive status |
| Firmware Update Available | Binary Sensor | Whether a firmware update is available |
| Clock Face | Select | Change the displayed face |
| Clock Format | Select | 12h or 24h format |
| Music Mode | Select | Off / Music / White Noise |
| Volume | Number | Speaker volume (0–100) |
| Brightness | Light | Dimmable upper light (off at 0%, maximum at 100%) |
| Noise Alert Threshold | Number | Noise notification threshold (0–100) |
| Night Light | Light | RGB night light color |
| Background Color | Light | RGB background LED color |
| Alarm (per alarm) | Switch | Enable/disable individual alarms |

---

## Brightness migration

Brightness is now a dimmable `light`, using the same API `luminosity` setting
(0–100). The old `number` and the incorrectly labelled lux sensor are removed
from this integration's entity registry entries when it loads. Their automation
references are not rewritten. No ambient illuminance sensor is provided.

Update automations that used `number.*_brightness` (or a renamed brightness
number) to target the new light entity shown on the REMI device page. Entity IDs
can differ between installations; the following IDs are examples only.

```yaml
# Previously
service: number.set_value
target:
  entity_id: number.example_brightness
data:
  value: 40
```

```yaml
# Now
service: light.turn_on
target:
  entity_id: light.example_brightness
data:
  brightness_pct: 40
```

Use `light.turn_off` to switch the upper light off. An unqualified `light.turn_on`
uses the current/last nonzero intensity, or 100% when none is known. The last
nonzero intensity is included in Home Assistant's restore data, so it can also
be restored after a restart while the light is off. Current nonzero API data takes
precedence over saved intensity. Missing, invalid or out-of-range API values make
the new light unavailable instead of inventing a brightness.

For state conditions, use the light's `on`/`off` state. For numeric conditions,
use its `brightness` attribute (0–255), not the old number's 0–100 state. A stored
reference to the old lux sensor must be removed or replaced with an actual
ambient light sensor. Historical values are not converted or reinterpreted.

## Alarm Services

Alarms are managed via HA services (callable from automations or Developer Tools → Services).

### `remi.create_alarm`

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✅ | Alarm label |
| `time` | ✅ | ISO 8601 datetime (e.g. `2026-02-20T07:00:00.000Z`) |
| `enabled` | — | Active/inactive (default: `true`) |
| `repeat` | — | Days to repeat: `[0=Sun, 1=Mon, …, 6=Sat]` |
| `face_define` | — | Face at alarm time (e.g. `FACE_DAY`) |
| `volume` | — | Volume override (0–100) |

### `remi.update_alarm`

Same fields as `create_alarm`, plus `event_id` (required) — the `objectId` of the alarm to update.

### `remi.delete_alarm`

| Field | Required | Description |
|-------|----------|-------------|
| `event_id` | ✅ | The `objectId` of the alarm to delete |

---

## Credits

This integration was inspired by [Remi_UrbanHello_hass](https://github.com/pdruart/Remi_UrbanHello_hass) by [@pdruart](https://github.com/pdruart), which provided valuable insights into the alarm toggle functionality and brightness control.

---

## Disclaimer

This integration uses the official UrbanHello cloud API. It may break if UrbanHello changes their API. Use at your own risk.

## License

MIT

