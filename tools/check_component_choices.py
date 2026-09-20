#!/usr/bin/env python3
"""Reproduce prototype capacitor, crystal-load and USB steady-state estimates.

Inputs are archived manufacturer *typical* DC-bias curves and explicitly named
assumptions. This is not a guaranteed corner model, USB compliance test, or a
substitute for measuring oscillator start-up and frequency on the routed PCB.
"""
from pathlib import Path
import json
import math

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/components'


def bias(mpn, voltage):
    source = json.loads((OUT / f'{mpn}-dc-bias.json').read_text())
    points = source['bias_V_deltaC_percent']
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= voltage <= x1:
            return y0 + (y1-y0)*(voltage-x0)/(x1-x0)
    raise ValueError((mpn, voltage))


capacitors = []
for refs, mpn, nominal, voltage, minimum in [
    ('C1 C2 C4', 'CL32B226KAJNNNE', 22, 5.5, 10),
    ('C5 C6 C9', 'CL31A226KAHNNNE', 22, 3.393, 11),
    ('C17 C19 C40', 'CL31B106KAHNNNE', 10, 5.5, 4.7),
    ('C21 C22', 'CL21B225KAFNNNE', 2.2, 1.8, None),
    ('C23 C24', 'CL21B225KAFNNNE', 2.2, 5.25, None),
    ('C15', 'CL21B105KBFNNNE', 1, 3.393, None),
    ('C42', 'CL21B105KBFNNNE', 1, 13.5, None),
    ('C44', 'CL21B475KAFNNNE', 4.7, 3.135, None),
    ('C46', 'CL31B475KBHNNNE', 4.7, 13.5, None),
    ('C47', 'CL21B225KAFNNNE', 2.2, 13.5, None),
]:
    delta = bias(mpn, voltage)
    typ = nominal * (1 + delta/100)
    # Deliberate screening allowances; independent multiplication is an estimate,
    # not a guaranteed combined voltage/temperature/aging characteristic.
    screening = typ * .90 * .85 * .95
    if minimum is not None:
        assert screening > minimum, (refs, screening, minimum)
    capacitors.append(dict(refs=refs, mpn=mpn, nominal_uF=nominal,
                           evaluated_bias_V=voltage, typical_bias_change_pct=delta,
                           typical_biased_uF=typ, screening_uF=screening,
                           screening_target_uF=minimum))

# AN14518 rev.6 Fig.5 convention includes crystal shunt capacitance.
# PCB parasitics below are measured on NXP's OM27160, not on this unlaid PCB.
ci, co = 2.0, 2.0  # PN7160 datasheet Table 46, typical pF
pcb_i, pcb_o, pcb_cross = 1.19, 1.31, 1.39  # AN14518 Table 2
c0, cm, cl = .60, .00154, 10.0  # pF, NDK EXS11B-10535
c26, c27 = 12.0, 15.0
a, b = ci + pcb_i + c26, co + pcb_o + c27
seen = a*b/(a+b) + pcb_cross + c0
offset = (math.sqrt((1+cm/(c0+seen))/(1+cm/(c0+cl)))-1)*1e6
# Equal capacitors giving the same target under the same NXP model.
lo, hi = 0.0, 40.0
for _ in range(80):
    mid = (lo+hi)/2
    x, y = ci+pcb_i+mid, co+pcb_o+mid
    if x*y/(x+y)+pcb_cross+c0 < cl:
        lo = mid
    else:
        hi = mid
equal = (lo+hi)/2
assert 12 < equal < 14 and -5 < offset < 0

usb = dict(source_min_V=4.75, source_rating_A=1.5,
           diode_drop_allowance_V_each=.5, vsys_min_estimate_V=3.75,
           buck_output_V=3.393, buck_output_A=.5, buck_efficiency=.85,
           oled_output_V=13.5, oled_output_A=.030, oled_efficiency=.75,
           nfc_allowance_A=.290, charger_max_A=.115,
           auxiliary_allowance_A=.020)
usb['estimated_continuous_input_A'] = (
    usb['buck_output_V']*usb['buck_output_A']/usb['buck_efficiency']
    + usb['oled_output_V']*usb['oled_output_A']/usb['oled_efficiency']
) / usb['vsys_min_estimate_V'] + usb['nfc_allowance_A'] + usb['charger_max_A'] + usb['auxiliary_allowance_A']
usb['source_current_margin_A'] = usb['source_rating_A'] - usb['estimated_continuous_input_A']
assert usb['source_current_margin_A'] > .3

report = dict(
    scope='Prototype engineering estimates; not measured or guaranteed limits',
    capacitor_screening_factors=dict(tolerance=.90, temperature=.85,
                                    additional_aging_margin_assumption=.95),
    capacitors=capacitors,
    oscillator=dict(crystal='NDK NX2016SA-27.12MHZ-EXS00A-CS06346',
                    frequency_Hz=27120000, load_pF=cl, shunt_pF=c0,
                    motional_pF=cm, pin_pF=[ci, co],
                    assumed_NXP_EVK_pcb_pF=[pcb_i, pcb_o, pcb_cross],
                    calculated_equal_external_pF=equal,
                    populated_external_pF=[c26, c27],
                    nxp_model_seen_pF=seen, nominal_model_offset_ppm=offset,
                    caveat='NXP reference-board parasitics and typical IC/crystal values; actual PCB and initial frequency error are unknown. NXP Fig.5 shunt-capacitance convention is used explicitly. Measure the carrier; do not treat this offset as a prediction for manufactured hardware.'),
    usb=usb,
)
(OUT / 'calculations.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
