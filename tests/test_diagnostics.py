from unittest.mock import AsyncMock, patch

from freezegun import freeze_time
from gtfs_station_stop.schedule import GtfsSchedule
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy import SnapshotAssertion
import syrupy.filters

from custom_components.gtfs_realtime.diagnostics import (
    async_get_config_entry_diagnostics,
)

exclude_props_filter = syrupy.filters.props("download_dir_path")


@freeze_time("2024-12-29 22:40:45.943287+00:00")
async def test_diagnostics(
    hass: HomeAssistant,
    entry_v2_full: MockConfigEntry,
    snapshot: SnapshotAssertion,
    mock_schedule: GtfsSchedule,
):
    """Test setting ups buttons in integration."""
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
        ),
        patch(
            "custom_components.gtfs_realtime.coordinator.GtfsSchedule.async_build_schedule",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        entry_v2_full.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry_v2_full.entry_id)
        await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, entry_v2_full)
    assert diagnostics == snapshot(exclude=exclude_props_filter)
