"""Test sensor."""

from gtfs_station_stop.alert import Alert

from datetime import timedelta, datetime
from dataclasses import dataclass

from freezegun.api import FrozenDateTimeFactory

from tests.util import async_setup_coordinator
from custom_components.gtfs_realtime.coordinator import GtfsRealtimeCoordinator

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.core import State

from unittest.mock import AsyncMock, patch

from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)


async def test_setup_binary_sensors(
    hass: HomeAssistant, entry_v2_nodialout: MockConfigEntry
):
    """Test setting up binary sensors for integration."""
    with (
        patch(
            "custom_components.gtfs_realtime.coordinator.GtfsRealtimeCoordinator._async_update_data",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.gtfs_realtime.coordinator.GtfsRealtimeCoordinator.async_update_static_data",
            new_callable=AsyncMock,
        ),
    ):
        entry_v2_nodialout.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry_v2_nodialout.entry_id)
        await hass.async_block_till_done()

        alert_1 = hass.states.get("binary_sensor.1_service_alerts")
        assert isinstance(alert_1, State)
        assert alert_1.state == STATE_OFF

        alert_2 = hass.states.get("binary_sensor.2_service_alerts")
        assert isinstance(alert_2, State)
        assert alert_2.state == STATE_OFF


async def test_binary_sensor_header_and_descriptions(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    entry_v2_nodialout: MockConfigEntry,
):
    hass.config.language = "en"  # Pin the language for this test
    start_time = datetime.now()
    coordinator: GtfsRealtimeCoordinator = await async_setup_coordinator(
        hass, entry_v2_nodialout
    )
    coordinator.route_icons = None
    coordinator.hub.realtime_feed_uris = []

    @dataclass
    class UpdateCounter:
        """Class to count updates."""

        update_count: int = 0

    update_counter = UpdateCounter(update_count=0)

    def make_ts(minutes) -> float:
        return (
            start_time + timedelta(minutes=minutes - update_counter.update_count)
        ).timestamp()

    def coordinator_update_side_effects(_):
        next(iter(coordinator.hub.subscribers["1"])).alerts = [
            Alert(
                freezer.time_to_freeze.timestamp() + 1000,
                {"en": "Alert"},
                {"EN": "There is a problem"},
            )
        ]
        next(iter(coordinator.hub.subscribers["2"])).alerts = [
            Alert(
                freezer.time_to_freeze.timestamp() + 1000,
                {"en-AU": "Alert"},
                {"en-AU": "There is a problem down under"},
            )
        ]
        update_counter.update_count += 1
        return

    coordinator.hub.async_update = AsyncMock()  # ty:ignore[invalid-assignment]
    coordinator.hub.async_update.side_effect = coordinator_update_side_effects  # ty:ignore[unresolved-attribute]
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert coordinator.hub.async_update.call_count == 1  # ty:ignore[unresolved-attribute]

    alert_sensor_1_data = hass.states.get(f"{BINARY_SENSOR_DOMAIN}.1_service_alerts")
    assert alert_sensor_1_data is not None
    assert alert_sensor_1_data.state == "on"
    assert alert_sensor_1_data.attributes["header_1"] == "Alert"
    assert alert_sensor_1_data.attributes["description_1"] == "There is a problem"

    alert_sensor_2_data = hass.states.get(f"{BINARY_SENSOR_DOMAIN}.2_service_alerts")
    assert alert_sensor_2_data is not None
    assert alert_sensor_2_data.state == "on"
    assert alert_sensor_2_data.attributes["header_1"] == "Alert"
    assert (
        alert_sensor_2_data.attributes["description_1"]
        == "There is a problem down under"
    )

    alert_sensor_3_data = hass.states.get(f"{BINARY_SENSOR_DOMAIN}.3_service_alerts")
    assert alert_sensor_3_data is not None
    assert alert_sensor_3_data.state == "off"
