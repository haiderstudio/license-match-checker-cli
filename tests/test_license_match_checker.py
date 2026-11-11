#!/usr/bin/env python3
"""Tests for license-match-checker-cli. Standard library unittest only.

Run from the repo root: python3 tests/test_license_match_checker.py
"""

import ast
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import license_match_checker as lmc  # noqa: E402

ALLOWED_STDLIB = {
    "argparse",
    "json",
    "re",
    "sys",
    "pathlib",
}

MIT_TEXT = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")

APACHE_TEXT = """Apache License
Version 2.0, January 2004
http://www.apache.org/licenses/

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
"""

GPL3_TEXT = """GNU GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

Copyright (C) 2007 Free Software Foundation, Inc.
Everyone is permitted to copy and distribute verbatim copies
of this license document, but changing it is not allowed.
"""

GPL2_TEXT = """GNU GENERAL PUBLIC LICENSE
Version 2, June 1991

Copyright (C) 1989, 1991 Free Software Foundation, Inc.
Everyone is permitted to copy and distribute verbatim copies
of this license document, but changing it is not allowed.
"""

LGPL3_TEXT = """GNU LESSER GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

Copyright (C) 2007 Free Software Foundation, Inc.
Everyone is permitted to copy and distribute verbatim copies
of this license document, but changing it is not allowed.
"""

LGPL21_TEXT = """GNU LESSER GENERAL PUBLIC LICENSE
Version 2.1, February 1999

Copyright (C) 1991, 1999 Free Software Foundation, Inc.
Everyone is permitted to copy and distribute verbatim copies
of this license document, but changing it is not allowed.
"""

BSD3_TEXT = """Redistribution and use in source and binary forms, with or
without modification, are permitted provided that the following
conditions are met:

1. Redistributions of source code must retain the above copyright
notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
contributors may be used to endorse or promote products derived from
this software without specific prior written permission.
"""

BSD2_TEXT = """Redistribution and use in source and binary forms, with or
without modification, are permitted provided that the following
conditions are met:

1. Redistributions of source code must retain the above copyright
notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.
"""

ISC_TEXT = """ISC License

Permission to use, copy, modify, and/or distribute this software for
any purpose with or without fee is hereby granted, provided that the
above copyright notice and this permission notice appear in all copies.
"""

MPL_TEXT = """Mozilla Public License Version 2.0
==================================

1. Definitions
--------------
"""

UNLICENSE_TEXT = """This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.
"""

CC0_TEXT = """CC0 1.0 Universal

Statement of Purpose

The person who associated a work with this deed has dedicated the work
to the public domain by waiving all of his or her rights to the work
worldwide under copyright law.
"""


def run_cli(argv):
    """Run main() in-process and capture (exit code, stdout, stderr)."""
    out = io.StringIO()
    err = io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = lmc.main(argv)
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 0
    finally:
        pass
    return code, out.getvalue(), err.getvalue()


