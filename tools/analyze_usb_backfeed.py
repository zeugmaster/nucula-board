#!/usr/bin/env python3
"""Screen the measured Rev-A hypothesis and the revised USB isolation circuit.

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
    from check_usb_backfeed import audit
    assert audit(ROOT/'nucula-v2.kicad_pcb', ROOT/'docs/netlist.xml')['passed']
    # Rev-A had 100k. Never reinterpret its measured current using the new 10k.
    historical_r18 = 100e3
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
                 f'R18 vbus 0 {historical_r18}',
                 f'C14 vbus 0 {d.value("C14")}',
                 'Rmeter vbus 0 10Meg', 'Rnumeric clamp 0 1e12',
                 '.options reltol=1e-8 abstol=1e-14', '.op', '.end']
        ng.run(lines)
        vbus = float(ng.get('vbus')[0])
        assert vbus > .8 if state == 'battery_usb_active' else abs(vbus) < .001
        rows.append(dict(state=state, source_V=voltage, assumed_diode_N=ideality,
                         assumed_diode_Is_A=saturation, VBUS_V=vbus,
                         Dplus_V=float(ng.get('dp')[0]),
                         R18_current_uA=vbus / historical_r18 * 1e6))
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
    corrected = []
    for voltage, usb_present, injected_uA in itertools.product([3.0, 3.3, 3.6], [False, True], [0, 1, 10]):
        # Deliberately partial DC model. The datasheet truth table supplies the
        # switch state; Q2 threshold/startup, the ESP PHY and TVS surges are absent.
        # Roff bounds leakage at 1uA for this drive voltage; not a fitted model.
        lines = ['Revised USB circuit; bounded DC isolation screen',
                 f'Vlogic logic 0 {voltage}', 'Rpull logic phy 1.5k',
                 f'Rseries phy switched {d.value("R13")}',
                 f'Rswitch switched dp {10 if usb_present else voltage/1e-6}',
                 'Rhost dp 0 15k',  # Powered-off/attached host pulldown.
                 f'R18 vbus 0 {d.value("R18")*1.01}',
                 f'Iother 0 vbus {injected_uA*1e-6}',
                 f'R17 logic oe {d.value("R17")*1.01}',
                 'Icontrol oe 0 1u',
                 f'Rq2 oe 0 {10 if usb_present else 1e12}',
                 *(['Vusb vbus 0 5'] if usb_present else []), '.op', '.end']
        ng.run(lines)
        dp, vbus, oe = [float(ng.get(x)[0]) for x in ['dp', 'vbus', 'oe']]
        assert (dp > 2.7 and oe < .5) if usb_present else (dp < .02 and oe > 1.3 and vbus < .11)
        corrected.append(dict(logic_V=voltage, USB_present=usb_present,
            assumed_other_VBUS_injection_uA=injected_uA, connector_Dplus_V=dp,
            VBUS_V=vbus, enable_V=oe))
        if voltage == 3.3 and injected_uA == 0:
            save_circuit(out, 'revised_usb_on' if usb_present else 'revised_battery_only', lines)
    result = dict(
        analysis_completed=True, hardware_fix_verified=False,
        hardware_circuit_changed=True, bench_measurements_pending=True,
        baseline_dc_measurements_completed=True,
        historical_design_decision=measurements['design_decision'],
        current_design='Ground-only data TVS U4; separate VBUS TVS D5; U10 isolates both data lines under Q2/R17 control.',
        pending_bench_checks=['RESET transient waveform capture',
                              'Validation of a permanent remedy and repeated USB reconnection'],
        simulations_completed=ng.count, solver_errors=[],
        source_sha256={name: sha(ROOT / name) for name in
                       ['nucula-v2.kicad_pcb', 'power-mcu.kicad_sch', 'docs/netlist.xml',
                        'tools/analyze_usb_backfeed.py', 'tools/simulate_preflight.py', measurement_path]},
        accepted_historical_path=['U3.14 / IO19', 'R13.2 -> R13.1 (22 ohm)',
                       'U4.4 -> internal upper steering diode -> U4.5',
                       'J1 VBUS / C14.1 / R18.1 / Q2 gate'],
        observed_battery_only=measurements['battery_only'],
        observed_VBUS_V=released['VBUS_C14_1_V'],
        observed_nominal_R18_backfeed_uA=released['VBUS_C14_1_V']/historical_r18*1e6,
        observed_Dplus_minus_VBUS_V=round(released['Dplus_R13_1_V']-released['VBUS_C14_1_V'], 6),
        observed_steady_3V3_difference_V=round(released['3V3_C11_1_V']-held['3V3_C11_1_V'], 6),
        maximum_total_injected_uA_for_VBUS_below_0_8V_at_R18_plus_1pct=.8/(d.value('R18')*1.01)*1e6,
        interpretation='Measured D+ and VBUS collapse on RESET while steady +3V3 remains at 3.33 V. '
            'Together with the topology and 0.79 V D+-to-VBUS difference, this strongly supports the U4 path. '
            'Simulated voltages do not identify the physical source or reproduce the observed voltage quantitatively. '
            'The user accepts this diagnosis for redesign without physical isolation. '
            'U4 pin-5 isolation was not performed; steady meter readings do not exclude brief rail transients.',
        historical_R18_ohm=historical_r18,
        historical_dc_scenarios=rows, revised_discharge_scenarios=discharge,
        revised_dc_scenarios=corrected,
        limits=['Illustrative ESP pull-up and diode models; no parameter fitted to the measured voltages.',
                'No USB-C source state machine, ESP reset/ROM behavior, Q2 switching threshold, or firmware model.',
                'D1/D2 leakage, TP4054 reverse current, contamination, cable and oscilloscope loading are omitted.',
                'Isolation scenarios are bench diagnostics; leaving U4.5 disconnected removes its VBUS protection.',
                'Existing 261 preflight cases do not simulate this USB current path.',
                'Revised DC cases assume the switch truth table and Q2 state; not manufacturer IC macromodels.',
                '1uA disabled data leakage and 1uA control leakage are bounds; 10uA other VBUS injection is an explicit stress assumption.',
                'IOFF is specified only at VCC=0; intermediate supply ramp and host-powered startup require hardware checks.',
                'Switch on-resistance and 15k host loads screen DC attach only, not packet edges or ESD performance.'],
        sources=['https://www.st.com/resource/en/datasheet/usblc6-2.pdf',
                 'https://www.usb.org/sites/default/files/USB%20Type%20C%20Functional%20Test%20Specification%202024%2003%2003.pdf',
                 'https://www.onsemi.com/pdf/datasheet/bss138-d.pdf',
                 'https://www.ti.com/lit/ds/symlink/ts3usb30e.pdf',
                 'https://www.ti.com/lit/ds/symlink/tpd2e2u06-q1.pdf',
                 'https://www.ti.com/lit/ds/symlink/tpd1e10b06.pdf'])
    (out / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    (out / 'ngspice.log').write_text('\n'.join(ng.log) + '\n')
    print(json.dumps({k: result[k] for k in ['analysis_completed', 'simulations_completed',
          'hardware_fix_verified', 'observed_nominal_R18_backfeed_uA']}, indent=2))


if __name__ == '__main__':
    main()
