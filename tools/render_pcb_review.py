#!/usr/bin/env python3
"""Render current-board review diagrams using native KiCad SVG plots.

Run with pcbnew-enabled Python. PNG output additionally uses rsvg-convert.
These annotated figures are review drawings, not manufacturing layers.
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

import pcbnew as k

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/pcb'


def main():
    board = k.LoadBoard(str(ROOT / 'nucula-v2.kicad_pcb'))
    # Catalogue URLs and other custom fields can be visible on F.Fab. Hide them
    # in this in-memory plotting copy so they do not obscure the routing review.
    for footprint in board.GetFootprints():
        for field in footprint.GetFields():
            field.SetVisible(field.GetName() == 'Reference')
    layers = {}
    usb_layers = {}
    with tempfile.TemporaryDirectory(prefix='nucula-review-') as tmp:
        plot = k.PLOT_CONTROLLER(board)
        options = plot.GetPlotOptions()
        options.SetOutputDirectory(tmp)
        options.SetPlotFrameRef(False)
        options.SetPlotValue(False)
        options.SetPlotReference(True)
        options.SetAutoScale(False)
        options.SetScale(1)
        options.SetUseAuxOrigin(False)
        for layer in [k.F_Cu, k.In1_Cu, k.In2_Cu, k.B_Cu, k.F_SilkS, k.F_Fab, k.Edge_Cuts]:
            name = k.LayerName(layer).replace('.', '_')
            plot.SetLayer(layer)
            plot.OpenPlotfile(name, k.PLOT_FORMAT_SVG, '')
            plot.PlotLayer()
            plot.ClosePlot()
            svg = (Path(tmp) / ('nucula-v2-' + name + '.svg')).read_text()
            layers[layer] = '\n'.join(line.rstrip() for line in
                                      svg[svg.index('<g '):svg.rindex('</svg>')].splitlines())
        # Enlarged USB reviews use one centered label per component. Native
        # reference fields plus ${REFERENCE} text otherwise overlap each other.
        for footprint in board.GetFootprints():
            for field in footprint.GetFields():
                field.SetVisible(False)
            for graphic in list(footprint.GraphicalItems()):
                if isinstance(graphic, k.PCB_TEXT):
                    graphic.SetLayer(k.Dwgs_User)
        for layer in [k.F_Cu, k.F_Fab]:
            name = 'usb-' + k.LayerName(layer).replace('.', '_')
            plot.SetLayer(layer)
            plot.OpenPlotfile(name, k.PLOT_FORMAT_SVG, '')
            plot.PlotLayer()
            plot.ClosePlot()
            svg = (Path(tmp) / ('nucula-v2-' + name + '.svg')).read_text()
            usb_layers[layer] = '\n'.join(line.rstrip() for line in
                                          svg[svg.index('<g '):svg.rindex('</svg>')].splitlines())

    def colored(layer, color):
        return layers[layer].replace('#000000', color)

    access = '''<g font-family="sans-serif" text-anchor="middle" fill="#075c50">
<rect x="71.15" y="98.55" width="17.7" height="5" fill="#e3fff3" fill-opacity="0.94"
 stroke="#087f6d" stroke-width="0.18" stroke-dasharray="0.6 0.4"/>
<text x="80" y="100.45" font-size="1.05">17.7 × 5.0 mm</text>
<text x="80" y="102.2" font-size="0.85">NO SMT COMPONENTS</text></g>'''
    detail = colored(k.F_Cu, '#c4c9c6') + colored(k.F_Fab, '#223a4b') + colored(k.F_SilkS, '#466052')
    top = colored(k.F_Cu, '#b08b47') + colored(k.F_Fab, '#364c48') + colored(k.F_SilkS, '#203c32')

    def write(name, box, content, width):
        path = OUT / (name + '.svg')
        path.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="' + box + '">'
                       '<rect x="0" y="0" width="400" height="400" fill="white"/>' + content + '</svg>\n')
        renderer = shutil.which('rsvg-convert')
        if renderer:
            subprocess.run([renderer, '-w', str(width), str(path), '-o', str(path.with_suffix('.png'))], check=True)

    write('display-clearance', '65 92 31 23', detail + access, 1550)
    write('top', '48 49 64 112', top + colored(k.Edge_Cuts, '#202c29') + access, 1400)
    mounts = [f for f in board.GetFootprints() if f.GetReference() in {'H1','H2','H3','H4','H5','H6'}]
    if len(mounts) == 6:
        mounting = '<g opacity="0.18">' + top + '</g>' + colored(k.Edge_Cuts, '#202c29')
        mounting += '<g font-family="sans-serif" fill="#075c50">'
        mounting += '<text x="80" y="42" font-size="2" text-anchor="middle">6 × Ø2.2 mm NPTH · M2 mounting</text>'
        mounting += '<text x="80" y="45" font-size="1.1" text-anchor="middle">Hardware Ø5.0 mm max · Ø5.5 mm keepout</text>'
        for f in mounts:
            x, y = k.ToMM(f.GetPosition().x), k.ToMM(f.GetPosition().y)
            mounting += (f'<circle cx="{x}" cy="{y}" r="2.75" fill="#b7f3de" fill-opacity="0.5" '
                         'stroke="#087f6d" stroke-width="0.15" stroke-dasharray="0.5 0.3"/>'
                         f'<circle cx="{x}" cy="{y}" r="1.1" fill="white" stroke="#075c50" stroke-width="0.15"/>')
            label_x, anchor = (x+4, 'start') if x < 80 else (x-4, 'end')
            mounting += (f'<text x="{label_x}" y="{y-.5}" font-size="1.2" text-anchor="{anchor}">{f.GetReference()}</text>'
                         f'<text x="{label_x}" y="{y+1}" font-size="0.85" text-anchor="{anchor}">({x:g}, {y:g})</text>')
        mounting += '<path d="M53.5 49H106.5 M53.5 48V50 M106.5 48V50 M114 53.5V120 M113 53.5H115 M113 120H115" fill="none" stroke="#075c50" stroke-width="0.12"/>'
        mounting += '<text x="80" y="48.3" text-anchor="middle" font-size="1.2">53.0 mm</text>'
        mounting += '<text x="115.5" y="86.75" font-size="1.2" text-anchor="middle" transform="rotate(90 115.5 86.75)">66.5 mm</text>'
        mounting += '<text x="80" y="164" text-anchor="middle" font-size="1.1">Centers in KiCad mm · keyboard hole spacing 53.0 mm</text></g>'
        write('mounting-holes', '47 39 72 128', mounting, 1400)
    usb = usb_layers[k.F_Cu].replace('#000000', '#c4c9c6') + usb_layers[k.F_Fab].replace('#000000', '#223a4b')
    for f in board.GetFootprints():
        if f.GetReference().startswith('MB'):
            continue
        x, y = k.ToMM(f.GetPosition().x), k.ToMM(f.GetPosition().y)
        size = .75 if f.GetReference() in ['U4', 'U10'] else .55
        usb += (f'<text x="{x}" y="{y}" font-family="sans-serif" font-size="{size}" '
                'text-anchor="middle" dominant-baseline="central" fill="#122c3b" '
                'stroke="white" stroke-width="0.18" paint-order="stroke">'
                + f.GetReference() + '</text>')
    mini_notes = '<g fill="#153c4a" stroke="#153c4a"><path d="M110 95V115" fill="none" stroke-width=".08" stroke-dasharray=".5 .4"/><text x="109.4" y="95.5" stroke="none" font-family="sans-serif" font-size=".65" text-anchor="end">Antenna tip flush: x = 110 mm</text></g>'
    write('mini-module', '90 94 24 25', top + colored(k.Edge_Cuts, '#202c29') + mini_notes, 1600)
    write('usb-protection', '54 107 16 10', usb + colored(k.Edge_Cuts, '#202c29'), 1600)
    write('usb-switch', '87 114 18 9.5', usb + colored(k.Edge_Cuts, '#202c29'), 1800)
    battery = '''<g font-family="sans-serif">
<rect x="43.4" y="89.2" width="30" height="3.1" fill="white"/>
<text x="55.2" y="90.3" font-size="0.85" text-anchor="middle" fill="#122c3b">J2: side-entry JST-SH / C160402</text>
<text x="55.2" y="91.7" font-size="0.7" text-anchor="middle" fill="#122c3b">2.95 mm high, including mated plug</text>
<path d="M55.125 100.9 H51.5 M52.2 100.4 L51.5 100.9 L52.2 101.4" fill="none" stroke="#087f6d" stroke-width="0.16"/>
<text x="46.8" y="99.7" text-anchor="middle" font-size="0.65" fill="#087f6d">Cable to back</text>
<text x="46.8" y="100.8" text-anchor="middle" font-size="0.65" fill="#087f6d">5 × 3 mm notch</text>
<text x="46.8" y="101.9" text-anchor="middle" font-size="0.6" fill="#087f6d">R0.5 all corners</text>
<path d="M49.3 98.4V103.4 M49 98.4H49.6 M49 103.4H49.6 M50 104H53 M50 103.7V104.3 M53 103.7V104.3" fill="none" stroke="#087f6d" stroke-width="0.07"/>
<text x="51.5" y="105" text-anchor="middle" font-size="0.65" fill="#087f6d">3 mm deep</text>
<circle cx="59.7" cy="100.4" r="0.19" fill="#b74425"/>
<circle cx="59.7" cy="101.4" r="0.19" fill="#243e56"/>
<text x="59.4" y="99.5" font-size="0.7" text-anchor="middle" fill="#b74425" stroke="white" stroke-width="0.16" paint-order="stroke">1 +</text>
<text x="60" y="102.3" font-size="0.65" text-anchor="middle" fill="#243e56" stroke="white" stroke-width="0.16" paint-order="stroke">2 GND</text>
<rect x="51.6" y="94.75" width="2.2" height="2.5" rx="0.44" fill="#243e56" fill-opacity="0.22"/>
<rect x="55" y="94.75" width="2.2" height="2.5" rx="0.44" fill="#b74425" fill-opacity="0.28"/>
<text x="52.7" y="97.9" font-size="0.6" text-anchor="middle" fill="#243e56" stroke="white" stroke-width="0.15" paint-order="stroke">GND</text>
<text x="56.1" y="97.9" font-size="0.6" text-anchor="middle" fill="#b74425" stroke="white" stroke-width="0.15" paint-order="stroke">BAT+</text>
<text x="46.9" y="95.4" font-size="0.65" text-anchor="middle" fill="#122c3b">J6: solder leads</text>
<text x="46.9" y="96.5" font-size="0.6" text-anchor="middle" fill="#122c3b">2.2 × 2.5 mm pads</text>
</g>'''
    write('battery-connector', '43 89 27 20', usb + colored(k.Edge_Cuts, '#202c29') + battery, 1600)
    write('nfc', '57 48 48 46', top, 1400)
    panels = []
    for i, (layer, name, color) in enumerate([(k.F_Cu, 'Front copper', '#9a6630'),
                                             (k.In1_Cu, 'Inner 1', '#6d5295'),
                                             (k.In2_Cu, 'Inner 2', '#468166'),
                                             (k.B_Cu, 'Back copper', '#346d9c')]):
        panels.append(f'<g transform="translate({i * 66},0)">' + colored(layer, color)
                      + colored(k.Edge_Cuts, '#26332f')
                      + f'<text x="80" y="47" font-family="sans-serif" text-anchor="middle" font-size="2">{name}</text></g>')
    write('copper-layers', '48 43 262 118', ''.join(panels), 2400)


if __name__ == '__main__':
    main()
