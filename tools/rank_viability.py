# Rank regionspark partials by how promising they are to complete.
# For each bundle: viable sparker periods (bodiless test), library oscillators of those periods,
# number of spark cells/groups, clearance (closest the pattern comes to any spark cell, Chebyshev,
# over the cycle excluding the 2 gens before the spark), period, debris.
# Sorted by closest approach after the spark (larger first), then number of factors of the period (more
# first), then smallest factor. Writes a sorted table.
# usage: rank_viability.py RULE LIBRARY OUT.txt BUNDLE...
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests', 'mock'))
import golly as g
rule, libf, out = sys.argv[1:4]; bundles = sys.argv[4:]
g.setrule(rule)
libper = {}
for m in re.findall(r'^p(\d+)\s', open(libf).read(), re.M): libper[int(m)] = libper.get(int(m), 0) + 1

def load(f):
    L = open(f).read().split('\n'); i = [k for k, l in enumerate(L) if l.startswith('Found')][0]; l = L[i]
    G = int(l.split(':')[1].split('[')[0].split(',')[2]); N = int(re.search(r'after=(\d+)', l)[1]); kind = re.search(r'match=(\w+)', l)[1]
    k = i + 1
    while not L[k].startswith('#C [1]'): k += 1
    R = []
    for _ in range(5):
        p = re.match(r'#CXRLE Pos=(-?\d+),(-?\d+)', L[k + 1]); c = g.parse(L[k + 3])
        R.append({(c[q] + int(p[1]), c[q + 1] + int(p[2])) for q in range(0, len(c), 2)}); k += 4
    return G, N, kind, R

def groups(cells):
    cells = set(cells); n = 0
    while cells:
        st = [cells.pop()]; n += 1
        while st:
            x, y = st.pop()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (x + dx, y + dy)
                    if q in cells: cells.remove(q); st.append(q)
    return n

rows = []
for f in bundles:
    G, N, kind, (one, two, three, four, five) = load(f)
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
    def run_cycle(p):
        g.new(''); [g.setcell(x, y, 1) for x, y in one]
        for s0, cs in sched:
            if s0 % p == 0: [g.setcell(*c, 1) for c in cs]
        start = set(g._cells); hist = [start]
        for cyc in range(2):
            for t in range(1, P + 1):
                g.run(1); gen = cyc * P + t
                for s, cs in sched:
                    if gen % p == s % p: [g.setcell(*c, 1) for c in cs]
                if cyc == 0: hist.append(set(g._cells))
            if set(g._cells) != start: return False, hist
        return True, hist
    viable = []; hist = None
    for p in [d for d in range(1, P + 1) if P % d == 0]:
        ok, h = run_cycle(p)
        if p == P: hist = h
        if ok: viable.append(p)
    # closest approach AFTER the spark: for each spark time s, generations s+2 .. s'-3 where s' is the
    # next spark time (skip the spark's own offspring and the approach needed to react); distance from
    # that spark's cells to the pattern (Chebyshev). Also the generation (after the spark) where it happens.
    sparkcells = set(three) | (tr(three) if kind != 'same' else set())
    clear = None; clear_at = None; leave_at = None
    times = sorted(s0 % P for s0, _ in sched)
    for s0, cs in sched:
        s0 %= P; nxt = min([t for t in times if t > s0] or [times[0] + P])
        # distance profile after this spark, then: when does the reaction first get >= 3 clear of the
        # spark cells, and how close does the pattern come back after that (before the next spark)
        prof = []
        for t in range(s0 + 1, nxt - 2):
            st = hist[t % P]
            prof.append((t - s0, min([max(abs(x - sx), abs(y - sy)) for (sx, sy) in cs for (x, y) in st] or [99])))
        leave = next((k for k, d in prof if d >= 3), None)
        if leave is None:
            cb, cb_at = -1, None          # never gets clear of the spark cells: worst
        else:
            after = [(d, k) for k, d in prof if k > leave]
            cb, cb_at = min(after) if after else (99, None)
        if clear is None or cb < clear: clear, clear_at, leave_at = cb, cb_at, leave
    avail = {p: libper.get(p, 0) for p in viable}
    debris = int(re.search(r'debris(\d+)', f)[1]) if re.search(r'debris(\d+)', f) else 0
    # SCORE: room around the sparks, small spark sets, several viable periods (especially short
    # ones), library coverage, low period; debris penalised
    shortest = min(viable) if viable else P
    c_ = 0 if clear is None else clear
    score = (3 * min(c_, 6) - 2 * groups(sparkcells) - len(sparkcells) / 4 + 2 * len(viable)
             + 6 * (P / shortest > 1) + 3 * min(sum(avail.values()), 5) / 5 - P / 50 - debris / 4)
    factors = [d for d in range(2, P) if P % d == 0]
    key = (-(clear if clear is not None else -2), -len(factors), factors[0] if factors else P)
    shown = 'n/a' if clear is None else ('never' if clear == -1 else ('none' if clear == 99 else clear))
    rows.append((key, os.path.basename(f), P, kind, viable, avail, len(sparkcells), groups(sparkcells),
                 shown, debris, factors, clear_at, leave_at))
rows.sort(key=lambda r: r[0])
with open(out, 'w') as w:
    w.write('Partials sorted by (1) how close the pattern comes back to the spark cells after the spark (comeback, larger first),\n')
    w.write('then (2) number of factors of the period (more first), then smallest factor (smaller first). Rule %s.\n' % rule)
    w.write('clear = generations after the spark when the reaction first gets >= 3 cells (Chebyshev) from all spark cells.\n')
    w.write('comeback = closest the pattern comes back to the spark cells after that, up to 3 gens before the next spark;\n')
    w.write('           never = it never gets 3 clear (worst); none = it never comes back within the cycle (best); at = when.\n')
    w.write('viable = factors p for which a spark repeated every p gens keeps the cycle exact; library = entries of those periods.\n\n')
    w.write('%-44s %8s %4s %5s %5s %-8s %-22s %-14s %-24s %6s %6s %6s\n' % ('find', 'comeback', 'at', 'clear', 'per', 'match', 'factors', 'viable', 'library', 'sparks', 'groups', 'debris'))
    for r in rows:
        w.write('%-44s %8s %4s %5s %5d %-8s %-22s %-14s %-24s %6d %6d %6d\n' % (r[1], r[8], '-' if r[11] is None else r[11], '-' if r[12] is None else r[12], r[2], r[3],
                ','.join(map(str, r[10])) or '-', ','.join(map(str, r[4])), ','.join('p%d:%d' % kv for kv in r[5].items()) or '-', r[6], r[7], r[9]))
print(open(out).read())
