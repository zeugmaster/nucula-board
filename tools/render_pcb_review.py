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
