# Write one bundle file per distinct clean find (0 debris) from summarize.py's rows.json.
# usage (in a run directory): clean_bundles.py PREFIX
import json, os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests', 'mock'))
import golly as g
g.setrule(os.environ.get('RULE', 'B3/S23-q4i'))
def natural_period(L, i, limit):
    # does the starting configuration oscillate by itself (no spark) within limit gens?
    k = i + 1
    while not L[k].startswith('#C [1]'): k += 1
    p = re.match(r'#CXRLE Pos=(-?\d+),(-?\d+)', L[k + 1]); c = g.parse(L[k + 3])
    one = {(c[q] + int(p[1]), c[q + 1] + int(p[2])) for q in range(0, len(c), 2)}
    g.new(''); [g.setcell(x, y, 1) for x, y in one]
    for t in range(1, limit + 1):
        g.run(1)
        if set(g._cells) == one: return t, one
    return None, one
natural = {}
prefix = sys.argv[1] if len(sys.argv) > 1 else 'f'
os.makedirs('clean', exist_ok=True)
import glob
for old in glob.glob('clean/*.txt') + glob.glob('debris/*.txt') + glob.glob('unsparked/*.txt'): os.remove(old)
rows = json.load(open('rows.json')); seen = set()
for r in rows:
    if r['dup']: continue
    mode = r['mode'].replace('_rot', '') if r['mode'] in ('X4_rot', 'D8_rot') else r['mode']  # same find either way
    key = (r['obj'], mode, r['X'], r['Y'], r['per'])
    if r['debris']: key = key + ('debris',)
    if key in seen: continue
    seen.add(key)
    L = open(r['file']).read().split('\n'); i = r['line']; j = i + 1
    while j < len(L) and not L[j].startswith(('Found', '# summary', '# done')): j += 1
    npd, one = natural_period(L, i, r['per'])
    # spark irrelevant? run the start with no spark for the same T and compare the check box with [5]
    k5 = i + 1
    while not L[k5].startswith('#C [5]'): k5 += 1
    p5 = re.match(r'#CXRLE Pos=(-?\d+),(-?\d+)', L[k5 + 1]); c5 = g.parse(L[k5 + 3])
    five = {(c5[q] + int(p5[1]), c5[q + 1] + int(p5[2])) for q in range(0, len(c5), 2)}
    mbox = re.search(r'Check box \(initial bounding box \+ 1\): cols (-?\d+)\.\.(-?\d+), rows (-?\d+)\.\.(-?\d+)', '\n'.join(L[i:k5]))
    mfr = re.search(r'frame \(top-left (-?\d+),(-?\d+)\)', '\n'.join(L[i:k5]))
    if mbox and mfr and not (npd and r['per'] % npd == 0):   # natural oscillators are reported below
        fx, fy = int(mfr[1]), int(mfr[2]); bx0, bx1, by0, by1 = [int(v) for v in mbox.groups()]
        inb = lambda cs: {c for c in cs if bx0 + fx <= c[0] <= bx1 + fx and by0 + fy <= c[1] <= by1 + fy}
        g.new(''); [g.setcell(x, y, 1) for x, y in one]; g.run(r['G'] + r['N'])
        if inb(set(g._cells)) == inb(five):
            trivial = globals().setdefault('trivial', [0]); trivial[0] += 1
            # works without the spark but leaves debris: keep it (could be cleaned up / a gun)
            g.new(''); [g.setcell(x, y, 1) for x, y in one]; own = None; boxone = inb(one)
            for t in range(1, r['G'] + r['N'] + 1):
                g.run(1)
                if inb(set(g._cells)) == boxone: own = t; break
            if own is None: own = r['G'] + r['N']   # mirror/rotated return: use the find's T
            g.new(''); [g.setcell(x, y, 1) for x, y in one]; g.run(own); s1 = set(g._cells)
            g.run(own); s2 = set(g._cells)
            deb1 = len(s1 - inb(s1)); deb2 = len(s2 - inb(s2))
            if deb1 == 0: continue   # exact natural oscillator: reported in natural_oscillators.txt
            far = lambda cs: max([max(abs(x - (bx0 + bx1) / 2 - fx), abs(y - (by0 + by1) / 2 - fy)) for x, y in cs - inb(cs)] or [0])
            kind_ = ('the core returns again at gen %d' % (2 * own)) if inb(s2) == inb(one) else ('the debris interferes: the core does NOT return again at gen %d' % (2 * own))
            ukey = (r['obj'], mode, r['X'], r['Y'], own)
            seen_u = globals().setdefault('seen_u', set())
            if ukey in seen_u: continue
            seen_u.add(ukey)
            os.makedirs('unsparked', exist_ok=True)
            name = 'unsparked/%s_obj%d_%s_%d_%d_own%d_debris%d.txt' % (prefix, r['obj'], r['mode'], r['X'], r['Y'], own, deb1)
            hdr = ('#C Works WITHOUT a spark: the box holds the start again at gen %d on its own; %d cells outside then, '
                   '%d at gen 2x; %s; farthest debris %.0f cells from the box centre.\n' % (own, deb1, deb2, kind_, far(s2)))
            open(name, 'w').write(L[0] + '\n' + hdr + '\n'.join(L[i:j]) + '\n')
            continue
    if npd and r['per'] % npd == 0:   # the spark is irrelevant: a natural oscillator
        nk = (r['obj'], mode, r['X'], r['Y'])
        if nk not in natural: natural[nk] = (npd, one, r)
        continue
    while j < len(L) and not L[j].startswith(('Found', '# summary', '# done')): j += 1
    if r['debris']:   # finds that leave debris outside the box: kept separately, debris count in the name
        os.makedirs('debris', exist_ok=True)
        name = 'debris/%s_obj%d_%s_%d_%d_p%d_debris%d.txt' % (prefix, r['obj'], r['mode'], r['X'], r['Y'], r['per'], r['debris'])
    else:
        name = 'clean/%s_obj%d_%s_%d_%d_p%d.txt' % (prefix, r['obj'], r['mode'], r['X'], r['Y'], r['per'])
    open(name, 'w').write(L[0] + '\n' + '\n'.join(L[i:j]) + '\n'); print(name)
