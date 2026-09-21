#!/usr/bin/env python3
"""Run scoped ngspice checks using the saved design's values and connectivity.

Requires numpy/matplotlib and shared ngspice (KiCad bundles it on macOS).
This does not simulate firmware, complete ICs, or extract PCB parasitics.
Generated circuits, measurements and plots go to docs/simulation by default.
"""
import argparse
import csv
import ctypes as ct
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from kicad_sexpr import parse, child, children, uq

ROOT = Path(__file__).resolve().parents[1]
F0 = 13.56e6
RF_REFS = ['R41', 'R42', 'L2', 'L3', 'C28', 'C29', 'C30', 'C31',
           'C32', 'C33', 'C34', 'C35', 'C36', 'C37', 'C38', 'C39',
           'C53', 'C54', 'R25', 'R26', 'R27', 'R28']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Design:
    def __init__(self):
        verification = json.loads((ROOT / 'docs/verification.json').read_text())
        for name, expected in verification['schematic_sha256'].items():
            assert sha(ROOT / name) == expected, 'Refresh schematic checks first: ' + name
        tree = ET.parse(ROOT / 'docs/netlist.xml').getroot()
        self.parts = {c.get('ref'): c for c in tree.find('components')}
        self.nets = {n.get('name'): n for n in tree.find('nets')}
        self.nodes = {name: 'n' + n.get('code') for name, n in self.nets.items()}
        self.nodes['GND'] = '0'
        self.pin_nets = {(p.get('ref'), p.get('pin')): name
                         for name, n in self.nets.items() for p in n.findall('node')}
        self.dnp = {r for r, p in self.parts.items()
                    if any(x.get('name') == 'dnp' for x in p.findall('property'))}
        # Compare actual PCB pad nets, values and population to the exported schematic.
        pcb = parse((ROOT / 'nucula-v2.kicad_pcb').read_text())
        seen = set()
        for fp in children(pcb, 'footprint'):
            props = {uq(p[1]): uq(p[2]) for p in children(fp, 'property')}
            ref = props['Reference']
            if ref not in self.parts:
                continue  # Mechanical mouse-bite patterns.
            seen.add(ref)
            assert props['Value'] == self.parts[ref].findtext('value'), ref
            attrs = children(fp, 'attr')
            assert bool(attrs and 'dnp' in attrs[0]) == (ref in self.dnp), ref
            for pad in children(fp, 'pad'):
                key = (ref, uq(pad[1]))
                if key in self.pin_nets:
                    net = child(pad, 'net')
                    assert uq(net[-1]).replace('{slash}', '/') == self.pin_nets[key], key
        assert seen == set(self.parts)

    def node(self, ref, pin):
        return self.nodes[self.pin_nets[ref, str(pin)]]

    def value(self, ref):
        value = self.parts[ref].findtext('value')
        match = re.fullmatch(r'([\d.]+)([RkMmunp]?)(?:[FH])?', value)
        assert match, (ref, value)
        scale = {'': 1, 'R': 1, 'k': 1e3, 'M': 1e6, 'm': 1e-3,
                 'u': 1e-6, 'n': 1e-9, 'p': 1e-12}[match[2]]
        return float(match[1]) * scale

    def tolerance(self, ref):
        fields = {p.get('name'): p.get('value') for p in self.parts[ref].findall('property')}
        return float(fields['Tolerance'].removesuffix('%')) / 100

    def passive(self, ref, scale=1):
        assert ref not in self.dnp
        return f'{ref} {self.node(ref, 1)} {self.node(ref, 2)} {self.value(ref)*scale:.15g}'


