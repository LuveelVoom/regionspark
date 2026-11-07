# regionspark

A standalone C++17 port of hotdogPi's one-spark oscillator search (ConwayLife.com forum, "Golly
scripts" page 12, post of July 6th 2021), for any INT (Hensel) rule without B0. MAP rules are accepted
too, but the search assumes symmetric patterns stay symmetric, so use only D8-symmetric MAP rules.

It places symmetric copies of an active region, hits them with a small spark, and reports when the
region comes back: a **partial** oscillator that needs sparkers to supply that spark every period.

## Build

    make            # OpenMP; on macOS it uses Homebrew g++ (brew install gcc)
    make nomp       # single-threaded, any C++17 compiler
    make test       # rule-table test and one oracle case (~20 s; needs tests/hotdogpi_jul6.py, see Tests)

## Running a search

    ./regionspark --rule B3/S23-q4i --pattern '2b3o$bo3bo$5bo$o2b2o$b2o!' --mode D8 > run.txt

- `--pattern` is the region to restore (RLE body, header optional), or `--pattern-file F`.
- `--mode` picks the symmetry: `C2` (default), `C4`, `D4`, `X4` (diagonal D4), `D8`, or `C1` (one copy).
  Run each mode you care about, and each again with `--rotate` to also accept a 90° turn.
- Each mode has a default offset range (`--x A:B --y A:B` to change it). The search covers every
  offset, so a full run per mode takes minutes to hours depending on the rule; `--threads N` uses
  N cores (output is the same for any N).
- Progress goes to stderr, results to stdout.

## Reading the output

Each find starts with a line like

    Found!: 11, 5, 45  [z=1 w=0 edge=4..4 spark=(-1,0) after=27 match=same T=72 -> period 72]

offset (x, y) and spark generation, then: `z` orientation index, `w` 0/1 (spark beside the lowest or
highest run of cells in the leftmost column), `edge` that run's rows, `spark` row offsets of the spark
cells, `after=N` generations until the box returns, and `match` (`same`, `flipped` or `rotated`).
The period is `gen + N` for `same` and twice that otherwise.

Five RLEs follow, all in one frame (same size and `#CXRLE Pos`), so they line up:

1. gen 0: all symmetric copies
2. gen `gen`, just before the spark
3. the spark cells alone (also listed as frame coordinates in a `#C` line)
4. [2] + [3]
5. [4] run `after` generations: inside the check box (in a `#C` line) it equals [1], or its mirror
   image or rotation; the cell count outside the box is given

Only the box is checked, so a find can leave debris outside it. A summary at the end groups finds
by offset and period.

## Turning finds into oscillators

A find needs a sparker that supplies spark [3] at generation `gen` of every period, and the region
must survive with nothing else hitting it. The scripts in `tools/` take a folder of runs this far:

    mkdir mysearch && echo '2b3o$bo3bo$5bo$o2b2o$b2o!' > mysearch/patterns.txt   # one region per line
    THREADS=8 sh tools/pipeline.sh mysearch obj library.rle B3/S23-q4i
    # arguments: folder, name prefix for the bundles, sparker library, rule

It runs every mode (with and without `--rotate`), re-simulates every find independently, and sorts
them into `clean/` (nothing outside the box), `debris/`, `unsparked/` (the region also returns with no
spark) and `natural_oscillators.txt` (the region oscillates by itself). Each clean find gets a
LifeViewer file (`lv/`) that replays it with the spark pasted in every period. Then
`divisor_report.py` checks which sparker periods could work (a spark repeated every p generations
must keep the cycle exact), and `fit_sparkers.py` tries every oscillator of a viable period in the
library as the sparker, in all orientations and phases. The library is one or more files, comma
separated: collection RLEs (oscillators are extracted from them) or drift `findings` oscillator lists. `MODES="C2 C4"` limits
the modes; `REGIONSPARK_ARGS` passes options to each run.

Other tools: `rank_viability.py` (ranks clean finds by viable periods and library coverage),
`make_vls_catalyst.py` (a vls catalyst-search input for one find), `combine_regions.py`,
`extract_oscillators.py`, `debris_pieces.py`, `check_unsparked.py`, `fix_rle_ws.py`.
They need Python 3 only.

## Changing the spark list

Each generation, the search takes the leftmost live column (rows y−40..y+39), keeps one contiguous
run of its cells (the bottom run for `w=0`, the top run for `w=1`), and tries each spark in the list
for that run's length. A spark is a list of **row offsets**: one cell per offset, in the column 2 left
of the run, with offset 0 = the run's top row (negative = above it). The symmetric copies for `--mode`
are added automatically, so list only the left-side cells.

