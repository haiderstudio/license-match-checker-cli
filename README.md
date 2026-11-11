# license-match-checker-cli

Check the LICENSE file matches the license declared in the README and pyproject.toml, fail CI on a mismatch.

[![CI](https://github.com/haiderstudio/license-match-checker-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/haiderstudio/license-match-checker-cli/actions/workflows/ci.yml) [![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)

## What it does

`license_match_checker` reads your LICENSE file, works out
which license its text actually is, and checks it against
the license you declared:

- A repo that declares MIT but ships an Apache LICENSE text
  (or the other way round) misleads every user about what
  they may do with the code — and the mismatch is usually a
  copy-paste accident nobody ever checks. This tool reports
  the mismatch with what was declared and what the LICENSE
  text actually is, and exits 1 when they disagree — so it
  can fail a CI run. A matching project exits 0.
- The LICENSE text is recognised by hand-rolled phrase
  matching on the standard wording of each license — MIT's
  "Permission is hereby granted, free of charge, to any
  person obtaining a copy", Apache's "Apache License,
  Version 2.0, January 2004", the GPL's "GNU GENERAL PUBLIC
  LICENSE", and so on.
- **Licenses it recognises:** MIT, Apache-2.0, GPL-2.0,
  GPL-3.0, LGPL-2.1, LGPL-3.0, BSD-2-Clause, BSD-3-Clause,
  ISC, MPL-2.0, Unlicense, and CC0-1.0 — full standard texts
  only, not one-line shorthands. A LICENSE file whose text
  matches none of them is reported as unknown, not guessed
  at.
- **It does NOT give legal advice.** It only compares two
  pieces of text — the license you declared and the license
  text you shipped — and tells you when they disagree.
  Whether a license suits your project, and what any license
  means in law, is a question for a lawyer, not for this
  tool.
- The declared license comes from the README (a line
  mentioning the license, for example "Licence: MIT" or
  "MIT — see LICENSE") and from `pyproject.toml` (the
  `license` field, or a "License :: OSI Approved :: ..."
  classifier). `--license` sets the declared license
  directly, for example `--license MIT`. When the README and
  `pyproject.toml` declare different licenses, that is
  reported as a mismatch too.
- **With no license declared anywhere and no `--license`,
  the tool stops with exit 2 and says so plainly.** There is
  nothing to match against. Declare one in the README or
  `pyproject.toml`, or pass `--license`.
- A missing LICENSE file is a fail (exit 1), not a skip: a
  project with no license file cannot match its declaration.
  The tool looks for `LICENSE`, `LICENSE.txt`, `LICENSE.md`,
  `LICENCE` and its variants, and `COPYING` and its variants.
- `--json` prints the result as machine-readable JSON (the
  summary goes to standard error, so standard output stays
  clean JSON).
- It is report-only and runs fully offline: it never edits a
  file, sends nothing anywhere, and needs no API key. Python
  standard library only — the matching is plain string
  checks on the license texts.

## What it does NOT do

- It does not give legal advice, and it does not say whether
  a license is the right one for your project. It only says
  whether the text you shipped matches the license you
  declared.
- It does not recognise a one-line license shorthand ("MIT
  License" and a copyright line, with no license text). The
  LICENSE file must hold the full standard text.
- It does not check license headers inside source files —
  that is repo #56's `license-header-checker-cli`. This
  tool's one job is the LICENSE file against the declared
  license.
- It does not check that a LICENSE file exists — that is
  repo #10's `repo-hygiene-checker-cli`. This tool checks
  that it MATCHES.
- It does not fix, rewrite, or replace any file. A mismatch
  is reported; fixing it is your job.

## Who it is for

Anyone publishing open source: a developer who copied a
LICENSE file from another project and never checked it
matches the license in the README, a maintainer adding a CI
step that fails the build when the declared license and the
shipped license drift apart, or anyone tidying a repo before
a public release. A license mismatch is invisible in the
file itself — this catches it before it goes live.

## How this differs from similar tools

The exact name `license-match-checker-cli` matches 0
repositories on GitHub (checked Nov 10, 2026), and the wider
field is noise: `license match checker` matches 2
repositories — a license-PLATE detection app and an FTC
robotics SDK. No rival checks that a LICENSE file agrees
with the declared license. This tool does that one job: a
Python standard-library-only CLI that reads the LICENSE
text, recognises twelve licenses by their own wording,
reads the declaration from the README and `pyproject.toml`,
and exits 1 for CI — no install beyond Python, no website,
no network.

## Install

Python standard library only — no packages to download. You need
Python 3.8 or newer. Clone the repo and run it in place:

```
git clone https://github.com/haiderstudio/license-match-checker-cli.git
cd license-match-checker-cli
python3 src/license_match_checker.py examples/mit-project
```

```
OK examples/mit-project: LICENSE is MIT, matches declared MIT
OK — 1 project(s) checked, LICENSE matches the declared license.
```

## Usage

Check a project whose LICENSE is MIT and which declares MIT:

```
python3 src/license_match_checker.py examples/mit-project
```

```
OK examples/mit-project: LICENSE is MIT, matches declared MIT
OK — 1 project(s) checked, LICENSE matches the declared license.
```

Check a project whose LICENSE is Apache 2.0 and which declares
Apache 2.0:

```
python3 src/license_match_checker.py examples/apache-project
```

```
OK examples/apache-project: LICENSE is Apache-2.0, matches declared Apache-2.0
OK — 1 project(s) checked, LICENSE matches the declared license.
```

Check a project that declares MIT but ships an Apache LICENSE
text:

```
python3 src/license_match_checker.py examples/mismatch-project
```

```
FAIL examples/mismatch-project: declared MIT, LICENSE text looks like Apache-2.0
Checked 1 project(s), 1 problem(s).
```

A project with no license declared anywhere stops with exit 2,
and says what to do:

```
python3 src/license_match_checker.py examples/no-declaration
```

```
error: no license declared for examples/no-declaration — no license in the README or pyproject.toml and no --license given. Declare one, for example --license MIT.
```

Declare the license on the command line instead:

```
python3 src/license_match_checker.py --license MIT examples/mit-project
```

```
OK examples/mit-project: LICENSE is MIT, matches declared MIT
OK — 1 project(s) checked, LICENSE matches the declared license.
```

Machine-readable output with `--json` (the summary goes to
standard error, so standard output stays clean JSON):

```
python3 src/license_match_checker.py --json examples/mismatch-project
```

```
{
  "projects": [
    {
      "folder": "examples/mismatch-project",
      "license_file": "examples/mismatch-project/LICENSE",
      "detected": "Apache-2.0",
      "declared": [
        "MIT"
      ],
      "sources": {
        "MIT": [
          "README",
          "pyproject.toml"
        ]
      },
      "problems": [
        "declared MIT, LICENSE text looks like Apache-2.0"
      ]
    }
  ],
  "summary": {
    "checked": 1,
    "problems": 1
  }
}
```

Exit codes: 0 when the LICENSE text matches the declared
license, 1 when it does not match, the LICENSE file is
missing, or its text is not recognised, 2 for a usage problem
(no license declared anywhere, a bad `--license` value, a
missing path, or a missing `--readme` / `--pyproject` file).

## Examples

### 1. A matching MIT project

`examples/mit-project/` holds a full MIT LICENSE text, a
README that says "MIT — see LICENSE", and a
`pyproject.toml` with `license = "MIT"`:

```
python3 src/license_match_checker.py examples/mit-project
```

```
OK examples/mit-project: LICENSE is MIT, matches declared MIT
OK — 1 project(s) checked, LICENSE matches the declared license.
```

### 2. A mismatch — declared MIT, shipped Apache

`examples/mismatch-project/` has the same README and
`pyproject.toml` as the MIT project, but its LICENSE file
holds the Apache 2.0 text:

```
python3 src/license_match_checker.py examples/mismatch-project
```

```
FAIL examples/mismatch-project: declared MIT, LICENSE text looks like Apache-2.0
Checked 1 project(s), 1 problem(s).
```

### 3. The bundled examples, all at once

```
sh examples/run-example.sh
```

The script checks the MIT project (pass), then the Apache
project (pass), then the mismatch project (fail, on
purpose), then the project with no declaration (stops with
exit 2, on purpose — its error goes to standard error, so
it does not appear in the saved output). Its full output is
in `examples/sample-output.md`, ending with `Checked 1
project(s), 1 problem(s).` The failing runs exit 1, which is
the expected result — the script ends with exit 0 so it can
be run as a demo.

## How it is tested

Tests, standard library `unittest` only, no packages to install:

```
python3 tests/test_license_match_checker.py
```

The tests cover: license detection (all twelve recognised
licenses, BSD-3 beating BSD-2, LGPL beating GPL, GPL 2 and 3
told apart, unknown text, one-line shorthands not recognised,
case and whitespace ignored), declared-license names (SPDX
ids, plain names like "Apache 2.0" and "GPLv3", unknown
names), reading declarations from README lines (including
badges) and from `pyproject.toml` (string form, dict form,
and classifiers), the project check (matching project,
mismatch naming both sides, missing LICENSE file, unknown
LICENSE text, no declaration, declarations that disagree,
`--license` setting the declaration and an unknown
`--license` value, `LICENCE.txt` spelling, input files left
unchanged), the CLI (exit 0/1/2, two projects at once,
`--json` output, `--version`, bad flags), the bundled
examples (sample output compared byte-for-byte against a
fresh run, and the README-quoted outputs checked against
it), and hygiene checks (no placeholder text, no absolute
paths, stdlib imports only, `.env` first in `.gitignore`, CI
file runs the test file).

## Contributing

Small, focused improvements are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

## Original work

This tool was written from scratch for this repo. The idea of
checking a license is not new — the similar tools named above
(a license-plate detector and a robotics SDK) are listed in
"How this differs" — but every line of code here is original,
and the tool builds on nothing but Python's standard library.
The license texts in `examples/` are the licenses' own
standard texts, used as sample inputs.
