#!/usr/bin/env python3
"""Export and check the power/USB draft against datasheet-derived connections.

Run from anywhere. Requires KiCad 10 and its standard footprint/3D libraries.
Creates docs/erc.json, docs/netlist.xml, docs/bom.csv and docs/verification.json.
Does not edit the schematic or PCB. Not an analog simulation or compliance test.
"""
from pathlib import Path
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from kicad_sexpr import parse, uq, children, child

ROOT = Path(__file__).resolve().parents[1]
MAC = Path('/Applications/KiCad/KiCad.app/Contents')
CLI = os.environ.get('KICAD_CLI') or shutil.which('kicad-cli') or str(MAC / 'MacOS/kicad-cli')
SHARE = Path(os.environ.get('KICAD_SHARE', str(MAC / 'SharedSupport') if MAC.exists() else '/usr/share/kicad'))
DOC = ROOT / 'docs'
DOC.mkdir(exist_ok=True)
SCH = ROOT / 'nucula-v2.kicad_sch'

def run(*args):
    subprocess.run([CLI, *map(str, args)], check=True, cwd=ROOT)

run('sch', 'erc', '--format', 'json', '--severity-all', '--exit-code-violations', '--output', DOC/'erc.json', SCH)
run('sch', 'export', 'netlist', '--format', 'kicadxml', '--output', DOC/'netlist.xml', SCH)
erc = json.loads((DOC/'erc.json').read_text())
assert not any(sheet['violations'] for sheet in erc['sheets'])
xml = ET.parse(DOC/'netlist.xml').getroot()
components = {c.attrib['ref']: c for c in xml.findall('./components/comp')}
net_of = {}
net_members = {}
for net in xml.findall('./nets/net'):
    name = net.attrib['name'].removeprefix('/')
    nodes = {f"{p.attrib['ref']}.{p.attrib['pin']}" for p in net.findall('node')}
    net_members[name] = nodes
    for node in nodes:
        assert node not in net_of, f'Duplicate pin {node}'
        net_of[node] = name

# These physical pin numbers come from the cited component datasheets, independently
# of the drawing-generation coordinates. Exact group membership catches crossed nets.
groups = {
    'VBUS': 'J1.A4 J1.A9 J1.B4 J1.B9 D1.2 U4.5 Q2.1 R18.1 C14.1',
    'USB_5V': 'D1.1 D2.2 Q1.1 R5.1 U1.4 C1.1 D3.2',
    'VSYS': 'D2.1 Q1.2 U2.1 U2.4 C4.1',
    'VBAT': 'U1.3 J2.1 Q1.3 C2.1 R15.1',
    '+3V3': 'L1.2 R6.1 C3.1 C5.1 C6.1 C9.1 C10.1 U3.1 U5.3 C11.1 R8.1 R9.1 R10.1 R11.1 R17.1',
    'BUCK_FB': 'U2.5 R6.2 R7.1 C3.2',
    'ESP_EN': 'U3.2 U5.2 R8.2 C12.1 SW1.1',
    'BOOT_N': 'U3.8 R11.2 R14.1',
    'STRAP_GPIO2': 'U3.16 R9.2',
    'STRAP_GPIO8': 'U3.7 R10.2',
    'VBAT_ADC': 'U3.18 R15.2 R16.1 C13.1',
    'USB_PRESENT_N': 'U3.17 Q2.3 R17.2',
    'USB_D-': 'J1.A7 J1.B7 U4.1',
    'USB_D+': 'J1.A6 J1.B6 U4.3',
    'USB_ESD_D-': 'U4.6 R12.1',
    'USB_ESD_D+': 'U4.4 R13.1',
}
for name, nodes in groups.items():
    assert net_members[name] == set(nodes.split()), f'{name}: {net_members[name]} != {nodes}'
for nodes in ['U2.3 L1.1', 'U1.5 R3.1', 'U1.1 R4.1', 'R4.2 D3.1',
              'J1.A5 R1.1', 'J1.B5 R2.1', 'R14.2 SW2.1',
              'R12.2 U3.13 C7.1', 'R13.2 U3.14 C8.1']:
    expected = set(nodes.split())
    assert net_members[net_of[next(iter(expected))]] == expected, nodes
for pin in ('J1.A1 J1.A12 J1.B1 J1.B12 J1.SH J2.2 U1.2 U2.2 U3.9 U3.19 U4.2 U5.1 '
            'Q2.2 R1.2 R2.2 R3.2 R5.2 R7.2').split():
    assert net_of[pin] == 'GND', pin
for pin in 'J1.A8 J1.B8 U3.3 U3.4 U3.5 U3.6 U3.10 U3.11 U3.12 U3.15'.split():
    assert net_of[pin].startswith('unconnected-'), pin

values = {r: c.findtext('value') for r, c in components.items()}
for ref, value in {'U1':'TP4054-42-SOT235', 'U2':'SY8089AAAC', 'U3':'ESP32-C3-WROOM-02-N4',
                   'U5':'TLV803EA30DCKR', 'R1':'5.1k', 'R2':'5.1k', 'R3':'10k',
                   'R6':'220k', 'R7':'48.7k', 'R12':'22R', 'R13':'22R',
                   'R15':'470k', 'R16':'470k', 'L1':'2.2uH'}.items():
    assert values[ref] == value, (ref, values[ref])