class Ngspice:
    class Complex(ct.Structure):
        _fields_ = [('real', ct.c_double), ('imag', ct.c_double)]

    class Vector(ct.Structure):
        pass

    Vector._fields_ = [('name', ct.c_char_p), ('type', ct.c_int), ('flags', ct.c_short),
                      ('real', ct.POINTER(ct.c_double)), ('complex', ct.POINTER(Complex)),
                      ('length', ct.c_int)]

    def __init__(self):
        libpath = os.environ.get('NGSPICE_LIBRARY',
            '/Applications/KiCad/KiCad.app/Contents/Frameworks/libngspice.0.dylib')
        self.lib = ct.CDLL(libpath)
        self.log, self.exits = [], []
        send_type = ct.CFUNCTYPE(ct.c_int, ct.c_char_p, ct.c_int, ct.c_void_p)
        exit_type = ct.CFUNCTYPE(ct.c_int, ct.c_int, ct.c_bool, ct.c_bool, ct.c_int, ct.c_void_p)
        self.send = send_type(lambda msg, *_: self.log.append(msg.decode(errors='replace')) or 0)
        self.exited = exit_type(lambda code, *_: self.exits.append(code) or 0)
        self.lib.ngSpice_Init.argtypes = [ct.c_void_p] * 7
        assert self.lib.ngSpice_Init(self.send, None, self.exited, None, None, None, None) == 0
        self.lib.ngSpice_Command.argtypes = [ct.c_char_p]
        self.lib.ngSpice_Circ.argtypes = [ct.POINTER(ct.c_char_p)]
        self.lib.ngGet_Vec_Info.argtypes = [ct.c_char_p]
        self.lib.ngGet_Vec_Info.restype = ct.POINTER(self.Vector)
        self.command('version')
        self.version = [s for s in self.log if 'ngspice-' in s]
        self.count = 0

    def command(self, text):
        assert self.lib.ngSpice_Command(text.encode()) == 0, text

    def run(self, lines):
        self.command('destroy all')
        start = len(self.log)
        data = (ct.c_char_p * (len(lines)+1))(*[s.encode() for s in lines], None)
        assert self.lib.ngSpice_Circ(data) == 0
        self.command('run')
        problems = [s for s in self.log[start:] if re.search(
            r'error|fatal|timestep too small|singular matrix|no convergence', s, re.I)]
        assert not problems and not self.exits, problems or self.exits
        self.count += 1

    def get(self, name):
        p = self.lib.ngGet_Vec_Info(name.lower().encode())
        assert p, name
        v = p.contents
        assert v.length > 0, name
        if v.complex:
            data = np.array([complex(v.complex[i].real, v.complex[i].imag) for i in range(v.length)])
        else:
            data = np.ctypeslib.as_array(v.real, shape=(v.length,)).copy()
        assert np.all(np.isfinite(data)), name
        return data


def save_circuit(out, name, lines):
    (out / (name + '.cir')).write_text('\n'.join(lines) + '\n')


def crossing(t, v, level, after=0):
    indices = np.flatnonzero((t[:-1] >= after) & (v[:-1] < level) & (v[1:] >= level))
    assert len(indices), (level, float(v.min()), float(v.max()))
    i = indices[0]
    return float(t[i] + (t[i+1]-t[i]) * (level-v[i]) / (v[i+1]-v[i]))


def rf_circuit(d, params, scales=None, sweep=False):
    scales = scales or {}
    lines = ['Nucula current schematic: passive NFC network',
             '* Ideal balanced 1 V differential AC excitation; no PN7160 macro-model.',
             '* Coil RL || C is an assumed scenario, NOT extracted from the routed PCB.',
             '* Coilcraft loss frozen at 13.56 MHz; sweeps are approximate away from f0.',
             f'VP {d.node("U6",21)} 0 DC 0 AC .5 0',
             f'VN {d.node("U6",19)} 0 DC 0 AC .5 180']
    for ref in RF_REFS:
        if ref in d.dnp:
            continue
        a, b = d.node(ref, 1), d.node(ref, 2)
        value = d.value(ref) * scales.get(ref, 1.)
        if ref.startswith('C'):
            lines += [f'R_esr_{ref} {a} x_{ref} .03', f'{ref} x_{ref} {b} {value:.15g}']
        elif ref.startswith('L'):
            assert d.parts[ref].find("property[@name='MPN']").get('value') == '0805HP-151XGRC'
            lines += [f'R_dc_{ref} {a} x_{ref} .288',
                      f'R_skin_{ref} x_{ref} y_{ref} {1.554e-4*math.sqrt(F0):.15g}',
                      f'{ref} y_{ref} {b} {148.8e-9*(value/150e-9):.15g}',
                      f'C_par_{ref} x_{ref} z_{ref} .135p', f'R_par_{ref} z_{ref} {b} 10']
        else:
            # A micro-ohm numerical short; actual jumper/trace impedance is unknown.
            lines.append(f'{ref} {a} {b} {max(value, 1e-6):.15g}')
    a, b = d.node('A1', 1), d.node('A1', 2)
    lines += [f'Ra {a} coil_inner {params["ra"]:.15g}',
              f'La coil_inner {b} {params["la"]:.15g}',
              f'Ca {a} {b} {params["ca"]:.15g}',
              f'R_rxn {d.node("U6",15)} 0 {params.get("rin",2200):.15g}',
              f'R_rxp {d.node("U6",16)} 0 {params.get("rin",2200):.15g}']
    if params.get('extra_shunt', 0):
        for ref in ['R27', 'R28']:
            lines.append(f'C_stray_{ref} {d.node(ref,1)} 0 {params["extra_shunt"]:.15g}')
    lines += ['.options reltol=1e-7 abstol=1e-12',
              '.ac lin 801 10Meg 18Meg' if sweep else '.ac lin 1 13.56Meg 13.56Meg', '.end']
    return lines


