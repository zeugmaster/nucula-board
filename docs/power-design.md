# USB-C, battery power and ESP32-C3 draft

Revision A-draft, updated 2026-09-20. Open `nucula-v2.kicad_pro` in KiCad 10.
The schematic is complete for this draft; the PCB remains the original blank board.
[PDF drawing](schematic.pdf), [BOM](bom.csv), [verification results](verification.json).

## Reference and scope

Adapted from Olimex **ESP32-C3-DevKit-Lipo revision C**, dated 2026-01-09,
from the local reference repository at commit
`5d93e79d46cf3b05782d9fe0f95a8a2e1ca6abbe`:
`HARDWARE/ESP32-C3-DevKit-Lipo_Rev_C/ESP32-C3-DevKit-Lipo_Rev_C.kicad_sch`.
[Upstream hardware repository](https://github.com/OLIMEX/ESP32-C3-DevKit-Lipo).

The retained circuit is TP4054 charging, Schottky/MOSFET USB-priority power
selection, and an SY8089 buck converter. The WROOM-02-N4 replaces the reference
board's MINI module. Its physical pin numbers were checked separately.
NFC, I/O expansion, connectors for future peripherals, firmware and PCB layout
are outside this draft.

## Power behavior

- USB: J1 VBUS → D1 → `USB_5V`. This supplies the charger and, through D2,
  `VSYS`. Q1 is off, separating the running system from charge-current sensing.
- Battery only: R5 pulls Q1's gate low. Q1 conducts from battery to `VSYS`.
  **Q1 drain is VBAT; source is VSYS.** Its body diode points from battery
  toward the system. D2 blocks current toward the USB supply branch.
- U2 converts `VSYS` to nominal 3.31 V. EN is tied to its input supply.
  The present rail target is 500 mA, conditional on input power and thermal/layout
  verification; the IC's advertised 2 A rating is not a rating for this board.
- USB can run the circuit without a battery. Battery-only operation is supported.
  Hot-plug/load-step performance still requires measurements on a laid-out board.

Battery target: **approximately 400 mAh, protected single-cell Li-ion/LiPo,
3.7 V nominal / 4.2 V full**, with pack protection against overdischarge,
short circuit and overcurrent. J2 is **2-pin JST-PH, 2.0 mm pitch**,
vertical: **pin 1 positive, pin 2 ground**. Purchased packs do not have universal
connector polarity. The exact pack, polarity, charge limits and discharge-current
rating must be checked before assembly. There is no battery protection IC,
cell-temperature sensor, or physical off switch in this draft.

JST-PH is used on small packs such as the
[Adafruit 400 mAh pack](https://www.adafruit.com/product/3898) and
[SparkFun 400 mAh pack](https://www.sparkfun.com/lithium-ion-battery-400mah.html).
These establish the connector choice; no battery model has been selected yet.
Keep the existing **100 mA charge setting**, equivalent to **0.25C at 400 mAh**.
Adafruit's example permits up to 400 mA charging and recommends its 100 mA
charger setting. The final pack's own limits still apply.

U1 is the Top Power **TP4054-42-SOT235**, not the BL4054 symbol name carried by
the reference. R3 = 10 kΩ sets 100 mA nominal; the data sheet specifies
85–115 mA at its stated conditions. Termination is approximately 10 mA.
C1 and C2 provide input/battery bypassing. D3 indicates charging.
The charger has internal thermal regulation, which does not measure cell temperature.
[TP4054 Rev 2.1 datasheet](https://www.toppwr.com/uploadfile/file/20240913/66e3d01d4c944.pdf).

D1/D2 use SS14 in SMA. Their forward drop reduces charging headroom: a low USB
voltage or resistive cable can prevent reaching full charge. At a pessimistic
4.75 V input and 0.5 V D1 drop, only 4.25 V reaches U1, close to the battery's
4.242 V maximum float voltage and sleep threshold. Full-charge performance at
minimum VBUS is **not guaranteed**. Validate this corner or replace D1 with a
lower-loss input stage before a product release.
[SS14 datasheet](https://www.vishay.com/docs/88746/ss12.pdf),
[Q1 IRLML6402 pinout and ratings](https://www.infineon.com/assets/row/public/documents/24/49/infineon-irlml6402-datasheet-en.pdf).

## Regulator and low battery

R6/R7 are **220 kΩ / 48.7 kΩ, both 0.1%**. With the 0.6 V feedback reference,
`VOUT = 0.6 × (1 + 220 / 48.7) = 3.310 V`.
Static limits including reference tolerance and ±50 nA feedback current are
approximately 3.228–3.393 V. C3 = 22 pF is the feed-forward capacitor.
C5/C6 provide 44 µF nominal output capacitance; C9/C10 decouple the module.
[Silergy SY8089 application note, supplied by Olimex](https://www.olimex.com/Products/Components/IC/SY8009A/resources/SY8089AAAC.pdf).

L1 is Taiyo Yuden **LSXND3030QKT2R2MNG**, the renamed NRS3015T2R2MNGH used in
Rev C: 2.2 µH, 1.48 A rated current. A 500 mA load scenario with 5.5 V input,
−20% inductance and an assumed 0.8 MHz switching frequency gives about
0.962 A peak. The app note specifies 1 MHz typical, not a guaranteed minimum;
this estimate is not a worst-case guarantee. The 69.6 mΩ maximum DCR exceeds
Silergy's preferred 50 mΩ target; verify loss and temperature in layout.
[Manufacturer specifications and name change](https://ds.yuden.co.jp/TYCOMPAS/eu/detail?pn=LSXND3030QKT2R2MNG&u=M).

The buck cannot maintain 3.3 V over the entire battery discharge curve.
U5, **TLV803EA30DCKR**, monitors the rail and pulls ESP_EN low around 3.08 V.
Its minimum static falling threshold is 3.018 V; maximum release threshold,
including hysteresis, is about 3.189 V, below the calculated minimum regulated
rail. Reset release is delayed about 200 ms. Fast dips still require transient
verification; the supervisor has propagation/glitch delays and EN has capacitance.
It does not disconnect the cell, so a protected battery remains necessary.
The **DCK/SC70 pinout is 1 GND, 2 RESET, 3 VDD**.
[TI datasheet](https://www.ti.com/lit/ds/symlink/tlv803e.pdf).

## USB, boot and sensing

J1 has separate 5.1 kΩ CC pulldowns. Both D− contacts feed U4 channel 1,
then R12 = 22 Ω and **GPIO18 / module pin 13**. Both D+ contacts feed U4 channel 2,
then R13 = 22 Ω and **GPIO19 / module pin 14**. U4's pass-through pairs are
pins 1–6 and 3–4. C7/C8 are **DNP**, reserved for USB tuning.
Native USB provides Serial/JTAG and ROM download; there is no UART bridge.
[ST USBLC6-2 datasheet](https://www.st.com/resource/en/datasheet/usblc6-2.pdf),
[Espressif schematic guidance](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c3/schematic-checklist.html).

GPIO2/8/9 have pullups. Hold BOOT and tap RESET for download mode.
ESP_EN has the recommended 10 kΩ / 1 µF network plus the supervisor.
Unused module pins carry explicit no-connect markers for this stage.

GPIO0/ADC1 senses half the battery voltage through 470 kΩ / 470 kΩ and 100 nF.
The calculated maximum is 2.142 V; use calibrated 11/12 dB attenuation and
allow at least 120 ms after the sensed rail settles. High divider impedance and
ADC sampling/calibration need firmware validation. GPIO1 receives inverted
VBUS presence through Q2: LOW means USB present. This avoids a 5 V divider
injecting current into an unpowered GPIO. R18 discharges the VBUS detector.
Firmware must manage USB attachment when VBUS is absent; this is not implemented
by the schematic alone. See the
[ESP32-C3-WROOM-02 datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-c3-wroom-02_datasheet_en.pdf).

## Boundaries before PCB

This preserves Rev C's simple input arrangement. **It does not implement USB
input-current negotiation/limiting, charger suspend control, or controlled
charging of the input capacitors.** C1+C4 alone total 44 µF nominal behind the
diodes. Do not treat two CC resistors or a zero-error ERC as USB compliance.
A full 500 mA rail load plus charging can exceed a legacy USB 2.0 port's 500 mA
budget. For initial powered evaluation use an adequate 5 V source (1 A or more);
source current capability does not replace USB host enumeration, suspend or
inrush requirements. Product-level use with arbitrary hosts needs a power-budget
and input-management revision before layout.
[USB-IF specifications](https://www.usb.org/document-library/usb-20-specification).

Select actual MLCC ordering codes and verify capacitance under DC bias,
tolerance and temperature: C1/C2/C4 need at least 10 µF effective; C5+C6 should
exceed 22 µF effective. Check charger heat, Wi-Fi load steps, low-cell reset,
USB insertion/removal, charging termination and battery-only leakage. Verify
90 Ω USB routing, short ESD return paths, buck switching loops and feedback
routing, and the module antenna keepout when PCB work begins.

## Verification and libraries

`python3 tools/check_schematic.py` runs native KiCad ERC, exports the netlist,
checks critical pin groups independently of drawing coordinates, checks selected
values/tolerances and DNP flags, matches physical symbol pins to footprint pads,
resolves assigned models, and recalculates the static limits above.
The checked draft has **47 components and zero ERC errors/warnings**. Footprint
filter checking is enabled. The drawing was also rendered and visually inspected.
This is schematic verification, not circuit simulation or hardware validation.

`Nucula_Project` is registered with `${KIPRJMOD}` paths. It contains the exact N4
module, TP4054, SY8089 and TLV803 symbols, module footprint/STEP and the inductor
footprint. Standard components use KiCad's installed libraries/models.
L1 has **no assigned 3D model**: the stock footprint's referenced model is missing,
and the manufacturer's old/new part download links returned HTTP 404. The local
footprint omits that broken reference. All other assigned models resolve.
BOM passives remain specification-based rather than procurement-ready ordering
codes. Downloaded datasheets are under `parts documentation/`; ST's PDF link is
recorded above because its direct file download failed.
