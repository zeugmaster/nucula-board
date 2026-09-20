#!/usr/bin/env python3
"""Reproducible quasi-static coil estimates and balanced RF matching calculation.

Requires numpy, scipy, matplotlib. No remote services. Does not alter KiCad files.
--la-uh/--ra-ohm/--ca-pf accept FITTED series RL || C parameters, not the
apparent Im(Z)/omega at 13.56 MHz with Ca added a second time.
Use --out /tmp/my-measurement to preserve the documented baseline artifacts.
"""
from pathlib import Path
import argparse
import csv
import json
import math
import sys
import numpy as np
from scipy.optimize import least_squares
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from generate_coil import geometry, WIDTH, GAP, OUTER, TURNS, ROOT

MU0 = 4 * math.pi * 1e-7
F0 = 13.56e6
RHO_CU = 1.724e-8  # ohm m, 20 C annealed copper engineering value


def inductance_estimates():
    dout, w, gap = OUTER / 1000, WIDTH / 1000, GAP / 1000
    din = dout - 2 * (TURNS * w + (TURNS - 1) * gap)
    dav = (dout + din) / 2
    rho = (dout - din) / (dout + din)
    mohan = MU0 * TURNS**2 * dav * 1.27 / 2 * (math.log(2.07 / rho) + .18 * rho + .13 * rho**2)
    wheeler = 2.34 * MU0 * TURNS**2 * dav / (1 + 2.75 * rho)
    # Neumann line integral, exact for axis-parallel filament pairs.
    # Thin rectangular strip self-term regularized by GMD ~0.2235*(w+t).
    # Uniform-current magnetostatic approximation, NOT full-wave EM/RF extraction.
    points = np.array(geometry()[2]) / 1000
    segs = list(zip(points, points[1:]))
    gmd = .2235 * (w + 35e-6)
    partial = 0.
    for i, (a, b) in enumerate(segs):
        length = np.linalg.norm(b - a)
        k = int(np.argmax(abs(b - a)))
        self_gmd = .2e-3 if k == 2 else gmd  # plated barrel radius approximation
        partial += MU0 / (2 * math.pi) * (length * math.asinh(length / self_gmd) - math.hypot(length, self_gmd) + self_gmd)
        for c, d in segs[:i]:
            k2 = int(np.argmax(abs(d - c)))
            if k2 != k:
                continue  # orthogonal dl dot dl = 0
            direction = np.sign((b[k] - a[k]) * (d[k] - c[k]))
            aa, bb = sorted([a[k], b[k]])
            cc, dd = sorted([c[k], d[k]])
            sep = float(np.linalg.norm(np.delete(a - c, k)))
            def primitive(x):
                if sep < 1e-14:
                    return 0. if abs(x) < 1e-14 else abs(x) * (math.log(abs(x)) - 1)
                return x * math.asinh(x / sep) - math.hypot(x, sep)
            integral = primitive(bb - cc) + primitive(aa - dd) - primitive(aa - cc) - primitive(bb - dd)
            partial += 2 * MU0 / (4 * math.pi) * direction * integral
    length = sum(np.linalg.norm(b - a) for a, b in segs if abs(b[2] - a[2]) < 1e-12)
    rdc = RHO_CU * length / (w * 35e-6)
    delta = math.sqrt(2 * RHO_CU / (2 * math.pi * F0 * MU0))
    # Two broad surfaces, exponential depth approximation; ignores proximity loss.
    teff = 2 * delta * (1 - math.exp(-35e-6 / (2 * delta)))
    rskin = RHO_CU * length / (w * teff)
    return dict(inner_opening_mm=din * 1000, fill_ratio=rho,
                mohan_current_sheet_uH=mohan * 1e6, modified_wheeler_uH=wheeler * 1e6,
                neumann_filament_gmd_uH=partial * 1e6, planar_trace_length_mm=length * 1000,
                rdc_trace_ohm=rdc, skin_depth_um=delta * 1e6,
                two_surface_skin_only_ohm=rskin)


