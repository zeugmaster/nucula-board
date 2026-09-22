# Five-board Berlin assembly contingency

Prepared 2026-09-22 against the **submitted r2 fabrication package**. **Private-customer online checkout is required.** The PCB candidate is now **Eurocircuits for five bare PCBs and one stencil**, subject to its online DFM and stackup checks; components remain **LCSC + Mouser**. CONTAG is excluded from the online-order route; Multi-CB is excluded because it sells only to businesses/public institutions. This is a researched procurement plan, not an order or a confirmed delivery commitment. No supplier has been contacted and no stock has been reserved.

Start with the [Eurocircuits online configurator](https://be.eurocircuits.com/shop/assembly/configurator.aspx) and the prepared [online ordering guide](pcb-online-ordering.md). Eurocircuits has an online order workflow and explicitly documents private customers in its account/VAT guidance. **The exact PCB is not yet qualified for its service:** the 0.20 mm hole / 0.45 mm pad geometry needs drill/annular-ring review and the USB pair needs a compatible stackup. [Ordering workflow](https://www.eurocircuits.com/), [private-customer reference](https://www.eurocircuits.com/user-guides/customer-account-user-guide/finance-and-administration/value-added-tax-vat/).

The target is **materials in Berlin on 29–30 September 2026**, seven to eight calendar days after this plan was requested. **Arrival time takes priority over cost**; show the full cost before ordering. The plan accounts for all **55 BOM lines / 116 placements per board / 580 placements for five boards**. It preserves 52 original MPNs and proposes three capacitor substitutions. The original design, BOM and Gerbers are unchanged. Lab equipment and access still need checking.

**This is a conditional route to that date, not a confirmed rescue.** LCSC lists a holiday operations notice covering 25 September–7 October. Its detailed warehouse/carrier schedule could not be retrieved, so neither a complete closure nor normal service is assumed. Obtain a dispatch commitment before relying on it. [LCSC notice index](https://www.lcsc.com/help-center/search).

## The three orders

| Order | What to request | Evidence and remaining confirmation |
|---|---|---|
| **Eurocircuits** | 5 complete 60 × 110 mm four-layer bare PCBs, ENIG, resin-filled/capped vias, electrical test; 1 top-side 0.10 mm stencil | Use STANDARD pool as the starting online configuration, with stackup/impedance review. Its general bare-board lead time is 5 working days, with shorter options in the calculator. The final configuration, drill rules, date and price must be accepted by Visualizer/CAM. PCB Proto's 0.25 mm minimum PTH rule does not cover the existing 0.20 mm holes unchanged. |
| **LCSC** | 45 exact-MPN lines in `lcsc-import.csv`; express courier to Berlin | Public catalogue pages list sufficient stock for the planned quantities. U1, U2 and Y1 make this the most straightforward route without active-device substitutions. LCSC says in-stock orders usually need a few days of processing; express courier transit comes after that. Confirm every line as warehouse stock and reject backorders. |
| **Mouser Germany** | 10 lines in `mouser-import.csv`, cut tape; fastest quoted Germany delivery | Public Mouser listings show sufficient stock for all 10 selected lines, including the three proposed substitutes. Several observations come from regional pages cached weeks/months ago. Confirm stock and delivery in the German basket; a Munich sales office does not establish German warehouse stock. |

Sources: [Eurocircuits STANDARD pool, including stencil options](https://www.eurocircuits.com/services/standard-pool/), [resin filling with copper caps](https://www.eurocircuits.com/technical-guidelines/pcb-design-guidelines/via-filling/), [PCB Proto limits](https://www.eurocircuits.com/services/pcb-proto/), [LCSC dispatch policy](https://www.lcsc.com/help-center/shipping-delivering/order-shipping-and-tracking), [LCSC courier options](https://www.lcsc.com/help-center/shipping-delivering/shipping-methods), [Mouser dispatch service](https://www.mouser.de/de/customer-resource-center/), [Mouser Germany delivery terms shown on its site](https://www.mouser.de/en/cs/localsites/).

**Ordering workflow:** upload the released Gerbers, select bare boards and a delivered top stencil, and use the prepared fabrication notes. The site has a real configurator and checkout; this research tool could read its form but could not operate the JavaScript calculation/upload workflow, so no populated cart, submitted DFM result or live PCB price is claimed. The original [CONTAG RFQ](pcb-rfq-de.txt) is retained only as a superseded draft. Multi-CB's [business-only restriction](https://www.multi-circuit-boards.eu/leiterplatten-express.html) rules it out for this purchase.

## Timing and the decision to activate

Both **Eurocircuits' exact DFM/production slot and LCSC's dispatch** remain schedule gates. European PCB manufacture removes one overseas shipment, but this route retains the overseas LCSC component shipment.

The requested 29–30 September arrival leaves only **five to six weekdays after 22 September**. LCSC's usual processing of a few days, followed by international transit, can consume that window. The holiday notice adds uncertainty. Express shipping alone does not establish arrival by the target. Obtain a committed dispatch date and a Berlin delivery estimate for the selected service; a target of **23 September, or 24 September at the latest**, is a planning gate, not a published carrier cutoff or proof that arrival will succeed.

| Date / gate | Action and required evidence |
|---|---|
| **22 September** | Upload the files to Eurocircuits, resolve drill/stackup checks, and inspect its fastest complete-board-plus-stencil option with delivery to Berlin on 29 September, or 30 September as fallback. Compare green mask if it improves the date. Import both parts files and verify every match, immediate stock, total cost and delivery estimate. |
| **23–24 September** | Aim for LCSC carrier handover before the period named in the holiday notice. Obtain tracking showing actual carrier acceptance, not just label creation. Ask explicitly about holiday warehouse operation and carrier collection. A later dispatch requires a fresh delivery commitment. |
| **29 September preferred; 30 September fallback** | All five PCBs, stencil and both component shipments in hand in Berlin. No backorders or partial kit counted as meeting the target. |
| **After receipt** | Allow 1–2 lab days for assembly and initial checks, with rework time. Reserve lab access provisionally; this materials target does not mean five tested devices on the same day. |

If either Eurocircuits or LCSC cannot support the target, this split does **not** meet the requested schedule. No fully sourced European-only replacement within two component vendors has been established; U1, U2 and the exact Y1 variant prevent casually moving the entire BOM to Mouser. Keep the existing JLCPCB order as a parallel route. A firm arrival claim requires checkout to the actual Berlin address and Eurocircuits' CAM acceptance; neither is available here. The unsent [LCSC inquiry](lcsc-dispatch-inquiry.txt) and [Mouser inquiry](mouser-delivery-inquiry.txt) make those checks explicit.

## Costs and quantities

The LCSC catalogue calculation for the selected **45 lines is US$125.53**, including spare quantities and retail ordering multiples. This excludes shipping, tax and import/carrier charges. The CSV preserves the observed unit prices and source for each row; some pages are older caches and checkout prices can differ.

For Mouser, observed prices cover seven of ten lines: **€14.34 + US$20.575**, in mixed regional catalogue currencies. Three lines still need German prices. These amounts are partial subtotals, **not** one basket total. Use a provisional **€60–100 parts allowance** for the ten Mouser lines until the German basket provides the actual amount; this allowance is our estimate, not a supplier quote.

**Eurocircuits fabrication, stencil, express production and shipping: live configuration price required.** No defensible all-in total exists yet. The working cost expression is **Eurocircuits checkout total + US$125.53 LCSC parts + €60–100 provisional Mouser parts + component shipping, taxes/fees and any missing lab consumables**. Count VAT/shipping only once when a checkout total already includes them. This is not a fixed offer or a landed-total estimate. Select the earliest viable service with its itemized price; there is no user-specified budget cap. Mouser advertises free shipping on most German orders above €75, but do not assume that includes the fastest needed service. Use its basket quote. [Mouser Germany](https://www.mouser.de/en/cs/localsites/).

`purchasing-5-boards.csv` is the master list: 580 fitted parts plus spares and order multiples, **2,056 purchased pieces** in total. High quantities on cheap resistors/LEDs reflect 100-piece retail packs, not 100 boards. Large ICs/modules/connectors generally have at least one spare, RF capacitors have 20 pieces per value, and L2/L3 have 15 pieces for 10 placements. Five bare boards leave no PCB spare; five working assemblies are a target, not a guaranteed yield.

## Parts that drive the vendor split

| References | Buy / quantity | Vendor | Catalogue observation |
|---|---|---|---|
| U1 | TP4054-42-SOT25R × 10 | LCSC C32574 | 27,505 listed; exact charger |
| U2 | SY8089AAAC × 10 | LCSC C78988 | 53,005 listed; exact regulator |
| Y1 | NX2016SA-27.12MHZ-EXS00A-CS06346 × 10 | LCSC C3008209 | 8,135 listed; retain 10 pF load variant |
| U3 | ESP32-C3-WROOM-02-N4 × 6 | LCSC C2934560 | 3,857 listed |
| U6 | PN7160A1HN/C100E × 6 | LCSC C3303788 | 3,219 listed; exact HVQFN part |
| DS1 | FH12A-24S-0.5SH(55) × 6 | Mouser 798-FH12A-24S0.5SH55 | 3,237 listed; **top-contact** socket |
| L2/L3 | 0805HP-151XGRC × 15 | Mouser 994-0805HP-151XGRC | 1,620 listed; retain Coilcraft 2% part |
| R27/R28 | CRCW12062R70FKEAHP × 20 | Mouser, match exact MPN | 2,409 listed; retain HP suffix |
| R30 | CPF0805B1M8E × 10 | Mouser 279-CPF0805B1M8E | 9,161 listed; retain 0.1% tolerance |

Every row's product URL, observed stock and cache age are in [purchasing-5-boards.csv](purchasing-5-boards.csv). The JSON files preserve the numerical catalogue observations, not full copied webpages. **These are observed listings, not live reserved quantities.** In particular, recheck L4 (five-month-old cache), R7 (two-month-old cache), and all Mouser lines. Different cached LCSC views disagree on C26; the planned source is Mouser.

The previous JLCPCB purchasing file reports **assembly** stock and machine placement loss allowances; neither proves availability nor supplies the right ordering multiples for retail self-assembly. LCSC public views showed several retail gaps, including DS1, the original 100 nF capacitor and the original 100 pF RF capacitor. That is why simply halving the old ten-board sheet is insufficient.

## Three proposed capacitor substitutions

These are explicitly identified in the master CSV and included in the Mouser import. They have been screened against the BOM value, package, voltage, dielectric and tolerance using manufacturer/distributor specifications. They are **not physically qualified replacements**, and do not alter the submitted PCB. Review them before purchase; keep the original BOM as the design record and record the actual fitted MPNs during assembly.

| References | Original | Proposed order part | Screening / limits |
|---|---|---|---|
| C10, C11, C13, C14, C16, C18, C20, C25, C43, C45, C48, C51 | Samsung CL10B104KB8NNNC | YAGEO **CC0603KRX7R9BB104** | Same 100 nF, 50 V, X7R, 10%, 0603. DC-bias behavior is not identical by definition; verify at actual rails. Power bulk capacitors remain exact MPNs. |
| C32/C33 | YAGEO CC0805FRNPO0BN680 | Vishay **VJ0805A680FXBPW1BC** | Same 68 pF, 100 V, C0G, 1%, 0805; 2.0 × 1.25 × 0.6 mm. Keep both halves identical. |
| C36/C37 | YAGEO CC0805GRNPO0BN101 | KEMET **C0805C101F1GACTU** | Same 100 pF, 100 V, C0G, 0805; tighter 1% rather than 2%; 2.0 × 1.25 × 0.78 mm. Keep both halves identical. |

Sources: [YAGEO 100 nF](https://www.mouser.fr/fr/ProductDetail/YAGEO/CC0603KRX7R9BB104?qs=sGAEpiMZZMt7gvpyg0xT8lc%252Bzo1hxTFgFLBhN1j2Qug%3D), [Vishay 68 pF](https://www.mouser.com/ProductDetail/Vishay-Vitramon/VJ0805A680FXBPW1BC?qs=LOE%2FbrHKynVKp8h9bQehOA%3D%3D), [KEMET 100 pF](https://www.mouser.cn/ProductDetail/KEMET/C0805C101F1GACTU?qs=PvkUd2vn8WpeBlgrApNklg%3D%3D).

RF loss/parasitics and power dissipation are not established by matching capacitance alone. The NFC network already needs prototype tuning; remeasure it on the alternate stackup and with these RF substitutions. Do not downgrade the RF capacitors to 50 V or X7R, change the crystal load specification, substitute a generic 150 nH inductor, or replace the high-power resistors with ordinary 1206 parts.

## PCB and stencil instructions that matter

Upload the **r2 Gerber ZIP included here**, plus `pcb-fabrication-notes.txt`, the via-fill identification layer and the outline drawing. This is the submitted geometry, not a re-export of a potentially edited working board. File hashes in `files.sha256` tie the copied inputs to r2. The extra via-fill layer is an instruction/identification layer, not an additional copper layer.

- Five complete boards, four layers, FR-4, 60 × 110 mm, nominal 1.6 mm, ENIG, 35 µm outer copper and approximately 15–18 µm inner copper. Quote black mask / white legend; green is an optional schedule alternative only.
- **335 plated round holes per board must be epoxy-filled, planarized and copper-capped**: 32 × 0.20 mm, 301 × 0.30 mm, 2 × 0.40 mm. Preserve mask openings. Tenting alone is insufficient for the existing via-in-pad geometry. Leave four 0.60 mm plated USB slots, nineteen 1.00 mm header holes and every NPTH open.
- JLC04161H-3313 is a supplier-specific construction, not a universally selectable stackup. Use Eurocircuits' stackup tools/CAM review to establish **90 Ω differential ±10%** on the existing B.Cu USB pair (0.15 mm width, 0.21 mm edge gap, In2.Cu ground reference). The original outer dielectric is about 0.0994 mm, Dk about 4.1. Do not silently accept a generic four-layer stack or automatic trace edits. Any construction deviation needs engineering review, including its effect on the NFC antenna.
- Keep the lower keyboard attached. Preserve the two internal cutouts, 28 mouse-bite holes and central electrical bridge. No added route, V-score or factory separation through the keyboard. Preserve the ESP32 antenna overhang and NFC copper exclusions.
- Request **one 0.10 mm top-side laser-cut stainless stencil** from the included `nucula-v2-F_Paste.gtp`. Confirm its outer dimensions/frame against the lab's printer or manual jig. Preserve the PN7160 exposed-pad nine-window pattern and all DNP paste omissions. No bottom stencil is needed.
- The JLC assembly carrier dimensions were for its factory process. Ask for individual boards suited to the lab fixture; any new rails/carrier need a matching stencil and must leave the functional keyboard attached.

The r2 readback reports zero placement-count discrepancies, four copper layers, the expected drilling, 24 DS1 signal paste regions and nine U6 exposed-pad windows. Those existing checks establish the export content, not acceptance by a new fabricator. The USB connector's minimum NPTH-to-pad clearance is about 0.233 mm; include that in CAM review.

## Lab preparation and assembly

This is practical hand placement followed by reflow if the lab has the right equipment. All fitted parts are on top. The difficult areas are the PN7160 HVQFN exposed pad, the ESP32 module ground pad, the small crystal and the USB/FPC connectors. Arrange a microscope, fine tweezers/vacuum pickup, stable stencil support, a reflow oven or suitable controlled reflow setup, thermocouples, a soldering iron, flux, braid and hot-air rework. Use the lab's approved paste, ESD setup and fume extraction. Confirm those resources and access hours before ordering.

Use paste with a profile compatible with the components and verify actual board temperatures, particularly under the module and at the connectors. Follow the supplied moisture-sensitive packaging and component handling/reflow limits. A nominal oven setting or a hot-air gun alone does not establish a usable profile. Check whether connector stakes need local touch-up after reflow.

1. Sort labelled cut tapes by reference; count and verify all parts before applying paste. Use the assembly drawing and the reference-specific purchasing sheet.
2. Assemble **one board first**, inspect paste and orientation under magnification, then reflow with the verified profile. Keep the keyboard supported and attached.
3. Inspect for bridges, opens, tombstones and connector alignment. Hidden exposed-pad joints cannot be fully verified visually; allow rework time. Check supply-to-ground resistance before power.
4. Start with current-limited USB-derived 5 V and **no battery or OLED attached**. Verify rails, then ESP32 boot/programming, reset and peripheral I²C. Check the OLED supply before connecting glass. Connect the optional battery only after the charger/polarity checks.
5. After that first board passes, populate the remaining four. Budget a second session for faults, RF tuning and display fit. Shipping all parts does not resolve the existing prototype validation work.

Keep **C7, C8, C34, C35, C38, C39, J3, J4, J5, R38, R39** unpopulated under the release BOM. A1 is etched copper; MB1/MB2 are mechanical features, not purchased parts. OLED glass, external keypad and battery are excluded from the released assembly BOM and from these two carts. This plan assumes you already have them; five complete devices require five suitable displays/keypads, plus any user-fitted keyboard headers/wiring. Confirm those counts separately. USB-only board testing does not require batteries. Paste, flux and other consumables are assumed available at the lab; if missing, add them to the same two vendor orders where suitable.

## Files

- `purchasing-5-boards.csv`: all references, five-board needs, spares, vendor, selected MPN, observed stock, prices, source age, substitution notes.
- `lcsc-import.csv` / `mouser-import.csv`: proposed basket imports; manually inspect importer matches, especially blank supplier-SKU fields and substitutions.
- `pcb-online-ordering.md`: Eurocircuits link, private-customer evidence, settings and outstanding DFM checks.
- `pcb-fabrication-notes.txt` / `nucula-v2-Via_Filling.gbr`: supplier-neutral requirements and identification of the 335 holes to fill.
- `pcb-rfq-de.txt`: superseded, unsent CONTAG request; not the selected ordering route.
- `lcsc-dispatch-inquiry.txt` / `mouser-delivery-inquiry.txt`: unsent requests for stock, dispatch, delivered cost and date confirmation.
- `nucula-v2-gerbers.zip`, `nucula-v2-F_Paste.gtp`, `fabrication-outline.pdf`, `assembly-top.pdf`: byte-identical copies from r2.
- `files.sha256`: checksums for copied fabrication/assembly inputs.
- `*-catalogue-observations.json`: numerical research record; never a substitute for checkout stock and delivery confirmation.
- `validation.json`: results of local coverage, quantity, price-tier, import and fabrication-input checks.

The complete folder is also available as [contingency-2026-09-22-package.zip](../contingency-2026-09-22-package.zip). Send each supplier only its relevant inquiry and attachments; the full archive is the internal procurement/assembly record.

Local quantities and coverage were checked against the r2 BOM/CPL. The final commercial checks are exact CAM acceptance, all stock available in the two baskets, and three delivery dates that meet the user's deadline.
