# Side-entry battery connector — engineering prototype

This package contains the current October display mapping, USB backfeed redesign,
and J2 side-entry correction. It supersedes September files for the next prototype.
Revised hardware still requires the USB/display bring-up described in validation/.

Fabrication: five four-layer FR-4 boards, nominal 1.6 mm, green mask, white legend,
ENIG and the supplier standard stackup. Upload nucula-v2-gerbers.zip. No controlled
impedance, custom dielectric construction, or via filling/capping. Request normal
electrical test. Keep the keyboard attached. Use a 100 um top stencil; DNP and
optional ESP32 centre-joint paste are omitted.

Assembly: 119 populated components per board, all on top. Use assembly/bom.csv
or assembly/jlcpcb-bom.csv, assembly/placements.csv or assembly/jlcpcb-cpl.csv,
and drawings/assembly-top.pdf. CPL coordinates preserve KiCad anchors, with no
unverified offsets or rotation corrections. Confirm all pin alignment in the
supplier preview; assembly/pad-coordinates.csv provides independent pad locations.
The public stock snapshot is dated per part and is not reserved inventory.

J2 MUST be JST S2B-PH-SM4-TB(LF)(SN), JLCPCB C295747, side-entry SMT,
5.5 mm above the PCB when mated. DO NOT substitute upright B2B-PH-SM4-TB / C160352.
The opening faces the LEFT edge (negative X); the battery lead lies parallel to
the board. Keep the existing PHR-2 / 2.00 mm plug. Pin 1 = battery positive,
pin 2 = GND; both mounting tabs are unconnected. See assembly/battery-connector.md
and drawings/battery-connector.png. At the (50,160) export origin J2 is
X=5.200 mm, Y=59.100 mm, rotation=270 deg in the JLC CPL. Its positive pad is
(8.050,60.100) and ground pad (8.050,58.100) mm in that same coordinate system.

Native DRC: zero errors, zero unconnected items and zero schematic-parity findings.
The 45 remaining warnings comprise 42 reviewed footprint-library differences,
two existing ESP32 edge warnings and one back-artwork/mask clipping warning.
See the hash-bound validation reports for placement, routing, stencil, polarity,
plug-access and simulation checks. Electrical/RF/ESD and enclosure qualification
remain physical prototype work. September packages remain historical records.
