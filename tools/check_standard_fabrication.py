#!/usr/bin/env python3
"""Audit rev-A-compatible fabrication and the OLED ribbon access area.

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
    from check_nfc_rev_a import audit as nfc_audit, BASELINE
    from zipfile import ZipFile
    nfc = nfc_audit(path)
    assert nfc['passed'], 'NFC must match the independently pinned rev-A baseline'
    board = k.LoadBoard(str(path))
    tree = parse(path.read_text())
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    vias = [t for t in board.GetTracks() if isinstance(t, k.PCB_VIA)]
    checks = {}
    checks['four_copper_layers'] = board.GetCopperLayerCount() == 4
    checks['routing_vias_match_supported_filled_capped_sizes'] = all(
        (round(k.ToMM(v.GetDrillValue()), 3), round(k.ToMM(v.GetWidth(k.F_Cu)), 3)) in [(.3,.7),(.3,.6),(.2,.45)]
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
    checks['via_in_pad_confined_to_preserved_NFC'] = all(
        i['reference'] in nfc['NFC_references'] for i in intersections)
    u3 = fps['U3']
    epad = [p for p in u3.Pads() if p.GetNumber() == '49']
    checks['esp32_centre_pad_has_no_holes_mask_or_paste'] = len(epad) == 1 and all(
        p.GetDrillSize().x == 0 and not p.IsOnLayer(k.F_Mask) and not p.IsOnLayer(k.F_Paste)
        and p.GetNetname() == 'GND' for p in epad) and not any(
            p.GetNumber() == '' and p.IsOnLayer(k.F_Paste) for p in u3.Pads())
    checks['esp32_required_ground_pin_retained'] = any(
        p.GetNumber() == '1' and p.GetNetname() == 'GND' and p.IsOnLayer(k.F_Mask)
        for p in u3.Pads())
    slots = [p for p in fps['J1'].Pads() if p.GetNumber() == 'SH']
    checks['usb_plated_slots_0_70_with_0_30_rings'] = len(slots) == 4 and all(
        p.GetDrillSize().x == k.FromMM(.7) and
        min(p.GetSize().x-p.GetDrillSize().x, p.GetSize().y-p.GetDrillSize().y) >= k.FromMM(.6)
        for p in slots)
    setup = child(tree, 'setup')
    checks['rev_A_stackup_mask_and_filled_capped_process'] = nfc['checks']['submitted_stackup_and_via_process_identical']
    drc = json.loads(drc_path.read_text())
    checks['native_drc_zero_errors'] = not any(v['severity'] == 'error' for v in drc['violations'])
    checks['native_drc_zero_unconnected'] = not drc['unconnected_items']
    checks['native_schematic_parity_clean'] = not drc.get('schematic_parity', [])
    checks['no_dangling_copper'] = not any(v['type'] in ['track_dangling','via_dangling'] for v in drc['violations'])
    audit_path = ROOT/'docs/pcb/standard-silk-audit.json'
    checks['silk_edits_preserve_all_other_footprint_geometry'] = False
    if audit_path.exists():
        audit = json.loads(audit_path.read_text())
        expected = dict(audit['geometry_before_silk_clipping'])
        # Preserve the historical clipping baseline; explicitly record later
        # electrical amendments and independently check the physical mapping.
        for ref, amendment in audit.get('approved_footprint_amendments', {}).items():
            assert ref == 'DS1' and expected[ref] == amendment['from_sha256']
            from check_display_mapping import audit as display_audit
            assert display_audit(path, ROOT / 'docs/netlist.xml')['passed']
            expected[ref] = amendment['to_sha256']
        # A separate, immutable-before / explicit-after record describes the
        # USB electrical revision. Unaffected footprints must still match.
        revision_path = ROOT/'docs/pcb/usb-footprint-amendments.json'
        if revision_path.exists():
            from check_usb_backfeed import audit as usb_audit, CHANGED_REFS
            revision = json.loads(revision_path.read_text())
            assert set(revision['footprints']) == CHANGED_REFS
            assert usb_audit(path, ROOT/'docs/netlist.xml')['passed']
            for ref, amendment in revision['footprints'].items():
                assert expected.get(ref) == amendment['from_sha256'], ref
                if amendment['to_sha256'] is None:
                    expected.pop(ref)
                else:
                    expected[ref] = amendment['to_sha256']
        battery_path = ROOT/'docs/pcb/battery-footprint-amendments.json'
        if battery_path.exists():
            from check_battery_connector import audit as battery_audit
            revision = json.loads(battery_path.read_text())
            assert set(revision['footprints']) == {'J2'}
            assert battery_audit(path)['passed']
            amendment = revision['footprints']['J2']
            assert expected['J2'] == amendment['from_sha256']
            expected['J2'] = amendment['to_sha256']
        notch_path = ROOT/'docs/pcb/battery-notch-amendments.json'
        if notch_path.exists():
            revision = json.loads(notch_path.read_text())
            assert set(revision['footprints']) == {'J2'}
            from check_battery_connector import audit as battery_audit
            assert battery_audit(path)['passed']
            amendment = revision['footprints']['J2']
            assert expected['J2'] == amendment['from_sha256']
            expected['J2'] = amendment['to_sha256']
        wire_path = ROOT/'docs/pcb/battery-wire-pad-amendments.json'
        if wire_path.exists():
            from check_battery_connector import audit as battery_audit
            revision = json.loads(wire_path.read_text())
            assert set(revision['footprints']) == {'J6'} and 'J6' not in expected
            assert revision['footprints']['J6']['from_sha256'] is None
            assert battery_audit(path)['passed']
            expected['J6'] = revision['footprints']['J6']['to_sha256']
        mini_path = ROOT/'docs/pcb/mini-footprint-amendments.json'
        if mini_path.exists():
            from check_mini_module import audit as mini_audit
            revision = json.loads(mini_path.read_text())
            assert set(revision['footprints']) == {'U3', 'R12', 'R13'}
            assert mini_audit(path, ROOT/'docs/netlist.xml')['passed']
            for ref, amendment in revision['footprints'].items():
                assert expected[ref] == amendment['from_sha256'], ref
                expected[ref] = amendment['to_sha256']
        mounting_path = ROOT/'docs/pcb/mounting-footprint-amendments.json'
        if mounting_path.exists():
            from check_mounting_holes import audit as mounting_audit, CENTERS
            revision = json.loads(mounting_path.read_text())
            assert set(revision['footprints']) == set(CENTERS) | {'R16'}
            assert mounting_audit(path)['passed']
            for ref, amendment in revision['footprints'].items():
                assert expected.get(ref) == amendment['from_sha256'], ref
                expected[ref] = amendment['to_sha256']
        button_path = ROOT/'docs/pcb/button-label-amendments.json'
        if button_path.exists():
            revision = json.loads(button_path.read_text())
            assert set(revision['footprints']) == {'SW1', 'SW2'}
            for ref, amendment in revision['footprints'].items():
                assert expected[ref] == amendment['from_sha256'], ref
                expected[ref] = amendment['to_sha256']
        # User-directed restoration is checked against immutable submitted
        # source, never against a freshly blessed current-board hash.
        with ZipFile(BASELINE) as archive:
            original = footprint_geometry_hashes(parse(archive.read('nucula-v2.kicad_pcb').decode()))
        for ref in nfc['NFC_references']:
            expected[ref] = original[ref]
        checks['silk_edits_preserve_all_other_footprint_geometry'] = (
            footprint_geometry_hashes(tree) == expected)
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
