# autoroute.py [--nets A,B] [--skip A,B] [--max N] : route DRC-unconnected pairs one by one
import json,subprocess,sys,os,re
S='/tmp/claude-0/-home-user-vio/3feb98dd-4d20-5b5c-81b5-59ee6194072c/scratchpad'; K=S+'/kicad/rootfs'
args=sys.argv[1:]
def opt(n,d=None):
    return args[args.index(n)+1] if n in args else d
only=set(opt('--nets','').split(',')) - {''}; skip=set(opt('--skip','').split(','))-{''}
maxn=int(opt('--max','999')); margin=float(opt('--margin','4'))
def ch(cmd): return subprocess.run(['chroot',K,'sh','-c','cd /work/r4/pcb && '+cmd],capture_output=True,text=True)
WIDTH={'V3D':0.3,'V3A':0.3,'V3LOAD':0.3,'VCAP1':0.25}
LAYERS='F.Cu,In2.Cu,In3.Cu,In4.Cu,In5.Cu,B.Cu'
failed=set(); done=0
while done<maxn:
    ch('HOME=/tmp kicad-cli pcb drc --refill-zones --format json -o /work/out/ar.json SmartVio-main-r3-linked.kicad_pcb')
    d=json.load(open(K+'/work/out/ar.json'))
    pairs=[]
    for u in d['unconnected_items']:
        it=u['items']; m=re.search(r'\[([^\]]*)\]',it[0]['description']); n=m.group(1) if m else ''
        if only and n not in only: continue
        if n in skip or n.startswith('unconnected-'): continue
        key=tuple(sorted(i['uuid'] for i in it))
        if key in failed: continue
        pairs.append((n,it,key))
    if not pairs: break
    n,it,key=pairs[0]
    json.dump([i['uuid'] for i in it],open(K+'/work/out/ar_ids.json','w'))
    ch('python3 /work/scripts/iteminfo.py /work/out/ar_ids.json /work/out/ar_info.json')
    info=json.load(open(K+'/work/out/ar_info.json'))
    A=info.get(it[0]['uuid']); B=info.get(it[1]['uuid'])
    if not A or not B: failed.add(key); print('noinfo',n); continue
    w=WIDTH.get(n,0.15)
    def ends(X,anchor):
        if X['kind']=='pad':
            out=[[X['pts'][0][0],X['pts'][0][1],X['layer'],max(0.05,X.get('r',0.1))]]
            if X.get('rect') and X['layer']!='*':
                x0,y0,x1,y1=X['bbox']; m=0.06
                xs=[x0+m+i*0.05 for i in range(int((x1-x0-2*m)/0.05)+1)]; ys=[y0+m+i*0.05 for i in range(int((y1-y0-2*m)/0.05)+1)]
                out+=[[x,y,X['layer'],0.0] for x in xs for y in ys]
            return out
        if X['kind']=='via': return [[X['pts'][0][0],X['pts'][0][1],'*',0.05]]
        (ax,ay),(bx,by)=X['pts']; L=max(1e-6,((ax-bx)**2+(ay-by)**2)**0.5); n=int(L/0.1)+1
        pts=[[ax+(bx-ax)*i/n,ay+(by-ay)*i/n,X['layer'],0.0] for i in range(n+1)]
        p=min(X['pts'],key=lambda q:(q[0]-anchor['x'])**2+(q[1]-anchor['y'])**2)
        return [[p[0],p[1],X['layer'],0.05]]+pts
    sa=ends(A,it[0]['pos']); sb=ends(B,it[1]['pos'])
    ok=False
    wl=[w]+([0.2,0.15] if w>0.2 else [])
    tries=[(mg,ww) for ww in wl for mg in (margin,margin*2.5)]
    for mg,w in tries:
        xs=[p[0] for p in sa+sb]; ys=[p[1] for p in sa+sb]
        win='%.2f,%.2f,%.2f,%.2f'%(max(0,min(xs)-mg),max(0,min(ys)-mg),min(74.6,max(xs)+mg),min(42.6,max(ys)+mg))
        lay=LAYERS
        if n in ('ADC_SCK','ADC_SCK_SRC'): lay='F.Cu,In2.Cu,In5.Cu,B.Cu'
        if n=='GND':
            spec={'start':sa,'goal_layer':'In1.Cu','via_cost':0.5,'layers':lay.split(',')+['In1.Cu']}
            lay=lay+',In1.Cu'
        else:
            spec={'start':sa,'goal':sb,'via_cost':1.0}
        r=subprocess.run([S+'/rt/route.sh','ar',n,str(w),lay,win,json.dumps(spec)],capture_output=True,text=True)
        print(n,win,r.stdout.strip()[-120:])
        if 'ok cost' not in r.stdout: continue
        a=ch('python3 /work/scripts/apply_route.py /work/out/r_ar.json %s %s'%(n,w))
        if 'saved' in a.stdout: ok=True; break
        print('  apply failed:',a.stdout.strip()[-300:])
    if not ok: failed.add(key); print('FAILED',n,[i['description'] for i in it])
    else: done+=1
print('routed',done,'failed',len(failed))
json.dump([list(k) for k in failed],open(K+'/work/out/ar_failed.json','w'))
