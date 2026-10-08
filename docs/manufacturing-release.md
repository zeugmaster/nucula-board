# Standard fabrication release — five bare boards

Current MCU revision (8 October 2026): **ESP32-C3-MINI-1-H4X / C41349510**.
The antenna is flush with the right PCB edge; the smaller milled notch includes
1 mm side clearance and 0.5 mm internal corner radii. GPIO functions and the
display/USB/battery corrections remain. [Compatibility and verification](esp32-mini.md).
Use the **mini-2026-10-08** package for this module; earlier packages use WROOM-02.

**Historical release — do not use for the October correction.** This package
predates the confirmed display reversal and retains the USB backfeed path.
The [editable design and bench follow-up](bringup/rev-b-display-and-usb.md)
supersede its wiring. The new [October prototype package](../manufacturing/mini-2026-10-08-package.zip)
includes those corrections, [side-entry J2 and direct wire pads J6](battery-connector.md); see its
[current assembly instructions](../manufacturing/mini-2026-10-08/README.md).
The rest of this page documents the September archive.

22 September 2026 · `routing-review-2026-09-22` · manual top-side reflow assembly

The archived [complete package](../manufacturing/routing-review-2026-09-22-package.zip) includes
its [Gerber ZIP](../manufacturing/routing-review-2026-09-22/nucula-v2-gerbers.zip).
This revision includes the connector-width ribbon access area and ordinary
unfilled through-vias, with the free-form routing regression repaired throughout
the board. [Routing review and validation](routing-review.md) ·
[Retained fabrication changes](standard-fabrication.md).

| Order field | Selection |
|---|---|
| Quantity | Five bare PCBs |
| Construction | Four-layer FR-4, nominal 1.6 mm, supplier standard stackup/tolerances |
| Size | 60 × 110 mm finished envelope |
| Copper | 1 oz outer; supplier standard inner copper |
| Mask / legend / finish | Green / white / ENIG |
| Via treatment | Ordinary open through-vias; no filling, capping or plugging |
| Minimum routing via | 0.30 mm finished hole / 0.70 mm land |
| Routing / net clearance | 0.15 mm / 0.20 mm |
| NPTH copper clearance | At least 0.25 mm |
| Plated USB slots | 0.70 mm wide, at least 0.30 mm annular ring |
| Impedance | No controlled impedance or custom dielectric requirement |
| Electrical test | Required |
| Keyboard | Delivered attached; preserve the functional bridge and mouse bites |
| Stencil | One 100 µm top stencil from included F.Paste; arrange holder size for the lab |

The ZIP contains four copper layers, both masks and legends, top paste, outline,
separate plated/nonplated Excellon drill files and a Gerber job file. The job
records layer order and nominal thickness, without individual custom material
stack dimensions. Plated slots
are Excellon routed ovals. Drill maps are kept outside the upload ZIP. Bottom
paste is absent because all components are on top. DNP and ESP32 centre paste
are omitted; the PN7160 exposed pad remains soldered.

The package provides 116 updated top placements, the engineering BOM, a
five-board purchasing list, IPC-D-356 netlist and assembly/layer/outline drawings.
The purchasing list retains the earlier LCSC/Mouser sourcing proposal and its
explicit substitution notes. Those observations are not a reservation or a
confirmed delivery date. The engineering BOM retains its original exact MPNs.
[Private-customer sourcing plan](../manufacturing/contingency-2026-09-22/README.md).
Use the new Gerbers, stencil and drawings with that plan.

[Assembly drawing](../manufacturing/routing-review-2026-09-22/drawings/assembly-top.pdf) ·
[Layer review PDF](../manufacturing/routing-review-2026-09-22/drawings/layers.pdf) ·
[Fabrication outline](../manufacturing/routing-review-2026-09-22/drawings/fabrication-outline.pdf)

Local checks pass with zero ERC/DRC errors and zero unconnected or parity
findings. Forty documented cosmetic DRC warnings remain; the legend is clipped
against mask in the Gerbers. The validation directory includes the exact reports,
board hashes, footprint-geometry audit, six passing routing-quality checks and
261-case partial simulation results. USB length skew and reference-plane
coverage remain advisory findings, documented in the routing review.
`manifest.json` records SHA-256 hashes for the package contents. Supplier CAM
acceptance, the retained keyboard breakaway, connector-fit testing and physical
bring-up are not established by these software checks.

Regenerate after repeating the checks described in [PCB layout](pcb-layout.md):

```sh
python3 tools/export_standard_fabrication.py
```

Use KiCad's `pcbnew`-enabled Python. The exporter rejects stale board, routing
audit, schematic or simulation results. `validation/export-board.kicad_pcb` is a derived plotting
copy with the (50, 160) mm drill/placement origin and DNP paste omissions; edit
the root project instead.

The [JLCPCB r2 archive](../manufacturing/jlcpcb-2026-09-21-r2-package.zip) remains
unchanged and records the board already sent to manufacturing. Its black-mask,
filled-via/custom-stackup instructions apply only to that archived order.
[Historical r2 instructions](jlcpcb-r2-release.md).
The first `standard-2026-09-22` package is also retained as a superseded archive;
use the routing-review package for new orders.
