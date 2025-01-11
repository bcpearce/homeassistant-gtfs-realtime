"""Test component setup."""

from datetime import timedelta
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gtfs_realtime.const import (
    CONF_GTFS_STATIC_DATA,
    CONF_STATIC_SOURCES_UPDATE_FREQUENCY,
    CONF_STATIC_SOURCES_UPDATE_FREQUENCY_DEFAULT,
)


async def test_lifecycle(hass: HomeAssistant, entry_v2_nodialout) -> None:
    """Test the component gets setup."""
    entry_v2_nodialout.add_to_hass(hass)
    await hass.config_entries.async_setup(entry_v2_nodialout.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_remove(entry_v2_nodialout.entry_id)
    await hass.async_block_till_done()
    hass.stop()


async def test_migrate_from_v1(
    hass: HomeAssistant,
    entry_v1_full: MockConfigEntry,
) -> None:
    """Test Migration From Version 1."""

    with (
        patch(
            "gtfs_station_stop.feed_subject.FeedSubject.async_update", return_value=None
        ),
        patch(
            "custom_components.gtfs_realtime.coordinator.GtfsRealtimeCoordinator.async_update_static_data",
            return_value=None,
        ),
    ):
        entry_v1_full.add_to_hass(hass)

        assert await hass.config_entries.async_setup(entry_v1_full.entry_id)

    await hass.async_block_till_done()

    # Adds default time for each static data url
    updated_entry = hass.config_entries.async_get_entry(entry_v1_full.entry_id)

    static_data_uris = [
        "https://example.com/gtfs1.zip",
        "https://example.com/gtfs2.zip",
    ]
    assert set(static_data_uris) == set(updated_entry.data.get(CONF_GTFS_STATIC_DATA))

    for uri in static_data_uris:
        # update everything to the default
        timedelta_dict = updated_entry.data.get(
            CONF_STATIC_SOURCES_UPDATE_FREQUENCY
        ).get(uri)
        assert (
            timedelta_dict.get("hours") == CONF_STATIC_SOURCES_UPDATE_FREQUENCY_DEFAULT
        )
        assert timedelta(**timedelta_dict) == timedelta(
            hours=CONF_STATIC_SOURCES_UPDATE_FREQUENCY_DEFAULT
        )