def rf_result(ng, d):
    z = 2 / (ng.get('vn#branch') - ng.get('vp#branch'))
    current = abs(ng.get('la#branch'))
    coil = abs(ng.get(d.node('A1', 1)) - ng.get(d.node('A1', 2)))
    drive_rms = 2 * math.sqrt(2) * 3.3 / math.pi
    return dict(z_real_ohm=float(z[0].real), z_imag_ohm=float(z[0].imag),
                z_abs_ohm=float(abs(z[0])),
                coil_rms_A_at_3V3_fundamental=float(current[0]*drive_rms),
                coil_peak_V_at_3V3_fundamental=float(coil[0]*drive_rms*math.sqrt(2)))


def run_rf(ng, d, out):
    old = json.loads((ROOT / 'docs/nfc/calculations.json').read_text())
    model = old['fitted_model_assumptions']
    base = dict(la=model['la_uH']*1e-6, ra=model['ra_ohm'], ca=model['ca_pF']*1e-12)
    scenarios = [('nominal_assumed_coil', base),
                 ('coil_L_minus_10pct', dict(base, la=base['la']*.9)),
                 ('coil_L_plus_10pct', dict(base, la=base['la']*1.1)),
                 ('extra_1pF_each_match_node', dict(base, extra_shunt=1e-12)),
                 ('extra_3pF_each_match_node', dict(base, extra_shunt=3e-12)),
                 ('rx_load_1k', dict(base, rin=1000)),
                 ('rx_load_10k', dict(base, rin=10000))]
    for la, ra, ca in itertools.product([.9, 1.1], [1., 2.5], [1e-12, 5e-12]):
        scenarios.append((f'coil_L{la:g}_R{ra:g}_C{ca*1e12:g}p', dict(la=base['la']*la, ra=ra, ca=ca)))
    rows = []
    for name, params in scenarios:
        lines = rf_circuit(d, params)
        if name == scenarios[0][0]:
            save_circuit(out, 'nfc-nominal', lines)
        ng.run(lines)
        rows.append(dict(scenario=name, **params, **rf_result(ng, d)))
    # Independent earlier half-circuit calculation checks extraction and factor-of-two.
    expected = complex(old['assembly']['z_diff_real_ohm'], old['assembly']['z_diff_imag_ohm'])
    actual = complex(rows[0]['z_real_ohm'], rows[0]['z_imag_ohm'])
    rel = abs(actual-expected)/abs(expected)
    assert rel < 1e-6, (actual, expected)
    rng = np.random.default_rng(7160)
    tolerance_rows = []
    populated = [ref for ref in RF_REFS if ref not in d.dnp and d.value(ref) > 0]
    for i in range(200):
        scales = {ref: 1+rng.uniform(-d.tolerance(ref), d.tolerance(ref)) for ref in populated}
        ng.run(rf_circuit(d, base, scales))
        tolerance_rows.append(dict(case=i, **rf_result(ng, d)))
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.3), layout='constrained')
    frequency_rows = []
    for name, params in scenarios[:3]:
        lines = rf_circuit(d, params, sweep=True)
        ng.run(lines)
        z = 2/(ng.get('vn#branch')-ng.get('vp#branch'))
        f = ng.get('frequency').real/1e6
        ax[0].plot(f, abs(z), label=name.replace('_', ' '))
        frequency_rows.extend(dict(scenario=name, frequency_Hz=float(freq*1e6),
                                   z_real_ohm=float(zz.real), z_imag_ohm=float(zz.imag))
                              for freq, zz in zip(f, z))
    ax[0].axvline(13.56, color='grey', ls=':')
    ax[0].axhline(20, color='grey', ls='--', label='20 ohm design target')
    ax[0].set(xlabel='Frequency (MHz)', ylabel='Differential |Z| (ohm)', ylim=(0, 100),
              title='Coil sensitivity; PCB parasitics unextracted')
    ax[0].legend(fontsize=7)
    ax[1].scatter([r['z_real_ohm'] for r in tolerance_rows],
                  [r['z_imag_ohm'] for r in tolerance_rows], s=10, alpha=.55)
    ax[1].scatter([actual.real], [actual.imag], marker='x', c='black', label='Nominal')
    ax[1].set(xlabel='Resistance (ohm)', ylabel='Reactance (ohm)',
              title='Independent part tolerances at 13.56 MHz\n200 assumed uniform samples; fixed coil')
    ax[1].legend()
    fig.savefig(out / 'nfc-sensitivity.png', dpi=160)
    plt.close(fig)
    for name, data in [('nfc-scenarios.csv', rows), ('nfc-part-tolerances.csv', tolerance_rows),
                       ('nfc-frequency-sweeps.csv', frequency_rows)]:
        fields = list(dict.fromkeys(k for r in data for k in r))
        with (out/name).open('w') as f:
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
            writer.writeheader(); writer.writerows(data)
    return dict(nominal=rows[0], scenarios=rows, half_circuit_relative_difference=rel,
                part_tolerance_samples=200, random_seed=7160,
                tolerance_ranges={key: [min(r[key] for r in tolerance_rows),
                                        max(r[key] for r in tolerance_rows)]
                                  for key in ['z_real_ohm', 'z_imag_ohm', 'coil_peak_V_at_3V3_fundamental']},
                scope='Passive schematic with ideal TX and assumed RX/coil loads; no EM extraction, active RF or tag model.')


