# Summarize all regionspark runs: one line per distinct (object, mode, offset, period),
# with debris count, verified flag (independent re-simulation of the bundle).
import sys, os, re, glob, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests', 'mock'))
import golly as g
g.setrule(os.environ.get('RULE', 'B3/S23-q4i'))

def rle_at(L, i):
    p = re.match(r'#CXRLE Pos=(-?\d+),(-?\d+)', L[i + 1]); j = i + 3; b = ''
    while '!' not in b: b += L[j]; j += 1
    c = g.parse(b); return {(c[k] + int(p[1]), c[k + 1] + int(p[2])) for k in range(0, len(c), 2)}, j
def run(c, n): g.new(''); [g.setcell(x, y, 1) for x, y in c]; g.run(n); return set(g._cells)

rows = []
for f in sorted(glob.glob('runs/*.txt')):
    obj, mode = re.match(r'runs/obj(\d+)_(\w+)\.txt', f).groups()
    L = open(f).read().split('\n')
    seen = set()
    for i, l in enumerate(L):
        if not l.startswith('Found'): continue
        X, Y, G = [int(v) for v in l.split(':')[1].split('[')[0].split(',')]
        N = int(re.search(r'after=(\d+)', l)[1]); kind = re.search(r'match=(\w+)', l)[1]
        per = int(re.search(r'period (\d+)', l)[1])
        k = i + 1
        while not L[k].startswith('#C [1]'): k += 1
        R = []
        for _ in range(5): c, k = rle_at(L, k); R.append(c)
        one, two, three, four, five = R
        xs = [x for x, y in one]; ys = [y for x, y in one]
        bx, by, bw, bh = min(xs) - 1, min(ys) - 1, max(xs) - min(xs) + 3, max(ys) - min(ys) + 3
        inbox = lambda c: {(x - bx, y - by) for x, y in c if bx <= x < bx + bw and by <= y < by + bh}
        if kind == 'rotated':  # Golly anticlockwise rotation of the box (bbox+1) about its centre
            top, left, bottom, right = by, bx, by + bh - 1, bx + bw - 1
            midy = top + (bottom - top) // 2; midx = left + (right - left) // 2
            nleft = midx + top - midy; nbottom = midy + right - midx
            rot = {(nleft + (y - top), nbottom - (x - left)) for x, y in one}
            rx = [x for x, y in rot]; ry = [y for x, y in rot]
            bx, by, bw, bh = min(rx) - 1, min(ry) - 1, max(rx) - min(rx) + 3, max(ry) - min(ry) + 3
            ref = {(x - bx, y - by) for x, y in rot}
        else:
            ref = inbox(one) if kind == 'same' else {(bw - 1 - x, y) for x, y in inbox(one)}
        ok = run(two | three, N) == five and inbox(five) == ref and run(one, G) >= two and four == two | three
        debris = len(five) - len(inbox(five))
        key = (X, Y, per)
        dup = key in seen; seen.add(key)
        rows.append(dict(obj=int(obj), mode=mode, X=X, Y=Y, G=G, N=N, kind=kind, per=per, debris=debris,
                         ok=ok, nspark=len(three), pop=len(one), file=f, line=i, dup=dup))
rows.sort(key=lambda r: (r['debris'] > 0, r['debris'], -r['per']))
print('total finds', len(rows), '| verified', sum(r['ok'] for r in rows), '| failed', sum(not r['ok'] for r in rows))
print('clean (0 debris), distinct offset/period:')
for r in rows:
    if r['debris'] == 0 and not r['dup']:
        print('  obj%(obj)d %(mode)-6s offset %(X)d,%(Y)d  p%(per)d  (%(kind)s, spark at gen %(G)d, %(nspark)d spark cells, pop %(pop)d) verified=%(ok)s' % r)
print('with debris (best 10):')
for r in [r for r in rows if r['debris'] > 0 and not r['dup']][:10]:
    print('  obj%(obj)d %(mode)-6s offset %(X)d,%(Y)d  p%(per)d  debris %(debris)d' % r)
import json; json.dump(rows, open('rows.json', 'w'))
