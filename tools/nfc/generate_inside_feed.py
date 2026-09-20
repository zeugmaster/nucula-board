#!/usr/bin/env python3
"""Inside-feed variant; leave the original bare-coil coupon reproducible."""
import json
import math
from generate_coil import ROOT, NAME as BARE_NAME, geometry as bare_geometry, lines, uid, THICKNESS

NAME = BARE_NAME + '_InsideFeed'
FEED1 = (-1.5, -14.5)
FEED2 = (-4.9, -14.5)
OUTER_HOLE = (-1.5, -20.6)
# Courtyard hole includes a notch reserving the feed lands and their underpass.
WINDOW = [(-16.1, -16.1), (-6.15, -16.1), (-6.15, -13.25),
          (-.25, -13.25), (-.25, -16.1), (16.1, -16.1),
          (16.1, 16.1), (-16.1, 16.1)]
RING = [(-21, -21.5, 21, -16.1), (-21, -16.1, -16.1, 16.1),
        (16.1, -16.1, 21, 16.1), (-21, 16.1, -3, 21), (3, 16.1, 21, 21)]
CORRIDOR = (-3, 16.1, 3, 21)


def geometry():
    old_front, _, _ = bare_geometry()
    front = [OUTER_HOLE] + old_front[1:] + [FEED2]
    back = [FEED1, OUTER_HOLE]
    path = [(*FEED1, 0), (*FEED1, -THICKNESS), (*OUTER_HOLE, -THICKNESS)]
    path += [(x, y, 0) for x, y in front]
    return front, back, path


def area(name, rect, layers='"*.Cu"', tracks='not_allowed'):
    x1, y1, x2, y2 = rect
    return f'''  (zone (net 0) (net_name "") (layers {layers}) (uuid "{uid(NAME + name)}")
    (name "{name}") (hatch edge .5) (connect_pads (clearance 0)) (min_thickness .25)
    (keepout (tracks {tracks}) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints not_allowed))
    (fill (thermal_gap .3) (thermal_bridge_width .3))
    (polygon (pts (xy {x1} {y1}) (xy {x2} {y1}) (xy {x2} {y2}) (xy {x1} {y2}))))'''


def custom(number, layer, points, anchor):
    return f'''  (pad "{number}" smd custom (at {anchor[0]} {anchor[1]}) (size .5 .5) (layers "{layer}")
    (zone_connect 0) (options (clearance outline) (anchor circle))
    (primitives
{lines(points, anchor)}
    ))'''


def generate():
    front, back, path = geometry()
    out = [f'''(footprint "{NAME}"
  (version 20241229) (generator "nucula_nfc_generator") (layer "F.Cu")
  (descr "40x40 mm four-turn NFC winding W0.50/S0.30; inside feeds; open center for NFC electronics. Perimeter keepout, B.Cu-only host entry at local +Y. Tune with final circuitry/stackup. See docs/nfc-antenna.md")
  (tags "NFC PCB antenna 13.56MHz inside feed")
  (attr exclude_from_pos_files exclude_from_bom)
  (net_tie_pad_groups "1,2")
  (property "Reference" "A**" (at 0 22.3) (layer "F.SilkS") (effects (font (size 1 1) (thickness .15))))
  (property "Value" "{NAME}" (at 0 24) (layer "F.Fab") (effects (font (size .8 .8) (thickness .12))))
  (fp_text user "NFC CIRCUIT AREA / LOCAL GND ONLY" (at 0 0) (layer "F.Fab") (effects (font (size .7 .7) (thickness .12))))
  (fp_text user "B.Cu HOST ENTRY" (at 0 22) (layer "F.Fab") (effects (font (size .7 .7) (thickness .12))))
  (fp_text user "1" (at -1.5 -12.6) (layer "F.SilkS") (effects (font (size .8 .8) (thickness .12))))
  (fp_text user "2" (at -4.9 -12.6) (layer "F.SilkS") (effects (font (size .8 .8) (thickness .12))))
  (fp_rect (start -20 -20) (end 20 20) (stroke (width .1) (type default)) (fill none) (layer "F.Fab"))''']
    for layer in ['F.CrtYd', 'B.CrtYd']:
        out.append(f'  (fp_rect (start -21 -21.5) (end 21 21) (stroke (width .05) (type default)) (fill none) (layer "{layer}"))')
        for a, b in zip(WINDOW, WINDOW[1:] + WINDOW[:1]):
            out.append(f'  (fp_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (stroke (width .05) (type default)) (layer "{layer}"))')
    # The net tie is the winding itself. Only the final inside lead is pad 2.
    out += [custom(1, 'F.Cu', front[:-2], OUTER_HOLE),
            custom(2, 'F.Cu', front[-3:], FEED2), custom(1, 'B.Cu', back, FEED1)]
    for x, y in [OUTER_HOLE, FEED1]:
        out.append(f'  (pad "1" thru_hole circle (at {x} {y}) (size .8 .8) (drill .4) (layers "*.Cu") (zone_connect 0))')
    for n, (x, y) in enumerate([FEED1, FEED2], 1):
        out.append(f'  (pad "{n}" smd rect (at {x} {y}) (size 1.5 2) (layers "F.Cu" "F.Mask") (zone_connect 0))')
    out += [area(f'winding-{i}', rect) for i, rect in enumerate(RING)]
    blocked_layers = ' '.join(f'"{layer}"' for layer in ['F.Cu'] + [f'In{i}.Cu' for i in range(1, 31)])
    out += [area('host-entry-no-front-or-inner-tracks', CORRIDOR, blocked_layers),
            area('host-entry-bottom-tracks-only', CORRIDOR, '"B.Cu"', 'allowed'), ')\n']
    footprint = ROOT / 'libraries/Nucula_Project.pretty' / (NAME + '.kicad_mod')
    footprint.write_text('\n'.join(out))
    data = dict(footprint=NAME, outer_winding_copper_mm=[40, 40], turns=4,
                trace_width_mm=.5, gap_mm=.3, feed1_mm=FEED1, feed2_mm=FEED2,
                plated_holes_mm=[OUTER_HOLE, FEED1], drill_mm=.4,
                front_centerline_mm=front, back_centerline_mm=back, current_path_3d_mm=path,
                total_centerline_including_barrels_mm=sum(math.dist(a, b) for a, b in zip(path, path[1:])),
                barrel_length_assumed_mm=THICKNESS, nominal_component_window_mm=[32.2, 32.2],
                courtyard_window_polygon_mm=WINDOW, winding_keepout_rectangles_mm=RING,
                host_entry_rectangle_mm=CORRIDOR, host_entry_track_layers=['B.Cu'],
                rf_status='Unmeasured; bare-coupon matching values are starting values only. Measure with final in-loop circuitry and ground.')
    directory = ROOT / 'docs/nfc/inside-feed'
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'geometry.json').write_text(json.dumps(data, indent=2) + '\n')
    print(footprint.relative_to(ROOT))


if __name__ == '__main__':
    generate()
