"""Test button."""

from unittest.mock import AsyncMock, patch

from homeassistant.components.button import (
    DOMAIN as BUTTON_DOMAIN,
    SERVICE_PRESS as BUTTON_SERVICE_PRESS,
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


async def test_setup_button(
    hass: HomeAssistant, entry_v2_full: MockConfigEntry, async_update_patcher, snapshot
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
        button_ids = [k for k, v in ent_reg.entities.items() if k.startswith("button")]
        assert button_ids == snapshot


# @pytest.mark.skip("Not working as expected")
async def test_button_press(
    hass: HomeAssistant, entry_v2_full: MockConfigEntry, async_update_patcher
):
    """Test refreshing static feed."""
    with (
        patch(
            "custom_components.gtfs_realtime.coordinator.GtfsRealtimeCoordinator._async_update_data",  # noqa E501
            new_callable=AsyncMock,
        ),
        async_update_patcher,
    ):
        entry_v2_full.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry_v2_full.entry_id)

    with async_update_patcher as update_static_data_mock:
        await hass.services.async_call(
            BUTTON_DOMAIN,
            BUTTON_SERVICE_PRESS,
            {
                ATTR_ENTITY_ID: "button.gtfs_schedule_refresh_schedule_feed_https_example_com_gtfs1_zip"
            },
            blocking=True,
        )
        update_static_data_mock.assert_called()
        await hass.services.async_call(
            BUTTON_DOMAIN,
            BUTTON_SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.gtfs_schedule_clear_gtfs_schedule"},
            blocking=True,
        )
        update_static_data_mock.assert_called_with(clear_old_data=True)
