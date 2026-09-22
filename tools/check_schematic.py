#!/usr/bin/env python3
"""Export and check the complete hierarchical draft against datasheet pin maps.

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
# KiCad embeds the absolute input path; publish a portable project-relative path.
netlist = DOC / 'netlist.xml'
netlist.write_text(netlist.read_text().replace(str(SCH), SCH.name))
erc = json.loads((DOC/'erc.json').read_text())
assert not any(sheet['violations'] for sheet in erc['sheets'])
xml = ET.parse(DOC/'netlist.xml').getroot()
components = {c.attrib['ref']: c for c in xml.findall('./components/comp')}
assert components['A1'].findtext('footprint') == 'Nucula_Project:NFC_PCB_Loop_40x40_4T_W0.50_S0.30_InsideFeed'
net_of = {}
net_members = {}
for net in xml.findall('./nets/net'):
    raw_name = net.attrib['name']
    name = raw_name.rsplit('/', 1)[-1] if raw_name.startswith('/') else raw_name
    nodes = {f"{p.attrib['ref']}.{p.attrib['pin']}" for p in net.findall('node')}
    assert name not in net_members, f'Ambiguous local net name: {name}'
    net_members[name] = nodes
    for node in nodes:
        assert node not in net_of, f'Duplicate pin {node}'
        net_of[node] = name

# These physical pin numbers come from the cited component datasheets, independently
# of the drawing-generation coordinates. Exact group membership catches crossed nets.
groups = {
    'VBUS': 'J1.A4 J1.A9 J1.B4 J1.B9 D1.2 U4.5 Q2.1 R18.1 C14.1',
    'USB_5V': 'D1.1 D2.2 Q1.1 R5.1 U1.4 C1.1 D3.2',
    'VSYS': 'D2.1 Q1.2 U2.1 U2.4 C4.1 C17.1 C18.1 Q3.2 R29.1 R33.1 U6.12 U6.28',
    'VBAT': 'U1.3 J2.1 Q1.3 C2.1 R15.1',
    '+3V3': 'L1.2 R6.1 C3.1 C5.1 C6.1 C9.1 C10.1 U3.1 U5.3 C11.1 R8.1 R9.1 R10.1 R11.1 R17.1 C15.1 C16.1 C49.1 C51.1 C52.1 J4.1 J5.1 R37.1 R38.1 R39.1 R40.1 U6.6 U8.16 U9.3',
    '+3V0': 'C43.1 C44.1 C50.1 DS1.5 DS1.6 R19.1 R20.1 R35.1 U9.2',
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
    'I2C_SDA': 'DS1.14 DS1.15 J4.3 J5.3 R19.2 R38.2 U3.3 U6.5 U8.15',
    'I2C_SCL': 'DS1.13 J4.4 J5.4 R20.2 R39.2 U3.4 U6.7 U8.14',
    'KEY_INT_N': 'J4.5 J5.5 R37.2 R40.2 U3.11 U8.13',
    'NFC_IRQ': 'U3.5 U6.8',
    'NFC_VEN': 'R22.1 U3.6 U6.10',
    'NFC_ADR0': 'R23.1 U6.1',
    'NFC_ADR1': 'R24.1 U6.3',
    'NFC_DWL_REQ': 'R21.1 U6.2',
    'NFC_RXN': 'C28.1 U6.15',
    'NFC_RXP': 'C29.1 U6.16',
    'NFC_TVDD': 'C23.1 C24.1 U6.14 U6.18 U6.22',
    'NFC_TX1': 'R41.1 U6.21',
    'NFC_TX2': 'R42.1 U6.19',
    'RF_DRV_P': 'R41.2 L2.1',
    'RF_DRV_N': 'R42.2 L3.1',
    'NFC_VDD18': 'C21.1 C22.1 U6.26 U6.27 U6.31',
    'NFC_VDDUP': 'C19.1 C20.1 R29.2 U6.13',
    'NFC_VMID': 'C25.1 U6.17',
    'NFC_XTAL1': 'C26.1 U6.30 Y1.1',
    'NFC_XTAL2': 'C27.1 U6.29 Y1.3',
    'RF_EMC_P': 'C30.1 C32.1 C34.1 C53.1 L2.2 R25.2',
    'RF_EMC_N': 'C31.2 C33.1 C35.1 C54.2 L3.2 R26.2',
    'RF_MATCH_P': 'C32.2 C34.2 C36.1 C38.1 R27.1',
    'RF_MATCH_N': 'C33.2 C35.2 C37.2 C39.2 R28.1',
    'OLED_PWR_EN': 'Q4.1 R34.1 U3.15',
    'OLED_RESET': 'Q5.1 R36.1 U3.10',
    'OLED_12V5': 'C41.1 C42.1 C45.1 C46.1 D4.1 DS1.23 R30.1',
    'OLED_BOOST_IN': 'C40.1 L4.1 Q3.3 U7.4 U7.5',
    'OLED_FB': 'C41.2 R30.2 R31.1 U7.3',
    'OLED_GATE_N': 'Q3.1 Q4.3 R33.2',
    'OLED_IREF': 'DS1.21 R32.1',
    'OLED_RES_N': 'C48.1 DS1.9 Q5.3 R35.2',
    'OLED_SW': 'D4.2 L4.2 U7.1',
    'OLED_VCOMH': 'C47.1 DS1.22',
}
for i, pin in enumerate([4, 5, 6, 7, 9, 10, 11]):
    groups[f'KEY_P{i}'] = f'J3.{i+2} U8.{pin}'
for name, nodes in groups.items():
    assert net_members[name] == set(nodes.split()), f'{name}: {net_members[name]} != {nodes}'
for nodes in ['U2.3 L1.1', 'U1.5 R3.1', 'U1.1 R4.1', 'R4.2 D3.1',
              'J1.A5 R1.1', 'J1.B5 R2.1', 'R14.2 SW2.1',
              'R12.2 U3.13 C7.1', 'R13.2 U3.14 C8.1',
              'A1.1 R27.2', 'A1.2 R28.2', 'C28.2 R25.1', 'C29.2 R26.1']:
    expected = set(nodes.split())
    assert net_members[net_of[next(iter(expected))]] == expected, nodes
for pin in ('J1.A1 J1.A12 J1.B1 J1.B12 J1.SH J2.2 U1.2 U2.2 U3.9 U3.19 U4.2 U5.1 '
            'Q2.2 R1.2 R2.2 R3.2 R5.2 R7.2 '
            'U6.4 U6.9 U6.20 U6.39 U6.41 Y1.2 Y1.4 R21.2 R22.2 R23.2 R24.2 '
            'C15.2 C16.2 C17.2 C18.2 C19.2 C20.2 C21.2 C22.2 C23.2 C24.2 C25.2 '
            'C26.2 C27.2 C30.2 C31.1 C36.2 C37.1 C38.2 C39.1 C53.2 C54.1 '
            'U7.2 Q4.2 Q5.2 R31.2 R32.2 R34.2 R36.2 C40.2 C42.2 C43.2 C44.2 '
            'C45.2 C46.2 C47.2 C48.2 DS1.1 DS1.2 DS1.3 DS1.7 DS1.8 DS1.10 '
            'DS1.11 DS1.12 DS1.16 DS1.17 DS1.18 DS1.19 DS1.20 DS1.24 '
            'U8.1 U8.2 U8.3 U8.8 J4.2 J5.2 C49.2 C50.2 C51.2 C52.2 U9.1').split():
    assert net_of[pin] == 'GND', pin
for pin in ('J1.A8 J1.B8 U3.12 DS1.4 U6.11 U6.23 U6.24 U6.25 '
            'U6.32 U6.33 U6.34 U6.35 U6.36 U6.37 U6.38 U6.40 J3.1 J3.9 U8.12').split():
    assert net_of[pin].startswith('unconnected-'), pin
for pin in ['J3.1','J3.9','U8.12']:
    assert net_members[net_of[pin]] == {pin}, f'{pin} must remain isolated'
assert 'KEY_P7' not in net_members, 'Only seven matrix lines connect to the keypad'

values = {r: c.findtext('value') for r, c in components.items()}
for ref, value in {'U1':'TP4054-42-SOT25R', 'U2':'SY8089AAAC', 'U3':'ESP32-C3-WROOM-02-N4',
                   'U5':'TLV803EA30DBZR', 'R1':'5.1k', 'R2':'5.1k', 'R3':'10k',
                   'R6':'220k', 'R7':'48.7k', 'R12':'22R', 'R13':'22R',
                   'R15':'470k', 'R16':'470k', 'L1':'2.2uH', 'D1':'B340A','D2':'B340A',
                   'U6':'PN7160A1HN/C100E','U7':'AP3012KTR-E1','U8':'PCF8574T',
                   'U9':'MCP1700T-3002E/TT','R19':'2.2k','R20':'2.2k','R21':'10k',
                   'R22':'100k','R23':'100k','R24':'100k','R29':'0R','R30':'1.8M',
                   'R31':'200k','R32':'910k','L4':'10uH','D4':'SS14',
                   'L2':'150nH','L3':'150nH','C28':'1nF','C29':'1nF',
                   'C30':'330pF','C31':'330pF','C53':'33pF','C54':'33pF','C32':'68pF','C33':'68pF',
                   'C36':'100pF','C37':'100pF','R25':'2.2k','R26':'2.2k',
                   'R27':'2.7R','R28':'2.7R','R41':'0R','R42':'0R'}.items():
    assert values[ref] == value, (ref, values[ref])
fields = {r: {f.attrib['name']: f.text or '' for f in c.findall('./fields/field')} for r,c in components.items()}
for ref in ['R6','R7','R30','R31']:
    assert fields[ref]['Tolerance'] == '0.1%', f'{ref} must be precision 0.1%'
def properties(item):
    result = {uq(p[1]): uq(p[2]) for p in children(item, 'property')}
    assert len(result) == len(children(item, 'property')), f'Duplicate property: {result}'
    return result

schematics = {}
instances = {}
def read_hierarchy(path):
    assert path not in schematics, f'Repeated sheet: {path}'
    tree = parse(path.read_text())
    schematics[path] = tree
    for symbol in children(tree, 'symbol'):
        ref = properties(symbol)['Reference']
        assert ref not in instances, f'Duplicate reference: {ref}'
        instances[ref] = symbol
    for sheet in children(tree, 'sheet'):
        read_hierarchy(path.parent / properties(sheet)['Sheetfile'])
read_hierarchy(SCH)
assert len(schematics) == 5
for ref in ['D1','D2']:
    assert properties(instances[ref])['Datasheet'] == 'https://www.diodes.com/datasheet/download/B340A.pdf'
for ref in ['C7','C8','J3','J4','J5','C34','C35','C38','C39','R38','R39']:
    assert child(instances[ref],'dnp')[1] == 'yes', f'{ref} must remain DNP'
assert fields['J3']['Pinout'] == '1=NC; 2..8=P0..P6; 9=NC'
assert components['J3'].findtext('footprint') == 'Connector_PinHeader_2.54mm:PinHeader_1x09_P2.54mm_Vertical'
keyboard = schematics[ROOT / 'keyboard.kicad_sch']
assert {uq(p[1]) for p in children(keyboard, 'hierarchical_label')} == {
    '+3V3', 'GND', 'I2C_SDA', 'I2C_SCL', 'KEY_INT_N'}
for symbol in children(keyboard, 'symbol'):
    props = properties(symbol)
    if not props['Reference'].startswith('#'):
        assert props['PCB Region'] == 'BREAKAWAY_KEYBOARD'
for ref, address in [('U6','0x28'),('U8','0x20'),('DS1','0x3C')]:
    assert fields[ref]['I2C Address'] == address
assert fields['DS1']['Footprint Status'].startswith('SELECTED:')
assert fields['DS1']['Actual Flex'].startswith('24 contacts per user')
assert fields['DS1']['MPN'] == 'FH12A-24S-0.5SH(55)'
assert fields['DS1']['LCSC'] == 'C506794'
assert components['DS1'].findtext('footprint') == 'Nucula_Project:Hirose_FH12A-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal'
assert 'top-contact' in fields['DS1']['Connector Mechanics']
assert net_of['DS1.1'] == net_of['DS1.24'] == 'GND'
assert not {'DS1.25', 'DS1.26'} & set(net_of)
assert {int(pin.split('.')[1]) for pin in net_of if pin.startswith('DS1.')} == set(range(1, 25))
# All 24 nets are checked above against the supplied CON24 breakout.
# User confirms flex pitch/thickness and top-contact insertion. Actual panel
# pin-1 correspondence, insertion length and operation still need hardware checks.
assert fields['Y1']['MPN'] == 'NX2016SA-27.12MHZ-EXS00A-CS06346'
assert fields['Y1']['LCSC'] == 'C3008209'
assert components['Y1'].findtext('footprint') == 'Nucula_Project:Crystal_NDK_NX2016SA_2.0x1.6mm'
assert values['C26'] == '12pF' and values['C27'] == '15pF'
for ref in ['C21','C22','C23','C24']:
    assert values[ref] == '2.2uF'
    assert fields[ref]['Tolerance'] == '10%'
    assert '0805' in components[ref].findtext('footprint')
    assert fields[ref]['Placement'].startswith('Local capacitor at U6.')
for ref in ['C1','C2','C4']:
    assert fields[ref]['MPN'] == 'CL32B226KAJNNNE'
    assert '1210' in components[ref].findtext('footprint')
for ref in ['C5','C6','C9']:
    assert fields[ref]['MPN'] == 'CL31A226KAHNNNE'
    assert '1206' in components[ref].findtext('footprint')
assert fields['J2']['MPN'] == 'B2B-PH-SM4-TB(LF)(SN)'
assert fields['J2']['LCSC'] == 'C160352'
assert components['J2'].findtext('footprint') == 'Nucula_Project:JST_PH_B2B-PH-SM4-TB_1x02-1MP_P2.00mm_Vertical'
assert child(instances['A1'], 'in_bom')[1] == 'no', 'Etched coil is not a purchased component'
assert 'A1.3' not in net_of, 'PCB loop has exactly two terminals, no ground tap'
for ref in ['C28','C29','C30','C31','C32','C33','C34','C35','C36','C37','C38','C39','C53','C54']:
    assert fields[ref]['Dielectric'] == 'C0G/NP0'
    assert fields[ref]['Voltage'] == '100 V'
    assert '0805' in components[ref].findtext('footprint')
    assert 'HandSolder' in components[ref].findtext('footprint')

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
# AP3012 reference limits, precision divider and conservative +/-100 nA FB bias.
boost_nom = 1.25 * (1 + 1.8e6 / 200e3)
boost_min = 1.17 * (1 + 1.8e6*.999 / (200e3*1.001)) - 100e-9*1.8e6*1.001
boost_max = 1.33 * (1 + 1.8e6*1.001 / (200e3*.999)) + 100e-9*1.8e6*1.001
assert 7 < boost_min < boost_nom < boost_max < 16
# MCP1700 +/-3% temperature accuracy plus +/-1.5% full-range load allowance.
# These are regulated-output estimates, not a guarantee through dropout/transients.
logic_min, logic_max = 3*(1-.03-.015), 3*(1+.03+.015)
assert logic_max < 3.3
bus_high_required = max(.75*v_max, .7*v_max, .8*logic_max)
assert logic_min > bus_high_required
pullup_sink_mA = (logic_max-.4)/(2200*.99)*1000
assert pullup_sink_mA < 3
# Standard-mode 100 kHz, 400 pF design ceiling; tr ~= 0.8473 * R * C.
rise_ns = .8473*2200*1.01*400e-12*1e9
assert rise_ns < 1000
oled_load_A = .030
boost_input_A = boost_max*oled_load_A/(3*.75)
boost_peak_A = boost_input_A + 3*(1-3/boost_max)/(2*1.1e6*10e-6*.8)
assert boost_peak_A < .5  # AP3012 typical limit, not a guaranteed minimum.
pending = {ref: {'value': values[ref], 'status': fields[ref].get('Status', fields[ref].get('Footprint Status',''))}
           for ref in components if 'TBD' in values[ref] or ref in ['DS1','Y1','A1']
           or fields[ref].get('Status','').startswith('PROTOTYPE')}
report={
 'schematic_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in schematics},
 'kicad_version':subprocess.check_output([CLI,'version'],text=True).strip(),
 'erc_violations':0,'sheets':len(schematics),'components':len(components), 'net_count':len(net_members),
 'checked_named_nets':len(groups),'unique_footprints':len(footprints),'resolved_models':len(models),'components_without_3D':without_models,
 'calculations':{'charge_nominal_mA':charge_mA,'vout_nominal_V':v_nom,'vout_static_min_V':v_min,
                 'vout_static_max_V':v_max,'reset_falling_min_V':reset_min,'reset_release_max_V':release_max,
                 'VBAT_ADC_max_V':adc_max,'inductor_peak_estimate_A_at_500mA_load':peak,
                 'OLED_nominal_V':boost_nom,'OLED_static_min_V':boost_min,'OLED_static_max_V':boost_max,
                 'logic_regulated_min_estimate_V':logic_min,'logic_regulated_max_estimate_V':logic_max,
                 'I2C_high_required_V':bus_high_required,'I2C_pullup_current_mA_at_VOL_0V4':pullup_sink_mA,
                 'I2C_rise_ns_at_400pF':rise_ns,'OLED_boost_peak_estimate_A_at_30mA_output':boost_peak_A},
 'i2c':{'speed_Hz':100000,'pullup_V':3.0,'addresses':{'PN7160':'0x28','SSD1309':'0x3C','PCF8574T':'0x20'}},
 'keypad':{'header':'J3','dnp':True,'isolated_header_pins':[1,9],
           'header_to_port':{str(i+2):f'P{i}' for i in range(7)},'unused_port':'P7',
           'legacy_mapping':'Old J2 pins 1..7 -> new J3 pins 2..8, same P0..P6 order',
           'reference_variant':'Adafruit 3845 / interleaved 3x4 matrix',
           'reference_rows_P':[1,6,5,3],'reference_columns_P':[2,0,4]},
 'pending_selection_or_tuning':pending,
 'ready_to_begin_pcb_layout':True,
 'pcb_layout_report':'pcb/layout-check.json',
 'fabrication_release_ready':False,
 'layout_blockers':[],
 'prototype_power_source':'User-confirmed: dedicated USB-C 5 V supply rated at least 1.5 A; ordinary computer-host operation unqualified.',
 'user_deferred':['Battery discharge capability/runtime','Off switch and improved low-battery behavior'],
 'limits':['Static checks only; no board or bench measurements.',
           'No USB input current/inrush/suspend controller; host-power compliance unresolved.',
           'Full-charge headroom depends on VBUS at connector and D1 forward drop.',
           'Battery is optional; select/check a protected pack and polarity before battery testing, not a USB-prototype layout prerequisite.',
           'USB steady-state estimate is 1.10 A from a specified 5 V / 1.5 A supply; startup/inrush and thermal performance require bench validation.',
           'Power MLCC ordering codes and typical DC-bias curves selected; combined-corner screening is an estimate, not a guaranteed minimum.',
           'RF prototype values and 40mm coil selected; actual RL/C, tuning and RF stress still require measurement. NDK crystal selected; load/frequency/startup/drive require bench verification.',
           'OLED CON24 electrical map retained; NFP1309-02Y user confirms 0.50mm pitch, 0.30mm flex and mounted contacts away from PCB. FH12A top-contact socket selected; physical panel pin-1 correspondence, insertion length, fold/enclosure clearance and panel current remain hardware checks.',
           'MCP1700 low-current dropout and AP3012 switch-current limits need bench validation.',
           'Keyboard break line and routing are covered by the PCB layout report; reconnect cable capacitance still needs validation.'],
 'models':sorted(models)
}
(DOC/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
with (DOC/'bom.csv').open('w',newline='') as f:
    writer=csv.writer(f,lineterminator='\n');writer.writerow(['Reference','Value','Footprint','Manufacturer','MPN','LCSC','Tolerance','Voltage','Rating','Dielectric','DNP','PCB Region','Status','Datasheet'])
    for ref in sorted(components,key=lambda s:(re.sub(r'\d','',s),int(re.search(r'\d+',s)[0]))):
        if child(instances[ref], 'in_bom')[1] == 'no':
            continue  # A1 is manufactured PCB copper, not an assembled part.
        c=components[ref];p=fields[ref]
        writer.writerow([ref,c.findtext('value'),c.findtext('footprint'),p.get('Manufacturer',''),p.get('MPN',''),p.get('LCSC',''),p.get('Tolerance',''),p.get('Voltage',''),p.get('Rating',''),p.get('Dielectric',''),child(instances[ref],'dnp')[1],p.get('PCB Region','MAIN'),p.get('Status',p.get('Footprint Status','')),properties(instances[ref]).get('Datasheet',c.findtext('datasheet'))])
print(json.dumps({k:v for k,v in report.items() if k not in ['models','limits','pending_selection_or_tuning']},indent=2))
