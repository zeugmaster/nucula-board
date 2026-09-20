# Nucula v2

Open `nucula-v2.kicad_pro` in **KiCad 10**.

The five-sheet schematic contains the ESP32-C3-WROOM-02-N4, native USB-C data,
a 100 mA single-cell Li-ion charger with JST-PH connector, USB/battery supply
selection, a 3.31 V buck rail, and boot/reset/voltage supervision. It is adapted
from Olimex ESP32-C3-DevKit-Lipo **revision C**. It now includes the PN7160 NFC
controller and antenna matching tree, SSD1309 OLED glass driver/boost supply,
and a detachable PCF8574T keyboard section. The PCB is still blank.

- [Schematic PDF](docs/schematic.pdf)
- [Design choices, datasheets and outstanding hardware limits](docs/power-design.md)
- [NFC, OLED, I²C pin map and breakaway keyboard design](docs/peripherals-design.md)
- [35 mm keyboard breakaway geometry and separation instructions](docs/keyboard-breakaway.md)
- [40 mm NFC coil, calculated matching values and prototype tuning guide](docs/nfc-antenna.md)
- [Selected crystal, capacitor calculations and confirmed prototype interfaces](docs/component-refinements.md)
- [10-board assembly audit, exact JLCPCB BOM and stock risks](docs/assembly-readiness.md)
- [BOM](docs/bom.csv) and [verification results](docs/verification.json)
- [Project library sources and licenses](libraries/README.md)

Battery target: approximately 400 mAh, protected single-cell Li-ion/LiPo,
3.7 V nominal / 4.2 V full; 2-pin JST-PH at 2.0 mm pitch, pin 1 positive,
pin 2 ground. Charging remains 100 mA (0.25C at 400 mAh).
Battery operation is optional for this prototype; runtime/discharge capability
and improved low-battery behavior are deferred. J2 uses a vertical SMT JST-PH
2.00 mm connector, B2B-PH-SM4-TB(LF)(SN), JLCPCB C160352.
The user-confirmed USB source is a dedicated **5 V / at least 1.5 A** supply; the
steady-state planning budget is about 1.10 A including charging. Startup/inrush
must be tested; operation from arbitrary computer hosts is not qualified.

Run `python3 tools/check_schematic.py` to repeat ERC, connectivity, pad/model and
voltage checks. KiCad's standard symbols, footprints and 3D models are required;
`KICAD_CLI` and `KICAD_SHARE` can override their locations. The project-specific
parts and ESP32/PN7160 STEP models are included with relative paths in `libraries/`.
All 128 physical components have assigned footprints. A1 is a reusable four-turn
40 × 40 mm PCB coil with its bottom return and copper keepout included. The NFC
tree now has calculated starting values, 0805 manual tuning pads and TX isolation
links. [A separate bare-coil coupon](prototypes/nfc-antenna/nfc-antenna.kicad_pro)
is available for fabrication and measurement. The user has confirmed the OLED's
**26-contact Waveshare pin order and orientation**: the initially counted 24
contacts exclude two outer ground contacts. The 0.5 mm 26-way FPC socket is
retained; check the physical fit and fold during PCB placement. See the library
notes for unavailable models.

The shared I²C bus runs at 100 kHz: PN7160 `0x28`, SSD1309 `0x3C`, PCF8574T `0x20`.
PCF8574T is an eight-bit I/O expander; no bus multiplexer is needed.
Its SOIC-16W_7.5x10.3mm_P1.27mm footprint matches the earlier BOM.
J3 is the user-fitted, DNP nine-pin keyboard header: **pins 1 and 9 are NC;
pins 2–8 connect to P0–P6**, preserving the early board's seven-line order.
[Keypad pinout and scanning notes](docs/keyboard-interface.md).
J4/J5 are optional DNP
five-pin headers for reconnecting the keyboard section after separation.

Y1 is now NDK NX2016SA-27.12MHZ-EXS00A-CS06346 (JLCPCB C3008209),
2.0 × 1.6 mm, with calculated 12 pF / 15 pF load-capacitor starts. Power
capacitor ordering codes and larger bulk footprints are selected using archived
manufacturer DC-bias curves. Run `python3 tools/check_component_choices.py` to
reproduce those estimates. RF tuning, oscillator qualification and power
measurements remain prototype bring-up work. **The schematic is ready to begin
PCB layout** for the agreed USB-powered prototype; the main PCB is not routed
or released for fabrication.

Git tracks design files, project libraries and documentation. Local editor state,
lock files, automatic backups and KiCad's `.history` are ignored.
