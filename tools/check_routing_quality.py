#!/usr/bin/env python3
"""Audit routing geometry beyond KiCad connectivity/clearance DRC.

Consumes native pad polygons from export_routing_geometry.py; requires Shapely 2.
Checks exact centreline joins, substantial pad/via entry and octilinear routing.
This is a geometric audit, not a signal-integrity or manufacturing-yield model.
"""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
TOL = .002  # mm; accommodates CAD polygon/coordinate approximation.


def copper_shape(item):
    if item['type'] == 'pad':
        return unary_union([Polygon(p).buffer(0) for p in item['poly'] if len(p) > 2])
    if item['type'] == 'via':
        return Point(item['xy']).buffer(item['w'] / 2, quad_segs=32)
    return LineString([item['start'], item['end']]).buffer(item['w'] / 2, quad_segs=24)


def pad_core(item, shape, width):
    """A full-width entry where the land is wide enough; its core otherwise."""
    centre = Point(item['xy'])
    radius = shape.boundary.distance(centre) if shape.covers(centre) else .1
    inset = max(0, min(width / 2, radius - TOL))
    return shape.buffer(-inset + TOL)


class UnionFind:
    def __init__(self, size):
        self.parents = list(range(size))

    def root(self, i):
        while self.parents[i] != i:
            self.parents[i] = self.parents[self.parents[i]]
            i = self.parents[i]
        return i

    def join(self, a, b):
        self.parents[self.root(a)] = self.root(b)


def audit(data):
    items = data['items']
    shapes = [copper_shape(q) for q in items]
    lines = [LineString([q['start'], q['end']]) if q['type'] == 'track' else None for q in items]
    index = STRtree(shapes)
    physical, robust = UnionFind(len(items)), UnionFind(len(items))
    same = collections.defaultdict(list)
    for i, q in enumerate(items):
        for j in index.query(shapes[i].buffer(TOL)):
            j = int(j)
            t = items[j]
            if j <= i or q['net'] != t['net'] or not set(q['layers']) & set(t['layers']):
                continue
            if shapes[i].distance(shapes[j]) > TOL:
                continue
            same[i].append(j)
            same[j].append(i)
            physical.join(i, j)
            if lines[i] is not None and lines[j] is not None:
                strong = lines[i].distance(lines[j]) <= TOL
            elif lines[i] is not None:
                strong = lines[i].distance(pad_core(t, shapes[j], q['w'])) <= TOL
            elif lines[j] is not None:
                strong = lines[j].distance(pad_core(q, shapes[i], t['w'])) <= TOL
            else:
                # Native footprint lands may intentionally overlap each other.
                strong = True
            if strong:
                robust.join(i, j)

    weak_groups = collections.defaultdict(set)
    for i in range(len(items)):
        weak_groups[physical.root(i)].add(robust.root(i))
    weak_bridges = []
    for group, roots in weak_groups.items():
        if len(roots) > 1:
            weak_bridges.append({'net': items[group]['net'],
                                 'robust_subgroups': len(roots),
                                 'items': [q['id'] for i, q in enumerate(items) if physical.root(i) == group]})

    non45, shallow, short, duplicates, acute = [], [], [], [], []
    seen = set()
    vertices = collections.defaultdict(list)
    for i, q in enumerate(items):
        if q['type'] != 'track':
            continue
        a, b = q['start'], q['end']
        dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
        length = math.hypot(dx, dy)
        if min(dx, dy, abs(dx - dy) / math.sqrt(2)) > TOL:
            non45.append(q['id'])
        key = (q['net'], tuple(q['layers']), tuple(sorted([tuple(a), tuple(b)])), q['w'])
        if key in seen:
            duplicates.append(q['id'])
        seen.add(key)
        for end, xy in enumerate([a, b]):
            p = Point(xy)
            vertices[(q['net'], q['layers'][0], tuple(xy))].append(i)
            full = any(lines[j].distance(p) <= TOL if lines[j] is not None else
                       pad_core(items[j], shapes[j], q['w']).covers(p) for j in same[i])
            if not full:
                shallow.append({'id': q['id'], 'end': end, 'xy': xy, 'net': q['net']})
        if length < .2:
            lands = unary_union([shapes[j] for j in same[i] if lines[j] is None])
            exposed = lines[i].difference(lands).length
            if exposed > .01:
                short.append({'id': q['id'], 'net': q['net'], 'layer': q['layers'][0],
                              'start': a, 'end': b, 'length_mm': round(length, 6),
                              'exposed_length_mm': round(exposed, 6)})

    for (net, layer, xy), ids in vertices.items():
        if len(ids) != 2:
            continue
        p = Point(xy)
        neighbours = set(same[ids[0]]) | set(same[ids[1]])
        if any(lines[j] is None and shapes[j].covers(p) for j in neighbours):
            continue
        if any(j not in ids and lines[j] is not None and lines[j].distance(p) <= TOL for j in neighbours):
            continue  # A T/Y branch, not a two-segment return bend.
        vectors = []
        for i in ids:
            q = items[i]
            far = q['end'] if tuple(q['start']) == xy else q['start']
            vectors.append((far[0] - xy[0], far[1] - xy[1]))
        u, v = vectors
        cosine = (u[0] * v[0] + u[1] * v[1]) / (math.hypot(*u) * math.hypot(*v))
        angle = math.degrees(math.acos(max(-1, min(1, cosine))))
        if angle < 89.9:
            acute.append({'net': net, 'layer': layer, 'xy': xy, 'angle_degrees': round(angle, 3)})

    checks = {'tracks_follow_45_degree_convention': not non45,
              'all_track_ends_have_full_entries_or_centreline_joins': not shallow,
              'no_connections_depend_only_on_edge_overlap': not weak_bridges,
              'no_duplicate_tracks': not duplicates,
              'no_acute_two_segment_return_bends': not acute,
              'no_exposed_segments_shorter_than_0_20_mm': not short}
    return {'passed': all(checks.values()), 'checks': checks,
            'source_board_sha256': data.get('source_board_sha256'),
            'coordinate_tolerance_mm': TOL,
            'statistics': {'tracks': sum(q['type'] == 'track' for q in items),
                           'vias': sum(q['type'] == 'via' for q in items),
                           'non45_tracks': len(non45), 'shallow_ends': len(shallow),
                           'weak_connection_groups': len(weak_bridges),
                           'duplicate_tracks': len(duplicates), 'acute_bends': len(acute),
                           'exposed_short_segments': len(short)},
            'non45': non45, 'shallow_ends': shallow, 'weak_connections': weak_bridges,
            'duplicates': duplicates, 'acute_bends': acute, 'exposed_short_segments': short,
            'scope': 'Copper geometry; native DRC additionally checks clearances, filled zones and netlist parity. No SI, RF, thermal or yield guarantee.'}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--geometry', type=Path, default=ROOT/'docs/pcb/routing-geometry.json')
    ap.add_argument('--board', type=Path, default=ROOT/'nucula-v2.kicad_pcb')
    ap.add_argument('--out', type=Path, default=ROOT/'docs/pcb/routing-quality.json')
    args = ap.parse_args()
    data = json.loads(args.geometry.read_text())
    assert data['source_board_sha256'] == hashlib.sha256(args.board.read_bytes()).hexdigest(), 'Stale geometry export'
    result = audit(data)
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result['statistics']))
    for name, ok in result['checks'].items():
        print(('PASS ' if ok else 'FAIL ')+name)
    raise SystemExit(0 if result['passed'] else 1)
