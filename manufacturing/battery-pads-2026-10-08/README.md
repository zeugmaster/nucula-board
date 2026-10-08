# JST-SH and direct battery wire pads — engineering prototype

This package contains the current October display mapping, USB backfeed redesign,
the 2.95 mm JST-SH J2 connector, and J6 direct battery wire solder pads.
It supersedes the October 7 connector packages and September files for the next prototype.
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

J2 MUST be JST SM02B-SRSS-TB(LF)(SN), JLCPCB C160402, side-entry SMT,
1.00 mm pitch and 2.95 mm above the PCB when mated. Do not substitute PH, ZH,
or top-entry SH. Use an SHR-02V-S-B battery plug with SSH-003T-P0.2-H contacts
and 28 AWG leads. THE PREVIOUS JST-PH BATTERY LEAD DOES NOT FIT.
The opening faces the LEFT edge (negative X), with the lead parallel to the
PCB. Pin 1 = battery positive, pin 2 = GND; both hold-down tabs are unconnected.
Check the actual lead polarity. See assembly/battery-connector.md and
assembly/JST-SH-datasheet.pdf, plus drawings/battery-connector.png.
At the (50,160) export origin J2 is X=3.700 mm, Y=59.100 mm, rotation=270 deg
in the JLC CPL. Positive pad: (5.700,59.600); ground pad: (5.700,58.600) mm.

J6 provides two 2.2 x 2.5 mm exposed copper lands above J2 for hand-soldered
battery leads. Viewed from the top with USB at the bottom: left = GND (pin 2),
right = BAT+ (pin 1). Both are labeled on the front silkscreen. The pads are
parallel with J2; use ONE battery connection at a time. No component, stencil
paste or pick-and-place entry is required for J6. At the export origin, J6's
BAT+ pad is (6.100,64.000), and GND is (2.700,64.000) mm.

The connector is rated 1 A with 28 AWG wire. The user accepts intermittent
peaks above this rating for the prototype; no new current limiter or operating
restriction is added. This acceptance is not a manufacturer pulse-current
rating or measured thermal qualification. Charging remains 100 mA.

Native DRC: zero errors, zero unconnected items and zero schematic-parity findings.
The 44 remaining warnings comprise 41 reviewed footprint-library differences,
two existing ESP32 edge warnings and one back-artwork/mask clipping warning.
See the hash-bound validation reports for placement, routing, stencil, polarity,
plug-access and simulation checks. Electrical/RF/ESD and enclosure qualification
remain physical prototype work. September packages remain historical records.
