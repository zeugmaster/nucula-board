#!/usr/bin/env python3
"""Read current standard-fabrication Gerbers/drills with the existing Gerbonara stack.

Unlike inspect_jlcpcb.py's historical r2 checks, this accepts the ordinary
0.30/0.70 mm routing vias and checks the corrected mounted display mapping.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import warnings

from gerbonara import LayerStack, ExcellonFile
from gerbonara.graphic_objects import Flash, Line, Arc
from gerbonara.utils import MM

from check_display_mapping import PANEL_NETS, ROOT, short_net


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('export', type=Path)
    ap.add_argument('--out', type=Path, default=ROOT / 'docs/bringup/gerber-readback.json')
    args = ap.parse_args()
    out = args.export
    manifest = json.loads((out / 'manifest.json').read_text())
    assert manifest['source_board_sha256'] == sha(ROOT / 'nucula-v2.kicad_pcb')
    for name, digest in manifest['files_sha256'].items():
        assert sha(out / name) == digest, name
    geometry = json.loads((ROOT / 'docs/pcb/routing-geometry.json').read_text())
    assert geometry['source_board_sha256'] == manifest['source_board_sha256']
    with warnings.catch_warnings(record=True) as caught:
        stack = LayerStack.open(out / 'gerbers')
        pth = ExcellonFile.open(out / 'gerbers/nucula-v2-PTH.drl')
        npth = ExcellonFile.open(out / 'gerbers/nucula-v2-NPTH.drl')
    warning_text = sorted(set(str(w.message).split(':')[-1].strip() for w in caught))
    assert all('G90 header statement found after end of header' in w for w in warning_text)
    checks = {}
    copper = {side for (side, use) in stack.graphic_layers if use == 'copper'}
    checks['four_copper_layers'] = copper == {'top', 'bottom', 'inner_1', 'inner_2'}

    pads = [o for o in stack.graphic_layers['top', 'copper'].objects
            if isinstance(o, Flash) and o.attrs.get('.P', ('',))[0] == 'DS1'
            and o.attrs['.P'][1].isdigit()]
    pads.sort(key=lambda o: o.x)
    checks['all_24_display_contacts_correct_in_exported_copper'] = len(pads) == 24 and all(
        int(p.attrs['.P'][1]) == 24-i and short_net(p.attrs['.N'][0]) == PANEL_NETS[i]
        and abs(p.x-(24.25+.5*i)) < 1e-6 and abs(p.y-49.3) < 1e-6
        for i, p in enumerate(pads))
    def size(obj):
        (x1, y1), (x2, y2) = obj.bounding_box(MM)
        return round(x2-x1, 6), round(y2-y1, 6)
    checks['display_copper_lands_0_30_by_1_30'] = all(size(p) == (.3, 1.3) for p in pads)
    mask = [o for o in stack.graphic_layers['top', 'mask'].objects
            if isinstance(o, Flash) and o.attrs.get('.C') == ('DS1',) and abs(o.y-49.3) < 1e-6]
    checks['display_mask_matches_all_24_lands'] = len(mask) == 24 and all(size(o) == (.3, 1.3) for o in mask)
    paste = stack.graphic_layers['top', 'paste'].objects
    regions = [o for o in paste if not isinstance(o, Flash)]
    centers = set()
    for o in regions:
        (x1, y1), (x2, y2) = o.bounding_box(MM)
        centers.add((round((x1+x2)/2, 6), round((y1+y2)/2, 6)))
    checks['display_24_separate_0_25_by_1_30_paste_apertures'] = len(regions) == 24 and all(
        size(o) == (.25, 1.3) for o in regions) and centers == {(24.25+.5*i, 49.3) for i in range(24)}
    placements = list(csv.DictReader((out / 'assembly/placements.csv').open()))
    populated = {r['Ref'] for r in placements}
    # Gerbonara 1.5's Region object does not preserve component attributes;
    # every populated footprint (including DS1's mounting lands) also flashes.
    pasted = {o.attrs['.C'][0] for o in paste if isinstance(o, Flash) and '.C' in o.attrs}
    checks['116_populated_parts_match_stencil_and_positions'] = len(placements) == len(populated) == 116 and pasted == populated
    spec = json.loads((out / 'manufacturing-spec.json').read_text())
    checks['no_DNP_or_mechanical_paste'] = not pasted.intersection(spec['dnp'] + spec['non_components'])

    # Compare all round holes to native geometry, including unfilled routing vias.
    expected_holes = []
    for q in geometry['items']:
        drill = q['drill'] if q['type'] == 'via' else (
            q['drill'][0] if q['type'] == 'pad' and q['drill'][0] == q['drill'][1] else 0)
        if drill:
            expected_holes.append((round(q['xy'][0]-50, 6), round(160-q['xy'][1], 6), round(drill, 6)))
    holes = [(round(o.x, 6), round(o.y, 6), round(o.aperture.diameter, 6))
             for o in pth.objects + npth.objects if isinstance(o, Flash)]
    # Excellon uses 0.001 mm coordinates; native geometry has finer precision.
    # Match each hole exactly once within half a coordinate quantum on each
    # axis, retaining exact drill sizes and counts (including coincident holes).
    unmatched = list(holes)
    drill_errors = []
    for x, y, diameter in expected_holes:
        candidates = [(max(abs(x-h[0]), abs(y-h[1])), i)
                      for i, h in enumerate(unmatched) if h[2] == diameter
                      and max(abs(x-h[0]), abs(y-h[1])) <= .000501]
        if not candidates:
            break
        error, index = min(candidates)
        drill_errors.append(error)
        unmatched.pop(index)
    checks['all_round_drill_locations_and_sizes_match_board'] = (
        len(drill_errors) == len(expected_holes) and not unmatched)
    slots = [o for o in pth.objects if not isinstance(o, Flash)]
    checks['four_0_70_mm_plated_USB_slots'] = len(slots) == 4 and all(isinstance(o, Line) and o.aperture.diameter == .7 for o in slots)
    checks['30_unplated_locators_and_mouse_bites'] = len(npth.objects) == 30 and Counter(
        round(o.aperture.diameter, 6) for o in npth.objects) == {.6: 28, .65: 2}

    graph = defaultdict(set)
    for obj in stack.outline.objects:
        assert isinstance(obj, (Line, Arc))
        a, b = (round(obj.x1, 6), round(obj.y1, 6)), (round(obj.x2, 6), round(obj.y2, 6))
        graph[a].add(b)
        graph[b].add(a)
    pending, loops = set(graph), []
    while pending:
        todo, seen = [next(iter(pending))], set()
        while todo:
            node = todo.pop()
            if node in seen:
                continue
            seen.add(node)
            todo.extend(graph[node]-seen)
        pending -= seen
        loops.append(seen)
    checks['three_closed_outline_contours'] = len(loops) == 3 and all(len(v) == 2 for v in graph.values())
    outer = max(loops, key=len)
    checks['60_by_110_mm_envelope'] = (min(p[0] for p in outer), max(p[0] for p in outer),
                                        min(p[1] for p in outer), max(p[1] for p in outer)) == (0, 60, 0, 110)
    report = dict(passed=all(checks.values()), checks=checks, source_board_sha256=manifest['source_board_sha256'],
                  export_manifest_sha256=sha(out / 'manifest.json'), parser_warnings=warning_text,
                  source_netlist_sha256=sha(ROOT / 'docs/netlist.xml'),
                  drill_coordinate_resolution_mm=.001,
                  maximum_drill_coordinate_rounding_mm=max(drill_errors, default=0),
                  display_contacts=[dict(panel_pin=i+1, socket_pad=p.attrs['.P'][1],
                                         gerber_xy_mm=[p.x, p.y], net=p.attrs['.N'][0]) for i, p in enumerate(pads)],
                  scope='Gerber/drill/placement translation audit; no electrical qualification or fabrication release.')
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    for name, ok in checks.items():
        print(('PASS ' if ok else 'FAIL ') + name)
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
