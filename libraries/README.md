# Project libraries and attribution

KiCad project tables register `Nucula_Project` with relative `${KIPRJMOD}` paths.
The global `Nucula` library remains available separately, including PN7160.

- ESP32-C3-WROOM-02-N4 symbol, footprint and STEP: KiCad Library Team's
  ESP32-C3-WROOM-02 assets from installed KiCad 10.0.6, specialized with N4/4 MB
  metadata. Footprint pad geometry and antenna keepout are preserved.
- TLV803EA30DBZR: adapted from KiCad's TPS3839DBZ drawing. Corrected to the
  TLV803E open-drain output, SOT-23 footprint, ordering code and documentation.
- JST_PH_B2B-PH-SM4-TB_1x02-1MP_P2.00mm_Vertical: KiCad's unmodified SMT
  land pattern for J2 / JST B2B-PH-SM4-TB(LF)(SN), JLCPCB C160352. Two
  electrical pads and two unconnected solder hold-down tabs, all with paste.
  Checked against the [JST drawing](../parts%20documentation/JST-PH-SMT-datasheet.pdf),
  pages 2 and 4. Only the unresolved optional KiCad 3D-model reference was removed;
  no substitute model is claimed. JST offers CAD through its email request form.
- MouseBite_2Rows7_D0.60_P1.00_Inset_Gap2.00: project mechanical footprint
  for MB1/MB2, with two rows of seven 0.60 mm NPTH holes on 1.00 mm centers.
  The adjoining slots are defined by the PCB's Edge.Cuts geometry. This is a
  board-only drilling feature, excluded from BOM/POS output, with no 3D model.
  See the [keyboard breakaway guide](../docs/keyboard-breakaway.md).
- TP4054-42-SOT25R and SY8089AAAC: adapted from the embedded Olimex Rev C
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
  The user confirms the reference pin order/orientation: 24 initially counted
  contacts plus two outer ground contacts. The assigned Hirose FH12 26-way
  0.5 mm connector and its standard 3D model are retained. The socket accepts
  0.30 mm flex and uses bottom contacts; check fit/fold during PCB placement.
  DS1's BOM item is the socket; the glass is supplied separately. No glass
  assembly model is claimed.
- Crystal_NDK_NX2016SA_2.0x1.6mm: adapted from KiCad's four-pad 2016 crystal
  footprint and standard package model, with NDK EXD14B-00467 recommended
  0.85 × 0.75 mm lands at 1.35 × 1.05 mm center spacing. Y1 uses the exact
  NX2016SA-27.12MHZ-EXS00A-CS06346 reference in NXP AN14518.
- NFC_PCB_Loop_40x40_4T / NFC_PCB_Loop_40x40_4T_W0.50_S0.30_InsideFeed: main-board
  antenna with both terminals inside the four-turn winding, an open-center
  courtyard, perimeter keepouts on all copper layers and a 6 mm B.Cu host-entry
  corridor. Accommodates the PN7160 and matching circuit inside the loop;
  ground must be confined to an intentional local region. Prototype RF values
  require measurement with the populated four-layer layout.
- NFC_PCB_Loop_40x40_4T_W0.50_S0.30: retained bare-coupon two-terminal
  PCB antenna replacing the three-pad placeholder. Four front copper turns,
  0.50 mm track / 0.30 mm gap, two plated return holes and a bottom underpass.
  Includes an all-copper-layer keepout and intentional net-tie declaration.
  No ground/shield pad, no discrete-part 3D model, excluded from purchased BOM
  and placement outputs. [Design and calculations](../docs/nfc-antenna.md).
- C_0805_HandSolder_NoPaste: KiCad's C_0805_2012Metric_Pad1.18x1.45mm_HandSolder
  geometry and standard model, with F.Paste removed for four optional RF trim pads.
  C53/C54 now use the standard footprint with paste and populated 33 pF parts.
- L_Coilcraft_0805HP: newly drawn from the manufacturer's 0805HP land pattern:
  1.02 × 1.98 mm pads with 1.12 mm gap, for L2/L3 = 0805HP-151XGRC (150 nH).
  No package model is claimed. RF electrical model is included in the calculations.
- L_Coilcraft_0805HQ_2012Metric and L_Coilcraft_LPS4018: unmodified KiCad land
  patterns copied locally with their missing optional 3D references removed.
  The 0805HQ footprint is retained as an unassigned legacy asset; L2/L3 now use
  the distinct 0805HP footprint above. L4 is LPS4018-103MRC.
  Manufacturer models are offered through Coilcraft's
  [mechanical model service](https://www.coilcraft.com/en-us/models/mechanical/),
  including a registration-based STEP export; these models are not installed.

PCF8574T, its SOIC-16W_7.5x10.3mm_P1.27mm footprint and package model use the
standard KiCad libraries. All assigned model paths resolve in the checked
installation. The verification report lists A1, J2 and L1–L4 as having no model.

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

The added NXP AN13219 rev 1.6, Mohan inductance paper, Coilcraft RF model/land
drawing and Vishay resistor datasheet are archived under `parts documentation/`
for design traceability. [Source URLs and hashes](../docs/nfc/sources.json).

PN7160 datasheet rev. 4.2, NXP AN12988/AN14518 and both NDK CS06346 drawings
are also archived under `parts documentation/`. Samsung's numerical typical
DC-bias curves and JLCPCB's observed crystal sourcing stock are recorded in
`docs/components/`, with source URLs and retrieval dates. See the
[component refinements and calculations](../docs/component-refinements.md).
