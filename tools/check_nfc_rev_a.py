#!/usr/bin/env python3
"""Freeze the proven rev-A NFC circuit and local physical layout. Requires pcbnew.

The baseline is the submitted rev-A source, not an inferred matching network.
Seven power/digital feeders are compared within the NFC boundary; their remote
routes, mounting hardware and the rest of the board can differ.
"""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
import pcbnew as k
from kicad_sexpr import parse, children, child, uq
from check_pcb_layout import canonical, digest
from substitution_amendments import original_form, AMENDMENTS

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT/'tools/baselines/rev-A-nfc.zip'
BOUNDS = (59.5, 49., 102., 91.5)
COMMIT = '7584d71f3cb1b120934be2b80cfab4a015ecddfd'


def in_region(item):
    if item[0] == 'via':
        x,y = map(float, child(item,'at')[1:3])
        return BOUNDS[0] <= x <= BOUNDS[2] and BOUNDS[1] <= y <= BOUNDS[3]
    if item[0] == 'segment':
        points = [list(map(float,child(item,key)[1:3])) for key in ['start','end']]
        # Slab intersection also catches a newly added segment that crosses
        # the whole region while both of its endpoints are outside it.
        low, high = 0., 1.
        for axis in [0,1]:
            start, end = points[0][axis], points[1][axis]
            delta = end-start
            if delta == 0:
                if not BOUNDS[axis] <= start <= BOUNDS[axis+2]: return False
            else:
                a,b = sorted(((BOUNDS[axis]-start)/delta,(BOUNDS[axis+2]-start)/delta))
                low,high = max(low,a),min(high,b)
                if low > high: return False
        return True
    return False


def clean(node):
    if not isinstance(node,list): return node
    return [clean(x) for x in node if not (isinstance(x,list) and x[0] in ['uuid','tstamp'])]


def routing(tree):
    return sorted(digest(clean(s)) for s in tree if isinstance(s,list) and in_region(s))


def footprints(tree):
    return {next(uq(p[2]) for p in children(f,'property') if uq(p[1])=='Reference'):f for f in children(tree,'footprint')}


def electrical_footprint(f):
    props = {uq(p[1]): uq(p[2]) for p in children(f,'property')}
    return clean([f[1], [list(p) for p in sorted(props.items())], [x for x in f if isinstance(x,list) and x[0] in
        ['at','layer','pad','zone','attr','net_tie_pad_groups','fp_line','fp_arc','fp_poly','fp_circle']]])


def audit(path=ROOT/'nucula-v2.kicad_pcb'):
    with ZipFile(BASELINE) as z:
        old_text=z.read('nucula-v2.kicad_pcb').decode()
        sch=z.read('nfc.kicad_sch')
        original_export=parse(z.read('export-board.kicad_pcb').decode())
    assert hashlib.sha256(old_text.encode()).hexdigest() == '4e582fc67796c618ffb62488af51a3807b1540be308f1a315ecae28ff7b50e96'
    old=parse(old_text); new=parse(path.read_text())
    refs=json.loads((ROOT/'docs/pcb/constraints.json').read_text())['nfc_refs']+['A1']
    a,b=footprints(old),footprints(original_form(new,'footprint'))
    changes=[r for r in refs if digest(electrical_footprint(a[r]))!=digest(electrical_footprint(b[r]))]
    setup, baseline_setup=child(new,'setup'),child(original_export,'setup')
    checks={'nfc_schematic_identical_except_reviewed_substitutions':
                digest(parse(sch.decode()))==digest(original_form(parse((ROOT/'nfc.kicad_sch').read_text()),'symbol')),
            'all_43_NFC_footprints_identical_except_reviewed_substitutions':not changes,
            'all_NFC_tracks_and_vias_identical':routing(old)==routing(new),
            'submitted_stackup_and_via_process_identical': all(
                digest(children(setup,key))==digest(children(baseline_setup,key)) for key in
                ['stackup','filling','capping','covering','plugging','tenting'])}
    return {'passed':all(checks.values()),'checks':checks,'board_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'baseline_commit':COMMIT,'baseline_archive_sha256':hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
            'region_mm':BOUNDS,'NFC_references':refs,'changed_footprints':changes,
            'baseline_routing_objects':len(routing(old)),'current_routing_objects':len(routing(new)),
            'substitutions_sha256':hashlib.sha256(AMENDMENTS.read_bytes()).hexdigest(),
            'schematic_byte_identical_to_rev_A':sch==(ROOT/'nfc.kicad_sch').read_bytes(),
            'scope':'Rev-A copper, pads, placements, matching values and process preserved. Only explicitly reviewed purchasing metadata, C36/C37 tolerance and inductor fabrication body differ. RF substitute requires separate model validation and physical bring-up; original measured performance does not transfer automatically.'}

if __name__=='__main__':
    result=audit();(ROOT/'docs/pcb/nfc-rev-a-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
