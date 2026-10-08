#!/usr/bin/env python3
"""Check MINI-1 datasheet pins, flush antenna fit, keepout and USB fanout.

Run with KiCad's pcbnew-enabled Python, after schematic export and zone refill.
This does not qualify RF performance, firmware, assembly or physical tolerances.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as k
from check_pcb_layout import rectangle, overlap_area

ROOT = Path(__file__).resolve().parents[1]
MPN = 'ESP32-C3-MINI-1-H4X'
FOOTPRINT = 'Nucula_Project:' + MPN + '_NoEPADSolder'
# Espressif MINI-1 datasheet v2.2, Table 3-1, independent of schematic symbol.
SIGNALS = {
    '3': '+3V3', '5': 'STRAP_GPIO2', '6': 'OLED_PWR_EN', '8': 'ESP_EN',
    '12': 'VBAT_ADC', '13': 'USB_PRESENT_N', '16': 'OLED_RESET',
    '18': 'I2C_SDA', '19': 'I2C_SCL', '20': 'NFC_IRQ', '21': 'NFC_VEN',
    '22': 'STRAP_GPIO8', '23': 'BOOT_N', '26': 'Net-(U3-IO18)',
    '27': 'Net-(U3-IO19)', '30': 'KEY_INT_N',
}
GROUND = {str(n) for n in [1, 2, 11, 14, *range(36, 54)]}
NC = {str(n) for n in [4, 7, 9, 10, 15, 17, 24, 25, 28, 29, 32, 33, 34, 35]}


def audit(board_path, netlist_path):
    board = k.LoadBoard(str(board_path))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    fp = fps['U3']
    pads = {p.GetNumber(): p for p in fp.Pads()}
    xml = ET.parse(netlist_path)
    nets = {n.get('name'): {(p.get('ref'), p.get('pin')) for p in n.findall('node')}
            for n in xml.findall('./nets/net')}
    pin = {p: n for n, members in nets.items() for p in members}
    comp = next(c for c in xml.findall('./components/comp') if c.get('ref') == 'U3')
    checks = {}
    checks['selected_4MB_H4X_module_and_footprint'] = (
        fp.GetValue() == comp.findtext('value') == MPN
        and str(fp.GetFPIDAsString()) == comp.findtext('footprint') == FOOTPRINT
        and fp.GetFieldText('MPN') == MPN and fp.GetFieldText('LCSC') == 'C41349510')
    checks['all_53_module_pins_present'] = set(pads) == {str(n) for n in range(1, 54)}
    checks['datasheet_signals_preserve_GPIO_assignments'] = all(
        pin.get(('U3', number), '').rsplit('/', 1)[-1] == name
        for number, name in SIGNALS.items())
    checks['all_22_ground_pins_grounded'] = all(pin.get(('U3', n)) == 'GND' for n in GROUND)
    checks['NC_pins_and_reserved_GPIO21_isolated'] = all(
        pin.get(('U3', n), '').startswith('unconnected-')
        and nets[pin['U3', n]] == {('U3', n)} for n in NC | {'31'})
    checks['every_PCB_pad_matches_schematic'] = all(
        p.GetNetname().replace('{slash}', '/') == pin.get(('U3', n)) for n, p in pads.items())
    epad = pads['49']
    checks['optional_EPAD_joint_omitted_without_via_in_pad'] = (
        not epad.IsOnLayer(k.F_Mask) and not epad.IsOnLayer(k.F_Paste)
        and epad.GetDrillSize().x == 0 and epad.GetNetname() == 'GND')
    checks['all_perimeter_pads_have_mask_and_paste'] = all(
        p.IsOnLayer(k.F_Mask) and p.IsOnLayer(k.F_Paste) for n, p in pads.items() if n != '49')
    position = [k.ToMM(fp.GetPosition().x), k.ToMM(fp.GetPosition().y), fp.GetOrientationDegrees()]
    checks['module_position_locked'] = position == [101.7, 106.14, -90.0] and fp.IsLocked()
    # Antenna is local x +/-6.6, y -8.3..-2.9, at the above rotation.
    antenna = rectangle([104.6, 99.54, 110.0, 112.74])
    outline = k.SHAPE_POLY_SET()
    checks['outline_is_closed'] = board.GetBoardPolygonOutlines(outline, False)
    checks['antenna_has_no_baseboard_underneath'] = overlap_area(outline, antenna) < 1e-7
    checks['antenna_tip_flush_with_110mm_board_edge'] = (
        abs(position[0] + 8.3 - 110) < 1e-9 and abs(k.ToMM(outline.BBox().GetRight()) - 110) < 1e-5)
    rules = [z for z in fp.Zones() if z.GetIsRuleArea()]
    checks['antenna_keepout_matches_datasheet_on_all_four_layers'] = len(rules) == 1 and all(
        all(z.IsOnLayer(l) for l in [k.F_Cu, k.In1_Cu, k.In2_Cu, k.B_Cu])
        and z.GetDoNotAllowTracks() and z.GetDoNotAllowVias() and z.GetDoNotAllowPads()
        and z.GetDoNotAllowZoneFills() and abs(overlap_area(z.Outline(), antenna) - 5.4 * 13.2) < 1e-7
        for z in rules)
    checks['no_filled_copper_under_antenna'] = all(
        overlap_area(z.GetFilledPolysList(layer), antenna) < 1e-7
        for z in board.Zones() if not z.GetIsRuleArea()
        for layer in [k.F_Cu, k.In1_Cu, k.In2_Cu, k.B_Cu] if z.IsOnLayer(layer))
    lengths = {}
    for gpio in ['18', '19']:
        net = f'Net-(U3-IO{gpio})'
        tracks = [t for t in board.GetTracks() if t.GetNetname() == net]
        checks[f'USB_GPIO{gpio}_has_no_vias_and_stays_on_front'] = all(
            not isinstance(t, k.PCB_VIA) and t.GetLayer() == k.F_Cu for t in tracks) and bool(tracks)
        lengths[gpio] = sum(k.ToMM(t.GetLength()) for t in tracks)
    checks['USB_module_to_resistor_lengths_match_within_0_01mm'] = abs(lengths['18'] - lengths['19']) < .01
    return dict(passed=all(checks.values()), checks=checks, selected_module=MPN,
                module_body_mm=[13.2, 16.6, 2.4], module_position=position,
                antenna_bounds_mm=[104.6, 99.54, 110, 112.74],
                notch_bounds_mm=[104.6, 98.54, 110, 113.74], notch_internal_radius_mm=.5,
                USB_module_to_resistor_lengths_mm=lengths,
                board_sha256=hashlib.sha256(board_path.read_bytes()).hexdigest(),
                netlist_sha256=hashlib.sha256(netlist_path.read_bytes()).hexdigest(), hardware_tested=False)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--board', type=Path, default=ROOT/'nucula-v2.kicad_pcb')
    ap.add_argument('--netlist', type=Path, default=ROOT/'docs/netlist.xml')
    ap.add_argument('--out', type=Path, default=ROOT/'docs/pcb/mini-module-check.json')
    args = ap.parse_args()
    result = audit(args.board, args.netlist)
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    for name, ok in result['checks'].items():
        print(('PASS ' if ok else 'FAIL ')+name)
    raise SystemExit(0 if result['passed'] else 1)
