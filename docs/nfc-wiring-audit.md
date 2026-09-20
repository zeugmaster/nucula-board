# NFC wiring audit against the early prototype

Audit date: 2026-09-20. Current design: commit `162260c`.
Reference: `legacy-design`.

**VEN and IRQ are not interchanged in the saved designs.** The early board
connects the breakout's labeled VEN to XIAO GPIO0 and IRQ to GPIO1. V2 keeps
the same signal directions on ESP32-C3 GPIO7 and GPIO6. The important new
finding is insufficient guaranteed low-level margin on V2's 100 kΩ address
pull-downs. This audit recommends correcting those straps before fabrication.
No schematic or PCB was changed by this audit.

## Evidence and scope

- Exported the early schematic netlist with the KiCad MCP tool and checked
  J3, U1, U2, R1 and R2 against the saved PCB pad nets. The production
  `production/netlist.ipc` independently agrees on VEN, IRQ and the SCL/SDL split.
- Inspected the early schematic PDF and the archived Elechouse PDF visually.
- Exported a fresh V2 netlist with KiCad CLI and compared its connectivity to
  `docs/netlist.xml`: identical. Reviewed all 40 U6 pins plus exposed pad 41.
- Cross-checked NXP PN7160/PN7161 datasheet rev. 4.2, AN12988 rev. 1.6 and
  UM11495 rev. 1.8. Inspected Elechouse's current module documentation too.
- [Machine-readable evidence and input hashes](nfc/wiring-audit.json).

This establishes the saved wiring. It cannot reveal a crossed jumper,
silkscreen mistake on an individual module, hand rework, or the old module's
firmware/nonvolatile configuration. The early folder has no Git history.
This was a pin/net review, not a new routing/DRC audit of the early PCB.

## Breakout-to-chip mapping

J3 below belongs to the **early** board. U6 and U3 belong to **V2**. GPIO
numbers are not module pad numbers.

| Breakout signal | Early connection | V2 connection | Assessment |
|---|---|---|---|
| VEN | J3.5 → U1.1, XIAO GPIO0 / D0 | U3.6, ESP32-C3 GPIO7 → U6.10; R22 = 100 kΩ to GND | Same direction; new GPIO and external default-low resistor |
| IRQ | J3.4 → U1.2, XIAO GPIO1 / D1 | U6.8 → U3.5, ESP32-C3 GPIO6 | Same direction; new GPIO; no external inverter or pull-up |
| SDA | J3.2 → U1.5, GPIO22 / D4 | U3.3, GPIO4 ↔ U6.5 | GPIO changed; shared bus retained |
| SCL | J3.3 → U1.6, GPIO23 / D5 | U3.4, GPIO5 ↔ U6.7 | GPIO changed; clock net corrected as described below |
| DWL | J3.1, accessible but no host GPIO connection | U6.2 → R21 = 10 kΩ → GND | Normal boot preserved; dedicated connector access lost |
| VDD | J3.6 → +3V3 | U6.6 VDD(PAD) → +3V3, nominal 3.31 V | Same host-logic supply role |
| GND | J3.7 → GND | U6.4, .9, .20 and exposed pad .41 → GND | Common ground preserved |
| VANT | J3.8 → XIAO VBUS | U6.12/.28 → VSYS; U6.13 → VSYS through R29 = 0 Ω | Supply changed from USB VBUS to the rail after D1/D2 |

### VEN and IRQ behavior

VEN is the chip's **input** at pin 10: the host drives it. IRQ is the chip's
**output** at pin 8: the host receives it. Datasheet Table 7 distinguishes
VEN's VBAT reference from IRQ's VDD(PAD) output domain. VEN accepts a high
above 1.1 V and a low below 0.4 V; it does not require a 5 V host signal.
Hold VEN low for at least 10 µs to reset, then allow the specified 2.5 ms
boot interval after raising it with supplies valid. See datasheet Tables
36/48/49 and section 11.5.

