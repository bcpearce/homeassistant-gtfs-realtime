"""Test Config Flow."""

from unittest.mock import AsyncMock, patch

from aiohttp.web import HTTPNotFound
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.selector import SelectOptionDict
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gtfs_realtime.config_flow import GtfsRealtimeConfigFlow
from custom_components.gtfs_realtime.const import (
    CONF_ARRIVAL_LIMIT,
    CONF_GTFS_PROVIDER,
    CONF_GTFS_PROVIDER_ID,
    CONF_GTFS_STATIC_DATA,
    CONF_ROUTE_IDS,
    CONF_STATIC_SOURCES_UPDATE_FREQUENCY,
    CONF_STOP_IDS,
    CONF_URL_ENDPOINTS,
    CONF_USE_LOCAL_FEEDS,
    DOMAIN,
)


@pytest.fixture(name="flow")
def flow_fixture():
    """Fixture that constructs the flow."""
    with patch.object(GtfsRealtimeConfigFlow, "_get_feeds", return_value={}):
        flow = GtfsRealtimeConfigFlow()
        yield flow


@pytest.fixture(name="example_gtfs_feed_data")
def example_gtfs_feed_data_fixture():
    """Fixture for example provider data."""
    yield {
        CONF_GTFS_PROVIDER: "Example GTFS Provider",
        CONF_GTFS_PROVIDER_ID: "example_gtfs_provider",
        CONF_URL_ENDPOINTS: [
            "https://gtfs.example.com/rt1",
            "https://gtfs.example.com/rt2",
        ],
        CONF_GTFS_STATIC_DATA: ["https://gtfs.example.com/static1.zip"],
    }


@pytest.fixture(name="good_routes_response_patch")
def good_routes_response_patch_fixture():
    """Fixture for good feed response for pre-populating routes."""
    yield patch.object(
        GtfsRealtimeConfigFlow,
        "_get_route_options",
        return_value=[SelectOptionDict(value="X", label="Route X")],
    )


@pytest.fixture(name="good_stops_response_patch")
def good_stops_response_patch_fixture():
    """Fixture for good feed response for pre-populating stops."""
    yield patch.object(
        GtfsRealtimeConfigFlow,
        "_get_stop_options",
        return_value=[SelectOptionDict(value="A", label="Route A")],
    )


@pytest.fixture(name="bad_routes_response_patch")
def bad_routes_response_patch_fixture():
    """Fixture for bad feed response for pre-populating routes."""
    yield patch.object(
        GtfsRealtimeConfigFlow,
        "_get_route_options",
        side_effect=HTTPNotFound(),
    )


@pytest.fixture(name="bad_stops_response_patch")
def bad_stops_response_patch_fixture():
    """Fixture for bad feed response for pre-populating stops."""
    yield patch.object(
        GtfsRealtimeConfigFlow,
        "_get_stop_options",
        side_effect=HTTPNotFound(),
    )


@pytest.fixture(name="example_gtfs_informed_entities_data")
def example_gtfs_informed_entities_data_fixture():
    """Fixture for informed entities data."""
    yield {CONF_ROUTE_IDS: ["X", "Y", "Z"], CONF_STOP_IDS: ["A", "B", "C"]}


# pylint: disable=unused-argument
async def test_form(hass: HomeAssistant, flow) -> None:
    """Test we get the form."""
    result: ConfigFlowResult = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}


async def test_step_user(flow: GtfsRealtimeConfigFlow) -> None:
    """Test User Setup through Config Flow."""
    result: ConfigFlowResult = await flow.async_step_user(None)
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}
    # check feeds were acquired
    GtfsRealtimeConfigFlow._get_feeds.assert_called()  # pylint: disable=protected-access


async def test_step_user_get_local_feeds() -> None:
    """Test Getting Local Feeds. Verify the feeds.json file can be read."""
    local_feed_flow = GtfsRealtimeConfigFlow()
    result: ConfigFlowResult = await local_feed_flow.async_step_user(
        {CONF_USE_LOCAL_FEEDS: True}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}


