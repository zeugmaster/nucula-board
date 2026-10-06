#!/usr/bin/env python3
"""Independently check the corrected USB topology, package pins and saved PCB.

ERC can accept the original steering-diode backfeed circuit. These requirements
encode the replacement's datasheet pin maps and fail if that path returns.
They do not prove physical leakage, ESD survival or USB signal integrity.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from kicad_sexpr import child, children, parse, uq

ROOT = Path(__file__).resolve().parents[1]
CHANGED_REFS = {'U4', 'U10', 'D5', 'C55', 'R12', 'R13', 'R17', 'R18',
                'C7', 'C8', 'C13', 'R16'}


def audit(board_path, netlist_path):
    xml = ET.parse(netlist_path)
    parts = {p.get('ref'): p for p in xml.findall('./components/comp')}
    nets = {n.get('name'): {(p.get('ref'), p.get('pin')) for p in n.findall('node')}
            for n in xml.findall('./nets/net')}
    pin = {p: n for n, ps in nets.items() for p in ps}
    tree = parse(board_path.read_text())
    fps = {next(uq(p[2]) for p in children(f, 'property') if uq(p[1]) == 'Reference'): f
           for f in children(tree, 'footprint')}
    def n(ref, num):
        return pin.get((ref, str(num)))
    def group(*ps):
        keys = {tuple(p.split('.')) for p in ps}
        return any(keys == v for v in nets.values())
    def props(f):
        return {uq(p[1]): uq(p[2]) for p in children(f, 'property')}
    qualified = {
        'U4': ('TPD2E2U06QDCKRQ1', 'C915089', 'Package_TO_SOT_SMD:SOT-323_SC-70'),
        'U10': ('TS3USB30EDGSR', 'C131998', 'Package_SO:TSSOP-10_3x3mm_P0.5mm'),
        'D5': ('TPD1E10B06DYAR', 'C3712135', 'Diode_SMD:D_SOD-523'),
    }
    checks = {}
    checks['qualified_parts_and_package_pin_maps'] = all(
        r in fps and (props(fps[r]).get('MPN'), props(fps[r]).get('LCSC'), uq(fps[r][1])) == v
        for r, v in qualified.items())
    checks['connector_Dminus_has_only_ground_TVS_and_switch_common'] = group('J1.A7', 'J1.B7', 'U4.1', 'U10.6')
    checks['connector_Dplus_has_only_ground_TVS_and_switch_common'] = group('J1.A6', 'J1.B6', 'U4.2', 'U10.4')
    checks['switch_port1_through_series_resistors_to_correct_ESP_pins'] = all([
        group('U10.8', 'R12.1'), group('U10.2', 'R13.1'),
        group('R12.2', 'U3.13'), group('R13.2', 'U3.14')])
    checks['data_TVS_has_no_supply_or_VBUS_connection'] = (
        {p[1] for p in pin if p[0] == 'U4'} == {'1', '2', '3'}
        and n('U4', 3) == 'GND' and n('C14', 1) not in {n('U4', p) for p in [1, 2, 3]})
    checks['VBUS_has_separate_ground_TVS'] = n('D5', 1) == n('J1', 'A4') == n('C14', 1) and n('D5', 2) == 'GND'
    checks['switch_select_and_ground_are_grounded'] = n('U10', 1) == n('U10', 5) == 'GND'
    checks['switch_unused_port_is_unconnected'] = all(
        n('U10', p) is not None and len(nets[n('U10', p)]) == 1 for p in [3, 7])
    checks['switch_3V3_supply_is_decoupled'] = n('U10', 10) == n('C55', 1) == n('C11', 1) and n('C55', 2) == 'GND'
    checks['active_low_enable_is_driven_by_existing_VBUS_detector'] = group('Q2.3', 'R17.2', 'U3.17', 'U10.9')
    checks['VBUS_detector_and_pullup_have_correct_rails'] = (
        n('Q2', 1) == n('R18', 1) == n('C14', 1) and n('Q2', 2) == n('R18', 2) == 'GND'
        and n('R17', 1) == n('C11', 1))
    checks['bleeder_pullup_series_and_decoupling_values'] = all(
        r in parts and parts[r].findtext('value') == value
        for r, value in {'R17': '10k', 'R18': '10k', 'R12': '22R', 'R13': '22R', 'C55': '100nF'}.items())
    checks['unused_USB_loading_branches_removed'] = not ({'C7', 'C8'} & set(parts)) and not ({'C7', 'C8'} & set(fps))
    checks['all_affected_PCB_pads_match_schematic'] = all(
        uq(child(p, 'net')[-1]).replace('{slash}', '/') == pin.get((r, uq(p[1])))
        for r in CHANGED_REFS & set(fps) for p in children(fps[r], 'pad'))
    return dict(passed=all(checks.values()), checks=checks,
                board_sha256=hashlib.sha256(board_path.read_bytes()).hexdigest(),
                netlist_sha256=hashlib.sha256(netlist_path.read_bytes()).hexdigest(),
                hardware_tested=False,
                scope='Electrical topology and manufacturer package pin maps; native DRC checks copper connectivity. Bench validation remains necessary.')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--board', type=Path, default=ROOT/'nucula-v2.kicad_pcb')
    ap.add_argument('--netlist', type=Path, default=ROOT/'docs/netlist.xml')
    ap.add_argument('--out', type=Path, default=ROOT/'docs/bringup/usb-backfeed-check.json')
    args = ap.parse_args()
    result = audit(args.board, args.netlist)
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    for name, ok in result['checks'].items():
        print(('PASS ' if ok else 'FAIL ')+name)
    raise SystemExit(0 if result['passed'] else 1)
