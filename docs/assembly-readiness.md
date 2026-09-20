# Component and footprint readiness — 10-board prototype

Checked 2026-09-20 against KiCad 10.0.6 and JLCPCB's public catalogue;
J2 changed to SMT and its stock rechecked 2026-09-21 (Berlin).
**Ready to begin component placement. Every physical symbol has a resolving
footprint and every populated purchased item has an exact manufacturer part
number and JLCPCB C-code.** This is not a fabrication release: the main PCB
has a preliminary layout; routing, final DRC, assembly rotations and CPL remain to be done.

There are **128 physical symbols**: 116 populated purchased components,
11 DNP components, and one etched PCB antenna. The populated BOM contains
**55 distinct purchased parts**, grouped by exact C-code rather than value alone.
The stock screen passes for ten boards, but two RF parts have limited stock.

## Files to use

- [JLCPCB BOM](assembly/jlcpcb-bom.csv): one-board reference designators, exact
  MPNs, catalogue packages and C-codes. Select **10 assembled boards** in the
  order; do not multiply designators or upload the purchasing report as the BOM.
- [Ten-board purchasing report](assembly/purchasing-10-boards.csv): quantity per
  board, total placements, public loss/minimum fields, stock and source links.
- [Footprint/model audit](assembly/footprint-audit.csv): every physical reference,
  including DNP pads and A1, with resolved footprint hashes and model paths.
- [Stock snapshot](assembly/jlc-stock-snapshot.json) and
  [machine-readable readiness result](assembly/readiness.json).
- [Updated schematic](schematic.pdf) and [complete engineering BOM](bom.csv).

DS1's purchased item is the Hirose FPC **socket**, not the OLED glass. The OLED
and keypad are user-supplied external modules. J3/J4/J5 remain DNP; J3 still has
isolated end pins 1/9 and P0–P6 on pins 2–8. A1 is manufactured copper, excluded
from the assembly BOM and future CPL. J2 is the populated **JST-PH 2 mm vertical
surface-mount battery connector**, **B2B-PH-SM4-TB(LF)(SN) / C160352**. JLCPCB
lists `smtWeld`, supporting Economic and Standard SMT assembly. It replaces the
through-hole C131337 connector; there are no remaining populated components
classified as manual/through-hole assembly in this catalogue audit. Mechanical
anchors on other SMT connectors are still part of their respective footprints.

J2 stock was checked at **2026-09-20 22:17 UTC / 2026-09-21 00:17 Berlin**:
**35,730 in stock; 34,746 available to order**, versus 10 needed. Public minimum
placement is 5 and loss allowance is 0, so the planning quantity remains 10.
The listed pre-order MOQ of 42 applies to pre-orders, not this available stock.
Stock is a dated observation, not a reservation.
[JLCPCB C160352](https://jlcpcb.com/partdetail/JST-B2B_PH_SM4_TB_LF_SN/C160352).

The project-local copy of the standard KiCad SMT footprint has two electrical lands and two mechanical
hold-down lands, all with paste apertures and no plated holes. JST's top-entry
land pattern and pin-1 mark were checked against the footprint. **Pin 1 remains
VBAT and pin 2 GND**; both `MP` hold-down pads are intentionally unconnected.
An update-from-schematic warning about `MP` having no symbol pin is mechanical,
not a missing battery connection. The larger package is moved slightly inward
from the left edge; its 90° rotation and electrical pin order are retained.
[Manufacturer drawing, pages 2 and 4](../parts%20documentation/JST-PH-SMT-datasheet.pdf).
The installed library's SMT 3D model was missing, so its unresolved reference
was removed from the local copy. J2 has no 3D body model; fabrication geometry is
unchanged from the verified KiCad footprint.

J3 and DS1 are centered on the board's X = 80 mm centerline (edges at X = 50
and 110 mm). J3 moved 2 mm left and DS1 moved 0.5 mm left; their Y positions
and rotations are unchanged. The [saved-board check](assembly/connector-update-check.json)
confirms zero DRC findings on the three changed connectors, with the other 125
footprints and board outline unchanged. The preliminary board still has 18
unrelated DRC findings. The subsequent [35 mm keyboard breakaway](keyboard-breakaway.md)
adds two mechanical footprints (130 PCB footprints total), places the keyboard
support parts, and routes the five J4-to-J5 connections. Its
[verification](keyboard/breakaway-check.json) confirms no new DRC findings;
303 unconnected items remain. MB1/MB2 are excluded from BOM and placement output.

## Sourcing changes applied before placement