fields = {r: {f.attrib['name']: f.text or '' for f in c.findall('./fields/field')} for r,c in components.items()}
for ref in ['R6','R7']:
    assert fields[ref]['Tolerance'] == '0.1%', f'{ref} must be precision 0.1%'
sch = parse(SCH.read_text())
instances = {uq(next(p[2] for p in children(s,'property') if uq(p[1])=='Reference')):s for s in children(sch,'symbol')}
for ref in ['C7','C8']:
    assert child(instances[ref],'dnp')[1] == 'yes', f'{ref} must remain unpopulated unless USB is retuned'
assert len(instances) == len(children(sch,'symbol')), 'Duplicate references'

# Check every physical symbol pin has a matching footprint pad and every referenced
# 3D model exists; excludes power symbols, which are not physical BOM components.
libparts = {(p.attrib['lib'],p.attrib['part']):p for p in xml.findall('./libparts/libpart')}
footprints = set()
models = set()
without_models = []
for ref,c in components.items():
    fp = c.findtext('footprint')
    assert fp, f'{ref}: missing footprint'
    lib,name = fp.split(':',1)
    path = ROOT/'libraries/Nucula_Project.pretty'/f'{name}.kicad_mod' if lib=='Nucula_Project' else SHARE/'footprints'/f'{lib}.pretty'/f'{name}.kicad_mod'
    assert path.is_file(), f'{ref}: missing {path}'
    tree = parse(path.read_text())
    pads = {uq(p[1]) for p in children(tree,'pad') if uq(p[1])}
    src=c.find('libsource');symbol=libparts[(src.attrib['lib'],src.attrib['part'])]
    pins={p.attrib['num'] for p in symbol.findall('./pins/pin')}
    assert pins <= pads, f'{ref}: pins without pads: {pins-pads}'
    footprints.add(fp)
    if not children(tree,'model'):without_models.append(ref)
    for model in children(tree,'model'):
        model_path=uq(model[1]).replace('${KIPRJMOD}',str(ROOT))
        model_path=re.sub(r'\$\{KICAD\d+_3DMODEL_DIR\}',str(SHARE/'3dmodels'),model_path)
        assert Path(model_path).is_file(), f'{ref}: missing model {model_path}'
        models.add(model_path.replace(str(ROOT),'${KIPRJMOD}').replace(str(SHARE),'${KICAD_SHARE}'))

# Static corner calculations: regulator reference +/-2%, divider +/-0.1%,
# FB bias +/-50 nA. These bounds do not include load-step ripple or dropout.
top,bottom=220000,48700
tol=.001
v_nom=.6*(1+top/bottom)
v_min=.588*(1+top*(1-tol)/(bottom*(1+tol)))-50e-9*top*(1+tol)
v_max=.612*(1+top*(1+tol)/(bottom*(1-tol)))+50e-9*top*(1+tol)
reset_min=3.08*.98
release_max=3.08*1.02*1.015
assert 3.0 < reset_min < release_max < v_min < v_nom < v_max < 3.6
charge_mA=1000/10000*1000
adc_max=4.242*(470000*1.01)/(470000*.99+470000*1.01)
assert adc_max < 2.5
# Inductor peak scenario at 5.5 V, assumed 0.8 MHz and -20% inductance.
# The application note gives 1 MHz typical, not a guaranteed minimum.
peak=.5+v_max*(1-v_max/5.5)/(2*.8e6*2.2e-6*.8)
assert peak < 1.48
report={
 'schematic_sha256':hashlib.sha256(SCH.read_bytes()).hexdigest(),
 'kicad_version':subprocess.check_output([CLI,'version'],text=True).strip(),
 'erc_violations':0,'components':len(components), 'net_count':len(net_members),
 'checked_named_nets':len(groups),'unique_footprints':len(footprints),'resolved_models':len(models),'components_without_3D':without_models,
 'calculations':{'charge_nominal_mA':charge_mA,'vout_nominal_V':v_nom,'vout_static_min_V':v_min,
                 'vout_static_max_V':v_max,'reset_falling_min_V':reset_min,'reset_release_max_V':release_max,
                 'VBAT_ADC_max_V':adc_max,'inductor_peak_estimate_A_at_500mA_load':peak},
 'limits':['Static checks only; no board or bench measurements.',
           'No USB input current/inrush/suspend controller; host-power compliance unresolved.',
           'Full-charge headroom depends on VBUS at connector and D1 forward drop.',
           'Battery model/polarity and capacitor MPN/DC-bias curves require selection before PCB.'],
 'models':sorted(models)
}
(DOC/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
with (DOC/'bom.csv').open('w',newline='') as f:
    writer=csv.writer(f);writer.writerow(['Reference','Value','Footprint','Manufacturer','MPN','Tolerance','Voltage','Dielectric','DNP','Datasheet'])
    for ref in sorted(components,key=lambda s:(re.sub(r'\d','',s),int(re.search(r'\d+',s)[0]))):
        c=components[ref];p=fields[ref]
        writer.writerow([ref,c.findtext('value'),c.findtext('footprint'),p.get('Manufacturer',''),p.get('MPN',''),p.get('Tolerance',''),p.get('Voltage',''),p.get('Dielectric',''),child(instances[ref],'dnp')[1],c.findtext('datasheet')])
print(json.dumps({k:v for k,v in report.items() if k not in ['models','limits']},indent=2))
