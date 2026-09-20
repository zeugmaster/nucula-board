#!/usr/bin/env python3
"""Run with KiCad's Python (pcbnew). Generate a standalone measurement coupon.

The main project PCB stays unplaced. This coupon contains the actual library
footprint and is a useful fabrication option for measuring its bare impedance.
"""
from pathlib import Path
import json
import os
import subprocess
import sys
import pcbnew as k

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from kicad_sexpr import parse, children, child, uq
NAME = 'NFC_PCB_Loop_40x40_4T_W0.50_S0.30'
LIB = ROOT / 'libraries/Nucula_Project.pretty'
OUT = ROOT / 'prototypes/nfc-antenna'
CLI = os.environ.get('KICAD_CLI', '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')


def vec(x, y):
    return k.VECTOR2I(k.FromMM(x), k.FromMM(y))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'fp-lib-table').write_text('(fp_lib_table (version 7)\n (lib (name "Nucula_Project") (type "KiCad") (uri "${KIPRJMOD}/../../libraries/Nucula_Project.pretty") (options "") (descr "Project NFC coil")))\n')
    board = k.BOARD()
    board.SetCopperLayerCount(2)
    board.GetDesignSettings().SetBoardThickness(k.FromMM(1.6))
    for name in ['RF_ANT_P', 'RF_ANT_N']:
        board.Add(k.NETINFO_ITEM(board, name))
    fp = k.FootprintLoad(str(LIB), NAME)
    assert fp is not None, 'KiCad could not load footprint'
    fp.SetFPID(k.LIB_ID('Nucula_Project', NAME))
    fp.SetReference('A1')
    fp.SetValue('40mm / 4T / W0.50 / S0.30')
    fp.Value().SetVisible(False)
    fp.SetPosition(vec(24, 26))
    board.Add(fp)
    nets = board.GetNetsByName()
    for pad in fp.Pads():
        pad.SetNet(nets['RF_ANT_P' if pad.GetNumber() == '1' else 'RF_ANT_N'])
    corners = [(1, 1), (47, 1), (47, 49), (1, 49), (1, 1)]
    for start, end in zip(corners, corners[1:]):
        line = k.PCB_SHAPE(board)
        line.SetShape(k.SHAPE_T_SEGMENT)
        line.SetStart(vec(*start));line.SetEnd(vec(*end))
        line.SetLayer(k.Edge_Cuts);line.SetWidth(k.FromMM(.05));board.Add(line)
    text = k.PCB_TEXT(board)
    text.SetText('NFC COIL TEST / 1 oz / 1.6 mm')
    text.SetPosition(vec(24, 26));text.SetTextSize(vec(.85, .85))
    text.SetTextThickness(k.FromMM(.12));text.SetLayer(k.F_SilkS);board.Add(text)
    board.GetTitleBlock().SetTitle('Nucula NFC bare-coil measurement coupon')
    board.GetTitleBlock().SetComment(0, '2 layers, 1.6 mm FR4, 35 um copper; no ground planes')
    path = OUT / 'nfc-antenna.kicad_pcb'
    k.SaveBoard(str(path), board)
    reloaded = k.LoadBoard(str(path))
    f = list(reloaded.GetFootprints())[0]
    assert sorted(p.GetNumber() for p in f.Pads()) == ['1', '1', '2', '2', '2', '2']
    assert len(list(f.Zones())) == 1
    tree = parse(path.read_text())
    ft = child(tree, 'footprint')
    assert uq(child(ft, 'net_tie_pad_groups')[1]) == '1,2'
    keepout = child(child(ft, 'zone'), 'keepout')
    assert all(child(keepout, p)[1] == 'not_allowed' for p in ['tracks', 'vias', 'copperpour', 'footprints'])
    assert child(keepout, 'pads')[1] == 'allowed'  # own copper pads must be permitted
    report = ROOT / 'docs/nfc/coupon-drc.json'
    subprocess.run([CLI, 'pcb', 'drc', '--format', 'json', '--severity-all',
                    '--exit-code-violations', '-o', str(report), str(path)], check=True)
    data = json.loads(report.read_text())
    assert not data['violations'] and not data['unconnected_items']
    subprocess.run([CLI, 'pcb', 'export', 'svg', '--layers', 'F.Cu,B.Cu,F.Silkscreen,Edge.Cuts',
                    '--mode-single', '--page-size-mode', '2', '--exclude-drawing-sheet',
                    '-o', str(ROOT / 'docs/nfc/coupon.svg'), str(path)], check=True)
    print('Native KiCad load/save and coupon DRC pass.')


if __name__ == '__main__':
    main()
