"""Test sensor."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from gtfs_station_stop.arrival import Arrival
from gtfs_station_stop.vehicle import Vehicle
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from syrupy.assertion import SnapshotAssertion

from custom_components.gtfs_realtime.const import ROUTE_ID, TRIP_ID
from custom_components.gtfs_realtime.coordinator import (
    GtfsRealtimeCoordinator,
)
from custom_components.gtfs_realtime.sensor import ArrivalSensor
from tests.util import async_setup_coordinator


def assert_all_equal(collection: Iterable[Any]) -> None:
    assert len(set(collection)) <= 1


async def test_setup_sensors(hass: HomeAssistant, entry_v2_nodialout: MockConfigEntry):
    """Test setting ups sensors in integration."""
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
        assert hass.states.get("sensor.101n_101n_arrival_4").state == STATE_UNKNOWN  # ty: ignore[unresolved-attribute]
        # All Sensors of a station have the same device id
        ent_reg = er.async_get(hass)
        assert_all_equal(
            ent_reg.async_get(f"sensor.{s}").device_id
            for s in [f"101n_101n_arrival_{i}" for i in range(1, 5)]
        )
        assert_all_equal(
            ent_reg.async_get(f"sensor.{s}").device_id
            for s in [f"102s_102s_arrival_{i}" for i in range(1, 5)]
        )
        assert ent_reg.async_get(
            "sensor.101n_101n_arrival_1"
        ).device_id != ent_reg.async_get("sensor.102s_102s_arrival_1")


async def test_update(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    entry_v2_nodialout: MockConfigEntry,
    snapshot: SnapshotAssertion,
):
    """Smoke test the sensor platform."""
    start_time = datetime.now(tz=UTC)
    coordinator: GtfsRealtimeCoordinator = await async_setup_coordinator(
        hass, entry_v2_nodialout
    )
    coordinator.route_icons = None
    coordinator.hub.realtime_feed_uris = set()

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
                Arrival(route="AX", trip="AX1", time=make_ts(-10)),  # test old arrival
                Arrival(
                    route="A",
                    trip="A1",
                    time=make_ts(4),
                    vehicle=Vehicle(
                        trip_id="A1", latitude=45.0, longitude=-75.0, bearing=0.0
                    ),
                ),
                Arrival(route="B", trip="B1", time=make_ts(6)),
                Arrival(route="123-route", trip="123-test", time=make_ts(8)),
            ],
            "102S": [
                Arrival(route="X", trip="X1", time=make_ts(9)),
                Arrival(route="Y", trip="Y1", time=make_ts(13)),
                Arrival(route="Z", trip="Z1", time=make_ts(17)),
            ],
        }
        for stop_id, stop in coordinator.gtfs_update_data.station_stops.items():
            stop.arrivals = arrivals[stop_id]
        update_counter.update_count += 1

    coordinator.hub.async_update = AsyncMock()
    coordinator.hub.async_update.side_effect = coordinator_update_side_effects
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert coordinator.hub.async_update.call_count == 1

    for sensor in [f"101n_101n_arrival_{i}" for i in range(1, 5)] + [
        f"102s_102s_arrival_{i}" for i in range(1, 5)
    ]:
        sensor_data = hass.states.get(f"{SENSOR_DOMAIN}.{sensor}")
        assert sensor_data is not None
        assert snapshot(name=f"{sensor}-after-1-minute") == sensor_data.state, (
            f"failed assertion for sensor {sensor}"
        )
        assert snapshot(name=f"{sensor}-attributes-after-1-minute") == dict(
            sensor_data.attributes
        ), f"failed assertion for sensor {sensor}"


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


@pytest.mark.parametrize(
    ("arrival_seconds", "departure_seconds", "expected_seconds"),
    [
        pytest.param(300, None, 300, id="arrival-only"),
        pytest.param(None, 300, 300, id="departure-only"),
        pytest.param(300, 600, 300, id="both-arrival-first"),
        pytest.param(300, 60, 300, id="both-departure-first"),
        pytest.param(None, None, None, id="neither"),
    ],
)
async def test_update_prediction_time(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    entry_v2_nodialout: MockConfigEntry,
    arrival_seconds: int | None,
    departure_seconds: int | None,
    expected_seconds: int | None,
):
    """Prefer arrival times and fall back to departure times when absent."""
    coordinator = await async_setup_coordinator(hass, entry_v2_nodialout)
    sensor = ArrivalSensor(coordinator, "101N", 0)
    now = datetime.now(tz=UTC).timestamp()
    sensor.station_stop.arrivals = [
        Arrival(
            route="A",
            trip="A1",
            time=now + arrival_seconds if arrival_seconds is not None else None,
            departure_time=(
                now + departure_seconds if departure_seconds is not None else None
            ),
        )
    ]

    sensor.update()

    assert sensor.native_value == expected_seconds
    assert sensor.extra_state_attributes[TRIP_ID] == "A1"
    assert sensor.extra_state_attributes[ROUTE_ID] == "A"


@pytest.mark.parametrize("time_field", ["time", "departure_time"])
@pytest.mark.parametrize(
    ("seconds", "expected_seconds"),
    [(-3600, None), (-121, None), (-120, None), (-119, 0), (-1, 0), (0, 0), (1, 1)],
)
async def test_update_prediction_time_tolerance(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    entry_v2_nodialout: MockConfigEntry,
    time_field: str,
    seconds: int,
    expected_seconds: int | None,
):
    """Apply the same stale cutoff and zero clamp to either prediction time."""
    coordinator = await async_setup_coordinator(hass, entry_v2_nodialout)
    sensor = ArrivalSensor(coordinator, "101N", 0)
    now = datetime.now(tz=UTC).timestamp()
    prediction = Arrival(route="A", trip="A1")
    setattr(prediction, time_field, now + seconds)
    if time_field == "time":
        # A valid departure must not override a zero, negative, or stale arrival.
        prediction.departure_time = now + 300
    sensor.station_stop.arrivals = [prediction]

    sensor.update()

    assert sensor.native_value == expected_seconds
    if expected_seconds is None:
        assert sensor.extra_state_attributes == {}
    else:
        assert sensor.extra_state_attributes[TRIP_ID] == "A1"


@pytest.mark.parametrize("reverse", [False, True])
async def test_update_mixed_prediction_order(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    entry_v2_nodialout: MockConfigEntry,
    reverse: bool,
):
    """Order mixed predictions by effective time, with untimed records last."""
    coordinator = await async_setup_coordinator(hass, entry_v2_nodialout)
    sensors = [ArrivalSensor(coordinator, "101N", idx) for idx in range(6)]
    now = datetime.now(tz=UTC).timestamp()
    predictions = [
        Arrival(route="A", trip="untimed"),
        Arrival(route="A", trip="late-departure", departure_time=now + 600),
        Arrival(route="A", trip="stale-departure", departure_time=now - 3600),
        Arrival(route="A", trip="arrival", time=now + 300),
        Arrival(route="A", trip="early-departure", departure_time=now + 60),
        Arrival(route="A", trip="both", time=now + 180, departure_time=now + 900),
    ]
    sensors[0].station_stop.arrivals = predictions[::-1] if reverse else predictions

    for sensor in sensors:
        sensor.update()

    assert [sensor.native_value for sensor in sensors] == [
        60,
        180,
        300,
        600,
        None,
        None,
    ]
    assert [sensor.extra_state_attributes.get(TRIP_ID) for sensor in sensors] == [
        "early-departure",
        "both",
        "arrival",
        "late-departure",
        "untimed",
        None,
    ]


async def test_update_departure_prediction_expires(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    entry_v2_nodialout: MockConfigEntry,
):
    """Clear a departure-only prediction and its attributes once it is stale."""
    coordinator = await async_setup_coordinator(hass, entry_v2_nodialout)
    sensor = ArrivalSensor(coordinator, "101N", 0)
    sensor.station_stop.arrivals = [
        Arrival(
            route="A", trip="A1", departure_time=datetime.now(tz=UTC).timestamp() + 60
        )
    ]

    sensor.update()
    assert sensor.native_value == 60
    assert sensor.extra_state_attributes[TRIP_ID] == "A1"

    freezer.tick(timedelta(seconds=179))
    sensor.update()
    assert sensor.native_value == 0
    assert sensor.extra_state_attributes[TRIP_ID] == "A1"

    freezer.tick(timedelta(seconds=1))
    sensor.update()
    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {}
