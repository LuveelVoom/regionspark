# Turn regionspark find bundles into LifeViewer RLEs with timed sparks (PASTET), pauses and a stop.
# LifeViewer semantics used (read from github.com/rowett/lifeviewer source):
#  * PASTE x y is relative to the top-left of the main RLE body (no XOFFSET used);
#  * PASTET EVERY P S pastes at gens S, S+P, ...; the paste is applied right after that
#    generation is computed, before it is displayed;
#  * "T g" starts a waypoint at generation g, "PAUSE s" holds that generation s seconds.
# Each output is re-simulated here with the same paste schedule (independent simulator).
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests', 'mock'))
import golly as g

rule, infile, outdir, cycles = sys.argv[1], sys.argv[2], sys.argv[3], 2
g.setrule(rule)
L = open(infile).read().split('\n')

def rle_at(i):
    p = re.match(r'#CXRLE Pos=(-?\d+),(-?\d+)', L[i + 1]); j = i + 3; b = ''
    while '!' not in b: b += L[j]; j += 1
    cl = g.parse(b); return {(cl[k] + int(p[1]), cl[k + 1] + int(p[2])) for k in range(0, len(cl), 2)}, j

def body(cells):  # trimmed RLE body, origin = bounding-box top-left; returns (x0, y0, rle)
    xs = [x for x, y in cells]; ys = [y for x, y in cells]; x0, y0 = min(xs), min(ys)
    rows = {}
    for x, y in cells: rows.setdefault(y - y0, []).append(x - x0)
    out = []; prev = 0
    for r in sorted(rows):
        if r > prev: out.append(('%d' % (r - prev) if r - prev > 1 else '') + '$')
        prev = r; cx = 0; xs_ = sorted(rows[r]); i = 0
        while i < len(xs_):
            if xs_[i] > cx: out.append(('%d' % (xs_[i] - cx) if xs_[i] - cx > 1 else '') + 'b'); cx = xs_[i]
            n = 0
            while i < len(xs_) and xs_[i] == cx + n: n += 1; i += 1
            out.append(('%d' % n if n > 1 else '') + 'o'); cx += n
    return x0, y0, ''.join(out) + '!'

def wrap(s, n=70):
    return '\n'.join(s[i:i + n] for i in range(0, len(s), n))

def simulate(init, pastes, gens):  # pastes: list of (every, start, cells)
    g.new(''); [g.setcell(x, y, 1) for x, y in init]; hist = {0: set(g._cells)}
    for gen in range(1, gens + 1):
        g.run(1)
        for every, start, cells in pastes:
            if gen >= start and (gen - start) % every == 0:
                for c in cells: g.setcell(c[0], c[1], 1)
        hist[gen] = set(g._cells)
    return hist

