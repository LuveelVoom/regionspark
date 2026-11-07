# Complete regionspark partials with known oscillators used as sparkers.
# usage: place_osc.py RULE OSC_FILE PERIODS BUNDLE...   (PERIODS like 3,6 or "auto")
# For each oscillator of an allowed period, orientation and phase, the oscillator is placed so
# that its cells at the spark generation cover one spark group; copies go wherever the
# pattern's symmetries send that group. Candidates whose cells ever coincide with the
# pattern's are dropped; the rest are simulated for 2 cycles and kept if exactly periodic.
import sys, os, re, itertools, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests', 'mock'))
import golly as g

rule, oscfile, periods = sys.argv[1], sys.argv[2], sys.argv[3]
g.setrule(rule)
def run(c, n): g.new(''); [g.setcell(x, y, 1) for x, y in c]; g.run(n); return set(g._cells)
MATS = [(1, 0, 0, 1), (0, -1, 1, 0), (-1, 0, 0, -1), (0, 1, -1, 0), (-1, 0, 0, 1), (1, 0, 0, -1), (0, 1, 1, 0), (0, -1, -1, 0)]
def ap(m, p): return (m[0] * p[0] + m[1] * p[1], m[2] * p[0] + m[3] * p[1])

# oscillator library: (name, period, phases)
lib = []
txt = open(oscfile).read().split('\n')
for i, l in enumerate(txt):
    m = re.match(r'p(\d+)\s', l)
    if m and i + 2 < len(txt) and txt[i + 1].startswith('x ='):
        body = ''; j = i + 2
        while '!' not in body: body += txt[j]; j += 1
        c = g.parse(body); S0 = {(c[k], c[k + 1]) for k in range(0, len(c), 2)}
        q = int(m[1]); ph = [S0]
        for _ in range(q - 1): ph.append(run(ph[-1], 1))
        if run(ph[-1], 1) != S0: continue
        lib.append(('#%d %s' % (len(lib) + 1, ' '.join(l.split()[:3])), q, ph))

def load(f):
    L = open(f).read().split('\n'); i = [k for k, l in enumerate(L) if l.startswith('Found')][0]; l = L[i]
    G = int(l.split(':')[1].split('[')[0].split(',')[2]); N = int(re.search(r'after=(\d+)', l)[1]); kind = re.search(r'match=(\w+)', l)[1]
    k = i + 1
    while not L[k].startswith('#C [1]'): k += 1
    R = []
    for _ in range(5):
        p = re.match(r'#CXRLE Pos=(-?\d+),(-?\d+)', L[k + 1]); j = k + 3; b = ''
        while '!' not in b: b += L[j]; j += 1
        c = g.parse(b); R.append({(c[q] + int(p[1]), c[q + 1] + int(p[2])) for q in range(0, len(c), 2)}); k = j
    return G, N, kind, R

def components(cells):
    cells = set(cells); out = []
    while cells:
        st = [cells.pop()]; comp = set(st)
        while st:
            x, y = st.pop()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (x + dx, y + dy)
                    if q in cells: cells.remove(q); comp.add(q); st.append(q)
        out.append(comp)
    return out

