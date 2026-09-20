#!/usr/bin/env python3
"""Check the inside-feed copper; --native also exercises KiCad DRC on fixtures.

Default: Python with shapely/matplotlib. --native: KiCad Python with pcbnew.
Fixtures live in a temporary directory, never in the production PCB/coupon.
"""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from kicad_sexpr import parse, children, child, uq
from generate_inside_feed import NAME

LIB = ROOT / 'libraries/Nucula_Project.pretty'
OUT = ROOT / 'docs/nfc/inside-feed'


def geometry_check():
    from shapely.geometry import LineString, Point
    from shapely.ops import unary_union
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle, Polygon as PatchPolygon

    tree = parse((LIB / (NAME + '.kicad_mod')).read_text())
    segments = {'F.Cu': [], 'B.Cu': []}
    pads = children(tree, 'pad')
    for pad in pads:
        if pad[3] != 'custom':
            continue
        origin = tuple(map(float, child(pad, 'at')[1:3]))
        layer = uq(child(pad, 'layers')[1])
        for line in children(child(pad, 'primitives'), 'gr_line'):
            pts = [tuple(round(float(v) + off, 6) for v, off in zip(child(line, key)[1:3], origin))
                   for key in ['start', 'end']]
            assert float(child(line, 'width')[1]) == .5
            segments[layer].append(tuple(pts))
    minima = {}
    for layer, lines in segments.items():
        degrees = Counter(p for line in lines for p in line)
        assert list(degrees.values()).count(1) == 2 and max(degrees.values()) <= 2
        gaps = [LineString(a).distance(LineString(b)) - .5 for i, a in enumerate(lines)
                for b in lines[:i] if not set(a) & set(b)]
        assert not gaps or min(gaps) >= .3 - 1e-6, (layer, min(gaps))
        minima[layer] = min(gaps) if gaps else None
        assert unary_union([LineString(line).buffer(.25) for line in lines]).geom_type == 'Polygon'
    # Compare every winding segment with the original, independently parsed copper.
    old = parse((LIB / (NAME.removesuffix('_InsideFeed') + '.kicad_mod')).read_text())
    old_winding = []
    for pad in children(old, 'pad'):
        if pad[3] != 'custom' or uq(child(pad, 'layers')[1]) != 'F.Cu':
            continue
        origin = tuple(map(float, child(pad, 'at')[1:3]))
        for line in children(child(pad, 'primitives'), 'gr_line'):
            pts = tuple(tuple(round(float(v) + off, 6) for v, off in zip(child(line, key)[1:3], origin))
                        for key in ['start', 'end'])
            if min(p[1] for p in pts) >= -20:
                old_winding.append(pts)
    assert all(line in segments['F.Cu'] for line in old_winding)
    winding = unary_union([LineString(line).buffer(.25) for line in old_winding])
    assert all(abs(a - b) < 1e-6 for a, b in zip(winding.bounds, [-20, -20, 20, 20]))
    holes = [tuple(map(float, child(p, 'at')[1:3])) for p in pads if p[2] == 'thru_hole']
    assert set(holes) == {(-1.5, -20.6), (-1.5, -14.5)}
    # A single unbranched electrical path including the plated barrels.
    graph = Counter()
    for layer, lines in segments.items():
        for a, b in lines:
            graph[(a, layer)] += 1; graph[(b, layer)] += 1
    # Front pad 1 landing is a terminal attached directly to its plated hole.
    for pt in holes:
        graph[(pt, 'F.Cu')] += 1; graph[(pt, 'B.Cu')] += 1
    assert sorted(graph.values()).count(1) == 2 and max(graph.values()) == 2
    assert {p for p, degree in graph.items() if degree == 1} == {
        ((-1.5, -14.5), 'F.Cu'), ((-4.9, -14.5), 'F.Cu')}
    # The outer plated hole must not touch any other turn; skip its connected lead.
    gaps = [Point(holes[0]).distance(LineString(line)) - .4 - .25
            for line in old_winding]
    assert min(gaps) >= .15 - 1e-6
    zones = children(tree, 'zone')
    assert len(zones) == 7
    for zone in zones:
        keepout = child(zone, 'keepout')
        assert all(child(keepout, key)[1] == 'not_allowed' for key in ['vias', 'copperpour', 'footprints'])
    report = dict(status='pass', unchanged_four_turn_winding=True,
                  outer_winding_copper_mm=[40, 40], minimum_nonadjacent_trace_gap_mm=minima,
                  single_unbranched_path_between_inside_feeds=True, plated_holes=2,
                  winding_rule_areas=7, rf_performance_measured=False)
    (OUT / 'geometry-check.json').write_text(json.dumps(report, indent=2) + '\n')
    data = json.loads((OUT / 'geometry.json').read_text())
    fig, ax = plt.subplots(figsize=(8, 8), layout='constrained')
    ax.set(aspect='equal', xlim=(-23, 23), ylim=(25, -25), xlabel='Local x (mm)', ylabel='Local y (mm)')
    for x1, y1, x2, y2 in data['winding_keepout_rectangles_mm']:
        ax.add_patch(Rectangle((x1, y1), x2-x1, y2-y1, facecolor='#eeeeee', edgecolor='#888888', lw=.5))
    ax.add_patch(PatchPolygon(data['courtyard_window_polygon_mm'], facecolor='#e9f3e8', edgecolor='#449966', ls='--'))
    x1, y1, x2, y2 = data['host_entry_rectangle_mm']
    ax.add_patch(Rectangle((x1,y1), x2-x1,y2-y1, facecolor='#dae8fa', edgecolor='#2266bb', ls='--'))
    for layer, color in [('B.Cu', '#2266bb'), ('F.Cu', '#bc5228')]:
        for i, (a,b) in enumerate(segments[layer]):
            ax.plot([a[0],b[0]], [a[1],b[1]], color=color, lw=2.2, label=layer if i==0 else None)
    for pad in pads:
        if pad[3] == 'custom': continue
        x,y = map(float, child(pad,'at')[1:3]); sx,sy = map(float,child(pad,'size')[1:3])
        if pad[2] == 'thru_hole':
            ax.add_patch(Circle((x,y),sx/2,facecolor='#ccab59'))
            ax.add_patch(Circle((x,y),.2,facecolor='white'))
        else:
            ax.add_patch(Rectangle((x-sx/2,y-sy/2),sx,sy,facecolor='#ccab59'))
    ax.text(-1.5,-12.2,'1',ha='center');ax.text(-4.9,-12.2,'2',ha='center')
    ax.text(0,0,'PN7160 + matching + crystal\ninside nominal 32.2 × 32.2 mm window\n\nCompact local ground only\nNo full-aperture plane',ha='center',va='center')
    ax.annotate('B.Cu host entry: 6 mm\nNo vias, components or pours',xy=(0,19),xytext=(0,23),ha='center',fontsize=9,arrowprops={'arrowstyle':'->'})
    ax.set_title('Inside-feed NFC antenna · 40 × 40 mm winding\n0.50 mm track / 0.30 mm gap · four turns retained')
    ax.legend(loc='lower right'); fig.savefig(OUT/'coil.svg');fig.savefig(OUT/'coil.png',dpi=160)
    print(json.dumps(report,indent=2))


