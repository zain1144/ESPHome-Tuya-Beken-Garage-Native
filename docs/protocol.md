# CB3S Garage-Door Opener Protocol Reference

## Scope and evidence

This document describes the stock flash image with SHA-256:

`804EDE79CF6B94F8ED01C3007437F8FBAFF2A5751B3D1B02BE6F2437DB8DDD61`

The image identifies itself as TuyaOS 3.8.5, application `CB3S_Opener`, version `1.0.7`. It does not use the TuyaMCU `55 AA` serial framing. The CB3S communicates with the opener through Modbus RTU.

“Dump-confirmed” means the call path, register, and value were recovered from the executable. “Capture-confirmed” means a user action in the stock Tuya application was matched to a live Modbus frame. Meanings marked experimental remain unverified on hardware.

## Transport

- UART1 on CB3S: RX `P10`, TX `P11`
- Internal TX-driver enable: `P7`
- Serial format: `9600 8O1`
- Motor address: `1`
- Read holding register: function `0x03`
- Write single register: function `0x06`
- CRC-16/Modbus, low byte transmitted first

The external USB-A-shaped connector carries proprietary `+5V`, `GND`, `RXD`, and `TXD` wiring. It is not standard USB D+/D−.

## Periodic reads made by the stock firmware

The original firmware reads one register per request.

| Register | Full request frame | Meaning | Confidence |
|---|---|---|---|
| `0x1000` | `01 03 10 00 00 01 80 CA` | Motion: 0 idle, 1 opening, 2 closing | Dump-confirmed and hardware-tested |
| `0x1001` | `01 03 10 01 00 01 D1 0A` | Opening position, 0 closed and 100 open | Dump-confirmed and hardware-tested across 1–99 |
| `0x1100` | `01 03 11 00 00 01 81 36` | Motor-light state | Dump-confirmed and hardware-tested |
| `0x4006` | `01 03 40 06 00 01 71 CB` | Opening force, application range 0–9 | Capture-confirmed |
| `0x4007` | `01 03 40 07 00 01 20 0B` | Closing force, application range 0–9 | Capture-confirmed |
| `0x4008` | `01 03 40 08 00 01 10 08` | Secondary delayed-closing setting, range 0–9 | Capture-confirmed; unit unknown |
| `0x4009` | `01 03 40 09 00 01 41 C8` | Photoelectric sensor enable | Capture-confirmed |
| `0x400B` | `01 03 40 0B 00 01 E0 08` | Three-button remote-control mode | Capture-confirmed; behavior is variant-dependent |
| `0x4010` | `01 03 40 10 00 01 90 0F` | Vacation mode | Capture-confirmed |
| `0xA100` | `01 03 A1 00 00 01 A7 F6` | Automatic closing delay in seconds | Capture-confirmed |
| `0xA101` | `01 03 A1 01 00 01 F6 36` | Light-off delay, application range 0–99 | Capture-confirmed; unit unknown |

These are all periodic register reads found in this stock application. The motor may implement additional registers that the Tuya firmware never queries.

## Writes

| Register/value | Example frame | Meaning | Status |
|---|---|---|---|
| `0x2000 = 0` | `01 06 20 00 00 00 82 0A` | Stop door | Confirmed |
| `0x2000 = 1` | `01 06 20 00 00 01 43 CA` | Open door | Confirmed |
| `0x2000 = 2` | `01 06 20 00 00 02 03 CB` | Close door | Confirmed |
| `0x2000 = 5` | `01 06 20 00 00 05 42 09` | Special command originating from DP102 | Unknown; disabled by default |
| `0x2004 = 0/1` | CRC varies | Motor light off/on | Confirmed |
| `0x2005 = 1` | `01 06 20 05 00 01 53 CB` | Start RF-remote learning | Capture-confirmed |
| `0x2005 = 2` | `01 06 20 05 00 02 13 CA` | Delete stored RF remotes | Capture-confirmed; no individual remote ID |
| `0x4006 = 0..9` | CRC varies | Opening force | Capture-confirmed |
| `0x4007 = 0..9` | CRC varies | Closing force | Capture-confirmed |
| `0x4008 = 0..9` | CRC varies | Secondary delayed-closing setting | Capture-confirmed; unit unknown |
| `0x4009 = 0/1` | CRC varies | Photoelectric sensor enable | Capture-confirmed |
| `0x400B = 0/1` | CRC varies | Three-button remote-control mode | Capture-confirmed; semantics unresolved |
| `0x4010 = 0/1` | CRC varies | Vacation mode | Capture-confirmed |
| `0xA100 = 0..600` | CRC varies | Automatic closing delay in seconds, step 10 | Tuya schema and capture-confirmed; value 30 observed |
| `0xA101 = 0..99` | CRC varies | Light-off delay | Capture-confirmed; 0, 10, 20, and 60 observed; unit unknown |
| `0xA001 = 0..3` | CRC varies | Accessory/motor firmware-update phases | Dump-confirmed; not an everyday control |

