# Minimal mock of Golly's Python API, enough to run hotdogPi's one-spark script.
# Semantics follow Golly's source (gui-wx/wxscript.cpp, wxselect.cpp, gollybase/liferules.cpp).
# Independent of regionspark.cpp: own rule code (geometric orbits) and set-based simulation.
import os, sys

_REP = {1: [1, 2], 2: [5, 10, 3, 40, 33, 68], 3: [69, 42, 11, 7, 98, 13, 14, 70, 41, 97],
        4: [325, 170, 15, 45, 99, 71, 106, 102, 43, 101, 105, 78, 108]}
_LET = "ceaiknjqrytwz"

def _grid(x): return [[(x >> (8 - (3 * r + c))) & 1 for c in range(3)] for r in range(3)]
def _ungrid(g): return sum(g[r][c] << (8 - (3 * r + c)) for r in range(3) for c in range(3))
def _rot(x): g = _grid(x); return _ungrid([[g[2 - c][r] for c in range(3)] for r in range(3)])
def _flip(x): g = _grid(x); return _ungrid([[g[r][2 - c] for c in range(3)] for r in range(3)])
def _orbit(x):
    s = set()
    for f in (x, _flip(x)):
        for _ in range(4):
            s.add(f); f = _rot(f)
    return s
def _cnt(i): return bin(i & 0x1ef).count('1')

def _parse_rule(rule):
    r = rule.replace('/', '').lower()
    b = r.index('b'); s = r.index('s')
    bp = r[b + 1:s] if b < s else r[b + 1:]
    sp = r[s + 1:b] if s < b else r[s + 1:]
    table = [0] * 512
    for part, centre in ((bp, 0), (sp, 16)):
        i = 0
        while i < len(part):
            n = int(part[i]); i += 1
            neg = False
            if i < len(part) and part[i] == '-':
                neg = True; i += 1
            lets = ''
            while i < len(part) and part[i].isalpha():
                lets += part[i]; i += 1
            alln = {k for k in range(512) if (k & 16) == centre and _cnt(k) == n}
            if not lets:
                on = alln
            else:
                sel = set()
                for l in lets:
                    li = _LET.index(l)
                    rep = _REP[n][li] if n <= 4 else _REP[8 - n][li] ^ 0x1ef
                    sel |= _orbit(rep | centre)
                on = (alln - sel) if neg else sel
            for k in on:
                table[k] = 1
    return table

_rule = os.environ.get('MOCK_RULE', 'B3/S23')
_table = _parse_rule(_rule)
_cells = set()
_sel = None
_clip = []
_gen = 0

class GollyExit(Exception):
    pass

def setrule(r):
    global _rule, _table
    _rule = r; _table = _parse_rule(r)
def getrule(): return _rule

def new(name):
    global _cells, _gen
    _cells = set(); _gen = 0

def parse(rle, x0=0, y0=0, axx=1, axy=0, ayx=0, ayy=1):
    out = []; x = y = 0; n = ''
    for ch in rle:
        if ch.isdigit(): n += ch; continue
        k = int(n) if n else 1; n = ''
        if ch in 'b.': x += k
        elif ch in 'oA':
            for _ in range(k): out += [x, y]; x += 1
        elif ch == '$': y += k; x = 0
        elif ch == '!': break
    return out

def putcells(cl, dx=0, dy=0, axx=1, axy=0, ayx=0, ayy=1, mode='or'):
    assert (axx, axy, ayx, ayy, mode) == (1, 0, 0, 1, 'or')
    for i in range(0, len(cl) - 1, 2):
        _cells.add((cl[i] + dx, cl[i + 1] + dy))

def getcells(rect):
    if not rect: return []
    x, y, w, h = rect
    sel = sorted((cy, cx) for (cx, cy) in _cells if x <= cx < x + w and y <= cy < y + h)
    out = []
    for cy, cx in sel: out += [cx, cy]
    return out

def getrect():
    if not _cells: return []
    xs = [c[0] for c in _cells]; ys = [c[1] for c in _cells]
    return [min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1]

