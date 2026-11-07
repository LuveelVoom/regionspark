# Try to complete a regionspark partial with copies of a known sparker.
# usage: python3 place_sparkers.py RULE BUNDLE_FILE SPARKER_RLE [extra-shift]
# For a representative spark cell and each of the 8 orientations of the sparker,
# copies are placed by the symmetries of the starting pattern, phased so each spark
# appears at the required generation; the whole thing is simulated for 3 periods.
import sys, os, re, itertools
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests', 'mock'))
import golly as g

rule, infile, sparker_rle = sys.argv[1:4]
extra = int(sys.argv[4]) if len(sys.argv) > 4 else 0  # extra distance to back the sparker off (unused if 0)
g.setrule(rule)

def run(cells, n):
    g.new(''); [g.setcell(x, y, 1) for x, y in cells]; g.run(n); return set(g._cells)

# sparker phases and its spark
cl = g.parse(sparker_rle); S0 = {(cl[i], cl[i + 1]) for i in range(0, len(cl), 2)}
phases = [S0]
for _ in range(64):
    phases.append(run(phases[-1], 1))
    if phases[-1] == S0: break
SP = len(phases) - 1
phases = phases[:SP]
spark = None
for k, c in enumerate(phases):
    for p in c:
        if not any((p[0] + dx, p[1] + dy) in c for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy):
            spark = (k, p)
assert spark, 'no isolated spark cell found'
sk, sc = spark
print('sparker period', SP, 'spark at phase', sk, 'cell', sc)

L = open(infile).read().split('\n')
def rle_at(i):
    p = re.match(r'#CXRLE Pos=(-?\d+),(-?\d+)', L[i + 1]); j = i + 3; b = ''
    while '!' not in b: b += L[j]; j += 1
    c = g.parse(b); return {(c[k] + int(p[1]), c[k + 1] + int(p[2])) for k in range(0, len(c), 2)}, j

# 8 orientations of the plane (matrices)
MATS = [(1, 0, 0, 1), (0, -1, 1, 0), (-1, 0, 0, -1), (0, 1, -1, 0), (-1, 0, 0, 1), (1, 0, 0, -1), (0, 1, 1, 0), (0, -1, -1, 0)]
def apply(m, p): return (m[0] * p[0] + m[1] * p[1], m[2] * p[0] + m[3] * p[1])

for i, l in enumerate(L):
    if not l.startswith('Found'): continue
    G = int(l.split(':')[1].split('[')[0].split(',')[2]); N = int(re.search(r'after=(\d+)', l)[1])
    kind = re.search(r'match=(\w+)', l)[1]
    k = i + 1
    while not L[k].startswith('#C [1]'): k += 1
    R = []
    for _ in range(5): c, k = rle_at(k); R.append(c)
    one, two, three, four, five = R
    T = G + N
    xs = [x for x, y in one]; ys = [y for x, y in one]
    cx2, cy2 = min(xs) + max(xs), min(ys) + max(ys)          # doubled centre
    def about(m, p):  # orientation m about the pattern centre (doubled arithmetic)
        X, Y = 2 * p[0] - cx2, 2 * p[1] - cy2
        X, Y = apply(m, (X, Y)); return ((X + cx2) // 2, (Y + cy2) // 2)
    mirror = lambda cs: {about(MATS[4], p) for p in cs}
    req = [(c, G) for c in three]
    if kind != 'same': req += [(c, G + T) for c in mirror(three)]
    P = T if kind == 'same' else 2 * T
    if P % SP: print(l[:60], ': period', P, 'not a multiple of sparker period'); continue
    syms = [m for m in MATS if {about(m, p) for p in one} == one]
    print(l[:75]); print('  period', P, 'spark cells', len(req), 'pattern symmetries', len(syms))
    c0, t0 = req[0]
    results = []
    for o in MATS:
        # sparker placement for c0: oriented phase-sk image translated so its spark lands on c0
        def placed(m_sym, cell, t):
            # orientation for this copy = m_sym composed with o
            img = {apply(o, p) for p in phases[0]}
            s_o = apply(o, sc)
            # translate so that the spark cell (in orientation o) sits on c0, then map by m_sym about centre
            dx, dy = c0[0] - s_o[0], c0[1] - s_o[1]
            base_phase0 = {(p[0] + dx, p[1] + dy) for p in img}
            cells0 = {about(m_sym, p) for p in base_phase0}
            # phase: the spark (phase sk) must appear at generation t: start in phase (sk - t) mod SP
            start = (sk - t) % SP
            return run(cells0, start) if start else cells0
        copies = []; ok = True; used = set()
        for (c, t) in req:
            # find a symmetry (or mirror-symmetry for second-half sparks) taking c0 to c
            cands = [m for m in MATS if about(m, c0) == c and ({about(m, p) for p in three} == three if t == t0 else {about(m, p) for p in three} == mirror(three))]
            if not cands: ok = False; break
            # the orientation applies to the evolved sparker, so phase-evolve after mapping
            copies.append(placed(cands[0], c, t))
        if not ok: print('  orientation', MATS.index(o), ': spark cells are not one symmetry orbit'); continue
        allspk = set().union(*copies)
        if any(len(a & b) for a, b in itertools.combinations(copies, 2)) or (allspk & one):
            results.append((MATS.index(o), 'overlap')); continue
        start = one | allspk
        st = start; okp = True
        for cyc in range(3):
            st = run(st, P)
            if st != start: okp = False; break
        if okp:
            results.append((MATS.index(o), 'OSCILLATOR p%d' % P))
            fn = 'osc_%s_p%d_o%d.rle' % (os.path.basename(infile).split('.')[0], P, MATS.index(o))
            xs = [x for x, y in start]; ys = [y for x, y in start]
            open(fn, 'w').write(str(sorted(start)))
        else:
            diff = len(st ^ start)
            results.append((MATS.index(o), 'fails (%d cells differ after a period)' % diff))
    for r in results: print('  orientation', r[0], ':', r[1])
