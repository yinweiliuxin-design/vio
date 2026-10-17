import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=load()
v1=add_via(b,'PWR_ONT',(65.971,25.008)); v2=add_via(b,'PWR_ONT',(72.1,23.9))
# snap tracks to via1 exact
for t in tracks(b,'PWR_ONT',vias=False):
    for get,setf in ((t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)):
        q=get()
        if abs(mm(q.x)-65.971)<0.01 and abs(mm(q.y)-25.008)<0.01: setf(v1.GetPosition())
print(collide_report(b,[v1,v2])); save(b)
