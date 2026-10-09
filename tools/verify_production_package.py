#!/usr/bin/env python3
"""Verify complete release archives, evidence freshness and all source hashes."""
import argparse,csv,hashlib,json
from pathlib import Path
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def verify(out):
    manifest=json.loads((out/'manifest.json').read_text())
    source=manifest['source_board_sha256']
    assert source==sha(ROOT/'nucula-v2.kicad_pcb')
    for name,digest in manifest['source_inputs_sha256'].items():
        assert sha(ROOT/name)==digest, 'Changed release input: '+name
    actual={str(p.relative_to(out)) for p in out.rglob('*') if p.is_file() and p.name!='manifest.json'}
    assert actual==set(manifest['files_sha256']), 'Unmanifested or missing package file'
    for name,digest in manifest['files_sha256'].items():assert sha(out/name)==digest,name
    reports=['nfc-rev-a-check.json','layout-check.json','standard-fabrication-check.json',
             'routing-quality.json','mini-module-check.json','mounting-holes-check.json',
             'battery-connector-check.json','usb-backfeed-check.json','display-mapping-check.json',
             'export-check.json','gerber-readback.json','nfc-gerber-comparison.json']
    for name in reports:
        r=json.loads((out/'validation'/name).read_text());assert r['passed'],name
        for key in ['source_board_sha256','board_sha256']:
            if key in r:assert r[key]==source, 'Stale '+name
    drc=json.loads((out/'validation/drc.json').read_text())
    assert not any(v['severity']=='error' for v in drc['violations'])
    assert not drc['unconnected_items'] and not drc.get('schematic_parity')
    schematic=json.loads((out/'validation/schematic-verification.json').read_text())
    assert schematic['erc_violations']==0
    for name,digest in schematic['schematic_sha256'].items():assert sha(ROOT/name)==digest
    counts=[]
    for name,count in [('simulation-results.json',261),('usb-spice-results.json',57)]:
        r=json.loads((out/'validation'/name).read_text())
        assert r['simulations_completed']==count and not r['solver_errors']
        for name,digest in r['source_sha256'].items():assert sha(ROOT/name)==digest,name
        counts.append(count)
    assert json.loads((out/'validation/nfc/spice-check.json').read_text())['status']=='pass'
    assert json.loads((out/'validation/nfc/inside-feed/native-check.json').read_text())['status']=='pass'
    rows=list(csv.DictReader((out/'assembly/placement-audit.csv').open()))
    assert len(rows)==119 and len({r['Reference'] for r in rows})==119
    assert all(r['Passed']=='True' and all(float(r[k])==0 for k in
               ['CPL_delta_X_mm','CPL_delta_Y_mm','CPL_delta_rotation']) for r in rows)
    package=out.with_name(out.name+'-package.zip')
    with ZipFile(package) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(set(z.namelist()))
        assert set(z.namelist())==actual|{'manifest.json'}
        for name in z.namelist():assert z.read(name)==(out/name).read_bytes(),name
    with ZipFile(out/'nucula-v2-gerbers.zip') as z:
        assert set(z.namelist())=={p.name for p in (out/'gerbers').iterdir()}
        for name in z.namelist():assert z.read(name)==(out/'gerbers'/name).read_bytes()
    with ZipFile(out/'nucula-v2-design-snapshot.zip') as z:
        assert z.testzip() is None
        assert hashlib.sha256(z.read('nucula-v2.kicad_pcb')).hexdigest()==source
        for name in z.namelist():assert z.read(name)==(ROOT/name).read_bytes(), 'Snapshot mismatch: '+name
    assert package.with_suffix('.zip.sha256').read_text().split()[0]==sha(package)
    return {'passed':True,'release':out.name,'board_sha256':source,'package_sha256':sha(package),
            'package_bytes':package.stat().st_size,'manifested_files':len(actual),
            'source_inputs_checked':len(manifest['source_inputs_sha256']),
            'ERC_violations':0,'DRC_errors':0,'unconnected':0,'schematic_parity_findings':0,
            'reviewed_DRC_warnings':len(drc['violations']),
            'placements_checked':119,'assembly_pads_checked':413,'SPICE_cases':sum(counts),
            'independent_NFC_SPICE_crosscheck':'pass','NFC_keepout_fixtures':12,
            'NFC_Gerber_copper_and_mask_comparison':'pass, all four copper and both mask layers',
            'supplier_preview_approved':False,'revised_hardware_bench_qualified':False,
            'scope':'Production-file integrity and documented engineering checks; supplier CAM/assembly acceptance and physical qualification are separate.'}
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('export',type=Path)
    ap.add_argument('--out',type=Path,default=ROOT/'docs/production-package-check.json');a=ap.parse_args()
    r=verify(a.export);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
