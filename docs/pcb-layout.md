# PCB placement and routing

22 September 2026 · KiCad 10.0.6 · routing-review revision

All 130 footprints are on top, with 116 populated purchased components and all
91 nets connected. Nineteen parts have been rearranged for ordinary 0.30/0.70 mm
vias and the **17.70 × 5.00 mm display-ribbon access area**. DS1 remains at
(80.00, 108.85) mm, rotated 180°. Its insertion area is enforced by a front
component keepout and independently checked against every component courtyard.
[Changes, dimensions and checks](standard-fabrication.md). The subsequent
[routing repair](routing-review.md) preserves every footprint's placement.

[Top view](pcb/top.svg) · [Ribbon clearance](pcb/display-clearance.svg) ·
[NFC detail](pcb/nfc.svg) · [All copper layers](pcb/copper-layers.svg) ·
[Layer PDF](../manufacturing/routing-review-2026-09-22/drawings/layers.pdf) ·
[Native DRC](pcb/drc.json) · [Layout checks](pcb/layout-check.json)

![Current PCB, top copper and component outlines](pcb/top.png)

## Preserved geometry

The board outline, 40 mm coil copper and antenna rule areas remain unchanged.
All 42 NFC support/controller footprints remain inside the coil's open courtyard;
other circuitry remains outside. U6 and its decoupling move upward, while the
eleven matching-component pairs and their mirrored matching-tree copper are
preserved. The original antenna feed corridor and five 0.20 mm functional
keyboard breakaway crossings are retained. The fracture band has no vias or
pours. Fixed connector positions and component values/nets are unchanged.

The all-layer pour exclusion remains x = 58.25–103.25 mm, y = 48.5–93.5 mm.
No pour occurs inside or beneath the winding. NFC ground connections use traces
and vias. Antenna tuning and complete populated-board performance require
measurements; matching-tree symmetry alone does not establish RF performance.

## Manufacturing and routing

The revised board has **1,021 trace segments and 312 routing vias**. Every trace
follows the 45-degree convention. Pad/via entries and centreline joins pass the
independent geometry audit, with no edge-only connections, acute return bends,
duplicate traces or exposed segments shorter than 0.20 mm. The audit permits
short segments buried inside lands. [Before/after evidence](routing-review.md).
All routing vias are ordinary through-vias with 0.30 mm holes and 0.70 mm lands,
separated from solderable SMT lands by at least 0.10 mm mask-opening separation.
The optional ESP32 centre joint/thermal holes are omitted. The PN7160 centre
pad remains soldered without via holes in its wettable land.

Routing retains the 0.15 mm minimum track and 0.20 mm net clearance. General
NPTH clearance is 0.25 mm; J1 no longer needs a footprint-specific exception.
Its USB shell slots are widened to 0.70 mm with 0.30 mm minimum rings. See the
[standard-fabrication report](standard-fabrication.md) for adapted USB lands,
fit limitations and the complete fabrication settings.

The USB D−/D+ traces between U4 and R12/R13 are 41.3053 mm and 42.2968 mm long
(0.9915 mm skew). The reference-plane sampling has two uncovered points out of
2,171. The 0.5 mm skew advisory and complete reference-coverage advisory are
unmet. Both are reported as **advisory**, following
the request to focus on manufacturing compatibility. There is no controlled
impedance order or custom stackup; USB signal integrity has not been qualified.

## Validation

- Native KiCad DRC with zone refill, all-track checks and schematic parity:
  **0 errors, 0 unconnected items, 0 parity findings**.
- Schematic ERC and independent pin/net checks: **0 violations**.
- **21 layout checks and 16 standard-fabrication checks pass**, including
  keepout enforcement, via-to-pad separation, preserved geometry and no dangling copper.
- **Six routing-quality checks pass** across all four copper layers; five
  regression tests exercise the audit's handling of good and marginal joins.
- **40 cosmetic warnings** remain: 37 deliberate front-legend/library differences,
  two existing ESP32 legend/edge warnings and one preserved back-artwork overlap
  clipped against mask during Gerber export. A separate footprint hash audit
  confirms that legend editing changed no other geometry.
- Component choices and the five-board assembly audit pass. **261 partial circuit
  simulations** complete without solver errors; their limitations and findings
  are in the [simulation report](simulation/README.md).

References that cannot print legibly beside the open vias remain in the
[assembly drawing](../manufacturing/routing-review-2026-09-22/drawings/assembly-top.pdf).
The original rear artwork and locally added U6 3D-model reference are preserved.

## Reproduce

Run from the project directory. The PCB tools require KiCad's `pcbnew` Python;
the routing-quality checker requires Shapely 2. SPICE additionally requires
numpy/matplotlib and a shared ngspice library. Use a suitable Python environment
for each tool; the geometry JSON connects the KiCad and Shapely environments.

```sh
kicad-cli pcb drc --refill-zones --save-board --schematic-parity \
  --all-track-errors --severity-all --format json -o docs/pcb/drc.json nucula-v2.kicad_pcb
python3 tools/check_pcb_layout.py --drc docs/pcb/drc.json
python3 tools/check_standard_fabrication.py
python3 tools/export_routing_geometry.py
python3 tools/check_routing_quality.py
python3 tools/test_routing_quality.py
python3 tools/check_schematic.py
python3 tools/check_component_choices.py
python3 tools/check_assembly_readiness.py --boards 5
python3 tools/simulate_preflight.py
python3 tools/render_pcb_review.py
python3 tools/export_standard_fabrication.py
```

The [constraints](pcb/constraints.json) retain the original geometric baseline
with the explicitly documented placement/land-pattern amendments. The isolated
older OLED and USB regression scripts remain historical records; this broader
revision uses the current layout and fabrication audits.
