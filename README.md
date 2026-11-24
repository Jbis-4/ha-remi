# Home Assistant REMI Integration — Jbis-4 fork

> **Unofficial** Home Assistant integration for the [UrbanHello Remi](https://www.urbanhello.com/) smart alarm clock.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

This repository is a fork of [timoa/ha-remi](https://github.com/timoa/ha-remi).
The temporary synchronization branch prepares upstream `main` at `034066f`
(version 0.2.8), fetched on 24 November 2026, on top of the fork's `63eb3c8`.
The full fork history is retained; no rebase or squash is used.

Fork PRs [#21](https://github.com/timoa/ha-remi/pull/21),
[#22](https://github.com/timoa/ha-remi/pull/22),
[#23](https://github.com/timoa/ha-remi/pull/23) and
[#24](https://github.com/timoa/ha-remi/pull/24) are present in upstream's history.
The newer official brightness slider and temperature decoding supersede the
corresponding fork implementations. Local privacy protection for API errors and
manual cleanup of legacy entity entries are retained.

See [the synchronization review](docs/SYNC_UPSTREAM_2026-11-24.md) for migration
steps, compatibility checks and the remaining two-device alarm limitation.
This integration is **not affiliated with or endorsed by UrbanHello**.

---

## Features

- **Sensors**: Room temperature, WiFi signal strength, firmware version, IP address, current face
- **Binary Sensors**: Online status, alive status, firmware update available
- **Select**: Clock face (Off / Awake / Sleepy / Semi-Awake / Smiley), clock format (12h / 24h), music mode
- **Number**: Volume, noise alert threshold, brightness
- **Switch**: Per-alarm enable/disable toggles (one switch per alarm)
- **Time**: Edit each alarm's hour and minute directly in Home Assistant
- **Lights**: App background color (RGB)
- **Alarm CRUD**: Create, update and delete alarms via HA services

---

## Requirements

- Compatibility is tested on the HA versions listed in the synchronization review.
  The old upstream claim of HA 2024.1 compatibility has not been validated.
- An UrbanHello account (username + password from the Remi app)

---

## Installation

### Via HACS

1. Open HACS in Home Assistant
2. Go to **Integrations** → **⋮** → **Custom repositories**
3. Choose `https://github.com/Jbis-4/ha-remi` for this fork, or
   `https://github.com/timoa/ha-remi` for the original integration, as an **Integration**
4. Search for **Remi** and install it
5. Restart Home Assistant

The fork and original use the same domain and cannot be installed side by side.
This temporary branch is a local preparation, not a published HACS release.

### Manual

1. Copy the `custom_components/urbanhello_remi_unofficial/` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

---

## Configuration

1. Go to **Settings → Integrations → Add Integration**
2. Search for **Remi**
3. Enter your UrbanHello account **username** and **password**
4. The integration authenticates and discovers the devices on your account.
5. Select the device to add. Repeat setup for the second REMI.

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
| Check firmware status | Button | Refresh device firmware status without installing firmware |
| Clock Face | Select | Change the displayed face |
| Clock Format | Select | 12h or 24h format |
| Music Mode | Select | Normal / Single track / Repeat track / Repeat playlist |
| Volume | Number | Speaker volume (0–100) |
| Brightness | Number | Upper light brightness (0–100) |
| Noise Alert Threshold | Number | Noise notification threshold (0–250) |
| App Background Color | Light | Color associated with the REMI in the official app |
| Alarm (per alarm) | Switch | Enable/disable individual alarms |
| Alarm time (per alarm) | Time | Edit the alarm in the REMI's local time zone |

---


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

In this fork, obsolete Night Light registry entries remain for manual cleanup.
Remove references from dashboards, scripts and automations before deleting the
old entity through HA. App background color does not control a physical light.

## Brightness migration

Brightness is a `number` slider on the REMI brightness scale (0–100), like
Volume and Noise Alert Threshold. It drives the same API `luminosity` setting
as before.

Earlier releases exposed that setting as a dimmable `light`, and before that as
a `number` named "Screen Brightness" next to an incorrectly labelled lux
sensor. In this fork, obsolete registry entries remain for manual cleanup.
They no longer have an implementation and can become unavailable. Their
automation references are not rewritten.
No ambient illuminance sensor is provided.

Update automations that used `light.*_brightness` to target the number entity
shown on the REMI device page. Entity IDs can differ between installations; the
following IDs are examples only.

```yaml
# Previously
service: light.turn_on
target:
  entity_id: light.example_brightness
data:
  brightness_pct: 40
```

```yaml
# Now
service: number.set_value
target:
  entity_id: number.example_brightness
data:
  value: 40
```

The number uses the REMI 0–100 scale, so a former `brightness_pct` value maps
to the same number. `0` switches the upper light off.

The light entity's "last nonzero intensity" behaviour is gone: the number has
no separate on/off state, so a slider left at `0` stays at `0`. For state
conditions, use the number's 0–100 state, not the former light's 0–255
`brightness` attribute. A stored reference to the old lux sensor must be
removed or replaced with an actual ambient light sensor. Historical values are
not converted or reinterpreted.

Missing, invalid or out-of-range API values leave the number unknown instead
of inventing a brightness.


## Temperature conversion

The Celsius conversion is `(raw - 50) / 5`, verified in the supplied
Android app build 3.4.23 (`com.app.urbanhello`). For example, raw `160` is **22.0 °C**, not 20.0 °C.
This integration preserves the fractional result and suggests one decimal place;
the app truncates its display to a whole number. Keeping decimals does not
establish the physical sensor's accuracy. Missing or invalid measurements remain
unknown. The sensor exposes the raw value and conversion as diagnostic attributes.

Existing temperature history is not rewritten. A change in the graph at upgrade
time can reflect the corrected conversion rather than a change in the room.
Protocol evidence is recorded in [the analysis notes](docs/protocol-3.4.23.json).

## Music mode correction

The app uses `musicMode` for playback behaviour: `0` = Normal, `1` = Single track,
`2` = Repeat track, `3` = Repeat playlist. The previous Off / Music / White Noise
labels were incorrect. The select entity retains its unique ID, but automations
that select or compare the old option names must be updated. This setting does
not select an audio file or start playback.

## Firmware status and connection recovery

The firmware alert uses the device's `firmware_need_update` flag or its
`update_firmware_version` target. The server-wide default version is informational:
it does not prove that a newer version has been assigned to this REMI. Missing
device firmware information is reported as unknown rather than as an update.

The firmware alert includes installed, assigned target and server default versions
as attributes. **Check firmware status** refreshes the device and cloud metadata;
it does not install firmware. UrbanHello manages normal firmware updates
automatically while REMI is connected to Wi-Fi. See the
[manufacturer's update instructions](https://www.urbanhello.com/fr/faq/faqs/comment-mettre-a-jour-remi-manuellement-).

Cloud reads use a 15-second request timeout and at most three attempts for
connection failures or HTTP 500/502/503/504 responses. Device writes and alarm
creation/deletion are not automatically replayed after such failures. Session
renewal preserves the selected REMI. Alarm services resolve the currently loaded
integration, so reloading it does not leave actions attached to an old client.

Alarm creation without an explicit device selector is supported when exactly one
REMI is loaded. With several devices it now fails explicitly instead of silently
using the first one. Update/delete actions locate the loaded device by event ID.

## Upstream validation (reported by upstream)

The following paragraph records upstream evidence, not validation of this fork
or of the two REMIs on this installation. Local results are in the synchronization review.


The automated suite passed with Python 3.14.9 and Home Assistant 2026.10.4:
248 passed, 2 skipped, 1 non-strict XPASS; coverage 97.32%.

After installation and a full restart on Home Assistant 2026.11.0, one REMI
running firmware 332 reported 22.0 °C for raw temperature 160, no pending
firmware update, the correct weekdays and four editable alarm times. Existing
entity identifiers, alarm times and enabled states were preserved. No integration
errors were observed in the startup logs. Alarm writes were tested with a mocked
API; the deployment checks did not change the physical device's schedule.

## Alarm Services

Alarms are managed via HA services (callable from automations or Developer Tools → Services).

### `urbanhello_remi_unofficial.create_alarm`

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✅ | Alarm label |
| `time` | ✅ | Local clock time in the REMI time zone (e.g. `07:00`) |
| `enabled` | — | Active/inactive (default: `true`) |
| `repeat` | — | Days to repeat: `[0=Sun, 1=Mon, …, 6=Sat]` |
| `face_define` | — | Face at alarm time (e.g. `FACE_DAY`) |
| `volume` | — | Volume override (0–100) |

The time entity and services write the actual `event_time` clock array used by
the app. ISO datetime inputs are now rejected: these alarms use a local clock
time, not a UTC date. Update existing service calls to use `HH:MM` (or
`HH:MM:00`). Nonzero seconds are rejected rather than silently discarded.

The cloud's `recurrence` array starts on Monday. Alarm attributes now display
the correct weekdays. The existing service input convention (`repeat`,
Sunday=0) is preserved and converted to that cloud array.

### `urbanhello_remi_unofficial.update_alarm`

Same fields as `create_alarm`, plus `event_id` (required) — the `objectId` of the alarm to update.

### `urbanhello_remi_unofficial.delete_alarm`

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

