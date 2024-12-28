"""Fixtures for testing."""

import json
from pathlib import Path

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.extensions.amber import AmberSnapshotExtension
from syrupy.location import PyTestLocation

from custom_components.gtfs_realtime.config_flow import DOMAIN

DIFFERENT_DIRECTORY = "snapshots"


class DifferentDirectoryExtension(AmberSnapshotExtension):
    @classmethod
    def dirname(cls, *, test_location: "PyTestLocation") -> str:
        return str(Path(test_location.filepath).parent.joinpath(DIFFERENT_DIRECTORY))


@pytest.fixture
def snapshot(snapshot):
    return snapshot.use_extension(DifferentDirectoryExtension)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integration that will be tested."""
    yield


@pytest.fixture(name="entry_v1")
def create_config_entry_v1():
    """Fixture for entry version 1."""
    yield MockConfigEntry(
        entry_id="mock_config_v1",
        domain=DOMAIN,
        version=1,
        minor_version=0,
        data={"url_endpoints": ["https://gtfs.example.com/feed"]},
    )


@pytest.fixture(name="entry_v1_full")
def create_config_entry_v1_full():
    """Fixture with full mock data for entry version 1."""
    with open("tests/fixtures/config_entry_v1_full.json") as f:
        conf = json.load(f)
    yield MockConfigEntry(**conf)


@pytest.fixture(name="entry_v2_full")
def create_config_entry_v2_full():
    """Fixture with full mock data for entry version 2."""
    with open("tests/fixtures/config_entry_v2_full.json") as f:
        conf = json.load(f)
    yield MockConfigEntry(**conf)


@pytest.fixture(name="entry_v2_nodialout")
def create_config_entry_v2_nodialout():
    """Fixture with mock data for entry version 2 with limited URLs to access."""
    with open("tests/fixtures/config_entry_v2_nodialout.json") as f:
        conf = json.load(f)
    yield MockConfigEntry(**conf)
