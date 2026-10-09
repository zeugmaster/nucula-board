#!/usr/bin/env python3
"""Compare HP and CS in the unchanged NFC network; no matching-value optimization.

Engineering acceptance: <=10% change in carrier impedance and coil current in
paired scenarios, CS terminal RMS below 0.4 A at ideal 5.5 V square drive,
and capacitor peak voltage below rated voltage. RF-loss heating is estimated
from the manufacturer's DC 15 C-rise reference, not a validated thermal model.
"""
import sys,json,math,itertools,hashlib,csv
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from simulate_preflight import Design,Ngspice,rf_circuit,rf_result,RF_REFS,F0,sha
from nfc.inductor_models import MODELS
OUT=ROOT/'docs/components/substitutions-2026-10-09'

def main():
 d=Design();ng=Ngspice();base=json.loads((ROOT/'docs/nfc/calculations.json').read_text())['fitted_model_assumptions']
 nominal=dict(la=base['la_uH']*1e-6,ra=base['ra_ohm'],ca=base['ca_pF']*1e-12)
 cases=[('nominal',nominal,{})]
 for rx_esr,match_esr in itertools.product([.003,.3],repeat=2):
  cases.append((f'new_cap_esr_{rx_esr}_{match_esr}',dict(nominal,cap_esr_by_ref=dict(C28=rx_esr,C29=rx_esr,C36=match_esr,C37=match_esr)),{}))
 # Paired engineering corners, not a proof of all combinations or production yield.
 for lf,ra,ca,rin,sgn in itertools.product([.9,1.1],[1.,2.5],[1e-12,5e-12],[1000,10000],[-1,1]):
  scales={r:1+sgn*d.tolerance(r) for r in RF_REFS if r not in d.dnp and d.value(r)>0}
  cases.append((f'corner-{len(cases)}',dict(la=nominal['la']*lf,ra=ra,ca=ca,rin=rin),scales))
 rng=np.random.default_rng(20261009)
 for i in range(200):
  scales={r:1+rng.uniform(-d.tolerance(r),d.tolerance(r)) for r in RF_REFS if r not in d.dnp and d.value(r)>0}
  cases.append((f'part-{i}',nominal,scales))
 rows=[];drive=2*math.sqrt(2)*5.5/math.pi
 for name,params,scales in cases:
  pair={}
  for mpn in MODELS:
   actual_params=dict(params)
   if mpn=='0805HP-151XGRC':actual_params.pop('cap_esr_by_ref',None)
   lines=rf_circuit(d,actual_params,scales,inductor_mpn=mpn);ng.run(lines)
   result=rf_result(ng,d)
   tx=max(abs(ng.get('vp#branch')[0]),abs(ng.get('vn#branch')[0]))*drive
   v=lambda node: 0j if node=='0' else ng.get(node)[0]
   capv={r:float(abs(v(d.node(r,1))-v(d.node(r,2)))*drive*math.sqrt(2)) for r in RF_REFS if r.startswith('C') and r not in d.dnp}
   damping=max(abs(v(d.node(r,1))-v(d.node(r,2)))**2*drive**2/(d.value(r)*scales.get(r,1)) for r in ['R27','R28'])
   result.update(tx_rms_A_at_5V5=float(tx),max_capacitor_peak_V_at_5V5=max(capv.values()),capacitor_peak_V=capv,damping_each_W_at_5V5=float(damping))
   pair[mpn]=result
   if name=='nominal':(OUT/('nfc-'+mpn+'.cir')).write_text('\n'.join(lines)+'\n')
  a,b=pair.values();za=complex(a['z_real_ohm'],a['z_imag_ohm']);zb=complex(b['z_real_ohm'],b['z_imag_ohm'])
  rows.append(dict(case=name,impedance_change_pct=100*abs(zb-za)/abs(za),coil_current_change_pct=100*(b['coil_rms_A_at_3V3_fundamental']/a['coil_rms_A_at_3V3_fundamental']-1),**b))
  if name=='nominal':nominal_pair=pair
 # Odd harmonics with frequency-dependent manufacturer loss, from balanced math.
 sys.path.insert(0,str(ROOT/'tools/nfc'));import calculate as c
 harmonic=[];max_harmonic_heat=0
 for mpn in MODELS:
  c.SELECTED=mpn;m=MODELS[mpn];loss=0;irms2=0
  for n in range(1,40,2):
   f=F0*n;z,_=c.network(f,nominal['la'],nominal['ra'],nominal['ca'],2.7,68e-12,100e-12)
   current=drive/n/abs(z);loss+=current**2*c.inductor_z(f).real;irms2+=current**2
  harmonic.append(dict(mpn=mpn,terminal_rms_A_odd_1_to_39=float(math.sqrt(irms2)),inductor_loss_W=float(loss)))
 cs=harmonic[1];rise=cs['inductor_loss_W']*15/(.4**2*.56)
 maximums={k:max(abs(r[k]) for r in rows) for k in ['impedance_change_pct','coil_current_change_pct','tx_rms_A_at_5V5','max_capacitor_peak_V_at_5V5','damping_each_W_at_5V5']}
 # Individual cap ratings from the actual schematic; no generic 100V assumption.
 cap_margins={r:float(d.parts[r].find("property[@name='Voltage']").get('value').rstrip('V'))/max(row['capacitor_peak_V'][r] for row in rows) for r in rows[0]['capacitor_peak_V']}
 checks={'carrier_impedance_change_below_10pct':maximums['impedance_change_pct']<10,
 'coil_current_change_below_10pct':maximums['coil_current_change_pct']<10,
 'fundamental_terminal_current_below_400mA':maximums['tx_rms_A_at_5V5']<.4,
 'nominal_harmonic_terminal_current_below_400mA':cs['terminal_rms_A_odd_1_to_39']<.4,
 'capacitor_peak_voltages_below_ratings':min(cap_margins.values())>1,
 'damping_each_below_500mW':maximums['damping_each_W_at_5V5']<.5,
 'nominal_loss_doubled_85C_ambient_below_140C':85+2*rise<140}
 report=dict(passed=all(checks.values()),checks=checks,nominal=nominal_pair,paired_cases=len(rows),spice_cases=ng.count,maximums=maximums,capacitor_voltage_margin_ratios=cap_margins,harmonics=harmonic,nominal_estimated_rise_C=rise,source_sha256={p:sha(ROOT/p) for p in ['nucula-v2.kicad_pcb','nfc.kicad_sch','docs/netlist.xml','tools/nfc/inductor_models.py','tools/nfc/qualify_substitution.py']},limitations=['Typical component models; coil R/L/C and RX load are assumed, not measured.','Paired finite corners and random scatter do not prove a global worst case.','No controller nonlinearity, tag, read-range, thermal extraction, RF emissions or full-board EM model.','Thermal estimate uses DC-derived thermal resistance, 85C ambient and doubled nominal RF loss; requires bench verification.','No guarantee that tuning or firmware adjustment will be unnecessary.'],rows=rows)
 OUT.mkdir(exist_ok=True);(OUT/'rf-qualification.json').write_text(json.dumps(report,indent=2)+'\n');(OUT/'rf-qualification.log').write_text('\n'.join(ng.log)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ['rows','source_sha256']},indent=2))
 assert report['passed'],checks
if __name__=='__main__':main()
