# regionspark: notes for developers

Built in a claude.ai session (2026-11-02..04) as the program `onespark`, renamed to `regionspark`; run files
made before the rename still say `# onespark:` (nothing parses it). Those run files, bundles and LifeViewer
files are in the local `../results/` folder, not in this repo; `../results/...` paths below refer to it.

## Goal
- Port hotdogPi's Golly Python one-spark oscillator search (ConwayLife forum, "Golly scripts" page 12,
  post of July 6th 2021) to a standalone program for all INT (Hensel) rules, and run it on B3/S23-q4i.
- Then try to complete the partials (sparkers / catalysts) with drift findings and vls.

## Conventions (state these at every program boundary)
- Coordinates: Golly's, x right, y down. RLE `#CXRLE Pos=x,y` = absolute top-left cell.
- Rule index layout: Golly/MAP, row-major from NW, weights NW=256 N=128 NE=64 W=32 C=16 E=8 SW=4 S=2 SE=1.
  In `regionspark.cpp` the stepper uses RULE2 = same table with each row triple bit-reversed (bit0 = west).
- Hensel representatives copied from Golly `gollybase/liferules.cpp` (letters "ceaiknjqrytwz";
  5-7 neighbours = complement (xor 0x1ef) of 3-1). '-' = all letters of that count except those listed.
- Golly semantics reproduced (read from Golly source, gui-wx): `g.hash(rect)` is relative to rect
  top-left; `rotate` is about the selection centre (exact when w+h even, which is why the script
  skips odd w+h in rotate mode); `flip` about the selection centre; clipboard pastes at the
  selection's top-left; `getcells` is row-major (y, then x).
- RLE output: pattern data has NO whitespace (one line); whitespace only in comments (user rule).

## Build / run
    g++ -O2 -std=c++17 -fopenmp -o regionspark regionspark.cpp
    ./regionspark --rule B3/S23-q4i --pattern '2b3o$bo3bo$5bo$o2b2o$b2o!' --mode D8
See `regionspark/README.md` for every option and how it maps to the script's lines.

## Verification status (measured / verified unless marked)
- Oracle = the original script, run verbatim except configuration lines (`tests/run_oracle.py`)
  against a mock `golly` module written from Golly's source (`tests/mock/golly.py`, own set-based
  INT simulator). Compared single-threaded on: visited offsets, number of generations simulated per
  offset, and every find (x, y, gen, z, w, spark, after).
  IDENTICAL on: full C2 B3/S23-q4i (1627 offsets, 9.3M generations, 0 finds); Life C2 near the May
  example (227 finds); C4; C4 a=0; D4; X4; D8; D8 a=0; --rotate; --stop; the author's catalyst setup
  (--alive/--keep/--resume/--skip-negative/--known); catalyst with negative offsets.
- Rule table: structural tests (letters partition each count, complements, '-' semantics, B0
  rejected) in `tests/test_rule.py`. NOT compared against a running Golly (running Golly-built code
  was blocked in that session); representatives were read from Golly's source.
- Every reported find re-simulated independently from its RLEs (`tests/check_bundle.py`; the older
  `verify_find.py`, for a previous output format, is retired); top-10 run: 108/108 pass.
- ASan/UBSan clean on small runs. OpenMP output order is fixed (task order); --stop with 2 threads
  gives the same first find as 1 thread.
- LifeViewer files: checked against LifeViewer source (github.com/rowett/lifeviewer: PASTE offsets
  relative to main RLE top-left, PASTET applied right after the generation is computed, PAUSE holds a
  generation, THEME name case-insensitive) and by re-simulating the paste schedule. NOT run in
  LifeViewer (blocked).
- Untested: MAP rules in a search; the "#C NOTE: escaping glider deleted" bundle path (never
  triggered); macOS/clang build; speed on Apple silicon.

## Quirks of the original kept on purpose (they can lose results; documented in README)
- generation_snapshots pruning (shape at inner gens 5..8 seen recently -> skip, even if position differs).
- `if g.empty(): break` in the spark loop: if a spark run dies out, remaining sparks for that edge are skipped.
- Only rows y-40..y+39 count for the left edge.
- C4 with non-square patterns: the diagonal test uses width BEFORE the width/height swap, so skipped
  z iterations skip the rotation and the orientation drifts between offsets. The port replays this
  state machine serially, then searches offsets in parallel. Consequence: C4 results depend on the
  start of the x/y range. (First port version assumed identity per (x,y): found by the oracle.)

