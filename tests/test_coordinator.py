"""Test Coordinator."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
from gtfs_station_stop.feed_subject import FeedSubject
from gtfs_station_stop.schedule import GtfsSchedule
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.gtfs_realtime.coordinator import GtfsRealtimeCoordinator


def test_coordinator_construction(hass: HomeAssistant):
    """Smoke test for creating a coordinator."""
    GtfsRealtimeCoordinator(hass, feed_subject=FeedSubject([]))


async def test_update_static_data(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    entry_v2_full: MockConfigEntry,
    mock_schedule: GtfsSchedule,
):
    """Test updates through the coordinator."""

    with (
        patch(
            "custom_components.gtfs_realtime.coordinator.FeedSubject.async_update",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "custom_components.gtfs_realtime.coordinator.async_build_schedule",
            new_callable=AsyncMock,
            return_value=mock_schedule,
        ) as async_build_schedule_mock,
        patch(
            "custom_components.gtfs_realtime.coordinator.GtfsSchedule.async_update_schedule",
            new_callable=AsyncMock,
            return_value=None,
        ) as async_update_schedule_mock,
    ):
        entry_v2_full.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry_v2_full.entry_id)
        await hass.async_block_till_done()
        async_build_schedule_mock.assert_called()
        async_build_schedule_mock.assert_awaited()
        update_call_count = async_update_schedule_mock.call_count

        # Tick the clock and check if static data is updated
        freezer.tick(timedelta(hours=2))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        assert update_call_count < async_update_schedule_mock.call_count
