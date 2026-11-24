"""Exercise two loaded devices through HA, with synthetic cloud responses only."""
from copy import deepcopy
from datetime import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.urbanhello_remi_unofficial.const import CONF_REMI_ID, DOMAIN
from .conftest import MOCK_EVENT_DATA, MOCK_FACES_DATA, MOCK_REMI_DATA


@pytest.fixture
async def two_remis(hass, enable_custom_integrations, mock_config_entry_data):
    """Load two independent entries sharing an account, with distinct alarms."""
    devices = []
    for index in range(2):
        remi_id = f"device_{index}"
        entry = MockConfigEntry(
            domain=DOMAIN, unique_id=remi_id,
            data={**mock_config_entry_data, CONF_REMI_ID: remi_id},
            title=f"REMI {index}",
        )
        entry.add_to_hass(hass)
        client = MagicMock()
        client.remi_id = remi_id
        client.get_remi = AsyncMock(return_value={
            **deepcopy(MOCK_REMI_DATA), "objectId": remi_id,
            "name": f"REMI {index}", "uniqueID": f"synthetic_serial_{index}",
            "temp": 150 + 10 * index, "luminosity": 20 + 40 * index,
        })
        client.get_events = AsyncMock(return_value=[{
            **deepcopy(MOCK_EVENT_DATA[0]), "objectId": f"alarm_{index}",
        }])
        client.get_faces = AsyncMock(return_value=deepcopy(MOCK_FACES_DATA))
        client.get_config = AsyncMock(return_value={"params": {}})
        for method in ("update_remi", "update_event", "create_event", "delete_event"):
            setattr(client, method, AsyncMock(return_value={}))
        with (
            patch("custom_components.urbanhello_remi_unofficial.RemiApiClient", return_value=client),
            patch("custom_components.urbanhello_remi_unofficial.async_get_clientsession"),
        ):
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
        devices.append((entry, client))
    return devices


async def test_entities_and_alarm_commands_stay_on_their_device(hass, two_remis):
    """Check unique identities, readings and all editable alarm/brightness paths."""
    registry = er.async_get(hass)
    for index, (entry, client) in enumerate(two_remis):
        remi_id = entry.data[CONF_REMI_ID]
        temperature = registry.async_get_entity_id("sensor", DOMAIN, f"{remi_id}_temperature")
        assert float(hass.states.get(temperature).state) == 20 + 2 * index
        brightness = registry.async_get_entity_id("number", DOMAIN, f"{remi_id}_brightness")
        assert float(hass.states.get(brightness).state) == 20 + 40 * index
        assert registry.async_get_entity_id("light", DOMAIN, f"{remi_id}_brightness") is None
        assert registry.async_get_entity_id("sensor", DOMAIN, f"{remi_id}_luminosity") is None
        for entity_id in (temperature, brightness):
            assert registry.async_get(entity_id).config_entry_id == entry.entry_id

        await hass.services.async_call("number", "set_value", {
            "entity_id": brightness, "value": 35,
        }, blocking=True)
        client.update_remi.assert_awaited_once_with({"luminosity": 35})
        alarm_time = registry.async_get_entity_id("time", DOMAIN, f"{remi_id}_alarm_alarm_{index}_time")
        await hass.services.async_call("time", "set_value", {
            "entity_id": alarm_time, "time": time(8, 15),
        }, blocking=True)
        client.update_event.assert_awaited_once_with(f"alarm_{index}", {"event_time": [8, 15]})
        client.update_event.reset_mock()
        switch = registry.async_get_entity_id("switch", DOMAIN, f"{remi_id}_alarm_alarm_{index}")
        await hass.services.async_call("switch", "turn_off", {"entity_id": switch}, blocking=True)
        client.update_event.assert_awaited_once_with(f"alarm_{index}", {"enabled": False})
        client.update_event.reset_mock()
        await hass.services.async_call(DOMAIN, "update_alarm", {
            "event_id": f"alarm_{index}", "time": "06:45", "repeat": [1, 5],
        }, blocking=True)
        client.update_event.assert_awaited_once_with(f"alarm_{index}", {
            "event_time": [6, 45], "recurrence": [1, 0, 0, 0, 1, 0, 0],
        })
        await hass.services.async_call(DOMAIN, "delete_alarm", {
            "event_id": f"alarm_{index}",
        }, blocking=True)
        client.delete_event.assert_awaited_once_with(f"alarm_{index}")
        if index == 0:
            other = two_remis[1][1]
            other.update_remi.assert_not_awaited()
            other.update_event.assert_not_awaited()
            other.delete_event.assert_not_awaited()


async def test_ambiguous_creation_is_refused_and_unload_keeps_other_device(hass, two_remis):
    """Document the official limitation and verify service lifetime with two entries."""
    with pytest.raises(HomeAssistantError, match="single loaded REMI"):
        await hass.services.async_call(DOMAIN, "create_alarm", {
            "name": "Morning", "time": "07:00",
        }, blocking=True)
    for _, client in two_remis:
        client.create_event.assert_not_awaited()
    assert await hass.config_entries.async_unload(two_remis[0][0].entry_id)
    assert hass.services.has_service(DOMAIN, "update_alarm")
    await hass.services.async_call(DOMAIN, "update_alarm", {
        "event_id": "alarm_1", "enabled": False,
    }, blocking=True)
    two_remis[1][1].update_event.assert_awaited_once_with("alarm_1", {"enabled": False})
    two_remis[0][1].update_event.assert_not_awaited()
    assert await hass.config_entries.async_unload(two_remis[1][0].entry_id)
    assert not hass.services.has_service(DOMAIN, "create_alarm")
