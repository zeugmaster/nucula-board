#!/usr/bin/env python3
"""Cross-check balanced half-circuit math with full differential ngspice.

Uses KiCad's bundled shared library on macOS; NGSPICE_LIBRARY overrides path.
Coilcraft Rvar is frozen at 13.56 MHz for this single-frequency regression.
The generated .cir is also usable in standalone ngspice.
"""
from pathlib import Path
import ctypes as c
import json
import math
import os

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/nfc'


def main():
    calc=json.loads((OUT/'calculations.json').read_text())
    model=calc['fitted_model_assumptions']
    la=model['la_uH']*1e-6;ra=model['ra_ohm'];ca=model['ca_pF']*1e-12
    rskin=1.554e-4*math.sqrt(13.56e6)
    lines=['Nucula NFC full differential passive model / 13.56MHz',
           '* Assumed bare-coil model; no nonlinear PN7160 or tag coupling.',
           '* Coilcraft 0805HP-151 doc 158-1/158-27; Rvar frozen at f0.',
           'VP txp 0 DC 0 AC 0.5 0','VN txn 0 DC 0 AC 0.5 180',
           '.subckt emc a b', 'Rd a x .288',f'Rskin x y {rskin:.15g}',
           'Lcore y b 148.8n','Cpar x z .135p','Rpar z b 10','.ends emc',
           'XLP txp ep emc','XLN txn en emc',
           'Rcp0 ep ep0 .03','Cp0 ep0 0 360p','Rcn0 en en0 .03','Cn0 en0 0 360p',
           'Rcp1 ep sp .03','Cp1 sp mp 68p','Rcn1 en sn .03','Cn1 sn mn 68p',
           'Rcp2 mp mp0 .03','Cp2 mp0 0 100p','Rcn2 mn mn0 .03','Cn2 mn0 0 100p',
           'Rqp mp ap 2.7','Rqn mn an 2.7',f'Ra ap ai {ra:.15g}',f'La ai an {la:.15g}',f'Ca ap an {ca:.15g}',
           'Rrxp ep rp 2200','Rcxp rp rp1 .03','Crxp rp1 rxp 1n','Rinp rxp 0 2200',
           'Rrxn en rn 2200','Rcxn rn rn1 .03','Crxn rn1 rxn 1n','Rinn rxn 0 2200',
           '.ac lin 1 13.56Meg 13.56Meg','.end']
    (OUT/'matching.cir').write_text('\n'.join(lines)+'\n')
    libpath=os.environ.get('NGSPICE_LIBRARY','/Applications/KiCad/KiCad.app/Contents/Frameworks/libngspice.0.dylib')
    lib=c.CDLL(libpath)
    output=[];exits=[]
    send_type=c.CFUNCTYPE(c.c_int,c.c_char_p,c.c_int,c.c_void_p)
    exit_type=c.CFUNCTYPE(c.c_int,c.c_int,c.c_bool,c.c_bool,c.c_int,c.c_void_p)
    @send_type
    def send(msg,ident,ptr):output.append(msg.decode(errors='replace'));return 0
    @exit_type
    def exited(code,immediate,quit_,ident,ptr):exits.append(code);return 0
    # KiCad's bundled ngspice 45 crashes in ngSpice_nospinit before callbacks
    # are registered. Initialize its normal shared-library interface directly.
    lib.ngSpice_Init.argtypes=[c.c_void_p]*7
    lib.ngSpice_Init(send,None,exited,None,None,None,None)
    lib.ngSpice_Command.argtypes=[c.c_char_p]
    lib.ngSpice_Command(b'version')
    arr=(c.c_char_p*(len(lines)+1))(*[s.encode() for s in lines],None)
    lib.ngSpice_Circ.argtypes=[c.POINTER(c.c_char_p)]
    assert lib.ngSpice_Circ(arr)==0
    assert lib.ngSpice_Command(b'run')==0
    class Complex(c.Structure):_fields_=[('real',c.c_double),('imag',c.c_double)]
    class Vector(c.Structure):
        _fields_=[('name',c.c_char_p),('type',c.c_int),('flags',c.c_short),
                  ('real',c.POINTER(c.c_double)),('complex',c.POINTER(Complex)),('length',c.c_int)]
    lib.ngGet_Vec_Info.argtypes=[c.c_char_p];lib.ngGet_Vec_Info.restype=c.POINTER(Vector)
    def get(name):
        p=lib.ngGet_Vec_Info(name.encode());assert p, name
        v=p.contents;assert v.length==1 and v.complex
        return complex(v.complex[0].real,v.complex[0].imag)
    z=2/(get('vn#branch')-get('vp#branch'))
    expected=complex(calc['assembly']['z_diff_real_ohm'],calc['assembly']['z_diff_imag_ohm'])
    rel=abs(z-expected)/abs(expected)
    assert rel<1e-8,(z,expected,rel)
    assert not exits and not any('error' in s.lower() for s in output),output
    result={'status':'pass','engine':'ngspice shared library bundled with KiCad',
            'version_output':[s for s in output if 'ngspice-' in s],
            'frequency_Hz':13.56e6,'full_differential_Z_ohm':[z.real,z.imag],
            'half_circuit_Z_ohm':[expected.real,expected.imag], 'relative_difference':rel,
            'note':'Numerical agreement validates circuit math only, not the assumed antenna parameters.'}
    (OUT/'spice-check.json').write_text(json.dumps(result,indent=2)+'\n')
    (OUT/'spice.log').write_text('\n'.join(output)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
