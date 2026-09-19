# Nucula v2

KiCad 10 PCB design project. Open `nucula-v2.kicad_pro` in KiCad.

- `nucula-v2.kicad_sch`: schematic.
- `nucula-v2.kicad_pcb`: board layout.
- `nucula-v2.kicad_pro`: shared project settings.
- `parts documentation/`: component documentation.
- `.codex/config.toml`: project-specific Codex configuration.

The custom `Nucula` parts library is installed globally in
`~/Documents/KiCad_Libraries` and is currently outside this repository. It
provides the ESP32-C3-WROOM-02-N4 and PN7160A1HN/C100E symbols, footprints,
and STEP models. On another machine, install that library and register
`Nucula.kicad_sym` and `Nucula.pretty`; update its absolute 3D-model paths.
PCF8574T and its SOIC footprint are available in KiCad's standard libraries.

Git tracks the design files and documentation. Local editor state, lock files,
automatic backups, and KiCad's `.history` folder are ignored.
