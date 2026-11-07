# Run hotdogPi's original Jul-6-2021 script against the mock golly module.
# Only configuration lines are edited (each edit asserted to apply exactly once).
# usage: python3 run_oracle.py RULE RLE X0 X1 Y0 Y1 [key=value ...]
#   mode=C2|C4|D4|X4|D8  a=0|1  gens=N gens2=N  rotate=1  stop=1
#   catalysts=1 : keep the author's catalyst lines as posted (block cells, row exclusion,
#                 x==1/y<26 resume, x<0&y<0 skip, (1,26) already-found)
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
rule, rle, x0, x1, y0, y1 = sys.argv[1:7]
opt = dict(a.split('=', 1) for a in sys.argv[7:])
mode = opt.get('mode', 'C2')
os.environ['MOCK_RULE'] = rule
src = open(os.path.join(here, 'hotdogpi_jul6.py')).read()

def edit(old, new, count=1):
    global src
    assert src.count(old) == count, old
    src = src.replace(old, new)

edit("input_pattern = g.parse('14b2o$6b3o5b2o$5bo3bo$4bo5bo$4bo5bo$4bo5bo$5bo3bo2b2o$6b3o3bobo$14bo$14b2o$2o$2o!')",
     "input_pattern = g.parse('%s')" % rle)
edit("mode = 'C2' #C2, C4, D4, X4, D8", "mode = '%s'" % mode)
if 'a' in opt:
    edit("    a = 1   #1 if even symmetry, 0 if odd; C4 and D8 only", "    a = %s" % opt['a'])
ranges = {'C1': "1, 30, 6, 30", 'C2': "1, 30, 6, 30", 'C4': "-15, 15, 0, 10", 'D4': "width+1, width+15, height+1, height+15",
          'X4': "-20, 20, -20, 15", 'D8': "0, 15, 0, 15"}
edit("start_x, end_x, start_y, end_y = %s" % ranges[mode], "start_x, end_x, start_y, end_y = %s, %s, %s, %s" % (x0, x1, y0, y1))
if opt.get('catalysts') != '1':
    # author: comment these out when there are no catalysts
    edit("            if x == 1 and y < 26:\n                continue\n", "")
    edit("            if x < 0 and y < 0:\n                continue\n", "")
    edit("if not g.getcell(14,0) or not g.getcell(0,2) or not g.getcell(0,10): #block broken\n", "if False:\n", 2)
    # row exclusion: without these two lines the temp save/restore is a no-op
    edit("                    g.select([-50,14,100,y+height-17])\n                    g.clear(1)\n", "")
edit("for generation in range(500):", "for generation in range(%s):" % opt.get('gens', '500'))
edit("for generation1 in range(2000):", "for generation1 in range(%s):" % opt.get('gens2', '2000'))
if opt.get('rotate') == '1':
    edit("rotate = False", "rotate = True")
if opt.get('stop') != '1':
    edit("""                                    g.warn('Found!: %s, %s, %s' % (x, y, generation))
                                    g.update()
                                    g.exit('Found!')""",
         """                                    g.warn('Found!: %s, %s, %s' % (x, y, generation))
                                    print('DETAIL', z, w, spark, generation1+1, flush=True)
                                    break""")
else:
    edit("""                                    g.warn('Found!: %s, %s, %s' % (x, y, generation))""",
         """                                    g.warn('Found!: %s, %s, %s' % (x, y, generation))
                                    print('DETAIL', z, w, spark, generation1+1, flush=True)""")
if mode == 'C1':   # extension (not in the original): single copy, single spark
    edit("copies = 8 if mode == 'D8' else 2 if mode == 'C2' else 4", "copies = 8 if mode == 'D8' else 2 if mode == 'C2' else 1 if mode == 'C1' else 4")
    edit("if mode == 'C2':\n    r_up = input_pattern", "if mode == 'C1':\n    r_up = input_pattern\nelif mode == 'C2':\n    r_up = input_pattern")
    edit("        for z in range(1 if mode in ('C2','X4') else 8 if mode == 'D8' else 4):", "        for z in range(1 if mode in ('C1','C2','X4') else 8 if mode == 'D8' else 4):")
    edit("            if mode == 'C2':\n                g.putcells(r_down, 0, 0)", "            if mode == 'C1':\n                g.putcells(r_up, x, y)\n                num1 = int(g.getpop())\n            elif mode == 'C2':\n                g.putcells(r_down, 0, 0)")
    edit("                            if mode == 'C2':\n                                g.setcell(min_x-2,spark1+min(edge),1)", "                            if mode == 'C1':\n                                g.setcell(min_x-2,spark1+min(edge),1)\n                            elif mode == 'C2':\n                                g.setcell(min_x-2,spark1+min(edge),1)")
    edit("'''Main loop'''", "if mode == 'C1':\n    start_x, end_x, start_y, end_y = 0, 0, 0, 0\n'''Main loop'''")
    if opt.get('selfsym') == '1':   # copy each spark by the pattern's own symmetries
        edit("            if mode == 'C1':\n                g.putcells(r_up, x, y)\n                num1 = int(g.getpop())",
             "            if mode == 'C1':\n                g.putcells(r_up, x, y)\n                num1 = int(g.getpop())\n"
             "                _P0 = set(zip(g.getcells(g.getrect())[0::2], g.getcells(g.getrect())[1::2]))\n"
             "                _cx2 = min(a for a, b in _P0) + max(a for a, b in _P0); _cy2 = min(b for a, b in _P0) + max(b for a, b in _P0)\n"
             "                _syms = [m for m in [(0,-1,1,0),(-1,0,0,-1),(0,1,-1,0),(-1,0,0,1),(1,0,0,-1),(0,1,1,0),(0,-1,-1,0)] if {((m[0]*(2*a-_cx2)+m[1]*(2*b-_cy2)+_cx2)/2, (m[2]*(2*a-_cx2)+m[3]*(2*b-_cy2)+_cy2)/2) for a, b in _P0} == _P0]")
        edit("                            if mode == 'C1':\n                                g.setcell(min_x-2,spark1+min(edge),1)",
             "                            if mode == 'C1':\n                                g.setcell(min_x-2,spark1+min(edge),1)\n"
             "                                for m in _syms:\n"
             "                                    _X = 2*(min_x-2)-_cx2; _Y = 2*(spark1+min(edge))-_cy2\n"
             "                                    g.setcell((m[0]*_X+m[1]*_Y+_cx2)//2, (m[2]*_X+m[3]*_Y+_cy2)//2, 1)")
sys.path.insert(0, os.path.join(here, 'mock'))
import golly
try:
    exec(compile(src, 'hotdogpi_jul6_edited.py', 'exec'), {'__name__': '__main__'})
except golly.GollyExit as e:
    print('exit', e)
golly._flush_runs()
print('END')
