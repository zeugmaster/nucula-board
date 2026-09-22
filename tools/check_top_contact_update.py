#!/usr/bin/env python3
"""Verify FH12A geometry and isolate the update from saved bottom-contact 96c8114.

Run after native DRC, schematic and assembly checks. Dimensions below come from
Hirose EDC3-150555-51 sheet 1, independently of the footprint generator.
"""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from kicad_sexpr import parse, children, child, uq
from check_oled24_update import canonical, props, net_members, indexed

ROOT = Path(__file__).resolve().parents[1]
BASE = '96c8114'


def old(name):
    from historical_source import read_baseline
    return read_baseline(BASE, name)


def run():
    before = parse(old('nucula-v2.kicad_pcb'))
    after = parse((ROOT / 'nucula-v2.kicad_pcb').read_text())
    a, b = [{props(f)['Reference']: f for f in children(t, 'footprint')} for t in [before, after]]
    ds = b['DS1']
    footprint = ROOT / 'libraries/Nucula_Project.pretty/Hirose_FH12A-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal.kicad_mod'
    lib = parse(footprint.read_text())
    checks = {}
    # Subsequent approved USB amendment is checked separately against d4eaaa9.
    from check_usb_clearance import run as usb_check
    checks['subsequent_usb_amendment_is_exact'] = usb_check()['passed']
    checks['same_130_footprints'] = set(a) == set(b) and len(b) == 130
    checks['other_128_footprints_identical'] = all(canonical(a[r]) == canonical(b[r]) for r in a if r not in {'DS1', 'J1'})
    checks['ds1_center_shift_only_0_20mm_y'] = canonical(child(ds, 'at')) == ['at', 80., 108.85, 180.]
    checks['ds1_lock_side_uuid_preserved'] = all(canonical(child(ds, k)) == canonical(child(a['DS1'], k)) for k in ['locked', 'layer', 'uuid'])
    checks['correct_top_contact_part'] = props(ds)['MPN'] == 'FH12A-24S-0.5SH(55)' and props(ds)['LCSC'] == 'C506794'
    pads = {uq(p[1]): p for p in children(lib, 'pad') if uq(p[1]).isdigit()}
    checks['drawing_24_pins_left_to_right_top_view'] = set(pads) == {str(i) for i in range(1, 25)} and all(
        canonical(child(pads[str(i)], 'at')) == ['at', -5.75 + .5*(i-1), -1.85] for i in range(1, 25))
    checks['drawing_signal_lands_0_30_by_1_30'] = all(canonical(child(p, 'size')) == ['size', .3, 1.3] for p in pads.values())
    mp = [p for p in children(lib, 'pad') if uq(p[1]) == 'MP']
    checks['drawing_mount_lands_17_10_outer_13_50_inner'] = len(mp) == 2 and sorted(canonical(child(p, 'at')) for p in mp) == [['at', -7.65, 1.4], ['at', 7.65, 1.4]] and all(canonical(child(p, 'size')) == ['size', 1.8, 2.2] for p in mp)
    paste = [x for x in children(lib, 'fp_rect') if uq(child(x, 'layer')[1]) == 'F.Paste']
    checks['drawing_24_paste_apertures_0_25_by_1_30'] = len(paste) == 24 and all(
        canonical(child(r, 'start')) == ['start', -5.75 + i*.5 - .125, -2.5] and
        canonical(child(r, 'end')) == ['end', -5.75 + i*.5 + .125, -1.2] and
        child(r, 'fill')[1] == 'solid' and float(child(child(r, 'stroke'), 'width')[1]) == 0
        for i, r in enumerate(paste)) and all('F.Paste' not in [uq(x) for x in child(p, 'layers')[1:]] for p in pads.values())
    # Placed copper, mask and paste must agree with the audited library definition.
    def pad_geometry(t):
        return sorted((uq(p[1]), canonical(child(p, 'at'))[1:3], canonical(child(p, 'size')),
                       canonical(child(p, 'layers'))) for p in children(t, 'pad'))
    checks['placed_lands_match_library'] = pad_geometry(lib) == pad_geometry(ds)
    def paste_geometry(t):
        # KiCad may reverse item serialization order and normalize solid -> yes.
        return sorted((canonical(child(x, 'start')), canonical(child(x, 'end')),
                       child(x, 'fill')[1] in ['solid', 'yes'],
                       float(child(child(x, 'stroke'), 'width')[1]))
                      for x in children(t, 'fp_rect') if uq(child(x, 'layer')[1]) == 'F.Paste')
    checks['placed_paste_matches_library'] = paste_geometry(ds) == paste_geometry(lib)
    for kind in ['general', 'setup', 'layers', 'gr_text', 'gr_text_box', 'gr_line', 'gr_arc', 'gr_poly', 'gr_circle', 'dimension', 'group']:
        checks[f'{kind}_unchanged'] = canonical(children(before, kind)) == canonical(children(after, kind))
    changes = {}
    scoped = True
    allowed = {'GND', '+3V0', 'I2C_SDA', 'I2C_SCL', 'OLED_RES_N', 'OLED_IREF', 'OLED_VCOMH', 'OLED_12V5'}
    for kind in ['segment', 'arc', 'via']:
        aa, bb = indexed(before, kind), indexed(after, kind)
        changed = [u for u in aa.keys() & bb.keys() if canonical(aa[u]) != canonical(bb[u])]
        changes[kind] = len(changed)
        scoped &= aa.keys() == bb.keys()
        for u in changed:
            for t in [aa[u], bb[u]]:
                scoped &= uq(child(t, 'net')[-1]).rsplit('/', 1)[-1] in allowed
                for key in ['start', 'end', 'at']:
                    for point in children(t, key):
                        x, y = map(float, point[1:3])
                        scoped &= 68 <= x <= 87 and 107 <= y <= 117
    checks['routing_changes_confined_to_oled'] = scoped
    checks['all_91_nets_identical'] = net_members(ET.fromstring(old('docs/netlist.xml'))) == net_members(ET.parse(ROOT / 'docs/netlist.xml').getroot())
    drc = json.loads((ROOT / 'docs/pcb/drc.json').read_text())
    checks['drc_only_same_two_existing_silk_warnings'] = drc['violations'] == json.loads(old('docs/pcb/drc.json'))['violations'] and not drc['unconnected_items'] and not drc['schematic_parity']
    rows = list(csv.DictReader((ROOT / 'docs/assembly/jlcpcb-bom.csv').open()))
    bom = {r.strip(): row for row in rows for r in row['Designator'].split(',')}
    checks['bom_exact_socket_only_modules_excluded'] = (len(rows) == 55 and len(bom) == 116 and
        bom['DS1']['Comment'] == 'FH12A-24S-0.5SH(55)' and bom['DS1']['LCSC Part #'] == 'C506794' and
        bom['U8']['LCSC Part #'] == 'C7605' and not {'J3', 'J4', 'J5', 'A1', 'MB1', 'MB2'} & bom.keys() and
        not any('NFP1309' in v for row in rows for v in row.values()))
    for name in ['nucula-v2.kicad_pro', 'nucula-v2.kicad_sch', 'nfc.kicad_sch', 'keyboard.kicad_sch']:
        checks[f'{name}_unchanged'] = (ROOT / name).read_text() == old(name)
    return {'baseline_commit': BASE, 'passed': all(checks.values()), 'checks': checks,
            'routing_items_modified': changes, 'board_sha256': hashlib.sha256((ROOT / 'nucula-v2.kicad_pcb').read_bytes()).hexdigest(),
            'limits': 'No physical panel fit, insertion strain, enclosure or functional measurements; 3D model is a simplified illustration.'}


if __name__ == '__main__':
    report = run()
    (ROOT / 'docs/oled24/top-contact-check.json').write_text(json.dumps(report, indent=2) + '\n')
    for name, ok in report['checks'].items():
        print(('PASS ' if ok else 'FAIL ') + name)
    raise SystemExit(0 if report['passed'] else 1)
