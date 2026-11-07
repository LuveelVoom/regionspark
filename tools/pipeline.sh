#!/bin/bash
# Full pipeline for a list of patterns (one RLE body per line in patterns.txt, run in DIR):
# regionspark (all modes, mirror + rotate) -> independent check + summary -> clean bundles ->
# LifeViewer files -> sparker fitting (period-filtered and all divisors).
# usage: pipeline.sh DIR PREFIX OSC_LIBRARY [RULE]   env: REGIONSPARK_ARGS, MODES (default "C2 C4 D4 X4 D8"), THREADS (default 2)
T=$(cd "$(dirname "$0")" && pwd); BIN="$T/../regionspark"
[ -x "$BIN" ] || { echo "build regionspark first (make)"; exit 1; }
DIR=$1; PREFIX=$2; LIB=$3; RULE=${4:-B3/S23-q4i}
export RULE
cd "$DIR" || exit 1; mkdir -p runs lv
n=0
while read -r p; do
  n=$((n+1))
  for m in ${MODES:-C2 C4 D4 X4 D8}; do for r in "" "--rotate"; do f=runs/obj${n}_${m}${r:+_rot}.txt
    if [ -f $f ] && grep -q "^# done" $f; then echo "obj$n $m${r:+ rot}: kept earlier run"; continue; fi
    "$BIN" --rule $RULE --pattern "$p" --mode $m $r --threads ${THREADS:-2} $REGIONSPARK_ARGS > $f 2>/dev/null
    echo "obj$n $m${r:+ rot}: $(grep -c '^Found' $f) finds, $(grep -c '# summary' $f) distinct"; done; done
done < patterns.txt
python3 "$T/summarize.py" > summary_raw.txt; head -1 summary_raw.txt
python3 "$T/clean_bundles.py" $PREFIX
[ -f natural_oscillators.txt ] && cat natural_oscillators.txt
for f in clean/*.txt; do python3 "$T/make_lifeviewer.py" $RULE $f lv | tail -1; done
mkdir -p lv_unsparked; for f in unsparked/*.txt; do [ -f "$f" ] && python3 "$T/make_lifeviewer_plain.py" $RULE $f lv_unsparked > /dev/null; done
mkdir -p lv_debris; for f in debris/*.txt; do [ -f "$f" ] && python3 "$T/make_lifeviewer.py" $RULE $f lv_debris > /dev/null; done; echo "debris finds: $(ls debris 2>/dev/null | wc -l)"
python3 "$T/fit_sparkers.py" $RULE fit_viable --osc "$LIB" clean/*.txt > fit_viable.log 2>&1
python3 "$T/fit_sparkers.py" $RULE fit_alldiv --osc "$LIB" clean/*.txt --all-divisors > fit_alldiv.log 2>&1
python3 "$T/divisor_report.py" $RULE clean/*.txt > divisor_report.txt
grep -h FOUND fit_viable.log fit_alldiv.log | sort -u; echo PIPELINE DONE
