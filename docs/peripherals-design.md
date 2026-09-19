# NFC, OLED and detachable keyboard

Revision B-draft, 2026-09-20. The project now has five schematic sheets:
system interconnect, power/ESP32, NFC, OLED, and keyboard.
[Combined drawing](schematic.pdf), [BOM](bom.csv), [verification](verification.json).
PCB layout and firmware have not been started.

## Shared I²C and MCU connections

| Function | ESP32 GPIO | WROOM-02 module pad | Notes |
|---|---:|---:|---|
| SDA | 4 | 3 | Shared open-drain data |
| SCL | 5 | 4 | Shared open-drain clock |
| NFC IRQ | 6 | 5 | PN7160 interrupt |
| NFC VEN | 7 | 6 | High enables NFC; external default low |
| OLED power | 3 | 15 | High connects boost input; external default low |
| OLED reset | 10 | 10 | High asserts reset through Q5 |
| Keyboard INT_N | 20 | 11 | Active-low, open-drain interrupt |

USB stays on GPIO18/19; battery ADC, USB detection, boot straps and reset
supervision are preserved. GPIO21 remains available for later additions.

| Device | Reference | Seven-bit address | Address selection |
|---|---|---|---|
| PN7160A1HN/C100E | U6 | `0x28` | ADR1/ADR0 pulled low |
| SSD1309 OLED glass | DS1 | `0x3C` | SA0 low |
| PCF8574T | U8 | `0x20` | A2/A1/A0 grounded |

Use **100 kHz**, the PCF8574T's maximum bus speed. R19/R20 provide the only
populated SDA/SCL pull-ups: 2.2 kΩ to **3.0 V**. Keep ESP internal pull-ups off.
U9, MCP1700T-3002E/TT, supplies the OLED logic and these pull-ups from +3V3.
Its SOT-23 pinout is **1 GND, 2 OUT, 3 IN**. C49/C50 provide local bypassing.

