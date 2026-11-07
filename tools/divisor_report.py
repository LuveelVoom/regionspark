# For each find and each divisor p of its period: repeat the spark every p generations (no sparker
# body) and report the first generation where the evolution leaves the intended cycle, and which
# extra spark caused it.
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests', 'mock'))
import golly as g
g.setrule(sys.argv[1])
for f in sys.argv[2:]:
    L = open(f).read().split('\n'); i = [k for k, l in enumerate(L) if l.startswith('Found')][0]; l = L[i]
    G = int(l.split(':')[1].split('[')[0].split(',')[2]); N = int(re.search(r'after=(\d+)', l)[1]); kind = re.search(r'match=(\w+)', l)[1]
    k = i + 1
    while not L[k].startswith('#C [1]'): k += 1
    R = []
    for _ in range(5):
        p = re.match(r'#CXRLE Pos=(-?\d+),(-?\d+)', L[k + 1]); j = k + 3; b = ''
        while '!' not in b: b += L[j]; j += 1
        c = g.parse(b); R.append({(c[q] + int(p[1]), c[q + 1] + int(p[2])) for q in range(0, len(c), 2)}); k = j
    one, two, three, four, five = R
    T = G + N; xs = [x for x, y in one]; ys = [y for x, y in one]
    if kind == 'rotated':
        left, top, right, bottom = min(xs) - 1, min(ys) - 1, max(xs) + 1, max(ys) + 1
        midy = top + (bottom - top) // 2; midx = left + (right - left) // 2
        nl = midx + top - midy; nb = midy + right - midx
        tr = lambda cs: {(nl + (y - top), nb - (x - left)) for x, y in cs}
    else:
        mx = min(xs) + max(xs); tr = lambda cs: {(mx - x, y) for x, y in cs}
    P = T if kind == 'same' else 2 * T
    sched = [(G, three)] if kind == 'same' else [(G, three), (G + T, tr(three))]
    def evolve(p, gens):
        g.new(''); [g.setcell(x, y, 1) for x, y in one]
        for s0, cs in sched:
            if s0 % p == 0: [g.setcell(*c, 1) for c in cs]
        hist = [set(g._cells)]
        for t in range(1, gens + 1):
            g.run(1)
            for s, cs in sched:
                if t % p == s % p: [g.setcell(*c, 1) for c in cs]
            hist.append(set(g._cells))
        return hist
    ref = evolve(P, 2 * P)
    out = []
    for p in [d for d in range(1, P + 1) if P % d == 0]:
        h = evolve(p, 2 * P)
        bad = next((t for t in range(2 * P + 1) if h[t] != ref[t]), None)
        returns = h[P] == ref[0] and h[2 * P] == ref[0]
        if bad is None: out.append('p%d ok' % p)
        elif returns: out.append('p%d ok (path differs from gen %d, still returns)' % (p, bad))
        else:
            extra = max(t for t in range(bad + 1) if any(t % p == s % p and t % P != s % P for s, _ in sched))
            out.append('p%d FAILS (diverges at gen %d after the extra spark at gen %d)' % (p, bad, extra))
    print('%s (p%d, spark at gen %d): %s' % (os.path.basename(f), P, G, '; '.join(out)))
