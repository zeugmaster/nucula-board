# Prototype component refinements — 2026-09-20

The first main-board prototype is intended to operate from a **dedicated 5 V
USB-C supply rated for at least 1.5 A at 5 V**, confirmed by the user. Battery runtime,
discharge capability and improved low-battery behavior are deferred by the
user. The charger, battery connector and existing buck/reset behavior remain.

The user also confirms the **26-contact Waveshare OLED pin order and
orientation**: the earlier count of 24 excluded two outer ground contacts.
The schematic can proceed to PCB layout within this prototype scope.

## Crystal selected from NXP's recommended references

Y1 is **NDK NX2016SA-27.12MHZ-EXS00A-CS06346**, JLCPCB **C3008209**.
It is explicitly listed in NXP AN14518 rev. 6.0, section 7.2, Table 9.
Its **2.0 × 1.6 mm** four-pad package replaces the unselected Epson 3225
candidate. The smaller package permits short oscillator routing; the crystal
can be assembled by the board assembler, while the load capacitors remain
0603 for adjustment. The RF antenna tuning capacitors remain hand-solder 0805.

The project footprint `Crystal_NDK_NX2016SA_2.0x1.6mm` uses NDK drawing
EXD14B-00467: **0.85 × 0.75 mm pads**, with centers spaced **1.35 × 1.05 mm**.
Pins 1/3 are the resonator; 2/4 connect to its metal cover and ground.

| Characteristic | NDK specification used |
|---|---|
| Frequency / mode | 27.120 MHz, fundamental |
| Nominal load | 10 pF |
| ESR | 25 Ω typical, **100 Ω maximum** |
| Crystal shunt capacitance | 0.60 pF ±20% |
| Motional capacitance | 1.54 fF ±20% |
| Drive | 10 µW typical, 100 µW maximum |
| Initial tolerance | ±15 ppm at 25 °C |
| Temperature shift | ±15 ppm over −20…+70 °C; ±40 ppm over −40…+105 °C |
| Aging | ±2 ppm first year in the newer NDK specification |

Use the actual NDK specification rather than the distributor's generic
60 Ω / −40…+125 °C catalogue attributes. The two downloaded NDK versions
agree on the oscillator parameters; the newer EXS11B-10535 includes the aging
limit. This selection does not guarantee a ±50 ppm total error over the
entire extended temperature range: initial, temperature, aging and PCB
loading errors must all be budgeted. Room-temperature tuning and cold/hot
start tests are still necessary.

The JLCPCB page was retrieved directly on 2026-09-20. Its public sourcing
data reported `overseasStockCount = 8896`, `canPresaleNumber = 8533`, and
`preMinPurchaseNum = 24`. This establishes available supplier stock through
JLCPCB, **not a reservation or confirmation of immediate assembly-factory
stock**. Check the assembly order's quantity/lead time before paying.
The machine-readable observation is [crystal-jlc-stock.json](components/crystal-jlc-stock.json).

