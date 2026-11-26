import pdfplumber, sys, json, re, collections
pdf = pdfplumber.open(sys.argv[1])
out = {"components": {}, "pages": {}}
issues = []
def near(a,b,t=0.6): return abs(a-b) <= t
for pi, p in enumerate(pdf.pages, start=1):
    if pi == 1: continue
    words = p.extract_words(x_tolerance=1.0, y_tolerance=1.0, extra_attrs=["size"])
    title = [w['text'] for w in words if abs(w['size']-9.0)<0.1]
    small = [w for w in words if abs(w['size']-3.95)<0.05]
    labels = [w for w in words if abs(w['size']-3.36)<0.05]
    # dedupe rects
    rects = []
    seen=set()
    for r in p.rects:
        k=(round(r['x0'],1),round(r['top'],1),round(r['x1'],1),round(r['bottom'],1))
        if k in seen: continue
        seen.add(k); rects.append(k)
    lines = [(l['x0'],l['top'],l['x1'],l['bottom']) for l in p.lines]
    used_lines=set(); used_labels=set()
    comps=[]
    for (x0,t,x1,b) in rects:
        # ref + value: small words above rect within 25, horizontally overlapping center
        cx=(x0+x1)/2
        above=[w for w in small if w['bottom']<=t+0.5 and w['bottom']>t-26 and w['x0']<cx+40 and w['x1']>cx-40]
        above.sort(key=lambda w:w['top'])
        rows=collections.OrderedDict()
        for w in above:
            key=round(w['top'])
            rows.setdefault(key,[]).append(w)
        rowtexts=[' '.join(x['text'] for x in sorted(v,key=lambda w:w['x0'])) for v in rows.values()]
        ref = rowtexts[0] if rowtexts else '?'
        val = ' | '.join(rowtexts[1:]) if len(rowtexts)>1 else ''
        pins=[]
        for li,(lx0,lt,lx1,lb) in enumerate(lines):
            if abs(lt-lb)>0.2: continue
            y=lt
            if not (t-0.5<=y<=b+0.5): continue
            if near(lx1,x0):   side='L'; outer=lx0
            elif near(lx0,x1): side='R'; outer=lx1
            else: continue
            used_lines.add(li)
            # pin number: small word above line between line ends
            cand=[w for w in small if w['bottom']<=y+0.5 and w['bottom']>y-6 and w['x0']>=min(lx0,lx1)-3 and w['x1']<=max(lx0,lx1)+3]
            num = cand[0]['text'] if cand else '?'
            # pin name inside rect
            nm=[w for w in small if w['top']<y+1 and w['bottom']>y-1 and w['x0']>=x0-0.5 and w['x1']<=x1+0.5]
            if side=='L': nm=sorted(nm,key=lambda w:w['x0'])[:1]
            else: nm=sorted(nm,key=lambda w:-w['x1'])[:1]
            pname = nm[0]['text'] if nm else ''
            # label
            lc=[]
            for wi,w in enumerate(labels):
                wc=(w['top']+w['bottom'])/2
                if abs(wc-y)>2.6: continue
                if side=='L' and abs(w['x0']-(outer-13.5))<1.6: lc.append((abs(w['x0']-(outer-13.5)),wi,w))
                if side=='R' and abs(w['x1']-(outer+12.9))<1.6: lc.append((abs(w['x1']-(outer+12.9)),wi,w))
            lc.sort(key=lambda z:z[0])
            net = lc[0][2]['text'] if lc else None
            if lc: used_labels.add(lc[0][1])
            pins.append({"num":num,"name":pname,"net":net,"side":side,"y":round(y,1)})
        comps.append({"ref":ref,"value":val,"rect":[x0,t,x1,b],"pins":pins})
    # NC markers: short diagonal lines
    diag=[(l['x0'],l['top'],l['x1'],l['bottom']) for l in p.lines if abs(l['top']-l['bottom'])>0.2 and abs(l['x0']-l['x1'])>0.2]
    for c in comps:
        for pn in c['pins']:
            if pn['net'] is None:
                # check NC: diagonal line near outer end
                x0,t,x1,b=c['rect']
                ox = x0-14.4 if pn['side']=='L' else x1+14.4
                nc=any(abs((d[0]+d[2])/2-ox)<4 and abs((d[1]+d[3])/2-pn['y'])<4 for d in diag)
                pn['net']='<NC>' if nc else '<UNLABELED>'
    unused=[labels[i]['text'] for i in range(len(labels)) if i not in used_labels]
    other_lines=[lines[i] for i in range(len(lines)) if i not in used_lines and abs(lines[i][1]-lines[i][3])<0.2 ]
    out['pages'][pi]={"title":' '.join(title),"ncomp":len(comps),"unused_labels":unused,"other_hlines":len(other_lines),"diag":len(diag)}
    for c in comps:
        c['page']=pi
        if c['ref'] in out['components']:
            issues.append(f"dup ref {c['ref']} p{pi} vs p{out['components'][c['ref']]['page']}")
            c['ref']=c['ref']+f"@p{pi}"
        out['components'][c['ref']]=c
out['issues']=issues
json.dump(out, open(sys.argv[2],'w'), ensure_ascii=False, indent=1)
for k,v in out['pages'].items(): print(k, v)
print(issues)
