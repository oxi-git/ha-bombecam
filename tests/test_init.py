"""Setup and unload tests for the BombeCam integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState

from custom_components.bombecam.coordinator import BombeCamCoordinator

EXPECTED_ENTITIES = [
    "button.ingresso_pan_left",
    "switch.ingresso_status_light",
    "select.ingresso_night_vision",
    "binary_sensor.ingresso_stream_online",
    "camera.ingresso",
]


async def test_setup_stores_coordinator_and_creates_entities(
    hass, mock_client, bombecam_entry
):
    """A full setup exposes the coordinator and every documented entity."""
    assert await hass.config_entries.async_setup(bombecam_entry.entry_id)
    await hass.async_block_till_done()

    assert bombecam_entry.state is ConfigEntryState.LOADED
    assert isinstance(bombecam_entry.runtime_data, BombeCamCoordinator)
    assert bombecam_entry.runtime_data.data is not None
    assert "cam1" in bombecam_entry.runtime_data.data.cameras

    for entity_id in EXPECTED_ENTITIES:
        assert hass.states.get(entity_id) is not None, f"missing entity {entity_id}"

    mock_client["async_get_gateway"].assert_awaited()
    mock_client["async_get_shadow"].assert_awaited_with("cam1")


async def test_unload_entry(hass, mock_client, bombecam_entry):
    """Unloading removes the entry without errors."""
    assert await hass.config_entries.async_setup(bombecam_entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(bombecam_entry.entry_id)
    await hass.async_block_till_done()

    assert bombecam_entry.state is ConfigEntryState.NOT_LOADED
