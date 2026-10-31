"""Report which documented names exist in the running interpreter.

Usage: python -I probe.py targets.json result.json
targets.json is a list of [module, qualname] pairs; qualname "" asks about the module.
Runs on every interpreter from 3.7 up, so it keeps to 3.7 syntax.

MV2, Munim, Inc. Apache-2.0. Made with AI agents.
"""
import importlib
import importlib.util
import json
import sys
import warnings

SKIP = {"antigravity", "this", "__main__", "turtledemo"}


class Missing(Exception):
    pass


def load(mod):
    if mod.split(".")[0] in SKIP:
        raise ImportError("skipped on purpose")
    try:
        return importlib.import_module(mod)
    except ModuleNotFoundError as e:
        if e.name and (mod == e.name or mod.startswith(e.name + ".")):
            raise Missing(mod)
        raise


def walk(obj, parts):
    for p in parts:
        try:
            obj = getattr(obj, p)
        except AttributeError:
            return "no"
    return "yes"


def probe(mod, qual):
    if not qual:
        try:
            return "yes" if importlib.util.find_spec(mod) is not None else "no_module"
        except Exception:  # parent package missing
            return "no_module"
    try:
        m = load(mod)
    except Missing:
        return "no_module"
    except BaseException:
        return "import_error"
    parts = qual.split(".")
    res = walk(m, parts)
    if res == "yes" or len(parts) < 2:
        return res
    # names written from the top level, e.g. "os.path.join" documented under os
    for i in range(len(parts) - 1, 0, -1):
        try:
            m2 = load(".".join(parts[:i]))
        except BaseException:
            continue
        if walk(m2, parts[i:]) == "yes":
            return "yes"
    return "no"


def main():
    warnings.simplefilter("ignore")
    with open(sys.argv[1], encoding="utf-8") as f:
        targets = json.load(f)
    out = {}
    for mod, qual in targets:
        try:
            out[mod + "|" + qual] = probe(mod, qual)
        except BaseException:
            out[mod + "|" + qual] = "error"
    v = sys.version_info
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump({"version": "%d.%d.%d" % (v[0], v[1], v[2]),
                   "releaselevel": v[3], "results": out}, f)


if __name__ == "__main__":
    main()
