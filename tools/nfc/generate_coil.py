#!/usr/bin/env python3
"""Generate the PCB coil as connected KiCad custom pads, not copper artwork.

Python standard library only. Native KiCad validation: check_coil.py.
The copper is intentionally DC-continuous between different schematic nets:
the footprint declares the two terminals as a net tie. Never route a shortcut.
"""
from pathlib import Path
import json
import math
import uuid

ROOT = Path(__file__).resolve().parents[2]
NAME = 'NFC_PCB_Loop_40x40_4T_W0.50_S0.30'
WIDTH = .5
GAP = .3
PITCH = WIDTH + GAP
OUTER = 40.
TURNS = 4
THICKNESS = 1.6
FEED1 = (-1.5, -22.)
FEED2 = (1.5, -22.)


def geometry():
    """Centerlines in mm. Four clockwise circuits; stepped open top seam."""
    front = [FEED1, (-1.5, -19.75)]
    for i in range(TURNS):
        r = OUTER / 2 - WIDTH / 2 - i * PITCH
        seam = -2.5 - i * PITCH
        front += [(r, -r), (r, r), (-r, r), (-r, -r), (seam, -r)]
        front += [(seam, -r + PITCH)]
    inner = front[-1]
    back = [inner, (inner[0], FEED2[1]), FEED2]
    # Current path: front, down plated hole, back, up plated feed hole.
    path3d = [(x, y, 0.) for x, y in front]
    path3d += [(x, y, -THICKNESS) for x, y in back]
    path3d += [(*FEED2, 0.)]
    return front, back, path3d


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'nucula:nfc:' + name))


def lines(points, anchor):
    out = []
    for a, b in zip(points, points[1:]):
        a = [a[i] - anchor[i] for i in range(2)]
        b = [b[i] - anchor[i] for i in range(2)]
        out.append(f'    (gr_line (start {a[0]:.6f} {a[1]:.6f}) (end {b[0]:.6f} {b[1]:.6f}) (width {WIDTH}))')
    return '\n'.join(out)


def generate():
    front, back, path3d = geometry()
    inner = front[-1]
    # No mask/paste on spiral or underpass. Only terminal landings are exposed.
    # Hole 2 inside is tented by omitting mask layers; copper exists on *.Cu.
    text = f'''(footprint "{NAME}"
  (version 20241229) (generator "nucula_nfc_generator")
  (layer "F.Cu")
  (descr "40x40 mm OUTER COPPER; 4 turns; W0.50/S0.30; 35um Cu; 1.6mm FR4 starting model. F.Cu loop/B.Cu return. Net tie is the inductor; never add a short. See docs/nfc-antenna.md")
  (tags "NFC PCB antenna loop 13.56MHz 40mm four turns")
  (attr exclude_from_pos_files exclude_from_bom)
  (net_tie_pad_groups "1,2")
  (property "Reference" "A**" (at 0 22.3) (layer "F.SilkS") (effects (font (size 1 1) (thickness .15))))
  (property "Value" "{NAME}" (at 0 24) (layer "F.Fab") (effects (font (size .8 .8) (thickness .12))))
  (fp_text user "NO METAL / NO PLANES" (at 0 0) (layer "F.Fab") (effects (font (size 1.3 1.3) (thickness .2))))
  (fp_text user "1" (at -1.5 -24) (layer "F.SilkS") (effects (font (size .8 .8) (thickness .12))))
  (fp_text user "2" (at 1.5 -24) (layer "F.SilkS") (effects (font (size .8 .8) (thickness .12))))
  (fp_rect (start -20 -20) (end 20 20) (stroke (width .1) (type default)) (fill none) (layer "F.Fab"))
  (fp_rect (start -21 -23.5) (end 21 21) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))
  (fp_rect (start -21 -23.5) (end 21 21) (stroke (width .05) (type default)) (fill none) (layer "B.CrtYd"))
  (pad "1" smd custom (at {FEED1[0]} {FEED1[1]}) (size .5 .5) (layers "F.Cu")
    (zone_connect 0) (options (clearance outline) (anchor circle))
    (primitives
{lines(front[:-1], FEED1)}
    ))
  (pad "1" smd rect (at {FEED1[0]} {FEED1[1]}) (size 1.5 2) (layers "F.Cu" "F.Mask"))
  (pad "2" smd custom (at {inner[0]:.6f} {inner[1]:.6f}) (size .5 .5) (layers "F.Cu")
    (zone_connect 0) (options (clearance outline) (anchor circle))
    (primitives
{lines(front[-2:], inner)}
    ))
  (pad "2" thru_hole circle (at {inner[0]:.6f} {inner[1]:.6f}) (size .8 .8) (drill .4) (layers "*.Cu") (zone_connect 0))
  (pad "2" smd custom (at {FEED2[0]} {FEED2[1]}) (size .5 .5) (layers "B.Cu")
    (zone_connect 0) (options (clearance outline) (anchor circle))
    (primitives
{lines(back, FEED2)}
    ))
  (pad "2" thru_hole circle (at {FEED2[0]} {FEED2[1]}) (size 1.5 1.5) (drill .4) (layers "*.Cu" "*.Mask") (zone_connect 0))
  (zone (net 0) (net_name "") (layers "*.Cu") (uuid "{uid('keepout')}") (hatch edge .5)
    (connect_pads (clearance 0)) (min_thickness .25)
    (keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints not_allowed))
    (fill (thermal_gap .3) (thermal_bridge_width .3))
    (polygon (pts (xy -21 -21) (xy 21 -21) (xy 21 21) (xy -21 21))))
)
'''
    path = ROOT / 'libraries/Nucula_Project.pretty' / (NAME + '.kicad_mod')
    path.write_text(text)
    length = sum(math.dist(a, b) for a, b in zip(path3d, path3d[1:]))
    data = {'footprint': NAME, 'turns': TURNS, 'outer_copper_mm': [OUTER, OUTER],
            'track_mm': WIDTH, 'gap_mm': GAP, 'copper_um': 35,
            'stackup_assumed_mm': THICKNESS, 'front_centerline_mm': front,
            'back_centerline_mm': back, 'current_path_3d_mm': path3d,
            'total_centerline_including_barrels_mm': length,
            'feed1_mm': FEED1, 'feed2_mm': FEED2, 'inner_hole_mm': inner,
            'hole_mm': .4, 'inner_pad_mm': .8,
            'keepout_mm': [-21, -21, 21, 21], 'keepout_layers': '*.Cu'}
    out = ROOT / 'docs/nfc'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'geometry.json').write_text(json.dumps(data, indent=2) + '\n')
    print(f'{path.relative_to(ROOT)}: copper path {length:.3f} mm')


if __name__ == '__main__':
    generate()