def native_check():
    import pcbnew as k
    cli = os.environ.get('KICAD_CLI', '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
    def vec(x,y): return k.VECTOR2I(k.FromMM(x), k.FromMM(y))
    def base():
        board = k.BOARD(); board.SetCopperLayerCount(4)
        for name in ['ANT1','ANT2','HOST']: board.Add(k.NETINFO_ITEM(board,name))
        fp = k.FootprintLoad(str(LIB),NAME); assert fp
        fp.SetFPID(k.LIB_ID('Nucula_Project',NAME));fp.SetReference('A1');fp.SetPosition(vec(25,25))
        board.Add(fp)
        for pad in fp.Pads():pad.SetNet(board.GetNetsByName()['ANT'+pad.GetNumber()])
        fp.BuildCourtyardCaches()
        for layer in [k.F_CrtYd,k.B_CrtYd]:
            court=fp.GetCourtyard(layer)
            assert court.OutlineCount()==1 and court.HoleCount(0)==1
            assert not court.Contains(vec(25,25)) and court.Contains(vec(44,25))
        for a,b in zip([(0,0),(50,0),(50,50),(0,50)],[(50,0),(50,50),(0,50),(0,0)]):
            line=k.PCB_SHAPE(board);line.SetShape(k.SHAPE_T_SEGMENT);line.SetStart(vec(*a));line.SetEnd(vec(*b))
            line.SetLayer(k.Edge_Cuts);line.SetWidth(k.FromMM(.05));board.Add(line)
        return board
    cases = [('baseline',None,None),('center_front',k.F_Cu,((22,25),(28,25))),
             ('center_inner',k.In1_Cu,((22,25),(28,25))),('entry_bottom',k.B_Cu,((25,40),(25,47))),
             ('entry_front',k.F_Cu,((25,40),(25,47))),('entry_inner1',k.In1_Cu,((25,40),(25,47))),
             ('entry_inner2',k.In2_Cu,((25,40),(25,47))),('winding_bottom',k.B_Cu,((40,25),(48,25))),
             ('entry_via',None,None),('center_via',None,None),
             ('center_component',None,None),('winding_component',None,None)]
    expected = {'entry_front','entry_inner1','entry_inner2','winding_bottom','entry_via','winding_component'}
    results={}
    with tempfile.TemporaryDirectory(prefix='nucula-inside-feed-') as folder:
        folder=Path(folder)
        (folder/'fp-lib-table').write_text(f'(fp_lib_table (version 7) (lib (name "Nucula_Project") (type "KiCad") (uri "{LIB}") (options "") (descr "")))')
        for name,layer,points in cases:
            board=base()
            if points:
                track=k.PCB_TRACK(board);track.SetStart(vec(*points[0]));track.SetEnd(vec(*points[1]));track.SetWidth(k.FromMM(.25));track.SetLayer(layer)
                track.SetNet(board.GetNetsByName()['HOST']);board.Add(track)
            if name.endswith('_via'):
                via=k.PCB_VIA(board);via.SetPosition(vec(25,44 if name=='entry_via' else 25));via.SetWidth(k.FromMM(.6));via.SetDrill(k.FromMM(.3));via.SetViaType(k.VIATYPE_THROUGH);via.SetLayerPair(k.F_Cu,k.B_Cu)
                via.SetNet(board.GetNetsByName()['HOST']);board.Add(via)
            if name.endswith('_component'):
                fp=k.FOOTPRINT(board);fp.SetReference('TEST');fp.SetPosition(vec(44 if name=='winding_component' else 25,25))
                for layer in [k.F_CrtYd,k.B_CrtYd]:
                    rect=k.PCB_SHAPE(fp);rect.SetShape(k.SHAPE_T_RECT);p=fp.GetPosition();rect.SetStart(p-vec(.5,.5));rect.SetEnd(p+vec(.5,.5));rect.SetLayer(layer);rect.SetWidth(k.FromMM(.05));fp.Add(rect)
                board.Add(fp)
            path=folder/(name+'.kicad_pcb');report=folder/(name+'.json');k.SaveBoard(str(path),board)
            subprocess.run([cli,'pcb','drc','--format','json','--severity-all','-o',str(report),str(path)],check=True,stdout=subprocess.DEVNULL)
            data=json.loads(report.read_text()); types=[v['type'] for v in data['violations']]
            blocked='items_not_allowed' in types
            assert blocked == (name in expected), (name,types)
            # Intentional negative probes may also touch copper; dangling probe tracks
            # and the anonymous test courtyard are fixture-only diagnostics.
            allowed={'track_dangling','via_dangling'}
            if name in expected:
                allowed |= {'items_not_allowed','shorting_items','clearance','courtyards_overlap'}
            assert not set(types)-allowed,(name,types)
            if name=='baseline':assert not types and not data['unconnected_items'],data
            if name=='center_component':assert 'courtyards_overlap' not in types
            results[name]={'winding_keepout_blocks':blocked,'drc_types':types}
    (OUT/'native-check.json').write_text(json.dumps({'status':'pass','four_layer_fixtures':results},indent=2)+'\n')
    print('Native four-layer DRC fixtures passed:',len(results))


if __name__ == '__main__':
    native_check() if '--native' in sys.argv else geometry_check()
