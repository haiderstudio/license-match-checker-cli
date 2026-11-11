#!/usr/bin/env python3
"""Check a LICENSE file matches the license declared in README/pyproject.

Run: python3 src/license_match_checker.py examples/mit-project
     python3 src/license_match_checker.py --license MIT examples/mit-project
     python3 src/license_match_checker.py examples/mismatch-project

The problem is quiet: a repo that declares MIT but ships an
Apache LICENSE text (or the other way round) misleads every
user about what they may do with the code — and the mismatch
is usually a copy-paste accident nobody ever checks. This
tool reads the LICENSE file, works out which license its text
actually is, reads the license declared in the README and in
pyproject.toml, and reports a mismatch with what was declared
and what the LICENSE text actually is. It exits 1 when they
disagree, so it can fail a CI run. A matching project exits 0.

The LICENSE text is recognised by hand-rolled phrase matching
on the standard wording of each license — MIT's "Permission
is hereby granted, free of charge, to any person obtaining a
copy", Apache's "Apache License, Version 2.0, January 2004",
the GPL's "GNU GENERAL PUBLIC LICENSE", and so on. It
recognises MIT, Apache-2.0, GPL-2.0, GPL-3.0, LGPL-2.1,
LGPL-3.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0,
Unlicense, and CC0-1.0 — full standard texts only, not
one-line shorthands. A LICENSE file whose text matches none
of them is reported as unknown, not guessed at.

The declared license comes from the README (a line mentioning
the license, for example "Licence: MIT" or "MIT — see
LICENSE") and from pyproject.toml (the license field, or a
"License :: OSI Approved :: ..." classifier). --license sets
the declared license directly, for example --license MIT.
When the README and pyproject.toml declare different
licenses, that is reported as a mismatch too.

With no license declared anywhere and no --license, the tool
stops with exit 2 and says so plainly: there is nothing to
match against. A missing LICENSE file is a fail (exit 1),
not a skip: a project with no license file cannot match its
declaration.

It never rewrites a file. It is report-only and runs fully
offline: it sends nothing anywhere and needs no API key.

This tool does NOT give legal advice. It only compares two
pieces of text — the license you declared and the license
text you shipped — and tells you when they disagree. Whether
a license suits your project, and what any license means in
law, is a question for a lawyer, not for this tool.

Exit codes: 0 when the LICENSE text matches the declared
license, 1 when it does not match, the LICENSE file is
missing, or its text is not recognised, 2 for a usage or
input problem (a missing path, a bad flag, or no license
declared anywhere).

Python standard library only.
"""

import argparse
import json
import re
import sys
from pathlib import Path

VERSION = "1.0.0"

LICENSE_FILENAMES = (
    "LICENSE",
    "LICENSE.txt",
    "LICENSE.md",
    "LICENCE",
    "LICENCE.txt",
    "LICENCE.md",
    "COPYING",
    "COPYING.txt",
    "COPYING.md",
)

RECOGNISED = (
    "MIT",
    "Apache-2.0",
    "GPL-2.0",
    "GPL-3.0",
    "LGPL-2.1",
    "LGPL-3.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "MPL-2.0",
    "Unlicense",
    "CC0-1.0",
)

# Each license: phrases that must all appear in the LICENSE text
# (lowercase, whitespace collapsed), in the order they are tried.
# More specific licenses are tried first: LGPL before GPL, because
# a GPL text must not be claimed by the LGPL check, and BSD-3
# before BSD-2, because a BSD-3 text contains the BSD-2 phrases
# plus the third clause.
LICENSE_PHRASES = (
    (
        "LGPL-3.0",
        (
            "gnu lesser general public license",
            "version 3, 29 june 2007",
        ),
    ),
    (
        "LGPL-2.1",
        (
            "gnu lesser general public license",
            "version 2.1, february 1999",
        ),
    ),
    (
        "GPL-3.0",
        (
            "gnu general public license",
            "version 3, 29 june 2007",
        ),
    ),
    (
        "GPL-2.0",
        (
            "gnu general public license",
            "version 2, june 1991",
        ),
    ),
    (
        "Apache-2.0",
        (
            "apache license",
            "version 2.0, january 2004",
        ),
    ),
    (
        "BSD-3-Clause",
        (
            "redistribution and use in source and binary forms",
            "neither the name",
        ),
    ),
    (
        "BSD-2-Clause",
        ("redistribution and use in source and binary forms",),
    ),
    (
        "MPL-2.0",
        ("mozilla public license version 2.0",),
    ),
    (
        "MIT",
        (
            "permission is hereby granted, free of charge, to any "
            "person obtaining a copy",
            "the above copyright notice and this permission notice "
            "shall be included in all",
        ),
    ),
    (
        "ISC",
        (
            "permission to use, copy, modify, and/or distribute this "
            "software",
        ),
    ),
    (
        "Unlicense",
        (
            "this is free and unencumbered software released into "
            "the public domain",
        ),
    ),
    (
        "CC0-1.0",
        ("cc0 1.0 universal",),
    ),
)

