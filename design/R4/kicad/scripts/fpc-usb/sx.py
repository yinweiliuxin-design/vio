# minimal top-level s-expression splitter for kicad files
def top_children(s):
    # returns list of (start,end) spans of top-level children of root list
    i=s.index('(')+1; depth=0; spans=[]; st=None; instr=False; esc=False
    j=i
    while j<len(s):
        c=s[j]
        if instr:
            if esc: esc=False
            elif c=='\\': esc=True
            elif c=='"': instr=False
        else:
            if c=='"': instr=True
            elif c=='(':
                if depth==0: st=j
                depth+=1
            elif c==')':
                if depth==0: break
                depth-=1
                if depth==0: spans.append((st,j+1))
        j+=1
    return spans
def head(s,span):
    t=s[span[0]+1:span[0]+40]
    return t.split()[0].rstrip(')')
def strip(src,dst,keep=('version','generator','generator_version','general','paper','layers','setup','embedded_fonts','title_block','property','net')):
    s=open(src).read(); sp=top_children(s)
    parts=[s[a:b] for a,b in sp if head(s,(a,b)) in keep]
    open(dst,'w').write('(kicad_pcb '+' '.join(parts)+')\n')
if __name__=='__main__':
    import sys; strip(sys.argv[1],sys.argv[2])
