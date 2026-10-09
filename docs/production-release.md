# Production package — 8 October 2026

Release `production-2026-10-08` is prepared for **five engineering prototypes**
from the current design, including the battery cable notch and latest artwork.
Use only files from this package together. Earlier October packages contain
changed NFC layouts and are superseded for this order.

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
the supplier's BOM matching. U3 assembly service eligibility needs supplier confirmation.

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

The NFC schematic is byte-identical to submitted rev A. All **43 local NFC
footprints and 366 tracks/vias** match its geometry, position, values and nets;
the submitted stackup and via process are restored. Independent Gerber readback
confirms the NFC area matches rev A on all four copper layers and both mask layers. User reports rev-A NFC
worked without tuning. No matching values were changed. The seven power/digital
feeders are identical through their entry into the NFC area; their remote
routing connects to the revised board. Mounting holes and circuitry elsewhere
differ, so this is not a claim of complete electromagnetic equivalence.

The strict routing report retains rev-A NFC findings (seven non-45° tracks,
12 shallow endpoints, five weak-connectivity groups, one duplicate and 22 short
segments) because changing them would violate the requested proven-layout
freeze. Each retained finding is reproduced on identical baseline copper;
**no new routing findings are accepted**. Both raw and regression reports are
included. Native clearance/connectivity DRC passes without excluding these items.

**261 preflight SPICE cases and 57 USB-backfeed cases completed without solver
errors**, with current input hashes, circuit decks and logs included. The
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
NFC production repeatability should be checked on assembled boards using the
same tag/setup as rev A; this is not an instruction to retune the matching tree.

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
both simulation scripts. `check_nfc_gerbers.py` additionally reads the historical
submitted rev-A Gerbers from the repository.

Set `VALIDATION_PYTHON` to the numerical environment's Python when running
`tools/export_standard_fabrication.py` with KiCad Python. The exporter refuses
stale evidence, runs independent Gerber/NFC/placement readback, hashes every
file and creates both ZIPs. Finish with
`python tools/verify_production_package.py manufacturing/production-2026-10-08`.
Existing packages are not overwritten; choose a new release identifier for
subsequent exports. Archived regression-only checks for superseded display/USB
revisions are not current-release acceptance tests.
