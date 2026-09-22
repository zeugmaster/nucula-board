# Nucula v2 — JLCPCB manufacturing package

Revision **r2**, prepared 2026-09-21 for **10 assembled prototypes**, with the confirmed
FH12A-24S-0.5SH(55) top-contact OLED socket. The approved 0.04 mm J1 ground-land trim is included. The circuit, placement, routing,
antenna and board outline are locked. The display connector questions are closed.

**Files are prepared for quotation and CAM review. Do not authorize production
until the supplier manufacturing reviews below are complete.**
The user is reviewing the JLCPCB upload. No parts have been reserved by these tools.

**r2 replaces the original CPL.** The original exporter added unverified
body-center offsets to U3, DS1 and J2. U3 and DS1 were visibly displaced in
JLCPCB's 2D and 3D previews. This revision removes all three offsets; confirm
lead-to-pad alignment in the updated JLCPCB 2D preview before production.
The PCB, Gerber geometry, BOM, component selections and rotations are unchanged.

## Upload these files

| JLCPCB input | File inside this package |
|---|---|
| PCB fabrication | `nucula-v2-gerbers.zip` |
| Assembly BOM | `assembly/jlcpcb-bom.csv` |
| Placement / CPL | `assembly/jlcpcb-cpl.csv` |
| Supporting drawings | `drawings/assembly-top.pdf`, `drawings/fabrication-outline.pdf`, `drawings/fabrication-notes.pdf` |
| Layer and stencil review | `drawings/layers.pdf`, `gerbers/nucula-v2-F_Paste.gtp` |
| USB clearance detail | `drawings/usb-copper.png`, `drawings/usb-mask.png`, `drawings/usb-paste.png` (blue lands, red NPTH) |
| Procurement quantities | `assembly/purchasing-10-boards.csv` — reference only, not the assembly BOM |

The BOM has **55 exact JLCPCB parts and 116 placements per board**. The CPL has
the same 116 designators, each exactly once. Upload the single-board BOM/CPL
and request 10 assemblies; do not multiply the reference designators by ten.
The fabrication ZIP contains four copper layers, both solder masks and
silkscreens, both paste layers, the outline, separate PTH/NPTH Excellon files,
and a Gerber job file. Bottom paste is intentionally empty. Drill maps are
outside the fabrication ZIP to avoid accidental layer recognition.

`nucula-v2-design-snapshot.zip` archives the input design, libraries and exporter.
`validation/export-board.kicad_pcb` records the derived plotting board, with the
manufacturing stackup/origin and DNP paste omissions. It is an export record;
continue editing the main project, then regenerate a new package.
`manifest.json` ties the outputs to exact input hashes; its source commit records
the baseline HEAD at export. The archived snapshot includes the approved USB fix.
The public r2 package was repacked for publication: local paths, editor locks
and the restricted PN7160 visualization model were removed, and hashes were
recalculated. Its fabrication, BOM and placement bytes are unchanged.

## Order configuration

| Setting | Selection |
|---|---|
| Quantity | 10 PCBs, 10 top-side assemblies |
| Service | Standard PCBA |
| Board | FR-4, four layers, 60 × 110 mm finished envelope |
| Thickness | 1.6 mm nominal |
| Color | Black solder mask, white silkscreen |
| Finish | ENIG |
| Copper | 1 oz outer; 0.5 oz inner |
| Stackup | **JLC04161H-3313**, not “No requirement” |
| Impedance | Request 90 Ω differential, ±10%, for the USB pair; CAM confirmation required |
| Via treatment | **Epoxy Filled & Capped**, all plated round holes of 0.20 / 0.30 / 0.40 mm; preserve supplied mask openings |
| Minimum via | 0.20 mm finished hole / 0.45 mm pad |
| Electrical test | Required |
| Edge rails / fiducials / tooling | **Added by JLCPCB**, supplier-generated carrier |
| Factory depanelization | Keep rails for delivery; **never detach the functional keyboard** |
| Order number | Remove order number; do not add markings over antenna, pads or instructions |

