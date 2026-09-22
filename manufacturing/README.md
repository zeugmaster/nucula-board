# Manufacturing releases

Use **[jlcpcb-2026-09-21-r2-package.zip](jlcpcb-2026-09-21-r2-package.zip)**.
Its [CPL](jlcpcb-2026-09-21-r2/assembly/jlcpcb-cpl.csv) removes the unverified
U3, DS1 and J2 body-center offsets. JLCPCB 2D pin alignment remains to be
confirmed in the order preview. [Correction details](../docs/assembly/cpl-alignment.md).

The superseded `jlcpcb-2026-09-21` package is excluded from this repository.
Its CPL displaced U3 and DS1 in the JLCPCB preview. The correction and original
coordinates remain documented in the placement review linked above.

The PCB, Gerber geometry and BOM are unchanged in r2.

The public package has been repacked to remove editor locks, local paths and
the restricted PN7160 visualization model. Fabrication, BOM and placement files
retain their original bytes. The manifest and ZIP checksums describe the public
package; see [publication notes](../docs/publication.md).
