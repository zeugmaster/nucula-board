# Nucula v2

Open `nucula-v2.kicad_pro` in **KiCad 10**.

The first schematic draft contains the ESP32-C3-WROOM-02-N4, native USB-C data,
a 100 mA single-cell Li-ion charger with JST-PH connector, USB/battery supply
selection, a 3.31 V buck rail, and boot/reset/voltage supervision. It is adapted
from Olimex ESP32-C3-DevKit-Lipo **revision C**. The PCB is still blank.

- [Schematic PDF](docs/schematic.pdf)
- [Design choices, datasheets and outstanding hardware limits](docs/power-design.md)
- [BOM](docs/bom.csv) and [verification results](docs/verification.json)
- [Project library sources and licenses](libraries/README.md)

Battery assumption: protected 4.2 V single-cell Li-ion/LiPo; JST-PH pin 1 positive,
pin 2 ground. Confirm the actual battery before assembly. This draft retains the
reference's simple USB power input; USB current/inrush/suspend management needs
further design before product-level use with arbitrary hosts.

Run `python3 tools/check_schematic.py` to repeat ERC, connectivity, pad/model and
voltage checks. KiCad's standard symbols, footprints and 3D models are required;
`KICAD_CLI` and `KICAD_SHARE` can override their locations. The project-specific
parts and ESP32 STEP model are included with relative paths in `libraries/`.
L1's manufacturer model was unavailable; its footprint is included.

The previously installed global `Nucula` library in `~/Documents/KiCad_Libraries`
also provides PN7160A1HN/C100E. That part is not yet in this schematic.
PCF8574T with SOIC-16W_7.5x10.3mm_P1.27mm is available in KiCad's standard libraries.

Git tracks design files, project libraries and documentation. Local editor state,
lock files, automatic backups and KiCad's `.history` are ignored.
