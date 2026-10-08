#!/usr/bin/env python3
"""Check M2 drills, hardware seating areas and isolation on the saved PCB.

Run with KiCad's pcbnew Python after native DRC and zone refill. This checks
geometry for hardware up to 5 mm diameter, not enclosure fit or screw torque.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import pcbnew as k
from check_pcb_layout import LAYERS, polygon, overlap_area

ROOT = Path(__file__).resolve().parents[1]
CENTERS = {'H1': (53.5, 53.5), 'H2': (106.5, 53.5),
           'H3': (53.5, 120.0), 'H4': (106.5, 120.0),
           'H5': (53.5, 156.5), 'H6': (106.5, 156.5)}
FOOTPRINT = 'Nucula_Project:MountingHole_2.2mm_M2_5.5mm_Keepout'


def circle(x, y, radius):
    return polygon([(x + radius * math.cos(i * math.tau / 256),
                     y + radius * math.sin(i * math.tau / 256)) for i in range(256)])


def audit(path=ROOT / 'nucula-v2.kicad_pcb'):
    board = k.LoadBoard(str(path))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    checks = {}
    checks['exactly_six_M2_holes'] = {r for r in fps if r.startswith('H')} == set(CENTERS)
    checks['corner_positions_locked'] = all(r in fps and fps[r].IsLocked() and
        (k.ToMM(fps[r].GetPosition().x), k.ToMM(fps[r].GetPosition().y)) == xy
        for r, xy in CENTERS.items())
    holes = [fps[r] for r in CENTERS if r in fps]
    checks['six_2_2mm_NPTH_no_plating_no_net_no_paste'] = len(holes) == 6 and all(
        len(list(f.Pads())) == 1 and all(
            p.GetAttribute() == k.PAD_ATTRIB_NPTH and p.GetShape() == k.PAD_SHAPE_CIRCLE
            and p.GetDrillSize().x == p.GetDrillSize().y == k.FromMM(2.2)
            and p.GetSize().x == p.GetSize().y == k.FromMM(2.2)
            and not p.GetNetname() and not p.IsOnLayer(k.F_Paste) and not p.IsOnLayer(k.B_Paste)
            for p in f.Pads()) for f in holes)
    checks['board_only_excluded_from_BOM_and_placement'] = all(
        f.GetAttributes() & k.FP_BOARD_ONLY and f.IsExcludedFromBOM()
        and f.IsExcludedFromPosFiles() and f.GetFPIDAsString() == FOOTPRINT for f in holes)
    outline = k.SHAPE_POLY_SET()
    checks['board_outline_closed'] = board.GetBoardPolygonOutlines(outline, False)
    offboard, intruders, copper, bad_rules = [], [], [], []
    for ref, (x, y) in CENTERS.items():
        if ref not in fps:
            continue
        area = circle(x, y, 2.75)
        outside = k.SHAPE_POLY_SET(area)
        outside.BooleanSubtract(outline)
        if outside.Area() > 1e4:
            offboard.append(ref)
        rules = list(fps[ref].Zones())
        if len(rules) != 1 or not all(
            z.GetIsRuleArea() and all(z.IsOnLayer(layer) for layer in LAYERS)
            and z.GetDoNotAllowTracks() and z.GetDoNotAllowVias()
            and z.GetDoNotAllowFootprints() and z.GetDoNotAllowZoneFills()
            and abs(overlap_area(z.Outline(), area) - area.Area() / 1e12) < 1e-6
            for z in rules):
            bad_rules.append(ref)
        # The rule allows its own NPTH pad. Independently reject every other
        # pad, including pads protruding beyond a component's courtyard.
        for other, f in fps.items():
            if other == ref:
                continue
            if any(overlap_area(f.GetCourtyard(layer), area) > 1e-7
                   for layer in [k.F_CrtYd, k.B_CrtYd]):
                intruders.append([ref, other, 'courtyard'])
            for p in f.Pads():
                if any(p.IsOnLayer(layer) and overlap_area(p.GetEffectivePolygon(layer), area) > 1e-7
                       for layer in LAYERS):
                    intruders.append([ref, other, 'pad ' + p.GetNumber()])
        for t in board.GetTracks():
            pos = k.VECTOR2I(k.FromMM(x), k.FromMM(y))
            if t.GetEffectiveShape(t.GetLayer()).Collide(pos, k.FromMM(2.75)):
                copper.append([ref, t.m_Uuid.AsString(), t.GetNetname()])
        for z in board.Zones():
            if not z.GetIsRuleArea():
                for layer in LAYERS:
                    if z.IsOnLayer(layer) and overlap_area(z.GetFilledPolysList(layer), area) > 1e-7:
                        copper.append([ref, z.GetZoneName(), k.LayerName(layer)])
    checks['5mm_hardware_plus_0_25mm_margin_fits_board'] = not offboard
    checks['all_four_copper_layers_have_hardware_keepouts'] = not bad_rules
    checks['no_other_pads_or_component_courtyards_in_hardware_area'] = not intruders
    checks['no_tracks_vias_or_filled_copper_in_hardware_area'] = not copper
    checks['R16_value_and_pad_nets_preserved'] = fps['R16'].GetValue() == '470k' and {
        p.GetNumber(): p.GetNetname().rsplit('/', 1)[-1] for p in fps['R16'].Pads()
    } == {'1': 'VBAT_ADC', '2': 'GND'}
    return dict(passed=all(checks.values()), checks=checks, centers_mm=CENTERS,
                drill_mm=2.2, hardware_max_diameter_mm=5.0, keepout_diameter_mm=5.5,
                main_hole_spacing_mm=[53, 66.5], keyboard_hole_spacing_mm=53,
                board_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                intruders=intruders, copper_intruders=copper, offboard=offboard,
                invalid_keepouts=bad_rules, hardware_tested=False,
                scope='Drill and seating geometry; verify actual standoffs, screw length, enclosure and RF operation on hardware.')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--board', type=Path, default=ROOT / 'nucula-v2.kicad_pcb')
    ap.add_argument('--out', type=Path, default=ROOT / 'docs/pcb/mounting-holes-check.json')
    args = ap.parse_args()
    result = audit(args.board)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    for name, ok in result['checks'].items():
        print(('PASS ' if ok else 'FAIL ') + name)
    raise SystemExit(0 if result['passed'] else 1)
