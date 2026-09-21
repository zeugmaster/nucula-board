# JLCPCB prototype manufacturing plan

Prepared 2026-09-21 against saved design `96c8114`. This is a preparation plan,
not a manufacturing release or an order. The planning basis remains **10 assembled
boards**, with assembly on the top side and the keyboard attached.

## Starting point

- Main PCB: 60 × 110 mm envelope, four copper layers, nominal 1.6 mm thickness,
  black solder mask. Surface finish is not specified in the PCB setup.
- Saved checks report zero ERC violations, zero PCB DRC errors, zero unconnected
  items and zero schematic/PCB parity findings. Two ESP32 outline silkscreen-edge
  warnings remain. These reports were inspected for this plan, not rerun.
- The existing assembly BOM has 55 exact purchased parts and 116 placements per
  board. There are 11 DNP references, an etched antenna and two mechanical
  mouse-bite footprints. The main board has no release Gerber archive or CPL yet;
  existing Gerbers under `prototypes/nfc-antenna/` are for the separate coil coupon.
- The current board has no fiducial footprints. A1 is excluded from the BOM but
  does not explicitly carry `exclude_from_pos_files`; the release exporter must
  exclude it reliably.

Sources for the baseline: [layout](pcb-layout.md), [saved DRC](pcb/drc.json),
[assembly audit](assembly/readiness.json), [OLED update](oled24/README.md).
Some earlier narrative documents still describe preliminary, unrouted layouts;
update those statements as part of release documentation.

## 1. Resolve the choices that could change the PCB

- **OLED connector update completed:** DS1 is now **Hirose FH12A-24S-0.5SH(55),
  C506794**, top contact, matching the user-confirmed 24-pin NFP1309-02Y flex
  (0.50 mm pitch, 0.30 mm thickness, mounted contacts away from PCB). The
  schematic, footprint, PCB, BOM and checks are updated; DS1 moved 0.20 mm for
  latch clearance. [Update report](oled24/top-contact.md). Physical panel pin-1
  correspondence, insertion length, fold/enclosure fit and any other display
  variants still need confirmation.
- **Assembly service and finish:** evaluate the existing black-mask design with
  a proposed ENIG finish under Standard assembly. Compare an Economic quote only
  for a supported color/finish/stackup combination; do not silently change the
  user's black-mask choice. Final service eligibility must include every part.
- **Actual stackup:** select an available JLCPCB four-layer, 1.6 mm construction
  and record its layer order, copper thicknesses and dielectric data in KiCad.
  Recalculate the USB pair's 90-ohm differential target against that construction.
  The current 0.15 mm width / 0.21 mm gap assumes 0.10 mm dielectric to In2.Cu;
  nominal board thickness alone does not establish impedance. Change the USB
  geometry if needed, then repeat reference-plane and skew checks.
- **Assembly carrier:** agree tooling/rail/fiducial locations for the selected
  service. JLCPCB lists a 70 × 70 mm minimum for Standard assembly, plus rails and
  fiducials, so the 60 mm-wide finished board needs a suitable carrier/panel.
  Ensure it accommodates the ESP32 antenna overhang and does not alter NFC copper.
- **Functional breakaway:** prepare a dimensioned drawing identifying the two
  support tabs, 28 NPTH mouse-bite holes, routed slots and central electrical
  bridge. Require the keyboard to stay attached through assembly and delivery.
  The central bridge is cut by the user later; it is not a factory routing line.

