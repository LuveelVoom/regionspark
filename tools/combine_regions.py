# Combine active regions into one RLE per rule, laid out left to right (top-aligned) with a gap.
# Input: a regions file, one region per line:  RULE<TAB>RLE[<TAB>label]   ('#' lines ignored).
# RLE may be a body ("b2o$o2bo$3o!") or a full RLE with header on one line. LifeHistory-style
# letters are accepted (odd states = alive). Duplicates (same object up to rotation/reflection)
# are merged. Output: one RLE per rule, pattern data on a single line (no whitespace).
# usage: combine_regions.py REGIONS.txt OUTPREFIX [--gap N] [--width W]
import sys, re
args = sys.argv[1:]
gap = int(args[args.index('--gap') + 1]) if '--gap' in args else 10
width = int(args[args.index('--width') + 1]) if '--width' in args else 0   # 0 = one row
src, outprefix = args[0], args[1]

def cells_of(rle):
    body = rle.split('\n')[-1] if '\n' in rle else rle
    body = re.sub(r'^\s*x\s*=.*?rule\s*=\s*\S+\s*', '', body) if body.lstrip().startswith('x') else body
    out = set(); x = y = 0; n = ''
    for ch in re.sub(r'\s', '', body):
        if ch.isdigit(): n += ch; continue
        k = int(n) if n else 1; n = ''
        if ch in '.b': x += k
        elif ch == 'o' or 'A' <= ch <= 'X':
            st = 1 if ch == 'o' else ord(ch) - 64
            if st % 2: out |= {(x + i, y) for i in range(k)}
            x += k
        elif ch == '$': y += k; x = 0
        elif ch == '!': break
    x0 = min(a for a, b in out); y0 = min(b for a, b in out)
    return {(a - x0, b - y0) for a, b in out}

MATS = [(1, 0, 0, 1), (0, -1, 1, 0), (-1, 0, 0, -1), (0, 1, -1, 0), (-1, 0, 0, 1), (1, 0, 0, -1), (0, 1, 1, 0), (0, -1, -1, 0)]
def canon(cs):
    best = None
    for m in MATS:
        t = [(m[0] * a + m[1] * b, m[2] * a + m[3] * b) for a, b in cs]
        x0 = min(a for a, b in t); y0 = min(b for a, b in t)
        k = tuple(sorted((a - x0, b - y0) for a, b in t))
        if best is None or k < best: best = k
    return best

def to_rle(cs):
    w = max(a for a, b in cs) + 1; h = max(b for a, b in cs) + 1
    rows = []
    for yy in range(h):
        r = ''.join('o' if (xx, yy) in cs else 'b' for xx in range(w)).rstrip('b')
        rows.append(re.sub(r'(o+|b+)', lambda m: (str(len(m[0])) if len(m[0]) > 1 else '') + m[0][0], r))
    s = re.sub(r'\$+', lambda m: (str(len(m[0])) if len(m[0]) > 1 else '') + '$', '$'.join(rows))
    return w, h, s + '!'

byrule = {}
for line in open(src):
    line = line.rstrip('\n')
    if not line.strip() or line.lstrip().startswith('#'): continue
    parts = line.split('\t')
    rule, rle = parts[0].strip(), parts[1].strip()
    rule = re.sub(r'History$', '', rule)
    label = parts[2].strip() if len(parts) > 2 else ''
    byrule.setdefault(rule, []).append((rle, label))

for rule, items in byrule.items():
    seen = {}; objs = []
    for rle, label in items:
        cs = cells_of(rle); k = canon(cs)
        if k in seen: seen[k][1].append(label or rle); continue
        seen[k] = (cs, [label or rle]); objs.append(k)
    # layout
    placed = set(); x = y = 0; rowh = 0; legend = []
    for n, k in enumerate(objs, 1):
        cs, labels = seen[k]
        w = max(a for a, b in cs) + 1; h = max(b for a, b in cs) + 1
        if width and x > 0 and x + w > width: x = 0; y += rowh + gap; rowh = 0
        placed |= {(a + x, b + y) for a, b in cs}
        legend.append('#C %d at (%d,%d): %s' % (n, x, y, ' = '.join(labels)))
        x += w + gap; rowh = max(rowh, h)
    W, H, body = to_rle(placed)
    fn = '%s_%s.rle' % (outprefix, re.sub(r'[^A-Za-z0-9]+', '-', rule).strip('-'))
    with open(fn, 'w') as f:
        f.write('#C %d distinct regions in %s (top-left of each region, x right, y down)\n' % (len(objs), rule))
        f.write('\n'.join(legend) + '\n')
        f.write('x = %d, y = %d, rule = %s\n%s\n' % (W, H, rule, body))
    print('%s: %d regions (%d given) -> %s' % (rule, len(objs), len(items), fn))
