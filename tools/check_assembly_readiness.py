#!/usr/bin/env python3
"""Build a JLCPCB BOM and audit footprints against the archived public catalogue.

Run tools/check_schematic.py first. Stdlib only; no network, purchases or PCB edits.
Stock is a dated observation, not a reservation or the final assembly quotation.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET
from kicad_sexpr import parse, children, child, uq

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/assembly'
MAC = Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport')
SHARE = Path(os.environ.get('KICAD_SHARE', str(MAC) if MAC.exists() else '/usr/share/kicad'))


def write_csv(name, fields, rows):
    with (OUT / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--boards', type=int, default=10)
    args = ap.parse_args()
    assert args.boards > 0
    verification = json.loads((ROOT / 'docs/verification.json').read_text())
    for file, digest in verification['schematic_sha256'].items():
        assert hashlib.sha256((ROOT / file).read_bytes()).hexdigest() == digest, 'Run check_schematic.py first'
    assert verification['erc_violations'] == 0
    parts = json.loads((OUT / 'jlc-stock-snapshot.json').read_text())['parts']
    bom = list(csv.DictReader((ROOT / 'docs/bom.csv').open()))
    populated = [r for r in bom if r['DNP'] == 'no']
    grouped = {}
    for r in populated:
        ref, code = r['Reference'], r['LCSC']
        assert code in parts, f'{ref}: missing verified JLCPCB part'
        p = parts[code]
        assert r['MPN'] == p['componentModelEn'], f'{ref}: catalogue MPN mismatch'
        assert r['Manufacturer'] == p['componentBrandEn'], f'{ref}: manufacturer mismatch'
        assert ref in p['references'], f'{ref}: snapshot reference mapping stale'
        # Numeric chip packages use imperial codes, not the metric 1608/2012 alias.
        pkg = p['componentSpecificationEn']
        if ref[0] in ['C', 'R'] and pkg in ['0603', '0805', '1206', '1210']:
            assert '_' + pkg + '_' in r['Footprint'], f'{ref}: package mismatch'
        grouped.setdefault(code, []).append(r)
    selected = {r['Reference'] for r in populated}
    assert selected == {r for p in parts.values() for r in p['references']}
    byref = {r['Reference']: r for r in bom}
    expected = {
        'DS1': ('C506794', 'Nucula_Project:Hirose_FH12A-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal'),
        'J2': ('C160352', 'Nucula_Project:JST_PH_B2B-PH-SM4-TB_1x02-1MP_P2.00mm_Vertical'),
        'U5': ('C5218924', 'Package_TO_SOT_SMD:SOT-23'),
        'R30': ('C2088132', 'Resistor_SMD:R_0805_2012Metric'),
        'J1': ('C5184243', 'Nucula_Project:USB_C_GCT_USB4105_16P_Standard'),
        'U8': ('C7605', 'Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm'),
    }
    for ref, (code, footprint) in expected.items():
        assert (byref[ref]['LCSC'], byref[ref]['Footprint']) == (code, footprint)
    for ref in ['C53', 'C54']:
        assert byref[ref]['DNP'] == 'no' and byref[ref]['Value'] == '33pF'
    for ref in ['C34', 'C35', 'C38', 'C39']:
        assert byref[ref]['DNP'] == 'yes' and 'NoPaste' in byref[ref]['Footprint']

    # Include the etched antenna and DNP parts in the physical footprint audit.
    xml = ET.parse(ROOT / 'docs/netlist.xml').getroot()
    audit = []
    for c in xml.findall('./components/comp'):
        ref = c.attrib['ref']
        footprint = c.findtext('footprint')
        lib, name = footprint.split(':', 1)
        path = (ROOT / 'libraries/Nucula_Project.pretty' if lib == 'Nucula_Project'
                else SHARE / 'footprints' / (lib + '.pretty')) / (name + '.kicad_mod')
        assert path.is_file(), f'{ref}: missing footprint'
        tree = parse(path.read_text())
        if ref == 'J2':
            pads = children(tree, 'pad')
            assert child(tree, 'attr')[1] == 'smd'
            assert len(pads) == 4 and all(p[2] == 'smd' for p in pads)
            assert sorted(uq(p[1]) for p in pads) == ['1', '2', 'MP', 'MP']
            assert parts[byref['J2']['LCSC']]['assemblyMode'] == 'smtWeld'
        model_paths = []
        for m in children(tree, 'model'):
            model = uq(m[1])
            resolved = model.replace('${KIPRJMOD}', str(ROOT))
            resolved = re.sub(r'\$\{KICAD\d+_3DMODEL_DIR\}', str(SHARE / '3dmodels'), resolved)
            assert Path(resolved).is_file(), f'{ref}: missing model'
            model_paths.append(model)
        if ref in ['C34', 'C35', 'C38', 'C39']:
            for pad in children(tree, 'pad'):
                assert not any('Paste' in uq(layer) for layer in child(pad, 'layers')[1:])
        audit.append(dict(Reference=ref, Population=('Etched PCB copper' if ref == 'A1' else
                          'DNP' if byref[ref]['DNP'] == 'yes' else 'Assemble'),
                          MPN=byref.get(ref, {}).get('MPN', ''), Footprint=footprint,
                          Footprint_SHA256=hashlib.sha256(path.read_bytes()).hexdigest(),
                          Models='; '.join(model_paths),
                          Model_status='Available' if model_paths else 'No model assigned'))
    write_csv('footprint-audit.csv', list(audit[0]), audit)

    purchasing = []
    jlc = []
    for code, rows in grouped.items():
        p = parts[code]
        need = len(rows) * args.boards
        # Conservative planning screen; these public fields are not a binding quote.
        allowance = int(p.get('lossNumber', 0))
        minimum = int(p.get('leastPatchNumber', 0))
        planned = max(need, minimum) + allowance
        available = max(0, int(p['canPresaleNumber']))
        status = 'SHORTAGE' if available < planned else 'TIGHT' if available < 2 * planned else 'AVAILABLE'
        refs = ', '.join(r['Reference'] for r in rows)
        purchasing.append(dict(References=refs, MPN=p['componentModelEn'], LCSC=code,
                               Package=p['componentSpecificationEn'], Per_board=len(rows),
                               Boards=args.boards, Placements=need, Minimum_placement=minimum,
                               Loss_allowance=allowance, Planning_quantity=planned,
                               Available_order_quantity=available, Stock_status=status,
                               Library=p['componentLibraryType'], Assembly_mode=p['assemblyMode'],
                               Preorder_MOQ=p.get('preMinPurchaseNum', ''),
                               Observed_UTC=p['retrieved_at'], Source=p['source']))
        jlc.append({'Comment': p['componentModelEn'], 'Designator': refs,
                    'Footprint': p['componentSpecificationEn'], 'LCSC Part #': code})
    write_csv('purchasing-10-boards.csv' if args.boards == 10 else f'purchasing-{args.boards}-boards.csv',
              list(purchasing[0]), purchasing)
    write_csv('jlcpcb-bom.csv', ['Comment', 'Designator', 'Footprint', 'LCSC Part #'], jlc)
    report = dict(boards=args.boards, physical_symbols=len(audit), purchased_populated_per_board=len(populated),
                  unique_purchased_parts=len(grouped), dnp_references=[r['Reference'] for r in bom if r['DNP'] == 'yes'],
                  footprint_status='All resolved; pin/pad correspondence checked by check_schematic.py',
                  without_3d=[r['Reference'] for r in audit if not r['Models']],
                  with_3d=sum(bool(r['Models']) for r in audit),
                  tight_stock=[r for r in purchasing if r['Stock_status'] == 'TIGHT'],
                  shortages=[r for r in purchasing if r['Stock_status'] == 'SHORTAGE'],
                  through_hole_assembly=sorted(r['Reference'] for r in populated
                                              if parts[r['LCSC']]['assemblyMode'] == 'manualWeld'),
                  scope='Component and footprint readiness; see docs/manufacturing-release.md and the hash-bound manufacturing package for Gerber/CPL validation and pending CAM acceptance',
                  stock_reserved=False,
                  quantity_method='Planning only: max(placements, public minimum placement) + public loss allowance. Final JLCPCB BOM matching controls quantities.',
                  inputs_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in [ROOT / 'docs/bom.csv', OUT / 'jlc-stock-snapshot.json']})
    (OUT / 'readiness.json').write_text(json.dumps(report, indent=2) + '\n')
    assert not report['shortages'], report['shortages']
    print(json.dumps({k: v for k, v in report.items() if k not in ['tight_stock', 'inputs_sha256']}, indent=2))
    print('Tight stock:', ', '.join(r['LCSC'] for r in report['tight_stock']))


if __name__ == '__main__':
    main()