# Names people write when they declare a license, mapped to SPDX ids.
NAME_TO_SPDX = {
    "mit": "MIT",
    "mit license": "MIT",
    "apache 2.0": "Apache-2.0",
    "apache-2.0": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "apache license, version 2.0": "Apache-2.0",
    "apache license": "Apache-2.0",
    "gpl 3.0": "GPL-3.0",
    "gpl-3.0": "GPL-3.0",
    "gplv3": "GPL-3.0",
    "gnu general public license v3": "GPL-3.0",
    "gnu general public license version 3": "GPL-3.0",
    "gpl 2.0": "GPL-2.0",
    "gpl-2.0": "GPL-2.0",
    "gplv2": "GPL-2.0",
    "gnu general public license v2": "GPL-2.0",
    "gnu general public license version 2": "GPL-2.0",
    "lgpl 3.0": "LGPL-3.0",
    "lgpl-3.0": "LGPL-3.0",
    "gnu lesser general public license v3": "LGPL-3.0",
    "lgpl 2.1": "LGPL-2.1",
    "lgpl-2.1": "LGPL-2.1",
    "gnu lesser general public license v2.1": "LGPL-2.1",
    "bsd 3-clause": "BSD-3-Clause",
    "bsd-3-clause": "BSD-3-Clause",
    "bsd 3 clause": "BSD-3-Clause",
    "bsd 2-clause": "BSD-2-Clause",
    "bsd-2-clause": "BSD-2-Clause",
    "bsd 2 clause": "BSD-2-Clause",
    "isc": "ISC",
    "isc license": "ISC",
    "mpl 2.0": "MPL-2.0",
    "mpl-2.0": "MPL-2.0",
    "mozilla public license 2.0": "MPL-2.0",
    "unlicense": "Unlicense",
    "the unlicense": "Unlicense",
    "cc0 1.0": "CC0-1.0",
    "cc0-1.0": "CC0-1.0",
    "cc0 1.0 universal": "CC0-1.0",
}

SPDX_IDS = tuple(RECOGNISED)

LICENSE_FIELD_RE = re.compile(
    r"""license\s*=\s*(?:\{[^}]*?text\s*=\s*["']([^"']+)["']|["']([^"']+)["'])""",
    re.IGNORECASE | re.DOTALL,
)
CLASSIFIER_RE = re.compile(
    r"""License\s*::\s*OSI Approved\s*::\s*([^\n"']+)""", re.IGNORECASE
)
SPDX_RE = re.compile(
    r"\b(MIT|Apache-2\.0|GPL-3\.0|GPL-2\.0|LGPL-3\.0|LGPL-2\.1"
    r"|BSD-3-Clause|BSD-2-Clause|ISC|MPL-2\.0|Unlicense|CC0-1\.0)\b",
    re.IGNORECASE,
)


def normalise(text):
    """Lowercase text and collapse all whitespace to single spaces."""
    return " ".join(text.lower().split())


def detect_license(text):
    """Return the SPDX id the LICENSE text looks like, or None.

    Every phrase for a license must appear in the text. Licenses
    are tried most specific first, so BSD-3 wins over BSD-2 and
    LGPL wins over GPL on their own texts.
    """
    flat = normalise(text)
    for spdx, phrases in LICENSE_PHRASES:
        if all(phrase in flat for phrase in phrases):
            return spdx
    return None


def canonical_spdx(name):
    """Return the SPDX id for a declared license name, or None."""
    cleaned = " ".join(name.strip().lower().split())
    if cleaned in NAME_TO_SPDX:
        return NAME_TO_SPDX[cleaned]
    for spdx in SPDX_IDS:
        if cleaned == spdx.lower():
            return spdx
    return None


