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

Pre-registered. Results will be added under `results/` with a hand-checked `FIXLIST.md`.
Only the "doc error" cases defined in PREREG.md go on that list. A clean result ("the
notes hold up") will be published the same way.

## Licence

Code Apache-2.0. Text and data CC BY 4.0. MV2, Munim, Inc., mv2@munimtech.com.
