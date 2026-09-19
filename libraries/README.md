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
- PN7160A1HN_C100E: project-local copy of the installed part, with a new readable
  symbol drawing using NXP's HVQFN40 pin map, including exposed ground pad 41.
  The KiCad-derived land pattern and installed SamacSys STEP model are included
  with relative paths. The model is a package representation, not an RF model;
  its terms are in [PN7160 model license](../LICENSES/PN7160-model-SamacSys.txt).
- SSD1309_COG_26: new symbol for the 26-contact glass interface in the supplied
  Waveshare schematic. These are flex/contact numbers, not bare SSD1309 die pads.
  The assigned Hirose FH12 26-way 0.5 mm connector and its standard 3D model are
  **provisional**, pending the actual panel's mechanical drawing/contact side.
  No glass assembly model is claimed.
- NFC_Loop_TBD / NFC_Antenna_Interface_TBD: explicit three-pad placeholder for
  coil ends and reference/shield ground. It contains no antenna geometry and
  has no 3D model. Replace it when the coil is designed.
- L_Coilcraft_0805HQ_2012Metric and L_Coilcraft_LPS4018: unmodified KiCad land
  patterns copied locally with their missing optional 3D references removed.
  L2/L3 values and final ordering codes await RF tuning. L4 is LPS4018-103MRC.
  Manufacturer models are offered through Coilcraft's
  [mechanical model service](https://www.coilcraft.com/en-us/models/mechanical/),
  including a registration-based STEP export; these models are not installed.

PCF8574T, its SOIC-16W_7.5x10.3mm_P1.27mm footprint and package model use the
standard KiCad libraries. All assigned model paths resolve in the checked
installation. The verification report lists A1 and L1–L4 as having no model.

The two user-supplied reference schematics remain under `parts documentation/`.
Their respective authors retain ownership; no broader redistribution license
is inferred. Downloaded SSD1309 and AP3012 datasheets retain their notices.

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
