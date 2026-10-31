# Pre-registration: do CPython's `versionadded` notes match the interpreters?

MV2, Munim, Inc. Filed 2026-10-31, before any data was downloaded or any interpreter
was probed. Made with AI agents working in MV2's name. Text CC BY 4.0, code Apache-2.0.

## Question

CPython's library docs mark new APIs with `.. versionadded:: X.Y` ("Added in version
X.Y" on docs.python.org). People use these notes to decide what they can call on the
oldest Python they support. The notes are written by hand when a feature is merged.
Nothing checks them against the interpreters themselves.

This audit runs that check. For every `versionadded` that sits directly on an
object's entry (a function, class, method, attribute, data item or exception) or on a
module, it asks whether the object exists in the latest 3.(Y-1) release and in the
latest 3.Y release.

## Prior art (searched 2026-10-31)

- python/cpython issue #115664 (2024): a manual clean-up of directive *usage*
  (added vs changed, ordering, duplicates). It did not check the version numbers
  against the interpreters.
- python/cpython issue #81165 / bpo-36984 (2019): typing's `versionadded` notes were
  inaccurate for many attributes. That was fixed by hand for one module.
- One-off fixes such as PR #101728 (subprocess `versionchanged`) and PR #24329.
- Related tools that do something else: the `stdlibs` package lists module names
  per release; typeshed's stubtest checks the type stubs (not the docs) against the
  runtime; python/docsbuild-scripts `check_versions.py` checks the Sphinx build per
  branch.

I found no systematic comparison of the docs' `versionadded` versions with the
interpreters.

## Data (fixed now)

- CPython `main` as a tarball from codeload.github.com. All `Doc/library/*.rst`
  files are read, and the commit id and tarball SHA-256 are recorded.
- CPython 3.7 through 3.15 at the latest micro release that `uv python install`
  provides (python-build-standalone builds, Linux x86-64). The exact versions are
  recorded. Any version uv cannot install is reported and its rows are "untested".
- Each top-level module is probed in a fresh `python -I` process with
  `importlib.import_module` plus `getattr` along the dotted name. Modules use
  `importlib.util.find_spec`.

## Rules (fixed now; implemented in audit.py, tested in test_audit.py)

- **Attachment.** A `versionadded` is attached to an object when it is a direct child
  of that object's directive. "Direct child" means its indentation equals the
  directive's body indentation. A marker at column 0 after `.. module::` and before
  the file's first rule line (`----`, `====` and so on) or first object directive
  marks the module. Everything else is "unattached" and not tested. That includes
  markers inside notes, list-tables and sections.
- **Names.** A name inside a class directive is qualified by the class (`Widget.grow`).
  `Class.member` written out is not doubled. Files with no module directive document
  `builtins`. `.. currentmodule:: None` names are not tested.
- **Primary set.** Attached markers with no description text (a bare
  `.. versionadded:: 3.Y` on the object itself), a plain `3.Y` version (not `3.Y.Z`
  with Z > 0, not `next`), and a module context.
- **Categories.** Each primary row is classified from the probe results:
  - ok: absent in 3.(Y-1), present in 3.Y.
  - earlier: present in 3.(Y-1).
  - later: absent in 3.Y, present in a later release.
  - gap: absent in 3.(Y-1) and 3.Y, present only before them.
  - never_found: absent in every tested release (platform-only names, instance
    attributes, parser misses).
  - import_error: the module failed to import for a reason other than not existing.
  - untested: 3.(Y-1) or 3.Y was not installed.

  Only ok, earlier, later and gap count in the test.

## Predictions

- **P1.** At least 95% of tested primary rows are ok. My expectation is about 96%.
  I give it roughly a 55% chance to hold, because backports, inherited methods and
  names documented after they appeared all show up as "earlier".
- **P2.** There are more "earlier" rows than "later" rows. A feature that slips a
  release usually has its note updated when it is merged, while names that existed
  before they were documented are common. I give this about 85%.
- **P3.** Hand review confirms at least 5 genuine documentation errors (definition
  below). I give this about 60%. It is the least blind prediction, because the
  verdict comes from human judgement under the rules below rather than from code.

P1 and P2 are computed mechanically by audit.grade and reported as they come out.

## Hand review for P3 (fixed now)

Every earlier, later and gap row in the primary set is read. Each is given one label,
checked against the CPython source at the release tags (v3.(Y-1).0 and v3.Y.0) and
against What's New / the changelog:

- **doc error, too late.** The object existed with the same name and meaning in
  v3.(Y-1).0. It was public (no leading underscore, not inherited unchanged from a
  base class). Neither 3.Y's What's New nor the entry itself says it was made public
  or newly documented in 3.Y.
- **doc error, too early.** The object is absent from v3.Y.0 on every platform and
  first appears in a later .0 release.
- **backport.** It appeared in a 3.(Y-1) micro release (for example a security fix).
  The marker is right for the feature release.
- **inherited.** The name resolves through a base class that already had it.
- **made public or documented later on purpose** (stated in What's New or the docs).
- **platform or build.** Present or absent because of the build, not the release.
- **parser or probe artefact.**

Only the two "doc error" labels count toward P3 and go on FIXLIST.md, each with the
tag-source evidence. Before anything is sent upstream, python/cpython issues and PRs
are searched for the name so that nothing duplicates a fix already in flight.

## Limits

- The test uses the latest micro of each release, so names backported in micro
  releases look "earlier". The hand review separates those out.
- `getattr` cannot see instance attributes set in `__init__`. Those fall into
  never_found and are not tested.
- Only Linux builds are probed, so Windows-only and macOS-only names are not tested.
- The docs on main describe today's API. Names that were removed are no longer
  documented, so this audits what readers see now.
