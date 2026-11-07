# Automatic sparker fitting for regionspark partials.
# 1. Extract oscillators from one or more collection RLEs (and/or drift-style oscillator lists).
# 2. For each find bundle, compute which sparker periods could work (spark repeated every p gens
#    with no sparker body keeps the cycle exact).
# 3. Run place_osc.py with only the oscillators of those periods.
# usage: fit_sparkers.py RULE OUTDIR --osc FILE[,FILE...] BUNDLE...
#   --all-divisors: try every library period dividing the find's period (skip the viable test)
#   FILE: a collection RLE (*.rle or anything with an 'x =' header first) or an oscillator list
#         in drift's findings format ("pN ..." line, header line, RLE line).
import sys, os, re, subprocess
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, '..', 'tests', 'mock'))
import golly as g

rule, outdir = sys.argv[1], sys.argv[2]
a = sys.argv.index('--osc'); oscsrc = sys.argv[a + 1].split(','); bundles = [b for b in sys.argv[a + 2:] if not b.startswith('--')]
os.makedirs(outdir, exist_ok=True)
g.setrule(rule)

# 1. oscillator library
libfiles = []
for i, f in enumerate(oscsrc):
    first = open(f).readline()
    if first.lstrip().startswith('x ='):
        out = os.path.join(outdir, 'lib%d_%s.txt' % (i, os.path.splitext(os.path.basename(f))[0]))
        print(subprocess.run([sys.executable, os.path.join(here, 'extract_oscillators.py'), rule, f, out],
                             capture_output=True, text=True).stdout.strip())
        libfiles.append(out)
    else:
        libfiles.append(f)
lib = os.path.join(outdir, 'library.txt')
with open(lib, 'w') as w:
    for f in libfiles: w.write(open(f).read().rstrip('\n') + '\n')
periods_available = sorted({int(m) for m in re.findall(r'^p(\d+)\s', open(lib).read(), re.M)})
print('library periods:', periods_available)

# 2. viable sparker periods per find
def viable(f):
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
    ok = []
    for p in [d for d in range(1, P + 1) if P % d == 0]:
        g.new(''); [g.setcell(x, y, 1) for x, y in one]
        for s0, cells in sched:
            if s0 % p == 0: [g.setcell(c[0], c[1], 1) for c in cells]
        startset = set(g._cells); good = True
        for cyc in range(2):
            for t in range(1, P + 1):
                g.run(1); gen = cyc * P + t
                for s, cells in sched:
                    if gen % p == s % p: [g.setcell(c[0], c[1], 1) for c in cells]
            if set(g._cells) != startset: good = False; break
        if good: ok.append(p)
    return P, ok

# 3. placement
for f in bundles:
    P, ok = viable(f)
    use = [p for p in ok if p in periods_available]
    if '--all-divisors' in sys.argv:  # ignore the bodiless test: every library period dividing P
        use = [p for p in periods_available if P % p == 0 and p > 1]
    print('\n## %s: period %d, viable sparker periods %s, in library: %s' % (os.path.basename(f), P, ok, use or 'none'))
    if not use: continue
    r = subprocess.run([sys.executable, os.path.join(here, 'place_osc.py'), rule, lib, ','.join(map(str, use)), f],
                       capture_output=True, text=True)
    print(r.stdout.strip()); print(r.stderr.strip()[-500:]) if r.returncode else None
