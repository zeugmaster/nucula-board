#!/usr/bin/env python3
"""Export the locked design for JLCPCB without editing the original PCB.

Run with KiCad's pcbnew-enabled Python. Run check_schematic.py and
check_assembly_readiness.py first; refresh_jlc_stock.py reads live stock.
Output must be a NEW directory. No orders, uploads or purchases are performed.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

import wx
import pcbnew as k
from kicad_sexpr import parse, dump, children, child, uq
from check_pcb_layout import run as layout_check, canonical, polygon, overlap_area

ROOT = Path(__file__).resolve().parents[1]
MAC = Path('/Applications/KiCad/KiCad.app/Contents')
CLI = os.environ.get('KICAD_CLI') or shutil.which('kicad-cli') or str(MAC / 'MacOS/kicad-cli')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def csv_out(path, fields, rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def nat(ref):
    import re
    return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', ref)]


def zip_files(dest, base, paths):
    with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(paths):
            z.write(p, str(p.relative_to(base)))


def main():
    app = wx.App(False)
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    out = args.output.resolve()
    if out.exists():
        raise SystemExit('Output already exists; choose a new directory to avoid mixing releases')
    spec = json.loads((ROOT / 'docs/manufacturing-spec.json').read_text())
    erc = json.loads((ROOT / 'docs/verification.json').read_text())
    assert erc['erc_violations'] == 0
    for name, digest in erc['schematic_sha256'].items():
        assert sha(ROOT / name) == digest, 'Schematic verification stale'
    from check_usb_clearance import run as check_usb
    usb = check_usb()
    assert usb['passed'], 'USB land amendment verification failed'
    assert usb == json.loads((ROOT / 'docs/usb-clearance-check.json').read_text()), 'USB audit stale'
    readiness = json.loads((ROOT / 'docs/assembly/readiness.json').read_text())
    assert readiness['boards'] == spec['boards'] and not readiness['shortages']
    for name, digest in readiness['inputs_sha256'].items():
        assert sha(ROOT / name) == digest, 'Assembly readiness inputs stale'
    stock = json.loads((ROOT / 'docs/assembly/jlc-stock-snapshot.json').read_text())
    now = datetime.now(timezone.utc)
    assert all(0 <= (now - datetime.fromisoformat(p['retrieved_at'])).total_seconds() < 86400
               for p in stock['parts'].values()), 'Refresh ALL stock observations (max age: 24h)'
    bom = list(csv.DictReader((ROOT / 'docs/assembly/jlcpcb-bom.csv').open()))
    refs = [r.strip() for row in bom for r in row['Designator'].split(',')]
    assert len(refs) == len(set(refs)) == readiness['purchased_populated_per_board'] == 116
    assert len(bom) == readiness['unique_purchased_parts'] == 55
    selected = set(refs)
    dnp = set(spec['dnp'])
    nonparts = set(spec['non_components'])
    assert not selected & (dnp | nonparts)
    original = k.LoadBoard(str(ROOT / 'nucula-v2.kicad_pcb'))
    fps = {f.GetReference(): f for f in original.GetFootprints()}
    assert set(fps) == selected | dnp | nonparts
    assert {r for r, f in fps.items() if f.IsDNP()} == dnp
    for row in bom:
        part = stock['parts'][row['LCSC Part #']]
        assert part['componentModelEn'] == row['Comment']
        rs = {r.strip() for r in row['Designator'].split(',')}
        assert rs == set(part['references'])
        need = max(len(rs) * spec['boards'], int(part['leastPatchNumber'])) + int(part['lossNumber'])
        assert part['canPresaleNumber'] >= need
        for ref in rs:
            f = fps[ref]
            assert f.GetFieldText('LCSC') == row['LCSC Part #']
            assert f.GetFieldText('MPN') == row['Comment']

    out.mkdir(parents=True)
    for name in ['gerbers', 'assembly', 'drawings', 'validation']:
        (out / name).mkdir()
    source_paths = sorted(set(
        list(ROOT.glob('*.kicad_*')) + [ROOT / 'fp-lib-table', ROOT / 'sym-lib-table'] +
        [p for p in (ROOT / 'libraries').rglob('*') if p.is_file()] +
        [p for p in (ROOT / 'LICENSES').rglob('*') if p.is_file()] +
        list((ROOT / 'tools').rglob('*.py')) + [ROOT / 'README.md'] +
        [p for p in (ROOT / 'docs').rglob('*') if p.suffix in ['.md','.json','.csv','.xml']]))
    source_paths = [p for p in source_paths if p.is_file() and p.suffix != '.kicad_prl']
    source_hashes = {str(p.relative_to(ROOT)): sha(p) for p in source_paths}
    zip_files(out / 'nucula-v2-design-snapshot.zip', ROOT, source_paths)
    log = []

    def run(*argv):
        command = [CLI, *map(str, argv)]
        log.append(command)
        subprocess.run(command, check=True, cwd=ROOT)

    with tempfile.TemporaryDirectory(prefix='nucula-jlcpcb-') as tmp:
        tmp = Path(tmp)
        for p in ROOT.glob('*.kicad_*'):
            if p.suffix != '.kicad_prl':
                shutil.copy2(p, tmp / p.name)
        for name in ['fp-lib-table', 'sym-lib-table']:
            shutil.copy2(ROOT / name, tmp / name)
        shutil.copytree(ROOT / 'libraries', tmp / 'libraries')
        boardfile = tmp / 'nucula-v2.kicad_pcb'
        run('pcb', 'drc', '--refill-zones', '--save-board', '--schematic-parity',
            '--all-track-errors', '--format', 'json', '-o', out / 'validation/drc.json', boardfile)
        drc = json.loads((out / 'validation/drc.json').read_text())
        assert not drc['unconnected_items'] and not drc['schematic_parity']
        assert len(drc['violations']) == 2 and all(
            v['severity'] == 'warning' and v['type'] == 'silk_edge_clearance' for v in drc['violations'])
        layout = layout_check(boardfile, json.loads((ROOT / 'docs/pcb/constraints.json').read_text()),
                              out / 'validation/drc.json')
        assert layout['passed']
        write_json(out / 'validation/layout-check.json', layout)

        # Manufacturing metadata on the export copy only. The locked source is intact.
        tree = parse(boardfile.read_text())
        before = parse((ROOT / 'nucula-v2.kicad_pcb').read_text())
        for key in ['segment', 'arc', 'via', 'gr_line', 'gr_arc', 'gr_poly', 'gr_text', 'footprint']:
            assert canonical(children(tree, key)) == canonical(children(before, key)), key
        setup = child(tree, 'setup')
        setup[:] = [x for x in setup if not isinstance(x, list) or x[0] != 'aux_axis_origin']
        setup.append(['aux_axis_origin', *map(str, spec['origin_kicad_mm'])])
        stack = child(setup, 'stackup')
        child(stack, 'copper_finish')[1] = '"ENIG"'
        for layer in children(stack, 'layer'):
            name = uq(layer[1])
            if name in ['In1.Cu', 'In2.Cu']:
                child(layer, 'thickness')[1] = str(spec['inner_copper_mm'])
            elif name.startswith('dielectric'):
                core = name == 'dielectric 2'
                child(layer, 'thickness')[1] = str(spec['core_mm' if core else 'prepreg_mm'])
                child(layer, 'epsilon_r')[1] = str(spec['core_er' if core else 'prepreg_er'])
                child(layer, 'material')[1] = '"FR4 core"' if core else '"3313"'
        child(setup, 'filling')[1] = 'yes'
        child(setup, 'capping')[1] = 'yes'
        boardfile.write_text(dump(tree) + '\n')
        board = k.LoadBoard(str(boardfile))
        footprints = {f.GetReference(): f for f in board.GetFootprints()}
        paste_removed = []
        for ref, fp in footprints.items():
            if ref in dnp | nonparts:
                fp.SetExcludedFromPosFiles(True)
            if ref in dnp:
                for pad in fp.Pads():
                    layers = pad.GetLayerSet()
                    if layers.Contains(k.F_Paste) or layers.Contains(k.B_Paste):
                        layers.RemoveLayer(k.F_Paste)
                        layers.RemoveLayer(k.B_Paste)
                        pad.SetLayerSet(layers)
                        paste_removed.append(ref + '.' + pad.GetNumber())
                assert not any(g.GetLayer() in [k.F_Paste, k.B_Paste] for g in fp.GraphicalItems())
        k.SaveBoard(str(boardfile), board)
        shutil.copy2(boardfile, out / 'validation/export-board.kicad_pcb')
        run('pcb', 'export', 'gerbers', '--layers',
            'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts,F.Paste,B.Paste',
            '--use-drill-file-origin', '--subtract-soldermask', '-o', out / 'gerbers', boardfile)
        run('pcb', 'export', 'drill', '--format', 'excellon', '--drill-origin', 'plot',
            '--excellon-units', 'mm', '--excellon-zeros-format', 'decimal',
            '--excellon-oval-format', 'route', '--excellon-separate-th', '--generate-map',
            '--map-format', 'pdf', '--generate-report', '--report-path', out / 'drawings/drill-report.txt',
            '-o', out / 'gerbers', boardfile)
        for p in (out / 'gerbers').glob('*.pdf'):
            shutil.move(str(p), out / 'drawings' / p.name)
        run('pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'front',
            '--use-drill-file-origin', '--exclude-dnp', '-o', out / 'validation/kicad-positions.csv', boardfile)
        raw_pos = list(csv.DictReader((out / 'validation/kicad-positions.csv').open()))
        assert {p['Ref'] for p in raw_pos} == selected and len(raw_pos) == len(selected)
        placement, audit, pads = [], [], []
        ox, oy = spec['origin_kicad_mm']
        for r in sorted(raw_pos, key=lambda row: nat(row['Ref'])):
            ref = r['Ref']
            fp = footprints[ref]
            angle = fp.GetOrientationDegrees()
            a = math.radians(angle)
            dx, dy = spec['local_body_center_offsets_mm'].get(ref, [0, 0])
            # KiCad +Y is downward; the export origin uses +Y upward.
            gx, gy = dx*math.cos(a) + dy*math.sin(a), -dx*math.sin(a) + dy*math.cos(a)
            x, y = k.ToMM(fp.GetPosition().x) - ox, oy - k.ToMM(fp.GetPosition().y)
            assert abs(x-float(r['PosX'])) < 1e-5 and abs(y-float(r['PosY'])) < 1e-5
            correction = spec['rotation_corrections_deg'].get(ref, 0)
            placement.append({'Designator': ref, 'Mid X': f'{x+gx:.6f}', 'Mid Y': f'{y-gy:.6f}',
                              'Layer': 'Top', 'Rotation': f'{(angle+correction)%360:.6f}'})
            audit.append({'Reference': ref, 'LCSC': fp.GetFieldText('LCSC'),
                          'Origin_X': x, 'Origin_Y': y, 'Center_offset_local_X': dx,
                          'Center_offset_local_Y': dy, 'KiCad_rotation_CCW': angle,
                          'JLC_rotation_correction': correction,
                          'Preview_status': 'Requires JLCPCB catalogue preview verification'})
            for pad in fp.Pads():
                if pad.GetNumber() and pad.IsOnLayer(k.F_Cu):
                    pads.append({'Reference': ref, 'Pad': pad.GetNumber(), 'Net': pad.GetNetname(),
                                 'X_mm': round(k.ToMM(pad.GetPosition().x)-ox, 6),
                                 'Y_mm': round(oy-k.ToMM(pad.GetPosition().y), 6)})
        csv_out(out / 'assembly/jlcpcb-cpl.csv', ['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'], placement)
        csv_out(out / 'assembly/placement-audit.csv', list(audit[0]), audit)
        csv_out(out / 'assembly/pad-coordinates.csv', list(pads[0]), pads)
        assert {p['Designator'] for p in placement} == selected
        # Drawing-only presentation: visible URL/MPN fields obscure pin numbers.
        # The archived plotting board and all fabrication/CPL outputs above are unchanged.
        for fp in board.GetFootprints():
            for field in fp.GetFields():
                field.SetVisible(field.GetName() == 'Reference')
        k.SaveBoard(str(boardfile), board)
        run('pcb', 'export', 'pdf', '--layers', 'F.Fab,F.Silkscreen,Edge.Cuts', '--mode-single',
            '--sketch-pads-on-fab-layers', '--crossout-DNP-footprints-on-fab-layers',
            '--exclude-value', '--black-and-white', '--bg-color', '#ffffff', '--scale', '0',
            '-o', out / 'drawings/assembly-top.pdf', boardfile)
        run('pcb', 'export', 'pdf', '--layers', 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste',
            '--common-layers', 'Edge.Cuts', '--mode-multipage', '-o', out / 'drawings/layers.pdf', boardfile)
        run('pcb', 'export', 'pdf', '--layers', 'Edge.Cuts,Dwgs.User', '--mode-single',
            '-o', out / 'drawings/fabrication-outline.pdf', boardfile)
        run('sch', 'export', 'pdf', '-o', out / 'drawings/schematic.pdf', tmp / 'nucula-v2.kicad_sch')
        # Audit wettable copper vs via holes, independent of electrical DRC.
        vias = [v for v in board.GetTracks() if isinstance(v, k.PCB_VIA)]
        via_in_pad = []
        for ref in selected:
            for p in footprints[ref].Pads():
                if p.GetAttribute() != k.PAD_ATTRIB_SMD or not p.IsOnLayer(k.F_Mask) or not p.IsOnLayer(k.F_Cu):
                    continue
                for v in vias:
                    if not p.HitTest(v.GetPosition(), v.GetDrillValue()//2):
                        continue
                    x, y = map(k.ToMM, v.GetPosition())
                    radius = k.ToMM(v.GetDrillValue())/2
                    hole = polygon([(x+radius*math.cos(i*math.tau/128),
                                     y+radius*math.sin(i*math.tau/128)) for i in range(128)])
                    area = overlap_area(p.GetEffectivePolygon(k.F_Cu), hole)
                    if area > 1e-8:
                        via_in_pad.append({'Reference': ref, 'Pad': p.GetNumber(),
                                           'via_mm': [x, y], 'hole_overlap_mm2': round(area, 6)})
        u6 = footprints['U6']
        paste = [p for p in u6.Pads() if p.GetNumber() == '' and p.IsOnLayer(k.F_Paste)]
        assert len(paste) == 9
        paste_area = sum(k.ToMM(p.GetSize().x)*k.ToMM(p.GetSize().y) -
                         (4-math.pi)*k.ToMM(p.GetRoundRectCornerRadius())**2 for p in paste)
        write_json(out / 'validation/export-check.json', {
            'bom_groups': len(bom), 'bom_and_cpl_placements': len(placement),
            'excluded_references': sorted(dnp | nonparts, key=nat),
            'removed_dnp_paste_pads': paste_removed, 'original_design_unchanged': True,
            'source_drc_errors': 0, 'source_drc_warnings': 2,
            'u6_exposed_pad_paste_apertures': len(paste),
            'u6_exposed_pad_paste_coverage_percent': round(paste_area / 4.1**2 * 100, 3),
            'smd_pad_via_hole_intersections': via_in_pad,
            'u3_thermal_holes_to_fill': 12,
            'via_covering': spec['via_covering'],
            'manufacturing_metadata_changes': ['JLC04161H-3313 stackup', 'ENIG', 'aux origin 50,160',
                                               'epoxy filling and copper capping'],
            'usb_npth_to_pad_clearance_mm': usb['minimum_npth_to_smd_clearance_mm'],
            'cam_acceptance_pending': ['90 ohm USB impedance on selected stackup',
                                       'carrier avoiding ESP32 overhang and preserving keyboard',
                                       'catalogue-specific placement rotations and centroids']})

    for p in ['jlcpcb-bom.csv', 'purchasing-10-boards.csv', 'jlc-stock-snapshot.json', 'readiness.json']:
        shutil.copy2(ROOT / 'docs/assembly' / p, out / 'assembly' / p)
    for p in ['erc.json', 'verification.json', 'usb-clearance-check.json']:
        shutil.copy2(ROOT / 'docs' / p, out / 'validation' / p)
    shutil.copy2(ROOT / 'docs/oled24/top-contact-check.json', out / 'validation/oled-top-contact-check.json')
    shutil.copy2(ROOT / 'docs/manufacturing-spec.json', out / 'manufacturing-spec.json')
    shutil.copy2(ROOT / 'docs/manufacturing-release.md', out / 'README.md')
    zip_files(out / 'nucula-v2-gerbers.zip', out / 'gerbers', (out / 'gerbers').iterdir())
    assert all(sha(ROOT / p) == digest for p, digest in source_hashes.items()), 'Source changed during export'
    write_json(out / 'manifest.json', {
        'generated_utc': now.isoformat(), 'source_commit': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source_revision_note': 'source_commit is the baseline HEAD at export; source_sha256 and the archived snapshot identify the exact working design',
        'kicad_version': subprocess.check_output([CLI, '--version'], text=True).strip(),
        'source_sha256': source_hashes, 'specification': spec,
        'status': spec['status'], 'commands': log,
        'artifacts_sha256': {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*')) if p.is_file()}})
    print('Prepared:', out)


if __name__ == '__main__':
    main()