An incoming `0xA002 = 1` event is interpreted by the stock application as a request to unbind Tuya/Wi-Fi. It is unrelated to RF-remote deletion and is not reproduced in ESPHome.

## Door-state model

- `0x1001 = 0`: fully closed
- `0x1001 = 100`: fully open
- `0x1000 = 1`: opening
- `0x1000 = 2`: closing
- `0x1000 = 0` with position 1–99: stopped part-way

The tested motor reports intermediate position values. The ESPHome cover publishes opening and closing immediately. When motion changes to idle it waits for the following `0x1001` read before publishing the final binary cover state; this prevents a false `Closing → Open → Closed` transition caused by reusing the previous position for a few milliseconds.

No confirmed register moves the door directly to a requested percentage, so `position_action` is intentionally absent.

## Tuya data-point map

| DP | Direction/type | Modbus mapping | Meaning |
|---|---|---|---|
| `1` | Boolean command/report | True opens; false closes; reports false when fully closed | Standard door switch/state |
| `2` | Numeric read/write | `0xA100` | Automatic closing delay in seconds |
| `101` | Enum command | 0 open, 1 stop, 2 close | Confirmed |
| `102` | Command | `0x2000 = 5` | Unknown |
| `103` | Enum report | 0 stopped, 1 open, 2 closed, 3 opening, 4 closing | Confirmed |
| `104` | Numeric read/write | `0x4008` | Secondary delayed-closing setting, 0–9; unit unknown |
| `105` | Numeric read/write | `0x4006` | Opening force |
| `106` | Numeric read/write | `0x4007` | Closing force |
| `107` | Boolean read/write | `0x4009` | Photoelectric sensor enable |
| `108` | Boolean read/write | `0x400B` | Three-button remote mode |
| `109` | Boolean read/write | `0x4010` | Vacation mode |
| `110` | Command | payload 0 → `0x2005=1`; nonzero → `0x2005=2` | Learn/delete RF remotes |
| `111` | Boolean read/write | read `0x1100`; write `0x2004` | Motor light |
| `112` | Numeric read/write | `0xA101` | Light-off delay, 0–99; unit unknown |
| `113` | String report | local string, not a motor register | Effectively unused |

## Known unknowns

- Meaning and safety implications of `0x2000 = 5`
- Unit and exact behavior of `0x4008`
- Time unit of `0xA101`
- Exact semantics and compatible RF-remotes for `0x400B`
- Names of the four update phases represented by `0xA001`

## Reverse-engineering method

1. Calculate the dump hash and inspect the BK7231N flash layout.
2. Extract/decrypt application partitions locally with `bk7231tools`.
3. Search ASCII, Tuya schema, product, UART, and command strings.
4. Follow ARM/Thumb literal references and call paths around the door-control strings.
5. Recover UART pins, serial format, direction-enable behavior, function codes, registers, and DP mappings.
6. Capture the stock module's UART as hexadecimal Modbus frames.
7. Change exactly one control in the Tuya application and correlate the new function-`06` write.
8. Reproduce confirmed reads and writes in ESPHome, keeping destructive and unknown commands disabled or guarded.

