# Sanitized regression inputs

These ZIPs contain the design/report files used by the historical USB and OLED
regression checks. They preserve comparison geometry without publishing private
Git history. Filenames identify the original revision. Personal filesystem paths
and the restricted optional PN7160 3D-model reference have been removed; circuit
connections, pad geometry, placement and routing are preserved.

Read them through `historical_source.read_baseline`. The hardware license and
third-party attribution at the repository root apply to these inputs as well.

`rev-A-nfc.zip` pins the submitted rev-A board/schematic, manufacturing export
stackup and native copper-geometry extraction for the exact NFC freeze audit.
The source board SHA-256 is independently checked against the recorded release.