async def test_step_user_input_manual_provider(flow: GtfsRealtimeConfigFlow) -> None:
    """Test User input selection 'Manual' GTFS provider."""
    result: ConfigFlowResult = await flow.async_step_user(
        user_input={CONF_GTFS_PROVIDER_ID: "_"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "choose_static_and_realtime_feeds"


async def test_user_step_get_feeds_fails() -> None:
    """Test that failures getting feeds do not break config flow."""
    with patch.object(GtfsRealtimeConfigFlow, "_get_feeds", side_effect=HTTPNotFound()):
        flow = GtfsRealtimeConfigFlow()
        result: ConfigFlowResult = await flow.async_step_user(None)
        assert "base" in result["errors"]
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"


async def test_step_choose_static_and_realtime_feeds_no_prefill(
    flow: GtfsRealtimeConfigFlow,
) -> None:
    """Test config flow for choosing static and realtime feeds."""
    result: ConfigFlowResult = await flow.async_step_choose_static_and_realtime_feeds()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "choose_static_and_realtime_feeds"


async def test_step_choose_static_and_realtime_feeds_prefilled(
    flow: GtfsRealtimeConfigFlow,
    example_gtfs_feed_data,
    good_stops_response_patch,
    good_routes_response_patch,
):
    """Test that choosing feeds pre-fills from the previous step."""
    with good_stops_response_patch, good_routes_response_patch:
        result: ConfigFlowResult = (
            await flow.async_step_choose_static_and_realtime_feeds(
                example_gtfs_feed_data
            )
        )
        # hub will be configured with the provider name and ID
        assert flow.hub_config[CONF_GTFS_PROVIDER_ID] == "example_gtfs_provider"
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "choose_informed_entities"


async def test_step_choose_informed_entities(
    flow: GtfsRealtimeConfigFlow,
    example_gtfs_feed_data,
    good_stops_response_patch,
    good_routes_response_patch,
) -> None:
    """Test config flow for choosing informed entities."""
    flow.hub_config |= example_gtfs_feed_data

    with good_stops_response_patch, good_routes_response_patch:
        result: ConfigFlowResult = await flow.async_step_choose_informed_entities()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "choose_informed_entities"


async def test_step_choose_informed_entities_shows_feed_selector_if_data_pull_fails(
    flow: GtfsRealtimeConfigFlow,
    example_gtfs_feed_data,
    bad_stops_response_patch,
    bad_routes_response_patch,
) -> None:
    """Test config flow for choosing informed entities."""
    flow.hub_config |= example_gtfs_feed_data

    with bad_stops_response_patch, bad_routes_response_patch:
        result: ConfigFlowResult = await flow.async_step_choose_informed_entities()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "choose_static_and_realtime_feeds"
    assert result["errors"]


async def test_step_choose_informed_entities_good_data(
    flow: GtfsRealtimeConfigFlow,
    example_gtfs_feed_data,
    example_gtfs_informed_entities_data,
) -> None:
    """Test config flow finish after choosing informed entities."""
    flow.hub_config |= example_gtfs_feed_data
    result: ConfigFlowResult = await flow.async_step_choose_informed_entities(
        user_input=example_gtfs_informed_entities_data
    )
    # creates an entry
    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_step_choose_informed_entities_no_entities(
    flow: GtfsRealtimeConfigFlow,
    example_gtfs_feed_data,
    good_stops_response_patch,
    good_routes_response_patch,
) -> None:
    """Test config flow finish after choosing informed entities."""
    flow.hub_config |= example_gtfs_feed_data
    with good_stops_response_patch, good_routes_response_patch:
        result: ConfigFlowResult = await flow.async_step_choose_informed_entities(
            user_input={CONF_ROUTE_IDS: [], CONF_STOP_IDS: []}
        )
    # creates an entry
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "choose_informed_entities"


async def test_step_reconfigure(
    hass: HomeAssistant,
    entry_v2_full: MockConfigEntry,
    flow,  # pylint: disable=unused-argument
    good_stops_response_patch,
    good_routes_response_patch,
    mock_schedule,
) -> None:
    """Test Reconfigure."""
    entry_v2_full.add_to_hass(hass)

    with (
        good_stops_response_patch,
        good_routes_response_patch,
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
            "custom_components.gtfs_realtime.coordinator.GtfsSchedule.async_update_schedule",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        result = await entry_v2_full.start_reconfigure_flow(hass)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reconfigure"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_STATIC_SOURCES_UPDATE_FREQUENCY: {
                    "https://example.com/gtfs1.zip": {"hours": 15},
                    "https://example.com/gtfs2.zip": {"days": 42},
                },
                CONF_ROUTE_IDS: [],
                CONF_STOP_IDS: [],
                CONF_GTFS_PROVIDER: "Test GTFS Provider",
                CONF_ARRIVAL_LIMIT: 4,
            },
        )

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "reconfigure_successful"
        entry = hass.config_entries.async_get_entry(entry_v2_full.entry_id)
        await hass.async_block_till_done()

        assert (
            entry.data[CONF_STATIC_SOURCES_UPDATE_FREQUENCY][
                "https://example.com/gtfs1.zip"
            ]["hours"]
            == 15
        )
        assert (
            entry.data[CONF_STATIC_SOURCES_UPDATE_FREQUENCY][
                "https://example.com/gtfs2.zip"
            ]["days"]
            == 42
        )

    hass.stop()
