import os, subprocess
B=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "regionspark")
def tab(r): return subprocess.run([B,"--dump-rule",r],capture_output=True,text=True).stdout.strip()
def grid(x): return [[(x>>(8-(3*r+c)))&1 for c in range(3)] for r in range(3)]
def ungrid(g): return sum(g[r][c]<<(8-(3*r+c)) for r in range(3) for c in range(3))
def rot(x): g=grid(x); return ungrid([[g[2-c][r] for c in range(3)] for r in range(3)])
def flip(x): g=grid(x); return ungrid([[g[r][2-c] for c in range(3)] for r in range(3)])
def orbit(x):
    s=set()
    for f in (x,flip(x)):
        for _ in range(4): s.add(f); f=rot(f)
    return s
pc=lambda i: bin(i&0x1ef).count('1')
L={1:"ce",2:"ceaikn",3:"ceaiknjqry",4:"ceaiknjqrytwz",5:"ceaiknjqry",6:"ceaikn",7:"ce"}
ok=True
for n in range(1,8):
    sets=[]
    for l in L[n]:
        t=tab("B%d%s/S"%(n,l)); on={i for i in range(512) if t[i]=='1'}
        if any(pc(i)!=n or i&16 for i in on): ok=False; print("bad count",n,l)
        if on!=orbit(min(on)): ok=False; print("not one orbit",n,l)
        sets.append(on)
    allon={i for i in range(512) if not i&16 and pc(i)==n}
    if set().union(*sets)!=allon or sum(map(len,sets))!=len(allon): ok=False; print("not a partition",n)
    if n>=5:
        for l,s in zip(L[n],sets):
            s2={i for i in range(512) if tab("B%d%s/S"%(8-n,l))[i]=='1'}
            if s!={i^0x1ef for i in s2}: ok=False; print("complement",n,l)
t=tab("B3/S23")
ok&= t==''.join('1' if ((not i&16 and pc(i)==3) or (i&16 and pc(i) in (2,3))) else '0' for i in range(512))
a=tab("b3s23-q4i"); b=tab("B3/S2"); c=tab("B/S3q"); d=tab("B/S3"); e=tab("B/S4i")
ok&= a==''.join('1' if (b[i]=='1' or (d[i]=='1' and c[i]=='0') or e[i]=='1') else '0' for i in range(512))
ok&= a==tab("B3/S2-3q4i".replace("2-3q","23-q"))
# spot checks of letter geometry (LifeWiki pictures, from memory [unsure]): 2a = N+NE, 2i = N+S, 3i = row of 3 on a side
def has(r,cells): return tab(r)[cells]=='1'
ok&= has("B2a/S",128+64) and has("B2i/S",128+2) and has("B3i/S",256+128+64) and has("B2c/S",256+64) and has("B2n/S",256+1)
print("structural tests", "PASS" if ok else "FAIL")
print("errors:", tab("B0/S"), "|", tab("B9/S"), "|", tab("B2x/S"), "|", tab("B1a/S"))