def run_i2c(ng, d, out):
    assert {'R38', 'R39'} <= d.dnp
    results = []
    fig, ax = plt.subplots(figsize=(7.5, 4.4), layout='constrained')
    for ref, cap in itertools.product(['R19', 'R20'], [100e-12, 200e-12, 400e-12, 600e-12]):
        supply, bus = d.node(ref, 1), d.node(ref, 2)
        scale = 1+d.tolerance(ref)
        lines = [f'Nucula {ref} I2C pull-up release, Cbus={cap:g}',
                 '* Bus capacitance is a scenario, not extracted from PCB/cable.',
                 '* Sink represented by an ideal controlled switch, 100 ohm on resistance.',
                 f'Vrail {supply} 0 3', d.passive(ref, scale), f'Cbus {bus} 0 {cap:.15g}',
                 'Vctrl ctrl 0 PULSE(1 0 2u 1n 1n 20u 40u)',
                 f'Ssink {bus} 0 ctrl 0 sink', '.model sink SW(Ron=100 Roff=1e12 Vt=.5 Vh=0)',
                 '.options reltol=1e-7', '.tran 2n 10u 0 2n', '.end']
        if cap == 400e-12:
            save_circuit(out, f'i2c-{ref.lower()}-400pf', lines)
        ng.run(lines)
        t, v = ng.get('time'), ng.get(bus)
        rise = crossing(t, v, 2.1, 2e-6)-crossing(t, v, .9, 2e-6)
        analytic = math.log(7/3)*d.value(ref)*scale*cap
        assert abs(rise/analytic-1) < .002
        results.append(dict(ref=ref, assumed_capacitance_pF=cap*1e12, rise_30_70_ns=rise*1e9,
                            standard_mode_rise_pass=rise <= 1e-6,
                            within_400pF_design_ceiling=cap <= 400e-12))
        if ref == 'R19':
            ax.plot((t-2e-6)*1e6, v, label=f'{cap*1e12:g} pF')
    ax.axhline(.9, color='grey', ls=':'); ax.axhline(2.1, color='grey', ls=':')
    ax.set(xlim=(0, 4), xlabel='Time after bus release (us)', ylabel='Bus voltage (V)',
           title='2.2 kohm +1% pull-up to 3.0 V; assumed bus capacitance')
    ax.legend(); fig.savefig(out/'i2c-rise.png', dpi=160); plt.close(fig)
    return dict(cases=results, pcf8574_max_bus_Hz=100000,
                scope='RC edge only; device protocol, clock stretching, pin leakage and rail startup not simulated.')


