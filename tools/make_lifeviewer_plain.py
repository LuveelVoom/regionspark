# LifeViewer file for a configuration that needs no spark: plays it, pauses 2 s at each of its own
# returns (period from the _ownN_ in the file name), stops after CYCLES returns.
# usage: make_lifeviewer_plain.py RULE BUNDLE OUTDIR [CYCLES]
import sys, os, re
rule, f, outdir = sys.argv[1:4]; cycles = int(sys.argv[4]) if len(sys.argv) > 4 else 2
L = open(f).read().split('\n'); own = int(re.search(r'_own(\d+)_', f)[1])
k = [i for i, l in enumerate(L) if l.startswith('#C [1]')][0]
note = [l for l in L if l.startswith('#C Works WITHOUT')]
body = L[k + 3]; hdr = L[k + 2]
# trim the frame-aligned body to its own bounding box (no leading blank rows/cols needed here)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests', 'mock'))
import golly as g
c = g.parse(body); cs = {(c[q], c[q + 1]) for q in range(0, len(c), 2)}
x0 = min(x for x, y in cs); y0 = min(y for x, y in cs)
rows = [''.join('o' if (x, y) in cs else 'b' for x in range(x0, max(a for a, b in cs) + 1)).rstrip('b') for y in range(y0, max(b for a, b in cs) + 1)]
rows = [re.sub(r'(o+|b+)', lambda m: (str(len(m[0])) if len(m[0]) > 1 else '') + m[0][0], r) for r in rows]
data = re.sub(r'\$+', lambda m: (str(len(m[0])) if len(m[0]) > 1 else '') + '$', '$'.join(rows)) + '!'
w = max(x for x, y in cs) - x0 + 1; h = max(y for x, y in cs) - y0 + 1
way = ' '.join('T %d PAUSE 2' % (own * n) for n in range(1, cycles))
span = max(w, h) + 40
txt = '\n'.join(note) + '\n#C Plays the configuration with no spark; pauses at each return of the core (every %d gens), stops after %d.\nx = %d, y = %d, rule = %s\n%s\n#C [[ AUTOSTART THEME Inverse GRID GPS 10 ZOOM %d STOP %d %s ]]\n' % (
    own, cycles, w, h, rule, data, max(1, min(12, 400 // span)), own * cycles, way)
fn = os.path.join(outdir, 'lv_' + os.path.splitext(os.path.basename(f))[0] + '.txt')
open(fn, 'w').write(txt); print(fn)
