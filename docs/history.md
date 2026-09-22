# Development history

The 17 original development commits were restored after the initial public
release used a single snapshot. Their original order, messages, author names,
author timestamps and committer timestamps are preserved. Both email fields use
the maintainer's GitHub no-reply identity. Historical personal paths, editor
state, workstation configuration and the restricted PN7160 3D model were removed;
nested archives and their checksums were sanitized as well.

Scrubbing changes Git object IDs. This map connects the original revision IDs
used by design reports, regression baselines and manufacturing manifests with
the corresponding public commits. The publication cleanup follows these commits
with its original September 22 timestamp; r2 changes that were uncommitted before
publication remain part of that cleanup rather than being assigned invented dates.

| Original author timestamp | Original revision | Public revision | Commit message |
|---|---|---|---|
| 2026-09-19T15:51:52+02:00 | `f0c1464` | [6b27609](https://github.com/zeugmaster/nucula-board/commit/6b276092c9259aabafe40b369c41f86b91687fc1) | Initialize KiCad project version control |
| 2026-09-19T16:26:53+02:00 | `213d2f3` | [4f9947c](https://github.com/zeugmaster/nucula-board/commit/4f9947c3936ad34a266f64537e2f12122101958f) | Draft ESP32-C3 USB-C and Li-ion power schematic |
| 2026-09-20T00:24:32+02:00 | `4abfd13` | [14cc2f2](https://github.com/zeugmaster/nucula-board/commit/14cc2f21f3a6a164a49174e989257ac59c567f0f) | Set 400 mAh battery target with JST-PH connector |
| 2026-09-20T01:17:07+02:00 | `b53ab0f` | [cfc0a15](https://github.com/zeugmaster/nucula-board/commit/cfc0a15dc0fa66233eac9acc17762b009c61673a) | Integrate NFC, OLED and breakaway I2C keyboard |
| 2026-09-20T16:59:40+02:00 | `162260c` | [ffa8072](https://github.com/zeugmaster/nucula-board/commit/ffa80729661c13fa6423cbea6232cedc2d707c32) | Add PCB NFC coil and refine prototype component selections |
| 2026-09-20T18:16:53+02:00 | `f72fe92` | [620e9a0](https://github.com/zeugmaster/nucula-board/commit/620e9a0b09c361a7e630645bee37224978bff467) | Keep keypad signals on center seven header pins |
| 2026-09-20T18:49:03+02:00 | `8878c5b` | [60bded4](https://github.com/zeugmaster/nucula-board/commit/60bded409d8906c1d8229b2f33225018ee2bb595) | Prepare components and JLCPCB BOM for 10-board assembly |
| 2026-09-20T23:36:58+02:00 | `6b7182d` | [eabce9f](https://github.com/zeugmaster/nucula-board/commit/eabce9fc502818d9e05a1bf46dd73501d06c9f8d) | Checkpoint preliminary four-layer PCB layout |
| 2026-09-21T00:15:50+02:00 | `210e3b8` | [a9ce620](https://github.com/zeugmaster/nucula-board/commit/a9ce620063e00828887cda2e7313f8e61e5c7d31) | Add inside-feed NFC antenna and ESP antenna notch |
| 2026-09-21T01:21:11+02:00 | `b88f7db` | [0506827](https://github.com/zeugmaster/nucula-board/commit/0506827419b707710ecff99728e8d59d94945ae5) | add break-away mouse bite line |
| 2026-09-21T01:28:15+02:00 | `f8a132d` | [21dbf25](https://github.com/zeugmaster/nucula-board/commit/21dbf25030c9c8159e9478dbf5f90c057cd02f10) | commit again after save |
| 2026-09-21T12:09:13+02:00 | `33dbf43` | [b2c0d92](https://github.com/zeugmaster/nucula-board/commit/b2c0d92daf5ada4d545dca2e925eabf4cfc48889) | Complete four-layer PCB placement and routing |
| 2026-09-21T17:24:24+02:00 | `aa6a3cd` | [d8d1cae](https://github.com/zeugmaster/nucula-board/commit/d8d1cae6b1a1729a299a26f4ac2cd00645b4f6d7) | add silkscreen label |
| 2026-09-21T17:24:43+02:00 | `600d88a` | [4402e20](https://github.com/zeugmaster/nucula-board/commit/4402e20b629fae3611d8a14672760c5120226085) | post save commit |
| 2026-09-21T18:35:52+02:00 | `96c8114` | [1fb2648](https://github.com/zeugmaster/nucula-board/commit/1fb2648f5917b3c9a2210a6645c2e7127f427d9f) | Correct OLED interface and routing for 24-pin display |
| 2026-09-21T19:30:21+02:00 | `d4eaaa9` | [cd4d2bd](https://github.com/zeugmaster/nucula-board/commit/cd4d2bd37eddcca779e9d887e21a10bd1d3ec863) | Use top-contact OLED connector and document manufacturing preparation |
| 2026-09-21T20:25:12+02:00 | `a67a5b6` | [cd4d45d](https://github.com/zeugmaster/nucula-board/commit/cd4d45d83b3ba04304c2bbd4614f6c99d1030e42) | Fix USB connector clearance and prepare JLCPCB manufacturing release |