def run_rc(ng, d, out):
    results = {}
    for name, resistor, capacitor, high, fraction, stop in [
        ('esp-enable', 'R8', 'C12', 3.31, .75, .06),
        ('oled-reset', 'R35', 'C48', 3., .8, .01)]:
        supply, node = d.node(resistor, 1), d.node(resistor, 2)
        assert d.node(capacitor, 1) == node and d.node(capacitor, 2) == '0'
        rscale, cscale = 1+d.tolerance(resistor), 1+d.tolerance(capacitor)
        lines = [f'Nucula {name} passive release, +R and +C tolerance',
                 '* IC reset output is replaced by an ideal open circuit after release.',
                 '* No supervisor delay, glitch filtering, GPIO clamp or transistor model.',
                 f'Vrail {supply} 0 {high}', d.passive(resistor, rscale),
                 d.passive(capacitor, cscale) + ' IC=0',
                 '.options reltol=1e-8', f'.tran {stop/10000:.15g} {stop} uic', '.end']
        save_circuit(out, name, lines); ng.run(lines)
        t, v = ng.get('time'), ng.get(node)
        delay = crossing(t, v, fraction*high)
        tau = d.value(resistor)*rscale*d.value(capacitor)*cscale
        assert abs(delay/(-tau*math.log(1-fraction))-1) < .002
        results[name] = dict(time_to_logic_high_ms=delay*1000, high_fraction=fraction,
                             rc_tau_ms=tau*1000,
                             scope='Passive RC after ideal reset release; initial capacitance tolerance only.')
    a, node, ground = d.node('R15', 1), d.node('R15', 2), d.node('R16', 2)
    assert ground == '0' and d.node('R16', 1) == node and d.node('C13', 1) == node
    rscale, cscale = 1+d.tolerance('R15'), 1+d.tolerance('C13')
    lines = ['Nucula battery sense divider startup, +R and +C tolerance',
             '* ADC pin is ideal high impedance; sampling capacitor/leakage not included.',
             f'Vbattery {a} 0 4.2', d.passive('R15', rscale), d.passive('R16', rscale),
             d.passive('C13', cscale)+' IC=0', '.options reltol=1e-8',
             '.tran 20u 300m uic', '.end']
    save_circuit(out, 'battery-adc-settling', lines); ng.run(lines)
    t, v = ng.get('time'), ng.get(node)
    final = 4.2*d.value('R16')/(d.value('R15')+d.value('R16'))
    tau = (d.value('R15')*d.value('R16')/(d.value('R15')+d.value('R16'))
           *rscale*d.value('C13')*cscale)
    error = 1-float(np.interp(.12, t, v))/final
    assert abs(error/math.exp(-.12/tau)-1) < .002
    results['battery-adc'] = dict(rc_tau_ms=tau*1000, settling_error_at_120ms_pct=error*100,
                                  time_to_0_1pct_ms=crossing(t,v,final*.999)*1000,
                                  settling_error_at_200ms_pct=(1-float(np.interp(.2,t,v))/final)*100,
                                  scope='Initial R/C tolerance only; capacitor temperature, ADC sampling, DC error and leakage excluded.')
    return results


