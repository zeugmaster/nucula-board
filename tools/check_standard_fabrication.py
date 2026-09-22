#!/usr/bin/env python3
"""Audit the ordinary-fabrication revision and the OLED ribbon access area.

Run with KiCad's pcbnew-enabled Python after a full native DRC with zone refill.
This checks physical geometry, not impedance, thermal performance or board function.
"""
import argparse
import hashlib
import json
from pathlib import Path

import pcbnew as k
from check_pcb_layout import polygon, rectangle, overlap_area, digest
from kicad_sexpr import parse, children, child, uq

ROOT = Path(__file__).resolve().parents[1]
ACCESS = [71.15, 98.55, 88.85, 103.55]


def footprint_geometry_hashes(tree):
    """Ignore field styling and front legend only; retain pads, models and rules."""
    result = {}
    for f in children(tree, 'footprint'):
        properties = {uq(p[1]): uq(p[2]) for p in children(f, 'property')}
        geometry = f[:2] + [x for x in f[2:] if not (
            isinstance(x, list) and (x[0] == 'property' or
            (x[0].startswith('fp_') and children(x, 'layer') and
             uq(child(x, 'layer')[1]) == 'F.SilkS')))]
        result[properties['Reference']] = digest([geometry, [list(p) for p in sorted(properties.items())]])
    return result


