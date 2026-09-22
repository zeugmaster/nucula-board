# JLCPCB placement reference correction — r2

The first CPL applied three unverified shifts from footprint origins to the
centers of their F.Fab body outlines. Those shifts were introduced in the
exporter, not in the PCB. The user reports correct KiCad 3D placement but an
ESP32 displaced right and a display connector displaced upward in both JLCPCB
2D and 3D. The generated shifts have exactly those directions.

| Part | Shift added by the original exporter | Native KiCad X, Y (mm) |
|---|---|---|
| U3, ESP32 | +3.10 mm X (right) | 47.900, 53.860 |
| DS1, display socket | +1.90 mm Y (up) | 30.000, 51.150 |
| J2, JST battery socket | −1.75 mm X (left) | 6.750, 59.100 |

The other 113 rows were not translated. All rotations, parts and board geometry
are unchanged. The offsets were applied consistently by the exporter, so the
old checks that matched BOM references and board geometry could not catch this
supplier-reference mismatch. Native DRC does not check CPL positions.

KiCad places its 3D model relative to each footprint origin. The CPL contains
only positions and angles; JLCPCB applies those to its own catalogue models.
Moving a coordinate to a body-outline center without verifying that model's
placement anchor can introduce an extra shift. Small symmetric components
usually have coincident origins and body centers; they also had no added shift
in this exporter.

Revision **jlcpcb-2026-09-21-r2** removes all three unverified body-center offsets
and uses native KiCad footprint positions, following the
[JLCPCB native-export workflow](https://jlcpcb.com/help/article/how-to-generate-the-bom-and-centroid-file-from-kicad).
This is the correction to review; it is not a claim that every JLCPCB model has
a standard origin. Catalogue-specific XY/angle corrections need direct evidence
from pin alignment. The public EasyEDA catalogue request was unavailable (HTTP
403), so no exact catalogue-origin measurement is claimed.

Upload the [r2 CPL](../../manufacturing/jlcpcb-2026-09-21-r2/assembly/jlcpcb-cpl.csv)
and inspect JLCPCB's **2D lead-to-pad alignment** for U3, DS1 and J2. The first two
were reported displaced; J2 is an additional check because its unverified shift
came from the same rule. Check pin 1, ESP32 antenna direction and connector entry
as well as translation. JLCPCB preview confirmation is still pending.

The revised independent audit compares all 116 CPL entries, coordinates,
normalized rotations and board sides with the native KiCad position export,
and checks the BOM reference set. The superseded package is excluded from the
public repository; **do not reuse its CPL**. Use the r2 package linked from the root
README. The BOM and fabrication geometry do not need changing for this fix.