The selected stackup has 0.035 mm outer copper, 0.0152 mm inner copper,
0.0994 mm 3313 prepreg at each surface and 1.265 mm core. Nominal thickness
and finished copper weights follow the supplier's convention; these individual
layer dimensions do not add to exactly 1.600 mm. Prepreg Dk is 4.1. Core Dk 4.6
is an engineering nominal in the export metadata; obtain actual laminate data
if the fabricator changes materials. The locked source board's older nominal
stackup is superseded by this manufacturing specification in the export copy.

This retains the existing 0.15 mm USB trace width and 0.21 mm edge spacing
on B.Cu, referenced to In2.Cu. A simple uncoated IPC-2141 screening estimate
is about 93 Ω differential with the selected prepreg, within the 90 Ω ±10%
target. That approximation is **not** a field-solver or finished-board
qualification: mask, etching and local coupling matter. Have JLCPCB confirm
the actual construction/impedance before production; do not permit automatic
trace changes to the locked design. The exported geometry check verifies
ground reference and 0.2184 mm pair skew.

Standard assembly supports this black/ENIG/specified-stackup combination.
The 60 mm board width is below its 70 mm minimum, so the supplier must add a
carrier meeting its assembly dimensions. Use at least 5 mm process rails,
1 mm fiducials with 2 mm mask openings and supplier tooling holes on the carrier.
Do not add metal, rails or support tabs across the ESP32 antenna notch/overhang.
Avoid carrier attachment near the NFC winding and the keyboard fracture band.
The carrier must support both keyboard and main board during assembly; supplier
CAM must determine tab positions from the actual copper clearance. Approve the
carrier drawing before production. JLCPCB must transform this single-board CPL
to its own panel coordinates; do not upload a manually offset or replicated CPL.

## USB clearance resolved and final manufacturing review

J1 uses the project-local USB4105 footprint with the two outer ground lands
shortened by **0.04 mm at the hole-facing end**. Copper, mask and paste follow
this trim. Minimum nominal NPTH-to-pad clearance is **0.2333 mm**, above
JLCPCB's 0.20 mm requirement; the local KiCad rule is raised to 0.20 mm.
Holes, shell stakes, connector placement, signals and routing are unchanged.
The footprint is a project adaptation, not a new manufacturer land drawing.
`validation/usb-clearance-check.json` and `validation/gerber-readback.json`
verify the source and exported geometry. No hole-clearance waiver is required.

1. Confirm the specified 3313 stackup and USB impedance without geometry changes.
2. Confirm supplier carrier dimensions, tooling and attachment locations, preserving
   the ESP32 overhang, NFC exclusion and attached functional keyboard.
3. Match all 55 C-codes and inspect all 116 placements in JLCPCB's assembly preview.
   The exported rotations are KiCad counterclockwise angles normalized to 0–360°.
   **Catalogue-specific rotations have not been verified in a logged-in preview.**
   Use the pad coordinates and assembly drawing to check pin 1, diode/LED cathodes,
   MOSFET pin order, module antenna direction and all connector openings. Record
   any necessary corrections in `docs/manufacturing-spec.json`, then regenerate.
4. Check the final quote's quantities, loss allowance and availability before payment.

Two existing ESP32 silk-to-edge warnings are accepted for this export: they
concern the outline at the antenna overhang. CAM may clip off-board silkscreen
only. No copper, pads, outline or component position may change. All other
electrical/routing/parity errors must remain zero. DRC's ignored checks are
listed in `validation/drc.json`; it is not a blanket process certification.

## Assembly and stencil details

Do not assemble **C7, C8, C34, C35, C38, C39, J3, J4, J5, R38, R39**.
Their copper and drill geometry remains; their stencil apertures are omitted.
**A1** is the etched antenna, and **MB1/MB2** are mechanical mouse-bite patterns.
None is a purchased or placed component. OLED glass, external keypad and battery
are user-supplied and excluded. DS1 purchases the socket only.

