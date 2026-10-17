# patch stackup of a saved FPC kicad_pcb: usage fpcstack.py file cu_mm
import sys,re
p,cu=sys.argv[1],float(sys.argv[2])
s=open(p).read()
cov=0.0275; core=0.025; tot=round(2*cov+2*cu+core,4)
i=s.index('(stackup'); depth=0
for j in range(i,len(s)):
    if s[j]=='(': depth+=1
    elif s[j]==')':
        depth-=1
        if depth==0: break
new=f'''(stackup
			(layer "F.Mask" (type "Solder Mask") (color "Coverlay PI 12.5um + adhesive 15um") (thickness {cov}) (material "PI coverlay") (epsilon_r 3.3) (loss_tangent 0.02))
			(layer "F.Cu" (type "copper") (thickness {cu}))
			(layer "dielectric 1" (type "core") (thickness {core}) (material "PI adhesiveless") (epsilon_r 3.3) (loss_tangent 0.02))
			(layer "B.Cu" (type "copper") (thickness {cu}))
			(layer "B.Mask" (type "Solder Mask") (color "Coverlay PI 12.5um + adhesive 15um") (thickness {cov}) (material "PI coverlay") (epsilon_r 3.3) (loss_tangent 0.02))
			(copper_finish "ENIG")
			(dielectric_constraints no)
		)'''
s=s[:i]+new+s[j+1:]
s=re.sub(r'\(general\s*\(thickness [\d.]+\)','(general (thickness %s)'%tot,s,count=1)
open(p,'w').write(s); print('stackup',tot)
