#!/usr/bin/env python3
"""Screen the measured Rev-A backfeed hypothesis; never report this as a bench fix.

Uses the existing ngspice wrapper and verified saved-board/netlist extraction.
The steering diode and ESP pull-up are illustrative models, not validated
manufacturer macromodels. Isolating U4.5 is a diagnostic scenario, not a release.
"""
import itertools
import json
import math
from pathlib import Path

from simulate_preflight import Design, Ngspice, ROOT, sha, save_circuit


def main():
    d = Design()
    measurement_path = 'docs/bringup/rev-A-usb-battery-2026-10-06.json'
    measurements = json.loads((ROOT / measurement_path).read_text())
    released = measurements['battery_only']['reset_released']
    held = measurements['battery_only']['reset_held']
    ng = Ngspice()
    out = ROOT / 'docs/bringup/backfeed-analysis'
    out.mkdir(parents=True, exist_ok=True)
    assert d.node('U4', 5) == d.node('C14', 1) == d.node('R18', 1) == d.node('J1', 'A4')
    assert d.node('U4', 4) == d.node('R13', 1)
    assert d.node('U3', 14) == d.node('R13', 2)
    assert d.node('Q2', 1) == d.node('U4', 5)
    assert d.node('Q2', 2) == d.node('R18', 2) == '0'
    rows = []
    for voltage, ideality, saturation, state in itertools.product(
            [3.0, 3.3, 3.6], [1, 2], [1e-14, 1e-12],
            ['battery_usb_active', 'reset_pullup_disabled', 'u4_pin5_isolated']):
        # RESET removes the pull-up in this hypothesis; measured D+ falls to 0 V.
        pullup = 1.5e3 if state != 'reset_pullup_disabled' else 1e12
        rail = 'vbus' if state != 'u4_pin5_isolated' else 'clamp'
        lines = ['Rev-A USB backfeed hypothesis; no USB cable or host attached',
                 '* 1.5k pull-up and diode Is/N are assumptions, not fitted measurements.',
                 '* No ESP PHY, Q2 channel, D1/D2 reverse leakage, charger, or ESD surge model.',
                 f'Vlogic logic 0 {voltage}', f'Rpull logic phy {pullup}',
                 f'R13 phy dp {d.value("R13")}',
                 f'Dupper dp {rail} steering', 'Dlower 0 dp steering',
                 f'.model steering D(Is={saturation} N={ideality} Rs=.52)',
                 f'R18 vbus 0 {d.value("R18")}',
                 f'C14 vbus 0 {d.value("C14")}',
                 'Rmeter vbus 0 10Meg', 'Rnumeric clamp 0 1e12',
                 '.options reltol=1e-8 abstol=1e-14', '.op', '.end']
        ng.run(lines)
        vbus = float(ng.get('vbus')[0])
        assert vbus > .8 if state == 'battery_usb_active' else abs(vbus) < .001
        rows.append(dict(state=state, source_V=voltage, assumed_diode_N=ideality,
                         assumed_diode_Is_A=saturation, VBUS_V=vbus,
                         Dplus_V=float(ng.get('dp')[0]),
                         R18_current_uA=vbus / d.value('R18') * 1e6))
        if voltage == 3.3 and ideality == 2 and saturation == 1e-14:
            save_circuit(out, state, lines)
    discharge = []
    for scale_r, scale_c in [(1, 1), (.99, .9), (1.01, 1.1)]:
        r, c = d.value('R18')*scale_r, d.value('C14')*scale_c
        lines = ['VBUS decay after ALL sources are removed; initial VBUS 5.25 V',
                 f'R18 vbus 0 {r}', f'C14 vbus 0 {c} IC=5.25',
                 '.tran 10u 60m uic', '.end']
        ng.run(lines)
        times, volts = ng.get('time'), ng.get('vbus')
        below = next(i for i, v in enumerate(volts) if v <= .8)
        measured = float(times[below])
        expected = r*c*math.log(5.25/.8)
        assert abs(measured-expected) < 30e-6
        discharge.append(dict(R18_ohm=r, C14_F=c, to_0_8V_ms=measured*1e3,
                              analytic_to_0_8V_ms=expected*1e3))
        if scale_r == 1:
            save_circuit(out, 'isolated_vbus_decay', lines)
    result = dict(
        analysis_completed=True, hardware_fix_verified=False,
        hardware_circuit_changed=False, bench_measurements_pending=True,
        baseline_dc_measurements_completed=True,
        design_decision=measurements['design_decision'],
        pending_bench_checks=['RESET transient waveform capture',
                              'Validation of a permanent remedy and repeated USB reconnection'],
        simulations_completed=ng.count, solver_errors=[],
        source_sha256={name: sha(ROOT / name) for name in
                       ['nucula-v2.kicad_pcb', 'power-mcu.kicad_sch', 'docs/netlist.xml',
                        'tools/analyze_usb_backfeed.py', 'tools/simulate_preflight.py', measurement_path]},
        verified_path=['U3.14 / IO19', 'R13.2 -> R13.1 (22 ohm)',
                       'U4.4 -> internal upper steering diode -> U4.5',
                       'J1 VBUS / C14.1 / R18.1 / Q2 gate'],
        observed_battery_only=measurements['battery_only'],
        observed_VBUS_V=released['VBUS_C14_1_V'],
        observed_nominal_R18_backfeed_uA=released['VBUS_C14_1_V']/d.value('R18')*1e6,
        observed_Dplus_minus_VBUS_V=round(released['Dplus_R13_1_V']-released['VBUS_C14_1_V'], 6),
        observed_steady_3V3_difference_V=round(released['3V3_C11_1_V']-held['3V3_C11_1_V'], 6),
        maximum_total_injected_uA_for_VBUS_below_0_8V_at_R18_plus_1pct=.8/(d.value('R18')*1.01)*1e6,
        interpretation='Measured D+ and VBUS collapse on RESET while steady +3V3 remains at 3.33 V. '
            'Together with the topology and 0.79 V D+-to-VBUS difference, this strongly supports the U4 path. '
            'Simulated voltages do not identify the physical source or reproduce the observed voltage quantitatively. '
            'The user accepts this diagnosis for redesign without physical isolation. '
            'U4 pin-5 isolation was not performed; steady meter readings do not exclude brief rail transients.',
        dc_scenarios=rows, discharge_scenarios=discharge,
        limits=['Illustrative ESP pull-up and diode models; no parameter fitted to the measured voltages.',
                'No USB-C source state machine, ESP reset/ROM behavior, Q2 switching threshold, or firmware model.',
                'D1/D2 leakage, TP4054 reverse current, contamination, cable and oscilloscope loading are omitted.',
                'Isolation scenarios are bench diagnostics; leaving U4.5 disconnected removes its VBUS protection.',
                'Existing 261 preflight cases do not simulate this USB current path.'],
        sources=['https://www.st.com/resource/en/datasheet/usblc6-2.pdf',
                 'https://www.usb.org/sites/default/files/USB%20Type%20C%20Functional%20Test%20Specification%202024%2003%2003.pdf',
                 'https://www.onsemi.com/pdf/datasheet/bss138-d.pdf'])
    (out / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    (out / 'ngspice.log').write_text('\n'.join(ng.log) + '\n')
    print(json.dumps({k: result[k] for k in ['analysis_completed', 'simulations_completed',
          'hardware_fix_verified', 'observed_nominal_R18_backfeed_uA']}, indent=2))


if __name__ == '__main__':
    main()