if natural:
    with open('natural_oscillators.txt', 'w') as w:
        done_bodies = set()
        for (obj, mode, X, Y), (npd, one, r) in sorted(natural.items()):
            x0 = min(x for x, y in one); y0 = min(y for x, y in one)
            rows = [''.join('o' if (x, y) in one else 'b' for x in range(x0, max(a for a, b in one) + 1)).rstrip('b') for y in range(y0, max(b for a, b in one) + 1)]
            rows = [re.sub(r'(o+|b+)', lambda m: (str(len(m[0])) if len(m[0]) > 1 else '') + m[0][0], q) for q in rows]
            body = re.sub(r'\$+', lambda m: (str(len(m[0])) if len(m[0]) > 1 else '') + '$', '$'.join(rows)) + '!'
            if body in done_bodies: continue
            done_bodies.add(body)
            w.write('#C natural p%d oscillator: object %d, mode %s, offset %d,%d (no spark needed)\nx = %d, y = %d, rule = %s\n%s\n' % (
                npd, obj, mode, X, Y, max(a for a, b in one) - x0 + 1, max(b for a, b in one) - y0 + 1, os.environ.get('RULE', 'B3/S23-q4i'), body))
            print('natural p%d oscillator at object %d %s offset %d,%d' % (npd, obj, mode, X, Y))
if 'trivial' in globals(): print('skipped %d find(s) whose box returns the same way without the spark' % trivial[0])
if 'seen_u' in globals(): print('%d find(s) work without a spark but leave debris -> unsparked/' % len(seen_u))