IRQ polarity is a significant configuration detail: UM11495 section 11.1,
page 94 gives `IRQ_POLARITY_CFG` = `0xA005`, default `0x00`. Bit 1 = 0 means
active high; bit 1 = 1 means active low. The setting is in EEPROM and persists
after firmware download. Thus a used breakout and a new IC need not have
the same IRQ polarity. This is a possible explanation for unexpected behavior,
not proof of what happened on the old prototype. Keep GPIO6 as an input and
make the firmware's IRQ interpretation match the chip configuration.

Neither the early host board nor the archived breakout circuit shows an IRQ
pull-up or inverter. Elechouse **R9 = 10 kΩ is on DWL_REQ**, not IRQ; this was
checked visually and against the PDF's embedded pin/net information.
V2 adds the 100 kΩ VEN pull-down; at 3.3 V its load is only 33 µA.

Sources: [NXP datasheet](https://www.nxp.com/docs/en/data-sheet/PN7160_PN7161.pdf),
[NXP user manual](https://www.nxp.com/docs/en/user-manual/UM11495.pdf),
[archived Elechouse schematic](../parts%20documentation/PN7160_schematic-3.pdf).

## Discrepancies and consequences

1. **Address straps need correction in V2.** R23/R24 reproduce the breakout's
   100 kΩ pull-downs on ADR0/ADR1, pins 1/3. Datasheet Table 58 specifies
   internal 55–120 kΩ pull-ups unless disabled by firmware. With those enabled:

   ```text
   Vpin / VDD(PAD) = 100k / (100k + Rinternal)
                  = 0.455 ... 0.645
   guaranteed LOW requires <= 0.35
   ```

   Therefore 0x28 is not guaranteed by the present resistor network. This is
   an inherited weakness, not evidence that the old module failed. Populate
   **R23/R24 as 0 Ω to GND** for the fixed address, as direct strapping is
   supported by UM11495 section 4.2.1. Alternatively, 10 kΩ gives at most
   0.154 × VDD(PAD) against the strongest specified pull-up. The previous ERC
   check verified connectivity but did not cover this analog divider margin.

2. **GPIO assignments changed.** Port firmware from VEN=0, IRQ=1, SDA=22,
   SCL=23 to **VEN=7, IRQ=6, SDA=4, SCL=5**. The direction of VEN/IRQ remains
   unchanged. Do not reuse XIAO D-pin numbering as ESP32-C3 GPIO numbering.

3. **RF power no longer comes directly from VBUS.** V2 powers VBAT/VBAT2
   and VDD(UP) from VSYS after two Schottky diodes. The USB planning minimum
   is 3.75 V, with initial VDD(TX) at or below 3.3 V. This requires matching
   PN7160 PMU/TXLDO settings, not blindly reusing a fixed-5-V breakout preset.
   AN12988 section 7.5 specifically calls out disabling TXLDO Check for supply
   values other than the supported 3.6 V/5 V check settings. Firmware remains
   responsible for setting and validating this configuration.

4. **The early board's clock net has an actual label error.** J3.3, the XIAO
   and the display share `SCL`, but PCF8574 U2.14 and its 1 kΩ pull-up R1
   belong to a separate `SDL` net. The label near the keypad clock is also
   misplaced. Both the saved PCB and production netlist retain the split.
   Consequently the old carrier has no R1 pull-up on the NFC clock bus and
   no connection from that bus to the keypad clock. Other attached modules
   or hand rework may have supplied the missing pull-up/connection. V2 has
   one connected `I2C_SCL` bus and 2.2 kΩ pull-ups on both I²C lines to 3.0 V.
   The lower pull-up rail is intentional for the OLED; the project's voltage
   checks retain high-level margin at the PN7160 and MCU.

5. **DWL_REQ has less convenient physical access.** The old J3 exposed DWL.
   V2's R21 reproduces the breakout's default-low resistor, but a net label
   alone is not a test pad. NXP AN12988 section 5.3 recommends host control.
   A reachable DWL_REQ pad, with VEN/GND/+3V3 access, would preserve manual
   firmware-download/recovery access without allocating another MCU GPIO.

6. **WKUP_REQ is explicitly grounded in V2.** The archived breakout leaves
   chip pin 39 open. V2 ties it low and uses I²C wake-up; it therefore cannot
   use dedicated-pin wake-up. This is consistent with the intended interface.
   It is unrelated to VEN or IRQ swapping.

7. **The archived Elechouse PDF is not a trustworthy connector-number map
   for this particular jumper arrangement.** Its P1 order is
   `DWL, GND, VBAT, VDD_PAD, VEN, IRQ, SCL, SDA`. Your J3 order is
   `DWL, SDA, SCL, IRQ, VEN, VDD, GND, VANT`, matching Elechouse's current
   module documentation. Compare named signals, not identical header numbers.
   Additionally, the PDF draws Elechouse R25 = 0 Ω between VDD_PAD and
   VBAT/VDD_UP. Populating that bridge while applying separate 3.3 V and 5 V
   would join the rails. The PDF cannot establish its population on your
   actual module. V2 keeps these domains separate; **V2 R29** only feeds
   VDD(UP) from VSYS. These resistor reference numbers belong to different
   schematics and are not interchangeable.

Sources: [NXP datasheet, Table 58](https://www.nxp.com/docs/en/data-sheet/PN7160_PN7161.pdf#page=54),
[NXP hardware guide](https://www.nxp.com/docs/en/application-note/AN12988.pdf),
[NXP user manual](https://www.nxp.com/docs/en/user-manual/UM11495.pdf),
[Elechouse current pinout](https://www.elechouse.com/docs/pn7160/).

## Remaining chip nets checked

These are the actual V2 assignments; package numbering is HVQFN40, not
breakout header numbering. Supply grouping agrees with datasheet Table 7.

| U6 pins | Current connection / review |
|---|---|
| 1 / 3 | ADR0 / ADR1 → R23 / R24 → GND; correct destination, resistor margin issue above |
| 2 | DWL_REQ → R21 → GND |
| 4 / 9 / 20 / 41 | All ground pins and exposed pad → GND |
| 5 / 7 | SDA / SCL → shared I²C bus |
| 6 | VDD(PAD) → +3V3 with C15/C16 |
| 8 / 10 | IRQ → GPIO6; VEN ← GPIO7, R22 to GND |
| 12 / 28 | VBAT2 / VBAT → VSYS with C17/C18; same supply |
| 13 | VDD(UP) → VSYS through R29 with C19/C20 |
| 14 / 18 / 22 | Internal TXLDO output and both TX supply inputs joined on NFC_TVDD, C23/C24 |
| 15 / 16 | RXN / RXP → C28/R25 and C29/R26 receiver taps respectively |
| 17 | VMID → C25 to GND, no external rail |
| 19 / 21 | TX2 / TX1 → R42/L3 and R41/L2 matching branches respectively |
| 23 / 24 / 25 | ANT1 / ANT2 / VDD(HF) open; enhanced RF-detector path unused |
| 26 / 27 / 31 | Analog/core supply pins joined on NFC_VDD18 with C21/C22; no external rail |
| 29 / 30 | XTAL2 / XTAL1 → crystal Y1.3 / Y1.1, C27 / C26 |
| 11 / 38 | Internally connected pins left open |
| 32–36 | NC pins left open |
| 37 / 40 | Unused DCDC_EN / CLK_REQ outputs left open |

The reference crystal electrodes are connected in the opposite order to Y1
in V2; the passive resonator has no polarity, so this is not a wiring error.
The RXN/TX1 and RXP/TX2 branch pairing remains the same as Elechouse's drawing.
RF values, local decoupling and the coil have intentionally changed as already
documented in [the antenna guide](nfc-antenna.md) and
[component refinements](component-refinements.md).

The actionable electrical correction from this review is **R23/R24**. VEN/IRQ
need the correct firmware GPIO mapping and IRQ polarity, not a hardware swap.
Adding physical recovery test access is a useful layout refinement.
