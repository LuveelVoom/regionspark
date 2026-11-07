# Which sparker periods could supply a find: repeat the spark every p generations (no sparker body)
import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests', 'mock')); import golly as g
g.setrule('B3/S23-q4i')
for f in sys.argv[1:]:
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
    T = G + N
    xs = [x for x, y in one]; ys = [y for x, y in one]
    if kind == 'rotated':
        left, top, right, bottom = min(xs) - 1, min(ys) - 1, max(xs) + 1, max(ys) + 1
        midy = top + (bottom - top) // 2; midx = left + (right - left) // 2
        nl = midx + top - midy; nb = midy + right - midx
        tr = lambda cs: {(nl + (y - top), nb - (x - left)) for x, y in cs}
    else:
        mx = min(xs) + max(xs); tr = lambda cs: {(mx - x, y) for x, y in cs}
    P = T if kind == 'same' else 2 * T
    sched = [(G, three)] if kind == 'same' else [(G, three), (G + T, tr(three))]
    ok = []
    for p in [d for d in range(1, P + 1) if P % d == 0]:
        g.new(''); [g.setcell(x, y, 1) for x, y in one]; good = True
        for s0, cells in sched:
            if s0 % p == 0: [g.setcell(c[0], c[1], 1) for c in cells]   # spark at generation 0
        startset = set(g._cells)
        for cyc in range(2):
            for t in range(1, P + 1):
                g.run(1); gen = cyc * P + t
                for s, cells in sched:
                    if gen % p == s % p: [g.setcell(c[0], c[1], 1) for c in cells]
            if set(g._cells) != startset: good = False; break
        if good: ok.append(p)
    print('%-34s p%-3d %-8s sparks %2d cells | viable sparker periods: %s' % (f.split('/')[-1], P, kind, len(three), ok))
