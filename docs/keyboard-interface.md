# 3×4 keypad connector and PCF8574 mapping

J3 remains a **DNP/user-fitted 1×9, 2.54 mm header**. Pins **1 and 9 are
electrically isolated**. Pins **2–8 connect to PCF8574T P0–P6**, and its unused
P7 (U8 pin 12) is marked NC. The keypad is a passive matrix: all seven active
contacts are scan signals, with no permanent ground or power contact.

## Compatibility with the early board

The early `legacy-design` schematic and PCB connect
J2 pins 1–7 to PCF8574 P0–P6 in that order. V2 preserves these same seven
port assignments: **old J2 pin n → new J3 pin n+1**. A keypad already working
with that seven-line ordering retains its matrix mapping, when installed
with the same orientation. The two new end positions add no electrical function.

This comparison concerns the keypad-to-expander wiring. The separate old
I²C `SDL` typo described in the NFC audit is not carried into V2.

## Researched common pinout

Adafruit's **3×4 Matrix Keypad, PID 3845**, documents the interleaved order
`C2, R1, C1, R4, C3, R3, R2`; its pinout photo shows unused positions at
both ends. The photo continues onto page 6 of the guide PDF, immediately
above the heading for the *different* PID 1824 keypad. PID 1824 and membrane
variants use other arrangements, so “3×4” alone does not specify a pinout.
The table below is the reference firmware mapping for the nine-position,
center-seven variant, not a claim that every plastic keypad is identical.

| V2 J3 pin | Old J2 pin | PCF port | U8 physical pin | PID 3845 matrix line |
|---:|---:|---|---:|---|
| 1 | — | — | — | NC |
| 2 | 1 | P0 | 4 | C2: 2 / 5 / 8 / 0 |
| 3 | 2 | P1 | 5 | R1: 1 / 2 / 3 |
| 4 | 3 | P2 | 6 | C1: 1 / 4 / 7 / * |
| 5 | 4 | P3 | 7 | R4: * / 0 / # |
| 6 | 5 | P4 | 9 | C3: 3 / 6 / 9 / # |
| 7 | 6 | P5 | 10 | R3: 7 / 8 / 9 |
| 8 | 7 | P6 | 11 | R2: 4 / 5 / 6 |
| 9 | — | — | — | NC |

Rows are counted top to bottom; columns left to right as viewed from the keys.
Map the first active contact in the source photo to **J3.2**, not J3.1. The
KiCad footprint's square pad identifies **J3.1, an unused end pad**. Check
the connector mating view during layout; viewing from the back reverses the
apparent left/right order. Keep both end pads free of tracks and copper fills.

Sources checked 2026-09-20:
[Adafruit 3845 product pin order](https://www.adafruit.com/product/3845),
[Adafruit pinout guide](https://learn.adafruit.com/matrix-keypad/pinouts),
[guide PDF, pages 5–6](https://cdn-learn.adafruit.com/downloads/pdf/matrix-keypad.pdf#page=5).
The [COM-08653 drawing hosted by SparkFun](https://cdn.sparkfun.com/datasheets/Components/General/SparkfunCOM-08653_Datasheet.pdf#page=3)
corroborates the same seven-contact mapping; it is a contributor-authored
drawing, so the Adafruit product documentation is the primary reference here.

## PCF8574 scanning

U8 is an **I²C GPIO expander**, with seven independently usable
quasi-bidirectional pins for the four rows and three columns. It remains at
7-bit address **0x20**, on the shared **100 kHz** bus. A written 1 releases
a port with its weak internal pull-up; a written 0 drives it low. Use a
PCF8574-aware scanner rather than MCU `digitalWrite()` calls.

For the reference matrix, the following are **PCF port bit indices**, not
ESP32 GPIO numbers or connector pins:

```text
rows, top to bottom:    [1, 6, 5, 3]
columns, left to right: [2, 0, 4]
keys:                  [[1,2,3], [4,5,6], [7,8,9], [*,0,#]]
```

Start with `0xFF`. Select one column low while all other bits remain 1,
then read the row bits; a low row identifies a closed key in that column.
The three scan bytes are **0xFB, 0xFE, 0xEF**. Keep unused P7's latch high.
Allow settling between write/read and debounce readings in firmware.

Optional interrupt idle state: `0xEA` holds all three columns low and
releases the four rows; a press can then assert `KEY_INT_N`. Read/scan the
port to service it, restore idle and handle held keys when rearming. PCF
reads/writes affect the interrupt state, so it is an event hint, not a
replacement for scanning. Ordinary periodic scanning is also usable.
The matrix has no per-key diodes; do not promise arbitrary multi-key rollover.

[NXP PCF8574 datasheet, sections 8.2–8.3](https://www.nxp.com/docs/en/data-sheet/PCF8574_PCF8574A.pdf)
describes the port and interrupt behavior. Actual switch timing and variant
mapping remain bring-up checks. A quick unpowered continuity check for the
reference mapping is: key **1** joins J3.3–J3.4, key **5** joins J3.2–J3.8,
and **#** joins J3.5–J3.6. This can detect reversal before firmware debugging.

## Verification

`python3 tools/check_schematic.py` verifies the seven exact port/header nets,
single-pin isolation of J3.1/J3.9/U8.12, the unchanged nine-pin footprint,
DNP status, native ERC and the remaining project connections. The BOM and
schematic PDF are regenerated with the new interface.

Result on 2026-09-20: native KiCad ERC **zero violations**; all seven new
header/port connections match the old netlist with the +1 connector offset.
The three unused pins are isolated, J3 remains DNP, and the exported keyboard
and system-interconnect sheets were visually inspected.
