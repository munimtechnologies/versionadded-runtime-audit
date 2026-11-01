# Grading: do CPython's `versionadded` notes match the interpreters? (run 1)

MV2, Munim, Inc. (mv2@munimtech.com). Graded 2026-11-01 against PREREG.md (filed 2026-10-31,
before any data was read). Made with AI agents working in MV2's name. Code Apache-2.0; text and
results CC BY 4.0.

## Data the run used

- python/cpython `main` at commit `aa4f541a9742fa1de1008d13cbf23b2eb3799e3a` (tarball SHA-256
  `365e96ba...24b64`, fetched 2026-11-01T06:59Z): 329 `Doc/library/*.rst` files, 2,511
  `versionadded` markers, 2,231 attached to an object or module, 2,140 names probed.
- Interpreters (python-build-standalone via uv 0.13.6, Linux x86-64): 3.8.20, 3.9.25, 3.10.22,
  3.11.18, 3.12.16, 3.13.18, 3.14.10, 3.15.2. **3.7 could not be installed** ("No download
  found"), so every 3.8 marker is untested, as are all older ones (1,333 rows untested).
- Rows and verdicts: `results/run1-summary.json`, `results/rows.csv`, `results/flagged.csv`.

## Verdicts

| | Prediction | Result | Verdict |
|---|---|---|---|
| P1 | at least 95% of tested primary rows are `ok` | 574 of 609 (94.3%) | **FAILED** (narrowly) |
| P2 | more `earlier` rows than `later` rows | 30 earlier, 5 later, 0 gap | **HELD** |
| P3 | hand review confirms at least 5 genuine doc errors | 1 marker (covering 7 names) | **FAILED** |

## Hand review of all 35 flagged rows

Each row was read in the rst source and checked against the CPython source at the release tags,
using the labels fixed in PREREG.md.

| Rows | Marker | Label | Evidence |
|---|---|---|---|
| 7 | calendar `MONDAY` ... `SUNDAY`, 3.12 | **doc error, too late** | see below |
| 1 | email.policy `Policy.verify_generated_headers`, 3.13 | backport | security fix shipped in 3.12 and older micro releases |
| 2 | enum `Flag.__iter__`, `Flag.__len__`, 3.11 | inherited | the class-level name resolves through the enum metaclass |
| 2 | ipaddress `IPv4Address.__format__`, `IPv6Address.__format__`, 3.9 | inherited | `object.__format__` |
| 1 | os.path `isdevdrive`, 3.12 (later) | platform | Windows-only in 3.12, so absent on Linux until 3.13 |
| 1 | os.path `ALLOW_MISSING`, 3.15 | backport | 2025 tarfile security fix, shipped in 3.9+ micro releases |
| 1 | os `pidfd_open`, 3.9 (later) | platform or build | Linux-only; missing from this 3.9 build |
| 1 | os `pidfd_open`, 3.12 | parser artefact | the 3.12 marker belongs to the nested `PIDFD_NONBLOCK` entry |
| 1 | profiling.tracing / `cProfile`, 3.15 | parser artefact | the marker is for the new `profiling.tracing` module; `cProfile` is its old-name alias |
| 1 | signal `pidfd_send_signal`, 3.9 (later) | platform or build | as `pidfd_open` |
| 2 | socket `CAN_RAW_JOIN_FILTERS`, `CAN_J1939`, 3.9 (later) | platform or build | kernel-header constants missing from this 3.9 build |
| 1 | ssl `OP_IGNORE_UNEXPECTED_EOF`, 3.10 | backport | absent from `Modules/_ssl.c` at v3.9.0, present in 3.9.25 and 3.8.20 |
| 4 | subprocess `Popen`, 3.9 | parser artefact | markers for new parameters (group, extra_groups, user, umask) inside the class entry |
| 2 | sys `get_int_max_str_digits`, `set_int_max_str_digits`, 3.11 | backport | 2022 integer-string security fix, shipped in older micro releases |
| 1 | tarfile `LinkFallbackError`, 3.15 | backport | 2025 security fix |
| 2 | tarfile `TarFile.extraction_filter`, `TarInfo.replace`, 3.12 | backport | PEP 706, shipped in older micro releases |
| 1 | typing `TypeAliasType.__qualname__`, 3.15 | inherited | the class itself has `type.__qualname__`; aliases gained their own in 3.15 |
| 1 | typing `TypeAliasType`, 3.14 | parser artefact | the 3.14 marker closes the "Unpacking" rubric inside the class (the class has its own 3.12 marker) |
| 1 | datetime `time.strptime`, 3.14 | probe artefact | the probe's top-level fallback found the `time` module's `strptime` |
| 2 | xml.etree `XMLParser.flush`, `XMLPullParser.flush`, 3.13 | backport | expat security fix, shipped in older micro releases |

Total: 35 rows; 1 genuine marker error (7 rows), 10 backport rows, 5 inherited, 5 platform or
build, 7 parser artefacts, 1 probe artefact.

How each label was checked: the calendar, ssl, datetime, typing, os `pidfd_open`, and
profiling.tracing rows were read first-hand in the rst or C source at the commit or tag. The
other backport labels (security fixes shipped in micro releases) and the `isdevdrive` and
`Popen` labels rest on CPython's release history and the probe pattern (present in the latest
3.(Y-1) micro, as a security backport would be). They were not re-read at the tag in this
run. None of them could change P3, because a backport is not a doc error under the rules.

## The confirmed error: calendar's weekday constants

`Doc/library/calendar.rst` documents `MONDAY` through `SUNDAY` ("Aliases for the days of the week,
where MONDAY is 0 and SUNDAY is 6") with `.. versionadded:: 3.12`, and docs.python.org/3 shows
"Added in version 3.12." But:

- `Lib/calendar.py` at v3.11.0 defines `(MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY,
  SUNDAY) = range(7)` and lists all seven in `__all__`; every probed interpreter back to 3.8 has
  them.
- `Doc/library/calendar.rst` at v3.11.0 already documents them as `.. data:: MONDAY` ...
  ("Aliases for day numbers, where MONDAY is 0 and SUNDAY is 6"), and `setfirstweekday` says
  "The values MONDAY, ... and SUNDAY are provided for convenience."
- At v3.12.0 the same entry gained `.. versionadded:: 3.12`. What 3.12 added was the `calendar.Day`
  enum (gh-103636), whose members the module re-exports under the old names; the entry does not
  say that the names themselves are older.

So a reader who supports Python 3.11 or older is told, wrongly, that `calendar.MONDAY` does not
exist there. A suggested fix is a `versionchanged:: 3.12` ("now members of the Day enum")
instead of the `versionadded`. Searches of python/cpython issues and PRs for calendar MONDAY
versionadded found only the original enum change (gh-103636, PR #103833), not this.

## What this means

The notes hold up well: of 609 testable bare markers, 574 match the interpreters, and of the 35
that do not, only one is a real documentation error. Most mismatches come from security fixes
shipped in older micro releases, which the `versionadded` rule cannot express. The prediction of
at least 5 errors failed. 3.8-and-older markers could not be tested, because uv had no 3.7 build.

## Limits

Linux builds only; class-level `getattr` cannot see instance attributes; `main` only.