def getpop(): return str(len(_cells))
def empty(): return not _cells
def getcell(x, y): return 1 if (x, y) in _cells else 0
def setcell(x, y, v):
    if v: _cells.add((x, y))
    else: _cells.discard((x, y))

def run(n):
    global _cells, _gen
    for _ in range(n):
        acc = {}
        for (x, y) in _cells:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    # cell (x,y) sits at offset (-dx,-dy) from centre (x+dx, y+dy)
                    bit = 8 - (3 * (1 - dy) + (1 - dx))
                    k = (x + dx, y + dy)
                    acc[k] = acc.get(k, 0) | (1 << bit)
        _cells = {k for k, idx in acc.items() if _table[idx]}
        _gen += 1
        global _runs
        if _runs is not None: _runs += 1

def _i32(v):
    v &= 0xffffffff
    return v - (1 << 32) if v & 0x80000000 else v

def hash(rect):
    x, y, w, h = rect
    hv = 31415962
    for cy, cx in sorted((cy, cx) for (cx, cy) in _cells if x <= cx < x + w and y <= cy < y + h):
        hv = _i32(hv * 1000003) ^ (cy - y); hv = _i32(hv)
        hv = _i32(hv * 1000003) ^ (cx - x); hv = _i32(hv)
    return hv

def select(rect):
    global _sel
    _sel = list(rect) if rect else None
def getselrect(): return list(_sel) if _sel else []

def _inside(c, r): return r[0] <= c[0] < r[0] + r[2] and r[1] <= c[1] < r[1] + r[3]

def rotate(direction):  # 0 = clockwise, 1 = anticlockwise (Selection::Rotate / RotatePattern)
    global _cells, _sel
    left, top, w, h = _sel; right = left + w - 1; bottom = top + h - 1
    halfht = (bottom - top) // 2; halfwd = (right - left) // 2
    midy = top + halfht; midx = left + halfwd
    ntop = midy + left - midx; nbottom = midy + right - midx
    nleft = midx + top - midy; nright = midx + bottom - midy
    moved = set(); keep = set()
    for c in _cells:
        if _inside(c, _sel):
            cx, cy = c
            if direction == 0: moved.add((nright - (cy - top), ntop + (cx - left)))
            else: moved.add((nleft + (cy - top), nbottom - (cx - left)))
        else:
            keep.add(c)
    assert not keep, "mock only supports selections enclosing the pattern"
    _cells = moved
    _sel = [nleft, ntop, nright - nleft + 1, nbottom - ntop + 1]

def flip(direction):  # 0 = left-right, 1 = top-bottom, about the selection centre
    global _cells
    left, top, w, h = _sel; right = left + w - 1; bottom = top + h - 1
    new_ = set()
    for c in _cells:
        if _inside(c, _sel):
            new_.add((left + right - c[0], c[1]) if direction == 0 else (c[0], top + bottom - c[1]))
        else:
            new_.add(c)
    _cells = new_

def cut():
    global _clip, _cells
    _clip = [(c[0] - _sel[0], c[1] - _sel[1]) for c in _cells if _inside(c, _sel)]
    _cells = {c for c in _cells if not _inside(c, _sel)}

def paste(x, y, mode):
    assert mode == 'or'
    for (cx, cy) in _clip: _cells.add((cx + x, cy + y))

def clear(where):
    global _cells
    if where == 0: _cells = {c for c in _cells if not _inside(c, _sel)}
    else: _cells = {c for c in _cells if _inside(c, _sel)}

_runs = None
def _flush_runs():
    global _runs
    if _runs is not None: print('steps', _runs, flush=True)
    _runs = None
def show(s):
    global _runs
    _flush_runs(); print('show', s, flush=True); _runs = 0
def update(): pass
def autoupdate(b): pass
def warn(s): print('warn', s, flush=True)
def note(s): print('note', s, flush=True)
def exit(s=''):
    raise GollyExit(s)
