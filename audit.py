"""Find every ``.. versionadded::`` in CPython's Doc/library, name the object it marks,
and grade the documented version against which interpreters actually have that object.

MV2, Munim, Inc. Apache-2.0. Made with AI agents.
"""
import re

OBJ_KINDS = ("function", "class", "method", "attribute", "data", "exception",
             "classmethod", "staticmethod", "property", "decorator",
             "decoratormethod", "coroutinefunction", "coroutinemethod",
             "abstractmethod")
CLASSLIKE = ("class", "exception")
DIRECTIVE = re.compile(r"^( *)\.\. (?:py:)?([a-z]+)::(.*)$")
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*")
VERSION = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?$")
RULE = re.compile(r"^([-=~^\"*+#])\1{3,}\s*$")
PRIMARY = ("ok", "earlier", "later", "gap")
P1_BAR = 0.95
P3_BAR = 5


def indent(line):
    return len(line) - len(line.lstrip(" "))


def first_name(sig):
    """Object name at the start of a signature: 'open' from 'open(file, mode="r")'."""
    m = NAME.match(sig.strip())
    return m.group(0).rstrip(".") if m else None


def qualify(name, parent):
    """Qualified name inside an enclosing class directive, if there is one."""
    if parent is None or parent["kind"] not in CLASSLIKE or not parent["qual"]:
        return name
    pq = parent["qual"]
    if name.split(".")[0] == pq.split(".")[-1]:  # written as Class.member already
        return pq.rsplit(".", 1)[0] + "." + name if "." in pq else name
    return pq + "." + name


def next_indent(lines, i):
    for line in lines[i + 1:]:
        if line.strip():
            return indent(line)
    return -1


def parse_version(tok):
    m = VERSION.match(tok)
    if not m:
        return None, None, None
    micro = int(m.group(3)) if m.group(3) else 0
    return int(m.group(1)), int(m.group(2)), micro


def scan(text, path=""):
    """One row per versionadded directive in an .rst file.

    kind is the marked object's directive (function, class, ...), "module" for a
    module-level marker placed before the file's first rule line or object, or
    "unattached" when the marker is not a direct child of an object directive.
    """
    rows = []
    lines = text.splitlines()
    module = "builtins"  # files without a module directive document builtins
    fresh = False        # after .. module::, before the first rule line or object
    stack = []           # open object directives, innermost last
    sig = None           # object directive whose signature lines are still open
    for i, line in enumerate(lines):
        if not line.strip():
            sig = None
            continue
        ind = indent(line)
        if sig is not None and ind > sig["indent"]:
            s = line.strip()
            if sig["cont"]:
                sig["cont"] = s.endswith("\\")
            elif not s.startswith(":"):
                n = first_name(s)
                if n:
                    sig["quals"].append(qualify(n, sig["parent"]))
                sig["cont"] = s.endswith("\\")
            continue
        sig = None
        while stack and stack[-1]["indent"] >= ind:
            stack.pop()
        if stack and stack[-1]["body"] is None:
            stack[-1]["body"] = ind
        if RULE.match(line):
            fresh = False
            continue
        m = DIRECTIVE.match(line)
        if not m:
            continue
        kind, arg = m.group(2), m.group(3).strip()
        if kind in ("module", "currentmodule"):
            module = None if arg == "None" else arg
            fresh = kind == "module"
        elif kind in OBJ_KINDS:
            fresh = False
            parent = stack[-1] if stack else None
            name = first_name(arg)
            qual = qualify(name, parent) if name else None
            entry = {"indent": ind, "kind": kind, "qual": qual,
                     "quals": [qual] if qual else [], "body": None,
                     "module": module, "parent": parent,
                     "cont": arg.endswith("\\")}
            stack.append(entry)
            sig = entry
        elif kind == "versionadded":
            tok = arg.split()
            major, minor, micro = parse_version(tok[0] if tok else "")
            base = {"file": path, "line": i + 1,
                    "version": tok[0] if tok else "",
                    "major": major, "minor": minor, "micro": micro,
                    "described": len(tok) > 1 or next_indent(lines, i) > ind}
            if stack and stack[-1]["body"] == ind:
                owner = stack[-1]
                for q in owner["quals"]:
                    rows.append(dict(base, kind=owner["kind"],
                                     module=owner["module"], qual=q))
            elif not stack and ind == 0 and fresh and module:
                rows.append(dict(base, kind="module", module=module, qual=""))
            else:
                rows.append(dict(base, kind="unattached", module=None, qual=None))
    return rows


def primary(row):
    """Is this row in the pre-registered test set (before probing)?"""
    return (row["kind"] != "unattached" and row["module"] is not None
            and not row["described"] and row["major"] == 3
            and row["minor"] is not None and row["micro"] == 0)


def classify(minor, st):
    """Category for a 'versionadded:: 3.<minor>' given probe statuses keyed by 3.x minor."""
    if minor not in st or (minor - 1) not in st:
        return "untested"
    norm = {k: ("no" if v == "no_module" else v) for k, v in st.items()}
    cur, prev = norm[minor], norm[minor - 1]
    if cur not in ("yes", "no") or prev not in ("yes", "no"):
        return "import_error"
    if not any(v == "yes" for v in norm.values()):
        return "never_found"
    if prev == "yes":
        return "earlier"
    if cur == "yes":
        return "ok"
    if any(v == "yes" for k, v in norm.items() if k > minor):
        return "later"
    return "gap"


def grade(rows):
    """Mechanical verdicts for P1 and P2; P3 needs the hand review."""
    prim = [r for r in rows if r.get("primary") and r.get("category") in PRIMARY]
    n = len(prim)
    ok = sum(1 for r in prim if r["category"] == "ok")
    early = sum(1 for r in prim if r["category"] == "earlier")
    late = sum(1 for r in prim if r["category"] == "later")
    gap = sum(1 for r in prim if r["category"] == "gap")
    share = ok / n if n else None
    cats, by_minor = {}, {}
    for r in rows:
        c = r.get("category", "not_probed")
        cats[c] = cats.get(c, 0) + 1
    for r in prim:
        d = by_minor.setdefault("3.%d" % r["minor"], {})
        d[r["category"]] = d.get(r["category"], 0) + 1
    return {
        "P1": {"n": n, "ok": ok, "share": share, "bar": P1_BAR,
               "verdict": "held" if share is not None and share >= P1_BAR else "failed"},
        "P2": {"earlier": early, "later": late, "gap": gap,
               "verdict": "held" if early > late else "failed"},
        "P3": {"bar": P3_BAR, "flagged": early + late + gap,
               "verdict": "pending hand review"},
        "categories_all_rows": cats,
        "primary_by_version": by_minor,
    }
