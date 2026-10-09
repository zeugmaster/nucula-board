# Manufacturing releases

**Current release: [production-2026-10-08-package.zip](production-2026-10-08-package.zip).**

Includes the latest battery notch and placement, artwork, six M2 holes, MINI-1,
display/USB corrections, and restored rev-A NFC geometry and manufacturing process.
Use the [production instructions](production-2026-10-08/README.md): **black mask,
JLC04161H-3313, filled/capped vias**. The earlier generic-stackup/open-via settings
are superseded. All 119 CPL anchors and all 413 assembly pad coordinates are
independently checked. Physical USB/display qualification and supplier preview
acceptance remain distinct from the completed file checks.

Earlier October packages, including `mounting-2026-10-08`, are historical and
must not be used for this order. They predate the latest geometry or NFC restoration.

The historical **[routing-review-2026-09-22-package.zip](routing-review-2026-09-22-package.zip)**
contains ordinary unfilled-via Gerbers,
the ribbon-clearance layout with repaired routing, updated stencil and assembly
drawings, and the validation records. [Settings and changes](../docs/manufacturing-release.md).

The battery-pad package supersedes the SH `low-profile-2026-10-07`, PH
`side-entry-2026-10-07` and September inputs for new prototypes. Those archives are unchanged.
The original contingency's PCB files and the first `standard-2026-09-22` package
were superseded by the routing-review revision. Its historical sourcing proposal
predates the current J2 and USB selections. Delivery and private-customer checkout still need
confirmation in the supplier's cart.

## Archived JLCPCB order

[jlcpcb-2026-09-21-r2-package.zip](jlcpcb-2026-09-21-r2-package.zip) records the
board already submitted to JLCPCB and remains unchanged.
Its [CPL](jlcpcb-2026-09-21-r2/assembly/jlcpcb-cpl.csv) removes the unverified
U3, DS1 and J2 body-center offsets. JLCPCB 2D pin alignment remains to be
confirmed in the order preview. [Correction details](../docs/assembly/cpl-alignment.md).

The superseded `jlcpcb-2026-09-21` package is excluded from this repository.
Its CPL displaced U3 and DS1 in the JLCPCB preview. The correction and original
coordinates remain documented in the placement review linked above.

The PCB, Gerber geometry and BOM are unchanged in r2.

[Five-board Berlin contingency](contingency-2026-09-22/README.md) contains the
proposed Eurocircuits online PCB/stencil configuration and LCSC/Mouser purchasing
lists for manual assembly, targeting materials on 29–30 September. Private-customer
checkout is required. PCB DFM acceptance and delivery dates are unconfirmed;
this is not a new design release or a placed order.

The archived r2 public package was previously repacked to remove editor locks, local paths and
the restricted PN7160 visualization model. Fabrication, BOM and placement files
retain their original bytes. The manifest and ZIP checksums describe the public
package; see [publication notes](../docs/publication.md).
