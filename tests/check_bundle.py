# Independent check of every find bundle: [1]->G->[2], [4]==[2]+[3], [4]->N->[5], box([5]) vs [1]
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mock'))
import golly as g
g.setrule(sys.argv[1]); L = open(sys.argv[2]).read().split('\n')
def rle_at(i):
    p = re.match(r'#CXRLE Pos=(-?\d+),(-?\d+)', L[i + 1]); j = i + 3; b = ''
    while '!' not in b: b += L[j]; j += 1
    cl = g.parse(b); return {(cl[k] + int(p[1]), cl[k + 1] + int(p[2])) for k in range(0, len(cl), 2)}, L[i + 2], j
def run(c, n): g.new(''); [g.setcell(x, y, 1) for x, y in c]; g.run(n); return set(g._cells)
good = bad = 0
for i, l in enumerate(L):
    if not l.startswith('Found'): continue
    G = int(l.split(',')[2].split()[0]); N = int(re.search(r'after=(\d+)', l)[1]); kind = re.search(r'match=(\w+)', l)[1]
    k = i + 1
    while not L[k].startswith('#C [1]'): k += 1
    notes = '\n'.join(L[i:k]); R = []; hdrs = []
    for _ in range(5): c, h, k = rle_at(k); R.append(c); hdrs.append(h)
    one, two, three, four, five = R
    xs = [x for x, y in one]; ys = [y for x, y in one]
    bx, by, bw, bh = min(xs) - 1, min(ys) - 1, max(xs) - min(xs) + 3, max(ys) - min(ys) + 3
    inbox = lambda c: {(x - bx, y - by) for x, y in c if bx <= x < bx + bw and by <= y < by + bh}
    ref = inbox(one) if kind == 'same' else {(bw - 1 - x, y) for x, y in inbox(one)}
    nat = run(one, G)
    ok = [len(set(hdrs)) == 1,                                          # same frame header
          nat == two or ('NOTE' in notes and two <= nat),                # [1] -> [2]
          four == two | three and not (two & three),                     # [4] = [2] + [3]
          run(four, N) == five,                                          # [4] -> [5]
          inbox(five) == ref]                                            # check box
    good += all(ok); bad += not all(ok)
    if not all(ok): print('FAIL', ok, l[:60])
print('bundles ok', good, 'failed', bad)
