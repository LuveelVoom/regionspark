import sys,re
def oracle(f):
    ev=[]; last=None
    for l in open(f):
        if l.startswith('show'): m=re.match(r'show \((-?\d+), (-?\d+)\)',l); ev.append(('visit',int(m[1]),int(m[2])))
        elif l.startswith('steps'): ev.append(('steps',int(l.split()[1])))
        elif l.startswith('warn Found'): last=[int(v) for v in l.split(':')[1].split(',')]
        elif l.startswith('DETAIL'):
            p=l.split(None,3); rest=p[3].rsplit(None,1)
            sp=tuple(int(v) for v in re.findall(r'-?\d+',rest[0]))
            ev.append(('found',*last,int(p[1]),int(p[2]),sp,int(rest[1])))
        elif l.startswith('warn Already'): ev.append(('already',l.strip()[5:]))
    return ev
def port(f):
    ev=[]
    for l in open(f):
        if l.startswith('visit'): a=l.split(); ev.append(('visit',int(a[1]),int(a[2])))
        elif l.startswith('steps'): ev.append(('steps',int(l.split()[1])))
        elif l.startswith('Found'):
            m=re.match(r'Found!: (-?\d+), (-?\d+), (-?\d+)  \[z=(\d+) w=(\d+) edge=\S+ spark=\(([^)]*)\) after=(\d+)',l)
            ev.append(('found',int(m[1]),int(m[2]),int(m[3]),int(m[4]),int(m[5]),tuple(int(v) for v in m[6].split(',')),int(m[7])))
        elif l.startswith('Already'): ev.append(('already',l.strip()))
    return ev
a=oracle(sys.argv[1]); b=port(sys.argv[2])
# port prints steps after the finds of a visit; oracle prints them at the next show: normalise order
def norm(ev):
    out=[]; cur=[]
    for e in ev:
        if e[0]=='visit':
            if cur: out.append(sorted(cur,key=str))
            cur=[e]
        else: cur.append(e)
    if cur: out.append(sorted(cur,key=str))
    return out
A=norm(a); B=norm(b)
print("oracle visits",len(A),"finds",sum(e[0]=='found' for e in a),"| port visits",len(B),"finds",sum(e[0]=='found' for e in b))
for i,(x,y) in enumerate(zip(A,B)):
    if x!=y: print("FIRST DIFF at visit",i); print(" oracle",x[:6]); print(" port  ",y[:6]); break
else:
    print("IDENTICAL" if len(A)==len(B) else "length differs")