def inductor_z(f, scale=1.):
    """Coilcraft 0805HP-151 model, doc 158-1/158-27 (2017).
    R2 + ((Rvar + jwL) || (R1 + 1/jwC)); Rvar=k*sqrt(f).
    Typical model values; mounted board parasitics are not included.
    """
    w = 2 * np.pi * f
    branch_l = 1.554e-4 * np.sqrt(f) + 1j * w * 148.8e-9 * scale
    branch_c = 10. + 1 / (1j * w * .135e-12)
    return .288 + 1 / (1 / branch_l + 1 / branch_c)


def coil_z(f, la, ra, ca):
    # RF resistance held constant in the narrow-band design model.
    return 1 / (1 / (ra + 1j * 2 * np.pi * f * la) + 1j * 2 * np.pi * f * ca)


def network(f, la, ra, ca, rq, c1, c2, c0=360e-12, lscale=1., rx=True):
    """Odd-mode half circuit. C0/C1/C2 are EACH physical branch value.
    Returns DIFFERENTIAL input impedance and half-circuit node voltage ratios.
    Capacitor ESR 0.03 ohm/part is an assumption, included in solve and sweeps.
    """
    w = 2 * np.pi * f
    cap = lambda c: .03 + 1 / (1j * w * c)
    za = coil_z(f, la, ra, ca)
    zd = rq + za / 2
    zp = 1 / (1 / zd + 1 / cap(c2))
    zs = cap(c1) + zp
    # RX input impedance is AGC dependent. Representative 2.2k internal
    # shunt is an assumption; the 2.2k external + 1nF are NXP start values.
    zrx = 2200. + 2200. + cap(1e-9)
    z0 = 1 / (1 / cap(c0) + 1 / zs + (1 / zrx if rx else 0.))
    zl = inductor_z(f, lscale)
    zh = zl + z0
    vemc = z0 / zh
    vmatch = vemc * zp / zs
    vant = vmatch * (za / 2) / zd
    return 2 * zh, (vemc, vmatch, vant)


def solve(la, ra, ca, target, q=20., c0=360e-12):
    za = coil_z(F0, la, ra, ca)
    rq = max(0., (za.imag / q - za.real) / 2)
    def residual(logc):
        c1, c2 = np.exp(logc) * 1e-12
        z, _ = network(F0, la, ra, ca, rq, c1, c2, c0)
        return [(z.real - target) / target, z.imag / target]
    for initial in ([65., 100.], [60., 80.], [50., 50.], [80., 60.]):
        sol = least_squares(residual, np.log(initial),
                            bounds=(np.log([1., 1.]), np.log([1000., 1000.])),
                            xtol=1e-13, ftol=1e-13, gtol=1e-13)
        if np.linalg.norm(sol.fun) < 1e-7:
            break
    assert sol.success and np.linalg.norm(sol.fun) < 1e-7, sol.message
    c1, c2 = np.exp(sol.x)
    return dict(c1_pF=float(c1), c2_pF=float(c2), rq_each_ohm=float(rq), target_ohm=target)


