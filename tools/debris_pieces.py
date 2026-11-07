# Split the debris outside the box at the core's own return into pieces and classify each alone.
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests', 'mock'))
import golly as g
rule, f = sys.argv[1], sys.argv[2]; g.setrule(rule)
L = open(f).read().split('\n'); own = int(re.search(r'_own(\d+)_', f)[1])
k = [i for i, l in enumerate(L) if l.startswith('#C [1]')][0]
p = re.match(r'#CXRLE Pos=(-?\d+),(-?\d+)', L[k + 1]); c = g.parse(L[k + 3])
one = {(c[q] + int(p[1]), c[q + 1] + int(p[2])) for q in range(0, len(c), 2)}
xs = [x for x, y in one]; ys = [y for x, y in one]
bx0, bx1, by0, by1 = min(xs) - 1, max(xs) + 1, min(ys) - 1, max(ys) + 1
inb = lambda cs: {q for q in cs if bx0 <= q[0] <= bx1 and by0 <= q[1] <= by1}
g.new(''); [g.setcell(x, y, 1) for x, y in one]; g.run(own); cs = set(g._cells); out = cs - inb(cs)
# pieces: within distance 2
pieces = []; rest = set(out)
while rest:
    st = [rest.pop()]; comp = set(st)
    while st:
        x, y = st.pop()
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                q = (x + dx, y + dy)
                if q in rest: rest.remove(q); comp.add(q); st.append(q)
    pieces.append(comp)
def classify(pc):
    g.new(''); [g.setcell(x, y, 1) for x, y in pc]
    def norm(s):
        x0 = min(a for a, b in s); y0 = min(b for a, b in s); return frozenset((a - x0, b - y0) for a, b in s), (x0, y0)
    n0, o0 = norm(pc)
    for t in range(1, 200):
        g.run(1)
        if not g._cells: return 'dies after %d gens' % t
        n, o = norm(g._cells)
        if n == n0:
            if o == o0: return 'still life' if t == 1 else 'p%d oscillator' % t
            return 'spaceship p%d moving (%d,%d)' % (t, o[0] - o0[0], o[1] - o0[1])
    return 'other (pop %d after 200 gens)' % len(g._cells)
print('%s: debris at the core\'s return (gen %d): %d cells in %d pieces' % (os.path.basename(f), own, len(out), len(pieces)))
from collections import Counter
cnt = Counter()
for pc in pieces:
    cx = sum(x for x, y in pc) / len(pc) - (bx0 + bx1) / 2; cy = sum(y for x, y in pc) / len(pc) - (by0 + by1) / 2
    cnt[(len(pc), classify(pc))] += 1
for (n, kind), m in sorted(cnt.items()): print('   %d x  %d-cell piece: %s' % (m, n, kind))
