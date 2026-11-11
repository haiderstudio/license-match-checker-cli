#!/bin/sh
# Check the bundled examples. The failing runs exit 1 on purpose,
# so each one ends with "|| true"; the script itself ends with
# exit 0 so it can be run as a demo. Run from the repo root:
# sh examples/run-example.sh
cd "$(dirname "$0")/.."
echo "== mit-project: LICENSE is MIT, declared MIT, passes =="
python3 src/license_match_checker.py examples/mit-project || true
echo
echo "== apache-project: LICENSE is Apache-2.0, declared Apache-2.0, passes =="
python3 src/license_match_checker.py examples/apache-project || true
echo
echo "== mismatch-project: declared MIT, LICENSE is Apache-2.0, fails =="
python3 src/license_match_checker.py examples/mismatch-project || true
echo
echo "== no-declaration: no license declared anywhere, stops =="
python3 src/license_match_checker.py examples/no-declaration || true
