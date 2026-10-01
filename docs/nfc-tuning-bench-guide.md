**PN7160 antenna tuning: a bench guide for Nucula v2**

Researched 2026-09-23 for phone-to-board, bidirectional communication, with the
board acting as an emulated card. The phone is the reader and supplies the RF
field; the powered PN7160 and ESP32 answer it. No RF measurements of a physical
Nucula board were available. All existing component values are starting values.

The recommended equipment is a **100–200 MHz oscilloscope, at least 1 GSa/s on
the channels in use, and a calibrated VNA that works well at 13.56 MHz**. A scope
alone does not give the complex impedance needed to select matching components.
Start with a small inductive pickup loop for the scope. Borrow suitable RF voltage
probes and a calibrated NFC test bench for the measurements they uniquely enable.

This guide was checked against a fresh schematic netlist and the saved PCB,
including the pad numbers below. Design files were not changed. The existing
[antenna design note](nfc-antenna.md), [RF schematic](nfc/schematic.pdf),
[PCB detail](pcb/nfc.png), and [matching calculator](../tools/nfc/calculate.py)
provide the board-specific background.

**What you are trying to achieve**

For application data, begin with NFC-A / ISO-DEP card emulation, initially at
106 kbit/s. The phone sends command APDUs; your ESP32 processes them and supplies
response APDUs through PN7160. Both directions can carry application data without
switching the RF roles. This is distinct from NFC peer-to-peer. PN7160's current
datasheet limits its P2P support to older firmware; do not assume an old P2P demo
is the right foundation for a current phone application. If the phone is instead
the emulated card, the board must be configured as the reader and generate RF.
[AN13861, sections 2–5](https://www.nxp.com/docs/en/application-note/AN13861.pdf)
describes host-based versus internal NDEF card emulation;
[datasheet, sections 2 and 6](https://www.nxp.com/docs/en/data-sheet/PN7160_PN7161.pdf)
records the firmware differences.

PN7160 uses active load modulation (ALM) to reply in card mode. The same matching
network is used for reader and card operation, but successful reader-mode tuning
does not establish successful card-mode replies. Card-mode phase, amplitude,
receiver behavior, and phone interoperability must also be checked. See the
project's [AN13219 rev. 1.6, section 7](../parts%20documentation/AN13219-rev1.6.pdf).

The engineering sequence is: measure the isolated antenna in its intended
mechanical environment; calculate the matching network; fit and measure it;
verify powered operation; optimize the intended communication mode; then check
multiple devices, loads, and production samples. This is also the general
approach in [ST AN4974](https://www.st.com/resource/en/application_note/dm00347152.pdf)
and [TI SLOA241](https://www.ti.com/lit/an/sloa241c/sloa241c.pdf).
Their chip-specific impedances, register settings, and networks do not transfer
to PN7160.

**Equipment and oscilloscope specifications**

| Item | Minimum or useful capability | Recommendation for this project |
|---|---|---|
| Scope analog bandwidth | NXP specifies at least 50 MHz for carrier-envelope shaping checks | Buy 100 MHz or 200 MHz; 200 MHz adds margin for edges and general embedded work |
| Real-time sample rate | 500 MSa/s is a usable engineering floor for these observations | At least 1 GSa/s with the intended channels enabled; check shared ADC limitations |
| Channels | Two: RF pickup and trigger/power/logic | Four are convenient for RF, TVDD, IRQ, and a firmware marker |
| Record length | Enough to retain useful time resolution over a transaction | At least 1 Mpoint/channel; around 10 Mpoints is convenient |
| Acquisition | Single shot, edge trigger, waveform zoom, peak-to-peak and timing measurements | Pulse-width trigger, persistence, waveform export, and segmented capture are useful |
| Resolution | An ordinary 8-bit scope can support initial tuning | More effective resolution helps see small replies on a large carrier, but does not replace an NFC measurement fixture |
| RF pickup | Small loop held in a fixed nonmetallic fixture | Make one or use a small H-field probe; it does not touch the board electrically |
| Direct RF voltage probe | Adequate bandwidth, input range, low capacitance, and RF voltage rating | Prefer approximately 1–2 pF or less loading where practical; verify each input and differential specifications |
| VNA | Complex S11 / R+jX, calibration, and coverage of 5–25 MHz | Coverage to 100 MHz is useful for antenna self-resonance; export Touchstone data and use hundreds of points near the carrier |
| Other bench equipment | DMM, current-limited supply, fine rework tools | Microscope, temperature measurement, spare C0G capacitors/resistors, and nonmetallic distance spacers |

The scope minimum comes from [AN13219 rev. 1.6, section 10.2, p. 45](../parts%20documentation/AN13219-rev1.6.pdf).
The stronger purchase specifications above are engineering recommendations,
not additional NXP requirements. The 13.56 MHz period is about 73.75 ns, so
1 GSa/s gives about 74 samples per cycle. Tektronix's amplitude-measurement
guidance uses roughly five times the highest frequency of interest; five times
the carrier is 67.8 MHz. A 100 MHz measurement system therefore has sensible
margin for the carrier. Faster edges and harmonics need more bandwidth.
[Tektronix bandwidth guidance](https://www.tek.com/en/support/faqs/why-it-important-use-oscilloscope-more-bandwidth-my-device-under-test).

Probe loading is often more important than buying extra scope bandwidth. A
10 pF probe is a substantial addition to a 68 pF or 100 pF matching component,
depending on the node and connection. Its reactance is about 1.17 kΩ at
13.56 MHz. A 1× probe is generally a particularly poor choice for RF nodes.
Two ordinary probes with channel subtraction still add both probes' loading.
[Tektronix probe-loading explanation](https://www.tek.com/en/documents/application-note/how-oscilloscope-probes-affect-your-measurement).

For direct antenna voltage measurements, low capacitance alone is insufficient.
The project's unverified model predicts about **47 V peak differential,
94 V peak-to-peak**, even at TVDD = 3.3 V. A useful initial probe selection target
is a linear differential range of at least ±100 V, with adequate per-input
common-mode range, **rated at 13.56 MHz**; this is not a guarantee that unknown
external fields stay within that range. Check frequency derating and the linear
measurement range, not merely a DC damage rating. Many low-capacitance logic
probes cannot measure these voltages. Borrowing a suitable probe is reasonable.

For a powered board, ordinary scope ground clips connect only to PCB GND.
**Never clip one to either antenna terminal or a driven TX terminal.** Scope
channel grounds are commonly connected together and to protective earth. Do not
remove protective earth. Do not connect a bare scope 50 Ω input across the coil.
A small inductive pickup is the easiest starting point: NXP shows a probe with
its ground lead connected to its own tip, forming a loop held above the antenna.
The indicated voltage depends on loop position and is not calibrated antenna
voltage or magnetic field strength.

NXP explicitly demonstrates economical VNA measurements in
[AN12810](https://www.nxp.com/docs/en/application-note/AN12810.pdf). A NanoVNA-class
instrument can be sufficient; an expensive microwave frequency limit is not
needed. Choose usable impedance display, stable calibration, data export, and
appropriate fixtures. A scalar SWR meter and a low-frequency LCR meter do not
provide the same information. Some instruments sold as two-port VNAs only
measure S11 and S21 in one direction, so two connectors alone do not establish
full differential measurement capability.

**The actual tuning components**

Each row describes equal components on the two branches, unless stated otherwise.
NXP's generic names C0/C1/C2 are functions, not your schematic reference numbers.

| Project references | Present value, each branch | Purpose and expected changes |
|---|---|---|
| A1 | 40 × 40 mm, four-turn PCB coil | Leave the copper geometry intact initially; measure its installed impedance |
| L2 / L3 | 150 nH, Coilcraft 0805HP-151XGRC | EMC filter inductors; retain initially |
| C30 / C31 | 330 pF | Main EMC capacitor C0 |
| C53 / C54 | 33 pF, populated | In parallel with C30/C31: total C0 = 363 pF per branch |
| C32 / C33 | 68 pF | Series matching capacitor C1; likely replacement candidates |
| C34 / C35 | DNP | Parallel trims for C32/C33; add the same value to both |
| C36 / C37 | 100 pF | Shunt matching capacitor C2; likely replacement candidates |
| C38 / C39 | DNP | Parallel trims for C36/C37; add the same value to both |
| R27 / R28 | 2.7 Ω, high-power 1206 | Set antenna damping/Q; remove both temporarily to measure the isolated coil |
| R25 / R26 | 2.2 kΩ | Receiver attenuation; remove for isolated passive-network measurement, tune later if needed |
| C28 / C29 | 1 nF | Receiver AC coupling; normally keep these values |
| R41 / R42 | 0 Ω | Transmitter isolation; remove both for passive-network measurement, refit before powered operation |
| R29 | 0 Ω, 0603 | TX-LDO supply input link; optional location for temporary supply-current sensing |

The per-branch path is:

```text
TX -- R41/R42 -- L2/L3 -- EMC node -- C1 -- match node -- Rq -- coil end
                            |                  |
                            C0                 C2
                            |                  |
                           GND                GND

Separate receive branch: EMC node -- Rrx -- Crx -- RX
```

On the positive branch, C1 = C32 + C34, C2 = C36 + C38, C0 = C30 + C53. On the negative branch,
C1 = C33 + C35, C2 = C37 + C39, C0 = C31 + C54. There is no coil center tap.
Retain the saved RXP/RXN branch association when restoring the components.

Use 0805 C0G/NP0 capacitors rated 100 V, preferably 1–2% for the main matching
values. Keep the existing high-power damping-resistor specification; an arbitrary
quarter-watt 1206 is not equivalent. Sensible tuning stock consists of paired
56, 62, 68, 75, 82, 100, and 120 pF parts, and paired 0.5, 1, 2.2, 3.3, 4.7,
6.8, 10, 15, 22, and 33 pF trims. Tight absolute tolerances matter at sub-pF
values. Have high-power 1.8, 2.2, 2.7, and 3.3 Ω resistor pairs available;
order intermediate values if the measurement calls for them.

Parallel trims can only increase capacitance. To get 65 pF from an existing
68 pF position, replace the base, for example with 62 pF plus a small trim.
Do not solder a potentiometer, long flying leads, or a leaded variable capacitor
into this matching network. Do not change C26/C27, the crystal load capacitors,
as an antenna-tuning adjustment.

**Board states and exact measurement pads**

| Measurement | Board electrical state | Components to remove | Connection |
|---|---|---|---|
| Isolated coil impedance | Entire board unpowered, external RF absent | R27 and R28 | A1 pads 1 and 2, equivalently R27 pad 2 and R28 pad 2 |
| Complete passive matching impedance | Entire board unpowered, external RF absent | R41, R42, R25, R26; R27/R28 fitted | R41 pad 2 (`RF_DRV_P`) and R42 pad 2 (`RF_DRV_N`) |
| Powered RF/current/AGC checks | Controlled supply; explicit diagnostic firmware state | Remove all VNA connections, restore every RF link | Pickup loop; TVDD and supply measurement points as appropriate |
| Phone/card-emulation tests | Board powered and configured as an ISO-DEP listener | RF links fitted, VNA absent | Phone generates RF; scope pickup and firmware logs observe transactions |

For passive measurements disconnect USB, battery, programmer, debug cable,
scope, and bench supply. VEN low is not equivalent to this isolation procedure.
Keep the intended display, battery, enclosure, ferrite, and metalwork physically
in their normal places where possible, but disconnect power. Their geometry
changes the antenna. The four-layer populated board is the relevant specimen;
the bare two-layer coupon is only a useful earlier comparison.

No transmitting phone or reader may be near the antenna while the VNA is
attached, even if the board itself has no power. The antenna can couple external
RF into the VNA input.

For the full network, choose one of these measurement arrangements:

* **Practical one-port arrangement:** connect the S11 center conductor to R41
  pad 2 and its shield return to R42 pad 2. Keep PCB GND entirely disconnected
  from instrument ground/earth; retain the board's internal ground connections
  and all shunt capacitors. This treats the isolated, approximately symmetric
  network as a floating two-terminal load, following NXP's two-wire fixture
  approach. Unintended capacitance from the board/metalwork to earth can disturb
  the result, so keep cable and fixture position repeatable and check stability.
* **Balanced fixture:** use a characterized RF transformer/balun fixture suitable
  for 13.56 MHz and calibrate at its DUT terminals. Its impedance transformation
  must be known. A nominal transformer ratio alone is not a calibration.
* **Full two-port arrangement:** both cable shields go to PCB RF ground; each
  center conductor goes to one of the two network input pads. Acquire all four
  calibrated S-parameters and convert to differential impedance. For equal
  50 Ω ports and negligible mode conversion, `Sdd11 = (S11-S12-S21+S22)/2` and
  `Zdiff = 100*(1+Sdd11)/(1-Sdd11)`. Significant mode conversion needs a fuller
  mixed-mode treatment with the intended common-mode termination.

The first arrangement is conditional on keeping the assembly floating. Do not
connect its shield to both R42 pad 2 and PCB GND: that grounds one RF input and
measures a different circuit. If your enclosure must be earthed or measurements
change substantially when the cable moves, use the balanced/full two-port
method. These are passive VNA arrangements, not permission to ground a driven
antenna terminal during powered scope tests.

**Step-by-step procedure**

1. **Establish the mechanics and prepare one development board.** Choose the
   actual display, battery position, enclosure, and any ferrite before final
   tuning. Keep the antenna away from an unintended metal workbench or conductive
   mat using a nonmetallic fixture. Start without a phone/tag nearby. Photograph
   the board, record fitted values, and inspect for bridges between coil turns.
   A1 should show low DC resistance, not an open circuit: it is a continuous
   winding. Subtract meter lead resistance; the old bare-coupon estimate of
   roughly 0.6 Ω is only a sanity check, not the RF resistance specification.

2. **Make digital bring-up reproducible before powered RF tests.** Confirm the
   supply rails, PN7160 reset/IRQ operation, I²C communication, and firmware
   version. The current board uses SDA GPIO4, SCL GPIO5, IRQ GPIO6, VEN GPIO7.
   A fresh export still shows **R23/R24 = 100 kΩ**. The
   [existing wiring audit](nfc-wiring-audit.md) found these insufficient to
   guarantee low address bits against the internal pull-ups. For fixed address
   0x28, fit 0 Ω at both positions; 10 kΩ pull-downs are another documented
   option. This is a bring-up correction, not an RF matching adjustment.
   The project contains no firmware, so a diagnostic host application is needed.
   This step can run in parallel with preparing the passive measurement setup.

3. **Make and calibrate a short VNA fixture.** Set a 5–25 MHz sweep, approximately
   801 points, with a marker exactly at 13.56 MHz. Display R+jX or magnitude and
   phase, not just return loss. If the VNA only supports a small number of points,
   use a narrower sweep or segmented PC acquisition. Calibrate open, short, and
   50 Ω load at the ends of the fixture that will contact the board. Include the
   cable and connector in that calibration. NXP's homemade calibration method
   uses a short two-pin fixture and an SMD resistor load. Check a separate known
   resistor near 20 Ω afterward: it should read close to its resistance with
   little reactance. Recalibrate when the fixture or relevant sweep setup changes.
   See [AN12810, sections 2.1 and 2.3](https://www.nxp.com/docs/en/application-note/AN12810.pdf).

4. **Measure the isolated coil.** Remove R27/R28, disconnect all power and
   instruments except the VNA fixture, and connect at their coil-side pads.
   Measure in the intended mechanical assembly. Save S11 and impedance versus
   frequency. At 13.56 MHz write down `Zcoil = R + jX`. For an inductive coil,
   the apparent series inductance is `Lapp = X/(2*pi*f)` and `Qcoil = X/R`.
   Extracting a small resistance alongside a large reactance is sensitive to
   fixture and calibration error; repeat the setup before trusting a very
   precise Q or damping result.
   NXP recommends bare-coil self-resonance above 25 MHz; extend and recalibrate
   the sweep to investigate it if your fixture allows. The bare coil itself is
   not supposed to self-resonate at 13.56 MHz. See
   [AN13219, sections 2.1.4 and 4.1.2](../parts%20documentation/AN13219-rev1.6.pdf).

5. **Turn the measurement into a model and choose damping.** For a first
   calculation at the carrier, use the measured apparent series R and L and
   explicitly set `Ca = 0` in this project's calculator. This is a local
   single-frequency approximation. For useful wider-band prediction, fit the
   model `(Ra + j*w*La) || 1/(j*w*Ca)` to a sweep. One complex measurement cannot
   determine all three parameters. Do not put an apparent inductance that
   already includes self-capacitance into the calculator and then add that
   capacitance again.

   Begin with a damped antenna-branch Q near 20; values around 15–20 are NXP's
   usual starting range. The two equal series damping resistors satisfy, at
   the carrier, `Rq_each = max(0, (X/Qtarget - R)/2)`. For an illustrative
   `Lapp = 1.62 uH`, `R = 1.80 ohm`, `X` is about 138.02 Ω and each resistor
   works out to 2.55 Ω. These are invented example measurements, not this
   board's results. If the isolated coil already has Q below the target,
   additional damping cannot improve it; investigate metal, loss, and geometry.
   This branch Q is not the loaded Q of the whole EMC/matching network.

6. **Calculate C1 and C2 for the existing network.** Start with the project's
   conservative **20 + j0 Ω differential** target at 13.56 MHz, its 150 nH
   inductors, and 363 pF per-branch EMC capacitance. The EMC LC frequency is
   about 21.57 MHz. This follows NXP's high-cutoff, asymmetric-frequency-response
   approach. Both physical branches still use equal component values: the word
   "asymmetric" refers to the frequency response, not unequal capacitors.

   NXP's typical higher-output target for TVDD ≤3.3 V is 13 Ω; the repository's
   20 Ω at that voltage deliberately sacrifices output for current margin.
   Start with 20 Ω, then consider a lower target only if measured card-mode
   performance needs it and current/thermal checks permit. The 20 Ω choice is
   not a uniquely optimal card-emulation match. Keep reader-mode DPC and
   card-mode DLMA conceptually separate. Do not lower the EMC cutoff toward
   NXP's roughly 14.6 MHz symmetric-response design without its associated
   DPC/tuning work. See
   [AN13219, sections 4.1.3.2–4.1.3.8](../parts%20documentation/AN13219-rev1.6.pdf).

   Use the existing Python calculator or NXP's PN7160 matching calculator.
   AN13219 references an Excel attachment, but the local PDF has no embedded
   spreadsheet; obtaining it may require NXP's design resources. The project
   calculator is already available. With its dependencies installed, this
   illustrative command preserves the repository's baseline output:

   ```sh
   python3 tools/nfc/calculate.py \
     --la-uh 1.62 --ra-ohm 1.80 --ca-pf 0 \
     --target-ohm 20 --out /tmp/nucula-nfc-measured
   ```

   Dependencies are in `tools/nfc/requirements.txt`; use a Python virtual
   environment. For those example inputs the continuous solution is approximately
   C1 = 65.96 pF, C2 = 100.17 pF, Rq = 2.55 Ω **per branch**. It includes the
   calculator's assumed receiver loading. The physical passive test removes
   that loading; use `network(..., rx=False)` for the corresponding simulation.
   The calculator's `exact_solve` is the new solution, while its `assembly`
   field continues to evaluate the original 68 pF / 100 pF / 2.7 Ω build.
   Running it does not change the schematic or assemble the calculated values.

   The existing, unmeasured repository coil model instead produces approximately
   66.45 pF / 102.28 pF / 2.61 Ω. Its fitted BOM rounds to 68 pF / 100 pF /
   2.7 Ω and predicts about 18.80 − j0.24 Ω with RX isolated. Do not regard
   agreement with that prediction as a physical pass criterion.

7. **Fit parts and measure the entire passive network.** Restore the selected
   R27/R28 damping resistors. Remove R41/R42 and R25/R26 and attach the fixture
   at R41 pad 2 and R42 pad 2. Keep all power disconnected. Record the sweep
   and 13.56 MHz impedance. Tune toward the chosen resistance with reactance
   near zero. Do not tune for minimum 50 Ω SWR: 20 Ω is intentionally a mismatch
   to a 50 Ω instrument. An ideal 20 Ω resistance gives S11 magnitude 0.429,
   return loss 7.36 dB, and SWR 2.5 on a 50 Ω display.

8. **Fine-tune in equal pairs and keep a log.** C1 is the main resistance/
   impedance-level adjustment; compensate the resulting reactance with C2.
   Both interact. Try about 1–2.2 pF per branch initially, record the direction
   of movement, and reduce the step near the target. Replace base parts when
   capacitance must decrease. Keep C0/L0 unchanged initially; changing the EMC
   stage changes the whole response and detuning behavior. If Q/ringing needs
   adjustment, change R27/R28 and then recalculate/retune C1/C2.
   Power must be absent for each rework; let the board cool, clean flux, and
   dry it before measuring. Avoid adding long stubs or stacks of components.
   As a provisional bench stopping window, approximately 18–22 Ω and
   |X| ≤2 Ω is reasonable around a 20 Ω target, provided the sweep is stable;
   this is an engineering starting window, not an NXP compliance specification.
   Recheck across several boards and environmental cases later.

9. **Remove the VNA and restore the board before powering it.** Refit R41/R42
   and R25/R26. Remove measurement pigtails. Inspect the rework and establish
   a controlled supply. Start with TVDD around 2.7–3.3 V and verify the actual
   RF-state voltage at C23/C24 (`NFC_TVDD`), not just its software setting.
   VDD(UP), accessible at R29 pad 2/C19/C20, is supplied from VSYS; it is not
   a guaranteed 5 V RF rail. The datasheet specifies selecting TVDD below
   VDD(UP) −0.3 V for proper regulation. Battery operation may require a lower
   setting. A 5 V firmware preset does not create a 5 V supply. See
   [datasheet section 11.4.3](https://www.nxp.com/docs/en/data-sheet/PN7160_PN7161.pdf).

10. **Use a deliberate RF diagnostic mode.** Even for a card-emulation product,
    a temporary reader-mode continuous carrier gives a repeatable initial RF,
    current, and receiver check. A normal polling loop repeatedly turns RF on
    and off; pure card/listen mode normally waits for an external field. No
    continuous carrier in listen mode is therefore expected.
    [UM11495 section 12](https://www.nxp.com/docs/en/user-manual/UM11495.pdf)
    specifies reset/init, test, and reset/init sequencing. Its
    `TEST_ANTENNA_CMD` test ID `0x20` controls the RF field and requires Standby
    disabled first. Test ID `0x01` measures TX-LDO current; ID `0x02` measures
    AGC. PRBS is a separate modulation test and needs hardware reset through
    VEN to stop. The old separate `TEST_RF_FIELD_CMD` has been replaced.
    Do not run diagnostic carrier generation while a phone is interrogating
    the board as a card.

11. **Check current, temperature, and waveform behavior.** Use the internal
    TX-LDO-current diagnostic and check the transmitter supply independently.
    R29 is an accessible supply-sense location: a temporary low-inductance
    0.1 Ω resistor gives 25 mV at 250 mA. Use short connections, keep downstream
    decoupling fitted, and account for measurement burden and bandwidth. This
    is TX-LDO input current, including regulator overhead. The whole board's
    USB current includes MCU/display/charging and cannot substitute for it.
    A DMM reading of burst-mode average current can hide a high active current;
    local capacitors also mask fast current changes at this sensing point.
    Use RF-on diagnostic readings and appropriate time-resolved measurements
    for the active intervals.

    The transmitter's maximum continuous current is **250 mA**. Its roughly
    300 mA current limiter is above the permitted operating current; it is not
    the tuning target. Keep margin below 250 mA and stop if limiting, substantial
    TVDD droop, or abnormal heating appears. Check L2/L3 and R27/R28 temperatures,
    and use a properly rated probe for component voltage stress. Compare the
    pickup waveform before and after direct probing to detect probe detuning.
    See [datasheet sections 5 and 11.4.3](https://www.nxp.com/docs/en/data-sheet/PN7160_PN7161.pdf)
    and [AN13892 section 6](https://www.nxp.com/docs/en/application-note/AN13892.pdf).

12. **Set the receiver attenuation with a defined test condition.** Keep
    C28/C29 = 1 nF and start with R25/R26 = 2.2 kΩ, appropriate for the existing
    EMC taps. In the steady diagnostic RF condition, AN13219's command
    `2F 3D 04 02 C8 60 03` reads AGC. After checking response status and length,
    the result is little-endian: low byte + 256 × high byte. The recommended
    diagnostic range is 500–800 decimal. Increase both RX resistors if above
    800; decrease both if below 500, then repeat.

    This is a baseline receiver adjustment, not a requirement to maintain the
    same AGC at all phone distances. External-field AGC changes with coupling;
    card-mode operation must be tested at strong and weak fields. Do not chase
    a fixed number by moving the phone and resoldering repeatedly. Avoid using
    the older AN13219 rev. 1.5 voltage illustration as a universal RX amplitude
    target: rev. 1.6 revised that section to the AGC workflow. The datasheet also
    gives a typical RX input capacitance of 6 pF, making a conventional probe a
    material load on the receiver. See
    [AN13219 rev. 1.6, section 6](../parts%20documentation/AN13219-rev1.6.pdf) and
    [datasheet section 15.3.7](https://www.nxp.com/docs/en/data-sheet/PN7160_PN7161.pdf).

13. **Prove a real command/response exchange.** Reset out of test mode and
    configure NFC-A ISO-DEP listener/card emulation with host routing to the
    ESP32. Start with a known working NDEF Type 4 example or a deterministic
    application SELECT/command/reply sequence. Log field detection, activation,
    received APDUs, sent responses, status, and timeouts. Distinguish a missing
    RF activation from an application command that arrives but is not answered.
    Keep the OLED/Wi-Fi workload quiet first, then add the intended concurrent
    activity. For active card emulation the board must have its own power;
    the phone's field is not a power supply for the whole ESP32 board.

14. **Optimize card-mode ALM using controlled trials.** NXP's procedure selects
    a load-modulation mode, adjusts the ALM phase, and then adjusts amplitude/
    conductance. Freeze dynamic behavior during this characterization; DLMA
    can otherwise change several effective drive settings as coupling changes.
    The relevant parameters are `CLIF_TX_CONTROL_REG`,
    `CLOCK_CONFIG_DLL_ALM` (configuration tag `0xA03A`), and
    `CLIF_ANA_TX_AMPLITUDE_REG`. Use the documented NCI configuration format,
    apply changes in the required state, preserve reserved bits, and record
    the complete configuration and firmware version.

    NXP defines phase values over 0–355° in 5° steps. With phone-only equipment,
    an engineering screening approach is a coarse 15–30° sweep, followed by
    5° steps near a promising region. At each setting use identical positions,
    transaction counts, and firmware behavior. Select a broad reliable region
    across several phones, including near-contact operation, rather than the
    greatest range on one phone. Revisit phase if the hardware match changes.
    This empirical screening does not measure standardized load-modulation
    amplitude. NXP's full phase/amplitude procedure uses a calibrated test bench.
    [AN13218, sections 4–5](https://www.nxp.com/docs/en/application-note/AN13218.pdf).

    In particular, **a card that works farther away but fails against the phone
    may be replying too strongly**. NXP documents default DLMA tuning intended
    for its evaluation antenna and recommends trying **DLMA disabled with ALM
    Mode 1** for this symptom on custom hardware. Mode 1 uses one transmitter;
    do not assume Mode 3 or maximum output is best. Keep the TX-LDO voltage
    limits compatible with your supply when using DLMA. This diagnostic is
    described in [AN13892, section 11, pp. 22–23](https://www.nxp.com/docs/en/application-note/AN13892.pdf).

    If a fixed ALM configuration gives the required operating range, DLMA need
    not automatically become another tuning project. If dynamic optimization
    is needed, use calibrated external field strengths, characterize received
    level and reply amplitude, and derive this antenna's DLMA scaling/gain
    parameters with [AN13223](https://www.nxp.com/docs/en/application-note/AN13223.pdf).
    A phone and an uncalibrated pickup loop cannot supply that absolute field
    calibration. DPC is the separate reader-mode power-control feature.

15. **Validate the complete product and record the final configuration.** Test
    multiple phones, near contact and increasing gaps, lateral offsets, both
    relevant orientations, and phone cases. A simple starting matrix uses
    0/5/10/20/30 mm gaps where the geometry permits, then locates the actual
    failure boundary. Test repeated short exchanges and the longest intended
    transfer, with supply extremes, USB/battery operation, enclosure, display,
    Wi-Fi, and charging states. A criterion such as 100/100 repeated successful
    transactions in each required operating position is a useful project
    acceptance test, not a substitute for a standards test.

    Check several assembled boards. Save final C/R values, part numbers,
    passive sweeps, fixture calibration details, supply/current/temperature
    results, firmware RF configuration, and transaction logs. Change the
    schematic/BOM only after choosing a measured result. Production normally
    uses fixed components and RF settings, with sample characterization and
    an appropriate production functional/self-test; it does not require hand
    tuning every unit. If certification or robust quantified margins are
    required, use an NFC Forum/ISO analog test bench to measure listener
    sensitivity, load-modulation amplitude, and timing over the required fields.
    A phone success test and a pickup-loop waveform cannot prove those margins.

**Where tuning stops being the right remedy**

| Observation | Next check |
|---|---|
| No I²C response | Supplies, address straps, VEN, IRQ polarity, host mapping, clock configuration |
| VNA trace changes greatly with cable or hand position | Fixture calibration, common-mode/earth coupling, unintended nearby conductors |
| Good impedance but poor phone detection | Listener configuration, receiver level, antenna environment, field-detection path |
| Activation occurs and APDUs arrive, but transfer stops | Host response/timeout handling first; then RF quality under long transfers |
| Works at a gap but fails very close | Excess ALM/default DLMA mismatch, supply behavior, strong-field behavior |
| Narrow range or excessive ringing | Damping/Q and EMC response, followed by matching and phase recheck |
| Adding ferrite or moving the display changes everything | Repeat installed-coil measurement and matching; these are antenna changes |
| Stable carrier but no board-originated signal in listen mode | Expected until a reader field and a response transaction are present |

Capacitors can compensate reactance and transform impedance; they cannot
recover magnetic coupling lost behind poorly placed metal or remove dissipative
losses in a loaded coil. The populated island inside A1 and any nearby battery or
display make measurements of the final assembly particularly important.

**Source map and revision notes**

| Source | Revision inspected | Most useful parts |
|---|---|---|
| [PN7160/PN7161 datasheet](https://www.nxp.com/docs/en/data-sheet/PN7160_PN7161.pdf) | 4.2, 22 July 2026; local copy in `parts documentation` | Firmware support; §11.4.3 supplies/current; §15.3.7 receiver limits |
| [AN13219 antenna design and matching](https://www.nxp.com/docs/en/application-note/AN13219.pdf) | 1.6, 25 June 2026; local copy inspected | §4 calculation/measurement; §5 fine tuning; §6 AGC; §7 shared RM/CM matching; §10 verification |
| [AN12988 hardware design](https://www.nxp.com/docs/en/application-note/AN12988.pdf) | 1.6, 7 May 2025; local copy inspected | Power, clocks, I²C interface, and layout |
| [AN12810 NanoVNA method](https://www.nxp.com/docs/en/application-note/AN12810.pdf) | 1.0, 21 April 2020 | Practical fixture, calibration, sweep and impedance display |
| [AN13218 RF settings](https://www.nxp.com/docs/en/application-note/AN13218.pdf) | 1.4, 31 July 2024 | §4 configuration procedure; §5 card ALM phase/amplitude; protected register fields |
| [AN13892 PN7160 FAQ](https://www.nxp.com/docs/en/application-note/AN13892.pdf) | 1.2, 6 September 2024 | §6 current measurement; §11 close-range card-emulation failures |
| [AN13223 DLMA](https://www.nxp.com/docs/en/application-note/AN13223.pdf) | 1.1, 13 September 2021 | External field / receive level / TX gain characterization |
| [AN13861 card emulation](https://www.nxp.com/docs/en/application-note/AN13861.pdf) | 1.0, 26 April 2023 | Host and internal NDEF architectures and ISO-DEP setup |
| [UM11495 PN7160 user manual](https://www.nxp.com/docs/en/user-manual/UM11495.pdf) | 1.8, 2 June 2025 | §12 test sessions, RF on/off, TX-LDO current, AGC, PRBS |

Public search snippets can still display older AN13219 revisions. The receiver
instructions above follow the actual local rev. 1.6 PDF. The PN7160 product
page also carries a newer qualification warning than some older application-note
introductions: do not infer EMVCo 3.x payment compliance merely from the guides'
use of EMV test equipment. For this phone data-transfer project, focus on the
intended NFC-A/ISO-DEP behavior and the relevant NFC Forum/ISO measurements.
[Current PN7160 product information](https://www.nxp.com/products/PN7160).
