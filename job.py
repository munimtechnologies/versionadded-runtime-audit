"""Data run: scan CPython Doc/library on main, probe interpreters 3.7-3.15, grade PREREG.md.

MV2, Munim, Inc. Apache-2.0. Made with AI agents.
"""
import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audit  # noqa: E402

UA = {"User-Agent": "mv2-versionadded-audit/0.1 (Munim, Inc.; mv2@munimtech.com)"}
TARBALL = "https://codeload.github.com/python/cpython/tar.gz/refs/heads/main"
MINORS = list(range(7, 16))  # 3.7 .. 3.15; any uv cannot install is reported and skipped
UV_ENV = dict(os.environ, UV_PYTHON_PREFERENCE="only-managed",
              UV_PYTHON_INSTALL_DIR="/tmp/uv-python")


def get(url, tries=3):
    err = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except Exception as e:  # network hiccup: retry
            err = e
        time.sleep(5 * (k + 1))
    raise err


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def read_docs(path):
    """Doc/library/*.rst from the tarball, plus the commit id git archive records."""
    docs = {}
    with tarfile.open(path, "r:gz") as tf:
        for m in tf:
            parts = m.name.split("/", 1)
            if (len(parts) == 2 and m.isfile() and parts[1].startswith("Doc/library/")
                    and parts[1].endswith(".rst")):
                docs[parts[1]] = tf.extractfile(m).read()
        commit = tf.pax_headers.get("comment", "")
    return docs, commit


def interpreter(minor):
    v = "3.%d" % minor
    r = subprocess.run(["uv", "python", "install", v], env=UV_ENV,
                       capture_output=True, text=True, timeout=1200)
    if r.returncode != 0:
        return None, (r.stderr or r.stdout)[-400:]
    r = subprocess.run(["uv", "python", "find", v], env=UV_ENV,
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or not r.stdout.strip():
        return None, (r.stderr or r.stdout)[-400:]
    return r.stdout.strip().splitlines()[-1], ""


def probe_all(py, groups, tmp):
    """One fresh process per module, so one bad import cannot spoil the rest."""
    results, version = {}, None
    for i, (mod, targets) in enumerate(sorted(groups.items())):
        tin = os.path.join(tmp, "t%d.json" % i)
        tout = os.path.join(tmp, "r%d.json" % i)
        with open(tin, "w", encoding="utf-8") as f:
            json.dump(targets, f)
        try:
            subprocess.run([py, "-I", os.path.join(HERE, "probe.py"), tin, tout],
                           cwd=tmp, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=120)
            with open(tout, encoding="utf-8") as f:
                got = json.load(f)
            results.update(got["results"])
            version = version or [got["version"], got["releaselevel"]]
        except Exception:  # crash or hang: every name in this module is an error
            for m, q in targets:
                results[m + "|" + q] = "error"
        for p in (tin, tout):
            if os.path.exists(p):
                os.remove(p)
    return results, version


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    snap = os.path.join(a.out_dir, "snapshot")
    os.makedirs(snap, exist_ok=True)

    fetched_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    tar_path = os.path.join(a.data_dir, "cpython-main-%s.tar.gz" % fetched_at[:10])
    if not os.path.exists(tar_path):
        raw = get(TARBALL)
        with open(tar_path, "wb") as f:
            f.write(raw)
    with open(tar_path, "rb") as f:
        tar_sha = sha256(f.read())
    docs, commit = read_docs(tar_path)

    rows = []
    for name in sorted(docs):
        rows.extend(audit.scan(docs[name].decode("utf-8"), name))
    for r in rows:
        r["primary"] = audit.primary(r)
    targets = sorted({(r["module"], r["qual"]) for r in rows
                      if r["kind"] != "unattached" and r["module"]})
    groups = {}
    for m, q in targets:
        groups.setdefault(m.split(".")[0], []).append([m, q])

    uv_version = subprocess.run(["uv", "--version"], capture_output=True,
                                text=True).stdout.strip()
    status, interpreters = {}, {}
    with tempfile.TemporaryDirectory() as tmp:
        for minor in MINORS:
            py, err = interpreter(minor)
            if not py:
                interpreters["3.%d" % minor] = {"installed": False, "error": err}
                print("3.%d not installed: %s" % (minor, err.strip()[-200:]))
                continue
            res, ver = probe_all(py, groups, tmp)
            interpreters["3.%d" % minor] = {"installed": True, "version": ver}
            print("3.%d probed: %s, %d names" % (minor, ver, len(res)))
            for key, s in res.items():
                status.setdefault(key, {})[minor] = s

    for r in rows:
        if r["kind"] == "unattached" or not r["module"]:
            r["category"] = "unattached" if r["kind"] == "unattached" else "no_module_context"
            continue
        st = status.get(r["module"] + "|" + r["qual"], {})
        r["status"] = {"3.%d" % k: v for k, v in sorted(st.items())}
        if r["major"] == 3 and r["minor"] is not None:
            r["category"] = audit.classify(r["minor"], st)
        else:
            r["category"] = "other_version"

    res = audit.grade(rows)
    res["counts"] = {
        "rst_files": len(docs),
        "versionadded_rows": len(rows),
        "attached": sum(1 for r in rows if r["kind"] != "unattached"),
        "described": sum(1 for r in rows if r["described"]),
        "micro": sum(1 for r in rows if r["micro"]),
        "non_numeric": sum(1 for r in rows if r["major"] is None),
        "primary_before_probe": sum(1 for r in rows if r["primary"]),
        "names_probed": len(targets),
    }
    res["source"] = {
        "fetched_at": fetched_at,
        "tarball_url": TARBALL,
        "tarball_sha256": tar_sha,
        "cpython_commit": commit,
        "uv": uv_version,
        "interpreters": interpreters,
        "platform": sys.platform,
    }
    with open(os.path.join(snap, "doc_library_sha256.json"), "w", encoding="utf-8") as f:
        json.dump({k: sha256(v) for k, v in sorted(docs.items())}, f, indent=1)
    with open(os.path.join(a.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    with open(os.path.join(a.out_dir, "rows.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1)
    cols = ["file", "line", "kind", "module", "qual", "version", "described",
            "primary", "category"]
    flagged = [r for r in rows if r["primary"] and r["category"] in ("earlier", "later", "gap")]
    for fname, subset in (("rows.csv", rows), ("flagged.csv", flagged)):
        with open(os.path.join(a.out_dir, fname), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols + ["status"])
            for r in subset:
                st = r.get("status", {})
                w.writerow([r[c] for c in cols] + [";".join("%s=%s" % kv for kv in st.items())])
    for k in ("P1", "P2", "P3"):
        print(k, res[k])
    print("interpreters", json.dumps(interpreters))


if __name__ == "__main__":
    main()