def declared_from_text(text, source):
    """Return the set of SPDX ids declared in a block of text.

    Only lines that mention a license are read, so a README
    that discusses other licenses in passing is not mistaken
    for a declaration. SPDX ids are tried first, then license
    names.
    """
    found = set()
    for line in text.splitlines():
        if "licen" not in line.lower() and "licence" not in line.lower():
            continue
        match = SPDX_RE.search(line)
        if match:
            found.add(canonical_spdx(match.group(1)))
            continue
        flat = normalise(line)
        for name in sorted(NAME_TO_SPDX, key=len, reverse=True):
            if name in flat:
                found.add(NAME_TO_SPDX[name])
                break
    return found


def declared_from_pyproject(text):
    """Return the set of SPDX ids declared in a pyproject.toml."""
    found = set()
    for match in LICENSE_FIELD_RE.finditer(text):
        value = match.group(1) or match.group(2)
        spdx = canonical_spdx(value)
        if spdx is not None:
            found.add(spdx)
    for match in CLASSIFIER_RE.finditer(text):
        value = match.group(1).strip()
        spdx = canonical_spdx(value)
        if spdx is None:
            # "MIT License" and friends: strip the trailing word.
            spdx = canonical_spdx(value.replace(" License", ""))
        if spdx is not None:
            found.add(spdx)
    return found


def find_license_file(folder):
    """Return the license file in a folder, or None."""
    for name in LICENSE_FILENAMES:
        candidate = folder / name
        if candidate.is_file():
            return candidate
    return None


def find_declared(folder, readme_path, pyproject_path):
    """Return (declared, sources) for a project folder.

    declared is a set of SPDX ids; sources maps each id to the
    places that declared it ("README", "pyproject.toml").
    """
    declared = set()
    sources = {}
    readme = readme_path or folder / "README.md"
    if readme.is_file():
        try:
            text = readme.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        for spdx in declared_from_text(text, "README"):
            declared.add(spdx)
            sources.setdefault(spdx, []).append("README")
    pyproject = pyproject_path or folder / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        for spdx in declared_from_pyproject(text):
            declared.add(spdx)
            sources.setdefault(spdx, []).append("pyproject.toml")
    return declared, sources


def build_parser():
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="license_match_checker",
        description=(
            "Check a LICENSE file matches the license declared "
            "in the README and/or pyproject.toml."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="project folders to check (default: current folder)",
    )
    parser.add_argument(
        "--license",
        metavar="LICENSE",
        default=None,
        help="license declared for this check, for example MIT "
        "(an SPDX id or a name like 'Apache 2.0')",
    )
    parser.add_argument(
        "--license-file",
        metavar="PATH",
        default=None,
        help="LICENSE file to check (default: LICENSE in the project folder)",
    )
    parser.add_argument(
        "--readme",
        metavar="PATH",
        default=None,
        help="README file to read the declared license from "
        "(default: README.md in the project folder)",
    )
    parser.add_argument(
        "--pyproject",
        metavar="PATH",
        default=None,
        help="pyproject.toml to read the declared license from "
        "(default: pyproject.toml in the project folder)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the result as machine-readable JSON",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s " + VERSION,
    )
    return parser


def check_project(folder, args):
    """Check one project folder. Returns a result dict.

    Keys: folder, license_file, detected, declared (sorted list),
    sources (dict), problems (list of strings).
    """
    result = {
        "folder": str(folder),
        "license_file": None,
        "detected": None,
        "declared": [],
        "sources": {},
        "problems": [],
    }
    if args.license_file is not None:
        license_file = Path(args.license_file)
        if not license_file.is_file():
            result["problems"].append(
                "license file not found: %s" % args.license_file
            )
            return result
    else:
        license_file = find_license_file(folder)
        if license_file is None:
            result["problems"].append("no LICENSE file found")
            return result
    result["license_file"] = str(license_file)
    try:
        text = license_file.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        result["problems"].append(
            "cannot read LICENSE file (%s)" % exc.strerror
        )
        return result
    detected = detect_license(text)
    result["detected"] = detected
    if detected is None:
        result["problems"].append(
            "LICENSE text does not match any recognised license "
            "(recognised: %s)" % ", ".join(RECOGNISED)
        )

    declared, sources = find_declared(
        folder,
        Path(args.readme) if args.readme else None,
        Path(args.pyproject) if args.pyproject else None,
    )
    if args.license is not None:
        spdx = canonical_spdx(args.license)
        if spdx is None:
            result["problems"].append(
                "unknown license for --license: %r (recognised: %s)"
                % (args.license, ", ".join(RECOGNISED))
            )
        else:
            declared.add(spdx)
            sources.setdefault(spdx, []).append("--license")
    result["declared"] = sorted(declared)
    result["sources"] = sources
    if not declared:
        result["problems"].append("no license declared")
    elif len(declared) > 1:
        result["problems"].append(
            "declarations disagree: %s"
            % ", ".join(
                "%s (%s)" % (spdx, ", ".join(sources.get(spdx, [])))
                for spdx in sorted(declared)
            )
        )
    elif detected is not None and detected not in declared:
        result["problems"].append(
            "declared %s, LICENSE text looks like %s"
            % (sorted(declared)[0], detected)
        )
    return result


