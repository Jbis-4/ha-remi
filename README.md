# Home Assistant REMI Integration — Jbis-4 fork

> **Unofficial** Home Assistant integration for the [UrbanHello Remi](https://www.urbanhello.com/) smart alarm clock.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

This repository is a fork of [timoa/ha-remi](https://github.com/timoa/ha-remi),
the original Home Assistant integration created by [@timoa](https://github.com/timoa).
It adds fixes developed and tested on two physical REMI devices running
firmware versions **329 and 332**.

Relevant fixes are proposed to the original project through focused pull requests.
An open PR is a proposal and does not mean the maintainer has accepted or merged it.
This community integration is **not affiliated with or endorsed by UrbanHello**.

## Changes in this fork

| Change | Description | Upstream status |
|--------|-------------|-----------------|
| Temperature | Corrected the raw temperature conversion to `(temp + 40) / 10`. | [PR #21](https://github.com/timoa/ha-remi/pull/21) — Open |
| Brightness | Replaced the old number entity with a dimmable light that restores its previous nonzero brightness when switched on; removed the misleading illuminance sensor. | [PR #23](https://github.com/timoa/ha-remi/pull/23) — Open |
| RGB entities | Removed the ineffective Night Light control and clarified the App Background Color entity. | [PR #24](https://github.com/timoa/ha-remi/pull/24) — Open |
| Noise Alert Threshold | Extended the supported range from 0–100 to 0–250. | [PR #22](https://github.com/timoa/ha-remi/pull/22) — Open |
| Multi-REMI reliability | Preserve the selected device identifier during API reconnections and verify device identity in API responses to avoid mixing devices. | Fork only — not yet submitted upstream |

Upstream status checked on **23 October 2026**. All four linked PRs are open and
have not been merged; follow the links for their current status. The features
and migration notes below describe this fork. The original version may differ.

---

## Features

- **Sensors**: Room temperature, WiFi signal strength, firmware version, IP address, current face
- **Binary Sensors**: Online status, alive status, firmware update available
- **Select**: Clock face (Off / Awake / Sleepy / Semi-Awake / Smiley), clock format (12h / 24h), music mode
- **Number**: Volume, noise alert threshold
- **Switch**: Per-alarm enable/disable toggles (one switch per alarm)
- **Lights**: Brightness (dimmable), app background color (RGB)
- **Alarm CRUD**: Create, update and delete alarms via HA services

---

## Requirements

- Home Assistant 2024.1 or newer
- An UrbanHello account (username + password from the Remi app)

---

## Installation

### Original version — HACS catalog

1. Open **HACS** and search the catalog for **Remi**.
2. Select the original integration from [timoa/ha-remi](https://github.com/timoa/ha-remi).
3. Download it and restart Home Assistant.

### This fork — HACS custom repository

1. Open **HACS** → **⋮** → **Custom repositories**.
2. Add `https://github.com/Jbis-4/ha-remi` with type **Integration**.
3. Select this fork's **Remi** entry and download it.
4. Restart Home Assistant.

The changes described here are on this fork's `main` branch. If HACS offers a
version selector, choose a version containing these changes.

**Choose one version.** The original and this fork use the same integration
domain, `urbanhello_remi_unofficial`, and the same `custom_components` folder.
They must not be installed simultaneously. When switching versions, replace the
existing installation rather than keeping both copies.

### Manual

1. Copy the `custom_components/urbanhello_remi_unofficial/` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

---

## Configuration

1. Go to **Settings → Integrations → Add Integration**
2. Search for **Remi**
3. Enter your UrbanHello account **username** and **password**
4. The integration authenticates and discovers the REMIs on your account.
5. If several devices are found, select the one to add. Repeat the setup for each REMI.

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
| Music Mode | Select | API mode selection; mapping remains unverified |
| Volume | Number | Speaker volume (0–100) |
| Brightness | Light | Dimmable upper light (off at 0%, maximum at 100%) |
| Noise Alert Threshold | Number | Noise notification threshold (0–250) |
| App Background Color | Light | Color associated with the REMI in the official app |
| Alarm (per alarm) | Switch | Enable/disable individual alarms |

The Music Mode labels, including the option labelled `White Noise`, remain
unverified. Their presence in the selector does not confirm the corresponding
playback behavior.

---

## Brightness migration

Brightness is now a dimmable `light`, using the same API `luminosity` setting
(0–100). The old `number` and the incorrectly labelled lux sensor are no longer
created. Previously registered entities may remain unavailable and can be removed
manually in Home Assistant. These obsolete entries are not automatically deleted
from the entity registry, and automation references are not rewritten. No ambient
illuminance sensor is provided.

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

## RGB entity changes

`App Background Color` changes the color associated with a REMI in the official
UrbanHello app. It remains an RGB `light` with the same unique ID, existing
entity ID and commands. Existing automations continue to target the same entity;
a user-defined display name is preserved by Home Assistant.

The former RGB `Night Light` entity has been removed. Commands to `lightnight`
had no observable physical effect on two tested REMIs running firmware 329 and
332. The field was initially absent on one device and appeared after RGB write
experiments. These observations do not establish hardware support on other
models. This integration no longer writes `lightnight` and does not delete or
reset existing values on UrbanHello's servers.

The obsolete Night Light entry may remain unavailable after an upgrade. Remove
it manually along with references in dashboards, scripts and automations, or
remove and re-add the integration if you do not need to retain its entities.
These obsolete light entries are not automatically deleted. The app background
color is not a replacement for a physical light.

## Alarm Services

Alarms are managed via HA services (callable from automations or Developer Tools → Services).

### `urbanhello_remi_unofficial.create_alarm`

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✅ | Alarm label |
| `time` | ✅ | ISO 8601 datetime (e.g. `2026-02-20T07:00:00.000Z`) |
| `enabled` | — | Active/inactive (default: `true`) |
| `repeat` | — | Days to repeat: `[0=Sun, 1=Mon, …, 6=Sat]` |
| `face_define` | — | Face at alarm time (e.g. `FACE_DAY`) |
| `volume` | — | Volume override (0–100) |

### `urbanhello_remi_unofficial.update_alarm`

Same fields as `create_alarm`, plus `event_id` (required) — the `objectId` of the alarm to update.

### `urbanhello_remi_unofficial.delete_alarm`

| Field | Required | Description |
|-------|----------|-------------|
| `event_id` | ✅ | The `objectId` of the alarm to delete |

---

## Credits

The original integration was created by [@timoa](https://github.com/timoa):
[timoa/ha-remi](https://github.com/timoa/ha-remi).

This integration was inspired by [Remi_UrbanHello_hass](https://github.com/pdruart/Remi_UrbanHello_hass) by [@pdruart](https://github.com/pdruart), which provided valuable insights into the alarm toggle functionality and brightness control.

---

## Disclaimer

This integration uses the official UrbanHello cloud API. It may break if UrbanHello changes their API. Use at your own risk.

## License

MIT

