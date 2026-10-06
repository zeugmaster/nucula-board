#!/usr/bin/env python3
"""Render an exact Rev-A probe map; run with pcbnew + matplotlib Python.

The board is read from the recorded fabrication commit, never from the working
Rev-B layout. Outputs are a printable one-page PDF, PNG, SVG and pad manifest.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import pcbnew as k
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Circle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/bringup'
PROVENANCE = json.loads((OUT / 'rev-A-provenance.json').read_text())
COMMIT = PROVENANCE['release_commit']
COLORS = {'A': '#bd4613', 'B': '#215bcc', 'C': '#08745f'}
INK, MUTED = '#182d3c', '#556671'
PROBES = [
    dict(letter='A', ref='C14', pad='1', xy=[64.25, 111.525], net='/Power + ESP32-C3/VBUS', name='VBUS', side='LOWER PAD'),
    dict(letter='B', ref='R13', pad='1', xy=[97.9, 118.325], net='/Power + ESP32-C3/USB_ESD_D+', name='D+', side='LOWER PAD · right resistor'),
    dict(letter='C', ref='C11', pad='1', xy=[94.775, 93.5], net='/+3V3', name='3.3 V', side='RIGHT PAD'),
]


def xy(v):
    return (v.x / 1e6, v.y / 1e6)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out-stem', type=Path, default=OUT / 'rev-A-usb-bench-guide',
                    help='Output path without extension; use a fresh stem to preserve annotated sheets.')
    stem = ap.parse_args().out_stem
    previous = json.loads(stem.with_suffix('.json').read_text()) if stem.with_suffix('.json').exists() else {}
    for ext in ['png', 'svg', 'pdf']:
        existing = stem.with_suffix('.'+ext)
        if existing.exists() and hashlib.sha256(existing.read_bytes()).hexdigest() != previous.get('outputs_sha256', {}).get(ext):
            raise SystemExit(f'Refusing to overwrite modified/annotated file: {existing}. Choose a fresh --out-stem.')
    source = subprocess.check_output(['git', 'show', f'{COMMIT}:nucula-v2.kicad_pcb'], cwd=ROOT)
    digest = hashlib.sha256(source).hexdigest()
    assert digest == PROVENANCE['pcb_sha256'], 'Rev-A provenance mismatch'
    with tempfile.TemporaryDirectory(prefix='nucula-bench-') as td:
        board_path, geom_path = Path(td) / 'rev-A.kicad_pcb', Path(td) / 'geometry.json'
        board_path.write_bytes(source)
        subprocess.run([sys.executable, str(ROOT / 'tools/export_routing_geometry.py'),
                        '--board', str(board_path), '--out', str(geom_path)], check=True)
        geometry = json.loads(geom_path.read_text())
        board = k.LoadBoard(str(board_path))
    pads = {(p['ref'], p['num']): p for p in geometry['items'] if p['type'] == 'pad'}
    for p in PROBES:
        actual = pads[p['ref'], p['pad']]
        assert actual['xy'] == p['xy'] and actual['net'] == p['net'], (p, actual['net'])
        assert actual['exposed'] and 0 in actual['layers']
    shell_pads = [p for p in geometry['items'] if p.get('ref') == 'J1' and p.get('num') == 'SH']
    assert len(shell_pads) == 4 and all(p['net'] == 'GND' for p in shell_pads)
    assert pads['SW1', '1']['net'].endswith('/ESP_EN') and pads['SW1', '2']['net'] == 'GND'
    assert pads['C14', '1']['xy'][1] > pads['C14', '2']['xy'][1]
    assert pads['R13', '1']['xy'][1] > pads['R13', '2']['xy'][1]
    assert pads['R13', '1']['xy'][0] > pads['R12', '1']['xy'][0]
    assert pads['C11', '1']['xy'][0] > pads['C11', '2']['xy'][0]

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'text.color': INK, 'svg.fonttype': 'none', 'pdf.fonttype': 42})
    fig = plt.figure(figsize=(8.27, 11.69), facecolor='white')
    fig.text(.05, .957, 'REV A · USB BACKFEED CHECK', fontsize=20, weight='bold')
    fig.text(.05, .929, 'Battery connected   /   USB cable unplugged   /   Meter on DC volts', fontsize=11)
    fig.text(.05, .898, 'COMPONENT SIDE UP · NFC COIL AT TOP', fontsize=10, weight='bold', color=MUTED)

    def drawing(ax, bounds, overview=False):
        ax.set_xlim(bounds[0], bounds[1])
        ax.set_ylim(bounds[3], bounds[2])
        ax.set_aspect('equal')
        ax.axis('off')
        for poly in geometry['outline']:
            ax.add_patch(Polygon(poly, facecolor='#edf3ef', edgecolor='#82958b', lw=.7, zorder=0))
        if not overview:
            for t in geometry['items']:
                if t['type'] == 'track' and 0 in t['layers']:
                    ax.plot([t['start'][0], t['end'][0]], [t['start'][1], t['end'][1]], color='#d1dfd6', lw=.7, zorder=1)
        for f in board.GetFootprints():
            for s in f.GraphicalItems():
                if not isinstance(s, k.PCB_SHAPE) or s.GetLayer() != k.F_Fab:
                    continue
                a, b = xy(s.GetStart()), xy(s.GetEnd())
                if s.GetShape() == k.SHAPE_T_RECT:
                    ax.add_patch(Rectangle((min(a[0], b[0]), min(a[1], b[1])), abs(a[0]-b[0]), abs(a[1]-b[1]),
                                           facecolor='#d5dedd', edgecolor='#657b7b', lw=.45, zorder=2))
                elif s.GetShape() == k.SHAPE_T_SEGMENT:
                    ax.plot([a[0], b[0]], [a[1], b[1]], color='#657b7b', lw=.45, zorder=2)
                elif s.GetShape() == k.SHAPE_T_CIRCLE:
                    ax.add_patch(Circle(a, k.ToMM(s.GetRadius()), facecolor='#c8d1d2', edgecolor='#657b7b', lw=.5, zorder=2))
        for q in geometry['items']:
            if q['type'] != 'pad' or 0 not in q['layers']:
                continue
            for poly in q['poly']:
                ax.add_patch(Polygon(poly, facecolor='#bbc5c8', edgecolor='#7d8e96', lw=.3, zorder=3))
        for p in PROBES:
            for poly in pads[p['ref'], p['pad']]['poly']:
                ax.add_patch(Polygon(poly, facecolor=COLORS[p['letter']], edgecolor='white', lw=.7, zorder=5))

    overview = fig.add_axes([.035, .413, .47, .466])
    drawing(overview, (46, 116, 48, 128), True)
    overview.text(80, 59, 'NFC COIL', ha='center', fontsize=9, weight='bold', color=MUTED)
    overview.text(80, 127, '↓ KEYBOARD', ha='center', fontsize=9, weight='bold', color=MUTED)
    overview.text(99.8, 105, 'ESP32', ha='center', fontsize=8, color=MUTED)
    overview.text(80, 107.5, 'DISPLAY', ha='center', fontsize=7, color=MUTED)
    overview.annotate('RESET\nlower button', xy=(106.5, 84), xytext=(94, 71.5), fontsize=9, weight='bold',
                      ha='center', arrowprops=dict(arrowstyle='->', color=INK, lw=1.3), zorder=8)
    overview.text(110, 79, 'BOOT', fontsize=6.5, va='center', color=MUTED)
    overview.annotate('BLACK LEAD\nUSB metal shell', xy=(52.5, 112), xytext=(63, 120.7), fontsize=8,
                      ha='center', weight='bold', arrowprops=dict(arrowstyle='->', color=INK, lw=1.3), zorder=8)
    for p, label_at in zip(PROBES, [(69, 115), (101.5, 123), (92, 87)]):
        overview.annotate(p['letter'], xy=p['xy'], xytext=label_at, ha='center', va='center',
                          color='white', fontsize=11, weight='bold', zorder=9,
                          bbox=dict(boxstyle='circle,pad=.27', fc=COLORS[p['letter']], ec='white', lw=1),
                          arrowprops=dict(arrowstyle='->', color=COLORS[p['letter']], lw=1.8))
    fig.text(.055, .395, 'Same orientation in every enlargement.\nColored pad = red probe tip.', fontsize=9.5, color=MUTED)

    zooms = [
        ((58.5, 67.1, 108.6, 114.1), [('C14', 65.55, 110.6), ('U4', 61, 113.8)], .723),
        ((94.6, 101.0, 115.6, 120.2), [('R12', 95.55, 117.4), ('R13', 99.0, 117.4)], .552),
        ((90.8, 97.2, 91.6, 95.7), [('C11', 94, 92.1)], .381),
    ]
    for p, (bounds, labels, ypos) in zip(PROBES, zooms):
        col = COLORS[p['letter']]
        fig.text(.55, ypos+.134, f"{p['letter']}   {p['name']}  ·  {p['ref']} pad 1", fontsize=13, weight='bold', color=col)
        fig.text(.55, ypos+.112, p['side'], fontsize=9.5, weight='bold', color=MUTED)
        ax = fig.add_axes([.55, ypos-.014, .40, .116])
        drawing(ax, bounds)
        for label, x, y in labels:
            ax.text(x, y, label, ha='center', va='center', fontsize=9, weight='bold',
                    bbox=dict(fc='white', ec='none', alpha=.86, pad=1), zorder=7)
        for num in ['1', '2']:
            q = pads[p['ref'], num]
            ax.text(*q['xy'], num, ha='center', va='center', fontsize=9, weight='bold',
                    color='white' if num == '1' else INK, zorder=8)
        # Scale bar is in native board millimetres.
        x, y = bounds[1]-1.5, bounds[3]-.3
        ax.plot([x, x+1], [y, y], color=INK, lw=1.5, zorder=9)
        ax.text(x+.5, y-.2, '1 mm', fontsize=6, ha='center', zorder=9)

    fig.text(.05, .34, 'WRITE SIX READINGS · VOLTS DC', fontsize=11, weight='bold')
    table_ax = fig.add_axes([.05, .207, .9, .116])
    table_ax.axis('off')
    cells = [['Probe', 'RESET released', 'RESET held'],
             ['A   VBUS / C14.1', '________ V', '________ V'],
             ['B   D+ / R13.1', '________ V', '________ V'],
             ['C   3.3 V / C11.1', '________ V', '________ V']]
    table = table_ax.table(cellText=cells, cellLoc='left', colWidths=[.42, .29, .29], bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor('#d2dcdf')
        cell.set_linewidth(.7)
        cell.PAD = .065
        if row == 0:
            cell.set_facecolor('#edf1f5')
            cell.set_text_props(weight='bold', color=INK)
        elif col == 0:
            cell.set_text_props(weight='bold', color=COLORS['ABC'[row-1]])
    fig.text(.05, .176, '1  Power off. Clip black lead to the USB metal shell; keep USB unplugged.', fontsize=10)
    fig.text(.05, .150, '2  Connect battery. Leave BOOT alone. With RESET released, read A → B → C.', fontsize=10)
    fig.text(.05, .124, '3  Hold RESET (SW1) down. Read A → B → C again while keeping it held.', fontsize=10)
    fig.text(.05, .098, 'Use a fine insulated tip; touch only the colored pad. Wait for each reading to settle.', fontsize=9, color=MUTED)
    fig.text(.05, .067, 'If A and B fall together while C stays near 3.3 V, the USB-data backfeed path is supported.\nIf C also falls, record it: RESET may be affecting the supply. Six readings first; no rework needed.', fontsize=9)
    fig.text(.05, .024, f'Exact fabricated Rev-A · {COMMIT[:12]} · front view, not mirrored · enlarged views not to print scale', fontsize=7, color=MUTED)
    stem.parent.mkdir(parents=True, exist_ok=True)
    for ext in ['png', 'svg', 'pdf']:
        fig.savefig(stem.with_suffix('.'+ext), dpi=220, facecolor='white')
    manifest = dict(board_commit=COMMIT, source_board_sha256=digest, view='component side; NFC above, keyboard below; no mirror',
                    probes=PROBES, ground='J1 USB metal shell; all SH pads are GND',
                    reset=dict(ref='SW1', xy_mm=[106.5, 84], position='lower of two buttons; SW2 above is BOOT'),
                    source='Native Rev-A pad polygons and F.Fab outlines; working Rev-B PCB is not used.',
                    outputs_sha256={ext: hashlib.sha256(stem.with_suffix('.'+ext).read_bytes()).hexdigest() for ext in ['png','svg','pdf']})
    stem.with_suffix('.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('Rev-A probe positions, nets, orientation and USB-shell ground verified; PNG, SVG, PDF written.')


if __name__ == '__main__':
    main()