| Reference | Final selection | Why / footprint consequence |
|---|---|---|
| J2 | JST B2B-PH-SM4-TB(LF)(SN), **C160352** | Stocked SMT top-entry PH connector; same 2 mm mating family and battery polarity. Larger footprint with two solder hold-down tabs replaces through-hole assembly. |
| U5 | TI TLV803EA30DBZR, **C5218924** | The DCKR variant was out of stock. Same 3.08 V threshold and nominal 200 ms delay; **SOT-23 replaces SC70**. Both selected variants use 1=GND, 2=RESET, 3=VDD. |
| J1 | GCT USB4105-GF-A-120, **C5184243** | Unsuffixed part had zero available order quantity. Same XY land pattern; shell stakes are **1.20 mm**, suitable for the specified 1.6 mm board. |
| R30 | TE CPF0805B1M8E, **C2088132** | Stocked 1.8 MΩ, **0.1%**, 0.1 W, 100 V; **0805 replaces 0603**. Divider voltage and precision remain unchanged. |
| U1 | TOPPOWER TP4054-42-SOT25R, **C32574** | Exact stocked catalogue ordering code replaces SOT235. Catalogue-linked manufacturer sheet confirms the same five-pin assignment and 100 mA with 10 kΩ. SOT-23-5 footprint retained. |
| C30/C31 + C53/C54 | 330 pF 1% **C527075** + 33 pF 5% **C309485** | Replaces the poorly stocked 360 pF 2% selection with **363 pF ±1.364%**, 100 V C0G, using the existing parallel pads. C53/C54 now populated with paste openings. |
| C32/C33 | Yageo CC0805FRNPO0BN680, **C576904** | Stocked 68 pF, 100 V NP0, **1%**; tighter than the previous 2% requirement. |
| R41/R42 | Yageo RC0805JR-070RL, **C96345** | 0805 removable links, **2 A rated jumper**, initial resistance <50 mΩ. Package is 0.125 W; the previous generic 0.25 W description is replaced by the meaningful jumper current rating. |
| Remaining populated items | Exact MPN + C-code assigned | Generic resistors, LED and bypass capacitors are now specified. Previously calculated bulk MLCC choices and precision divider tolerances are retained. |

