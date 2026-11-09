# BombeCam for Home Assistant

Custom Home Assistant integration for a BombeCam gateway on the local network.
It polls the gateway's REST API and exposes every camera as one device with PTZ
buttons, switches, a night-vision select, a stream-online binary sensor and a
camera entity that serves the gateway's RTSP stream.

The API contract this integration implements is documented in
[CONTRACT.md](CONTRACT.md).

## Requirements

- A BombeCam gateway reachable from Home Assistant over the LAN.
- An API token minted by the gateway (see below).
- The gateway HTTP server bound to a LAN address. Start the gateway with
  `OSAIO_HTTP=0.0.0.0:8654`; otherwise it may only listen on loopback and Home
  Assistant cannot reach it.
- Home Assistant 2025.1.0 or newer.

## Installation

The repository must be public. On Home Assistant 2026.11 and newer, install it
from the built-in **Marketplace**; on older versions use HACS.

### Marketplace (Home Assistant 2026.11+)

1. Open **Settings > Marketplace**.
2. In the upper-right corner, select **Add from link**.
3. Enter `https://github.com/oxi-git/ha-bombecam` and select **Add**. If the
   type is not detected, choose **Integration** and add it again.
4. Open the repository page and select **Install**.
5. Restart Home Assistant if the dialog asks for it, then go to
   **Settings > Devices & services > Add integration > BombeCam**.

Adding a custom repository needs a GitHub connection: the Marketplace asks for
it and uses GitHub's device sign-in, which does not expose your password to
Home Assistant.

### HACS (Home Assistant 2026.10 and older)

1. In HACS, open **Integrations**, then the three-dot menu, then
   **Custom repositories**.
2. Add the repository URL with category **Integration**.
3. Install **BombeCam** and restart Home Assistant.
4. Go to **Settings > Devices & services > Add integration > BombeCam**.

## Configuration

The config flow asks for the gateway address and an API token. The address may
be entered with or without a scheme; it is normalized to `http://host:port` and
used as the config entry unique ID, so the same gateway cannot be added twice.

Generate a token on the machine running BombeCam:

```sh
curl -u admin:YOUR_PASSWORD -X POST http://192.168.1.12:8654/api/v1/operator/token
```

Copy the token from the response into the integration form. The token is stored
in the Home Assistant config entry and sent as a Bearer token on every request;
paste it as returned (`bc_tok_...`). A pasted `Bearer ` prefix and surrounding
spaces are removed automatically.

If the gateway later rejects the token, Home Assistant starts a re-auth flow and
asks for a new one; the address is kept.

## Entities

One Home Assistant device is created per camera, named after the camera. The
example below uses a camera named `Ingresso` with UUID `cam1`.

| Platform | Name | Example entity ID | Unique ID |
|---|---|---|---|
| button | Pan left | `button.ingresso_pan_left` | `cam1_ptz_left` |
| button | Pan right | `button.ingresso_pan_right` | `cam1_ptz_right` |
| button | Tilt up | `button.ingresso_tilt_up` | `cam1_ptz_up` |
| button | Tilt down | `button.ingresso_tilt_down` | `cam1_ptz_down` |
| button | Stop | `button.ingresso_stop` | `cam1_ptz_stop` |
| camera | (device name) | `camera.ingresso` | `cam1_camera` |
| switch | Status light | `switch.ingresso_status_light` | `cam1_status_light` |
| switch | Motion detection | `switch.ingresso_motion_detection` | `cam1_motion_detection` |
| switch | Sound detection | `switch.ingresso_sound_detection` | `cam1_sound_detection` |
| switch | Spotlight | `switch.ingresso_spotlight` | `cam1_spotlight` |
| select | Night vision | `select.ingresso_night_vision` | `cam1_night_vision` |
| binary_sensor | Stream online | `binary_sensor.ingresso_stream_online` | `cam1_stream` |

The night-vision select offers `auto` and `off`. Switch and select states come
from the camera shadow; a value the camera did not report is shown as unknown
rather than guessed.

The camera entity exposes the gateway's RTSP URL as its stream source. Still
images are fetched from the gateway's `still_image_url`.

## Dashboard widget

[`dashboard/webcam-card.yaml`](dashboard/webcam-card.yaml) is a ready-to-use
card with the live stream, the PTZ D-pad (left, right, up, down, stop) and the
camera controls in one card. Add it with **Dashboard > Edit > Add card >
Manual** and replace `ingresso` with your device's slug.

`camera_view: live` starts the stream as soon as the card is visible and Home
Assistant closes it when the view is left; a dashboard cannot stream while the
dashboard is closed. The PTZ buttons send one pulse of the configured length,
they do not keep moving while held.

## Options

Open the integration entry and choose **Configure**:

| Option | Default | Range | Meaning |
|---|---|---|---|
| Polling interval | 30 s | 10-600 s | How often the gateway and camera shadows are polled. |
| PTZ pulse length | 400 ms | 100-2000 ms | How long a pan/tilt button keeps the motors running. |

Changing the options reloads the config entry.

## Limitations

- The gateway API is plain HTTP. The token and all traffic are readable by
  anyone who can observe the LAN path; do not expose the gateway to the
  internet.
- PTZ pulses default to 400 ms. Very short pulses may be ignored and very long
  ones may be clamped by the camera firmware.
- PTZ support depends on the camera model and firmware. Cameras without motor
  control still provide their stream.
- Multiple gateways are supported only as multiple config entries, each polled
  independently. There is no shared multi-gateway view.
- Shadow readback is best effort. When a camera does not answer on its control
  channel, its stream and PTZ may still work while switch states stay unknown.
- No cloud features: the integration talks to the gateway only.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `401` or `403`, config flow reports `invalid_auth` | Token missing, expired or wrong. Mint a new token and use the re-auth flow. |
| `404` | The address points to another service, or the gateway firmware lacks the `/api/v1/integrations/homeassistant` endpoint. |
| `503` | The gateway cannot reach the camera control channel. Streams may still work; controls stay unavailable until the camera reconnects. |
| Timeouts and `cannot_connect` | Wrong address or port, gateway bound to loopback only (start it with `OSAIO_HTTP=0.0.0.0:8654`), or a firewall between Home Assistant and the gateway. |
| `already_configured` | An entry for that normalized address already exists. Edit or remove it instead of adding another. |

Enable debug logging for `custom_components.bombecam` to see the failing request.

## Development

Tests use `pytest-homeassistant-custom-component` and run in Docker so the Home
Assistant test harness does not have to be installed on the host.

```sh
docker build -t ha-bombecam-test -f Dockerfile.test .
docker run --rm -v "$PWD":/app -w /app ha-bombecam-test pytest -q
```

The test suite mocks every gateway call; no network access is needed. CI runs
hassfest, the HACS validation action and the same pytest command.
