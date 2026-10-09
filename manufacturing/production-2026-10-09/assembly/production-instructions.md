# Production package — 9 October 2026

Release `production-2026-10-09` is prepared for **five engineering prototypes**
from the current design, including the battery cable notch and latest artwork.
Use only files from this package together. This package supersedes the 8 October release because four BOM lines became unavailable.
Use its updated BOM and source together; do not substitute an older BOM.

## Files to send

| Purpose | File |
|---|---|
| PCB fabrication | `nucula-v2-gerbers.zip` |
| Assembly BOM | `assembly/jlcpcb-bom.csv` |
| Placement | `assembly/jlcpcb-cpl.csv` |
| Assembly drawing | `drawings/assembly-top.pdf` |
| Enlarged anchor and pad-number reference | `drawings/placement-reference.pdf` |
| Independent placement evidence | `assembly/placement-audit.csv`, `assembly/pad-coordinates.csv` |
| Fabrication outline and layers | `drawings/fabrication-outline.pdf`, `drawings/layers.pdf` |
| Editable source and libraries | `nucula-v2-design-snapshot.zip` |
| Integrity and validation | `manifest.json`, `validation/` |

The BOM and CPL describe **119 fitted components per board, all on top**.
Order five assemblies with the single-board files. A1, J6, H1–H6, mouse bites,
and DNP components are excluded. The display panel, battery, mounting hardware
and optional keyboard headers are not purchased by this BOM. Inventory is a
dated observation, not reserved stock; exact-part availability is settled by
the supplier's BOM matching. The four new selections are listed for SMT assembly on JLC detail pages. U3 assembly-service eligibility still needs supplier confirmation.

## Mandatory fabrication instructions

| Setting | Required value |
|---|---|
| Board | Four-layer FR-4, 60 × 110 mm envelope, nominal 1.6 mm |
| Stackup | **JLC04161H-3313, as submitted for rev A**; retain the Gerber job material stack |
| Copper | 1 oz outer, 0.5 oz inner |
| Finish / mask / legend | ENIG / **black** / white, matching rev A |
| Via treatment | **Epoxy filled and copper capped** for all 0.20 / 0.30 / 0.40 mm plated round holes; preserve supplied mask openings |
| Smallest via | 0.20 mm hole / 0.45 mm land; restored NFC via-in-pad requires filling/capping |
| USB mounting slots | Four plated routed slots, 0.70 mm wide |
| Mounting holes | Six 2.2 mm NPTH, M2 clearance; no plating or countersink |
| Stencil | 100 µm, top only, using supplied F.Paste |
| Test | Electrical test required |
| Delivery | Keyboard remains attached; supplier may add assembly rails/fiducials outside finished outline |

**Do not use the earlier ordinary/open-via or generic-stackup instructions.**
Do not substitute ink plugging for filled/capped via-in-pad. Do not resize,
retune or reroute the NFC antenna, matching tree, controller, crystal or local
vias. No copper thieving, test pads, order markings or supplier-added metal
inside or beside the antenna. Preserve all four-layer NFC copper exclusions.
The supplied board has no blanket controlled-impedance certification. Any
supplier USB impedance proposal must avoid changing the frozen NFC geometry.

JLCPCB's [via-covering instructions](https://jlcpcb.com/help/article/pcb-via-covering)
distinguish filled/capped processing from ink plugging. This package preserves
the recorded rev-A manufacturing specification; actual supplier CAM changes
on the previous physical boards are not available in the repository.

## Placement instructions — prevent the previous offset error

CPL X/Y use **native KiCad footprint anchors**, relative to (50,160) mm with
positive Y upward. Rotations are native KiCad angles normalized to 0–360°.
There are **no body-center offsets or unverified angle corrections**.
Every CPL row is independently compared with the source PCB; pad coordinates
are independently compared with exported copper. Do not apply the earlier
ESP32 +3.10 mm X, display +1.90 mm Y, or battery −1.75 mm X shifts.

Before the supplier releases its assembly job, check its **2D lead-to-pad
alignment** for all parts, especially U3, DS1, J2, U6, U4 and U10. Align actual
pin numbers, not a 3D body center. Supplier catalogue model anchors cannot be
certified from local files; use the supplied audit and pad table to resolve
any supplier-specific discrepancy.

- **U3:** ESP32-C3-MINI-1-H4X, **C41349510**. WROOM-02 is incompatible. Antenna points
  right and is flush with the cutout. Pad 49 is masked with no paste; perimeter
  ground pads are soldered. Use compatible ESP32-C3 revision-1.1 firmware.
- **DS1:** FH12A-24S-0.5SH(55), **C506794**, top-contact socket. The corrected mounted
  panel relationship is panel pin n = socket pad 25−n. Do not renumber or rotate
  the footprint to “correct” this intended reversal.
- **J2:** JST SM02B-SRSS-TB(LF)(SN), **C160402**, side entry, 1 mm pitch. Opening faces
  left, toward the cable notch. CPL X=7.700 mm, Y=59.100 mm, rotation=270°.
  Positive pad 1 is (9.700,59.600); ground pad 2 is (9.700,58.600) mm.
  SHR-02V-S-B mating lead; the old PH plug does not fit. Verify lead polarity.
- **J6:** hand-solder battery lands only. Left pad is GND; right pad is BAT+.
  No component or stencil paste. Use J2 or J6 for one battery connection.

## Validation and scope

