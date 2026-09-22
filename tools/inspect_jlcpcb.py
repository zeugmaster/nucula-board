#!/usr/bin/env python3
"""Independently read exported Gerbers/drills, draw fabrication notes, seal package.

Requires gerbonara==1.5.0, reportlab and rsvg-convert. No KiCad Python required.
"""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import subprocess
import warnings
import zipfile

from gerbonara import LayerStack, GerberFile, ExcellonFile
from gerbonara.graphic_objects import Flash, Line, Arc
from gerbonara.utils import MM
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('release', type=Path)
    args = ap.parse_args()
    out = args.release.resolve()
    manifest = json.loads((out / 'manifest.json').read_text())
    for name, digest in manifest['artifacts_sha256'].items():
        assert sha(out / name) == digest, 'Modified release artifact: ' + name
    g = out / 'gerbers'
    spec = json.loads((out / 'manufacturing-spec.json').read_text())
    # Native KiCad export is an independent reference for the CSV conversion.
    # A pass here does not certify JLC's own catalogue model/pin registration.
    assert not spec['local_placement_offsets_mm'], 'Review any new catalogue offsets independently'
    with (out / 'validation/kicad-positions.csv').open() as f:
        native_rows = list(csv.DictReader(f))
    with (out / 'assembly/jlcpcb-cpl.csv').open() as f:
        cpl_rows = list(csv.DictReader(f))
    with (out / 'assembly/jlcpcb-bom.csv').open() as f:
        bom_refs = [r.strip() for row in csv.DictReader(f) for r in row['Designator'].split(',')]
    native = {row['Ref']: row for row in native_rows}
    cpl = {row['Designator']: row for row in cpl_rows}
    assert len(native_rows) == len(native) == len(cpl_rows) == len(cpl) == len(bom_refs) == len(set(bom_refs)) == 116
    assert set(native) == set(cpl) == set(bom_refs)
    for ref, row in cpl.items():
        original = native[ref]
        assert abs(float(row['Mid X'])-float(original['PosX'])) < 1e-6, ref
        assert abs(float(row['Mid Y'])-float(original['PosY'])) < 1e-6, ref
        expected_rotation = (float(original['Rot'])+spec['rotation_corrections_deg'].get(ref,0))%360
        assert abs(float(row['Rotation'])-expected_rotation) < 1e-6, ref
        assert original['Side'] == 'top' and row['Layer'] == 'Top', ref
    for ref, expected in {'U3':(47.9,53.86,270), 'DS1':(30,51.15,180), 'J2':(6.75,59.1,90)}.items():
        assert tuple(float(cpl[ref][k]) for k in ['Mid X','Mid Y','Rotation']) == expected
    with warnings.catch_warnings(record=True) as caught:
        stack = LayerStack.open(g)
        pth = ExcellonFile.open(g / 'nucula-v2-PTH.drl')
        npth = ExcellonFile.open(g / 'nucula-v2-NPTH.drl')
    parser_warnings = sorted(set(str(w.message).split(':')[-1].strip() for w in caught))
    assert all('G90 header statement found after end of header' in w for w in parser_warnings)
    assert len(stack.graphic_layers) == 11
    copper = {side for (side, use) in stack.graphic_layers if use == 'copper'}
    assert copper == {'top', 'bottom', 'inner_1', 'inner_2'}
    counts = Counter(round(o.aperture.diameter, 6) for o in pth.objects if isinstance(o, Flash))
    assert counts == {0.2: 32, 0.3: 301, 0.4: 2, 1.0: 19}, counts
    slots = [o for o in pth.objects if not isinstance(o, Flash)]
    assert len(slots) == 4 and all(isinstance(o, Line) and o.aperture.diameter == .6 for o in slots)
    assert len(pth.objects) == 358 and len(npth.objects) == 30
    bites = {(round(o.x, 6), round(o.y, 6)) for o in npth.objects if o.aperture.diameter == .6}
    assert bites == {(float(x), y) for x in list(range(9,16))+list(range(45,52)) for y in [34.7,37.3]}
    assert all(isinstance(o, Flash) for o in npth.objects)
    for filename, flag in [('nucula-v2-PTH.drl', 'Plated'), ('nucula-v2-NPTH.drl', 'NonPlated')]:
        assert f'TF.FileFunction,{flag}' in (g / filename).read_text()
    outline = stack.outline
    graph = defaultdict(set)
    for obj in outline.objects:
        assert isinstance(obj, (Line, Arc))
        a, b = (round(obj.x1,6),round(obj.y1,6)), (round(obj.x2,6),round(obj.y2,6))
        graph[a].add(b)
        graph[b].add(a)
    assert all(len(v) == 2 for v in graph.values()), 'Open/branching outline'
    pending, loops = set(graph), []
    while pending:
        todo, seen = [next(iter(pending))], set()
        while todo:
            n = todo.pop()
            if n in seen:
                continue
            seen.add(n)
            todo.extend(graph[n] - seen)
        pending -= seen
        loops.append(seen)
    assert len(loops) == 3, 'Expected one outer contour and two internal slots'
    outer = max(loops, key=len)
    assert (min(p[0] for p in outer), max(p[0] for p in outer),
            min(p[1] for p in outer), max(p[1] for p in outer)) == (0,60,0,110)
    paste = stack.graphic_layers[('top','paste')]
    flashes = [o for o in paste.objects if isinstance(o, Flash)]
    regions = [o for o in paste.objects if not isinstance(o, Flash)]
    assert len(flashes) == 360 and len(regions) == 24
    pasted_refs = {o.attrs['.C'][0] for o in flashes if '.C' in o.attrs}
    assert not pasted_refs & set(spec['dnp'] + spec['non_components'])
    assert len(pasted_refs) == 116, 'Every populated footprint must have paste'
    assert not stack.graphic_layers[('bottom','paste')].objects
    region_centers = []
    for o in regions:
        (x1,y1),(x2,y2) = o.bounding_box(MM)
        assert abs(x2-x1-.25) < 1e-6 and abs(y2-y1-1.3) < 1e-6
        region_centers.append((round((x1+x2)/2,6),round((y1+y2)/2,6)))
    assert set(region_centers) == {(24.25+i*.5,49.3) for i in range(24)}
    u6 = [o for o in flashes if o.attrs.get('.C') == ('U6',) and
          abs(o.x-25.9375)<2 and abs(o.y-90.25)<2]
    assert len(u6) == 9, 'U6 exposed-pad windowing missing'
    # Check actual plotted copper, mask and paste, independently of pcbnew.
    usb_holes = [o for o in npth.objects if o.aperture.diameter == .65]
    assert {(o.x, o.y) for o in usb_holes} == {(6.,51.), (6.,45.22)}
    usb_clearances = []
    for use in ['copper', 'mask', 'paste']:
        lands = [o for o in stack.graphic_layers[('top',use)].objects
                 if isinstance(o,Flash) and abs(o.x-7.095)<1e-6 and
                 any(abs(o.y-y)<1e-6 for y in [51.31,44.91])]
        assert len(lands) == 4, (use, 'Missing J1 overlapping ground lands')
        assert {round(o.y,6) for o in lands} == {51.31,44.91}
        for o in lands:
            (x1,y1),(x2,y2) = o.bounding_box(MM)
            assert abs(x2-x1-1.11)<1e-6 and abs(y2-y1-.6)<1e-6
            assert abs(x1-6.54)<1e-6 and abs(x2-7.65)<1e-6
            assert o.aperture.macro.name == 'RoundRect'
            # KiCad's macro specifies corner radius followed by corner centers.
            expected = (.15,-.405,.15,-.405,-.15,.405,-.15,.405,.15,0.)
            assert len(o.aperture.parameters) == len(expected)
            assert all(abs(a-b)<1e-6 for a,b in zip(o.aperture.parameters,expected))
            radius = o.aperture.parameters[0]
            if use == 'copper':
                for hole in usb_holes:
                    dx = max(abs(hole.x-o.x)-((x2-x1)/2-radius),0)
                    dy = max(abs(hole.y-o.y)-((y2-y1)/2-radius),0)
                    usb_clearances.append(math.hypot(dx,dy)-radius-hole.aperture.diameter/2)
    assert abs(min(usb_clearances)-.233308)<1e-6 and min(usb_clearances)>.20
    # A plated via is intentionally filled/capped; ensure all 335 are unambiguously selected.
    assert sum(counts[d] for d in [.2,.3,.4]) == 335
    h,w,t,s,er = spec['prepreg_mm'],.15,spec['outer_copper_mm'],.21,spec['prepreg_er']
    z0 = 87/math.sqrt(er+1.41)*math.log(5.98*h/(.8*w+t))
    zdiff = 2*z0*(1-.48*math.exp(-.96*s/h))
    report = {
        'inspected_utc': datetime.now(timezone.utc).isoformat(),
        'gerbonara_version': importlib.metadata.version('gerbonara'),
        'checks_passed': True, 'parser_warnings': parser_warnings,
        'placement': {'rows':len(cpl), 'matches_native_kicad_origins':True,
                      'matches_bom_references':True, 'rotation_conversion_checked':True,
                      'unverified_body_center_offsets_removed':['U3','DS1','J2'],
                      'jlc_catalogue_pin_alignment':'Pending user review in JLCPCB 2D viewer'},
        'parser_warning_review': 'KiCad G90 after M95 is accepted as absolute coordinates; all hole coordinates checked',
        'copper_layers': sorted(copper), 'closed_outline_contours': len(loops),
        'board_envelope_mm': [60,110], 'pth_features': len(pth.objects),
        'pth_round_holes_by_diameter_mm': dict(counts), 'pth_slots': len(slots),
        'npth_features': len(npth.objects), 'mouse_bite_holes': len(bites),
        'top_paste_flashes': len(flashes), 'ds1_paste_regions': len(regions),
        'u6_ep_paste_windows': len(u6), 'dnp_paste_absent': True,
        'filled_capped_round_holes': 335,
        'usb_connector': {'copper_mask_paste_ground_lands_mm': [1.11,.6],
                          'npth_to_ground_land_mm': round(min(usb_clearances),6),
                          'minimum_required_mm': .20, 'locating_holes_unchanged': True},
        'usb_impedance_screening': {
            'method': 'IPC-2141 microstrip approximation; no soldermask; not a field solver',
            'w_mm': w, 'gap_mm': s, 'h_mm': h, 't_mm': t, 'er': er,
            'single_ended_ohms': round(z0,3), 'differential_ohms': round(zdiff,3),
            'fabricator_confirmation_required': True}}
    (out / 'validation/gerber-readback.json').write_text(json.dumps(report,indent=2)+'\n')

    def svg_png(name, svg, width=1200):
        sp = out / 'drawings' / (name+'.svg')
        pp = sp.with_suffix('.png')
        sp.write_text(str(svg))
        subprocess.run(['rsvg-convert','--background-color','white','-w',str(width),'-o',str(pp),str(sp)],check=True)
        return pp

    for side in ['top','bottom']:
        svg_png('gerber-'+side, stack.to_pretty_svg(side=side,margin=1,
            colors={'copper':'#c9ad68','mask':'#18191ce8','paste':'#999999',
                    'silk':'#ffffff','drill':'#555555','outline':'#999999'}))
    for (side,use), layer in stack.graphic_layers.items():
        if use == 'copper':
            svg_png('copper-'+side,layer.to_svg(force_bounds=((-1,-1),(61,111))))
    svg_png('paste-top',paste.to_svg(force_bounds=((-1,-1),(61,111))))
    outline_png = svg_png('outline',outline.to_svg(force_bounds=((-1,-1),(61,111))))
    # Actual drill/outline data, with only those layers displayed.
    svg_png('drills-and-outline', stack.to_svg(side_re='mechanical',drills=True,
                colors={'mechanical outline':'black','drill pth':'#2863b5',
                        'drill npth':'#bd241e','drill unknown':'#bd241e'},
                force_bounds=((-1,-1),(61,111))))
    for use in ['copper','mask','paste']:
        svg_png('usb-'+use, stack.to_svg(side_re='top',drills=True,
                    colors={'top '+use:'#2863b5','drill npth':'#bd241e'},
                    force_bounds=((4.8,43.9),(8.8,52.3))), width=700)
    c = canvas.Canvas(str(out / 'drawings/fabrication-notes.pdf'),pagesize=A4)
    c.setTitle('Nucula v2 - fabrication and assembly specification')
    c.setFillColorRGB(1,1,1)
    c.rect(0,0,*A4,stroke=0,fill=1)
    c.setFillColorRGB(0,0,0)
    c.setFont('Helvetica-Bold',16)
    c.drawString(35,800,'NUCULA v2  /  JLCPCB')
    c.setFont('Helvetica',10)
    c.drawString(35,780,'10 prototypes - 2026-09-21 - quotation / CAM review')
    c.setFillColorRGB(.65,.1,.05)
    c.drawString(35,760,'Pending final supplier stackup, carrier and placement review')
    c.setFillColorRGB(0,0,0)
    style = ParagraphStyle('notes',fontName='Helvetica',fontSize=9,leading=13)
    notes = [
        '<b>FABRICATION</b><br/>4 layers; FR-4; 1.6 mm; black mask; white silk; ENIG. '
        '1 oz outer / 0.5 oz inner. JLC04161H-3313. Electrical test required.',
        '<b>LAYER ORDER</b><br/>F.Cu / In1.Cu / In2.Cu / B.Cu.<br/>'
        '35 / 15.2 / 15.2 / 35 micrometre copper; 0.0994 mm surface prepreg; 1.265 mm core.',
        '<b>VIA FILL</b><br/>Epoxy fill and copper cap all 0.20, 0.30 and 0.40 mm plated round holes '
        '(335). Includes U3 thermal holes. Leave 0.60 mm slots, 1.00 mm headers and all NPTH open.',
        '<b>ASSEMBLY</b><br/>Top only. 116 placements, 55 BOM groups. Add supplier carrier, '
        'fiducials and tooling. Preserve ESP32 overhang. Keyboard remains attached.',
        '<b>USB CONNECTOR</b><br/>J1 outer ground lands trimmed 0.04 mm at the hole-facing end. '
        'NPTH-to-pad clearance 0.233 mm; meets 0.20 mm minimum. Holes and shell stakes unchanged.',
        '<b>USB</b><br/>90 ohm differential target, +/-10%; B.Cu referenced to In2.Cu; '
        '0.15 mm traces / 0.21 mm gap. Confirm with actual stackup before production.'
    ]
    y=735
    for text in notes:
        p=Paragraph(text,style); _,height=p.wrap(295,200)
        p.drawOn(c,35,y-height); y-=height+14
    c.drawImage(str(outline_png),365,405,width=62*mm,height=112*mm)
    c.setFont('Helvetica',9)
    c.drawCentredString(365+31*mm,390,'60 mm finished envelope')
    c.saveState(); c.translate(555,405+56*mm); c.rotate(90)
    c.drawCentredString(0,0,'110 mm finished envelope'); c.restoreState()
    c.drawString(365,372,'Outline from exported Gerber')
    c.setFont('Helvetica-Bold',11)
    c.drawString(35,285,'FUNCTIONAL KEYBOARD - DO NOT FACTORY-SEPARATE')
    details = [
        'Lower keyboard: 60 x 35 mm. Routed gap: 2 mm. Two 4.5 mm support-tab necks.',
        '28 NPTH mouse bites: 0.60 mm diameter; 1.00 mm pitch; 2 rows of 7 per tab.',
        'Tab centers X=12 and 48 mm in export coordinates. Hole rows Y=34.7 and 37.3 mm.',
        'Central electrical bridge: 3.5 mm wide; centered X=30 mm. Five traces cross it.',
        'User cut at Y=36 mm is a drawing instruction only. Do not route or V-score here.',
        'Drills: 354 plated round holes + 4 plated slots; 30 NPTH holes; 2 closed routed slots.',
        'Origin: lower-left envelope corner. +X right, +Y up, millimetres. Top view.',
        'DNP: C7 C8 C34 C35 C38 C39 J3 J4 J5 R38 R39. A1 / MB1 / MB2 are not parts.',
        'Stencil: 0.10 mm nominal; U6 nine windows (61.91%); DS1 0.25 x 1.30 mm apertures.',
        'See README.md for assembly preview checks, stock, and complete order remarks.'
    ]
    c.setFont('Helvetica',9)
    for i,line in enumerate(details):
        c.drawString(35,263-i*17,line)
    c.showPage(); c.save()
    # Seal all artifacts after independent readback and drawing generation.
    manifest['independent_readback'] = report
    manifest['artifacts_sha256'] = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*'))
                                  if p.is_file() and p.name != 'manifest.json'}
    (out / 'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive = out.parent / (out.name + '-package.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.rglob('*')):
            if p.is_file():
                z.write(p,str(p.relative_to(out)))
    archive.with_suffix('.zip.sha256').write_text(sha(archive)+'  '+archive.name+'\n')
    print(json.dumps(report,indent=2))
    print('Package:', archive)


if __name__ == '__main__':
    main()