def run_dc_corners(ng, d, out):
    # Ideal feedback regulation with datasheet reference/bias bounds; NOT converter dynamics.
    results = {}
    for name, upper, lower, references, bias in [
        ('buck', 'R6', 'R7', [.588, .612], 50e-9),
        ('oled-boost', 'R30', 'R31', [1.17, 1.33], 100e-9)]:
        rail, fb = d.node(upper, 1), d.node(upper, 2)
        assert d.node(lower, 1) == fb and d.node(lower, 2) == '0'
        values = []
        for vref, hi, lo, ibias in itertools.product(references, [-1, 1], [-1, 1], [-bias, bias]):
            lines = [f'Nucula {name}: ideal regulated DC operating point',
                     '* Unlimited ideal regulator; no input/dropout/current-limit/dynamic model.',
                     f'Vref ref 0 {vref}', f'Ereg {rail} 0 ref {fb} 1e9',
                     d.passive(upper, 1+hi*d.tolerance(upper)),
                     d.passive(lower, 1+lo*d.tolerance(lower)),
                     f'Ibias {fb} 0 {ibias}', '.options reltol=1e-9', '.op', '.end']
            ng.run(lines)
            vout = float(ng.get(rail)[0])
            rt = d.value(upper)*(1+hi*d.tolerance(upper))
            rb = d.value(lower)*(1+lo*d.tolerance(lower))
            assert abs(vout-(vref*(1+rt/rb)+ibias*rt)) < 1e-6
            values.append(vout)
        save_circuit(out, name+'-dc-corner', lines)
        results[name] = dict(min_V=min(values), max_V=max(values), cases=len(values),
                             scope='Ideal DC regulation only; no startup, load regulation, stability, dropout or ripple validation.')
    release = 3.08*1.02*1.015
    results['reset_release_margin_mV'] = (results['buck']['min_V']-release)*1000
    results['reset_falling_margin_mV'] = (results['buck']['min_V']-3.08*1.02)*1000
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'docs/simulation')
    args = parser.parse_args(); out = args.out; out.mkdir(parents=True, exist_ok=True)
    d, ng = Design(), Ngspice()
    tracked = ['nucula-v2.kicad_pcb', 'nucula-v2.kicad_pro', 'nucula-v2.kicad_dru',
               *sorted(p.name for p in ROOT.glob('*.kicad_sch'))]
    hashes = {p: sha(ROOT/p) for p in tracked}
    report = dict(scope='Partial circuit simulation; not a manufacturing release or complete board simulation.',
                  design_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=hashes, netlist_sha256=sha(ROOT/'docs/netlist.xml'),
                  simulation_script_sha256=sha(Path(__file__)),
                  nfc_assumptions_sha256=sha(ROOT/'docs/nfc/calculations.json'),
                  engine=ng.version, pcb_values_pad_nets_population_match_netlist=True)
    report['nfc'] = run_rf(ng, d, out)
    report['i2c'] = run_i2c(ng, d, out)
    report['rc'] = run_rc(ng, d, out)
    report['dc'] = run_dc_corners(ng, d, out)
    report['simulations_completed'] = ng.count
    report['solver_errors'] = []
    report['engine_warnings'] = sorted(set(s for s in ng.log if 'warning' in s.lower()))
    report['not_simulated'] = ['SY8089/AP3012 closed-loop switching and startup',
        'USB insertion/removal, inrush, source/cable and charger dynamics',
        'MCP1700 dropout and regulator stability', 'PN7160 active TX/RX, firmware, tags and read range',
        'ESP32 execution, RF behavior and current bursts', 'SSD1309 panel/firmware sequencing',
        '27.12 MHz oscillator startup/drive', 'USB signal integrity and ESD',
        'PCB parasitic extraction, EM coupling, thermal behavior and EMC']
    assert hashes == {p: sha(ROOT/p) for p in tracked}, 'Design modified during simulation'
    (out/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    (out/'ngspice.log').write_text('\n'.join(ng.log)+'\n')
    (out/'node-map.json').write_text(json.dumps(d.nodes, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ['simulations_completed', 'solver_errors', 'rc', 'dc']}, indent=2))
    print('NFC nominal:', report['nfc']['nominal'])
    print('NFC tolerance ranges:', report['nfc']['tolerance_ranges'])
    print('I2C:', report['i2c']['cases'])


if __name__ == '__main__':
    main()
