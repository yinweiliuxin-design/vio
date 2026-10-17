# edit DSN: In1 -> power; USB D+/- class restricted to F/B with 0.2 width
import sys,re
p=sys.argv[1]; s=open(p).read()
s=s.replace("(layer In1.Cu\n      (type signal)","(layer In1.Cu\n      (type power)")
dnets=sys.argv[2].split(',') if len(sys.argv)>2 else []
m=re.search(r'\(class kicad_default (.*?)\n      \(circuit',s,re.S)
names=m.group(1).split()
rest=[n for n in names if n not in dnets]
newcls='(class kicad_default '+' '.join(rest)+'\n      (circuit'
s=s[:m.start()]+newcls+s[m.end():]
if dnets:
    add='''    (class USBD '''+' '.join(dnets)+'''
      (circuit
        (use_via "Via[0-3]_600:300_um")
        (use_layer F.Cu B.Cu)
      )
      (rule
        (width 200)
        (clearance 150)
      )
    )
'''
    i=s.index('  (wiring'); j=s.rindex('  )',0,i); s=s[:j]+add+s[j:]
open(p,'w').write(s)
