# For a spark-free return with debris: does the box hold the start exactly every cycle for N cycles,
# and how does the outside debris behave (count, distance; linear growth = emitter/gun)?
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests', 'mock'))
import golly as g
rule, f = sys.argv[1], sys.argv[2]; ncyc = int(sys.argv[3]) if len(sys.argv) > 3 else 10
g.setrule(rule)
L = open(f).read().split('\n'); own = int(re.search(r'_own(\d+)_', f)[1])
k = [i for i, l in enumerate(L) if l.startswith('#C [1]')][0]
p = re.match(r'#CXRLE Pos=(-?\d+),(-?\d+)', L[k + 1]); c = g.parse(L[k + 3])
one = {(c[q] + int(p[1]), c[q + 1] + int(p[2])) for q in range(0, len(c), 2)}
xs = [x for x, y in one]; ys = [y for x, y in one]
bx0, bx1, by0, by1 = min(xs) - 1, max(xs) + 1, min(ys) - 1, max(ys) + 1
inb = lambda cs: {q for q in cs if bx0 <= q[0] <= bx1 and by0 <= q[1] <= by1}
cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
g.new(''); [g.setcell(x, y, 1) for x, y in one]
print(os.path.basename(f), '| box %dx%d, own return period %d' % (bx1 - bx0 + 1, by1 - by0 + 1, own))
for cyc in range(1, ncyc + 1):
    g.run(own); cs = set(g._cells); out = cs - inb(cs)
    dist = max([max(abs(x - cx), abs(y - cy)) for x, y in out] or [0])
    print('  cycle %2d (gen %4d): box exact=%s, outside cells %4d, farthest %5.0f' % (cyc, cyc * own, inb(cs) == one, len(out), dist))