JLCPCB's [assembly capabilities](https://jlcpcb.com/capabilities/pcb-assembly-capabilities)
distinguish Economic and Standard service, including carrier and stackup limits.
Use the selected order's actual stackup with its
[impedance parameters](https://cart.jlcpcb.com/client/template/placeOrder/impedance.html).

**Completion condition:** OLED fit is resolved, the manufacturing specification
is recorded, and the assembly/carrier approach is defined.

## 2. Refresh sourcing while those choices are resolved

- Refresh all 55 exact C-codes and regenerate the ten-board purchasing report.
  Include placement losses/minimums from the final quote, not just 10× the BOM.
- Prioritize L2/L3, **C20417049 / Coilcraft 0805HP-151XGRC**: the September 20
  snapshot had 21 available against 20 placements. C36/C37, **C527192**, had 50
  against a planning requirement of 28. Neither figure is live or reserved.
- DS1 is updated to top-contact **C506794**, with 5,189 available at the latest
  observation; refresh again close to ordering. Confirm SMT J2 **C160352**
  matches the final BOM.
  Treat any replacement as a component/footprint review; RF inductors must also
  preserve the required RF characteristics or trigger recalculation and tuning.
- Identify procurement lead times and any parts that need purchasing/reservation
  before order placement. Obtain the final cost before committing expenditure.

Use `tools/refresh_jlc_stock.py` followed by
`tools/check_assembly_readiness.py --boards 10`. The latter alone is an offline
check against the saved snapshot.

**Completion condition:** every populated reference has an exact available or
explicitly sourced part and a realistic quantity/lead time.

## 3. Complete fabrication and assembly checks

- Compare the design against the chosen JLCPCB process: 0.15 mm minimum tracks,
  0.20 mm copper clearance, 0.20 mm minimum via drill and 0.125 mm annular ring.
  Review board-edge, slot, hole and mask clearances, including process tolerances.
- Resolve J1's local NPTH-to-pad exception: the current manufacturer footprint
  has about 0.1944 mm clearance and a 0.19 mm KiCad rule. A passing local DRC does
  not establish acceptance by the selected fabrication process.
- Check PN7160 exposed-pad paste coverage and nearby vias, fine-pitch connector
  paste/mask openings, connector mechanical lands and all DNP paste apertures.
  Confirm via tenting and any via-in-pad treatment actually required by geometry.
- Remove or explicitly accept the two ESP32 silkscreen-edge warnings. Check
  polarity/pin-1 marks, battery polarity, interface labels, revision marking,
  breakaway instructions and any manufacturer order-number placement.
- Preserve the NFC all-layer pour exclusions, ESP32 antenna clearance, USB ground
  reference and breakaway keepouts through any manufacturing edits.
- Refill zones and rerun native ERC, DRC with schematic parity/all-track checking,
  the layout checks and assembly audit on the final saved files. Review ignored
  checks and custom exceptions. Rerun circuit-specific checks if affected by edits.

Use the current [fabrication capabilities](https://jlcpcb.com/capabilities/Capab)
and the project's existing verification tools.

**Completion condition:** zero unresolved electrical/routing/parity errors, with
every remaining manufacturing exception documented and resolved for the process.

## 4. Generate a reproducible release package

Create a release directory tied to a commit and file hashes. Generate all outputs
from the same frozen revision:

| Deliverable | Contents / acceptance check |
|---|---|
| Fabrication ZIP | F.Cu, In1.Cu, In2.Cu, B.Cu; both masks and silkscreens; Edge.Cuts; separate PTH and NPTH Excellon drills. Include the mouse bites and connector slots with correct plating. |
| Assembly BOM CSV | Exact MPN/C-code groups; currently 55 lines covering 116 populated references. Reconcile counts if any approved changes occur. |
| CPL CSV | Designator, Mid X, Mid Y, Layer, Rotation; millimetres; exactly the same populated reference set as the BOM, each appearing once. |
| Paste data | Top stencil/paste Gerber with intentional DNP omissions and reviewed exposed-pad apertures. |
| Assembly drawing | Reference positions, pin-1/polarity marks and explicit DNP list. |
| Fabrication drawing and notes | Stackup, finish, thickness, dimensions, slots, tooling/carrier and attached-keyboard requirement. |
| Release record | Source revision, tool versions, checks, dated sourcing report and hashes. |

Explicitly omit **C7, C8, C34, C35, C38, C39, J3, J4, J5, R38, R39**, **A1** and
**MB1/MB2** from the assembly BOM/CPL. Retain their intended fabrication geometry.
The OLED glass (including **NFP1309-02Y**), external keyboard/keypad and battery
are external items, excluded from the assembly BOM and CPL. The user explicitly
reconfirmed the display and keyboard exclusions on 2026-09-21. DS1 orders the
socket only; onboard display support and keyboard interface electronics remain
in the populated BOM. J3/J4/J5 remain DNP/user-fitted.

Use a documented, consistent coordinate origin and orientation across the Gerber,
drill and placement exports. Check component centroids as well as rotations;
footprint origins and assembler package origins can differ. If panelization
changes coordinates, keep the panel data and BOM/CPL workflow consistent.

JLCPCB documents its [BOM fields](https://jlcpcb.com/help/article/bill-of-materials-for-pcb-assembly),
[CPL fields](https://jlcpcb.com/help/article/pick-place-file-for-pcb-assembly) and
[Gerber/drill preparation](https://jlcpcb.com/help/article/how-to-generate-gerber-and-drill-files-in-kicad-9).

**Completion condition:** repeatable exports with no missing/extra placements and
an independently inspected Gerber/drill/paste view.

## 5. Review the quote and manufacturing interpretation

- Upload the package for quotation; check layer recognition, dimensions, all
  routed slots and PTH/NPTH holes in the manufacturing preview.
- Review every BOM match against the exact C-code and every assembly placement.
  Check IC pin 1, transistors, diode/LED polarity, crystal orientation, the ESP32
  module, USB, battery and OLED connectors. Record any required CPL corrections
  in the reproducible export process.
- Confirm the keyboard is treated as an attached functional section, and that
  tooling/rails do not damage the antenna or obstruct overhanging components.
- Review fabrication/assembly engineering questions and obtain the final quote,
  including parts, losses, Extended-part fees, assembly, inspection, shipping and
  applicable import charges. Commit the order only after reviewing that result.

**Completion condition:** accepted fabrication interpretation, verified assembly
preview, sourced parts and a reviewed final price.

## 6. Prepare prototype acceptance before delivery

Write a board-by-board bring-up sheet: visual inspection and resistance checks,
current-limited USB power-up, supply rails/reset, programming and USB enumeration,
I²C devices, keyboard and OLED operation, then NFC oscillator/antenna tuning.
Test the existing dedicated 5 V / at least 1.5 A supply assumption, startup/inrush
and load transients. If battery operation is exercised, follow the existing
battery/charger design checks. Test separation and reconnection on one unit only
after attached-board operation is established.

NFC tuning, oscillator startup and real display operation remain prototype
measurements; their existing calculations are not hardware qualification.

**Immediate next work:** resolve the manufacturing specification, refresh critical
stock, and complete the remaining fabrication/assembly audit findings. DS1
replacement and its electrical/layout regression checks are complete.
