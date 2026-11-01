# versionadded-runtime-audit

Do CPython's "Added in version X.Y" notes match the interpreters? This is a pre-registered
audit by MV2 of Munim, Inc., made with AI agents working in his name.

CPython's library docs mark new APIs with `.. versionadded:: X.Y`. These notes are written
by hand and nothing checks them. This audit reads every one in `Doc/library` on `main` and
finds the object each note is attached to. It then imports that object in CPython 3.7 to
3.15 to see whether it really first appears in release X.Y.

- `PREREG.md`: the question, prior art, rules and three predictions, fixed before any data
  was read.
- `audit.py`: finds each marker's object, classifies the probe results and grades P1 and P2.
- `probe.py`: runs inside each interpreter (3.7 syntax) and reports which names exist.
- `job.py`: the data run. It downloads the docs tarball, installs each interpreter with
  `uv python install`, probes one module per process and writes `summary.json`, `rows.csv`,
  `flagged.csv` and file hashes.
- `test_audit.py`: tests with hand-worked expected values.

Run it with `python -m unittest -v`, then `python job.py --data-dir DATA --out-dir OUT`. You
need network access and `uv`.

## Status

- 2026-10-31: pre-registered.
- 2026-11-01: run 1 graded (GRADING.md, results in `results/`). 574 of 609 testable bare
  markers (94.3%) match the interpreters. P1 (at least 95%) narrowly **failed**, P2 (more
  "earlier" than "later" mismatches, 30 to 5) held, and P3 (at least 5 real errors)
  **failed**: hand review of all 35 mismatches found one real error. `calendar.MONDAY` to
  `SUNDAY` are marked "Added in version 3.12" but were already public and documented in 3.11
  (FIXLIST.md). Most mismatches are security fixes shipped in older micro releases. uv had no
  3.7 build, so 3.8 and older markers are untested.

## Licence

Code Apache-2.0. Text and data CC BY 4.0. MV2, Munim, Inc., mv2@munimtech.com.
