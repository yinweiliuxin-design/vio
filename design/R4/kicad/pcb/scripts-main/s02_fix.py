import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=load()
# fix PWR_ONT start stub to exact via center
v=[t for t in tracks(b,'PWR_ONT',vias=True) if abs(xy(t.GetPosition())[0]-65.971)<0.01][0]
for t in tracks(b,'PWR_ONT',layer='In5.Cu'):
    for get,setf in ((t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)):
        q=get()
        if abs(mm(q.x)-65.971)<0.05 and abs(mm(q.y)-25.0)<0.15: setf(v.GetPosition())
# drop zero-length
for t in tracks(b,'PWR_ONT',layer='In5.Cu'):
    if t.GetLength()<1000: b.Delete(t)
new=add_track(b,'GND','F.Cu',0.3,[(73.0,20.1),(73.0,19.25)])+[add_via(b,'GND',(73.0,19.25))]
print(collide_report(b,new))
save(b)
