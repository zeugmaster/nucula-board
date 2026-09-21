# OLED correction to the 24-contact interface

2026-09-21 · KiCad 10.0.6

**Current socket: FH12A-24S-0.5SH(55), C506794, top contacts.**
The [subsequent top-contact update](top-contact.md) supersedes the socket and
placement described in the historical 26-to-24-contact correction below.
The electrical map remains unchanged. Historical baseline: `600d88a`.

The user's [exact breakout schematic](../../parts%20documentation/i2c-display-breakout-schematic.png.png)
shows **J1 CON24**. This supersedes the previous 26-contact assumption.
The project symbol, schematic, PCB footprint, 3D socket model, BOM and purchasing
data now use **24 contacts**. The symbol describes the glass interface; the
purchased DS1 item is the socket, **Hirose FH12-24S-0.5SH(55), C202112**.

## Pinout checked against the supplied image

| Contacts | Breakout function | Project connection |
|---|---|---|
| 1, 2, 3 | GND, VLSS, VSS | GND |
| 4 | N.C. | Explicitly unconnected |
| 5 | VDD | +3V0 logic supply |
| 6 | BS1 | +3V0; I²C interface selection |
| 7, 8 | BS2, CS# | GND |
| 9 | RES# | OLED_RES_N, Q5/R35/C48 reset network |
| 10 | D/C# | GND; I²C address 0x3C |
| 11, 12 | R/W#, E/RD# | GND |
| 13 | D0 | I2C_SCL |
| 14, 15 | D1, D2 | Both connect to I2C_SDA |
| 16–20 | D3–D7 | GND |
| 21 | IREF | OLED_IREF, R32 = 910 kΩ to GND |
| 22 | VCOM | OLED_VCOMH, C47 to GND |
| 23 | VOP | OLED_12V5 panel supply |
| 24 | GND | GND |

Pins 1–24 retain their previous net assignments. Only the nonexistent ground
contacts 25 and 26 were removed. Pin 2's label is corrected to VLSS and pin 23's
label to VOP_PANEL. The project's existing 3.0 V logic supply, switched AP3012
boost, reset translation and component values remain unchanged; this update
does not claim to duplicate the breakout's XC6206/HM1308 circuitry.

[Machine-readable source map](pinout.json) records the reference image hash and
all 24 expected connections independently of the symbol and PCB.

## Placement and routing

DS1 remains locked at **(80, 108.65 mm), 180° on F.Cu**. The standard 24-position
footprint is 1 mm narrower than the former 26-position version. Keeping its
center fixed moves each retained contact 0.50 mm left on the board.

The local pad escapes were rerouted, with 43 old segments replaced by 40 new
segments and five existing vias shifted. The board now has **1,066 trace segments
and 321 vias**. Changes are confined to the OLED connector area. Copper zones
were refilled on all four layers without altering zone boundaries or rules.

All other 129 footprints are identical to the saved baseline. Component
positions, population flags, values, antenna copper and keepouts, symmetric NFC
matching branches, USB routing, keyboard breakaway and all board graphics are
preserved, including the user's back silkscreen and black mask settings.

## Regression results

- Native ERC: **0 violations**, five sheets, 128 physical components, 91 nets.
- Native PCB DRC with all-track checking: **0 errors, 0 unconnected items,
  0 schematic parity issues**. The same two U3 silkscreen-edge warnings remain,
  with the same affected item UUIDs as the freshly checked baseline.
- **23/23 existing layout checks pass**, including all-layer NFC pour exclusion,
  fixed placements, matched RF geometry, breakaway crossings and USB ground reference.
- **31/31 connector and regression checks pass**. All 91 nets are identical
  except for removing DS1.25/26 from GND. No unrelated validation constraints
  were relaxed. KiCad's omission of an empty `zone_defaults` element is ignored
  as serialization normalization; actual setup and stackup settings match.
- All physical symbols resolve to footprint pads; referenced 3D models resolve.
  Assembly audit passes with the new exact socket MPN and C-code.
- All **261 scoped ngspice cases** completed without solver errors. Numerical
  results match the previous run exactly, including its already documented
  600 pF I²C stress-limit failure. This is regression evidence for the modeled
  circuits, not full-board or panel simulation.
- The updated OLED schematic and connector rendering were visually reviewed.
  The PCB editor was reloaded after confirming it held no intervening edits.

[Regression report](regression-check.json) · [Baseline DRC](baseline-drc.json) ·
[Current DRC](../pcb/drc.json) · [Layout checks](../pcb/layout-check.json) ·
[Schematic PDF](../schematic.pdf) · [PCB layer PDF](../pcb/layers.pdf) ·
[Simulation scope and findings](../simulation/README.md)

Reproduce with `tools/check_schematic.py`, native KiCad PCB DRC,
`tools/check_pcb_layout.py` (KiCad's Python), `tools/check_assembly_readiness.py`,
`tools/simulate_preflight.py` and finally `tools/check_oled24_update.py`.
The last check compares against commit `600d88a` and requires fresh simulation
and netlist results for the current saved design.

## Panel identification and remaining mechanical check

On 2026-09-21 the user identified one of the intended displays as a **2.4-inch
chip-on-glass panel with `NFP1309-02Y` printed on its ribbon**, and confirmed:

- **0.50 mm contact pitch**.
- **0.30 mm insertion thickness**.
- **Exposed contacts on the same face as the light-emitting display surface**.
- **With the display mounted and ribbon folded into DS1, the tip contacts face
  away from the PCB** (subsequently confirmed by the user).

These are user-confirmed properties of that panel. An exact-marking web search
did not locate a manufacturer datasheet; the ribbon marking is not treated as a
verified manufacturer ordering code. Other display variants must be checked
separately. The supplied CON24 breakout remains the electrical pin-map source.

The selected socket is now **Hirose FH12A-24S-0.5SH(55), C506794**, with top
contacts matching the confirmed insertion orientation. Its manufacturer drawing,
lands, pin order, paste pattern and updated placement have been checked. The
[completed connector update](top-contact.md) includes the revised schematic/PCB,
BOM, sourcing observation and regression reports. The 0.20 mm move toward the
keyboard clears the larger latch while keeping all other footprints fixed.

Actual panel pin-1 correspondence, insertion length, fold strain, enclosure
clearance and display operation still require physical prototype checks.

The **OLED panel and external keyboard/keypad remain excluded from the assembly
BOM and CPL**. DS1 purchases only the PCB socket; onboard display support and
keyboard interface components remain populated as specified. J3/J4/J5 remain
DNP/user-fitted. Panel current, sequencing and optical operation still require
prototype validation; no glass assembly model or validated panel SPICE model
is claimed.
