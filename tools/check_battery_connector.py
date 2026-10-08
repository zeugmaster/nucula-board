#!/usr/bin/env python3
"""Check J2 side entry and J6 hand-solder battery lands and polarity.

Run with KiCad's pcbnew-enabled Python. Dimensions are from JST eSH pages 1/3;
this does not qualify the enclosure or the polarity of a purchased battery lead.
"""
import argparse
import hashlib
import json
from pathlib import Path

import pcbnew as k
from check_pcb_layout import rectangle, overlap_area
from kicad_sexpr import parse, children, child, uq

ROOT = Path(__file__).resolve().parents[1]
NAME = 'JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal'
MPN = 'SM02B-SRSS-TB(LF)(SN)'
CODE = 'C160402'
WIRE_PADS = 'Battery_Lead_SolderPads_2x2.2x2.5mm_P3.4mm'


def properties(node):
    return {uq(p[1]): uq(p[2]) for p in children(node, 'property')}


def lands(node):
    return sorted((uq(p[1]), p[2], p[3],
                   tuple(map(float, child(p, 'at')[1:3])),
                   tuple(map(float, child(p, 'size')[1:])),
                   tuple(sorted(uq(x) for x in child(p, 'layers')[1:])),
                   float(child(p, 'roundrect_rratio')[1]))
                  for p in children(node, 'pad'))