Native ERC: zero violations. Native PCB DRC: zero errors, zero unconnected
items, zero schematic-parity findings. The 33 warnings are 32 reviewed library
footprint differences and one clipped R17 silkscreen reference. Export subtracts
solder mask from silkscreen. These warnings do not alter placement coordinates.

The NFC antenna, all pad positions/shapes, the 366 local tracks/vias, matching
values, stackup and via process remain those of submitted rev A. Independent
Gerber readback compares all four copper layers and both mask layers with rev A.
The seven feeders remain identical through the NFC area; remote routing differs.

The user explicitly authorized a different RF part after revalidation. Four
purchasing substitutions affect 19 placements:

| References | New part | JLC code | Change |
|---|---|---|---|
| C10/C11/C13/C14/C16/C18/C20/C25/C43/C45/C48/C51/C55 | Samsung CL10B104KB8NNNL | C913912 | Same 100 nF/50 V/X7R/10%/0603 component, different reel packaging |
| C28/C29 | Yageo CC0805JRNPO0BN102 | C326940 | Same 1 nF/100 V/C0G/5%/0805 ratings |
| C36/C37 | Fenghua 0805CG101F101NT | C464454 | Same 100 pF/100 V/C0G/0805; tolerance tightened from 2% to 1% |
| L2/L3 | Coilcraft 0805CS-151XGLC | C38190612 | 150 nH/2%; different RF loss, 0.40 A DC thermal reference |

L2/L3 use a dedicated body drawing on retained rev-A lands. Keep their existing
CPL anchors and rotations. The L termination is RoHS compliant silver/palladium/
platinum glass frit, **not halogen-free**. No automatic substitution of other
Coilcraft suffixes is permitted. The custom land pattern covers the terminal
contact regions but is not the CS datasheet's recommended land pattern; inspect
solder joints during first-article assembly.

Paired manufacturer-model screening compares the original and replacement
inductors without changing matching values. Nominal impedance moves from
18.84 − j0.14 Ω to 19.88 − j0.11 Ω; modeled coil current falls about 5.2%.
The separate qualification report records 237 paired cases (474 ngspice runs),
component stress, harmonic loss estimates, explicit acceptance limits and source
hashes. Those engineering limits are not NXP certification requirements.
**The replacement has not been tested on hardware.** Rev-A's demonstrated read
range and no-tuning behavior cannot be guaranteed for this new BOM. Verify NFC
operation, range, AGC and inductor temperature on the first assembled boards.

The strict routing report retains rev-A NFC findings (seven non-45° tracks,
12 shallow endpoints, five weak-connectivity groups, one duplicate and 22 short
segments) because changing them would violate the requested proven-layout
freeze. Each retained finding is reproduced on identical baseline copper;
**no new routing findings are accepted**. Both raw and regression reports are
included. Native clearance/connectivity DRC passes without excluding these items.

**261 preflight SPICE cases, 57 USB-backfeed cases and 474 paired RF substitution
cases completed without solver errors**, with current input hashes, circuit decks and logs included. The
independent full/half-circuit NFC numerical comparison and 12 native antenna
keepout fixtures also pass. These cover
passive NFC sensitivity, I²C, reset/ADC RC timing, ideal converter DC setpoints
and modeled USB isolation/backfeed. They are not a full assembled-board
simulation, switching-converter stability analysis, USB compliance test or
full-board RF field simulation.

Use I²C at 100 kHz within the 400 pF modeled budget; allow 200 ms initial battery
ADC settling. The modeled 600 pF bus deliberately exceeds the rise-time limit.
USB copper lengths are D− 63.5329 mm / D+ 53.1877 mm; two of 2,097 sampled
reference-plane points are uncovered. These remain documented advisories; revised
USB enumeration/reconnection, ESD, display operation and power transients need
physical bring-up. Use the established dedicated 5 V / at least 1.5 A supply.
Check NFC production repeatability with the same tags/setup as rev A. No matching
values were retuned in this release; physical validation may reveal adjustments.

The package is ready for supplier upload and CAM/assembly review. No order has
been placed and no supplier preview approval is claimed. Bench qualification
of the changed hardware remains distinct from production-file readiness.

## Reproduce this release

Use KiCad 10's pcbnew-enabled Python for the native board checks and exporter,
and a Python environment with `tools/nfc/requirements.txt` plus Gerbonara 1.5.0
for numerical and Gerber checks. Run the schematic check before simulations;
refill the board, then run native DRC with schematic parity before geometry checks.
Run `check_nfc_rev_a.py`, `check_pcb_layout.py --drc docs/pcb/drc.json`,
`check_mini_module.py`, `check_mounting_holes.py`, `check_battery_connector.py`,
`check_standard_fabrication.py`, `export_routing_geometry.py`, then
`check_release_routing.py`. Repeat the display/USB/component/assembly checks and
both simulation scripts and `tools/nfc/qualify_substitution.py`. `check_nfc_gerbers.py` additionally reads the historical
submitted rev-A Gerbers from the repository.

Set `VALIDATION_PYTHON` to the numerical environment's Python when running
`tools/export_standard_fabrication.py` with KiCad Python. The exporter refuses
stale evidence, runs independent Gerber/NFC/placement readback, hashes every
file and creates both ZIPs. Finish with
`python tools/verify_production_package.py manufacturing/production-2026-10-09`.
Existing packages are not overwritten; choose a new release identifier for
subsequent exports. Archived regression-only checks for superseded display/USB
revisions are not current-release acceptance tests.
