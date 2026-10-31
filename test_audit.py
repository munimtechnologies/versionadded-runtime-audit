"""Tests for audit.py and probe.py. Expected values were worked out by hand from the fixtures.

MV2, Munim, Inc. Apache-2.0. Made with AI agents.
"""
import unittest

import audit
import probe

DEMO = "\n".join([
    ":mod:`!demo` --- Demo",                      # 1
    "=====================",                      # 2
    "",                                           # 3
    ".. module:: demo",                           # 4
    "   :synopsis: Demo.",                        # 5
    "",                                           # 6
    ".. versionadded:: 3.9",                      # 7  module-level
    "",                                           # 8
    "--------------",                             # 9
    "",                                           # 10
    ".. versionadded:: 3.10",                     # 11 after the rule: unattached
    "",                                           # 12
    ".. class:: Widget(size)",                    # 13
    "",                                           # 14
    "   A widget.",                               # 15
    "",                                           # 16
    "   .. method:: grow(n)",                     # 17
    "",                                           # 18
    "      Grow it.",                             # 19
    "",                                           # 20
    "      .. versionadded:: 3.11",               # 21 Widget.grow
    "",                                           # 22
    "   .. attribute:: Widget.color",             # 23
    "",                                           # 24
    "      .. versionadded:: 3.12",               # 25 described (line 26)
    "         The default changed.",              # 26
    "",                                           # 27
    "   .. versionadded:: 3.8",                   # 28 the class itself
    "",                                           # 29
    ".. data:: ONE",                              # 30
    "          TWO",                              # 31
    "",                                           # 32
    "   Constants.",                              # 33
    "",                                           # 34
    "   .. versionadded:: 3.13",                  # 35 ONE and TWO
    "",                                           # 36
    ".. function:: build(a, \\",                  # 37
    "                    b)",                     # 38 continued signature, not a name
    "",                                           # 39
    "   .. versionadded:: 3.12.1",                # 40 micro release
    "",                                           # 41
    "   .. note::",                               # 42
    "",                                           # 43
    "      .. versionadded:: 3.14",               # 44 inside a note: unattached
])

BUILTINS = "\n".join([
    ".. class:: str(object='')",                  # 1
    "",                                           # 2
    "   .. method:: str.removeprefix(prefix, /)",  # 3
    "",                                           # 4
    "      .. versionadded:: 3.9",                # 5
    "",                                           # 6
    ".. currentmodule:: None",                    # 7
    "",                                           # 8
    ".. function:: nowhere()",                    # 9
    "",                                           # 10
    "   .. versionadded:: 3.10",                  # 11
    "",                                           # 12
    ".. currentmodule:: pkg.mod",                 # 13
    "",                                           # 14
    ".. py:class:: Outer.Inner",                  # 15
    "",                                           # 16
    "   .. py:method:: Inner.go()",               # 17
    "",                                           # 18
    "      .. versionadded:: next",               # 19
])


def short(rows):
    return [(r["line"], r["kind"], r["module"], r["qual"], r["version"], r["described"])
            for r in rows]


class TestScan(unittest.TestCase):
    def test_demo_rows(self):
        rows = audit.scan(DEMO, "demo.rst")
        self.assertEqual(short(rows), [
            (7, "module", "demo", "", "3.9", False),
            (11, "unattached", None, None, "3.10", False),
            (21, "method", "demo", "Widget.grow", "3.11", False),
            (25, "attribute", "demo", "Widget.color", "3.12", True),
            (28, "class", "demo", "Widget", "3.8", False),
            (35, "data", "demo", "ONE", "3.13", False),
            (35, "data", "demo", "TWO", "3.13", False),
            (40, "function", "demo", "build", "3.12.1", False),
            (44, "unattached", None, None, "3.14", False),
        ])
        self.assertEqual(rows[7]["micro"], 1)
        self.assertEqual((rows[2]["major"], rows[2]["minor"], rows[2]["micro"]), (3, 11, 0))
        self.assertEqual([audit.primary(r) for r in rows],
                         [True, False, True, False, True, True, True, False, False])

    def test_builtins_default_and_currentmodule(self):
        rows = audit.scan(BUILTINS, "b.rst")
        self.assertEqual(short(rows), [
            (5, "method", "builtins", "str.removeprefix", "3.9", False),
            (11, "function", None, "nowhere", "3.10", False),
            (19, "method", "pkg.mod", "Outer.Inner.go", "next", False),
        ])
        self.assertEqual([audit.primary(r) for r in rows], [True, False, False])
        self.assertIsNone(rows[2]["major"])

    def test_helpers(self):
        self.assertEqual(audit.first_name("open(file, mode='r')"), "open")
        self.assertEqual(audit.first_name("  Path.read_text(encoding=None)"), "Path.read_text")
        self.assertIsNone(audit.first_name("(weird)"))
        self.assertEqual(audit.parse_version("3.9"), (3, 9, 0))
        self.assertEqual(audit.parse_version("3.6.1"), (3, 6, 1))
        self.assertEqual(audit.parse_version("next"), (None, None, None))
        self.assertTrue(audit.RULE.match("--------------"))
        self.assertTrue(audit.RULE.match("===="))
        self.assertFalse(audit.RULE.match("===  ==="))
        self.assertFalse(audit.RULE.match(":mod:`x` --- y"))


