# Stock substitution qualification — 9 October 2026

Status: engineering screening for five prototypes; **physical RF qualification is outstanding**.
The user explicitly accepted a different RF part after revalidation. There is
no claim of identical electrical specifications or guaranteed unchanged read range.

## Selected parts

| References | Original | Selected / JLC code | Preserved / changed |
|---|---|---|---|
| C10 C11 C13 C14 C16 C18 C20 C25 C43 C45 C48 C51 C55 | CL10B104KB8NNNC | CL10B104KB8NNNL / C913912 | 0603, 100 nF, 50 V, X7R, 10%; Samsung confirms C and L are reel-packaging alternatives of the same component |
| C28 C29 | GRM2165C2A102JA01D | CC0805JRNPO0BN102 / C326940 | 0805, 1 nF, 100 V, C0G/NP0, 5%; manufacturer changes |
| C36 C37 | CC0805GRNPO0BN101 | 0805CG101F101NT / C464454 | 0805, 100 pF, 100 V, C0G; tolerance tightens from 2% to 1% |
| L2 L3 | 0805HP-151XGRC | 0805CS-151XGLC / C38190612 | 150 nH, 2%; different RF impedance and terminations, described below |

The original-BOM live check found four unavailable lines, including C36/C37
which were not in the initial user list. Inventory observations are not reserved
parts. See the package purchasing table for quantities, minimums and loss allowances.

The 150 nH catalogue search returned 314 records across seven pages. Additional
part-number searches covered alternative HP packaging, CS/HT/HQ, R15G/R15F,
151XG and air-core families. No exact stocked HP electrical equivalent was
verified. The CS option has a directly published manufacturer RF model and
allows retention of the original copper. Murata LQW2BANR15G00L and larger
Coilcraft 1008CS/1206CS/1812SMS candidates also differ electrically; the larger
parts offer no established equivalence and would alter the mounted geometry.

## Inductor electrical screening

The original and new ceramic-core inductors are both 150 nH ±2% at the vendor's
100 MHz test frequency. HP DCR maximum is 0.288 Ω versus CS 0.560 Ω. HP SRF is
1150 MHz typical versus CS 920 MHz typical. HP Q is 80 typical at 250 MHz;
CS Q is 50 minimum at 250 MHz: these are different statistical specifications,
not a measured side-by-side Q ratio. The 15°C-rise DC reference current changes
from 0.60 A to 0.40 A; it is not an absolute maximum or an RF thermal guarantee.

Published typical models use the topology
`Rdc + ((k*sqrt(f) + jwL) || (Rpar + 1/jwC))`:

| Part | Rdc Ω | k | L nH | C pF | Rpar Ω |
|---|---:|---:|---:|---:|---:|
| 0805HP-151 | 0.288 | 1.554e-4 | 148.8 | 0.135 | 10 |
| 0805CS-151 | 0.560 | 2.230e-4 | 149.0 | 0.110 | 24 |

No matching capacitance, resistance or nominal inductance was retuned.
`rf-qualification.json` contains 237 paired cases, 474 ngspice runs, and hashes
of the exact board/netlist/model/script inputs. These include coil L ±10%,
assumed coil R/C and receiver-load corners, 200 independent component-tolerance
samples, and replacement-capacitor ESR scenarios from 0.003 to 0.3 Ω.
The ESR bounds are engineering assumptions, not guaranteed vendor limits.

Acceptance limits chosen for this engineering substitution are <10% relative
change in carrier input impedance and coil current, terminal current <0.4 A,
capacitor peak voltages below ratings, and each damping resistor below the
existing 0.5 W screening limit. These are project criteria, not an NXP RF
conformance specification. Models do not establish global worst-case bounds.

At 13.56 MHz nominal, input impedance changes from 18.84 − j0.14 Ω to
19.88 − j0.11 Ω; coil current under the modeled 3.3 V drive decreases from
251.4 mA to 238.3 mA. Across tested scenarios, the largest impedance change is
8.44% and coil-current change 6.89%. At the deliberately conservative ideal
5.5 V square-drive fundamental, maximum terminal current is 378.5 mA,
capacitor peak voltage 42.84 V and damping-resistor power 0.441 W.

The separate frequency-dependent odd-harmonic estimate (1st–39th harmonics)
gives nominal CS terminal current 251.0 mA and inductor dissipation 87.7 mW
at 5.5 V. A DC-derived thermal-resistance estimate gives ~14.7°C nominal rise.
Doubling that nominal loss at 85°C ambient remains below the 140°C part limit.
This is a screening estimate only; neither board thermal resistance nor
worst-case RF heating has been measured. Check temperature on assembled boards.

## Mechanical and placement review

All 19 substitutions retain their original footprint anchors, orientation,
net connections and pad copper/mask/paste. Capacitor packages remain 0603 or
0805 as originally laid out. L2/L3 now use the explicitly named custom footprint
`L_Coilcraft_0805CS_RevALands`, with a 2.29 × 1.73 mm maximum body drawing.
The original HP maximum body length was 2.21 mm, so this is +0.04 mm per end.
The existing 3.66 × 2.48 mm courtyard contains the new body.

CS datasheet dimensions A/B/C are 2.29/1.73/1.52 mm maximum. Terminal wraparound
is approximately 0.38 mm at both ends. The retained pads span x = −1.58…−0.56
and +0.56…+1.58 mm, y = ±0.99 mm, relative to the footprint anchor. They cover
the contact strips indicated by the manufacturer's body/terminal drawing and
provide toe/side solder area. These retained 1.02 × 1.98 mm pads with 1.12 mm
gap differ from the manufacturer's recommended 1.02 × 1.78 mm pads with 0.76 mm
gap. Terminal-wrap dimensions are approximate; this is an engineering fit
review, not a manufacturer endorsement of the custom land pattern. Inspect
first-article joints. No body-center or catalogue rotation offsets are added.

The selected L termination is RoHS-compliant silver/palladium/platinum glass
frit and **is not halogen-free**. The archived CS datasheet explicitly covers
this suffix. The maximum body and terminal pattern are common to the series.

The updated regression permits only the listed metadata/tolerance/body-drawing
amendments. It still rejects pad, placement, routing, matching-value, stackup
or via-process changes. Nine mutation tests exercise this behavior, including
moving a substituted inductor, changing its pad and selecting an unreviewed MPN.
Independent fabrication Gerber comparison continues to require exact rev-A
NFC copper and solder-mask geometry.

## Scope and sources

This review does not simulate the complete PN7160 controller, firmware, tags,
RF emissions, assembled-board electromagnetic coupling or read range. Use the
same test tags/setup as rev A and check AGC, temperature and supply current.
A simulation pass cannot guarantee that no physical tuning will be needed.

- [Samsung common family and packaging codes](https://product.samsungsem.com/cn/mlcc/CL10B104KB8NNN.do)
- Yageo and Fenghua manufacturer datasheets archived as C326940.pdf / C464454.pdf; ordering codes retain voltage and dielectric ratings.
- [Coilcraft CS datasheet](https://www.coilcraft.com/getmedia/dd5f20e4-1ff7-43df-8317-b693eb2dce3e/0805cs.pdf), archived as 0805cs.pdf.
- [Coilcraft CS RF model, doc 158-6, 2025-01-16](https://www.coilcraft.com/getmedia/c86a99da-e310-4932-bb03-09af08346f8a/spice_0805cs.pdf), archived as 0805cs-spice.pdf.
- [Coilcraft HP reference model](https://www.coilcraft.com/getmedia/d2f56f9b-ef33-42ca-bf60-5b64b7e705a7/spice_0805hp.pdf).