The PN7160 U6 exposed pad uses nine rounded 1.1 mm stencil apertures, approximately
62% total coverage of its 4.1 mm square copper land. Preserve this windowing.
DS1's 24 signal apertures are 0.25 × 1.30 mm on 0.50 mm pitch, with separate
hold-down apertures. Use a nominal **0.10 mm stencil**, subject to assembler
paste-volume review for connectors and the exposed pad. Do not add paste to DNP
pads or turn the exposed-pad windows into one full-size aperture.

Fill and copper-cap **all 335 plated round holes of 0.20, 0.30 and 0.40 mm**.
This includes U3's twelve 0.20 mm thermal pad holes, the via centered in R28
pad 2, and vias overlapping other exposed lands. Tenting alone cannot prevent
solder wicking where a pad's mask opening intersects a hole. Preserve the
specified mask apertures over the caps. **Leave the four 0.60 mm USB connector
slots, nineteen 1.00 mm header holes and every NPTH hole open.** The diameter
selection is unambiguous in the separate PTH drill file. Select “Confirm
production files” to verify the fill interpretation. This process adds cost;
the final quote must include it. [JLCPCB via-covering instructions](https://jlcpcb.com/help/article/pcb-via-covering).

CPL coordinates use the board's lower-left envelope corner: KiCad (50,160 mm)
becomes (0,0), +X right, +Y up in the top view. Gerbers and drills use the same
origin. The board envelope is X = 0–60, Y = 0–110 mm.

CPL coordinates now preserve the **native KiCad footprint origins**, without
re-centering on the F.Fab body outline. KiCad's model is already positioned
relative to its footprint; JLCPCB renders its own catalogue model using the
uploaded placement reference. A body center is not automatically that reference.

The three changes from the original upload are:

| Reference | Original CPL X, Y (mm) | r2 CPL X, Y (mm) | Rotation |
|---|---|---|---|
| U3, ESP32 | 51.000, 53.860 | **47.900, 53.860** | 270° |
| DS1, display socket | 30.000, 53.050 | **30.000, 51.150** | 180° |
| J2, battery socket | 5.000, 59.100 | **6.750, 59.100** | 90° |

The U3 and DS1 offset directions match the user's observed error. J2's
unverified shift came from the same export rule and is also removed; its
catalogue alignment has not yet been reported. The other 113 placement rows
are unchanged. Recheck all three in JLCPCB's 2D pad view, including pin 1 and
connector entry/antenna direction. A correct KiCad 3D view does not validate
JLCPCB's independent model origins or zero-degree orientations.

`assembly/placement-audit.csv` records native origins and explicit offsets.
`validation/gerber-readback.json` verifies all 116 CPL coordinates against the
native KiCad export and the selected BOM. It does not certify alignment of
JLCPCB's catalogue models. `assembly/pad-coordinates.csv` supplies the board
pad positions/nets for the final assembly review. See JLCPCB's
[native KiCad CPL export instructions](https://jlcpcb.com/help/article/how-to-generate-the-bom-and-centroid-file-from-kicad).

## Keyboard and routing instructions

The keyboard is an intentional functional part of **one board**, not a second
customer design to separate in the factory. It occupies the lower 35 mm of the
60 × 110 mm envelope. Keep it attached throughout assembly and shipment.

In KiCad coordinates the 2 mm routing gap is Y = 123–125 mm. Two perforated
support tabs are centered at X = 62 and 98 mm, with 4.5 mm necks. Each carries
two rows of seven 0.60 mm NPTH holes on 1.00 mm pitch: **28 mouse-bite holes**.
The separate 3.5 mm central bridge at X = 80 mm carries five electrical traces.
The intended later user cut at Y = 124 mm is on Dwgs.User **only**. It must not
be routed, V-scored or drilled by the factory. Fabricate only the actual Edge.Cuts
features and supplied drills. Preserve the two closed internal slots, outer
notches and the separate PTH connector slots.

Paste this into the order's engineering remarks:

> One functional PCB with attached keyboard: DO NOT separate, V-score or route
> through the central electrical bridge or the two internal mouse-bite tabs.
> Keep keyboard and external assembly rails attached for delivery. Use
> JLC04161H-3313, black mask, ENIG, top assembly. Confirm 90-ohm USB differential
> impedance on B.Cu/In2.Cu without copper edits. Add carrier/rails/fiducials/tooling
> clear of ESP32 antenna overhang and NFC winding. J1 supplied lands have
> 0.233 mm NPTH clearance. No unapproved copper/pad/hole/component changes. Preserve U6 windowed paste and DNP omissions.
> Epoxy-fill and copper-cap all 0.20/0.30/0.40 mm plated round holes (335 total),
> including U3 thermal holes; preserve the supplied solder-mask openings. Leave
> 0.60 mm plated connector slots, 1.00 mm headers and all NPTH holes open.

## Stock and prototype acceptance

All 55 exact C-codes were refreshed on 2026-09-21 and have enough available
quantity for the saved ten-board purchasing plan, including the catalogue's
minimum placement/loss fields. Stock is not reserved. **L2/L3 C20417049: 21
available / 20 planned. C36/C37 C527192: 50 available / 28 planned.** Recheck
these first at checkout. No part substitutions were made.

For each delivered board, record its identifier and:

- Inspect assembly, connector contact side, polarity and solder joints; measure
  resistance from each power rail to ground before power-up.
- Use the agreed dedicated 5 V / at least 1.5 A USB supply with current monitoring;
  verify VSYS, 3.3 V, 3.0 V and enabled OLED boost, reset and startup current.
- Program and check USB enumeration, then I²C PN7160 0x28, OLED 0x3C and keypad
  expander 0x20 at 100 kHz; exercise display and all keys.
- Follow the existing NFC oscillator/antenna tuning procedure in the actual
  enclosure; calculations and DRC do not qualify RF performance.
- If used, verify battery polarity and 100 mA charging before unattended use.
  Test keyboard separation/reconnection on one unit only after attached operation
  works, with USB and battery disconnected.

## Reproduce

From the source repository:

```sh
python3 tools/check_schematic.py
python3 tools/refresh_jlc_stock.py
python3 tools/check_assembly_readiness.py --boards 10
python3 tools/check_usb_clearance.py
python3 tools/check_top_contact_update.py
# Use a Python interpreter that can import pcbnew and wx:
python3 tools/prepare_jlcpcb.py --output manufacturing/NEW-RELEASE
```

On this Mac the last command uses
`/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9`.
Exports use KiCad 10.0.6. A separate Gerbonara readback checks actual Gerber/drill
outputs and produces the fabrication notes and inspection views. Its command is
`python3 tools/inspect_jlcpcb.py manufacturing/NEW-RELEASE` with Gerbonara 1.5.0
and ReportLab installed, plus `rsvg-convert` for PNG previews. KiCad exports contain
timestamps, so reproduce geometry and audit counts; use manifest hashes to
identify the exact delivered archive rather than expecting byte-identical PDFs.

Sources checked on 2026-09-21: [JLCPCB fabrication capabilities](https://jlcpcb.com/capabilities/Capab),
[assembly capabilities](https://jlcpcb.com/capabilities/pcb-assembly-capabilities),
[stackup](https://jlcpcb.com/impedance),
[carrier requirements](https://jlcpcb.com/help/article/how-to-add-edge-rails-fiducials-for-pcb-assembly-order),
[Gerber export](https://jlcpcb.com/help/article/how-to-generate-gerber-and-drill-files-in-kicad-9),
[BOM format](https://jlcpcb.com/help/article/bill-of-materials-for-pcb-assembly),
[CPL format](https://jlcpcb.com/help/article/pick-place-file-for-pcb-assembly).
