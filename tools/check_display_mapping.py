#!/usr/bin/env python3
"""Check mounted display contacts against physical socket pads, not symbol names.

The user confirmed on 2026-10-06 that display pin 1 is PCB-left and pin 24
PCB-right in the existing mounted orientation. Hirose pad numbers are retained.
This catches the Rev-A reversal even when both ERC and schematic parity pass.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from kicad_sexpr import child, children, parse, uq

ROOT = Path(__file__).resolve().parents[1]
FOOTPRINT = 'Hirose_FH12A-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal'
# Display ribbon order from CON24, viewed in the user's mounted arrangement.
PANEL_NETS = ['GND', 'GND', 'GND', 'NC', '+3V0', '+3V0', 'GND', 'GND',
              'OLED_RES_N', 'GND', 'GND', 'GND', 'I2C_SCL', 'I2C_SDA',
              'I2C_SDA', 'GND', 'GND', 'GND', 'GND', 'GND', 'OLED_IREF',
              'OLED_VCOMH', 'OLED_12V5', 'GND']


def props(node):
    return {uq(p[1]): uq(p[2]) for p in children(node, 'property')}


def short_net(name):
    return 'NC' if name.startswith('unconnected-') else name.rsplit('/', 1)[-1]


def audit(board_path, netlist_path):
    tree = parse(board_path.read_text())
    ds = next(f for f in children(tree, 'footprint') if props(f)['Reference'] == 'DS1')
    pads = {int(uq(p[1])): p for p in children(ds, 'pad') if uq(p[1]).isdigit()}
    xml = ET.parse(netlist_path)
    sch = {int(p.get('pin')): n.get('name') for n in xml.findall('./nets/net')
           for p in n.findall('node') if p.get('ref') == 'DS1'}
    rows = []
    for panel_pin, expected in enumerate(PANEL_NETS, 1):
        socket_pad = 25 - panel_pin
        p = pads[socket_pad]
        # Absolute position at the independently required 180-degree placement.
        local_x, local_y = map(float, child(p, 'at')[1:3])
        x, y = 80 - local_x, 108.85 - local_y
        actual = short_net(uq(child(p, 'net')[-1]))
        rows.append(dict(panel_pin=panel_pin, socket_pad=socket_pad,
                         x_mm=x, y_mm=y, expected_net=expected, pcb_net=actual,
                         schematic_net=short_net(sch[socket_pad])))
    lib = parse((ROOT / 'libraries/Nucula_Project.pretty' / (FOOTPRINT + '.kicad_mod')).read_text())
    def lands(node):
        return sorted((uq(p[1]), tuple(child(p, 'at')[1:3]), tuple(child(p, 'size')[1:]),
                       tuple(child(p, 'layers')[1:])) for p in children(node, 'pad'))
    checks = {
        'same_top_contact_socket_and_footprint': uq(ds[1]) == 'Nucula_Project:' + FOOTPRINT
            and props(ds)['MPN'] == 'FH12A-24S-0.5SH(55)',
        'same_position_rotation_and_front_side': list(map(float, child(ds, 'at')[1:])) == [80, 108.85, 180]
            and uq(child(ds, 'layer')[1]) == 'F.Cu' and bool(children(ds, 'locked')),
        'manufacturer_pad_geometry_and_numbering_unchanged': lands(ds) == lands(lib),
        'exactly_24_signal_pads': set(pads) == set(range(1, 25)),
        'panel_1_left_panel_24_right': all(abs(r['x_mm'] - (74.25 + .5*i)) < 1e-6
            and abs(r['y_mm'] - 110.7) < 1e-6 for i, r in enumerate(rows)),
        'all_24_physical_contacts_match_panel': all(r['expected_net'] == r['pcb_net'] for r in rows),
        'all_24_schematic_socket_pins_match_panel': all(r['expected_net'] == r['schematic_net'] for r in rows),
        'panel_NC_is_isolated_socket_21': len(next(n for n in xml.findall('./nets/net')
            if n.get('name') == sch[21]).findall('node')) == 1 and short_net(sch[21]) == 'NC',
    }
    return dict(passed=all(checks.values()), checks=checks, contacts_left_to_right=rows,
                board_sha256=hashlib.sha256(board_path.read_bytes()).hexdigest(),
                netlist_sha256=hashlib.sha256(netlist_path.read_bytes()).hexdigest(),
                scope='Mounted electrical mapping and connector lands; operation and flex fit require hardware.')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--board', type=Path, default=ROOT / 'nucula-v2.kicad_pcb')
    ap.add_argument('--netlist', type=Path, default=ROOT / 'docs/netlist.xml')
    ap.add_argument('--out', type=Path, default=ROOT / 'docs/oled24/mounted-mapping-check.json')
    args = ap.parse_args()
    report = audit(args.board, args.netlist)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    for name, ok in report['checks'].items():
        print(('PASS ' if ok else 'FAIL ') + name)
    raise SystemExit(0 if report['passed'] else 1)