The SSD1309 specifies 3.3 V maximum operating logic supply, while the existing
buck's static upper bound is 3.393 V. A dedicated 3.0 V rail provides margin.
The estimated regulated range, including temperature and a full-load allowance,
is 2.865–3.135 V. This exceeds the largest calculated high-level requirement
of 2.545 V across the bus devices. At 400 pF, the pull-up RC estimate is 753 ns,
within the 1 µs standard-mode rise-time limit; low-level sink current is about
1.26 mA at 0.4 V. These checks assume U9 is regulating: measure low-current
dropout, startup and load transients on hardware, especially near low-battery
reset. Keep wiring short and total capacitance at or below 400 pF.
[MCP1700 datasheet](https://ww1.microchip.com/downloads/en/DeviceDoc/MCP1700-Data-Sheet-20001826F.pdf),
[PCF8574 datasheet](https://www.nxp.com/docs/en/data-sheet/PCF8574_PCF8574A.pdf),
[ESP32-C3-WROOM-02 datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-c3-wroom-02_datasheet_en.pdf).

## PN7160 and antenna network

The full balanced matching tree comes from the user-supplied
[PN7160 breakout schematic](../parts%20documentation/PN7160_schematic-3.pdf).
The I²C variant is **PN7160A1HN/C100E**, with a local symbol, HVQFN40 footprint
and STEP model. Pin numbers were checked against the
[NXP datasheet](https://www.nxp.com/docs/en/data-sheet/PN7160_PN7161.pdf) and
[hardware design guide AN12988](https://www.nxp.com/docs/en/application-note/AN12988.pdf).

VDD_PAD uses +3V3. VBAT/VBAT2 and VDD_UP use VSYS, allowing USB-only operation
without a battery. R29 is the 0 Ω VDD_UP feed. Internal regulator output pin 31
feeds VDDA/VDD pins 26/27; internal TX regulator pin 14 feeds pins 18/22.
Neither internal output is tied to an external supply. C15–C25 decouple each
domain and VMID; all ground pads, including exposed pad 41, are connected.

VEN and DWL_REQ default low. WKUP_REQ is grounded for I²C wake-up. ANT1/ANT2
and VDHF are unused; firmware must use the corresponding normal RF-detection
configuration. I²C address selection is documented in
[NXP UM11495](https://www.nxp.com/docs/en/user-manual/UM11495.pdf).

| Supplied RF reference | Project refs | Role |
|---|---|---|
| L1 / L2 | L2 / L3 | Series EMC inductors |
| C53 / C54 | C30 / C31 | Post-inductor shunt capacitors |
| C52 / C56 | C32 / C33 | Primary series matching |
| C51 / C55 | C34 / C35 | Parallel series trim, DNP |
| C61 / C63 | C36 / C37 | Antenna-side shunt capacitors |
| C62 / C64 | C38 / C39 | Parallel shunt trim, DNP |
| R13 / R14 | R27 / R28 | Series damping |
| C59 + R11 | C28 + R25 | RXN tap from the TX1 post-inductor node |
| C58 + R12 | C29 + R26 | RXP tap from the TX2 post-inductor node |
| A1 | A1 | Coil ends on pads 1/2, reference/shield ground on pad 3 |

RF values are deliberately **TBD**, including damping and receiver branches.
Use C0G capacitors, initially 50 V rated, and high-Q RF inductors with adequate
current and self-resonance. Final voltage/current stress must be measured after
tuning. The antenna footprint is a labelled interface placeholder, with no coil
geometry or center-tap assumption. It must be replaced before PCB fabrication.

Y1 is a 27.12 MHz Epson TSX-3225-family candidate. C26/C27 = 10 pF are the
reference's starting values only. Select the exact crystal load capacitance,
ESR and drive grade before ordering, then account for PCB and pin capacitance.

## OLED glass and boost supply

The supplied
[Waveshare 2.42-inch OLED schematic](../parts%20documentation/2.42inch-OLED-Module-Schematic.pdf)
defines a **26-contact SSD1309 glass interface**. DS1 represents that interface;
the controller is already on the glass. Pin 6/BS1 is high, BS2 and CS are low,
and pin 10/SA0 is low. D0 is SCL; **D1 and D2 both connect to SDA** for data and
acknowledgement. Unused parallel inputs are grounded; pin 4 is NC.

The shared 3.0 V logic rail replaces the reference's RT9193-33 stage. The
TXB0108 translation stage is omitted: all hosts share compatible voltage levels
and open-drain I²C. Q5 translates the MCU reset signal without applying a 3.3 V
push-pull level to the OLED logic rail.

U7 is **AP3012KTR-E1**, with 10 µH Coilcraft LPS4018-103MRC and an SS14
Schottky output diode. R30/R31 = 1.8 MΩ / 200 kΩ, both 0.1%, set nominal
**12.5 V**. Reference/bias/divider corner estimates are 11.50–13.50 V, within
SSD1309's 7–16 V range. R32 = 910 kΩ retains the reference IREF starting point;
contrast and actual panel current still require validation.
[AP3012 datasheet](https://www.diodes.com/datasheet/download/AP3012.pdf),
[Coilcraft LPS4018 specifications](https://www.coilcraft.com/en-us/products/power/shielded-inductors/ferrite-drum/lps/lps4018/lps4018-103/),
[SSD1309 datasheet](https://files.waveshare.com/wiki/2.42inch-OLED-Module/SSD1309Datasheet.pdf).

Q3/Q4 disconnect the **input** of the boost stage, including its diode
feed-through path, while the OLED logic stays powered. The boost defaults off.
There is no active OLED-rail discharge, following SSD1309's guidance to let
VCC float when switched off. Firmware must:

1. Keep OLED power off while logic stabilizes; assert GPIO10 high for reset.
2. Hold reset for at least 3 µs (use 1 ms), release it, and allow the reset RC
   to rise (at least 5 ms for the present 10 kΩ / 100 nF network).
3. Initialize the SSD1309, enable OLED power, wait for the boost to settle,
   then issue display-on `AFh`.
4. On shutdown, issue display-off `AEh`, disable the boost and keep logic
   powered. Validate power-fail/rapid restart behavior on the actual glass.

A 30 mA panel-load scenario at 3 V input, 75% assumed efficiency, minimum
switching frequency and −20% inductance gives approximately 0.313 A peak
inductor current. The AP3012's 500 mA switch limit is **typical**, not a
guaranteed display-output rating. Full-white current, efficiency and overshoot
must be measured before fixing brightness limits.

The assigned **Hirose FH12 26-way 0.5 mm footprint is provisional**. The
reference PDF does not establish flex pitch, contact side or whether the glass
requires direct soldering. Exact glass ordering code and mechanical drawing
are required before layout; the connector model does not represent the glass.

## Breakaway keyboard

U8 is **PCF8574T**, an eight-bit quasi-bidirectional I/O expander, in the same
wide SOIC-16 footprint as the earlier BOM. J3 is a **DNP/user-fitted 1×9,
2.54 mm header**: pins 1–8 are P0–P7; pin 9 is ground. This supports eight
switch lines plus common ground, or eight lines of a keyboard matrix. Final
matrix mapping and debounce are firmware decisions. Write 1 to PCF pins before
using them as inputs; service its active-low interrupt by reading the port.

Every physical part on `keyboard.kicad_sch` carries
`PCB Region = BREAKAWAY_KEYBOARD`. Only five nets cross the future break line:
+3V3, GND, SDA, SCL and INT_N. J4 on the main board and J5 on the detachable
section are DNP 1×5, 2.54 mm headers with matching pin order:

| Pin | Signal |
|---:|---|
| 1 | +3V3 |
| 2 | GND |
| 3 | SDA |
| 4 | SCL |
| 5 | INT_N |

While attached, PCB traces provide these connections. After separation,
populate J4/J5 and reconnect straight through. R37 provides the module INT
pull-up; R40 keeps the MCU input defined when the module is absent. R38/R39
are DNP optional bus pull-ups for standalone use; leave them unpopulated when
connected to the main board. Layout must keep parts/pads away from fracture
areas and control every trace and plane crossing. Hot-plug operation and long
cables are not designed or qualified.

## Power budget

NFC transmitter and OLED boost power come directly from VSYS; their load is
additional to the existing buck rail. An illustrative simultaneous upper-load
scenario at 3.2 V VSYS is:

| Load assumption | Approximate VSYS current |
|---|---:|
| 3.31 V rail at its 500 mA design target, 85% buck efficiency | 609 mA |
| NFC allowance: 250 mA transmitter plus 40 mA controller | 290 mA |
| OLED at 12.5 V / 30 mA, 75% boost efficiency | 156 mA |
| Total, before small auxiliary currents | 1.06 A |

This is a planning scenario, not a measured consumption claim or guaranteed
worst case. NFC matching/configuration and display content affect actual load.
A 400 mAh pack would need roughly 2.7C capability for this scenario; many small
packs cannot supply it. Select a suitable protected cell or constrain concurrent
RF/Wi-Fi/display use and brightness. D1/D2 are upgraded to B340A for current
margin, but voltage drop, temperature and copper still need verification.

Charging remains 100 mA. The previously documented USB input-current,
enumeration/suspend and inrush limitations remain open; USB current capability
cannot be inferred from the CC pulldowns alone. Resolve the input budget and
actual battery discharge rating before PCB release.

## Verification and remaining selections

`python3 tools/check_schematic.py` passes native ERC on all five sheets:
**124 components, 87 nets, zero errors/warnings**. It checks 57 named net groups,
additional internal connections and ground/NC pads, all physical symbol-to-pad
mappings, DNP/region/address fields, available model paths and static voltage
calculations. The five-page PDF was rendered and visually inspected.

Remaining decisions are RF tuning/coil geometry, crystal grade/load, exact OLED
glass/flex and full-white current, the battery/input power budget, and final
MLCC ordering codes with effective capacitance under bias. These require the
eventual mechanical parts or hardware measurements; they are explicitly marked
in the schematic/BOM rather than hidden behind guessed ordering codes.