## Differences from the original (deliberate)
- 32-bit g.hash replaced by exact comparison (box) / 64-bit shape hash.
- Finds don't stop the run unless --stop; after a find the inner loop ends, snapshot list kept
  (earlier version reset it, giving many duplicate reports; changed).
- Author-specific catalyst settings are options, default off (author: switch off without catalysts).
- C2 default range -20..20 (May 2021 post); others as in the Jul 6 script.

## Results
### Your pattern 2b3o$bo3bo$5bo$o2b2o$b2o! (B3/S23-q4i, defaults)
- D8 offset (11,5) p72 clean (spark gen 45, 16 cells = 8 dominoes); C4 offset (-8,5) p156 clean
  (flipped, sparks gen 6 + mirror at 84); D4 offset (9,7) p56 with 72 debris cells. Others none.
### Top-10 active regions (user list): 108 finds, 10 distinct clean ones (objects 2 and 8), see
  `../results/out/top10/SUMMARY.txt`.

## Completion attempts (rejected ideas, with numbers)
- Ideal bodiless sparker test (spark repeated every p gens): viable p only:
  D8 p72 -> 24,36,72; C4 p156 -> 78,156; D4 p56 -> none (debris).
  top10: p63->21,63; p60->60; p49->7,49; p42->6,14,42; p27->9,27; p14->14; p11->11; p6->3,6.
- drift sparky p4 (findings/B3-S23-q4i/sparky.txt, 24 cells, free 1-cell spark at phase 2):
  C4 p156: copies collide (sparks 7 rows apart on a side); D8: needs domino; D4: 152-184 cells wrong.
- drift oscillators (findings/B3-S23-q4i/oscillators.txt) of viable periods as sparkers, all 8
  orientations x phases, covering a spark group, symmetric copies, overlap filter then 2-cycle sim
  (`tools/place_osc.py`): D8 p49 with 15 p7: 20832 placements, 301 simulated, 0; X4 p42 (x2) with
  39 p6 + 3 p14: 131256 each, 384 simulated, 0; D4 p27 with 5 p9: 7704, 351, 0; obj8 p14 (x2) with
  3 p14: 0 pass filter; C2 p11 with 1 p11: 1864, 242, 0; X4 p6 with 62 p3 + 39 p6: 0 pass filter
  (pattern 10x10, sparkers collide).
- vls catalyst search (lifeweb by speedydelete, `tools/make_vls_catalyst.py`): window on the left
  of the D8 p72 find; pattern cells fixed to the known cycle at every gen; far window edges
  dont_care; catalyst zone unknown; `wrap 0 0` over 72 gens. Sanity: empty zone + no spark ->
  solvable; empty zone + spark -> contradiction exactly at the domino at gen 44.
  * zone x -27..-22, rows -12..11, still life gens 0..37 and 66..71 (exact: pattern first touches
    x=-21 at gen 38): 9822 unknowns, exhausted in 15 s, 0 solutions.
  * + never-visited cells x -21..-18 reached after gen 24, per-cell still windows: 10252 unknowns,
    exhausted in 25 s, 0 solutions.
  * stalled (progress all zeros, stopped): every cell free all 72 gens (18960 unknowns); zone to
    x -32 full height; never-visited cells near the pattern from gen 1 (13076 unknowns).
  User heuristic: if the progress string has no 1 in its first 6-7 digits after ~1 s, something is
  wrong; ~19000 unknowns is too many.
- vls run from TS source: esbuild bundle (`lib/vls/index.js`) with `@babel/parser` replaced by a
  small expression parser shim and `@babel/types` by an empty module (types only). Local one-line
  fix in vls `src/vls/compiler.ts` generationOrRange: accept '-' as well as 'to' (boundStateSpecifier
  matches '0-37:' but the range parser only knew 'to'). Not pushed (third-party repo).
- vls -s D2-/D2v implementation reassigns a local `grid` variable: looks broken, not used.

