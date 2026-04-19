"""Common utils shared between tests."""

from unittest.mock import AsyncMock, patch

from gtfs_station_stop.route_info import RouteInfo, RouteType
from gtfs_station_stop.trip_info import TripInfo
from gtfs_station_stop.schedule import GtfsSchedule
from custom_components.gtfs_realtime.coordinator import GtfsRealtimeCoordinator

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def async_setup_coordinator(
    hass: HomeAssistant, entry_v2_nodialout: MockConfigEntry
) -> GtfsRealtimeCoordinator:
    """Setup the Coordinator."""
    static_update_data = GtfsSchedule()
    static_update_data.route_info_ds.route_infos["123"] = RouteInfo(
        {
            "route_id": "123",
            "route_short_name": "123",
            "route_type": RouteType.SUBWAY.value,
            "route_color": "FFFFFF",
            "route_text_color": "888888",
        }
    )
    static_update_data.trip_info_ds.trip_infos["123-test"] = TripInfo(
        {
            "route_id": "123",
            "trip_id": "123-test",
            "service_id": "SVC",
            "trip_headsign": "Downtown",
            "trip_short_name": "123-test",
            "direction_id": "Northbound",
        }
    )

    with (
        patch(
            "custom_components.gtfs_realtime.coordinator.FeedSubject.async_update",  # noqa E501
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "custom_components.gtfs_realtime.coordinator.GtfsRealtimeCoordinator.async_update_static_data",  # noqa E501
            new_callable=AsyncMock,
            return_value=static_update_data,
        ),
    ):
        entry_v2_nodialout.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry_v2_nodialout.entry_id)
        await hass.async_block_till_done()

    return entry_v2_nodialout.runtime_data