Sources: [NXP oscillator guide](https://www.nxp.com/docs/en/application-note/AN14518.pdf),
[PN7160 datasheet rev. 4.2](https://www.nxp.com/docs/en/data-sheet/PN7160_PN7161.pdf),
[NDK exact-part specification](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/6749/CS06346-27.12M.pdf),
[JLCPCB C3008209](https://jlcpcb.com/partdetail/C3008209).
Copies of the NXP and NDK PDFs are in `parts documentation/`.

## Crystal load calculation and adjustment

C26 = **12 pF**, Samsung CL10C120JB8NNNC, and C27 = **15 pF**,
Samsung CL10C150JB8NNNC (C1644). Both are **0603, 50 V, C0G, ±5%**.
The 12 pF part has a manufacturer ordering code; no unverified JLCPCB code is
attached to it. These are starting values, not a claim of final frequency.

We used NXP AN14518 rev. 6.0 Figure 5's explicitly stated model:

```text
A = C26 + C_IC_IN + C_PCB_IN
B = C27 + C_IC_OUT + C_PCB_OUT
C_seen,NXP = A × B / (A + B) + C_PCB_CROSS + C_crystal_shunt
```

PN7160 Table 46 specifies 2 pF typical at each oscillator pin. In the absence
of this PCB, the calculation uses NXP's measured OM27160 board parasitics
as a reference: 1.19 pF input-to-ground, 1.31 pF output-to-ground, 1.39 pF
cross-coupling. **These are not measurements of our design.** Crystal shunt
capacitance is 0.60 pF. NXP's Figure 5 convention includes this shunt term;
do not silently interchange it with a Pierce formula that defines external
load separately from the crystal's internal capacitance.

Under that model, equal capacitors would be **12.770 pF**. The readily
available E12 combination **12 pF / 15 pF** yields 10.292 pF. The indicative
pull from the nominal 10 pF load is about **−1.95 ppm**, ignoring initial
crystal frequency error. Different loading on the two oscillator pins is
allowed by the two-capacitor model; this is separate from the antenna's
balanced network, whose corresponding branches must remain matched.

NXP recommends measuring and adjusting the RF carrier to **−5…0 ppm**
relative to 13.56 MHz. The calculated offset above cannot establish that
result before layout. Keep 10, 12, 15, 18 and 22 pF C0G 0603 parts for
replacement, and small 0.5–2.2 pF parts for temporary parallel adjustment.
Do not add long oscillator test-point stubs. Measure the carrier with loose
coupling so that probing the oscillator does not change its load. Increasing
load generally reduces frequency, but retest start-up after changing it.

Place Y1 immediately beside U6 pins 29/30 with short traces, local ground
returns for both capacitors and the case, and no switching-node routing
nearby. Measure repeated cold starts, standby wake-ups, frequency and drive
over the intended supply/temperature range. PN7160's stated oscillator
start-up maximum is 3 ms. AN14518 recommends using the retry/boosted-start
feature available in firmware 12.50.11; the retained C100E device originally
ships with older firmware, so check/update firmware before relying on it.
The labeled `NFC_DWL_REQ` net must be accessible for download-mode recovery.

Sources: [12 pF manufacturer data](https://product.samsungsem.com/mlcc/CL10C120JB8NNN.do),
[15 pF manufacturer data](https://product.samsungsem.com/mlcc/CL10C150JB8NNN.do).

## PN7160 decoupling and power capacitor selection

AN12988 rev. 1.6 section 7.1 calls for separate 2.2 µF capacitors close to
the digital/analog pins and two 2.2 µF capacitors on the transmitter supply.
The former single 10 µF plus 100 nF on each rail has been changed accordingly:

| References | Selected value/package | Placement / purpose |
|---|---|---|
| C21 / C22 | 2.2 µF each, 25 V X7R 10%, 0805 | U6.26 VDDA / U6.27 VDD, respectively |
| C23 / C24 | 2.2 µF each, 25 V X7R 10%, 0805 | U6.18 TVDD_IN / U6.22 TVDD, respectively |
| C17 / C19 | 10 µF, 25 V X7R 10%, 1206 | VBAT / VDD_UP; margin for 4.7 µF reference requirement |
| C15 | 1 µF, 50 V X7R 10%, 0805 | VDD_PAD |
| C16 / C18 / C20 / C25 | 100 nF, 50 V X7R 10%, 0603 | Additional local bypass / VMID |
| C1 / C2 / C4 | 22 µF, 25 V X7R 10%, **1210** | Charger input / battery / VSYS |
| C5 / C6 / C9 | 22 µF, 25 V X5R 10%, **1206** | Buck output and ESP32 local bulk |
| C40 | 10 µF, 25 V X7R 10%, 1206 | OLED boost input |
| C42 / C46 | 1 µF 50 V 0805 / 4.7 µF 50 V 1206 | OLED boosted-rail capacitors, X7R 10% |
| C44 / C47 | 4.7 µF / 2.2 µF, 25 V X7R 10%, 0805 | OLED logic bulk / VCOMH |

Exact manufacturer and LCSC codes are in [the BOM](bom.csv). In particular,
C1/C2/C4 use CL32B226KAJNNNE, C5/C6/C9 use CL31A226KAHNNNE, and
C17/C19/C40 use CL31B106KAHNNNE. The 2.2 µF CL21B225KAFNNNE/C19110
is a catalogue-supported prototype selection, but Samsung marks it **NRND**;
requalify its suggested successor for a production revision. The reference
2.2 µF values are nominal values, not promises of 2.2 µF minimum at bias.

Samsung's numerical, typical DC-bias curves were downloaded and archived as
JSON in `docs/components/`. For screening we multiply biased capacitance by
0.90 for tolerance, 0.85 for temperature and an additional 0.95 allowance.
The 5% allowance is an engineering assumption, not a manufacturer lifetime
guarantee. Combining typical bias data with independent derating factors is
a useful design screen, not a guaranteed combined-corner specification.

| Capacitor group | Evaluated voltage | Typical at bias | Screened estimate per part |
|---|---:|---:|---:|
| C1/C2/C4 | 5.5 V | 16.64 µF | 12.09 µF; target >10 µF |
| C5/C6/C9 | 3.393 V | 17.26 µF | 12.54 µF; C5+C6 >22 µF |
| C17/C19/C40 | 5.5 V | 6.86 µF | 4.98 µF; reference target 4.7 µF |

This is why several bulk capacitors now occupy 1206/1210 instead of generic
0805. Verify input/output ripple, load-step response and regulator stability
on the prototype. Keep the buck input loop compact despite the larger part.

Sources: [NXP hardware guide](https://www.nxp.com/docs/en/application-note/AN12988.pdf),
[1210 bulk capacitor](https://product.samsungsem.com/mlcc/CL32B226KAJNNN.do),
[1206 bulk capacitor](https://product.samsungsem.com/mlcc/CL31A226KAHNNN.do),
[10 µF capacitor](https://product.samsungsem.com/mlcc/CL31B106KAHNNN.do),
[2.2 µF capacitor](https://product.samsungsem.com/mlcc/CL21B225KAFNNN.do).
Each archived curve also records its source, AC measurement conditions and date.

## USB operation and deferred battery work

The schematic supports USB operation with **J2 empty**: power reaches VSYS
through D1/D2, independently of the battery and charger output. The separate
5.1 kΩ CC resistors remain. No USB-PD voltage above 5 V is requested.

Use a known USB-C source that offers at least **1.5 A at 5 V**. For a
4.75 V connector voltage and conservative 0.5 V allowance per diode,
VSYS is 3.75 V. The following planning case totals **1.10 A at USB**:

```text
I_USB = [(3.393 V × 0.5 A / 0.85) + (13.5 V × 0.030 A / 0.75)] / 3.75 V
        + 0.290 A NFC + 0.115 A charging + 0.020 A auxiliary
      = 1.101 A
```

The 500 mA logic-rail and 30 mA OLED currents are load assumptions, not
measured worst cases. Measure the actual panel current to validate this
budget. At VSYS 3.75 V the initial NFC TVDD setting of 3.3 V
retains more than NXP's typical 0.3 V TXLDO headroom requirement.

This closes a **steady-state prototype source budget**, not USB host
qualification: the circuit does not detect the source's advertised current,
limit input current, control capacitor inrush, or suspend charging with the
host. A 500 mA computer port is not the specified source. Verify power-up,
hot-plug and D1/D2 temperatures with the selected adapter/cable and loads.
The source must not fold back during input-capacitor charging. If it does,
input soft-start is needed before relying on that source. Firmware still
needs to initialize PN7160 power/clock settings and sequence OLED power.

J2 remains **JST B2B-PH-K-S(LF)(SN), 2.00 mm pitch**, pin 1 battery positive,
pin 2 ground. Battery testing is optional; existing charge current, lack of a
physical off switch and low-battery reset behavior are accepted for this
iteration. Pack selection/polarity/protection must be checked before attaching
a battery, but battery runtime is not a USB-prototype layout criterion.

## Confirmed OLED interface

The user corrected the initial count: **26 contacts total**, comprising the
24 originally counted contacts plus two outer ground contacts, at **0.50 mm
pitch**, with copper on the emitting side. They explicitly confirmed that
the supplied Waveshare 2.42-inch schematic has the correct pin order and
orientation. This confirmation is the basis for retaining the existing
26-pin circuit; no pin numbers have been shifted. Pins **1 and 26 are GND**,
as are the other ground pins in the reference, verified in the netlist.

DS1 now names the board-mounted **Hirose FH12-26S-0.5SH(55)** socket in the
BOM; the OLED glass is supplied separately. It is a bottom-contact socket
for **0.30 mm thick flex**. During PCB placement, check the actual insertion
thickness, pin-1 view and flex fold against the installed connector. Contacts
on the emitting face do not alone determine top/bottom contact after folding.
The electrical pinout blocker is closed; mechanical fit is part of the next
PCB placement work. No panel assembly model is claimed.

Sources: [user-supplied Waveshare schematic](../parts%20documentation/2.42inch-OLED-Module-Schematic.pdf),
[Hirose socket specification](https://www.hirose.com/product/p/CL0586-0576-2-55).

## Reproduction

Run `python3 tools/check_component_choices.py` to regenerate
[calculated results](components/calculations.json) from the archived curves.
Run `python3 tools/check_schematic.py` for native KiCad ERC, independent pin/net
checks, footprint checks, selected component checks and regenerated BOM.
Native KiCad PDF export generates `docs/schematic.pdf`.
No PCB layout, measured oscillator qualification, full-wave RF validation,
USB compliance claim or fabrication release is included in these refinements.