## Later sessions (2026-11-04)
### Pipeline (tools/pipeline.sh DIR PREFIX LIBRARY [RULE], env REGIONSPARK_ARGS)
regionspark all modes (mirror + rotate) -> summarize.py (independent re-simulation of every bundle,
debris count) -> clean_bundles.py -> make_lifeviewer.py -> divisor_report.py -> fit_sparkers.py
(period-filtered and --all-divisors). clean_bundles.py sorts finds into:
- clean/  : box returns, nothing outside;
- debris/ : box returns, debris outside (debris count in the file name; candidates for clean-up);
- natural_oscillators.txt : the starting configuration oscillates by itself (no spark needed);
- skipped : debris finds whose box returns the same way with no spark (spark irrelevant).
### Sparker fitting
- extract_oscillators.py: collection RLE -> objects (cells within distance 2) -> stationary
  oscillators (labels die; objects that settle into an oscillator keep the cycle; dedup over
  phases/orientations). User collection: 821 objects -> 172 oscillators (p2..p16, p29, p36, p60).
- place_osc.py speed-ups (results unchanged on compared cases): anchor only rotor cells (stator
  cells are lit every generation, and period 1 is never viable); exact pre-test of the
  representative copy against the pattern (symmetric copies map onto it).
- divisor_report.py: per divisor p of the find's period, does a spark repeated every p gens keep
  the cycle exact ("ok", "ok but path differs", "FAILS at gen g after the extra spark at gen h").
  Periods not dividing the find period cannot work (some cycles would miss the spark).
- --all-divisors: every library period dividing the find period, ignoring the bodiless test:
  20 clean finds, 553894 placements, 1038 simulated 2 cycles, 0 completions.
### Results
- 3o$o$3o! = top-10 object 2 one generation later (same partials, translated, spark 1 gen earlier);
  new clean: C2 rotated p52 at (6,+-10) (viable sparker periods 26, 52).
- b2o$o2bo$3o!: 32 finds; clean p36 (C2 rot), p24 (X4), p21 (D4), p18, p16 (C2 flipped), p14 (D8, X4).
- four regions + o2bo$o2bo$o2bo!: 497 finds; clean p104 (obj4 C2), p76 x2 (obj2 D4 rot; viable
  4,19,38,76; 11422 placements each, 0), p28, p22 x2. NATURAL p36 oscillator (10-26 cells):
x = 9, y = 7, rule = B3/S23-q4i
o$3o$bo2$7bo$6b3o$8bo!
  two copies of bo$3o$2bo! (each dies alone); not in the user collection or drift findings
  (all phases/orientations compared); whether known elsewhere: unknown.
- B36/S23-e7, $b2o$obo$b2o!: the region settles into a p24 oscillator by itself, so every spark
  "returns" at p24 or a multiple (345884 such finds in C2 before it was stopped). regionspark now has
  --skip-period 24 (drops periods that are multiples of 24; opt-in, can drop real p48/p72 partials).
- The top-10 SUMMARY said "none of that period" for obj8 C4 p60; drift's list does have a p60.
  Both p60s (drift 236 cells, collection 238 cells) were tried: 57088 placements, 0.
