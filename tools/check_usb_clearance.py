#!/usr/bin/env python3
"""Audit the approved USB land trim against the locked design d4eaaa9."""
import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess

from kicad_sexpr import parse, child, children, uq

ROOT = Path(__file__).resolve().parents[1]
BASE = 'd4eaaa9'
OLD = 'Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal'
NEW = 'Nucula_Project:USB_C_GCT_USB4105_16P_JLCPCB'
LANDS = {'A1', 'A12', 'B1', 'B12'}


def canonical(node):
    if isinstance(node, list):
        return [canonical(x) for x in node if not (isinstance(x, list) and
                (x[0] in ['version', 'generator', 'generator_version', 'filled_polygon',
                          'fill_segments'] or x == ['zone_defaults']))]
    if node.startswith('"'):
        return uq(node)
    try:
        return float(node)
    except ValueError:
        return node


def baseline(name):
    from historical_source import read_baseline
    return read_baseline(BASE, name)


def run():
    board = ROOT / 'nucula-v2.kicad_pcb'
    before, after = parse(baseline(board.name)), parse(board.read_text())
    def footprints(tree):
        return {next(uq(p[2]) for p in children(f, 'property') if uq(p[1]) == 'Reference'): f
                for f in children(tree, 'footprint')}
    a, b = footprints(before), footprints(after)
    expected = copy.deepcopy(a['J1'])
    expected[1] = json.dumps(NEW)
    for p in children(expected, 'pad'):
        if uq(p[1]) in LANDS:
            child(p, 'at')[2] = '-3.70'
            child(p, 'size')[2] = '1.11'
    checks = {'same_130_footprints': set(a) == set(b) and len(b) == 130,
              'j1_only_approved_four_pad_definitions_and_library_id': canonical(b['J1']) == canonical(expected),
              'other_129_footprints_identical': all(canonical(a[r]) == canonical(b[r]) for r in a if r != 'J1')}
    expected_board = copy.deepcopy(before)
    expected_board[expected_board.index(next(f for f in children(expected_board, 'footprint')
        if uq(f[1]) == OLD))] = expected
    checks['all_other_board_geometry_and_settings_identical_except_zone_refill'] = canonical(expected_board) == canonical(after)
    checks['schematic_only_j1_library_assignment_changed'] = (ROOT / 'power-mcu.kicad_sch').read_text() == baseline('power-mcu.kicad_sch').replace(OLD, NEW)
    checks['only_j1_hole_rule_raised_to_0_20mm'] = (ROOT / 'nucula-v2.kicad_dru').read_text() == baseline('nucula-v2.kicad_dru').replace('manufacturer NPTH-pad spacing', 'JLCPCB NPTH-pad spacing').replace('0.19mm', '0.20mm')
    for name in ['nucula-v2.kicad_pro', 'nucula-v2.kicad_sch', 'oled.kicad_sch', 'nfc.kicad_sch', 'keyboard.kicad_sch']:
        if (ROOT / name).exists():
            checks[name + '_unchanged'] = (ROOT / name).read_text() == baseline(name)
    lib = parse((ROOT / 'libraries/Nucula_Project.pretty' / (NEW.split(':')[1]+'.kicad_mod')).read_text())
    def pads(tree):
        return sorted((uq(p[1]), p[2:4], canonical(child(p, 'at'))[1:3],
                       canonical(child(p, 'size')), canonical(child(p, 'layers')),
                       canonical(children(p, 'drill')), canonical(children(p, 'roundrect_rratio')))
                      for p in children(tree, 'pad'))
    checks['all_library_pad_shapes_and_holes_match_board'] = pads(lib) == pads(b['J1'])
    holes = [p for p in children(lib, 'pad') if p[2] == 'np_thru_hole']
    clearances = []
    for p in children(lib, 'pad'):
        if p[2] != 'smd':
            continue
        x, y = map(float, child(p, 'at')[1:3])
        w, h = map(float, child(p, 'size')[1:3])
        radius = min(w,h)*float(child(p, 'roundrect_rratio')[1])
        for hole in holes:
            hx, hy = map(float, child(hole, 'at')[1:3])
            dx, dy = max(abs(hx-x)-(w/2-radius),0), max(abs(hy-y)-(h/2-radius),0)
            gap = math.hypot(dx,dy)-radius-float(child(hole, 'drill')[1])/2
            clearances.append(gap)
    minimum = min(clearances)
    checks['all_j1_npth_to_smd_clearances_above_0_20mm'] = minimum > .20
    checks['minimum_matches_independent_geometry_0_233308mm'] = abs(minimum-.233308)<1e-6
    report = json.loads((ROOT / 'docs/pcb/drc.json').read_text())
    checks['native_drc_only_original_two_silk_warnings'] = report['violations'] == json.loads(baseline('docs/pcb/drc.json'))['violations'] and not report['unconnected_items'] and not report['schematic_parity']
    return {'baseline_commit': BASE, 'passed': all(checks.values()), 'checks': checks,
            'minimum_npth_to_smd_clearance_mm': round(minimum,6), 'j1_rule_minimum_mm': .20,
            'physical_lands_modified': 2, 'pad_definitions_modified': sorted(LANDS),
            'trim_at_hole_facing_end_mm': .04, 'land_size_mm': [.6,1.11],
            'land_area_reduction_percent': round(.6*.04/(.6*1.15-(4-math.pi)*.15**2)*100,3),
            'board_sha256': hashlib.sha256(board.read_bytes()).hexdigest(),
            'limits': 'Nominal geometry audit, not a physical connector or assembly qualification; project adaptation of manufacturer lands.'}


if __name__ == '__main__':
    report = run()
    (ROOT / 'docs/usb-clearance-check.json').write_text(json.dumps(report, indent=2)+'\n')
    for name, ok in report['checks'].items():
        print(('PASS ' if ok else 'FAIL ')+name)
    raise SystemExit(0 if report['passed'] else 1)
