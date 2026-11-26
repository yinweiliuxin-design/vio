import sys,math
def segd(p1,p2,q1,q2):
    def pd(p,a,b):
        ax,ay=a; bx,by=b; px,py=p; dx,dy=bx-ax,by-ay; L=dx*dx+dy*dy
        t=0 if L==0 else max(0,min(1,((px-ax)*dx+(py-ay)*dy)/L)); return math.hypot(px-ax-t*dx,py-ay-t*dy)
    def inter(a,b,c,d):
        def o(p,q,r): return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
        return o(a,b,c)*o(a,b,d)<0 and o(c,d,a)*o(c,d,b)<0
    if inter(p1,p2,q1,q2): return 0
    return min(pd(p1,q1,q2),pd(p2,q1,q2),pd(q1,p1,p2),pd(q2,p1,p2))
T=[]
for l in open(sys.argv[1]):
    a=l.split()
    if a[0] in ('F.Cu','B.Cu'): T.append((a[0],a[1],float(a[2]),(float(a[3]),float(a[4])),(float(a[6]),float(a[7]))))
F=[t for t in T if t[0]=='F.Cu' and (t[1].startswith('LED') or t[1]=='PWR_PB')]
Bs=[t for t in T if t[0]=='B.Cu' and t[1].startswith('SPK')]
m=min(segd(f[3],f[4],b[3],b[4])-f[2]/2-b[2]/2 for f in F for b in Bs)
print(sys.argv[1].split('/')[-1],'min XY edge gap F(LED/PWR) vs B(SPK) = %.3f mm (negative = overlap)'%m)
