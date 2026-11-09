"""Entity behaviour tests for the BombeCam platform modules."""

from __future__ import annotations

from custom_components.bombecam.const import CONF_PTZ_DURATION

CAMERA_ENTITY = "camera.ingresso"
RTSP_URL = "rtsp://192.168.1.12:8554/ingresso"


async def _setup(hass, entry) -> None:
    """Set up an entry and wait for the platforms to settle."""
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_pan_right_uses_default_duration(hass, mock_client, bombecam_entry):
    """A pan button sends the default 400 ms pulse."""
    await _setup(hass, bombecam_entry)

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.ingresso_pan_right"},
        blocking=True,
    )

    mock_client["async_ptz"].assert_awaited_once_with("cam1", "right", 400)


async def test_pan_left_uses_configured_duration(
    hass, mock_client, entry_factory
):
    """The ptz_duration option replaces the default pulse length."""
    entry = entry_factory(options={CONF_PTZ_DURATION: 800})
    await _setup(hass, entry)

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.ingresso_pan_left"},
        blocking=True,
    )

    mock_client["async_ptz"].assert_awaited_once_with("cam1", "left", 800)


async def test_stop_sends_zero_duration(hass, mock_client, bombecam_entry):
    """Stop is a PTZ command with a zero-length pulse."""
    await _setup(hass, bombecam_entry)

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.ingresso_stop"},
        blocking=True,
    )

    mock_client["async_ptz"].assert_awaited_once_with("cam1", "stop", 0)


async def test_status_light_turn_on(hass, mock_client, bombecam_entry):
    """Turning the status light on sends led=true."""
    await _setup(hass, bombecam_entry)

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.ingresso_status_light"},
        blocking=True,
    )

    mock_client["async_control"].assert_awaited_once_with(
        "cam1", "led", value=True
    )


async def test_night_vision_select_off(hass, mock_client, bombecam_entry):
    """Selecting off sends ir mode=off."""
    await _setup(hass, bombecam_entry)

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.ingresso_night_vision", "option": "off"},
        blocking=True,
    )

    mock_client["async_control"].assert_awaited_once_with(
        "cam1", "ir", mode="off"
    )


async def test_switch_state_follows_shadow(hass, mock_client, entry_factory):
    """LedOnOff=1 in the shadow reads back as an on switch."""
    mock_client["async_get_shadow"].return_value = {"LedOnOff": 1}
    entry = entry_factory()
    await _setup(hass, entry)

    state = hass.states.get("switch.ingresso_status_light")
    assert state is not None
    assert state.state == "on"


async def test_switch_keeps_optimistic_state_on_stale_shadow(
    hass, mock_client, bombecam_entry
):
    """A stale readback must not flip the switch back to its old value."""
    mock_client["async_get_shadow"].return_value = {"LedOnOff": 0}
    await _setup(hass, bombecam_entry)
    coordinator = bombecam_entry.runtime_data

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.ingresso_status_light"},
        blocking=True,
    )
    assert hass.states.get("switch.ingresso_status_light").state == "on"

    # The camera still answers with the old value for a moment.
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("switch.ingresso_status_light").state == "on"

    # Once the camera confirms, the optimistic state is dropped and the
    # readback takes over again.
    mock_client["async_get_shadow"].return_value = {"LedOnOff": 1}
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("switch.ingresso_status_light").state == "on"

    mock_client["async_get_shadow"].return_value = {"LedOnOff": 0}
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("switch.ingresso_status_light").state == "off"


async def test_switch_keeps_state_when_readback_fails(
    hass, mock_client, bombecam_entry
):
    """An empty shadow does not blank a switch whose value is already known."""
    mock_client["async_get_shadow"].return_value = {"LedOnOff": 1}
    await _setup(hass, bombecam_entry)
    coordinator = bombecam_entry.runtime_data
    assert hass.states.get("switch.ingresso_status_light").state == "on"

    # The gateway cannot read the camera back for a moment.
    mock_client["async_get_shadow"].return_value = {}
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("switch.ingresso_status_light").state == "on"

    # And a command sent while the readback is failing still holds.
    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": "switch.ingresso_status_light"},
        blocking=True,
    )
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("switch.ingresso_status_light").state == "off"


async def test_switch_follows_external_change(
    hass, mock_client, bombecam_entry
):
    """A value that changes after a command still comes from the camera."""
    mock_client["async_get_shadow"].return_value = {"LedOnOff": 0}
    await _setup(hass, bombecam_entry)
    coordinator = bombecam_entry.runtime_data

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.ingresso_status_light"},
        blocking=True,
    )
    # Stale readback: ignored.
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("switch.ingresso_status_light").state == "on"

    # The camera applies the command.
    mock_client["async_get_shadow"].return_value = {"LedOnOff": 1}
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("switch.ingresso_status_light").state == "on"

    # The vendor app turns it off.
    mock_client["async_get_shadow"].return_value = {"LedOnOff": 0}
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("switch.ingresso_status_light").state == "off"


async def test_night_vision_keeps_optimistic_option_on_stale_shadow(
    hass, mock_client, bombecam_entry
):
    """The night vision select ignores a stale readback until it is confirmed."""
    mock_client["async_get_shadow"].return_value = {"IrLedMode": 1}
    await _setup(hass, bombecam_entry)
    coordinator = bombecam_entry.runtime_data

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.ingresso_night_vision", "option": "off"},
        blocking=True,
    )
    assert hass.states.get("select.ingresso_night_vision").state == "off"

    # Still reporting "auto" from before the command.
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("select.ingresso_night_vision").state == "off"

    mock_client["async_get_shadow"].return_value = {"IrLedMode": 0}
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("select.ingresso_night_vision").state == "off"

    mock_client["async_get_shadow"].return_value = {"IrLedMode": 1}
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("select.ingresso_night_vision").state == "auto"


async def test_night_vision_keeps_state_when_readback_fails(
    hass, mock_client, bombecam_entry
):
    """An empty shadow does not blank the night vision select."""
    mock_client["async_get_shadow"].return_value = {"IrLedMode": 0}
    await _setup(hass, bombecam_entry)
    coordinator = bombecam_entry.runtime_data
    assert hass.states.get("select.ingresso_night_vision").state == "off"

    mock_client["async_get_shadow"].return_value = {}
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("select.ingresso_night_vision").state == "off"


async def test_camera_stream_source(hass, mock_client, bombecam_entry):
    """The camera stream source is the RTSP URL reported by the gateway."""
    await _setup(hass, bombecam_entry)

    camera_component = hass.data.get("camera")
    assert camera_component is not None
    camera_entity = camera_component.get_entity(CAMERA_ENTITY)
    assert camera_entity is not None

    assert await camera_entity.stream_source() == RTSP_URL