for f in sys.argv[4:]:
    G, N, kind, (one, two, three, four, five) = load(f)
    T = G + N; P = T if kind == 'same' else 2 * T
    xs = [x for x, y in one]; ys = [y for x, y in one]
    cx2, cy2 = min(xs) + max(xs), min(ys) + max(ys)
    def about(m, p):
        X, Y = 2 * p[0] - cx2, 2 * p[1] - cy2; X, Y = ap(m, (X, Y)); return ((X + cx2) // 2, (Y + cy2) // 2)
    if kind == 'rotated':
        left, top, right, bottom = min(xs) - 1, min(ys) - 1, max(xs) + 1, max(ys) + 1
        midy = top + (bottom - top) // 2; midx = left + (right - left) // 2
        nl = midx + top - midy; nb = midy + right - midx
        half = lambda cs: {(nl + (y - top), nb - (x - left)) for x, y in cs}
    else:
        half = lambda cs: {about(MATS[4], p) for p in cs}
    req = [(c, G) for c in components(three)]
    if kind != 'same': req += [(c, G + T) for c in components(half(three))]
    # pattern history over one cycle (with its sparks)
    H = []; g.new(''); [g.setcell(x, y, 1) for x, y in one]
    if G == 0: [g.setcell(x, y, 1) for x, y in three]
    for t in range(P):
        H.append(set(g._cells)); g.run(1)
        for s, cs in [(G, three)] + ([(G + T, half(three))] if kind != 'same' else []):
            if (t + 1) % P == s % P: [g.setcell(x, y, 1) for x, y in cs]
    allowed = None if periods == 'auto' else set(int(v) for v in periods.split(','))
    syms = [m for m in MATS if {about(m, p) for p in one} == one]
    # symmetry maps taking the representative group to each group (respecting timing)
    C0, t0 = req[0]
    maps = []
    for (C, t) in req:
        cand = [m for m in MATS if {about(m, p) for p in C0} == C and
                (({about(m, p) for p in three} == three) if t == t0 else ({about(m, p) for p in three} == half(three)))]
        if not cand: maps = None; break
        maps.append((cand[0], t))
    print('==', os.path.basename(f), 'p%d %s, %d spark groups, %d oscillators to try' % (P, kind, len(req), sum(1 for o in lib if P % o[1] == 0 and (allowed is None or o[1] in allowed))))
    if maps is None: print('   spark groups are not one symmetry orbit; skipped'); continue
    found = 0; tried = 0; simulated = 0
    for name, q, ph in lib:
        if P % q or (allowed is not None and q not in allowed): continue
        for o in MATS:
            oph = [{ap(o, p) for p in s} for s in ph]
            # a spark cell must be a rotor cell: a stator cell is lit every generation, which no
            # find tolerates unless period 1 is allowed (it never was in the viable-period test)
            stator = set.intersection(*oph) if not (allowed and 1 in allowed) else set()
            c0 = next(iter(C0))
            for phi in range(q):            # oscillator phase at generation t0
                cells = oph[phi]
                for anchor in cells - stator:
                    d = (c0[0] - anchor[0], c0[1] - anchor[1])
                    if any((x - d[0], y - d[1]) not in cells for x, y in C0): continue
                    # quick exact pre-test on the representative copy alone (symmetric copies of the
                    # pattern map onto it, so if it overlaps the pattern so do they)
                    rep_bad = False
                    for t in range(P):
                        own = (three if t == G else set()) | (half(three) if kind != 'same' and t == G + T else set())
                        ph_t = oph[(phi + t - t0) % q]
                        if any((x + d[0], y + d[1]) in H[t] and (x + d[0], y + d[1]) not in own for x, y in ph_t):
                            rep_bad = True; break
                    if rep_bad: tried += 1; continue
                    # all copies, as cell sets per generation (phase at gen t = phi + t - t_copy)
                    copies = []
                    for m, t in maps:
                        base = [{about(m, (x + d[0], y + d[1])) for x, y in s} for s in oph]
                        copies.append((base, t))
                    def at(t):
                        out = set()
                        for base, tc in copies: out |= base[(phi + t - tc) % q]
                        return out
                    tried += 1
                    # cheap filter: never on top of the pattern, copies never overlap
                    bad = False
                    for t in range(P):
                        st = [base[(phi + t - tc) % q] for base, tc in copies]
                        if any(a & b for a, b in itertools.combinations(st, 2)): bad = True; break
                        own = (three if t == G else set()) | (half(three) if kind != 'same' and t == G + T else set())
                        if at(t) & (H[t] - own): bad = True; break
                    if bad: continue
                    start = H[0] | at(0); simulated += 1
                    if run(start, P) == start and run(start, 2 * P) == start:
                        found += 1
                        fn = os.path.splitext(f)[0] + '_osc%d.rle' % found
                        xs2 = [x for x, y in start]; ys2 = [y for x, y in start]
                        x0, y0 = min(xs2), min(ys2)
                        rows = []
                        for y in range(y0, max(ys2) + 1):
                            rows.append(''.join('o' if (x, y) in start else 'b' for x in range(x0, max(xs2) + 1)).rstrip('b'))
                        open(fn, 'w').write('#C %s completed with %s, orientation %d, phase %d: period %d oscillator\nx = %d, y = %d, rule = %s\n%s!\n' %
                                            (os.path.basename(f), name, MATS.index(o), phi, P, max(xs2) - x0 + 1, max(ys2) - y0 + 1, rule, '$'.join(rows)))
                        print('   FOUND p%d oscillator using %s (orientation %d, phase %d) -> %s' % (P, name, MATS.index(o), phi, fn))
    print('   %d placements, %d passed the overlap filter and were simulated, %d oscillators found' % (tried, simulated, found))
