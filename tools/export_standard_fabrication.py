#!/usr/bin/env python3
"""Export the verified standard-fabrication board for five bare PCBs/self assembly.

Run with KiCad's pcbnew-enabled Python. No orders or supplier uploads are made.
Historical JLCPCB releases remain immutable.
"""
import csv
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
import pcbnew as k

ROOT = Path(__file__).resolve().parents[1]
CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    spec = json.loads((ROOT/'docs/manufacturing-spec.json').read_text())
    assert spec['via_covering'] == 'Unfilled, uncapped, open through-vias'
    check = json.loads((ROOT/'docs/pcb/standard-fabrication-check.json').read_text())
    assert check['passed'] and check['board_sha256'] == sha(ROOT/'nucula-v2.kicad_pcb')
    assert check['drc_sha256'] == sha(ROOT/'docs/pcb/drc.json')
    assert json.loads((ROOT/'docs/pcb/layout-check.json').read_text())['passed']
    quality = json.loads((ROOT/'docs/pcb/routing-quality.json').read_text())
    assert quality['passed'] and quality['source_board_sha256'] == sha(ROOT/'nucula-v2.kicad_pcb'), 'Stale or failing routing-quality audit'
    verification = json.loads((ROOT/'docs/verification.json').read_text())
    for name, digest in verification['schematic_sha256'].items():
        assert sha(ROOT/name) == digest, 'Stale schematic verification: '+name
    simulations = json.loads((ROOT/'docs/simulation/results.json').read_text())
    assert simulations['simulations_completed'] == 261 and not simulations['solver_errors']
    for name, digest in simulations['source_sha256'].items():
        assert sha(ROOT/name) == digest, 'Stale simulation input: '+name
    out = ROOT/'manufacturing'/spec['release']
    out.mkdir(exist_ok=True)
    for name in ['gerbers','assembly','drawings','validation']:
        (out/name).mkdir(exist_ok=True)
    logs=[]
    def run(*args):
        logs.append([str(a).replace(str(ROOT),'${PROJECT}') for a in args])
        subprocess.run([CLI,*map(str,args)],check=True,cwd=ROOT)
    with tempfile.TemporaryDirectory(prefix='nucula-standard-export-') as tmp:
        tmp=Path(tmp)
        path=tmp/'nucula-v2.kicad_pcb'
        b=k.LoadBoard(str(ROOT/'nucula-v2.kicad_pcb'))
        b.GetDesignSettings().SetAuxOrigin(k.VECTOR2I(k.FromMM(50),k.FromMM(160)))
        expected=set();removed=[]
        for f in b.GetFootprints():
            nonpart=f.GetReference() in spec['non_components']
            if f.IsDNP() or nonpart:
                f.SetExcludedFromPosFiles(True)
                for pad in f.Pads():
                    layers=pad.GetLayerSet()
                    if layers.Contains(k.F_Paste) or layers.Contains(k.B_Paste):
                        layers.RemoveLayer(k.F_Paste);layers.RemoveLayer(k.B_Paste)
                        pad.SetLayerSet(layers);removed.append(f.GetReference()+'.'+pad.GetNumber())
                assert not any(g.GetLayer() in [k.F_Paste,k.B_Paste] for g in f.GraphicalItems())
            else:expected.add(f.GetReference())
        assert len(expected)==116
        k.SaveBoard(str(path),b)
        shutil.copyfile(path,out/'validation/export-board.kicad_pcb')
        run('pcb','export','gerbers','--layers','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts,F.Paste',
            '--use-drill-file-origin','--subtract-soldermask','-o',out/'gerbers',path)
        # KiCad exports its nominal CAD stack even without dielectric constraints.
        # Do not accidentally order those individual dielectric/copper thicknesses.
        job_path = out/'gerbers/nucula-v2-job.gbrjob'
        job = json.loads(job_path.read_text())
        job.pop('MaterialStackup', None)
        job['GeneralSpecs']['Size'] = dict(zip(['X', 'Y'], spec['board_size_mm']))
        job['GeneralSpecs']['ProjectId']['Revision'] = spec['release']
        job_path.write_text(json.dumps(job, indent=2)+'\n')
        run('pcb','export','drill','--format','excellon','--drill-origin','plot','--excellon-units','mm',
            '--excellon-zeros-format','decimal','--excellon-oval-format','route','--excellon-separate-th',
            '--generate-map','--map-format','pdf','--generate-report','--report-path',out/'drawings/drill-report.txt','-o',out/'gerbers',path)
        for p in (out/'gerbers').glob('*.pdf'):shutil.move(str(p),out/'drawings'/p.name)
        run('pcb','export','pos','--format','csv','--units','mm','--side','front','--use-drill-file-origin','--exclude-dnp',
            '-o',out/'assembly/placements.csv',path)
        rows=list(csv.DictReader((out/'assembly/placements.csv').open()))
        assert len(rows)==116 and {r['Ref'] for r in rows}==expected
        paste = (out/'gerbers/nucula-v2-F_Paste.gtp').read_text()
        paste_refs = set(re.findall(r'%TO.C,([^*]+)\*%', paste))
        assert paste_refs == expected, 'Stencil component set does not match assembly'
        plated = (out/'gerbers/nucula-v2-PTH.drl').read_text()
        assert 'T1C0.300' in plated and 'T3C0.700' in plated
        assert plated.count('\nM15\n') == 4, 'Expected four plated USB slots'
        run('pcb','export','ipcd356','-o',out/'nucula-v2.ipc',path)
        # Hide component catalogue fields in assembly drawings only.
        for f in b.GetFootprints():
            for field in f.GetFields():field.SetVisible(field.GetName()=='Reference')
        k.SaveBoard(str(path),b)
        run('pcb','export','pdf','--layers','F.Fab,F.Silkscreen,Edge.Cuts','--mode-single','--sketch-pads-on-fab-layers',
            '--crossout-DNP-footprints-on-fab-layers','--exclude-value','--black-and-white','--bg-color','#ffffff','--scale','0',
            '-o',out/'drawings/assembly-top.pdf',path)
        run('pcb','export','pdf','--layers','Edge.Cuts,Dwgs.User','--mode-single','--black-and-white','--bg-color','#ffffff','--scale','0',
            '-o',out/'drawings/fabrication-outline.pdf',path)
        run('pcb','export','pdf','--layers','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste','--common-layers','Edge.Cuts',
            '--mode-multipage','-o',out/'drawings/layers.pdf',path)
    for src,dest in [('docs/bom.csv','assembly/bom.csv'),('docs/manufacturing-spec.json','manufacturing-spec.json'),
                     ('manufacturing/contingency-2026-09-22/purchasing-5-boards.csv','assembly/purchasing-5-boards.csv'),
                     ('docs/pcb/drc.json','validation/drc.json'),('docs/pcb/layout-check.json','validation/layout-check.json'),
                     ('docs/pcb/standard-fabrication-check.json','validation/standard-fabrication-check.json'),
                     ('docs/pcb/standard-silk-audit.json','validation/standard-silk-audit.json'),
                     ('docs/pcb/standard-changes.json','validation/standard-changes.json'),
                     ('docs/pcb/routing-quality.json','validation/routing-quality.json'),
                     ('docs/pcb/routing-comparison.svg','drawings/routing-comparison.svg'),
                     ('docs/pcb/routing-comparison.png','drawings/routing-comparison.png'),
                     ('docs/pcb/display-clearance.svg','drawings/display-clearance.svg'),
                     ('docs/pcb/display-clearance.png','drawings/display-clearance.png'),
                     ('docs/verification.json','validation/schematic-verification.json'),('docs/simulation/results.json','validation/simulation-results.json')]:
        shutil.copyfile(ROOT/src,out/dest)
    (out/'validation/export-check.json').write_text(json.dumps({'passed':True,'placements':len(rows),
        'stencil_component_references_match_placements': sorted(paste_refs) == sorted(expected),
        'usb_plated_slots': 4, 'job_omits_custom_layer_construction': 'MaterialStackup' not in job,
        'dnp_paste_removed':removed,'source_board_sha256':sha(ROOT/'nucula-v2.kicad_pcb'),
        'export_board_sha256':sha(out/'validation/export-board.kicad_pcb'),'commands':logs},indent=2)+'\n')
    (out/'README.md').write_text('''# Standard fabrication / five-board contingency — routing review

Upload `nucula-v2-gerbers.zip`. Order five bare four-layer FR-4 boards, nominal
1.6 mm, green mask, white legend, ENIG, standard copper and supplier stackup.
No controlled impedance, via filling/capping, or custom dielectric construction
is required. Request normal electrical testing. Keep the keyboard attached.
The Gerber job identifies the four layers and nominal board thickness; its
individual material-stack dimensions are deliberately omitted. Follow the
supplier's standard four-layer construction and the accompanying specification.

Order a 100 µm top stencil using the included F.Paste Gerber. DNP paste and the
optional ESP32 centre-pad paste are omitted. Fit the unchanged 116 components
per board using `assembly/bom.csv` and the updated assembly drawing.
The five-board purchasing list carries dated vendor observations and proposed
substitutes, not reserved stock or a delivery promise. The engineering BOM
retains its original MPNs; substitution notes in the purchasing list still apply.

`drawings/display-clearance.png` marks a 17.70 × 5.00 mm component-free ribbon
insertion area above DS1. Tracks, vias and soldermask-covered copper are permitted
there. This annotated review image is not a fabrication layer.

These files supersede the older filled-via contingency Gerbers. The archived
JLCPCB r2 package describes the board already submitted and remains unchanged.
They also supersede the first standard-fabrication package: routing has been
rebuilt with full pad/via entries and 45-degree traces. The independent geometry
audit checks every trace, rejects connections relying only on edge overlap,
and reports no acute return bends or exposed segments shorter than 0.20 mm.
`drawings/routing-comparison.png` shows two areas before and after the repair.
Validation reports accompany this package; supplier CAM acceptance and physical
prototype testing remain separate from the recorded software checks.

Native DRC has zero errors, zero unconnected items and zero schematic-parity
findings. Its 40 cosmetic warnings are documented: 37 footprint-library
differences from front-legend clipping around open vias, two existing ESP32
outline/edge warnings, and one back-artwork/mask overlap clipped in Gerbers.
The independent geometry audit verifies that legend clipping changed no pads,
models, rules or other footprint geometry. The 261 simulation cases exercise
partial circuit models; they do not validate PCB parasitics or full operation.
The layout report retains two USB advisories: 0.9915 mm U4-to-series-resistor
length mismatch and two uncovered ground-reference samples out of 2,171.
USB signal integrity has not been qualified.
''')
    with zipfile.ZipFile(out/'nucula-v2-gerbers.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted((out/'gerbers').iterdir()):z.write(p,p.name)
    files=[p for p in out.rglob('*') if p.is_file() and p.name!='manifest.json']
    (out/'manifest.json').write_text(json.dumps({'release':spec['release'],'source_board_sha256':sha(ROOT/'nucula-v2.kicad_pcb'),
        'files_sha256':{str(p.relative_to(out)):sha(p) for p in sorted(files)}},indent=2)+'\n')
    with zipfile.ZipFile(out.with_name(out.name+'-package.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.rglob('*')):
            if p.is_file():z.write(p,str(p.relative_to(out)))
    print('Exported',out)


if __name__=='__main__':main()
