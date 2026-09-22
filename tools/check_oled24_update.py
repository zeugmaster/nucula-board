#!/usr/bin/env python3
"""Check the CON24 source map and isolate changes from saved design 600d88a.

Run after check_schematic.py and native PCB DRC. Stdlib only. This is an
electrical/geometry regression check; the schematic cannot prove flex fit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from kicad_sexpr import child, children, parse, uq

ROOT = Path(__file__).resolve().parents[1]
BASE = '600d88a'
OUT = ROOT / 'docs/oled24'


def baseline(name):
    from historical_source import read_baseline
    return read_baseline(BASE, name)


def canonical(node):
    if isinstance(node, list):
        return [canonical(x) for x in node if not (isinstance(x, list) and
                (x[0] in ['version', 'generator', 'generator_version'] or
                 x == ['zone_defaults']))]
    if node.startswith('"'):
        return uq(node)
    try:
        return float(node)
    except ValueError:
        return node


def props(node):
    return {uq(p[1]): uq(p[2]) for p in children(node, 'property')}


def indexed(tree, kind, key='uuid'):
    return {uq(child(n, key)[1]): n for n in children(tree, kind)}


def net_members(xml):
    return {n.attrib['name']: {(p.attrib['ref'], p.attrib['pin']) for p in n.findall('node')}
            for n in xml.findall('./nets/net')}


def run(board_path, drc_path):
    source = json.loads((OUT / 'pinout.json').read_text())
    checks = {}
    # Subsequent approved USB amendment is checked separately against d4eaaa9.
    from check_usb_clearance import run as usb_check
    checks['subsequent_usb_amendment_is_exact'] = usb_check()['passed']
    checks['reference_image_hash'] = hashlib.sha256((ROOT / source['source']).read_bytes()).hexdigest() == source['source_sha256']
    old = parse(baseline('nucula-v2.kicad_pcb'))
    new = parse(board_path.read_text())
    oldfps = {props(f)['Reference']: f for f in children(old, 'footprint')}
    newfps = {props(f)['Reference']: f for f in children(new, 'footprint')}
    checks['same_130_footprints'] = set(oldfps) == set(newfps) and len(newfps) == 130
    modified_others = [r for r in oldfps if r not in {'DS1', 'J1'} and canonical(oldfps[r]) != canonical(newfps[r])]
    checks['other_128_footprints_identical'] = not modified_others
    ds = newfps['DS1']
    # Top-contact latch needs 0.20mm more space toward the keyboard. Keep X,
    # rotation and lock; this is the documented subsequent connector update.
    checks['ds1_documented_position_rotation_lock'] = (
        canonical(child(ds, 'at')) == ['at', *source['placement_mm_deg']] and
        all(canonical(child(ds, k)) == canonical(child(oldfps['DS1'], k)) for k in ['locked', 'layer']))
    checks['selected_socket_and_model'] = (uq(ds[1]) == source['footprint'] and
        props(ds)['MPN'] == source['socket_mpn'] and props(ds)['LCSC'] == source['socket_lcsc'] and
        len(children(ds, 'model')) == 1 and uq(child(ds, 'model')[1]) == source['socket_model'])
    pads = {uq(p[1]): p for p in children(ds, 'pad') if uq(p[1]).isdigit()}
    checks['exactly_24_numbered_pads'] = set(pads) == {str(i) for i in range(1, 25)}
    checks['pad_row_pitch_and_number_order'] = all(
        canonical(child(pads[str(i)], 'at')) == ['at', -5.75 + .5*(i-1), -1.85, 180.]
        for i in range(1, 25))
    xml = ET.parse(ROOT / 'docs/netlist.xml').getroot()
    oldnets, newnets = net_members(ET.fromstring(baseline('docs/netlist.xml'))), net_members(xml)
    expected = {n: pins - {('DS1', '25'), ('DS1', '26')} for n, pins in oldnets.items()}
    checks['all_91_nets_unchanged_except_removed_25_26'] = expected == newnets and len(newnets) == 91
    net_of = {p: n for n, pins in newnets.items() for p in pins}
    pin_results = []
    for p in source['pins']:
        num = str(p['pin'])
        schematic_net = net_of[('DS1', num)].rsplit('/', 1)[-1]
        board_net = uq(child(pads[num], 'net')[-1]).rsplit('/', 1)[-1]
        expected_net = 'unconnected-(DS1-NC-Pad4)' if p['project_net'] == 'NC' else p['project_net']
        pin_results.append(dict(p, schematic_net=schematic_net, board_net=board_net,
                                passed=schematic_net == board_net == expected_net))
    checks['all_24_pins_match_independent_reference'] = all(p['passed'] for p in pin_results)
    for kind in ['gr_text', 'gr_text_box', 'gr_poly', 'gr_line', 'gr_arc', 'gr_circle', 'dimension', 'group', 'setup', 'layers', 'general']:
        checks[f'{kind}_preserved'] = canonical(children(old, kind)) == canonical(children(new, kind))
    def zone_settings(t):
        return [[v for v in z if not (isinstance(v, list) and v[0] in ['filled_polygon', 'fill_segments'])]
                for z in children(t, 'zone')]
    checks['zone_outlines_and_keepouts_preserved'] = canonical(zone_settings(old)) == canonical(zone_settings(new))
    changes = {}
    bounds_ok = True
    allowed_nets = {'GND', '+3V0', 'I2C_SDA', 'I2C_SCL', 'OLED_RES_N', 'OLED_IREF', 'OLED_VCOMH', 'OLED_12V5'}
    nets_ok = True
    for kind in ['segment', 'arc', 'via']:
        a, b = indexed(old, kind), indexed(new, kind)
        removed = set(a) - set(b)
        added = set(b) - set(a)
        changed = {u for u in set(a) & set(b) if canonical(a[u]) != canonical(b[u])}
        changes[kind] = dict(removed=len(removed), added=len(added), changed=len(changed))
        for t, tree in [(a[u], old) for u in removed | changed] + [(b[u], new) for u in added | changed]:
            nets = {n[1]: uq(n[2]) for n in children(tree, 'net')}
            net = uq(child(t, 'net')[-1])
            net = nets.get(net, net).rsplit('/', 1)[-1]
            nets_ok &= net in allowed_nets
            for key in ['start', 'end', 'mid', 'at']:
                for point in children(t, key):
                    x, y = map(float, point[1:3])
                    bounds_ok &= 68 <= x <= 87 and 107 <= y <= 117
    checks['routing_changes_only_oled_escapes'] = bounds_ok and nets_ok
    for name in ['nucula-v2.kicad_pro', 'nfc.kicad_sch', 'keyboard.kicad_sch']:
        checks[f'{name}_unchanged'] = (ROOT / name).read_text() == baseline(name)
    previous_constraints = json.loads(baseline('docs/pcb/constraints.json'))
    current_constraints = json.loads((ROOT / 'docs/pcb/constraints.json').read_text())
    current_constraints.pop('authorized_amendments', None)
    previous_constraints['pad_nets']['DS1'] = [p for p in previous_constraints['pad_nets']['DS1'] if p[0] not in ['25', '26']]
    previous_constraints['values']['DS1'] = 'SSD1309 OLED / 24-pin'
    previous_constraints['fixed_placements']['DS1'] = [80.0, 108.85, 180.0]
    checks['no_unrelated_validation_constraints_relaxed'] = current_constraints == previous_constraints
    drc = json.loads(drc_path.read_text())
    before_drc = json.loads((OUT / 'baseline-drc.json').read_text())
    checks['native_drc_no_new_findings'] = drc['violations'] == before_drc['violations'] and not drc['unconnected_items'] and not drc['schematic_parity']
    simulation = json.loads((ROOT / 'docs/simulation/results.json').read_text())
    old_simulation = json.loads(baseline('docs/simulation/results.json'))
    checks['simulation_uses_current_design'] = all(
        hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha
        for name, sha in simulation['source_sha256'].items()) and (
        simulation['netlist_sha256'] == hashlib.sha256((ROOT / 'docs/netlist.xml').read_bytes()).hexdigest())
    checks['all_261_simulation_results_unchanged'] = simulation['simulations_completed'] == 261 and all(
        simulation[key] == old_simulation[key] for key in ['nfc', 'i2c', 'rc', 'dc', 'solver_errors'])
    return dict(baseline_commit=BASE, checks=checks, passed=all(checks.values()),
                pinout=pin_results, other_footprints_modified=modified_others, routing_changes=changes,
                board_sha256=hashlib.sha256(board_path.read_bytes()).hexdigest(),
                netlist_sha256=hashlib.sha256((ROOT / 'docs/netlist.xml').read_bytes()).hexdigest(),
                limits=source['mechanical_limit'])


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--board', type=Path, default=ROOT / 'nucula-v2.kicad_pcb')
    ap.add_argument('--drc', type=Path, default=ROOT / 'docs/pcb/drc.json')
    ap.add_argument('--output', type=Path, default=OUT / 'regression-check.json')
    args = ap.parse_args()
    report = run(args.board, args.drc)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    for key, ok in report['checks'].items():
        print(('PASS ' if ok else 'FAIL ') + key)
    raise SystemExit(0 if report['passed'] else 1)