class TestClassify(unittest.TestCase):
    def test_categories(self):
        st = {7: "no", 8: "yes", 9: "yes"}
        self.assertEqual(audit.classify(8, st), "ok")
        self.assertEqual(audit.classify(9, st), "earlier")
        self.assertEqual(audit.classify(9, {8: "no", 9: "no", 10: "yes"}), "later")
        self.assertEqual(audit.classify(9, {8: "no", 9: "no", 10: "no"}), "never_found")
        self.assertEqual(audit.classify(9, {8: "yes", 9: "no", 10: "no"}), "earlier")
        self.assertEqual(audit.classify(9, {7: "yes", 8: "no", 9: "no", 10: "no"}), "gap")
        self.assertEqual(audit.classify(9, {8: "no_module", 9: "yes"}), "ok")
        self.assertEqual(audit.classify(9, {8: "import_error", 9: "yes"}), "import_error")
        self.assertEqual(audit.classify(9, {9: "yes"}), "untested")


class TestGrade(unittest.TestCase):
    def row(self, prim, cat):
        return {"primary": prim, "category": cat, "minor": 9}

    def test_failed_p1_held_p2(self):
        rows = [self.row(True, "ok")] * 3 + [self.row(True, "earlier"),
                                             self.row(False, "earlier"),
                                             self.row(True, "never_found")]
        g = audit.grade(rows)
        self.assertEqual((g["P1"]["n"], g["P1"]["ok"], g["P1"]["share"]), (4, 3, 0.75))
        self.assertEqual(g["P1"]["verdict"], "failed")
        self.assertEqual((g["P2"]["earlier"], g["P2"]["later"]), (1, 0))
        self.assertEqual(g["P2"]["verdict"], "held")
        self.assertEqual(g["P3"]["flagged"], 1)
        self.assertEqual(g["categories_all_rows"], {"ok": 3, "earlier": 2, "never_found": 1})
        self.assertEqual(g["primary_by_version"], {"3.9": {"ok": 3, "earlier": 1}})

    def test_held_p1_failed_p2(self):
        g = audit.grade([self.row(True, "ok"), self.row(True, "ok")])
        self.assertEqual(g["P1"]["share"], 1.0)
        self.assertEqual(g["P1"]["verdict"], "held")
        self.assertEqual(g["P2"]["verdict"], "failed")

    def test_empty(self):
        g = audit.grade([])
        self.assertIsNone(g["P1"]["share"])
        self.assertEqual(g["P1"]["verdict"], "failed")


class TestProbe(unittest.TestCase):
    def test_probe_on_this_interpreter(self):
        self.assertEqual(probe.probe("json", "dumps"), "yes")
        self.assertEqual(probe.probe("json", "no_such_name_xyz"), "no")
        self.assertEqual(probe.probe("json", "json.decoder.JSONDecoder"), "yes")
        self.assertEqual(probe.probe("json", ""), "yes")
        self.assertEqual(probe.probe("no_such_module_xyz", "a"), "no_module")
        self.assertEqual(probe.probe("no_such_module_xyz", ""), "no_module")
        self.assertEqual(probe.probe("xml.no_such_module_xyz", ""), "no_module")
        self.assertEqual(probe.probe("builtins", "str.removeprefix"), "yes")
        self.assertEqual(probe.probe("this", "s"), "import_error")


if __name__ == "__main__":
    unittest.main()