def run(path, drc_path):
    board = k.LoadBoard(str(path))
    tree = parse(path.read_text())
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    vias = [t for t in board.GetTracks() if isinstance(t, k.PCB_VIA)]
    checks = {}
    checks['four_copper_layers'] = board.GetCopperLayerCount() == 4
    checks['all_routing_vias_0_30_drill_0_70_pad'] = all(
        v.GetDrillValue() == k.FromMM(.3) and v.GetWidth(k.F_Cu) == k.FromMM(.7)
        and v.GetViaType() == k.VIATYPE_THROUGH for v in vias)
    keepouts = [z for z in board.Zones() if z.GetZoneName().startswith('OLED ribbon insertion')]
    access = rectangle(ACCESS)
    checks['ribbon_keepout_enforced_on_front_components'] = len(keepouts) == 1 and all(
        z.GetIsRuleArea() and z.IsOnLayer(k.F_Cu) and z.GetDoNotAllowFootprints()
        and abs(z.Outline().Area()/1e12 - 17.7*5) < 1e-6
        and abs(overlap_area(z.Outline(), access) - 17.7*5) < 1e-6
        for z in keepouts)
    intruders = {ref: round(overlap_area(f.GetCourtyard(k.F_CrtYd), access), 8)
                 for ref, f in fps.items() if f.GetLayer() == k.F_Cu}
    checks['ribbon_access_contains_no_component_courtyards'] = not any(intruders.values())
    exposed_pads = [(f.GetReference(), p) for f in fps.values() for p in f.Pads()
                    if p.GetAttribute() == k.PAD_ATTRIB_SMD and p.IsOnLayer(k.F_Mask)]
    intersections = []
    for v in vias:
        # Include the complete via land and 0.10 mm mask-opening separation.
        pos = v.GetPosition()
        import math
        radius = k.ToMM(v.GetWidth(k.F_Cu))/2 + .1
        area = polygon([(pos.x/1e6 + radius*math.cos(i*math.tau/128),
                         pos.y/1e6 + radius*math.sin(i*math.tau/128)) for i in range(128)])
        for ref, p in exposed_pads:
            overlap = overlap_area(p.GetEffectivePolygon(k.F_Cu), area)
            if overlap > 1e-8:
                intersections.append({'via': v.m_Uuid.AsString(), 'reference': ref,
                                      'pad': p.GetNumber(), 'overlap_mm2': round(overlap, 8)})
    checks['open_vias_separated_from_solderable_smd_pads'] = not intersections
    u3 = fps['U3']
    epad = [p for p in u3.Pads() if p.GetNumber() == '19']
    checks['esp32_centre_pad_has_no_holes_mask_or_paste'] = len(epad) == 1 and all(
        p.GetDrillSize().x == 0 and not p.IsOnLayer(k.F_Mask) and not p.IsOnLayer(k.F_Paste)
        and p.GetNetname() == 'GND' for p in epad) and not any(
            p.GetNumber() == '' and p.IsOnLayer(k.F_Paste) for p in u3.Pads())
    checks['esp32_required_ground_pin_retained'] = any(
        p.GetNumber() == '9' and p.GetNetname() == 'GND' and p.IsOnLayer(k.F_Mask)
        for p in u3.Pads())
    slots = [p for p in fps['J1'].Pads() if p.GetNumber() == 'SH']
    checks['usb_plated_slots_0_70_with_0_30_rings'] = len(slots) == 4 and all(
        p.GetDrillSize().x == k.FromMM(.7) and
        min(p.GetSize().x-p.GetDrillSize().x, p.GetSize().y-p.GetDrillSize().y) >= k.FromMM(.6)
        for p in slots)
    setup = child(tree, 'setup')
    checks['no_filling_capping_plugging_or_covering'] = all(
        not children(setup, tag) or child(setup, tag)[1] == 'no' for tag in ['filling', 'capping']) and all(
        not children(setup, tag) or all(child(child(setup, tag), side)[1] == 'no' for side in ['front','back'])
        for tag in ['plugging', 'covering'])
    checks['open_vias_in_mask_data'] = all(child(child(setup, 'tenting'), s)[1] == 'no' for s in ['front','back'])
    stack = child(setup, 'stackup')
    checks['green_mask_enig_no_custom_dielectric_constraint'] = child(stack,'copper_finish')[1] == '"ENIG"' and child(stack,'dielectric_constraints')[1] == 'no' and all(
        child(layer,'color')[1] == '"Green"' for layer in children(stack,'layer') if uq(layer[1]) in ['F.Mask','B.Mask'])
    drc = json.loads(drc_path.read_text())
    checks['native_drc_zero_errors'] = not any(v['severity'] == 'error' for v in drc['violations'])
    checks['native_drc_zero_unconnected'] = not drc['unconnected_items']
    checks['native_schematic_parity_clean'] = not drc.get('schematic_parity', [])
    checks['no_dangling_copper'] = not any(v['type'] in ['track_dangling','via_dangling'] for v in drc['violations'])
    audit_path = ROOT/'docs/pcb/standard-silk-audit.json'
    checks['silk_edits_preserve_all_other_footprint_geometry'] = False
    if audit_path.exists():
        audit = json.loads(audit_path.read_text())
        checks['silk_edits_preserve_all_other_footprint_geometry'] = (
            footprint_geometry_hashes(tree) == audit['geometry_before_silk_clipping'])
    return {'passed': all(checks.values()), 'checks': checks,
            'board_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'drc_sha256': hashlib.sha256(drc_path.read_bytes()).hexdigest(),
            'ribbon_access_mm': ACCESS, 'ribbon_access_width_height_mm': [17.7,5.0],
            'intruders': {r:a for r,a in intruders.items() if a},
            'smd_via_mask_conflicts': intersections, 'routing_vias': len(vias),
            'scope': 'Geometry and native-rule acceptance; supplier CAM acceptance and physical performance are separate.'}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--board', type=Path, default=ROOT/'nucula-v2.kicad_pcb')
    ap.add_argument('--drc', type=Path, default=ROOT/'docs/pcb/drc.json')
    ap.add_argument('--out', type=Path, default=ROOT/'docs/pcb/standard-fabrication-check.json')
    a = ap.parse_args()
    result = run(a.board, a.drc)
    a.out.write_text(json.dumps(result, indent=2)+'\n')
    for name, ok in result['checks'].items():
        print(('PASS ' if ok else 'FAIL ')+name)
    raise SystemExit(0 if result['passed'] else 1)