`--sparks` replaces lists: `KEY:LIST` groups separated by `;`, where KEY is the run length `1`, `2`,
`3`, `4` (4 or more cells) or `*` (all four), and LIST is sparks separated by spaces, each a
comma-separated list of offsets. Lengths you don't mention keep the original list. The defaults
(the original script's lists) written this way:

    --sparks '1:-2,-1 -1,0 0,1 1,2;
              2:-1 0 2 -2,-1 -1,0 1,2 2,3;
              3:-1 0 1 2 3 -2,-1 -1,0 2,3 3,4;
              4:-1 0 1 2 3 4 -2,-1 -1,0 0,1 1,2 2,3 3,4 4,5'

(one line in practice; spaces and line breaks around `;` are fine inside the quotes). Examples:

    --sparks '*:0 0,2'               # beside every run: a single cell, or two cells with a gap
    --sparks '1:-2,-1 -1,0 0,1 1,2 -1,0,1'   # runs of 1: the original dominoes plus a 3-cell line

With `--sparks`, the run file's header gets a `# sparks:` line with the lists used, and each find's
`spark=(...)` field gives the offsets of the spark that worked. Notes:

- Order matters a little: a spark is skipped when its reaction at inner generations 5..8 matches a
  recent one, so earlier entries take precedence.
- Sparks are always one column wide, 2 columns left of the edge. Another column or a 2-D spark means
  changing `min_x - 2` in the per-mode placement code in `regionspark.cpp` (every mode has its own
  formula for the symmetric copies) and the C1/`--selfsym` branch.
- `tests/run_cases.sh` compares against the original script's lists, so don't use `--sparks` there.

## Options

| option | meaning | original script |
|---|---|---|
| `--rule R` | e.g. `B3/S23-q4i`, `b3s23-q4i`, `MAP...` | Golly's current rule |
| `--pattern RLE` / `--pattern-file F` | header line optional | `input_pattern` |
| `--mode`, `--a`, `--rotate` | as in the script (default C2, a=1, mirror) | `mode`, `a`, `rotate` |
| `--x A:B --y A:B` | offset ranges; defaults: C2 −20..20 both (May 2021 post), others as in the Jul 6 script | `start_x` ... |
| `--gens 500 --gens2 2000` | outer / inner generation limits | `range(500)`, `range(2000)` |
| `--alive 'x,y;...'` | cells that must stay alive | "block broken" lines (posted: `14,0;0,2;0,10`) |
| `--keep X0,Y0,W,DH` | spark only in rect [X0, Y0, W, y+height+DH] | `g.select([-50,14,100,y+height-17]); g.clear(1)` |
| `--resume X,Y` | skip x==X and y<Y | `if x == 1 and y < 26` |
| `--skip-negative` | skip x<0 and y<0 | same line |
| `--no-c4-diag` | turn off C4's diagonal bounding (use with catalysts) | C4 line |
| `--known 'x,y;...'` | warn "Already found" instead of reporting | `(x, y) == (1,26)` |
| `--stop` | exit at first find | default behaviour of the script |
| `--threads N` | OpenMP threads | — |
| `--mode C1` | one copy, one spark; the pattern's 8 orientations at offset 0,0 | — |
| `--selfsym` | C1 only: also place each spark at its images under the pattern's own symmetries | — |
| `--skip-period L` | drop finds whose period is a multiple of one in L (e.g. `24` when the region settles into a p24 by itself); can drop real partials of those periods | — |
| `--skip-unsparked` | drop finds whose box also returns with no spark | — |
| `--max-finds N` | at most N reported finds per offset | — |
| `--sparks SPEC` | replace the spark lists (see Changing the spark list) | the `sparks = [...]` lines |
| `--trace` | list each (x,y,z) searched and generations simulated | — |

The posted script has its catalyst settings switched on; the author says to switch them off for
searches without catalysts, so here they default to off.

## Differences from the original

* Finds don't stop the run unless `--stop` is given. After a find the inner loop ends and
  the snapshot list is kept.
* Golly's 32-bit `g.hash()` is replaced by exact box comparison and a 64-bit shape hash,
  so the original's (rare) hash-collision false finds and false prunes don't happen.
* B0 rules are rejected.

## Things the original does that are kept on purpose (they can lose results)

* The `generation_snapshots` pruning skips a spark when the shape at inner generations
  5..8 equals a recent one, even if the position differs.
* `if g.empty(): break` in the spark loop: if a spark run dies out, the remaining sparks
  for that edge are skipped.
* Only cells in rows y−40..y+39 count for the left edge.
* C4 with a non-square pattern: the diagonal test uses `width` before the width/height
  swap, so when it fails for some z the rotation is skipped. The pattern's orientation
  then drifts from one offset to the next, and some orientations are never tried at some
  offsets. So C4 results depend on where the x/y range starts. The port replays this
  serially; the offsets are then searched in parallel.

## Tests

- `tests/test_rule.py`: rule-table structure (letters partition each count, complements, `-`, B0 rejected).
- `tests/run_cases.sh [NAME...]`: runs hotdogPi's original script against a mock `golly` module
  (`tests/mock/golly.py`, its own simulator, semantics from Golly's source) and compares every visited
  offset, generation count and find with `regionspark --trace --threads 1` on the cases in
  `tests/cases.txt`. The original script isn't in this repo (it was posted without a license): save
  the Jul 6 2021 post's script as `tests/hotdogpi_jul6.py`. The oracle is slow (minutes per case).
- `tests/check_bundle.py RULE run.txt`: re-simulates every find in a run file independently.

Developer notes and the results of the original sessions: [DEVELOPMENT.md](DEVELOPMENT.md).
