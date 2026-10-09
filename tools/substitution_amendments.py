"""Reverse ONLY the reviewed purchasing metadata and inductor fab-body edits.

No pads, placement, values, nets, routing, mask, paste or rules are normalized.
Unexpected field contents stay unchanged and therefore fail baseline comparison.
"""
import copy
import json
from pathlib import Path
from kicad_sexpr import child, children, uq

ROOT = Path(__file__).resolve().parents[1]
AMENDMENTS = ROOT/'docs/components/substitutions-2026-10-09/amendments.json'

def original_form(tree, kind):
    tree = copy.deepcopy(tree)
    doc = json.loads(AMENDMENTS.read_text())
    changes = doc['footprints'] if kind=='footprint' else doc['schematic_properties']
    for node in children(tree, kind):
        properties = {uq(p[1]):p for p in children(node,'property')}
        ref = uq(properties['Reference'][2]) if 'Reference' in properties else None
        if ref not in changes:
            continue
        edits = changes[ref]['properties'] if kind=='footprint' else changes[ref]
        for name, edit in edits.items():
            if name=='Footprint' and kind=='footprint':
                if uq(node[1])==edit['new']:node[1]=json.dumps(edit['old'])
            elif name in properties and uq(properties[name][2])==edit['new']:
                properties[name][2]=json.dumps(edit['old'])
        if kind=='footprint' and ref in ['L2','L3']:
            descr=child(node,'descr')
            if descr and uq(descr[1])=='Coilcraft 0805CS on retained rev-A lands; terminal coverage verified; see substitution qualification':
                descr[1]=json.dumps("Coilcraft 0805HP recommended land pattern: 1.02 x 1.98 mm pads, 1.12 mm gap; manufacturer's drawing 0805hpd")
            for rect in children(node,'fp_rect'):
                if uq(child(rect,'layer')[1])!='F.Fab':continue
                start,end=child(rect,'start'),child(rect,'end')
                if list(map(float,start[1:]))==[-1.145,-.865] and list(map(float,end[1:]))==[1.145,.865]:
                    start[1]='-1.105';end[1]='1.105'
    return tree
