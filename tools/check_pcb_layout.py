#!/usr/bin/env python3
"""Check PCB placement, preserved geometry, RF symmetry and filled-copper limits.

Run with KiCad's pcbnew-enabled Python after refilling zones and running native
DRC. This supplements DRC; it does not measure impedance or RF performance.
"""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path

import pcbnew as k

from kicad_sexpr import child, children, parse, uq

ROOT = Path(__file__).resolve().parents[1]
LAYERS = [k.F_Cu, k.In1_Cu, k.In2_Cu, k.B_Cu]


def canonical(node):
    if isinstance(node, list):
        return [canonical(x) for x in node]
    if node.startswith('"'):
        return uq(node)
    try:
        return float(node)
    except ValueError:
        return node


def digest(node):
    return hashlib.sha256(json.dumps(canonical(node), sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def polygon(points):
    result = k.SHAPE_POLY_SET()
    result.NewOutline()
    for x, y in points:
        result.Append(round(x * 1e6), round(y * 1e6))
    return result


def rectangle(bounds):
    x1, y1, x2, y2 = bounds
    return polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])


def overlap_area(a, b):
    result = k.SHAPE_POLY_SET(a)
    result.BooleanIntersection(b)
    return result.Area() / 1e12


def run(board_path, constraints, drc_path):
    board = k.LoadBoard(str(board_path))
    tree = parse(board_path.read_text())
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    checks = {}
    checks["all_original_footprints_present"] = set(fps) == set(constraints["pad_nets"])
    checks["all_components_on_top"] = all(f.GetLayer() == k.F_Cu for f in fps.values())
    checks["component_values_preserved"] = all(
        fps[r].GetValue() == v for r, v in constraints["values"].items())
    checks["pad_nets_preserved"] = all(
        sorted([[p.GetNumber(), p.GetNetname()] for p in fps[r].Pads()]) == expected
        for r, expected in constraints["pad_nets"].items())
    fixed = {}
    for ref, expected in constraints["fixed_placements"].items():
        f = fps[ref]
        actual = [k.ToMM(f.GetPosition().x), k.ToMM(f.GetPosition().y),
                  f.GetOrientationDegrees()]
        fixed[ref] = {"position_rotation": actual, "unchanged": actual == expected,
                      "locked": f.IsLocked()}
    checks["fixed_placements_preserved_and_locked"] = all(
        x["unchanged"] and x["locked"] for x in fixed.values())
    antenna = next(f for f in children(tree, "footprint") if any(
        uq(p[1]) == "Reference" and uq(p[2]) == "A1" for p in children(f, "property")))
    antenna_geometry = [x for x in antenna if isinstance(x, list)
                        and x[0] in ["pad", "zone", "net_tie_pad_groups"]]
    checks["antenna_copper_and_original_rules_unchanged"] = (
        digest(antenna_geometry) == constraints["antenna_copper_and_rule_sha256"])
    edges = [x for x in tree if isinstance(x, list)
             and x[0] in ["gr_line", "gr_arc", "gr_poly"]
             and uq(child(x, "layer")[1]) == "Edge.Cuts"]
    checks["board_outline_unchanged"] = digest(edges) == constraints["edge_cuts_sha256"]
    board_outline = k.SHAPE_POLY_SET()
    assert board.GetBoardPolygonOutlines(board_outline, False)
    offboard = {}
    for ref, f in fps.items():
        if ref in constraints["fixed_placements"]:
            continue
        court = k.SHAPE_POLY_SET(f.GetCourtyard(k.F_CrtYd))
        court.BooleanSubtract(board_outline)
        offboard[ref] = round(court.Area() / 1e12, 9)
    checks["remaining_component_courtyards_inside_board"] = all(a < 1e-8 for a in offboard.values())

    aperture = rectangle(constraints["nfc_aperture_mm"])
    aperture.BooleanSubtract(rectangle([94.0, 64.85, 96.85, 70.75]))
    outside = {}
    for ref in constraints["nfc_refs"]:
        court = k.SHAPE_POLY_SET(fps[ref].GetCourtyard(k.F_CrtYd))
        court.BooleanSubtract(aperture)
        outside[ref] = round(court.Area() / 1e12, 9)
    checks["all_nfc_component_courtyards_inside_coil"] = all(a < 1e-8 for a in outside.values())
    checks["no_unrelated_component_courtyards_inside_coil"] = all(
        overlap_area(f.GetCourtyard(k.F_CrtYd), aperture) < 1e-8
        for r, f in fps.items() if r not in constraints["nfc_refs"] + ["A1"])

    mirror = 2 * constraints["mirror_y_mm"]
    symmetry = {}
    for a, b in constraints["mirrored_pairs"]:
        pa, pb = fps[a].GetPosition(), fps[b].GetPosition()
        symmetry[a + "/" + b] = pa.x == pb.x and abs(k.ToMM(pa.y + pb.y) - mirror) < 1e-6
    checks["matching_components_mirrored"] = all(symmetry.values())
    tracks = [t for t in board.GetTracks() if not isinstance(t, k.PCB_VIA)]
    vias = [t for t in board.GetTracks() if isinstance(t, k.PCB_VIA)]
    rf_symmetry = {}
    for family in ["RF_DRV", "RF_EMC", "RF_MATCH"]:
        def segments(suffix, reflect):
            out = []
            for t in tracks:
                if not t.GetNetname().endswith("/" + family + suffix):
                    continue
                ends = []
                for p in [t.GetStart(), t.GetEnd()]:
                    x, y = k.ToMM(p.x), k.ToMM(p.y)
                    ends.append((round(x, 5), round(mirror - y if reflect else y, 5)))
                out.append((tuple(sorted(ends)), t.GetLayer(), t.GetWidth()))
            return sorted(out)
        rf_symmetry[family] = segments("_P", True) == segments("_N", False)
    checks["matching_tree_copper_mirrored"] = all(rf_symmetry.values())

    exclusion = rectangle(constraints["pour_exclusion_mm"])
    fracture = rectangle([49, 121.9, 111, 126.1])
    zones = []
    for zone in board.Zones():
        if zone.GetIsRuleArea():
            continue
        for layer in LAYERS:
            if not zone.IsOnLayer(layer):
                continue
            fill = zone.GetFilledPolysList(layer)
            zones.append({"name": zone.GetZoneName(), "layer": k.LayerName(layer),
                          "net": zone.GetNetname(), "filled_area_mm2": round(fill.Area() / 1e12, 4),
                          "nfc_overlap_mm2": round(overlap_area(fill, exclusion), 9),
                          "fracture_overlap_mm2": round(overlap_area(fill, fracture), 9)})
    checks["ground_pours_on_all_four_layers"] = {z["layer"] for z in zones if z["net"] == "GND" and z["filled_area_mm2"] > 0} == {k.LayerName(l) for l in LAYERS}
    checks["no_pour_inside_or_near_nfc_on_any_layer"] = all(z["nfc_overlap_mm2"] < 1e-8 for z in zones)
    checks["no_pour_in_fracture_band"] = all(z["fracture_overlap_mm2"] < 1e-8 for z in zones)
    crossings = []
    for t in tracks:
        a, b = t.GetStart(), t.GetEnd()
        if min(a.y, b.y) < 124e6 < max(a.y, b.y):
            x = (a.x + (b.x - a.x) * (124e6 - a.y) / (b.y - a.y)) / 1e6
            crossings.append([round(x, 6), t.GetNetname(), k.LayerName(t.GetLayer()), k.ToMM(t.GetWidth())])
    crossings.sort()
    expected = [[79 + i * .5, net, "F.Cu", .2] for i, net in enumerate(
        ["/+3V3", "GND", "/I2C_SDA", "/I2C_SCL", "/KEY_INT_N"])]
    checks["five_original_breakaway_crossings_preserved"] = crossings == expected
    checks["no_vias_in_fracture_band"] = all(not 121.9 < k.ToMM(v.GetPosition().y) < 126.1 for v in vias)
    widths = {}
    for t in tracks:
        widths.setdefault(t.GetNetname(), collections.Counter())[str(round(k.ToMM(t.GetWidth()), 4))] += k.ToMM(t.GetLength())
    widths = {net: {w: round(length, 4) for w, length in ws.items()} for net, ws in widths.items()}
    usb_lengths = {sign: round(sum(k.ToMM(t.GetLength()) for t in tracks if t.GetNetname().endswith("/USB_ESD_D" + sign)), 4) for sign in ["-", "+"]}
    checks["usb_esd_to_series_resistor_skew_below_0_5mm"] = abs(usb_lengths["+"] - usb_lengths["-"]) < .5
    reference = k.SHAPE_POLY_SET()
    for zone in board.Zones():
        if not zone.GetIsRuleArea() and zone.IsOnLayer(k.In2_Cu) and zone.GetNetname() == "GND":
            reference.BooleanAdd(zone.GetFilledPolysList(k.In2_Cu))
    usb_vias = [v.GetPosition() for v in vias if "/USB_ESD_D" in v.GetNetname()]
    missing_reference = []
    reference_samples = 0
    for t in tracks:
        if t.GetLayer() != k.B_Cu or "/USB_ESD_D" not in t.GetNetname():
            continue
        a, b = t.GetStart(), t.GetEnd()
        length = t.GetLength()
        if not length:
            continue
        nx, ny = -(b.y - a.y) / length, (b.x - a.x) / length
        count = max(1, math.ceil(length / 100000))
        for i in range(count + 1):
            for offset in [-t.GetWidth() / 2, 0, t.GetWidth() / 2]:
                x = round(a.x + (b.x - a.x) * i / count + nx * offset)
                y = round(a.y + (b.y - a.y) * i / count + ny * offset)
                # The signal via's antipad is an intentional local reference opening.
                if any(math.hypot(x - p.x, y - p.y) <= 600000 for p in usb_vias):
                    continue
                reference_samples += 1
                if not reference.Contains(k.VECTOR2I(x, y)):
                    missing_reference.append([x / 1e6, y / 1e6])
    checks["usb_has_in2_ground_beneath_both_trace_edges"] = not missing_reference
    drc = json.loads(drc_path.read_text()) if drc_path else None
    if drc is not None:
        checks["native_drc_zero_errors"] = not any(v["severity"] == "error" for v in drc["violations"])
        checks["native_drc_zero_unconnected"] = not drc["unconnected_items"]
        checks["native_drc_no_new_warning_types"] = all(v["type"] == "silk_edge_clearance" for v in drc["violations"])
        checks["native_report_has_no_schematic_parity_issues"] = not drc.get("schematic_parity", [])
    return {"board": board_path.name, "checks": checks, "passed": all(checks.values()),
            "footprints": len(fps), "tracks": len(tracks), "vias": len(vias),
            "fixed_placements": fixed, "nfc_courtyard_outside_area_mm2": outside,
            "matching_component_symmetry": symmetry, "matching_copper_symmetry": rf_symmetry,
            "ground_pours": zones, "breakaway_crossings": crossings,
            "usb_esd_to_series_resistor_lengths_mm": usb_lengths,
            "usb_ground_reference": {"samples": reference_samples, "missing": missing_reference,
                                     "via_antipad_exemption_radius_mm": .6},
            "track_widths_and_total_lengths_mm": widths}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", type=Path, default=ROOT / "nucula-v2.kicad_pcb")
    parser.add_argument("--drc", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/pcb/layout-check.json")
    args = parser.parse_args()
    report = run(args.board, json.loads((ROOT / "docs/pcb/constraints.json").read_text()), args.drc)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    for name, passed in report["checks"].items():
        print(("PASS " if passed else "FAIL ") + name)
    raise SystemExit(0 if report["passed"] else 1)
