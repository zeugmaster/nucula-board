#!/usr/bin/env python3
"""Export the verified standard-fabrication board and assembly inputs.

Run with KiCad's pcbnew-enabled Python. No orders or supplier uploads are made.
Historical JLCPCB releases remain immutable.
"""
import csv
import argparse
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
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, help='Alternate output directory for validation exports; preserves archived releases.')
    args = ap.parse_args()
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
    mini = json.loads((ROOT/'docs/pcb/mini-module-check.json').read_text())
    assert mini['passed'] and mini['board_sha256'] == sha(ROOT/'nucula-v2.kicad_pcb')
    assert mini['netlist_sha256'] == sha(ROOT/'docs/netlist.xml')
    mounting = json.loads((ROOT/'docs/pcb/mounting-holes-check.json').read_text())
    assert mounting['passed'] and mounting['board_sha256'] == sha(ROOT/'nucula-v2.kicad_pcb')
    battery = json.loads((ROOT/'docs/assembly/battery-connector-check.json').read_text())
    assert battery['passed'] and battery['board_sha256'] == sha(ROOT/'nucula-v2.kicad_pcb')
    simulations = json.loads((ROOT/'docs/simulation/results.json').read_text())
    assert simulations['simulations_completed'] == 261 and not simulations['solver_errors']
    for name, digest in simulations['source_sha256'].items():
        assert sha(ROOT/name) == digest, 'Stale simulation input: '+name
    out = args.out.resolve() if args.out else ROOT/'manufacturing'/spec['release']
    if args.out:
        spec = dict(spec, release=out.name, release_status='Validation export only; see current hardware findings.')
        spec['dnp'] = [r['Reference'] for r in csv.DictReader((ROOT/'docs/bom.csv').open()) if r['DNP'] == 'yes']
    if (out / 'manifest.json').exists():
        raise SystemExit('Refusing to overwrite an archived export. Choose a new --out directory.')
    out.mkdir(parents=True, exist_ok=True)
    for name in ['gerbers','assembly','drawings','validation']:
        (out/name).mkdir(exist_ok=True)
    logs=[]
    def run(*args):
        logs.append([str(a).replace(str(ROOT),'${PROJECT}').replace(str(tmp),'${EXPORT_TMP}') for a in args])
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
        assert len(expected)==119
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
        assert len(rows)==119 and {r['Ref'] for r in rows}==expected
        # Keep the KiCad anchor; never invent catalogue body-centre offsets.
        # Assembly houses must verify pin alignment in their placement preview.
        with (out/'assembly/jlcpcb-cpl.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=['Designator','Mid X','Mid Y','Layer','Rotation'], lineterminator='\n')
            writer.writeheader()
            writer.writerows({'Designator': r['Ref'], 'Mid X': r['PosX'], 'Mid Y': r['PosY'],
                              'Layer': 'Top', 'Rotation': f"{float(r['Rot']) % 360:.6f}"} for r in rows)
        bom_rows = list(csv.DictReader((ROOT/'docs/assembly/jlcpcb-bom.csv').open()))
        bom_refs = [r.strip() for row in bom_rows for r in row['Designator'].split(',')]
        assert len(bom_refs) == len(expected) and set(bom_refs) == expected
        fps = {f.GetReference(): f for f in b.GetFootprints()}
        for row in bom_rows:
            for ref in row['Designator'].split(','):
                f = fps[ref.strip()]
                assert f.GetFieldText('MPN') == row['Comment']
                assert f.GetFieldText('LCSC') == row['LCSC Part #']
        with (out/'assembly/pad-coordinates.csv').open('w', newline='') as stream:
            writer = csv.writer(stream, lineterminator='\n')
            writer.writerow(['Reference','Pad','Net','X_mm','Y_mm'])
            for ref in sorted(expected):
                for pad in fps[ref].Pads():
                    if pad.GetNumber() and pad.IsOnLayer(k.F_Cu):
                        writer.writerow([ref,pad.GetNumber(),pad.GetNetname(),
                                         round(k.ToMM(pad.GetPosition().x)-50,6),
                                         round(160-k.ToMM(pad.GetPosition().y),6)])
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
    run('sch','export','pdf','-o',out/'drawings/schematic.pdf',ROOT/'nucula-v2.kicad_sch')
    for src,dest in [('docs/bom.csv','assembly/bom.csv'),('docs/manufacturing-spec.json','manufacturing-spec.json'),
                     ('docs/mounting-holes.md','assembly/mounting-holes.md'),
                     ('docs/pcb/mounting-holes.png','drawings/mounting-holes.png'),
                     ('docs/pcb/mounting-holes.svg','drawings/mounting-holes.svg'),
                     ('docs/pcb/mounting-holes-check.json','validation/mounting-holes-check.json'),
                     ('docs/pcb/mounting-footprint-amendments.json','validation/mounting-footprint-amendments.json'),
                     ('libraries/Nucula_Project.pretty/MountingHole_2.2mm_M2_5.5mm_Keepout.kicad_mod','assembly/M2.kicad_mod'),
                     ('docs/assembly/jlcpcb-bom.csv','assembly/jlcpcb-bom.csv'),
                     ('LICENSES/Espressif-KiCad-libraries.md','assembly/U3-library-license.md'),
                     ('docs/esp32-mini.md','assembly/esp32-mini.md'),
                     ('docs/pcb/mini-module-check.json','validation/mini-module-check.json'),
                     ('docs/pcb/mini-footprint-amendments.json','validation/mini-footprint-amendments.json'),
                     ('docs/pcb/mini-outline-amendment.json','validation/mini-outline-amendment.json'),
                     ('libraries/Nucula_Project.pretty/ESP32-C3-MINI-1-H4X_NoEPADSolder.kicad_mod','assembly/U3.kicad_mod'),
                     ('parts documentation/esp32-c3-mini-1_datasheet_en.pdf','assembly/ESP32-C3-MINI-1-datasheet.pdf'),
                     ('docs/pcb/mini-module.png','drawings/mini-module.png'),
                     ('docs/battery-connector.md','assembly/battery-connector.md'),
                     ('parts documentation/JST-SH-side-entry-2026-10-07.pdf','assembly/JST-SH-datasheet.pdf'),
                     ('libraries/Nucula_Project.pretty/JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal.kicad_mod','assembly/J2.kicad_mod'),
                     ('libraries/Nucula_Project.pretty/Battery_Lead_SolderPads_2x2.2x2.5mm_P3.4mm.kicad_mod','assembly/J6.kicad_mod'),
                     ('docs/assembly/battery-connector-check.json','validation/battery-connector-check.json'),
                     ('docs/pcb/battery-footprint-amendments.json','validation/battery-footprint-amendments.json'),
                     ('docs/pcb/battery-wire-pad-amendments.json','validation/battery-wire-pad-amendments.json'),
                     ('docs/pcb/battery-connector.png','drawings/battery-connector.png'),
                     ('docs/assembly/purchasing-5-boards.csv','assembly/purchasing-5-boards.csv'),
                     ('docs/bringup/usb-backfeed-check.json','validation/usb-backfeed-check.json'),
                     ('docs/bringup/usb-backfeed-fix.md','validation/usb-backfeed-fix.md'),
                     ('docs/bringup/backfeed-analysis/results.json','validation/usb-spice-results.json'),
                     ('docs/bringup/measurements/rev-A-usb-battery-2026-10-06.pdf','validation/rev-A-usb-battery-2026-10-06.pdf'),
                     ('docs/assembly/jlc-stock-snapshot.json','assembly/jlc-stock-snapshot.json'),
                     ('docs/pcb/usb-protection.png','drawings/usb-protection.png'),
                     ('docs/pcb/usb-switch.png','drawings/usb-switch.png'),
                     ('docs/pcb/usb-footprint-amendments.json','validation/usb-footprint-amendments.json'),
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
    report_path = out/'validation/usb-backfeed-fix.md'
    report_path.write_text(report_path.read_text().replace('../pcb/', '../drawings/')
        .replace('measurements/rev-A-usb-battery-2026-10-06.pdf', 'rev-A-usb-battery-2026-10-06.pdf')
        .replace('backfeed-analysis/results.json', 'usb-spice-results.json'))
    report_path = out/'assembly/battery-connector.md'
    report_path.write_text(report_path.read_text().replace('pcb/battery-connector.png', '../drawings/battery-connector.png')
                          .replace('assembly/battery-connector-check.json', '../validation/battery-connector-check.json'))
    report_path = out/'assembly/esp32-mini.md'
    report_path.write_text(report_path.read_text().replace('pcb/mini-module.png', '../drawings/mini-module.png')
                          .replace('](pcb/', '](../validation/')
                          .replace('../libraries/README.md', 'U3-library-license.md'))
    report_path = out/'assembly/mounting-holes.md'
    report_path.write_text(report_path.read_text().replace('pcb/mounting-holes.png', '../drawings/mounting-holes.png')
                          .replace('](pcb/', '](../validation/'))
    (out/'validation/export-check.json').write_text(json.dumps({'passed':True,'placements':len(rows),
        'stencil_component_references_match_placements': sorted(paste_refs) == sorted(expected),
        'usb_plated_slots': 4, 'job_omits_custom_layer_construction': 'MaterialStackup' not in job,
        'dnp_paste_removed':removed,'source_board_sha256':sha(ROOT/'nucula-v2.kicad_pcb'),
        'export_board_sha256':sha(out/'validation/export-board.kicad_pcb'),'commands':logs},indent=2)+'\n')
    (out/'README.md').write_text('''# Six M2 mounts and MINI-1 — engineering prototype

This package contains the current October display mapping, USB backfeed redesign,
the MINI-1-H4X module, resized flush antenna notch, 2.95 mm JST-SH J2
connector, and J6 direct battery wire solder pads. U3 must be C41349510; the
WROOM footprint does not fit this PCB. See assembly/esp32-mini.md.
Six 2.2 mm non-plated M2 clearance holes are included: four main-board corners
and the lower two keyboard corners. Hardware up to 5.0 mm diameter has a
5.5 mm copper/component keepout. See assembly/mounting-holes.md and the
dimensioned review in drawings/mounting-holes.png. H1-H6 are not assembly parts.
Antenna-side ground lands have 0.30 mm edge clearance (0.25 mm minimum);
other copper retains 0.50 mm. Internal notch corners have 0.5 mm radius.
Use firmware compatible with C3 chip revision 1.1 (ESP-IDF 5.4+ recommended).
It supersedes the MINI package without mounts and earlier packages for the next prototype.
Revised hardware still requires the USB/display bring-up described in validation/.

Fabrication: five four-layer FR-4 boards, nominal 1.6 mm, green mask, white legend,
ENIG and the supplier standard stackup. Upload nucula-v2-gerbers.zip. No controlled
impedance, custom dielectric construction, or via filling/capping. Request normal
electrical test. Keep the keyboard attached. Use a 100 um top stencil; DNP and
optional ESP32 centre-joint paste are omitted.

Assembly: 119 populated components per board, all on top. Use assembly/bom.csv
or assembly/jlcpcb-bom.csv, assembly/placements.csv or assembly/jlcpcb-cpl.csv,
and drawings/assembly-top.pdf. CPL coordinates preserve KiCad anchors, with no
unverified offsets or rotation corrections. Confirm all pin alignment in the
supplier preview; assembly/pad-coordinates.csv provides independent pad locations.
The public stock snapshot is dated per part and is not reserved inventory.

J2 MUST be JST SM02B-SRSS-TB(LF)(SN), JLCPCB C160402, side-entry SMT,
1.00 mm pitch and 2.95 mm above the PCB when mated. Do not substitute PH, ZH,
or top-entry SH. Use an SHR-02V-S-B battery plug with SSH-003T-P0.2-H contacts
and 28 AWG leads. THE PREVIOUS JST-PH BATTERY LEAD DOES NOT FIT.
The opening faces the LEFT edge (negative X), with the lead parallel to the
PCB. Pin 1 = battery positive, pin 2 = GND; both hold-down tabs are unconnected.
Check the actual lead polarity. See assembly/battery-connector.md and
assembly/JST-SH-datasheet.pdf, plus drawings/battery-connector.png.
At the (50,160) export origin J2 is X=3.700 mm, Y=59.100 mm, rotation=270 deg
in the JLC CPL. Positive pad: (5.700,59.600); ground pad: (5.700,58.600) mm.

J6 provides two 2.2 x 2.5 mm exposed copper lands above J2 for hand-soldered
battery leads. Viewed from the top with USB at the bottom: left = GND (pin 2),
right = BAT+ (pin 1). Both are labeled on the front silkscreen. The pads are
parallel with J2; use ONE battery connection at a time. No component, stencil
paste or pick-and-place entry is required for J6. At the export origin, J6's
BAT+ pad is (6.100,64.000), and GND is (2.700,64.000) mm.

The connector is rated 1 A with 28 AWG wire. The user accepts intermittent
peaks above this rating for the prototype; no new current limiter or operating
restriction is added. This acceptance is not a manufacturer pulse-current
rating or measured thermal qualification. Charging remains 100 mA.

Native DRC: zero errors, zero unconnected items and zero schematic-parity findings.
The 43 remaining warnings comprise 40 reviewed footprint-library differences
and three silkscreen/mask clipping warnings. No dangling copper remains.
See the hash-bound validation reports for placement, routing, stencil, polarity,
plug-access and simulation checks. Electrical/RF/ESD and enclosure qualification
remain physical prototype work. September packages remain historical records.
''')
    if args.out:
        (out / 'manufacturing-spec.json').write_text(json.dumps(spec, indent=2) + '\n')
        (out / 'README.md').write_text(
            '# Validation export — not a fabrication release\n\n'
            'Generated from the current board to check Gerber, drill, stencil and placement output. '
            'Historical manufacturing packages are unchanged.\n\n'
            'Display ribbon mapping is reversed at the fixed Hirose socket: panel pin n = socket pad 25-n. '
            'The USB redesign uses ground-referenced data TVS protection and a VBUS-controlled data switch; '
            'its physical operation, reconnection and ESD performance still require testing on revised hardware. '
            'Do not use this export as authorization to order boards.\n\n'
            'Consult the current schematic verification, routing, fabrication and simulation reports '
            'included under validation/. The older routing-comparison drawing is historical.\n')
    with zipfile.ZipFile(out/'nucula-v2-gerbers.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted((out/'gerbers').iterdir()):z.write(p,p.name)
    files=[p for p in out.rglob('*') if p.is_file() and p.name!='manifest.json']
    (out/'manifest.json').write_text(json.dumps({'release':spec['release'],'source_board_sha256':sha(ROOT/'nucula-v2.kicad_pcb'),
        'source_inputs_sha256':{name:sha(ROOT/name) for name in [
            'nucula-v2.kicad_pcb','nucula-v2.kicad_pro','nucula-v2.kicad_dru','power-mcu.kicad_sch',
            'libraries/Nucula_Project.kicad_sym',
            'libraries/Nucula_Project.pretty/ESP32-C3-MINI-1-H4X_NoEPADSolder.kicad_mod',
            'libraries/Nucula_Project.3dshapes/ESP32-C3-MINI-1.STEP',
            'tools/check_mini_module.py','docs/esp32-mini.md',
            'tools/check_mounting_holes.py','docs/mounting-holes.md',
            'libraries/Nucula_Project.pretty/MountingHole_2.2mm_M2_5.5mm_Keepout.kicad_mod',
            'libraries/Nucula_Project.pretty/JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal.kicad_mod',
            'libraries/Nucula_Project.pretty/Battery_Lead_SolderPads_2x2.2x2.5mm_P3.4mm.kicad_mod',
            'tools/check_battery_connector.py','tools/check_standard_export.py',
            'tools/export_standard_fabrication.py','docs/battery-connector.md',
            'docs/manufacturing-spec.json','docs/assembly/jlc-stock-snapshot.json']},
        'files_sha256':{str(p.relative_to(out)):sha(p) for p in sorted(files)}},indent=2)+'\n')
    with zipfile.ZipFile(out.with_name(out.name+'-package.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.rglob('*')):
            if p.is_file():z.write(p,str(p.relative_to(out)))
    package = out.with_name(out.name+'-package.zip')
    package.with_suffix('.zip.sha256').write_text(sha(package)+'  '+package.name+'\n')
    print('Exported',out)


if __name__=='__main__':main()
