# Public repository and validation

This repository publishes the Nucula v2 hardware as `nucula-board`. It starts
with a clean public history. Private development commits and workstation
configuration are not required to open or validate the design.

## Validation

Use KiCad 10 with the standard libraries and Python 3:

```sh
python3 tools/check_schematic.py
python3 tools/check_component_choices.py
python3 tools/check_assembly_readiness.py
python3 tools/check_usb_clearance.py
python3 tools/check_top_contact_update.py
```

`KICAD_CLI` and `KICAD_SHARE` override the CLI and standard library locations.
The PCB layout and manufacturing exporter use KiCad's `pcbnew` Python module;
run them with KiCad's bundled Python or an environment providing that module.
The independent Gerber audit requires `gerbonara==1.5.0`, `reportlab` and
`rsvg-convert`. Simulation dependencies are listed in
[the simulation guide](simulation/README.md) and
[NFC requirements](../tools/nfc/requirements.txt).

The USB and display-change regression tools read sanitized design snapshots
from `tools/baselines/`, so they work without private Git commits. The filenames
identify the original development revisions, not reachable public commits.
Only their required design/report inputs are retained. Local paths and the
restricted PN7160 visualization model were removed consistently from both
the baselines and current design. The older `check_oled24_update.py` describes
the earlier 26-to-24-contact transition; use `check_top_contact_update.py` for
the current top-contact connector.

## Manufacturing archive

Only the corrected r2 release is published. The public repack preserves all
Gerber, drill, BOM and CPL bytes. It removes editor state, local paths and the
restricted optional 3D model, refreshes the source snapshot and validation
records, and recalculates the manifest and archive checksums. `source_commit`
records the original development baseline; the snapshot's file hashes identify
the published inputs independently of that private commit.

The design still needs the physical qualification and supplier review described
in [the manufacturing instructions](manufacturing-release.md). Successful
software checks do not establish electrical, RF or manufacturing qualification.

## Publication hygiene

Workstation configuration, editor state, backups, virtual environments and
credential files are ignored. Before publishing a new release, scan the proposed
Git history and recursively inspect all archive members and PDF metadata/text.
Run Gitleaks on both the Git history and the unpacked release contents. Check
that release manifests and `.sha256` files match the actual files. Git author
and committer identities should use the maintainer's GitHub no-reply address.
