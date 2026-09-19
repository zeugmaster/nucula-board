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
- [BOM](docs/bom.csv) and [verification results](docs/verification.json)
- [Project library sources and licenses](libraries/README.md)

Battery target: approximately 400 mAh, protected single-cell Li-ion/LiPo,
3.7 V nominal / 4.2 V full; 2-pin JST-PH at 2.0 mm pitch, pin 1 positive,
pin 2 ground. Charging remains 100 mA (0.25C at 400 mAh).
Confirm the actual battery before assembly. This draft retains the
reference's simple USB power input; USB current/inrush/suspend management needs
further design before product-level use with arbitrary hosts.

Run `python3 tools/check_schematic.py` to repeat ERC, connectivity, pad/model and
voltage checks. KiCad's standard symbols, footprints and 3D models are required;
`KICAD_CLI` and `KICAD_SHARE` can override their locations. The project-specific
parts and ESP32/PN7160 STEP models are included with relative paths in `libraries/`.
All 124 components have assigned footprints; the antenna and OLED interface
mechanics are explicitly provisional. See the library notes for unavailable models.

The shared I²C bus runs at 100 kHz: PN7160 `0x28`, SSD1309 `0x3C`, PCF8574T `0x20`.
PCF8574T is an eight-bit I/O expander; no bus multiplexer is needed.
Its SOIC-16W_7.5x10.3mm_P1.27mm footprint matches the earlier BOM.
J3 is the user-fitted, DNP nine-pin keyboard header. J4/J5 are optional DNP
five-pin headers for reconnecting the keyboard section after separation.

RF matching values/coil geometry, crystal grade/load, exact OLED glass/flex,
and the battery/USB peak-power budget remain open before PCB release.

Git tracks design files, project libraries and documentation. Local editor state,
lock files, automatic backups and KiCad's `.history` are ignored.
