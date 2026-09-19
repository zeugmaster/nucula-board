# Project libraries and attribution

KiCad project tables register `Nucula_Project` with relative `${KIPRJMOD}` paths.
The global `Nucula` library remains available separately, including PN7160.

- ESP32-C3-WROOM-02-N4 symbol, footprint and STEP: KiCad Library Team's
  ESP32-C3-WROOM-02 assets from installed KiCad 10.0.6, specialized with N4/4 MB
  metadata. Footprint pad geometry and antenna keepout are preserved.
- TLV803EA30DCKR: adapted from KiCad's TPS3839DBZ drawing. Corrected to the
  TLV803E open-drain output, SC70 footprint, ordering code and documentation.
- TP4054-42-SOT235 and SY8089AAAC: adapted from the embedded Olimex Rev C
  symbols. Corrected part names, pin electrical types, datasheets and footprint
  filters; replaced internal artwork with clean outlines and removed the old
  component-specific annotations.
- L_Taiyo-Yuden_NR-30xx: KiCad land pattern copied unchanged. Removed its
  missing 3D-model reference. No substitute model is claimed.

Olimex hardware source:
[ESP32-C3-DevKit-Lipo](https://github.com/OLIMEX/ESP32-C3-DevKit-Lipo),
Rev C, commit `5d93e79d46cf3b05782d9fe0f95a8a2e1ca6abbe`, © Olimex Ltd.
The adapted hardware schematic and Olimex-derived symbols retain
[CERN-OHL-S-2.0](../LICENSES/CERN-OHL-S-2.0.txt).

KiCad-derived library assets retain the
[KiCad CC-BY-SA-4.0 license with design exception](../LICENSES/KiCad-library-CC-BY-SA-4.0-exception.txt).
Original sources: [symbols](https://gitlab.com/kicad/libraries/kicad-symbols),
[footprints](https://gitlab.com/kicad/libraries/kicad-footprints),
[3D models](https://gitlab.com/kicad/libraries/kicad-packages3D).
Manufacturer datasheets retain their respective notices.
