# Integration contract

Shared rules for the parallel work. Read this before touching code.

## Gateway endpoints (verified in the BombeCam source)

| method | path | meaning |
|---|---|---|
| GET | `/api/v1/integrations/homeassistant` | gateway addresses + every camera (uuid, name, model, streaming, rtsp_url, still_image_url, stream_name) |
| GET | `/api/v1/cameras/{uuid}/shadow` | `{"state":{"reported":{...}}}` with `IrLedMode`, `LedOnOff`, `LightSW`, `MotionDetectSW`, `SoundDetectSW`; `readback_error` when the camera did not answer |
| POST | `/api/v1/cameras/{uuid}/ptz` | `{"direction":"left\|right\|up\|down\|stop","duration_ms":int}` (max 2000) |
| POST | `/api/v1/cameras/{uuid}/control` | `{"action":"ir\|led\|light\|motion\|sound", ...}` |

Control details:

- `ir`: `mode` = `auto` or `off`. Shadow `IrLedMode`: `0` = off, `1`/`2` = auto.
- `led` (`LedOnOff`), `light` (`LightSW`), `motion` (`MotionDetectSW`), `sound` (`SoundDetectSW`): send `value: true|false`; shadow `1` = on, `0` = off.
- Auth is a Bearer token. `401`/`403` mean auth (and the config flow treats them as `invalid_auth`); `503` means the camera control channel is not available.

## Python pieces already in `main`

- `entry.runtime_data` is a `BombeCamCoordinator`.
- `coordinator.data.gateway`, `coordinator.data.cameras: dict[str, CameraInfo]`.
- `coordinator.shadow: dict[str, dict]` — shadow attributes per uuid, refreshed together with the cameras.
- `coordinator.runtime(uuid) -> CameraRuntime | None` (`.info`, `.reported`; `CameraRuntime.value("IrLedMode")`).
- `coordinator.client` — `async_ptz(uuid, direction, duration_ms)`, `async_control(uuid, action, **values)`, `async_get_shadow(uuid)`.
- `entity.BombeCamEntity(coordinator, uuid)` — one HA device per camera, `has_entity_name = True`, `available` false when the camera disappears.
- `const.CONF_PTZ_DURATION` (entry option, default 400, min 100, max 2000).

## Entity contract (tests depend on it; do not rename)

| platform | name | unique_id | icon |
|---|---|---|---|
| button | `Pan left` | `{uuid}_ptz_left` | `mdi:arrow-left-bold` |
| button | `Pan right` | `{uuid}_ptz_right` | `mdi:arrow-right-bold` |
| button | `Tilt up` | `{uuid}_ptz_up` | `mdi:arrow-up-bold` |
| button | `Tilt down` | `{uuid}_ptz_down` | `mdi:arrow-down-bold` |
| button | `Stop` | `{uuid}_ptz_stop` | `mdi:stop` |
| camera | (no name; device name) | `{uuid}_camera` | — |
| switch | `Status light` | `{uuid}_status_light` | `mdi:led-on` |
| switch | `Motion detection` | `{uuid}_motion_detection` | `mdi:motion-sensor` |
| switch | `Sound detection` | `{uuid}_sound_detection` | `mdi:ear-hearing` |
| switch | `Spotlight` | `{uuid}_spotlight` | `mdi:light-flood-down` |
| select | `Night vision` | `{uuid}_night_vision` | `mdi:weather-night` (options `auto`, `off`) |
| binary_sensor | `Stream online` | `{uuid}_stream` | connectivity |

With `has_entity_name`, the entity_id comes from the device name and the entity name: camera `Ingresso` → `button.ingresso_pan_left`, `switch.ingresso_status_light`, `select.ingresso_night_vision`, `binary_sensor.ingresso_stream_online`.

## Behaviour rules

- Buttons: pulse `CONF_PTZ_DURATION` from `entry.options` (default 400 ms); `stop` sends `0`. Raise `HomeAssistantError` with the gateway message when the call fails.
- Switches/select: optimistic state until the next coordinator refresh, reverted on failure; then `await coordinator.async_request_refresh()`. Unknown readback → state `None` (shown as unknown), not a guess.
- Camera: `stream_source()` returns `rtsp_url`; `async_camera_image()` fetches `still_image_url` through `async_get_clientsession(hass)`; re-fetch the still every poll is unnecessary, cache briefly is optional.
- Never call the gateway from the event loop without the client (it already enforces timeouts and error types).
- Code, comments and docstrings in English. `from __future__ import annotations` at the top. No new dependencies.
