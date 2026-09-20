#!/usr/bin/env python3
"""Independently read custom-pad copper and check for opens/shorted turns.

KiCad intentionally permits same-net pad copper to overlap, so native DRC alone
cannot detect an accidentally shorted turn. Requires shapely and matplotlib.
"""
from pathlib import Path
import sys
import json
import math
from collections import Counter
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from kicad_sexpr import parse, children, child, uq


def main():
    path = ROOT / 'libraries/Nucula_Project.pretty/NFC_PCB_Loop_40x40_4T_W0.50_S0.30.kicad_mod'
    tree = parse(path.read_text())
    segments = {'F.Cu': [], 'B.Cu': []}
    pads = []
    for pad in children(tree, 'pad'):
        x, y = map(float, child(pad, 'at')[1:3])
        layers = [uq(l) for l in child(pad, 'layers')[1:]]
        if pad[3] == 'custom':
            layer = next(l for l in layers if l in segments)
            for primitive in children(child(pad, 'primitives'), 'gr_line'):
                a = tuple(round(float(v) + d, 6) for v, d in zip(child(primitive, 'start')[1:], (x, y)))
                b = tuple(round(float(v) + d, 6) for v, d in zip(child(primitive, 'end')[1:], (x, y)))
                width = float(child(primitive, 'width')[1])
                assert width == .5
                segments[layer].append((a, b, width))
        else:
            pads.append((pad, x, y, layers))
    minima = {}
    for layer, lines in segments.items():
        endpoint_counts = Counter(point for a, b, _ in lines for point in [a, b])
        assert sorted(endpoint_counts.values()).count(1) == 2, (layer, endpoint_counts)
        assert max(endpoint_counts.values()) == 2, 'Branched or shorted path'
        minimum = math.inf
        for i, (a, b, width) in enumerate(lines):
            for c, d, width2 in lines[:i]:
                if set((a, b)) & set((c, d)):
                    continue
                gap = LineString([a, b]).distance(LineString([c, d])) - (width + width2) / 2
                minimum = min(minimum, gap)
                assert gap >= .3 - 1e-6, f'{layer} unintended turn contact/clearance: {gap}'
        minima[layer] = minimum if math.isfinite(minimum) else None
        copper = unary_union([LineString([a, b]).buffer(w / 2) for a, b, w in lines])
        assert copper.geom_type == 'Polygon', f'{layer}: disconnected copper'
    # Remove only the outward terminal lead to measure the actual winding outline.
    winding = unary_union([LineString([a, b]).buffer(w / 2) for a, b, w in segments['F.Cu']
                          if min(a[1], b[1]) >= -20])
    assert all(abs(a - b) < 1e-6 for a, b in zip(winding.bounds, (-20, -20, 20, 20)))
    pth = [(x,y) for p,x,y,l in pads if p[2]=='thru_hole']
    assert len(pth)==2
    for pt in pth:
        assert any(Point(pt).distance(LineString([a,b]))<1e-8 for a,b,w in segments['B.Cu'])
    inner = min(pth, key=lambda p: abs(p[1]))
    assert any(Point(inner).distance(LineString([a,b]))<1e-8 for a,b,w in segments['F.Cu'])
    # Check hole clearance to OTHER turns (exclude the intended terminal segment).
    gaps = [Point(inner).distance(LineString([a,b]))-.4-w/2 for a,b,w in segments['F.Cu']
            if inner not in [a,b]]
    assert min(gaps) >= .15 - 1e-6
    report = {'status':'pass', 'outer_winding_copper_mm':[40,40],
              'trace_width_mm':.5, 'minimum_nonadjacent_trace_gap_mm':minima,
              'front_segments':len(segments['F.Cu']), 'back_segments':len(segments['B.Cu']),
              'plated_return_holes':2, 'each_layer_path_connected':True,
              'no_unintended_same_layer_turn_contacts':True}
    (ROOT/'docs/nfc/geometry-check.json').write_text(json.dumps(report,indent=2)+'\n')
    fig, ax=plt.subplots(figsize=(8,8),layout='constrained')
    ax.set_aspect('equal');ax.set(xlim=(-24,24),ylim=(23,-27),xlabel='x (mm)',ylabel='y (mm)')
    ax.add_patch(Rectangle((-21,-21),42,42,facecolor='#eeeeee',edgecolor='#999999',linestyle='--',alpha=.4))
    for layer,color in [('B.Cu','#2266bb'),('F.Cu','#bc5228')]:
        for i,(a,b,w) in enumerate(segments[layer]):
            ax.plot([a[0],b[0]],[a[1],b[1]],color=color,lw=2.3,solid_capstyle='round',label=layer if i==0 else None)
    for p,x,y,layers in pads:
        sx,sy=map(float,child(p,'size')[1:3])
        if p[3]=='circle':
            ax.add_patch(Circle((x,y),sx/2,facecolor='#ccab59',edgecolor='#333333',lw=.5))
            ax.add_patch(Circle((x,y),float(child(p,'drill')[1])/2,facecolor='white',edgecolor='none'))
        else:ax.add_patch(Rectangle((x-sx/2,y-sy/2),sx,sy,facecolor='#ccab59',edgecolor='#333333',lw=.5))
    ax.text(-1.5,-24,'1',ha='center');ax.text(1.5,-24,'2',ha='center')
    ax.text(0,0,'Keep all layers clear\nof planes, tracks and parts\n\nNo battery / display / metal behind coil',ha='center',va='center',color='#555555')
    ax.set_title('40 × 40 mm outer copper · four turns\n0.50 mm track · 0.30 mm gap · bottom return included')
    ax.legend(loc='lower right');ax.grid(alpha=.12)
    fig.savefig(ROOT/'docs/nfc/coil.svg');fig.savefig(ROOT/'docs/nfc/coil.png',dpi=160)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
