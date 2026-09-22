# Standard fabrication / five-board contingency

Upload `nucula-v2-gerbers.zip`. Order five bare four-layer FR-4 boards, nominal
1.6 mm, green mask, white legend, ENIG, standard copper and supplier stackup.
No controlled impedance, via filling/capping, or custom dielectric construction
is required. Request normal electrical testing. Keep the keyboard attached.
The Gerber job identifies the four layers and nominal board thickness; its
individual material-stack dimensions are deliberately omitted. Follow the
supplier's standard four-layer construction and the accompanying specification.

Order a 100 µm top stencil using the included F.Paste Gerber. DNP paste and the
optional ESP32 centre-pad paste are omitted. Fit the unchanged 116 components
per board using `assembly/bom.csv` and the updated assembly drawing.
The five-board purchasing list carries dated vendor observations and proposed
substitutes, not reserved stock or a delivery promise. The engineering BOM
retains its original MPNs; substitution notes in the purchasing list still apply.

`drawings/display-clearance.png` marks a 17.70 × 5.00 mm component-free ribbon
insertion area above DS1. Tracks, vias and soldermask-covered copper are permitted
there. This annotated review image is not a fabrication layer.

These files supersede the older filled-via contingency Gerbers. The archived
JLCPCB r2 package describes the board already submitted and remains unchanged.
Validation reports accompany this package; supplier CAM acceptance and physical
prototype testing remain separate from the recorded software checks.

Native DRC has zero errors, zero unconnected items and zero schematic-parity
findings. Its 40 cosmetic warnings are documented: 37 footprint-library
differences from front-legend clipping around open vias, two existing ESP32
outline/edge warnings, and one back-artwork/mask overlap clipped in Gerbers.
The independent geometry audit verifies that legend clipping changed no pads,
models, rules or other footprint geometry. The 261 simulation cases exercise
partial circuit models; they do not validate PCB parasitics or full operation.