def nxp_example_check():
    # Independent closed-form inversion of the ideal NXP half circuit.
    # Figure 24: 1522 nH / 1.4 ohm / .1pF / Q20 / target20 / L0 160nH / C0 330pF.
    w = 2 * math.pi * F0
    za = coil_z(F0, 1522e-9, 1.4, .1e-12)
    rq = (w * 1522e-9 / 20 - 1.4) / 2
    zh = (za + 2 * rq) / 2
    needed = 1 / (1 / (10 - 1j * w * 160e-9) - 1j * w * 330e-12)
    y = 1 / zh
    # Select inductive shunt impedance so subsequent series C cancels it.
    b = -math.sqrt(y.real / needed.real - y.real**2)
    c2 = (b - y.imag) / w
    zp = 1 / complex(y.real, b)
    c1 = 1 / (w * (zp.imag - needed.imag))
    assert abs(c1 * 1e12 - 65.1) < .5
    assert abs(c2 * 1e12 - 111.) < 1.
    return dict(c1_pF=c1 * 1e12, c2_pF=c2 * 1e12, rq_ohm=rq)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--la-uh', type=float)
    parser.add_argument('--ra-ohm', type=float, default=1.5)
    parser.add_argument('--ca-pf', type=float, default=2.)
    parser.add_argument('--target-ohm', type=float, default=20.)
    parser.add_argument('--out', type=Path, default=ROOT / 'docs/nfc')
    args = parser.parse_args()
    estimates = inductance_estimates()
    la = (args.la_uh if args.la_uh is not None else estimates['mohan_current_sheet_uH']) * 1e-6
    ra, ca = args.ra_ohm, args.ca_pf * 1e-12
    assert la > 0 and ra > 0 and ca >= 0 and args.target_ohm > 0
    baseline = solve(la, ra, ca, args.target_ohm)
    # E24/E12 initial assembly, changed only after reviewing report.
    c1, c2, rq = 68e-12, 100e-12, 2.7
    z, ratios = network(F0, la, ra, ca, rq, c1, c2)
    isolated_z, _ = network(F0, la, ra, ca, rq, c1, c2, rx=False)
    trims = []
    for name, delta in [('C1', 1e-12), ('C2', 1e-12), ('C0', 10e-12)]:
        tz, _ = network(F0, la, ra, ca, rq,
                        c1 + (delta if name == 'C1' else 0),
                        c2 + (delta if name == 'C2' else 0),
                        360e-12 + (delta if name == 'C0' else 0))
        trims.append(dict(change=name, added_each_leg_pF=delta*1e12,
                          z_diff_real_ohm=tz.real, z_diff_imag_ohm=tz.imag))
    za = coil_z(F0, la, ra, ca)
    f = np.linspace(8e6, 22e6, 1401)
    zin, vs = network(f, la, ra, ca, rq, c1, c2)
    gamma = (zin - args.target_ohm) / (zin + args.target_ohm)
    # Seeded uniform engineering scatter, not a yield prediction. Independent
    # per-branch variations belong in the full nodal check; here pairs track.
    rng = np.random.default_rng(7160)
    size = 10000
    lmc = la * rng.uniform(.9, 1.1, size)
    rmc = rng.uniform(1., 2.5, size)
    camc = rng.uniform(1e-12, 5e-12, size)
    zmc, _ = network(F0, lmc, rmc, camc, rq * rng.uniform(.99, 1.01, size),
                      c1 * rng.uniform(.98, 1.02, size), c2 * rng.uniform(.98, 1.02, size),
                      360e-12 * rng.uniform(.98, 1.02, size), rng.uniform(.98, 1.02, size))
    # Fundamental estimate for ideal differential square drive: V1rms=2sqrt(2)VTVDD/pi.
    stress = []
    for tvdd in [2.7, 3.3, 5.]:
        vdiff = 2 * math.sqrt(2) / math.pi * tvdd
        iin = vdiff / abs(z)
        ia = abs(ratios[2]) * vdiff / abs(za)
        stress.append(dict(tvdd_V=tvdd, differential_fundamental_rms_V=vdiff,
                           tx_fundamental_rms_A=iin, coil_fundamental_rms_A=ia,
                           damping_each_W=ia**2 * rq,
                           coil_differential_peak_V=math.sqrt(2) * abs(ratios[2]) * vdiff,
                           ideal_driver_real_power_W=vdiff**2 * (1 / z).real))
    sensitivity = []
    for lfactor in [.9, 1., 1.1]:
        for cp in [1., 2., 5.]:
            for r in [1., 1.5, 2.5]:
                sensitivity.append(dict(la_uH=la * lfactor * 1e6, ra_ohm=r, ca_pF=cp,
                    **solve(la * lfactor, r, cp * 1e-12, args.target_ohm)))
    report = dict(frequency_Hz=F0, estimates=estimates,
                  fitted_model_assumptions=dict(la_uH=la*1e6, ra_ohm=ra, ca_pF=ca*1e12,
                      measured=False, capacitor_esr_each_ohm=.03, rx_internal_each_ohm=2200.),
                  nxp_figure24_regression=nxp_example_check(), exact_solve=baseline,
                  alternate_13ohm_solve=solve(la, ra, ca, 13.),
                  isolated_rx_removed_Z_ohm=[isolated_z.real, isolated_z.imag],
                  paired_trim_examples=trims,
                  assembly=dict(c0_pF=360., c1_pF=68., c2_pF=100., rq_each_ohm=rq,
                      z_diff_real_ohm=z.real, z_diff_imag_ohm=z.imag,
                      coil_damped_q=za.imag/(za.real+2*rq),
                      emc_nominal_resonance_MHz=1/(2*np.pi*np.sqrt(150e-9*360e-12))/1e6,
                      modeled_inductor_z_real_ohm=inductor_z(F0).real,
                      modeled_inductor_z_imag_ohm=inductor_z(F0).imag,
                      return_loss_to_target_dB=-20*math.log10(abs((z-args.target_ohm)/(z+args.target_ohm))),
                      coil_srf_MHz=1/(2*np.pi*np.sqrt(la*ca))/1e6 if ca else None),
                  stress_fundamental_only=stress,
                  scatter_10000_seed7160=dict(real_range_ohm=[float(zmc.real.min()),float(zmc.real.max())],
                      imag_range_ohm=[float(zmc.imag.min()),float(zmc.imag.max())],
                      note='Uniform assumed uncertainty; balanced paired variations; not manufacturing yield'),
                  retuning_scenarios=sensitivity,
                  limitations=['Quasi-static estimates, not a full-wave EM simulation.',
                    'Ra and Ca are assumed, not extracted or measured.',
                    'No tag coupling, metal, ferrite, reader driver impedance or nonlinear RX model.',
                    'Square-wave harmonics, transient overshoot and card-mode external fields not in stress estimate.'])
    out=args.out;out.mkdir(parents=True,exist_ok=True)
    (out/'calculations.json').write_text(json.dumps(report,indent=2)+'\n')
    with (out/'impedance-sweep.csv').open('w',newline='') as fp:
        w=csv.writer(fp);w.writerow(['frequency_Hz','Zdiff_real_ohm','Zdiff_imag_ohm','return_loss_target_dB','coil_voltage_gain'])
        w.writerows(zip(f,zin.real,zin.imag,-20*np.log10(abs(gamma)),abs(vs[2])))
    fig, axes = plt.subplots(2,1,figsize=(8,7),sharex=True,layout='constrained')
    axes[0].plot(f/1e6,zin.real,label='Resistance');axes[0].plot(f/1e6,zin.imag,label='Reactance')
    axes[0].axhline(args.target_ohm,color='.5',ls=':',label=f'{args.target_ohm:g} ohm target')
    axes[0].set(ylabel='Differential impedance (ohm)',ylim=(-80,120))
    axes[0].legend();axes[0].grid(alpha=.2)
    axes[1].plot(f/1e6,-20*np.log10(abs(gamma)),color='#227755')
    axes[1].set(xlabel='Frequency (MHz)',ylabel=f'Return loss relative to {args.target_ohm:g} ohm (dB)')
    axes[1].grid(alpha=.2)
    for ax in axes:ax.axvline(13.56,color='#aa4433',ls='--')
    fig.suptitle('NFC prototype: assumed antenna + typical RF component models\n68 pF series / 100 pF shunt / 2.7 ohm each leg')
    fig.savefig(out/'impedance-sweep.svg');plt.close(fig)
    print(json.dumps({k:v for k,v in report.items() if k not in ['retuning_scenarios','limitations']},indent=2))


if __name__ == '__main__':
    main()
