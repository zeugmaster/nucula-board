#!/usr/bin/env python3
"""Strict routing regression, retaining only identical proven rev-A NFC findings."""
import hashlib,json
from pathlib import Path
from zipfile import ZipFile
from check_routing_quality import audit
ROOT=Path(__file__).resolve().parents[1]

def main():
    geometry=json.loads((ROOT/'docs/pcb/routing-geometry.json').read_text())
    board_sha=hashlib.sha256((ROOT/'nucula-v2.kicad_pcb').read_bytes()).hexdigest()
    assert geometry['source_board_sha256']==board_sha
    nfc=json.loads((ROOT/'docs/pcb/nfc-rev-a-check.json').read_text())
    assert nfc['passed'] and nfc['board_sha256']==board_sha
    baseline=ROOT/'tools/baselines/rev-A-nfc.zip'
    assert hashlib.sha256(baseline.read_bytes()).hexdigest()==nfc['baseline_archive_sha256']
    with ZipFile(baseline) as z:old=json.loads(z.read('routing-geometry.json'))
    assert old['source_board_sha256']=='4e582fc67796c618ffb62488af51a3807b1540be308f1a315ecae28ff7b50e96'
    prior=audit(old);current=audit(geometry)
    before={q['id']:q for q in old['items']}
    x1,y1,x2,y2=nfc['region_mm']
    def frozen(q):
        return q==before.get(q['id']) and x1<=q['xy'][0]<=x2 and y1<=q['xy'][1]<=y2
    unchanged={q['id'] for q in geometry['items'] if frozen(q)}
    new={};retained={}
    for key in ['non45','duplicates','shallow_ends','exposed_short_segments','weak_pairs','acute_bends']:
        def allowed(finding):
            if finding not in prior[key]:return False
            if isinstance(finding,str):return finding in unchanged
            if isinstance(finding,list):return set(finding)<=unchanged
            return finding.get('id') in unchanged
        retained[key]=[v for v in current[key] if allowed(v)]
        new[key]=[v for v in current[key] if not allowed(v)]
    report={'passed':not any(new.values()),'source_board_sha256':board_sha,
            'checks':{'no_new_routing_findings_outside_frozen_NFC':not any(new.values()),
                      'NFC_rev_A_copper_and_reviewed_substitutions_pass':nfc['passed']},
            'strict_geometry_passed':current['passed'],'strict_statistics':current['statistics'],
            'retained_rev_A_NFC_findings':retained,'new_findings':new,
            'scope':'User requested unchanged proven NFC. Only findings reproduced on identical rev-A copper objects are retained; no native DRC errors or new routing findings are accepted.'}
    (ROOT/'docs/pcb/routing-quality-raw.json').write_text(json.dumps(current,indent=2)+'\n')
    (ROOT/'docs/pcb/routing-quality.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
