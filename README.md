# ESPHome Tuya/Beken Garage Native

[العربية](README_AR.md) | **English**

**Direct control through the opener's original Tuya CB3S module—no relay add-on.**

This is an ESPHome replacement for the Tuya firmware shipped on an Eazylift-style garage-door opener Wi-Fi module. The original CB3S (BK7231N) talks directly to the motor controller over its internal Modbus RTU bus. It does not simulate a wall button with an external relay, and it does not use the usual TuyaMCU `55 AA` protocol.

```text
Home Assistant ⇄ ESPHome on original CB3S ⇄ Modbus RTU ⇄ garage motor controller
```

The protocol and pin mapping were recovered from the stock firmware and verified against live UART captures. The included configuration provides local control through Home Assistant and an optional web page, without Tuya Cloud.

## Supported features

- Open, stop, and close commands
- Home Assistant garage-door cover
- Opening percentage reported by the motor (`0` closed, `100` open)
- Opening, closing, open, closed, and stopped states
- Motor-light control with real feedback
- Opening and closing force settings
- Automatic-closing delay
- Raw closing-delay and light-off-delay settings
- Photoelectric safety-sensor setting
- Vacation mode
- Remote learning and protected deletion of all RF remotes
- Wi-Fi, heap, loop-time, temperature, uptime, and reset diagnostics
- Web UI, captive recovery AP, and guarded OTA updates

The motor does **not** expose a confirmed command for moving directly to an arbitrary percentage. Position is therefore read-only; the cover deliberately has no position slider.

## Hardware and bus

| Item | Value |
|---|---|
| Module | Tuya CB3S / BK7231N |
| ESPHome board | `cb3s` |
| Motor protocol | Modbus RTU client/master |
| UART | `9600`, 8 data bits, odd parity, 1 stop bit (`8O1`) |
| Motor address | `0x01` |
| RX | `P10` |
| TX | `P11` |
| TX-driver enable | `P7` (`flow_control_pin`) |
| Status LED | `P26`, active low |
| Local module button | `P14`, active low |

The USB-A-shaped connector is **not a standard USB data interface**. It carries `+5V`, `GND`, `RXD`, and `TXD` using the opener's proprietary wiring. Do not assume it is safe or compatible with a normal computer USB port.

`P7` is not exposed at the connector. The stock firmware asserts it around UART transmission, indicating that it enables the adapter board's internal line driver.

## Installation

1. Back up the original flash before replacing the firmware.
2. Copy [`esphome/cb3s-garage-door.yaml`](esphome/cb3s-garage-door.yaml) into your ESPHome configuration directory.
3. Add your Wi-Fi values to ESPHome's `secrets.yaml`; see [`esphome/secrets.example.yaml`](esphome/secrets.example.yaml).
4. Validate and compile the YAML with ESPHome.
5. Flash the CB3S over its programming UART for the first installation.
6. Reconnect the module to the opener and test with the door area clear and a person beside the physical stop control.
7. Confirm that `Opening Position` reads `0%` when fully closed and `100%` when fully open before relying on automations.

The configuration was validated with ESPHome 2026.8.1. It uses the native Home Assistant API without API encryption, matching the intended local setup. Add encryption yourself if your network policy requires it.

## OTA and recovery behavior

The opener connection previously made warm OTA reboots unreliable. The configuration now:

- suspends Modbus while Wi-Fi starts;
- suspends Modbus and clears its transmit queue before shutdown or OTA;
- resumes motor polling five seconds after Wi-Fi connects;
- disables automatic Wi-Fi/API reboot timeouts;
- exposes a fallback access point and diagnostic entities.

Do not remove the `on_boot`, `on_shutdown`, Wi-Fi callbacks, or OTA guard unless you understand the adapter board's UART-driver behavior.

## Remote controls

`0x2005 = 1` starts RF-remote learning. `0x2005 = 2` deletes the stored remotes; the command carries no individual remote ID, so it is treated as **delete all remotes**. The ESPHome button is disabled by default and requires the separate 15-second arming switch.

The `Three-Button Remote Control` setting at `0x400B` is motor/remote-variant dependent. On the tested four-button remote it reset itself after about 17 seconds or after completing a movement, and each learned button still acted as a single open/stop/close step button. Do not assume true dedicated open/stop/close buttons without testing your exact motor and remote.

## Documentation and analysis tools

- [Protocol reference (English)](docs/protocol.md)
- [مرجع البروتوكول بالعربية](docs/protocol-ar.md)
- [`tools/analyze_bk_dump.py`](tools/analyze_bk_dump.py): flash layout, entropy, strings, and JSON fragments
- [`tools/reverse_uart.py`](tools/reverse_uart.py): product strings, pointers, and nearby ARM/Thumb code
- [`tools/disasm_thumb.py`](tools/disasm_thumb.py): annotated Thumb disassembly ranges
- [`tools/find_thumb_xrefs.py`](tools/find_thumb_xrefs.py): literal and branch cross-reference search

The original dump, decrypted partitions, extracted Tuya storage, device identifiers, credentials, and vendor firmware are intentionally **not included**. The protocol-documentation hash lets owners compare their own legally obtained backup without distributing it.

## Safety

Garage doors are heavy moving machinery. Keep the opener's physical limit, obstruction, and photoelectric safety systems active. Home Assistant, Wi-Fi, this firmware, and the `Stop` command are not substitutes for certified safety hardware. Test changes with the travel path clear.

## License

Project-authored code and documentation are released under the [MIT License](LICENSE). Vendor firmware and trademarks remain the property of their respective owners and are not distributed here.