def audit(path=ROOT / 'nucula-v2.kicad_pcb'):
    board = k.LoadBoard(str(path))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    fp = fps['J2']
    tree = parse(path.read_text())
    placed = next(f for f in children(tree, 'footprint') if properties(f)['Reference'] == 'J2')
    library_path = ROOT / 'libraries/Nucula_Project.pretty' / (NAME + '.kicad_mod')
    lib = parse(library_path.read_text())
    sch = parse((ROOT / 'power-mcu.kicad_sch').read_text())
    symbol = next(s for s in children(sch, 'symbol') if properties(s)['Reference'] == 'J2')
    checks = {}
    checks['exact_side_entry_part_in_schematic_and_board'] = all(
        properties(s)['MPN'] == MPN and properties(s)['LCSC'] == CODE
        and properties(s)['Manufacturer'] == 'JST' for s in [placed, symbol])
    checks['horizontal_footprint_selected'] = (
        uq(placed[1]) == properties(symbol)['Footprint'] == 'Nucula_Project:' + NAME)
    checks['manufacturer_lands_preserved_on_board'] = lands(placed) == lands(lib)
    checks['horizontal_SH_model_assigned'] = (children(placed, 'model') == children(lib, 'model') and len(children(lib, 'model')) == 1)
    # Independent drawing dimensions, including circuit 1 at local X=-0.5.
    expected = [('1', (-.5, -2.), (.6, 1.55)), ('2', (.5, -2.), (.6, 1.55)),
                ('MP', (-1.8, 1.875), (1.2, 1.8)), ('MP', (1.8, 1.875), (1.2, 1.8))]
    checks['jst_side_entry_land_dimensions_and_numbering'] = (
        [(p[0], p[3], p[4]) for p in lands(lib)] == expected)
    checks['four_smd_lands_with_mask_and_paste_no_holes'] = len(list(fp.Pads())) == 4 and all(
        p.GetAttribute() == k.PAD_ATTRIB_SMD and p.GetDrillSize().x == 0
        and p.IsOnLayer(k.F_Cu) and p.IsOnLayer(k.F_Mask) and p.IsOnLayer(k.F_Paste)
        for p in fp.Pads())
    def outlines(node, layer):
        return sorted((tuple(map(float, child(g, 'start')[1:])),
                       tuple(map(float, child(g, 'end')[1:])),
                       float(child(child(g, 'stroke'), 'width')[1]))
                      for g in children(node, 'fp_line') if uq(child(g, 'layer')[1]) == layer)
    checks['body_and_courtyard_match_library'] = all(
        outlines(placed, layer) == outlines(lib, layer) for layer in ['F.Fab', 'F.CrtYd'])
    pos = [round(k.ToMM(fp.GetPosition().x), 6), round(k.ToMM(fp.GetPosition().y), 6),
           fp.GetOrientationDegrees()]
    checks['locked_socket_faces_left_edge'] = pos == [57.7, 100.9, -90.] and fp.IsLocked()
    pads = {p.GetNumber(): p for p in fp.Pads() if p.GetNumber() in ['1', '2']}
    checks['pin_1_positive_pin_2_ground'] = (pads['1'].GetNetname().endswith('/VBAT')
                                           and pads['2'].GetNetname() == 'GND')
    checks['physical_polarity_matches_drawing'] = all(
        abs(k.ToMM(pads[n].GetPosition().x) - 59.7) < 1e-6 and
        abs(k.ToMM(pads[n].GetPosition().y) - y) < 1e-6 for n, y in [('1', 100.4), ('2', 101.4)])
    checks['mounting_tabs_have_no_net'] = all(not p.GetNetname() for p in fp.Pads() if p.GetNumber() == 'MP')
    approach_bounds = [50., 98., 55.125, 103.8]
    approach = rectangle(approach_bounds)
    intruders = {ref: overlap_area(f.GetCourtyard(k.F_CrtYd), approach)
                 for ref, f in fps.items() if ref != 'J2' and f.GetLayer() == k.F_Cu}
    checks['left_edge_plug_approach_has_no_components'] = not any(intruders.values())
    outline = k.SHAPE_POLY_SET()
    assert board.GetBoardPolygonOutlines(outline, False)
    # Independent nominal dimensions for the cable notch. Both mouth shoulders
    # and both inner corners are R0.5; the overall mouth is 5 mm, depth 3 mm.
    def xy(point):
        return tuple(round(k.ToMM(v), 5) for v in (point.x, point.y))
    notch_edges = [g for g in board.GetDrawings() if g.GetLayer() == k.Edge_Cuts
                   and all(49.99 <= x <= 53.01 and 98.39 <= y <= 103.41
                           for x, y in [xy(g.GetStart()), xy(g.GetEnd())])]
    straight = {tuple(sorted([xy(g.GetStart()), xy(g.GetEnd())]))
                for g in notch_edges if g.GetShape() == k.SHAPE_T_SEGMENT}
    checks['cable_notch_5mm_mouth_3mm_depth'] = straight == {
        ((50.5, 98.9), (52.5, 98.9)), ((53., 99.4), (53., 102.4)),
        ((50.5, 102.9), (52.5, 102.9))}
    arcs = [g for g in notch_edges if g.GetShape() == k.SHAPE_T_ARC]
    checks['cable_notch_four_R0_5_tangent_corners'] = len(arcs) == 4 and {
        tuple(sorted([xy(g.GetStart()), xy(g.GetEnd())])) for g in arcs} == {
        ((50., 98.4), (50.5, 98.9)), ((52.5, 98.9), (53., 99.4)),
        ((52.5, 102.9), (53., 102.4)), ((50., 103.4), (50.5, 102.9))} and all(
            abs(k.ToMM(g.GetRadius()) - .5) < .001 and
            abs(abs(g.GetArcAngle().AsDegrees()) - 90) < .1 for g in arcs)
    # Check the cut is removed material, with the deepest edge at X=53.
    checks['cable_notch_is_open_removed_material'] = (
        overlap_area(outline, rectangle([50., 99.4, 53., 102.4])) < 1e-6 and
        abs(overlap_area(outline, rectangle([53., 99.4, 54., 102.4])) - 3.) < 1e-6)
    court = k.SHAPE_POLY_SET(fp.GetCourtyard(k.F_CrtYd))
    court.BooleanSubtract(outline)
    checks['entire_connector_courtyard_on_board'] = court.Area() == 0
    stock = json.loads((ROOT / 'docs/assembly/jlc-stock-snapshot.json').read_text())['parts'][CODE]
    checks['catalogue_identifies_right_angle_smt_part'] = (
        stock['componentModelEn'] == MPN and stock['componentBrandEn'] == 'JST'
        and 'Right Angle' in stock['componentSpecificationEn'] and stock['assemblyMode'] == 'smtWeld')
    wire_fp = fps['J6']
    wire_placed = next(f for f in children(tree, 'footprint') if properties(f)['Reference'] == 'J6')
    wire_lib_path = ROOT / 'libraries/Nucula_Project.pretty' / (WIRE_PADS + '.kicad_mod')
    wire_lib = parse(wire_lib_path.read_text())
    wire_symbol = next(s for s in children(sch, 'symbol') if properties(s)['Reference'] == 'J6')
    checks['wire_pads_same_library_in_schematic_and_board'] = (
        uq(wire_placed[1]) == properties(wire_symbol)['Footprint'] == 'Nucula_Project:' + WIRE_PADS
        and lands(wire_placed) == lands(wire_lib))
    wp = {p.GetNumber(): p for p in wire_fp.Pads()}
    checks['wire_pads_parallel_with_J2_correct_polarity'] = set(wp) == {'1', '2'} and all(
        wp[n].GetNetname() == pads[n].GetNetname() for n in wp)
    checks['wire_pads_large_exposed_top_copper_without_paste_or_holes'] = len(wp) == 2 and all(
        p.GetAttribute() == k.PAD_ATTRIB_SMD and p.GetDrillSize().x == 0
        and (p.GetSize().x, p.GetSize().y) == (k.FromMM(2.2), k.FromMM(2.5))
        and set(k.LayerName(layer) for layer in p.GetLayerSet().Seq()) == {'F.Cu', 'F.Mask'}
        for p in wp.values())
    checks['ground_wire_pad_thermal_relief_for_hand_soldering'] = all(
        all(float(child(pad, tag)[1]) == value for tag, value in [
            ('zone_connect', 1), ('thermal_gap', .25), ('thermal_bridge_width', .4)])
        for node in [wire_placed, wire_lib]
        for pad in children(node, 'pad') if uq(pad[1]) == '2')
    checks['wire_pads_locked_above_connector'] = wire_fp.IsLocked() and all(
        (round(k.ToMM(wp[n].GetPosition().x), 6), round(k.ToMM(wp[n].GetPosition().y), 6)) == xy
        for n, xy in [('1', (56.1, 96.)), ('2', (52.7, 96.))])
    checks['wire_pads_marked_BAT_positive_and_GND'] = {
        uq(g[2]) for g in children(wire_placed, 'fp_text') if uq(child(g, 'layer')[1]) == 'F.SilkS'
    } == {'BAT+', 'GND'}
    checks['wire_pads_not_a_purchased_or_placed_component'] = (
        child(wire_symbol, 'in_bom')[1] == 'no' and wire_fp.IsExcludedFromBOM()
        and wire_fp.IsExcludedFromPosFiles())
    wire_court = wire_fp.GetCourtyard(k.F_CrtYd)
    outside = k.SHAPE_POLY_SET(wire_court)
    outside.BooleanSubtract(outline)
    checks['wire_pads_on_board_and_clear_of_other_components'] = outside.Area() == 0 and all(
        overlap_area(wire_court, other.GetCourtyard(k.F_CrtYd)) == 0
        for ref, other in fps.items() if ref != 'J6' and other.GetLayer() == k.F_Cu)
    return dict(passed=all(checks.values()), checks=checks,
                board_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                footprint_sha256=hashlib.sha256(library_path.read_bytes()).hexdigest(),
                wire_pad_footprint_sha256=hashlib.sha256(wire_lib_path.read_bytes()).hexdigest(),
                wire_pads=dict(reference='J6', size_mm=[2.2, 2.5], pitch_mm=3.4,
                               ground_thermal_gap_mm=.25, ground_thermal_spoke_width_mm=.4,
                               positive_xy_mm=[56.1, 96.], ground_xy_mm=[52.7, 96.],
                               paste=False, connection='Parallel with J2; use one battery connection at a time'),
                part=MPN, lcsc=CODE, height_mm=2.95, mated_height_mm=2.95,
                mating_housing='SHR-02V-S-B', pitch_mm=1., rated_current_A_at_AWG28=1.,
                peak_current_assumption='User accepts intermittent excursions above 1 A; no new current limiter or battery operating restriction. Above-rating pulses are not manufacturer-qualified by this audit.',
                placement_mm_deg=pos, opening='Left edge (-X); cable parallel to PCB',
                approach_bounds_mm=approach_bounds,
                cable_notch=dict(bounds_mm=[50., 98.4, 53., 103.4],
                                 overall_mouth_mm=5., straight_channel_width_mm=4.,
                                 depth_mm=3., inner_and_outer_radius_mm=.5,
                                 socket_move_inward_mm=4., mating_face_x_mm=55.125,
                                 mating_face_to_notch_back_mm=2.125),
                intruding_courtyards={r: a for r, a in intruders.items() if a},
                source='https://www.jst-mfg.com/product/pdf/eng/eSH.pdf',
                limitations='KiCad SH STEP model assigned. Enclosure/cable bend room, supplied SH lead polarity and intermittent-peak performance need physical confirmation.')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--board', type=Path, default=ROOT / 'nucula-v2.kicad_pcb')
    ap.add_argument('--out', type=Path, default=ROOT / 'docs/assembly/battery-connector-check.json')
    args = ap.parse_args()
    result = audit(args.board)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    for name, ok in result['checks'].items():
        print(('PASS ' if ok else 'FAIL ') + name)
    raise SystemExit(0 if result['passed'] else 1)
