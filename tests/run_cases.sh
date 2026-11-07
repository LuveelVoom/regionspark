#!/bin/sh
# Oracle comparison: hotdogPi's original script (tests/hotdogpi_jul6.py, run against the mock golly
# module in tests/mock/) versus regionspark, single-threaded, on every case in tests/cases.txt.
# Each line must say IDENTICAL. usage: sh tests/run_cases.sh [NAME...]   (run from the repo root)
cd "$(dirname "$0")/.." || exit 1
[ -x ./regionspark ] || { echo "build it first: make"; exit 1; }
[ -f tests/hotdogpi_jul6.py ] || { echo "tests/hotdogpi_jul6.py (the original script) is missing (it is not in the repo; see README.md, Tests)"; exit 1; }
T=$(mktemp -d); fail=0
while IFS='|' read -r name rule rle range okv pargs; do
    [ -z "$name" ] && continue
    if [ $# -gt 0 ]; then case " $* " in *" $name "*) ;; *) continue ;; esac; fi
    set -f
    python3 tests/run_oracle.py "$rule" "$rle" $range $okv > "$T/o.txt" 2>&1
    ./regionspark --rule "$rule" --pattern "$rle" --trace --threads 1 $pargs > "$T/p.txt" 2>/dev/null
    set +f
    r=$(python3 tests/compare.py "$T/o.txt" "$T/p.txt")
    echo "$name: $r" | tr '\n' ' '; echo
    case "$r" in *IDENTICAL*) ;; *) fail=1 ;; esac
done < tests/cases.txt
rm -rf "$T"
[ $fail = 0 ] && echo "all identical" || { echo "DIFFERENCES"; exit 1; }
