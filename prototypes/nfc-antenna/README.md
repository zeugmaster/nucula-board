# Bare NFC coil measurement coupon

Open `nfc-antenna.kicad_pro` in KiCad 10. This **46 × 48 mm** coupon contains
the same reusable antenna footprint assigned to A1 in the main schematic.
It is a passive two-terminal coil, without NFC controller, matching network or
ground plane. It is not the main product PCB.

Fabrication assumptions:

- Two copper layers, 1.6 mm FR4, 35 µm finished copper per layer.
- Four turns, 40 × 40 mm outer winding copper, 0.50 mm traces / 0.30 mm gaps.
- Two **plated** 0.40 mm holes complete the bottom-layer return; do not make them NPTH.
- Retain soldermask over the windings and underpass. Expose only the feed pads
  shown in the mask Gerbers. The inner hole has no mask opening.
- No copper pours, metal backing, ferrite, components or added test loops.
- `gerbers/` contains the copper/mask/silk/outline files and separate PTH/NPTH
  Excellon drill files. The NPTH drill file is intentionally empty.

Solder a short calibrated fixture to terminals 1 and 2 and measure while
unpowered. The two terminals are expected to be DC-connected through the coil.
Avoid adding a cable loop or measurement-fixture ground plane behind the coil.
Save the raw impedance sweep, fixture calibration and final assembly environment.

See [the design and tuning guide](../../docs/nfc-antenna.md) for measurements,
calculations, limitations and how to use the footprint in the main layout.
Native KiCad DRC and independent same-net clearance checks pass; RF behavior
still requires measurement.

Regenerate the coupon using `tools/nfc/check_coil.py` with KiCad's `pcbnew`
Python. This regenerates the `.kicad_pcb` and validation preview, so preserve
any manual coupon changes first. Re-export Gerber/drill outputs after edits.