Sources: [TI pinout and ordering table](https://www.ti.com/lit/ds/symlink/tlv803e.pdf),
[GCT ordering/dimensional drawing](https://gct.co/files/drawings/usb4105.pdf),
[TE exact resistor](https://www.te.com/en/product-7-1614894-6.html),
[C32574 manufacturer sheet](../parts%20documentation/TP4054-42-SOT25R-C32574-datasheet.pdf),
[Yageo resistor selection guide, RC0805 jumper rating](https://www1.futureelectronics.com/doc/YAGEO%20AMERICA%20CORPORATION/RL0805FR-070R4L.pdf).
Individual current catalogue sources are linked in the purchasing CSV.
[Archived drawing provenance and hashes](assembly/sources.json).

The revised NFC network calculates **18.838 − j0.140 Ω at 13.56 MHz** under the
documented assumed antenna model. Independent full differential ngspice agrees
with Python to 3.01e-12 relative difference. These checks validate the arithmetic,
not measured RF performance. Four free 0805 no-paste tuning pads remain at
C34/C35 and C38/C39; the EMC stage can be adjusted by changing the populated
33 pF parts in matched pairs. The [NFC guide](nfc-antenna.md) includes the updated
tolerances, ESR model, voltage/current estimates and tuning procedure.

## Parts to secure before placing the assembly order

| References | JLCPCB part | Needed for 10 boards | Planning quantity incl. published allowances | Available order quantity at audit |
|---|---|---:|---:|---:|
| **L2/L3** | [C20417049, Coilcraft 0805HP-151XGRC](https://jlcpcb.com/partdetail/C20417049) | 20 | 20 | **21** |
| **C36/C37** | [C527192, Yageo CC0805GRNPO0BN101](https://jlcpcb.com/partdetail/C527192) | 20 | 28 | **50** |
| R27/R28 | [C2079511, Vishay CRCW12062R70FKEAHP](https://jlcpcb.com/partdetail/C2079511) | 20 | 24 | 130 |
| R30 | [C2088132, TE CPF0805B1M8E](https://jlcpcb.com/partdetail/C2088132) | 10 | 10 | 154 |
| Y1 | [C3008209, NDK NX2016SA-27.12MHZ-EXS00A-CS06346](https://jlcpcb.com/partdetail/C3008209) | 10 | 10 | 8,538 |

**L2/L3 remain the primary procurement risk.** Only one part remains beyond the
20 placements, and no parts are reserved by this audit. Check/secure this exact
part before relying on a quick assembly turn. A generic 150 nH 0805 inductor is
not automatically equivalent: body/lands, RF loss and impedance differ, and the
calculation uses the Coilcraft model. Murata LQW2BANR15G00L (C2046580) was found
with more stock, but is **not qualified as a drop-in alternative**. It would need
its own land-pattern and RF-model review. R27/R28 must remain the specified
high-power series, not an ordinary 1206 resistor with the same resistance.

CL21B225KAFNNNE/C19110 remains **NRND**, as already documented. The snapshot
shows ample stock for this prototype; qualify a current successor and its
DC-bias behavior before a production revision. Stock availability today cannot
guarantee supply on a later date. The audit makes exact parts easy to find and
identifies the exceptions instead of claiming future availability.

## How stock and quantities were interpreted

JLCPCB's part pages and public search endpoint were read without an account.
The raw page field `overseasStockCount` is displayed as **In Stock**; its name
does not establish Global Sourcing. `canPresaleNumber` is **Available Order Qty**.
Negative values are treated as zero. This distinction rejected the old USB
connector even though its gross stock count was nonzero.

For planning, the checker uses:

```text
placements = references per board × 10
planning quantity = max(placements, leastPatchNumber) + lossNumber
```

This is a conservative screen using the public minimum-placement and loss fields,
not an authenticated assembly quotation. JLCPCB's final BOM matching page controls
actual consumption, attrition, service eligibility and price. `preMinPurchaseNum`
is recorded for possible replenishment; it is **not imposed as an in-stock assembly
MOQ**. For example, Y1's pre-order minimum of 24 does not force 24 crystals onto
this ten-board build. Most selections are Extended parts; expect applicable
setup/handling charges rather than an all-Basic BOM.

Sources: [JLCPCB BOM format](https://jlcpcb.com/help/article/bill-of-materials-for-pcb-assembly),
[minimum/loss and matching explanations](https://jlcpcb.com/help/article/common-bom-and-cpl-matching-issues-and-explanations),
[in-stock versus pre-order rules](https://jlcpcb.com/help/article/how-to-build-your-own-parts-library-in-jlcpcb),
[parts sourcing services](https://jlcpcb.com/help/article/pcba-parts-sourcing-instruction).

## Footprints and 3D coverage

All assigned footprint files resolve, and every schematic physical pin has a
matching numbered footprint pad. **123 of 128 symbols have resolving 3D models.**
The exceptions are A1 (etched copper, no separate body) and L1–L4 (footprints
ready, optional body models absent). The ESP32 and PN7160 STEP files are bundled;
other assigned models use installed KiCad libraries. These are visual package
representations, not a certification of every selected vendor variant. In
particular, the generic USB4105 model may depict the original stake length.

The L1 land drawing was additionally checked against the exact current Taiyo
Yuden part: **0.8 × 2.7 mm pads on 2.2 mm centers**, matching the project footprint.
[Archived manufacturer drawing](../parts%20documentation/LSXND3030QKT2R2MNG-datasheet.pdf).
The source explicitly identifies NRS3015T2R2MNGH as the former part number.
The RF inductors retain their manufacturer-derived 0805HP lands; the NDK crystal
retains its specific 2016 land pattern. U8 is the **wide 7.5 mm SOIC-16** variant.
The Hirose socket accepts 0.30 mm flex and has bottom contacts; the confirmed
electrical pin order remains, with physical fit/fold to check during placement.

## Reproduce and refresh

```sh
python3 tools/check_schematic.py
python3 tools/check_assembly_readiness.py --boards 10
python3 tools/check_component_choices.py
python3 tools/nfc/calculate.py
python3 tools/nfc/check_spice.py
```

The last two commands need the dependencies in `tools/nfc/requirements.txt` and
KiCad's ngspice library. The assembly checker is offline and uses the dated
snapshot. To refresh public quantities without placing any order:

```sh
python3 tools/refresh_jlc_stock.py
python3 tools/check_assembly_readiness.py --boards 10
```

The refresh script rejects part-number/manufacturer/package changes rather than
silently substituting a part. JLCPCB's undocumented public endpoint may change;
if retrieval fails, inspect the linked part pages. The stock report is dated and
should always be regenerated close to ordering. Do not generate a CPL from the
blank PCB; export it after placement and verify every polarized part's orientation
in JLCPCB's assembly preview.
