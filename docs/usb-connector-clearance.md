# USB4105 locating-hole clearance

The approved manufacturing amendment removes the former **0.1944 mm** J1
NPTH-to-pad exception. The minimum nominal clearance is now **0.2333 mm**,
above [JLCPCB's published 0.20 mm minimum](https://jlcpcb.com/capabilities/Capab)
(checked 2026-09-21). J1 remains **USB4105-GF-A-120, C5184243**.

The project-local footprint is
`Nucula_Project:USB_C_GCT_USB4105_16P_JLCPCB`. It derives from KiCad 10.0.6's
GCT USB4105 footprint and changes only the two physical outer ground lands.
Each is represented by two overlapping pad numbers: A1/B12 and A12/B1.

| Dimension, footprint-local coordinates | Before | After |
|---|---:|---:|
| Land width × length | 0.60 × 1.15 mm | 0.60 × 1.11 mm |
| Land center X | ±3.20 mm | ±3.20 mm |
| Land center Y | −3.68 mm | −3.70 mm |
| Hole-facing end Y | −3.105 mm | −3.145 mm |
| Opposite end Y | −4.255 mm | −4.255 mm |
| Corner radius | 0.15 mm | 0.15 mm |
| Minimum hole clearance | 0.1944 mm | 0.2333 mm |

Copper, solder mask and paste all follow the 0.04 mm trim. The copper-area
reduction is **3.578%** per physical land. The Ø0.65 mm locating holes, their
positions, shell stakes, other lands, connector placement, 3D model and all
routing remain unchanged. The global 0.25 mm hole-clearance setting is retained;
J1's scoped rule is raised from 0.19 to **0.20 mm**.

The nearest rounded corner gives the independent clearance calculation:
`sqrt(0.16² + 0.69²) − 0.15 − 0.325 = 0.233308 mm`.
The [archived GCT drawing](../parts%20documentation/USB4105-drawing.pdf), revision
B4, specifies the original 1.15 mm lands and Ø0.65 mm holes. This is a small
project adaptation of that land pattern, not a manufacturer-approved revision.
Physical solder-joint and connector fit inspection remain prototype checks.

[Source audit](usb-clearance-check.json) verifies the exact change against
locked commit `d4eaaa9`, including unchanged holes, every other footprint,
routing, net assignments and settings. Native DRC with zone refill and
schematic parity has **0 errors, 0 unconnected items and 0 parity issues**;
only the same two ESP32 silkscreen-edge warnings remain. The local library
matches the placed footprint without a library-mismatch warning.

The [manufacturing release](manufacturing-release.md) is regenerated from this
board. Its independent Gerber readback checks the actual copper, mask, paste
and drill coordinates and confirms the 0.2333 mm clearance in the exported files.