def main(argv=None):
    """Run the checker. Returns an exit code: 0 match, 1 mismatch, 2 usage."""
    parser = build_parser()
    args = parser.parse_args(argv)

    paths = args.paths or ["."]
    for raw in paths:
        if not Path(raw).is_dir():
            print("error: project folder not found: %s" % raw, file=sys.stderr)
            return 2
    if args.readme is not None and not Path(args.readme).is_file():
        print("error: README file not found: %s" % args.readme, file=sys.stderr)
        return 2
    if args.pyproject is not None and not Path(args.pyproject).is_file():
        print(
            "error: pyproject.toml file not found: %s" % args.pyproject,
            file=sys.stderr,
        )
        return 2

    results = [check_project(Path(raw), args) for raw in paths]

    # "No license declared" is a usage problem (exit 2), not a
    # mismatch: there is nothing to match against.
    if any("no license declared" in p for r in results for p in r["problems"]):
        for result in results:
            for problem in result["problems"]:
                if problem == "no license declared":
                    print(
                        "error: no license declared for %s — no license "
                        "in the README or pyproject.toml and no "
                        "--license given. Declare one, for example "
                        "--license MIT." % result["folder"],
                        file=sys.stderr,
                    )
        return 2

    total_problems = sum(len(r["problems"]) for r in results)
    checked = len(results)

    if args.json:
        payload = {
            "projects": [
                {
                    "folder": r["folder"],
                    "license_file": r["license_file"],
                    "detected": r["detected"],
                    "declared": r["declared"],
                    "sources": r["sources"],
                    "problems": r["problems"],
                }
                for r in results
            ],
            "summary": {
                "checked": checked,
                "problems": total_problems,
            },
        }
        print(json.dumps(payload, indent=2))
        if total_problems == 0:
            print(
                "OK — %d project(s) checked, LICENSE matches the "
                "declared license." % checked,
                file=sys.stderr,
            )
        else:
            print(
                "Checked %d project(s), %d problem(s)."
                % (checked, total_problems),
                file=sys.stderr,
            )
    else:
        for result in results:
            if result["problems"]:
                for problem in result["problems"]:
                    if result["detected"] is not None and (
                        "declared" in problem and "LICENSE text looks like" in problem
                    ):
                        print(
                            "FAIL %s: declared %s, LICENSE text looks "
                            "like %s"
                            % (
                                result["folder"],
                                result["declared"][0],
                                result["detected"],
                            )
                        )
                    elif problem == "no LICENSE file found":
                        print(
                            "FAIL %s: no LICENSE file found"
                            % result["folder"]
                        )
                    elif problem.startswith(
                        "LICENSE text does not match any recognised"
                    ):
                        print(
                            "FAIL %s: LICENSE text does not match any "
                            "recognised license" % result["folder"]
                        )
                    else:
                        print("FAIL %s: %s" % (result["folder"], problem))
            else:
                print(
                    "OK %s: LICENSE is %s, matches declared %s"
                    % (
                        result["folder"],
                        result["detected"],
                        result["declared"][0],
                    )
                )
        if total_problems == 0:
            print(
                "OK — %d project(s) checked, LICENSE matches the "
                "declared license." % checked
            )
        else:
            print(
                "Checked %d project(s), %d problem(s)."
                % (checked, total_problems)
            )

    return 1 if total_problems else 0


if __name__ == "__main__":
    sys.exit(main())
