# FIXLIST: CPython `versionadded` notes that do not match the interpreters (run 1)

MV2, Munim, Inc.; made with AI agents. CC BY 4.0. Checked 2026-11-01.

1. **`Doc/library/calendar.rst`, `.. data:: MONDAY` ... `SUNDAY`: `.. versionadded:: 3.12` is
   wrong.** The seven constants are in `calendar.__all__` and documented as data at v3.11.0
   (`Lib/calendar.py`: `(MONDAY, ..., SUNDAY) = range(7)`), and they exist in every interpreter
   probed (3.8.20 to 3.15.2). 3.12 made them members of the new `calendar.Day` enum (gh-103636).
   Suggested fix: replace the `versionadded` with `.. versionchanged:: 3.12` saying they are now
   `Day` members. No existing issue or PR found (searched 2026-11-01).

Every other flagged row was a backport, an inherited name, a platform/build difference or a
parser/probe artefact; see GRADING.md.
