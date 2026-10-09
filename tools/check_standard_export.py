#!/usr/bin/env python3
"""Read current production Gerbers/drills with the existing Gerbonara stack.

Checks restored NFC mixed via sizes, corrected mounted display mapping, and
every native footprint anchor and assembly pad against the exported files.
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

    mini_pads = [o for o in stack.graphic_layers['top', 'copper'].objects
                 if isinstance(o, Flash) and o.attrs.get('.P', ('',))[0] == 'U3']
    mini_by_pin = {o.attrs['.P'][1]: o for o in mini_pads}
    checks['MINI_all_53_lands_exported'] = len(mini_pads) == 53 and set(mini_by_pin) == {str(n) for n in range(1, 54)}
    checks['MINI_USB_and_supply_manufacturer_pin_numbers'] = all(
        mini_by_pin[n].attrs['.N'][0].rsplit('/', 1)[-1] == net
        for n, net in {'3': '+3V3', '8': 'ESP_EN', '26': 'Net-(U3-IO18)', '27': 'Net-(U3-IO19)'}.items())
    for layer in ['mask', 'paste']:
        flashes = [o for o in stack.graphic_layers['top', layer].objects
                   if isinstance(o, Flash) and o.attrs.get('.C') == ('U3',)]
        checks['MINI_52_perimeter_lands_no_EPAD_in_' + layer] = (
            len(flashes) == 52 and all(abs(o.x - 49) > .01 or abs(o.y - 53.86) > .01 for o in flashes))
    checks['MINI_resized_notch_in_exported_outline'] = any(
        isinstance(o, Line) and abs(o.x1 - 54.6) < 1e-5 and abs(o.x2 - 54.6) < 1e-5
        and abs(min(o.y1, o.y2) - 46.76) < 1e-5 and abs(max(o.y1, o.y2) - 60.96) < 1e-5
        for o in stack.outline.objects)

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
    # Manufacturer side-entry lands at the locked, outward-facing placement.
    j2_expected = [(9.7, 59.6, 1.55, .6), (9.7, 58.6, 1.55, .6),
                   (5.825, 60.9, 1.8, 1.2), (5.825, 57.3, 1.8, 1.2)]
    def j2_flashes(layer):
        return [o for o in stack.graphic_layers['top', layer].objects
                if isinstance(o, Flash) and (o.attrs.get('.P', ('',))[0] == 'J2'
                                             if layer == 'copper' else o.attrs.get('.C') == ('J2',))]
    for layer in ['copper', 'mask', 'paste']:
        actual = [(round(o.x, 6), round(o.y, 6), *size(o)) for o in j2_flashes(layer)]
        checks['J2_side_entry_four_lands_in_' + layer] = sorted(actual) == sorted(j2_expected)
    j2_signals = {o.attrs['.P'][1]: o for o in j2_flashes('copper')
                  if o.attrs.get('.P', ('', ''))[1] in ['1', '2']}
    checks['J2_exported_positive_and_ground_polarity'] = (
        set(j2_signals) == {'1', '2'} and
        j2_signals['1'].attrs['.N'][0].endswith('/VBAT') and
        j2_signals['2'].attrs['.N'][0] == 'GND' and
        abs(j2_signals['1'].y - 59.6) < 1e-6 and abs(j2_signals['2'].y - 58.6) < 1e-6)
    j2_tabs = [o for o in j2_flashes('copper') if o.attrs.get('.P', ('',''))[1] == 'MP']
    checks['J2_exported_hold_down_tabs_are_unconnected'] = len(j2_tabs) == 2 and all(
        o.attrs.get('.N', ('',))[0] == 'N/C' for o in j2_tabs)
    bom = list(csv.DictReader((out/'assembly/jlcpcb-bom.csv').open()))
    j2_bom = [r for r in bom if 'J2' in [s.strip() for s in r['Designator'].split(',')]]
    checks['J2_exact_side_entry_order_code_in_BOM'] = len(j2_bom) == 1 and (
        j2_bom[0]['Comment'] == 'SM02B-SRSS-TB(LF)(SN)' and j2_bom[0]['LCSC Part #'] == 'C160402')
    cpl = list(csv.DictReader((out/'assembly/jlcpcb-cpl.csv').open()))
    # Independently read the source footprint anchors, not the exporter copy
    # or its position CSV. This catches the old shared body-center-offset bug.
    from kicad_sexpr import parse, children, child, uq
    source = parse((ROOT/'nucula-v2.kicad_pcb').read_text())
    anchors = {}
    for fp in children(source, 'footprint'):
        ref = next(uq(p[2]) for p in children(fp, 'property') if uq(p[1]) == 'Reference')
        at = child(fp, 'at')
        anchors[ref] = (float(at[1])-50, 160-float(at[2]),
                        float(at[3]) % 360 if len(at) > 3 else 0,
                        uq(child(fp, 'layer')[1]))
    audit_rows = []
    for row in cpl:
        ref = row['Designator']
        x, y, angle, layer = anchors[ref]
        dx, dy = float(row['Mid X'])-x, float(row['Mid Y'])-y
        da = (float(row['Rotation'])-angle+180) % 360-180
        audit_rows.append([ref, round(x,6), round(y,6), angle,
                           round(dx,6), round(dy,6), round(da,6),
                           layer == 'F.Cu' and row['Layer'] == 'Top'
                           and max(abs(dx),abs(dy),abs(da)) < 1e-6])
    checks['every_CPL_anchor_angle_and_side_matches_source_PCB'] = (
        len(audit_rows) == 119 and all(row[-1] for row in audit_rows))
    checks['native_position_CSV_matches_source_PCB'] = all(
        max(abs(float(row['PosX'])-anchors[row['Ref']][0]),
            abs(float(row['PosY'])-anchors[row['Ref']][1]),
            abs((float(row['Rot'])-anchors[row['Ref']][2]+180) % 360-180)) < 1e-6
        and row['Side'] == 'top' for row in placements)
    def normalized_net(net):
        return net.replace('{slash}', '/') if net not in ['', 'N/C'] else ''
    expected_pads = Counter((q['ref'], q['num'], normalized_net(q['net']),
                             round(q['xy'][0]-50,6), round(160-q['xy'][1],6))
                            for q in geometry['items'] if q['type'] == 'pad'
                            and q['ref'] in populated and q['num'] and 0 in q['layers'])
    exported_pads = Counter((o.attrs['.P'][0], o.attrs['.P'][1],
                             normalized_net(o.attrs.get('.N', ('',))[0]),
                             round(o.x,6), round(o.y,6))
                            for o in stack.graphic_layers['top', 'copper'].objects
                            if isinstance(o,Flash) and o.attrs.get('.P', ('',))[0] in populated)
    table_pads = Counter((r['Reference'],r['Pad'],normalized_net(r['Net']),
                          round(float(r['X_mm']),6),round(float(r['Y_mm']),6))
                         for r in csv.DictReader((out/'assembly/pad-coordinates.csv').open()))
    checks['all_413_assembly_pad_positions_and_nets_match_source_Gerber_and_table'] = (
        sum(expected_pads.values()) == 413 and expected_pads == exported_pads == table_pads)
    with (out/'assembly/placement-audit.csv').open('w', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['Reference','Expected_X_mm','Expected_Y_mm','Expected_rotation',
                         'CPL_delta_X_mm','CPL_delta_Y_mm','CPL_delta_rotation','Passed'])
        writer.writerows(audit_rows)
    j2_cpl = [r for r in cpl if r['Designator'] == 'J2']
    checks['J2_CPL_anchor_rotation_and_side'] = len(j2_cpl) == 1 and (
        tuple(float(j2_cpl[0][k]) for k in ['Mid X','Mid Y','Rotation']) == (7.7,59.1,270.)
        and j2_cpl[0]['Layer'] == 'Top')
    # Hand-solder lands must survive fabrication export, but never get paste
    # or a machine-placement/BOM entry. Coordinates use the same plot origin.
    wire_expected = [(6.1, 64., 2.2, 2.5), (2.7, 64., 2.2, 2.5)]
    wire_copper = []
    for layer in ['copper', 'mask']:
        flashes = [o for o in stack.graphic_layers['top', layer].objects
                   if isinstance(o, Flash) and (o.attrs.get('.P', ('',))[0] == 'J6'
                   if layer == 'copper' else o.attrs.get('.C') == ('J6',))]
        checks['J6_two_hand_solder_lands_in_' + layer] = sorted(
            (round(o.x, 6), round(o.y, 6), *size(o)) for o in flashes) == sorted(wire_expected)
        if layer == 'copper':
            wire_copper = flashes
    checks['J6_exported_positive_right_ground_left'] = len(wire_copper) == 2 and all(
        (o.attrs['.P'][1] == '1' and o.attrs['.N'][0].endswith('/VBAT') and abs(o.x-6.1) < 1e-6)
        or (o.attrs['.P'][1] == '2' and o.attrs['.N'][0] == 'GND' and abs(o.x-2.7) < 1e-6)
        for o in wire_copper)
    checks['J6_absent_from_stencil_BOM_and_placements'] = (
        not any(isinstance(o, Flash) and o.attrs.get('.C') == ('J6',) for o in paste)
        and 'J6' not in populated and all('J6' not in r['Designator'].split(',') for r in bom)
        and all(r['Designator'] != 'J6' for r in cpl))
    checks['JLC_BOM_CPL_and_native_positions_have_same_references'] = (
        {r.strip() for row in bom for r in row['Designator'].split(',')} == populated
        == {r['Designator'] for r in cpl} and len(cpl) == len(populated))
    # Gerbonara 1.5's Region object does not preserve component attributes;
    # every populated footprint (including DS1's mounting lands) also flashes.
    pasted = {o.attrs['.C'][0] for o in paste if isinstance(o, Flash) and '.C' in o.attrs}
    checks['119_populated_parts_match_stencil_and_positions'] = len(placements) == len(populated) == 119 and pasted == populated
    from check_usb_backfeed import CHANGED_REFS, audit as usb_audit
    assert usb_audit(ROOT/'nucula-v2.kicad_pcb', ROOT/'docs/netlist.xml')['passed']
    expected_usb = {(q['ref'], q['num']): q for q in geometry['items']
                    if q['type'] == 'pad' and q['ref'] in CHANGED_REFS}
    exported_usb = {tuple(o.attrs['.P'][:2]): o
                    for o in stack.graphic_layers['top', 'copper'].objects
                    if isinstance(o, Flash) and o.attrs.get('.P', ('',))[0] in CHANGED_REFS}
    checks['USB_redesign_pad_nets_and_positions_match_exported_copper'] = (
        set(expected_usb) == set(exported_usb) and all(
            o.attrs.get('.N', ('',))[0] == q['net']
            and abs(o.x-(q['xy'][0]-50)) < 1e-6
            and abs(o.y-(160-q['xy'][1])) < 1e-6
            for key, q in expected_usb.items() for o in [exported_usb[key]]))
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
    checks['36_unplated_mounts_locators_and_mouse_bites'] = len(npth.objects) == 36 and Counter(
        round(o.aperture.diameter, 6) for o in npth.objects) == {.6: 28, .65: 2, 2.2: 6}
    mount_xy = {(3.5, 106.5), (56.5, 106.5), (3.5, 40.0),
                (56.5, 40.0), (3.5, 3.5), (56.5, 3.5)}
    checks['six_M2_NPTH_drills_at_requested_corners'] = {
        (round(o.x, 6), round(o.y, 6)) for o in npth.objects
        if isinstance(o, Flash) and abs(o.aperture.diameter - 2.2) < 1e-6
    } == mount_xy
    mounts = {'H1', 'H2', 'H3', 'H4', 'H5', 'H6'}
    checks['mounts_absent_from_BOM_CPL_and_stencil'] = (
        not mounts.intersection(populated | pasted)
        and not mounts.intersection(r.strip() for row in bom for r in row['Designator'].split(','))
        and not mounts.intersection(row['Designator'] for row in cpl))

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
