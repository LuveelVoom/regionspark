# Compare regionspark --mode C1 with the oracle (original script + C1 branch), orientation by orientation.
# usage: compare_c1.py RULE RLE [oracle options like gens=N gens2=N]
import sys, os, re, subprocess
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, 'mock')); import golly as g
rule, rle = sys.argv[1], sys.argv[2]; extra = sys.argv[3:]
g.setrule(rule)
c = g.parse(rle); P = [(c[i], c[i + 1]) for i in range(0, len(c), 2)]
def norm(cs):
    x0 = min(x for x, y in cs); y0 = min(y for x, y in cs); return sorted((x - x0, y - y0) for x, y in cs)
cw = lambda cs: norm([(-y, x) for x, y in cs]); ccw = lambda cs: norm([(y, -x) for x, y in cs])
lr = lambda cs: norm([(-x, y) for x, y in cs]); tb = lambda cs: norm([(x, -y) for x, y in cs]); r180 = lambda cs: norm([(-x, -y) for x, y in cs])
orients = [norm(P), cw(P), r180(P), ccw(P), lr(P), lr(cw(P)), tb(P), lr(ccw(P))]   # same order as regionspark C1
def to_rle(cs):
    w = max(x for x, y in cs) + 1; h = max(y for x, y in cs) + 1
    rows = [''.join('o' if (x, y) in set(map(tuple, cs)) else 'b' for x in range(w)).rstrip('b') for y in range(h)]
    return '$'.join(re.sub(r'(o+|b+)', lambda m: (str(len(m[0])) if len(m[0]) > 1 else '') + m[0][0], r) for r in rows) + '!'
gens = [a.split('=')[1] for a in extra if a.startswith('gens=')]; gens2 = [a.split('=')[1] for a in extra if a.startswith('gens2=')]
popt = (['--gens', gens[0]] if gens else []) + (['--gens2', gens2[0]] if gens2 else [])
popt += ['--selfsym'] if 'selfsym=1' in extra else []
port = subprocess.run([os.path.join(here, '..', 'regionspark', 'regionspark'), '--rule', rule, '--pattern', rle, '--mode', 'C1', '--threads', '1', '--trace'] + popt,
                      capture_output=True, text=True).stdout.split('\n')
# split port output by z
byz = {}; cur = None
for l in port:
    m = re.match(r'visit 0 0 (\d+)', l)
    if m: cur = int(m[1]); byz[cur] = []; continue
    if cur is not None and (l.startswith('steps') or l.startswith('Found')):
        if l.startswith('Found'):
            m = re.match(r'Found!: (-?\d+), (-?\d+), (-?\d+)  \[z=\d+ w=(\d+) edge=\S+ spark=\(([^)]*)\) after=(\d+)', l)
            byz[cur].append(('found', int(m[3]), int(m[4]), tuple(int(v) for v in m[5].split(',')), int(m[6])))
        else: byz[cur].append(('steps', int(l.split()[1])))
seen = []; ok = bad = 0
for z, o in enumerate(orients):
    if o in seen: continue
    seen.append(o)
    out = subprocess.run([sys.executable, os.path.join(here, 'run_oracle.py'), rule, to_rle(o), '0', '0', '0', '0', 'mode=C1'] + extra,
                         capture_output=True, text=True).stdout.split('\n')
    ev = []; last = None
    for l in out:
        if l.startswith('steps'): ev.append(('steps', int(l.split()[1])))
        elif l.startswith('warn Found'): last = int(l.split(',')[2])
        elif l.startswith('DETAIL'):
            p = l.split(None, 3); rest = p[3].rsplit(None, 1)
            ev.append(('found', last, int(p[2]), tuple(int(v) for v in re.findall(r'-?\d+', rest[0])), int(rest[1])))
        elif l.startswith('Traceback') or 'Error' in l: print('ORACLE ERROR', l)
    a = sorted(ev, key=str); b = sorted(byz.get(z, []), key=str)
    same = a == b; ok += same; bad += not same
    print('orientation %d: oracle %d finds, %s steps | port %d finds, %s steps | %s' % (
        z, sum(e[0] == 'found' for e in a), [e[1] for e in a if e[0] == 'steps'], sum(e[0] == 'found' for e in b), [e[1] for e in b if e[0] == 'steps'], 'IDENTICAL' if same else 'DIFFERENT'))
print('orientations identical: %d, different: %d' % (ok, bad))