os.makedirs(outdir, exist_ok=True)
n = 0
for i, l in enumerate(L):
    if not l.startswith('Found'): continue
    n += 1
    X, Y, G = [int(v) for v in l.split(':')[1].split('[')[0].split(',')]
    N = int(re.search(r'after=(\d+)', l)[1]); kind = re.search(r'match=(\w+)', l)[1]
    mode = re.search(r'mode (\w+)', open(infile).read()).group(1) if re.search(r'mode (\w+)', open(infile).read()) else '?'
    k = i + 1
    while not L[k].startswith('#C [1]'): k += 1
    R = []
    for _ in range(5): c, k = rle_at(k); R.append(c)
    one, two, three, four, five = R
    T = G + N
    mx = min(x for x, y in one) + max(x for x, y in one)
    if kind == 'rotated':  # Golly anticlockwise rotation of the bbox+1 box about its centre
        _xs = [x for x, y in one]; _ys = [y for x, y in one]
        left, top, right, bottom = min(_xs) - 1, min(_ys) - 1, max(_xs) + 1, max(_ys) + 1
        midy = top + (bottom - top) // 2; midx = left + (right - left) // 2
        nleft = midx + top - midy; nbottom = midy + right - midx
        mirror = lambda cs: {(nleft + (y - top), nbottom - (x - left)) for x, y in cs}
    else:
        mirror = lambda cs: {(mx - x, y) for x, y in cs}
    if kind == 'same':
        P = T; pastes = [(P, G, three)]
    else:  # flipped: mirror-image sparks in the second half
        P = 2 * T; pastes = [(P, G, three), (P, G + T, mirror(three))]
    # a paste at generation 0: put those cells in the starting pattern, repeat from one period later
    start_cells = set(one)
    for idx, (every, start, cells) in enumerate(pastes):
        if start == 0: start_cells |= cells; pastes[idx] = (every, every, cells)
    hist = simulate(start_cells, pastes, cycles * P)
    exact = all(hist[c * P] == start_cells for c in range(1, cycles + 1))
    half = kind == 'same' or all(hist[c * P - T] == mirror(one) for c in range(1, cycles + 1))
    debris = len(hist[P] - start_cells)
    # build the LifeViewer RLE
    bx, by, mbody = body(start_cells)
    w = max(x for x, y in start_cells) - bx + 1; h = max(y for x, y in start_cells) - by + 1
    snippets = []; cmds = []
    for idx, (every, start, cells) in enumerate(pastes):
        sx, sy, sb = body(cells)
        name = 'spark%d' % (idx + 1)
        snippets.append('RLE %s %s' % (name, sb))
        cmds.append('PASTET EVERY %d %d PASTE %s %d %d' % (every, start, name, sx - bx, sy - by))
    stops = []
    for c in range(cycles):
        for every, start, cells in pastes:
            stops.append(start + c * P)
        stops.append((c + 1) * P - (T if kind != 'same' else 0)) if kind != 'same' else None
        stops.append((c + 1) * P)
    stops = sorted(set(s for s in stops if s and s <= cycles * P))
    way = ' '.join('T %d PAUSE 2' % s for s in stops[:-1]) + ' T %d' % stops[-1]
    allc = set().union(start_cells, *[c for _, _, c in pastes])
    span = max(max(x for x, y in allc) - min(x for x, y in allc), max(y for x, y in allc) - min(y for x, y in allc)) + 1
    zoom = max(1, min(12, int(400 / (span + 8))))
    desc = [
        '#C One-spark oscillator partial in %s, found by regionspark (port of hotdogPi\'s script).' % rule,
        '#C Mode %s, offset (%d,%d). Sparks are pasted automatically at generation %d%s,' % (mode, X, Y, G,
            ' (%s sparks at %d)' % ('rotated' if kind == 'rotated' else 'mirror-image', G + T) if kind != 'same' else ''),
        '#C then every %d generations; playback pauses 2 s at each spark and at each return' % P,
        '#C to the start%s, and stops after %d cycles (generation %d).' % ((' (or its rotation)' if kind == 'rotated' else ' (or its mirror image)') if kind != 'same' else '', cycles, cycles * P),
        '#C Period %d. The sparks have no sparker yet: this is a partial, not an oscillator.' % P,
        ('#C Checked by re-simulation: returns exactly every cycle, nothing left over.' if exact and half else
         '#C Checked by re-simulation: the start box returns, but %d debris cells remain outside it, so it does not repeat cleanly.' % debris),
    ]
    script = ['#C [[ ' + s + ' ]]' for s in snippets] + ['#C [[ ' + c + ' ]]' for c in cmds]
    script.append('#C [[ AUTOSTART THEME Inverse GRID GPS 10 ZOOM %d STOP %d %s ]]' % (zoom, cycles * P, way))
    text = '\n'.join(desc) + '\nx = %d, y = %d, rule = %s\n%s\n' % (w, h, rule, mbody) + '\n'.join(script) + '\n'
    fn = os.path.join(outdir, 'lv_' + os.path.splitext(os.path.basename(infile))[0] + '.txt')
    open(fn, 'w').write(text)
    print(fn, 'period', P, 'exact return each cycle:', exact and half, 'debris after 1 cycle:', debris)
