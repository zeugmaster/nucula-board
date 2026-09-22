# Online PCB order: private customer

**Current candidate: [Eurocircuits configurator](https://be.eurocircuits.com/shop/assembly/configurator.aspx).** Its site provides upload, price calculation, DFM and online ordering. Its [account/VAT guidance](https://www.eurocircuits.com/user-guides/customer-account-user-guide/finance-and-administration/value-added-tax-vat/) explicitly addresses private customers. An ordinary private account is intended; a student account is not required or assumed.

CONTAG is excluded from this route because the user requires online ordering. Multi-CB has an online calculator but [sells only to businesses and public institutions](https://www.multi-circuit-boards.eu/leiterplatten-express.html).

## Configuration to check

| Setting | Requested value |
|---|---|
| Product | Bare PCBs, no assembly; **STANDARD pool** starting point |
| Quantity / dimensions | 5 complete single boards; 60 × 110 mm |
| Layers / material | 4 copper layers; FR-4; nominal 1.6 mm |
| Copper | Finished outer 35 µm; inner approximately 15–18 µm; distinguish base foil from finished copper |
| Stackup | Match or validate against the released construction; see fabrication notes |
| Surface | ENIG explicitly |
| Mask / legend | Black / white; compare green if it shortens production, with colour change recorded |
| Via filling | **Resin**, producing filled and copper-capped vias; 335 holes identified in the extra layer |
| Open holes | USB plated slots, 1.00 mm header holes and all NPTH |
| Stencil | One delivered top stencil, 100 µm; existing paste apertures, no additional automatic reduction |
| Delivery | Fastest complete PCB + stencil option arriving Berlin 29 September, or 30 September fallback |

Do not use the advertised PCB Proto price/lead time: its [minimum PTH is 0.25 mm](https://www.eurocircuits.com/services/pcb-proto/), while this release contains 0.20 mm holes. STANDARD pool [lists a general five-working-day bare-board lead time, with shorter options in the calculator](https://www.eurocircuits.com/services/standard-pool/); this is not a commitment for this configuration.

## Two engineering checks before payment

1. **Small via pads.** Some released vias are 0.20 mm holes in 0.45 mm pads. Eurocircuits calculates annular ring against the manufacturing tool, not simply the finished hole. Its published classification adds 0.10 mm to PTH finished diameter for the tool: a 0.30 mm tool leaves only (0.45 − 0.30) / 2 = 0.075 mm ring. This is below its listed outer/inner minima. Its [drilled-hole rules](https://www.eurocircuits.com/technical-guidelines/pcb-design-guidelines/drilled-holes/) allow reducing holes classified as vias; a 0.10 mm finished via with a 0.20 mm tool would leave 0.125 mm. **That is a possible CAM remedy, not an approved modification or a demonstrated DFM pass.** Review drill classification, all resulting dimensions and the original filled thermal holes; preserve connector holes. [Classification reference](https://www.eurocircuits.com/wp-content/uploads/EC-classification-ENGLISH-10-2019-V1.pdf).
2. **USB stackup.** Validate 90 Ω differential ±10% for the existing bottom-layer pair, 0.15 mm width / 0.21 mm edge gap, against In2.Cu ground. The release uses approximately 0.0994 mm outer dielectric and nominal Dk 4.1. A default four-layer stack is not established as equivalent. Do not accept automatic copper changes; review a proposed construction before production. The NFC antenna also needs validation on the alternate construction.

## Upload and price status

Upload `nucula-v2-gerbers.zip`; add `pcb-fabrication-notes.txt`, `fabrication-outline.pdf` and `nucula-v2-Via_Filling.gbr` as manufacturing instructions. Assign Via_Filling as a via-fill identification layer, not copper, soldermask or paste. The supplier [prefers a separate identification file for specific holes](https://www.eurocircuits.com/technical-guidelines/pcb-design-guidelines/via-filling/). This also makes the released component-drill thermal holes explicit. Use `nucula-v2-F_Paste.gtp` for the top stencil and check the frame/outer size against the lab fixture.

The source Gerbers and drill data are unchanged. The added Gerber contains circular markers at exactly the 335 selected drill coordinates, using their released diameters; it does not replace either drill file.

The research browser reached the configurator but could not operate its JavaScript upload/calculation flow. **No live PCB price, completed cart, submitted DFM analysis or arrival commitment has been obtained.** Record the full five-board price, stencil, express surcharge, shipping and VAT from the private-customer checkout. An online order form alone does not establish that this design passes or meets the date. If the checks fail or the complete delivered date is too late, this candidate cannot be treated as the contingency supplier.