- B36/S23-e7 result (stopped after C2, C2 rotate, C4, C4 rotate at the user's request; D4/X4/D8 not run):
  with --skip-period 24, C2 gave 779 finds (all verified): 2 clean p46 at (13,-2) and (13,0)
  (viable sparker periods 23, 46: none in drift HighLife list or q4i library), 589 with debris
  (bundles + LifeViewer files in ../results/e7/debris, ../results/e7/lv_debris), 1 spark-irrelevant find skipped.
- Spark-free finds with debris (clean_bundles.py -> unsparked/, LifeViewer lv_unsparked/):
  q4i 3o$o$3o! D8 (8,3): core returns exactly at gen 54 and emits 8 copies of the seed
  3o$o$3o! (seed emitter; debris then wrecks the next cycle). e7 C2 (-8,-1): returns at 123 with
  4 active 21-cell pieces. Both return once only. See ../results/out/spark_free_with_debris.txt.
- rank_viability.py: ranks clean partials (viable sparker periods, library coverage, spark cells/
  groups, clearance, period). ../results/out/viability_ranking_*.txt. Clearance is weakly discriminating.
### regionspark options added (all off by default; default output re-checked identical on D8/C4)
--skip-period L, --skip-unsparked, --max-finds N.
### Other scripts
combine_regions.py (all regions into one RLE per rule, duplicates merged). make_package.py (wrote the
single-file package; kept in ../results/notes/).

## B2i3/S23-c (2026-11-04)
- Regions from transcensus (LuveelVoom/life-misc/transcensus, built with gcc here):
  transcensus-int -r B2i3/S23-c -n 100000 -t 20 -j 2 -l census_list.txt (15 s; 100000 of 558999
  soups settled; 386 precursors seen >= 20 times). Top 7 used (user: big drop after #7, 1160 -> 538):
  2o$o2bo$obo! (6207), b2o$2o$bo! (5459), 2bo$bobo$2ob2o! (4121), 3o$o2bo$ob2o! (1910),
  3bo$bobo$o$2o! (1856), 3bo$o2bo$o2bo$bo! (1359), bo$o$o3bo$b3o! (1160).
- regionspark C2 and C4 only (mirror + rotate; object 1 also has D4/D4 rot/X4 from before the switch),
  --gens 167 --gens2 667 (one third of the defaults), --max-finds 200. No sparker fitting (user:
  not for other rules).
- 106 finds (all verified): 12 clean (10 distinct; C4 rotate duplicates C4), 94 debris, no natural
  or spark-free ones. Ranking (comeback, then period factors) in ../results/out/viability_ranking_b2i.txt;
  top: obj3 C4 p126 at (-8,6)/(3,6) (comeback 2, factors 2,3,6,7,9,14,18,21,42,63), obj4 C4 p24 at
  (3,4) (comeback 2; same offset also p23 and p25), obj2 C2 p146.
- Pipeline: MODES env (default all five), finished runs are kept on restart.

## C1 and --selfsym (2026-11-04)
- --mode C1 (extension): one copy, one spark, the pattern's distinct orientations, offset 0,0.
  --selfsym: also place each spark's images under the pattern's own symmetries (symmetric sparks).
- Checked against the original script with a C1 branch (and the same selfsym code) added in
  tests/run_oracle.py, orientation by orientation (tests/compare_c1.py): identical finds and
  generation counts on q4i 3o$obo$b2o!, e7 $b2o$obo$b2o! (1871 finds plain, 1745 with --selfsym),
  and with --selfsym on boo$oo$boo!, bo$3o$bo!, 3o$obo$b2o!, o2bo$o2bo$o2bo!, b2i 2bo$bobo$2ob2o!.
- Runs on all regions (C1 plain: 18 q4i, 1 e7 with --skip-period 24, 7 b2i; --selfsym: the 9
  symmetric regions): clean only in e7: C1 p44 (comeback 2), --selfsym p44 (1) and p12 (never).
  q4i and b2i: debris finds only.

## Open items / next steps
- vls catalyst search for top10 D4 p63, C4 p60, D8 p49 (keep unknowns ~10k, 10-min cap).
- C4 flipped/rotated finds need a 2-half-cycle generator in make_vls_catalyst.py (only 'same' supported).
- drift survey for new q4i sparkers of period 7/9/14/21/60 (python-sat needed for finish.py; PyPI
  was unreachable in the session).
- Sparky oscillators: none found or searched for (user asks to report them with catalyst results).

## Sources
Golly source (github.com/AlephAlpha/golly mirror): liferules.cpp, wxscript.cpp (GSF_hash),
wxselect.cpp (Rotate/Flip/clipboard). LifeViewer source (github.com/rowett/lifeviewer): parser.js,
lifeview.js. drift (github.com/LuveelVoom/drift) findings. lifeweb/vls (github.com/speedydelete/lifeweb).


## Checked on macOS (2026-11-07, M4 Pro, Homebrew g++-16)
- Builds without warnings (`-Wall`); `make` picks Homebrew g++ on macOS.
- Rule tables: `--dump-rule` equals casim (an independent Golly-compatible simulator) on 2000 rules:
  random INT rules in several spellings, plus random isotropic and non-isotropic MAP rules.
- Oracle comparison `tests/run_cases.sh`, single-threaded: c4, c4a0, d4, x4 and stop IDENTICAL; d8, d8a0,
  rot, cat and catneg were still running at the first push (the original session had all ten identical).
- D8 q4i known find (offset 11,5, p72) reproduced; `tests/check_bundle.py` passes on it.
