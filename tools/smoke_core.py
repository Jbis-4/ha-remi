"""Run from the repository with `python -m tools.smoke_core`.

Load two synthetic REMIs in real HA Core, without the version-pinned pytest
plugin. All configuration writes go to a new temporary directory. Every REMI
API method is mocked; no credentials or production files are used.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import time
import logging
from tempfile import TemporaryDirectory
from types import MappingProxyType
from unittest.mock import AsyncMock, MagicMock, patch

import homeassistant  # Preload HA's httpx alias before any optional test plugins.
from homeassistant import bootstrap, loader
from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
from homeassistant.const import __version__
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.urbanhello_remi_unofficial.api import RemiApiClient
from custom_components.urbanhello_remi_unofficial.const import CONF_REMI_ID, DOMAIN
from tests.conftest import MOCK_EVENT_DATA, MOCK_FACES_DATA, MOCK_REMI_DATA


async def check(config_dir: str) -> None:
    """Exercise platform loading and service routing with real HA registries."""
    hass = HomeAssistant(config_dir)
    loader.async_setup(hass)
    hass.config.skip_pip = True
    hass.config_entries = ConfigEntries(hass, {})
    assert await bootstrap.async_load_base_functionality(hass)
    entries = []
    clients = []
    try:
        for index in range(2):
            remi_id = f"synthetic_remi_{index}"
            client = MagicMock(spec=RemiApiClient)
            client.remi_id = remi_id
            client.get_remi = AsyncMock(return_value={
                **deepcopy(MOCK_REMI_DATA), "objectId": remi_id,
                "uniqueID": f"synthetic_serial_{index}", "name": f"REMI {index}",
                "temp": 150 + 10 * index, "luminosity": 20 + 40 * index,
            })
            client.get_events = AsyncMock(return_value=[{
                **deepcopy(MOCK_EVENT_DATA[0]), "objectId": f"alarm_{index}",
            }])
            client.get_faces = AsyncMock(return_value=deepcopy(MOCK_FACES_DATA))
            client.get_config = AsyncMock(return_value={"params": {}})
            for name in ("update_event", "create_event", "delete_event", "update_remi"):
                setattr(client, name, AsyncMock(return_value={}))
            entry = ConfigEntry(
                domain=DOMAIN, unique_id=remi_id, title=f"REMI {index}",
                data={"username": "synthetic@example.invalid", "password": "synthetic",
                      CONF_REMI_ID: remi_id},
                source="user", version=1, minor_version=1, options={},
                discovery_keys=MappingProxyType({}), subentries_data=[],
            )
            with (
                patch("custom_components.urbanhello_remi_unofficial.RemiApiClient", return_value=client),
                patch("custom_components.urbanhello_remi_unofficial.async_get_clientsession"),
            ):
                await hass.config_entries.async_add(entry)
                await hass.async_block_till_done()
            assert entry.state is ConfigEntryState.LOADED, entry.state
            entries.append(entry)
            clients.append(client)

        registry = er.async_get(hass)
        for index, (entry, client) in enumerate(zip(entries, clients, strict=True)):
            def entity_id(domain: str, suffix: str) -> str:
                result = registry.async_get_entity_id(domain, DOMAIN, f"{entry.unique_id}_{suffix}")
                assert result is not None, (domain, suffix)
                assert registry.async_get(result).config_entry_id == entry.entry_id
                return result

            assert float(hass.states.get(entity_id("sensor", "temperature")).state) == 20 + 2 * index
            assert float(hass.states.get(entity_id("number", "brightness")).state) == 20 + 40 * index
            await hass.services.async_call("number", "set_value", {
                "entity_id": entity_id("number", "brightness"), "value": 35,
            }, blocking=True)
            client.update_remi.assert_awaited_once_with({"luminosity": 35})
            await hass.services.async_call("time", "set_value", {
                "entity_id": entity_id("time", f"alarm_alarm_{index}_time"), "time": time(8, 15),
            }, blocking=True)
            client.update_event.assert_awaited_once_with(f"alarm_{index}", {"event_time": [8, 15]})
            client.update_event.reset_mock()
            await hass.services.async_call("switch", "turn_off", {
                "entity_id": entity_id("switch", f"alarm_alarm_{index}"),
            }, blocking=True)
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
                clients[1].update_remi.assert_not_awaited()
                clients[1].update_event.assert_not_awaited()

        try:
            await hass.services.async_call(DOMAIN, "create_alarm", {
                "name": "Synthetic", "time": "07:00",
            }, blocking=True)
        except HomeAssistantError:
            pass
        else:
            raise AssertionError("Ambiguous alarm creation must be refused")
        for client in clients:
            client.create_event.assert_not_awaited()
        assert await hass.config_entries.async_unload(entries[0].entry_id)
        assert hass.services.has_service(DOMAIN, "update_alarm")
        clients[1].update_event.reset_mock()
        await hass.services.async_call(DOMAIN, "update_alarm", {
            "event_id": "alarm_1", "enabled": True,
        }, blocking=True)
        clients[1].update_event.assert_awaited_once_with("alarm_1", {"enabled": True})
        assert await hass.config_entries.async_unload(entries[1].entry_id)
        assert not hass.services.has_service(DOMAIN, "create_alarm")
        print(f"PASS: HA {__version__}; two entries, all eight platforms, isolated readings, "
              "brightness, alarm time/toggle/update/delete, ambiguous creation, unload")
    finally:
        await hass.async_stop(force=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    with TemporaryDirectory(prefix="remi-core-smoke-") as config_dir:
        asyncio.run(check(config_dir))
