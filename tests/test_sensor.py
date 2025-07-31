"""Test sensor."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
from gtfs_station_stop.arrival import Arrival
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from syrupy.assertion import SnapshotAssertion

from custom_components.gtfs_realtime.const import ROUTE_ID
from custom_components.gtfs_realtime.coordinator import (
    GtfsRealtimeCoordinator,
    GtfsUpdateData,
)

from custom_components.gtfs_realtime.sensor import ArrivalSensor


def assert_all_equal(collection: Iterable[Any]) -> bool:
    assert len(set(collection)) <= 1


async def test_setup_sensors(hass: HomeAssistant, entry_v2_nodialout: MockConfigEntry):
    """Test setting ups sensors in integration."""
    with (
        patch(
            "custom_components.gtfs_realtime.coordinator.GtfsRealtimeCoordinator._async_update_data",  # noqa E501
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.gtfs_realtime.coordinator.GtfsRealtimeCoordinator.async_update_static_data",  # noqa E501
            new_callable=AsyncMock,
        ),
    ):
        entry_v2_nodialout.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry_v2_nodialout.entry_id)
        await hass.async_block_till_done()
        assert hass.states.get("sensor.4_101n").state == STATE_UNKNOWN
        # All Sensors of a station have the same device id
        ent_reg = er.async_get(hass)
        assert_all_equal(
            ent_reg.async_get(f"sensor.{s}").device_id
            for s in ["1_101n", "2_101n", "3_101n", "4_101n"]
        )
        assert_all_equal(
            ent_reg.async_get(f"sensor.{s}").device_id
            for s in ["1_102s", "2_102s", "3_102s", "4_102s"]
        )
        assert ent_reg.async_get("sensor.1_101n").device_id != ent_reg.async_get(
            "sensor.1_102s"
        )


async def async_setup_coordinator(
    hass: HomeAssistant, entry_v2_nodialout: MockConfigEntry
) -> GtfsRealtimeCoordinator:
    """Setup the Coordinator."""
    with (
        patch(
            "custom_components.gtfs_realtime.coordinator.FeedSubject.async_update",  # noqa E501
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "custom_components.gtfs_realtime.coordinator.GtfsRealtimeCoordinator.async_update_static_data",  # noqa E501
            new_callable=AsyncMock,
            return_value=GtfsUpdateData(),
        ),
    ):
        entry_v2_nodialout.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry_v2_nodialout.entry_id)
        await hass.async_block_till_done()

    return entry_v2_nodialout.runtime_data


async def test_update(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    entry_v2_nodialout: MockConfigEntry,
    snapshot: SnapshotAssertion,
):
    """Smoke test the sensor platform."""
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
        arrivals = {
            "101N": [
                Arrival(route="A", trip="", time=make_ts(4)),
                Arrival(route="B", trip="", time=make_ts(6)),
                Arrival(route="C", trip="", time=make_ts(8)),
            ],
            "102S": [
                Arrival(route="X", trip="", time=make_ts(9)),
                Arrival(route="Y", trip="", time=make_ts(13)),
                Arrival(route="Z", trip="", time=make_ts(17)),
            ],
        }
        for stop_id, stop in coordinator.gtfs_update_data.station_stops.items():
            stop.arrivals = arrivals[stop_id]
        update_counter.update_count += 1
        return

    coordinator.hub.async_update = AsyncMock()
    coordinator.hub.async_update.side_effect = coordinator_update_side_effects
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert coordinator.hub.async_update.call_count == 1

    for sensor in [
        "1_101n",
        "2_101n",
        "3_101n",
        "4_101n",
        "1_102s",
        "2_102s",
        "3_102s",
        "4_102s",
    ]:
        assert (
            snapshot(name=f"{sensor}-after-1-minute")
            == hass.states.get(f"{SENSOR_DOMAIN}.{sensor}").state
        )


async def test_route_icon_missing_route_id(
    hass: HomeAssistant, entry_v2_nodialout: MockConfigEntry
):
    """Test that missing route ID does not break the sensor."""
    coordinator: GtfsRealtimeCoordinator = await async_setup_coordinator(
        hass, entry_v2_nodialout
    )
    coordinator.route_icons = "http://example.com/{}.png"
    sensor = ArrivalSensor(coordinator, "1", 0)
    sensor._arrival_detail[ROUTE_ID] = ""
    assert sensor.entity_picture is not None
    sensor._arrival_detail[ROUTE_ID] = None
    assert sensor.entity_picture is None
