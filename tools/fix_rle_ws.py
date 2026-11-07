# Remove whitespace (spaces, line breaks) from RLE pattern data; comments and headers untouched.
# Checks every pattern decodes to the same cells before and after.
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests', 'mock'))
import golly as g
def cells(body): return g.parse(re.sub(r'\s', '', body))
tot = 0
for f in sys.argv[1:]:
    L = open(f).read().split('\n'); out = []; i = 0; n = 0; changed = False
    while i < len(L):
        l = L[i]; out.append(l)
        if re.match(r'\s*x\s*=\s*\d+\s*,\s*y\s*=', l):
            j = i + 1; parts = []
            while j < len(L) and not L[j].lstrip().startswith('#'):
                parts.append(L[j]); j += 1
                if '!' in parts[-1]: break
            orig = '\n'.join(parts); new = re.sub(r'\s', '', orig)
            assert cells(orig) == cells(new), (f, i)
            if new != orig: changed = True; n += 1
            out.append(new); i = j; continue
        i += 1
    if changed: open(f, 'w').write('\n'.join(out)); tot += n
    print('%-70s %d pattern(s) fixed' % (f, n)) if n else None
print('total patterns fixed:', tot)
