#!/usr/bin/env python3
"""Generate DS1 lands and a simplified envelope model from Hirose EDC3-150555-51.

Drawing sheet 1, top view: pin 1 is left with the cable entry below the pad row.
The pin row is deliberately located at the existing DS1 local Y=-1.85 mm.
The independently authored VRML is a mechanical illustration, not vendor CAD.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = 'Hirose_FH12A-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal'
MODEL = 'FH12A-24S-0.5SH-envelope.wrl'


def generate():
    lines = [f'(footprint "{NAME}"', '(version 20260206)', '(generator "pcbnew")',
             '(layer "F.Cu")',
             '(descr "Hirose FH12A-24S-0.5SH(55), top contact, 0.30mm flex; EDC3-150555-51 sheet 1; 0.25mm paste apertures")',
             '(tags "Hirose FH12A top contact FPC 24 0.5mm")',
             f'(property "Reference" "REF**" (at 0 -3.7) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
             f'(property "Value" "{NAME}" (at 0 6) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))',
             '(attr smd)']

    def line(a, b, layer, width):
        lines.append(f'(fp_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (stroke (width {width}) (type solid)) (layer "{layer}"))')

    def outline(points, layer, width):
        for a, b in zip(points, points[1:] + points[:1]):
            line(a, b, layer, width)

    # 15.35mm housing, 16.5mm latch envelope, 6.2mm housing depth.
    outline([(-7.675, -1.2), (7.675, -1.2), (7.675, 3.15), (8.25, 3.15),
             (8.25, 5), (-8.25, 5), (-8.25, 3.15), (-7.675, 3.15)], 'F.Fab', .1)
    line((-7.675, 3.15), (7.675, 3.15), 'F.Fab', .1)
    outline([(-6.25, -1.2), (-5.75, -.5), (-5.25, -1.2)], 'F.Fab', .1)
    # Keep printed lines clear of signal and mounting-pad mask openings.
    for a, b in [((-7.8, -1.3), (-6.16, -1.3)), ((-6.16, -1.3), (-6.16, -2.5)),
                 ((6.16, -1.3), (7.8, -1.3)), ((-7.8, -1.3), (-7.8, .04)),
                 ((7.8, -1.3), (7.8, .04)), ((-8.35, 2.76), (-8.35, 5.1)),
                 ((8.35, 2.76), (8.35, 5.1)), ((-8.35, 5.1), (8.35, 5.1))]:
        line(a, b, 'F.SilkS', .12)
    outline([(-8.8, -2.75), (8.8, -2.75), (8.8, 5.25), (-8.8, 5.25)], 'F.CrtYd', .05)
    for i in range(24):
        x = -5.75 + .5 * i
        # Independent paste rectangles retain the 1.3mm length while narrowing
        # only the aperture width from copper 0.30 to recommended paste 0.25mm.
        lines.append(f'(pad "{i+1}" smd rect (at {x} -1.85) (size 0.3 1.3) (layers "F.Cu" "F.Mask"))')
        lines.append(f'(fp_rect (start {x-.125} -2.5) (end {x+.125} -1.2) (stroke (width 0) (type solid)) (fill solid) (layer "F.Paste"))')
    for x in [-7.65, 7.65]:
        lines.append(f'(pad "MP" smd rect (at {x} 1.4) (size 1.8 2.2) (layers "F.Cu" "F.Mask" "F.Paste"))')
    lines.append(f'(model "${{KIPRJMOD}}/libraries/Nucula_Project.3dshapes/{MODEL}" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))')
    lines.append(')')
    (ROOT / 'libraries/Nucula_Project.pretty' / (NAME + '.kicad_mod')).write_text('\n'.join(lines) + '\n')

    # VRML coordinates use KiCad's conventional 0.1-inch units; model Y is
    # opposite the footprint's screen Y. Body/slot/latch are simplified boxes.
    model = ['#VRML V2.0 utf8', '# Independently authored from published dimensions; not Hirose CAD.',
             '# Closed-latch illustration only. Open-latch height is approximately 3.6mm.']
    def box(x, y, z, sx, sy, sz, color):
        center = ' '.join(f'{v / 2.54:.8f}' for v in [x, -y, z])
        size = ' '.join(f'{v / 2.54:.8f}' for v in [sx, sy, sz])
        model.append(f'Transform {{ translation {center} children [ Shape {{ appearance Appearance {{ material Material {{ diffuseColor {color} }} }} geometry Box {{ size {size} }} }} ] }}')
    cream, brown, metal = '.78 .73 .60', '.22 .16 .12', '.72 .72 .69'
    box(0, 1.9, .275, 15.35, 6.2, .45, cream)
    box(0, .975, 1.15, 15.35, 4.35, 1.7, cream)
    for x in [-7.475, 7.475]:
        box(x, 4.075, 1.1, 1.55, 1.85, 1.8, cream)
    box(0, 4.075, 1.775, 13.4, 1.85, .45, brown)
    for i in range(24):
        box(-5.75 + i * .5, -1.6, .1, .2, .8, .2, metal)
    for x in [-7.7, 7.7]:
        box(x, 1.4, .1, .7, .85, .2, metal)
    (ROOT / 'libraries/Nucula_Project.3dshapes' / MODEL).write_text('\n'.join(model) + '\n')


if __name__ == '__main__':
    generate()