def write(path, text):
    """Write text to path, creating parent folders."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def make_project(folder, license_text, readme, pyproject=None):
    """Build a small project folder. Returns the folder path."""
    folder.mkdir(parents=True, exist_ok=True)
    if license_text is not None:
        write(folder / "LICENSE", license_text)
    write(folder / "README.md", readme)
    if pyproject is not None:
        write(folder / "pyproject.toml", pyproject)
    return folder


class TestDetectLicense(unittest.TestCase):
    def test_each_recognised_license(self):
        cases = {
            "MIT": MIT_TEXT,
            "Apache-2.0": APACHE_TEXT,
            "GPL-3.0": GPL3_TEXT,
            "GPL-2.0": GPL2_TEXT,
            "LGPL-3.0": LGPL3_TEXT,
            "LGPL-2.1": LGPL21_TEXT,
            "BSD-3-Clause": BSD3_TEXT,
            "BSD-2-Clause": BSD2_TEXT,
            "ISC": ISC_TEXT,
            "MPL-2.0": MPL_TEXT,
            "Unlicense": UNLICENSE_TEXT,
            "CC0-1.0": CC0_TEXT,
        }
        for spdx, text in cases.items():
            self.assertEqual(lmc.detect_license(text), spdx, spdx)

    def test_bsd3_beats_bsd2(self):
        # A BSD-3 text contains the BSD-2 phrases too; the third
        # clause must win.
        self.assertEqual(lmc.detect_license(BSD3_TEXT), "BSD-3-Clause")

    def test_lgpl_beats_gpl(self):
        self.assertEqual(lmc.detect_license(LGPL3_TEXT), "LGPL-3.0")
        self.assertEqual(lmc.detect_license(LGPL21_TEXT), "LGPL-2.1")

    def test_gpl_versions_told_apart(self):
        self.assertEqual(lmc.detect_license(GPL3_TEXT), "GPL-3.0")
        self.assertEqual(lmc.detect_license(GPL2_TEXT), "GPL-2.0")

    def test_unknown_text(self):
        self.assertIsNone(lmc.detect_license("Just some words.\n"))
        self.assertIsNone(lmc.detect_license(""))
        self.assertIsNone(
            lmc.detect_license("MIT License\n\nCopyright (c) 2026 Someone\n")
        )

    def test_case_and_whitespace_insensitive(self):
        noisy = MIT_TEXT.upper().replace("  ", "   ")
        self.assertEqual(lmc.detect_license(noisy), "MIT")


class TestCanonicalSpdx(unittest.TestCase):
    def test_spdx_ids(self):
        for spdx in lmc.RECOGNISED:
            self.assertEqual(lmc.canonical_spdx(spdx), spdx)
            self.assertEqual(lmc.canonical_spdx(spdx.lower()), spdx)

    def test_names(self):
        cases = {
            "MIT License": "MIT",
            "Apache 2.0": "Apache-2.0",
            "Apache License": "Apache-2.0",
            "GPLv3": "GPL-3.0",
            "GPLv2": "GPL-2.0",
            "BSD 3-Clause": "BSD-3-Clause",
            "BSD 2-Clause": "BSD-2-Clause",
            "Mozilla Public License 2.0": "MPL-2.0",
            "The Unlicense": "Unlicense",
            "CC0 1.0 Universal": "CC0-1.0",
            "LGPL 2.1": "LGPL-2.1",
        }
        for name, spdx in cases.items():
            self.assertEqual(lmc.canonical_spdx(name), spdx, name)

    def test_unknown_names(self):
        self.assertIsNone(lmc.canonical_spdx("WTFPL"))
        self.assertIsNone(lmc.canonical_spdx(""))
        self.assertIsNone(lmc.canonical_spdx("Proprietary"))


class TestDeclared(unittest.TestCase):
    def test_readme_lines(self):
        self.assertEqual(
            lmc.declared_from_text("## Licence\n\nMIT — see LICENSE.\n", "x"),
            {"MIT"},
        )
        self.assertEqual(
            lmc.declared_from_text("Licence: Apache-2.0\n", "x"),
            {"Apache-2.0"},
        )
        self.assertEqual(
            lmc.declared_from_text(
                "[![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)\n",
                "x",
            ),
            {"MIT"},
        )

    def test_readme_prose_without_license_line_is_ignored(self):
        # A README that only talks about licenses in passing, with
        # no declaration line, declares nothing.
        self.assertEqual(
            lmc.declared_from_text(
                "This project has no license yet.\n", "x"
            ),
            set(),
        )

    def test_pyproject_string_form(self):
        self.assertEqual(
            lmc.declared_from_pyproject('[project]\nlicense = "MIT"\n'),
            {"MIT"},
        )

    def test_pyproject_dict_form(self):
        self.assertEqual(
            lmc.declared_from_pyproject(
                '[project]\nlicense = {text = "Apache-2.0"}\n'
            ),
            {"Apache-2.0"},
        )

    def test_pyproject_classifier(self):
        self.assertEqual(
            lmc.declared_from_pyproject(
                '[project]\nclassifiers = [\n'
                '  "License :: OSI Approved :: MIT License",\n]\n'
            ),
            {"MIT"},
        )

    def test_pyproject_no_license(self):
        self.assertEqual(
            lmc.declared_from_pyproject('[project]\nname = "x"\n'), set()
        )


class TestCheckProject(unittest.TestCase):
    def test_matching_mit_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = make_project(
                Path(tmp) / "proj",
                MIT_TEXT,
                "# P\n\n## Licence\n\nMIT — see LICENSE.\n",
                '[project]\nlicense = "MIT"\n',
            )
            result = lmc.check_project(folder, lmc.build_parser().parse_args([]))
            self.assertEqual(result["problems"], [])
            self.assertEqual(result["detected"], "MIT")
            self.assertEqual(result["declared"], ["MIT"])

    def test_mismatch_reports_both_sides(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = make_project(
                Path(tmp) / "proj",
                APACHE_TEXT,
                "# P\n\n## Licence\n\nMIT — see LICENSE.\n",
                '[project]\nlicense = "MIT"\n',
            )
            result = lmc.check_project(folder, lmc.build_parser().parse_args([]))
            self.assertEqual(len(result["problems"]), 1)
            self.assertIn("declared MIT", result["problems"][0])
            self.assertIn("Apache-2.0", result["problems"][0])
            self.assertEqual(result["detected"], "Apache-2.0")

    def test_missing_license_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = make_project(
                Path(tmp) / "proj",
                None,
                "# P\n\n## Licence\n\nMIT — see LICENSE.\n",
            )
            result = lmc.check_project(folder, lmc.build_parser().parse_args([]))
            self.assertEqual(result["problems"], ["no LICENSE file found"])

    def test_unknown_license_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = make_project(
                Path(tmp) / "proj",
                "Some custom words, not a known license.\n",
                "# P\n\n## Licence\n\nMIT — see LICENSE.\n",
            )
            result = lmc.check_project(folder, lmc.build_parser().parse_args([]))
            self.assertEqual(len(result["problems"]), 1)
            self.assertIn("not match any recognised", result["problems"][0])

    def test_no_declaration(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = make_project(
                Path(tmp) / "proj",
                MIT_TEXT,
                "# P\n\nNothing about a license here.\n",
            )
            result = lmc.check_project(folder, lmc.build_parser().parse_args([]))
            self.assertIn("no license declared", result["problems"])

    def test_declarations_disagree(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = make_project(
                Path(tmp) / "proj",
                MIT_TEXT,
                "# P\n\n## Licence\n\nMIT — see LICENSE.\n",
                '[project]\nlicense = "Apache-2.0"\n',
            )
            result = lmc.check_project(folder, lmc.build_parser().parse_args([]))
            self.assertEqual(len(result["problems"]), 1)
            self.assertIn("disagree", result["problems"][0])

    def test_license_flag_declares(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = make_project(
                Path(tmp) / "proj",
                MIT_TEXT,
                "# P\n\nNothing about a license here.\n",
            )
            args = lmc.build_parser().parse_args(["--license", "MIT"])
            result = lmc.check_project(folder, args)
            self.assertEqual(result["problems"], [])

    def test_license_flag_unknown_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = make_project(
                Path(tmp) / "proj",
                MIT_TEXT,
                "# P\n\n## Licence\n\nMIT — see LICENSE.\n",
            )
            args = lmc.build_parser().parse_args(["--license", "WTFPL"])
            result = lmc.check_project(folder, args)
            self.assertTrue(
                any("unknown license" in p for p in result["problems"])
            )

    def test_licence_spelling_and_license_txt(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "proj"
            folder.mkdir(parents=True)
            write(folder / "LICENCE.txt", MIT_TEXT)
            write(folder / "README.md", "# P\n\nLicence: MIT\n")
            result = lmc.check_project(folder, lmc.build_parser().parse_args([]))
            self.assertEqual(result["problems"], [])
            self.assertEqual(result["detected"], "MIT")

    def test_input_files_are_not_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = make_project(
                Path(tmp) / "proj",
                MIT_TEXT,
                "# P\n\n## Licence\n\nMIT — see LICENSE.\n",
            )
            before = (folder / "LICENSE").read_text(encoding="utf-8")
            lmc.check_project(folder, lmc.build_parser().parse_args([]))
            after = (folder / "LICENSE").read_text(encoding="utf-8")
            self.assertEqual(before, after)


class TestCli(unittest.TestCase):
    def test_matching_project_exit_0(self):
        code, out, _ = run_cli([str(REPO_ROOT / "examples" / "mit-project")])
        self.assertEqual(code, 0)
        self.assertIn("mit-project: LICENSE is MIT", out)
        self.assertIn("matches declared MIT", out)

    def test_mismatch_project_exit_1(self):
        code, out, _ = run_cli(
            [str(REPO_ROOT / "examples" / "mismatch-project")]
        )
        self.assertEqual(code, 1)
        self.assertIn(
            "mismatch-project: declared MIT, LICENSE "
            "text looks like Apache-2.0",
            out,
        )

    def test_no_declaration_exit_2(self):
        code, _, err = run_cli(
            [str(REPO_ROOT / "examples" / "no-declaration")]
        )
        self.assertEqual(code, 2)
        self.assertIn("no license declared", err)

    def test_missing_folder_exit_2(self):
        code, _, err = run_cli(["no-such-project"])
        self.assertEqual(code, 2)
        self.assertIn("not found", err)

    def test_missing_license_file_exit_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = make_project(
                Path(tmp) / "proj",
                None,
                "# P\n\n## Licence\n\nMIT — see LICENSE.\n",
            )
            code, out, _ = run_cli([str(folder)])
            self.assertEqual(code, 1)
            self.assertIn("no LICENSE file found", out)

    def test_two_projects(self):
        code, out, _ = run_cli(
            [
                str(REPO_ROOT / "examples" / "mit-project"),
                str(REPO_ROOT / "examples" / "apache-project"),
            ]
        )
        self.assertEqual(code, 0)
        self.assertIn("2 project(s) checked", out)

    def test_json_output(self):
        code, out, err = run_cli(
            ["--json", str(REPO_ROOT / "examples" / "mismatch-project")]
        )
        self.assertEqual(code, 1)
        payload = json.loads(out)
        self.assertEqual(payload["projects"][0]["detected"], "Apache-2.0")
        self.assertEqual(payload["projects"][0]["declared"], ["MIT"])
        self.assertEqual(len(payload["projects"][0]["problems"]), 1)
        self.assertIn("1 problem(s)", err)

    def test_version_flag(self):
        code, out, _ = run_cli(["--version"])
        self.assertEqual(code, 0)
        self.assertIn("1.0.0", out)

    def test_bad_flag_is_exit_2(self):
        code, _, _ = run_cli(["--nope"])
        self.assertEqual(code, 2)


class TestBundledExamples(unittest.TestCase):
    def test_mit_example(self):
        code, out, _ = run_cli([str(REPO_ROOT / "examples" / "mit-project")])
        self.assertEqual(code, 0)
        self.assertIn(
            "mit-project: LICENSE is MIT, matches declared MIT",
            out,
        )

    def test_apache_example(self):
        code, out, _ = run_cli(
            [str(REPO_ROOT / "examples" / "apache-project")]
        )
        self.assertEqual(code, 0)
        self.assertIn("LICENSE is Apache-2.0, matches declared Apache-2.0", out)

    def test_mismatch_example(self):
        code, out, _ = run_cli(
            [str(REPO_ROOT / "examples" / "mismatch-project")]
        )
        self.assertEqual(code, 1)
        self.assertIn(
            "mismatch-project: declared MIT, LICENSE "
            "text looks like Apache-2.0",
            out,
        )

    def test_run_example_script_matches_sample_output(self):
        script = REPO_ROOT / "examples" / "run-example.sh"
        result = subprocess.run(
            ["sh", str(script)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0)
        sample = (REPO_ROOT / "examples" / "sample-output.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(result.stdout, sample)

    def test_readme_quotes_real_output(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        for line in (
            "OK examples/mit-project: LICENSE is MIT, matches declared MIT",
            "FAIL examples/mismatch-project: declared MIT, LICENSE "
            "text looks like Apache-2.0",
            "OK examples/apache-project: LICENSE is Apache-2.0, "
            "matches declared Apache-2.0",
            "Checked 1 project(s), 1 problem(s).",
        ):
            self.assertIn(line, readme, line)


class TestHygiene(unittest.TestCase):
    def test_no_placeholder_text(self):
        banned = ("TODO", "coming soon", "lorem")
        hits = []
        for path in REPO_ROOT.rglob("*"):
            if (
                ".git" in path.parts
                or "__pycache__" in path.parts
                or "tests" in path.parts
            ):
                continue
            if path.is_file() and path.suffix in (
                ".py",
                ".md",
                ".toml",
                ".yml",
                ".sh",
            ):
                text = path.read_text(encoding="utf-8", errors="replace")
                for word in banned:
                    if word in text:
                        hits.append("%s: %s" % (path, word))
        self.assertEqual(hits, [])

    def test_no_absolute_local_paths(self):
        hits = []
        for path in REPO_ROOT.rglob("*"):
            if (
                ".git" in path.parts
                or "__pycache__" in path.parts
                or "tests" in path.parts
            ):
                continue
            if path.is_file() and path.suffix in (
                ".py",
                ".md",
                ".toml",
                ".yml",
                ".sh",
            ):
                text = path.read_text(encoding="utf-8", errors="replace")
                if "/home/" in text or "/Users/" in text or "C:\\" in text:
                    hits.append(str(path))
        self.assertEqual(hits, [])

    def test_stdlib_imports_only(self):
        source = (REPO_ROOT / "src" / "license_match_checker.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        extra = imports - ALLOWED_STDLIB
        self.assertEqual(extra, set())

    def test_env_first_in_gitignore(self):
        lines = (REPO_ROOT / ".gitignore").read_text(
            encoding="utf-8"
        ).splitlines()
        self.assertEqual(lines[0], ".env")

    def test_ci_runs_the_test_file(self):
        ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("tests/test_license_match_checker.py", ci)
        self.assertIn("setup-python", ci)

    def test_no_secrets(self):
        for path in REPO_ROOT.rglob("*"):
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if path.is_file() and path.name == ".env":
                self.fail(".env file must not ship: %s" % path)


if __name__ == "__main__":
    unittest.main()
