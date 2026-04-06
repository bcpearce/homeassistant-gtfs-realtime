"""Test number."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE as NUMBER_SERVICE_SET_VALUE,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.fixture
def async_update_patcher():
    return patch(
        "custom_components.gtfs_realtime.coordinator.GtfsRealtimeCoordinator.async_update_static_data",  # noqa E501
        new_callable=AsyncMock,
    )


async def test_setup_number(
    hass: HomeAssistant, entry_v2_full: MockConfigEntry, async_update_patcher
):
    """Test setting ups buttons in integration."""
    with (
        patch(
            "custom_components.gtfs_realtime.coordinator.GtfsRealtimeCoordinator._async_update_data",  # noqa E501
            new_callable=AsyncMock,
        ),
        async_update_patcher,
    ):
        entry_v2_full.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry_v2_full.entry_id)
        await hass.async_block_till_done()

        ent_reg = er.async_get(hass)
        number_ids = [k for k, v in ent_reg.entities.items() if k.startswith("number")]
        assert len(number_ids) == 2  # one for each url plus clear all


async def test_number_value_change(
    hass: HomeAssistant, entry_v2_full: MockConfigEntry, async_update_patcher
):
    """Test changing static feed update frequency."""
    with (
        patch(
            "custom_components.gtfs_realtime.coordinator.GtfsRealtimeCoordinator._async_update_data",  # noqa E501
            new_callable=AsyncMock,
        ),
        async_update_patcher,
    ):
        entry_v2_full.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry_v2_full.entry_id)

    await hass.services.async_call(
        NUMBER_DOMAIN,
        NUMBER_SERVICE_SET_VALUE,
        {
            ATTR_ENTITY_ID: "number.gtfs_schedule_refresh_schedule_feed_interval_https_example_com_gtfs1_zip",
            ATTR_VALUE: 5.0,
        },
        blocking=True,
    )

    await hass.services.async_call(
        NUMBER_DOMAIN,
        NUMBER_SERVICE_SET_VALUE,
        {
            ATTR_ENTITY_ID: "number.gtfs_schedule_refresh_schedule_feed_interval_https_example_com_gtfs2_zip",
            ATTR_VALUE: 8.5,
        },
        blocking=True,
    )

    assert entry_v2_full.runtime_data.static_timedelta[
        "https://example.com/gtfs1.zip"
    ] == timedelta(hours=5.0)
    assert entry_v2_full.runtime_data.static_timedelta[
        "https://example.com/gtfs2.zip"
    ] == timedelta(hours=8.5)
