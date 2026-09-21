# PCB placement and routing

2026-09-21 · KiCad 10.0.6 · four-layer prototype layout

The remaining **113 footprints are placed and all 91 nets are connected**.
All 130 footprints, including the two mouse-bite patterns, are on F.Cu.
The 17 previously placed footprints remain at their original positions and
rotations and are locked. The board outline, antenna copper, antenna rule areas,
and five breakaway bridge crossings are preserved.

[Top view](pcb/top.svg) · [NFC detail](pcb/nfc.svg) ·
[All copper layers](pcb/copper-layers.svg) ·
[Six-page copper/silkscreen/assembly PDF](pcb/layers.pdf) ·
[Native DRC](pcb/drc.json) · [Geometry checks](pcb/layout-check.json)

![Completed PCB, top copper and silkscreen](pcb/top.png)

## NFC placement and copper

All 42 NFC support/controller footprints fit inside the coil's open courtyard,
including the PN7160, crystal, decoupling, receiver taps and tuning components.
Other circuitry remains outside that aperture.

The eleven matching-component pairs mirror about **y = 80.5 mm**. The driver,
EMC and matching branches also have exactly mirrored trace coordinates, layers
and widths. L2/L3 sit 0.4 mm inward from their respective main buses to make room
for the fixed QFN's staggered via escapes. The fixed IC pins and antenna terminals
require different incoming TX and outgoing antenna-feed paths; those paths are
not claimed to be geometrically identical.

An all-layer pour exclusion covers **x = 58.25–103.25 mm,
y = 48.5–93.5 mm**, extending 2.5 mm beyond the nominal winding rectangle.
There are **no copper pours in the aperture or under/near the winding on any
layer**. NFC ground connections use traces and vias, including the common shunt
return, rather than a local poured plane. The seven host connections cross the
winding only through its existing B.Cu entry corridor. The original winding
restrictions remain in force.

The existing antenna-feed net names are now explicit global labels in
`nfc.kicad_sch`. This removes a KiCad CLI parity discrepancy with automatically
assigned antenna-net names. The exported net names, pin membership, circuit
values and topology are unchanged.

## Routing and manufacturing dimensions

The board contains **1,069 trace segments and 321 through-vias**. Ground pours
on all four layers are connected with stitching and component-return vias.
The full fracture band remains free of pours and vias; only the original five
0.20 mm F.Cu traces cross the cut bridge.

| Use | Routing dimensions |
|---|---|
| Main supply trunks | 0.75 mm; narrower branches according to their load and pin escapes |
| 3.3 V distribution | 0.50 mm main routes |
| Buck switch/output connections | 0.50 / 0.60 mm |
| OLED boost input and switch paths | 0.40 mm, entirely on F.Cu; no switch-node vias |
| NFC RF branches | 0.35–0.40 mm main traces, with local taps and pin necks |
| General signals | 0.20 mm nominal; 0.15 mm for dense escapes |
| General vias | 0.60 mm copper / 0.30 mm finished drill |
| Dense QFN escapes | 0.45 mm copper / 0.20 mm finished drill; 0.125 mm annulus |
| Copper clearance | 0.20 mm minimum; pours use 0.25 mm clearance |

The global track minimum is 0.15 mm and the through-hole minimum is 0.20 mm.
These dimensions must be included in the fabrication specification. The
footprint-specific rule in `nucula-v2.kicad_dru` permits 0.19 mm NPTH-to-pad
clearance only within J1: its existing manufacturer land pattern has about
0.1944 mm there. Other hole-clearance constraints remain unchanged.

The USB pair from U4 to R12/R13 uses **0.15 mm traces with 0.21 mm edge spacing
on B.Cu**, referenced to In2.Cu. The nominal stack is 35 µm copper with 0.10 mm
dielectric to that reference plane, targeting 90 Ω differential. Confirm the
impedance with the fabricator's actual stackup. The two routed lengths are
**41.2784 mm and 41.4968 mm**, giving **0.2184 mm skew**, with two equal through-via
transitions per conductor. A rule area protects the ground reference under the
long coupled run. The geometry check samples the center and both edges every
0.1 mm: all 2,324 samples have ground beneath them, excluding the intentional
0.6 mm radius around the signal-via antipads.

## Validation

- Native DRC, including all-track checking: **0 errors, 0 unconnected items**.
- Schematic/PCB parity: **0 findings**.
- Schematic ERC and existing independent pin/net checks: **0 violations**,
  128 physical schematic components, 91 nets.
- The layout checker passes all 23 checks, including fixed placements, component
  containment, net/value preservation, unchanged antenna/outline geometry,
  mirrored matching copper, USB reference coverage and actual filled-pour limits.
- Two pre-existing silkscreen-edge warnings remain on U3's outline at the fixed
  ESP32 antenna overhang. There are no other DRC warnings, routing stubs,
  clearance violations or courtyard overlaps.

Fifteen crowded component references are retained on the fabrication layer
instead of being printed over pads. The assembly page in the PDF shows their
locations. Copper-layer plots and the revised NFC schematic were visually checked.

Run from the project directory, with `kicad-cli` and a Python interpreter that
can import `pcbnew`:

```sh
kicad-cli pcb drc --refill-zones --save-board --schematic-parity \
  --all-track-errors --format json -o docs/pcb/drc.json nucula-v2.kicad_pcb
python3 tools/check_pcb_layout.py --drc docs/pcb/drc.json
python3 tools/check_schematic.py
```

On the macOS installation used here, the PCB checker runs with
`/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9`.
The original placement/net/geometry constraints are recorded in
[constraints.json](pcb/constraints.json), against commit `f8a132d`.

This completes placement and routing for the agreed prototype. DRC does not
measure NFC tuning, crystal startup, power transients or USB impedance. Follow
the existing [NFC tuning procedure](nfc-antenna.md#bench-procedure) with the
assembled board and final enclosure, and the documented power bring-up checks.
The [NXP PN7160 hardware guide](https://www.nxp.com/docs/en/application-note/AN12988.pdf)
remains the reference for hardware bring-up and layout guidance.
