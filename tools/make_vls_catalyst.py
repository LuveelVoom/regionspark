# Build a VLS input file: find a catalyst/sparker beside a regionspark partial.
# Window [x0,x1]x[y0,y1] (absolute coords of the find). Cells with x <= catx are the
# catalyst zone (unknown); all other cells follow the known cycle H(t) exactly; the
# outer ring of the pattern zone (right/top/bottom edges) is dont_care so the
# window boundary doesn't force wrong transitions. wrap 0 0 over the period.
# usage: make_vls_catalyst.py RULE BUNDLE x0 x1 y0 y1 catx OUT [--nospark] [--emptycat]
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests', 'mock'))
import golly as g
rule, f = sys.argv[1], sys.argv[2]
x0, x1, y0, y1, catx = map(int, sys.argv[3:8]); out = sys.argv[8]
nospark = '--nospark' in sys.argv; emptycat = '--emptycat' in sys.argv; nowrap = '--nowrap' in sys.argv
caty = None
stable = None
if '--stable' in sys.argv:
    a = sys.argv.index('--stable'); stable = (int(sys.argv[a + 1]), int(sys.argv[a + 2]))  # still life for gens 0..A and B..P-1
if '--caty' in sys.argv:
    a = sys.argv.index('--caty'); caty = (int(sys.argv[a + 1]), int(sys.argv[a + 2]))
g.setrule(rule)
L = open(f).read().split('\n'); i = [k for k, l in enumerate(L) if l.startswith('Found')][0]
l = L[i]; G = int(l.split(':')[1].split('[')[0].split(',')[2]); N = int(re.search(r'after=(\d+)', l)[1])
assert re.search(r'match=same', l), 'only "same" finds supported here'
k = i + 1
while not L[k].startswith('#C [1]'): k += 1
R = []
for _ in range(5):
    p = re.match(r'#CXRLE Pos=(-?\d+),(-?\d+)', L[k + 1]); j = k + 3; b = ''
    while '!' not in b: b += L[j]; j += 1
    c = g.parse(b); R.append({(c[q] + int(p[1]), c[q + 1] + int(p[2])) for q in range(0, len(c), 2)}); k = j
one, two, three, four, five = R
P = G + N
H = []
g.new(''); [g.setcell(x, y, 1) for x, y in one]
for t in range(P):
    if t == G and not nospark: [g.setcell(x, y, 1) for x, y in three]
    H.append(set(g._cells)); g.run(1)
if not nospark: assert set(g._cells) == one, 'cycle does not return'
W, Ht = x1 - x0 + 1, y1 - y0 + 1
never = None
mint0 = int(sys.argv[sys.argv.index('--mint0') + 1]) if '--mint0' in sys.argv else 0
if '--never' in sys.argv: never = int(sys.argv[sys.argv.index('--never') + 1])
everon = set().union(*H)
def inzone(x, y):
    if x > x1 - 1 or y <= y0 or y >= y1: return False if x > catx else (not caty or caty[0] <= y <= caty[1])
    if x <= catx: return not caty or caty[0] <= y <= caty[1]
    if not (never is not None and x <= never and (x, y) not in everon and (not caty or caty[0] <= y <= caty[1])): return False
    if mint0:  # skip never-visited cells the pattern comes near too early
        for t in range(mint0):
            if any((x + dx, y + dy) in H[t] for dx in range(-3, 4) for dy in range(-3, 4)): return False
    return True
if stable and stable[0] < 0:  # auto: still until a pattern-zone cell bordering the zone changes
    border = {(x + dx, y + dy) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1) if inzone(x, y)
              for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    border = {c for c in border if x0 <= c[0] <= x1 and y0 <= c[1] <= y1 and not inzone(*c)}
    t0 = next(t for t in range(P) if any((c in H[t]) != (c in H[0]) for c in border))
    stable = (t0 - 1, stable[1])
    print('auto: catalyst still for gens 0..%d' % (t0 - 1))
def ring(x, y): return x > catx and not inzone(x, y) and (x == x1 or y == y0 or y == y1)
def rle(rows):
    return 'x = %d, y = %d, rule = %s\n' % (W, Ht, rule) + '$\n'.join(''.join(r) for r in rows) + '!'
lines = ['pattern %dx%d %d gens' % (W, Ht, P), '7 = nop', '8 = all: dont_care', '9 = all: off'] + (['10 = 0 - %d: p1, %d - %d: p1' % (stable[0], stable[1], P - 1)] if stable else []) + ([] if nowrap else ['wrap 0 0'])
# ring (and empty catalyst zone if requested) for all gens
rows = []
for y in range(y0, y1 + 1):
    r = ''
    for x in range(x0, x1 + 1):
        if ring(x, y): r += 'H'          # state 8
        elif inzone(x, y) and emptycat and not (x == x0 and y == y0): r += 'I'  # state 9 (corner left unknown: vls needs >= 1 unknown)
        elif x <= catx and not inzone(x, y): r += 'I'  # catalyst side outside the zone: empty
        else: r += 'G'                    # state 7 (nop)
    rows.append(r)
lines += ['all gens:', rle(rows)]
percell = '--percell' in sys.argv
def t0_of(x, y):
    if x <= catx: return stable[0] + 1
    for t in range(P):  # heuristic: still until a pattern cell comes within 3
        if any((x + dx, y + dy) in H[t] for dx in range(-3, 4) for dy in range(-3, 4)): return max(1, (t // 4) * 4)
    return stable[0] + 1
if stable and percell:
    buckets = sorted({t0_of(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1) if inzone(x, y)})
    assert len(buckets) <= 15, buckets
    letter = {}
    for n, t0 in enumerate(buckets):
        st = 10 + n; letter[t0] = chr(ord('A') + st - 1)
        lines.append('%d = 0 - %d: p1, %d - %d: p1' % (st, t0 - 1, stable[1], P - 1))
    print('per-cell still windows (gens 0..t0-1), t0 values:', buckets)
    rows = []
    for y in range(y0, y1 + 1):
        rows.append(''.join(letter[t0_of(x, y)] if inzone(x, y) else 'G' for x in range(x0, x1 + 1)))
    lines += ['gen 0:', rle(rows)]
elif stable:  # catalyst zone cells: one variable over the still-life generations
    rows = []
    for y in range(y0, y1 + 1):
        r = ''
        for x in range(x0, x1 + 1):
            incat = inzone(x, y)
            r += 'J' if incat else 'G'
        rows.append(r)
    lines += ['gen 0:', rle(rows)]
for t in range(P):
    rows = []
    for y in range(y0, y1 + 1):
        r = ''
        for x in range(x0, x1 + 1):
            if inzone(x, y) or ring(x, y) or x <= catx: r += 'G'
            else: r += 'A' if (x, y) in H[t] else '.'
        rows.append(r)
    lines += ['gen %d:' % t, rle(rows)]
open(out, 'w').write('\n'.join(lines) + '\n')
print('wrote', out, 'window %dx%d, %d gens, spark gen %d' % (W, Ht, P, G))
