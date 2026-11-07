# Extract oscillators from a collection RLE (any LifeHistory odd state = alive).
# Objects = groups of cells within Chebyshev distance 2 of each other (closer cells interact).
# Each object is simulated alone; kept if it returns to exactly its start (same position) with
# period >= 2 within MAXGEN. Labels drawn with dots die and are dropped; still lifes are
# reported separately; spaceships/puffers/unstable objects are dropped.
# Duplicates (same oscillator in another phase or orientation) are merged.
# usage: extract_oscillators.py RULE COLLECTION.rle OUT.txt [MAXGEN]
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests', 'mock'))
import golly as g
rule, src, out = sys.argv[1:4]; MAXGEN = int(sys.argv[4]) if len(sys.argv) > 4 else 1000
g.setrule(rule)
txt = open(src).read()
body = ''.join(l.strip() for l in txt.split('\n') if l.strip() and not l.lstrip().startswith(('#', 'x')))
# multistate RLE: '.'=0, 'A'..'X' = 1..24, also b/o
cells = set(); x = y = 0; n = ''
for ch in body:
    if ch.isdigit(): n += ch; continue
    k = int(n) if n else 1; n = ''
    if ch in '.b': x += k
    elif ch == 'o' or ('A' <= ch <= 'X'):
        st = 1 if ch == 'o' else ord(ch) - ord('A') + 1
        if st % 2 == 1:
            for _ in range(k): cells.add((x, y)); x += 1
        else: x += k
    elif ch == '$': y += k; x = 0
    elif ch == '!': break
# group cells (union-find over cells within distance 2)
parent = {c: c for c in cells}
def find(c):
    while parent[c] != c: parent[c] = parent[parent[c]]; c = parent[c]
    return c
for (cx, cy) in cells:
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            q = (cx + dx, cy + dy)
            if q in parent and q != (cx, cy):
                a, b = find((cx, cy)), find(q)
                if a != b: parent[a] = b
groups = {}
for c in cells: groups.setdefault(find(c), set()).add(c)
MATS = [(1, 0, 0, 1), (0, -1, 1, 0), (-1, 0, 0, -1), (0, 1, -1, 0), (-1, 0, 0, 1), (1, 0, 0, -1), (0, 1, 1, 0), (0, -1, -1, 0)]
def canon(cs):
    best = None
    for m in MATS:
        t = [(m[0] * a + m[1] * b, m[2] * a + m[3] * b) for a, b in cs]
        x0 = min(a for a, b in t); y0 = min(b for a, b in t)
        k = tuple(sorted((a - x0, b - y0) for a, b in t))
        if best is None or k < best: best = k
    return best
def rle(cs):
    x0 = min(a for a, b in cs); y0 = min(b for a, b in cs); w = max(a for a, b in cs) - x0 + 1; h = max(b for a, b in cs) - y0 + 1
    rows = []
    for yy in range(y0, y0 + h):
        r = ''.join('o' if (xx, yy) in cs else 'b' for xx in range(x0, x0 + w)).rstrip('b')
        rows.append(re.sub(r'(o+|b+)', lambda m: (str(len(m[0])) if len(m[0]) > 1 else '') + m[0][0], r))
    s = '$'.join(rows)
    s = re.sub(r'\$+', lambda m: (str(len(m[0])) if len(m[0]) > 1 else '') + '$', s)
    return w, h, s + '!'
stats = {'died': 0, 'still': 0, 'moving/unstable': 0, 'osc': 0, 'dup': 0}
oscs = []; seen = {}
for key, cs in sorted(groups.items(), key=lambda kv: (min(c[1] for c in kv[1]), min(c[0] for c in kv[1]))):
    g.new(''); [g.setcell(a, b, 1) for a, b in cs]
    start = set(cs); per = None; died = False
    for t in range(1, MAXGEN + 1):
        g.run(1)
        if not g._cells: died = True; break
        if g._cells == start: per = t; break
    if died: stats['died'] += 1; continue
    if per is None:
        # maybe a label or debris died off: look for a stationary cycle after a transient
        g.new(''); [g.setcell(a, b, 1) for a, b in cs]; hist = {}; cyc = None
        for t in range(MAXGEN + 1):
            fs = frozenset(g._cells)
            if not fs: break
            if fs in hist: cyc = (hist[fs], t - hist[fs], set(fs)); break
            hist[fs] = t; g.run(1)
        if cyc is None or cyc[1] == 1 and False:
            stats['moving/unstable'] += 1; continue
        if cyc[1] == 1: stats['still'] += 1; continue
        stats['settled'] = stats.get('settled', 0) + 1
        cs = cyc[2]; per = cyc[1]; start = set(cs)
    if per == 1: stats['still'] += 1; continue
    # canonical over all phases and orientations
    ph = [start]
    for _ in range(per - 1): ph.append(run_ := None) if False else None
    g.new(''); [g.setcell(a, b, 1) for a, b in cs]
    phases = []
    for _ in range(per): phases.append(set(g._cells)); g.run(1)
    c = min(canon(p) for p in phases)
    if c in seen: stats['dup'] += 1; continue
    seen[c] = True; stats['osc'] += 1
    x0 = min(a for a, b in cs); y0 = min(b for a, b in cs)
    oscs.append((per, len(cs), x0, y0, rle(cs)))
oscs.sort(key=lambda o: (o[0], o[1]))
with open(out, 'w') as f:
    for per, pop, x0, y0, (w, h, s) in oscs:
        f.write('p%d  %d cells  from collection at (%d,%d)\nx = %d, y = %d, rule = %s\n%s\n' % (per, pop, x0, y0, w, h, rule, s))
print('objects:', len(groups), stats)
from collections import Counter
print('oscillators by period:', sorted(Counter(o[0] for o in oscs).items()))
