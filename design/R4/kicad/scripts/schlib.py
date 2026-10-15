import sys, math, uuid, re
sys.path.insert(0, '/work/scripts') if False else None
import sexp
from sexp import Sym, QStr, find, findall, prop

def fl(x): return float(x)
def R(v): return round(v, 3)

class Sheet:
    def __init__(self, path):
        self.path = path
        raw = open(path, newline='').read()
        self.eol = '\r\n' if raw.endswith('\r\n') else '\n'
        self.tree = sexp.parse(raw)
        self.libs = {str(e[1]): e for e in findall(find(self.tree, 'lib_symbols'), 'symbol')}
    def symbols(self):
        return findall(self.tree, 'symbol')
    def sym_by_ref(self, ref):
        for s in self.symbols():
            p = prop(s, 'Reference')
            if p and p[2] == ref: return s
        return None
    def lib_pins(self, libname):
        lib = self.libs[libname]
        pins = []
        def walk(n):
            for e in n:
                if isinstance(e, list) and e:
                    if e[0] == 'pin':
                        at = find(e, 'at'); num = find(e, 'number')[1]; name = find(e, 'name')[1]
                        pins.append(dict(num=str(num), name=str(name), x=fl(at[1]), y=fl(at[2]), etype=str(e[1])))
                    elif e[0] == 'symbol':
                        walk(e)
        walk(lib)
        return pins
    def pin_positions(self, sym):
        at = find(sym, 'at'); x0, y0 = fl(at[1]), fl(at[2]); rot = fl(at[3]) if len(at) > 3 else 0
        mirror = find(sym, 'mirror')
        out = []
        for p in self.lib_pins(str(find(sym, 'lib_id')[1])):
            px, py = p['x'], -p['y']
            if mirror:
                if mirror[1] == 'x': py = -py
                else: px = -px
            a = math.radians(-rot)
            # rotation in screen coords (y down): rotating CCW visually
            rx = px * math.cos(a) - py * math.sin(a)
            ry = px * math.sin(a) + py * math.cos(a)
            out.append(dict(p, ax=R(x0 + rx), ay=R(y0 + ry)))
        return out
    def wires(self):
        res = []
        for w in findall(self.tree, 'wire'):
            pts = findall(find(w, 'pts'), 'xy')
            res.append((w, [(R(fl(p[1])), R(fl(p[2]))) for p in pts]))
        return res
    def labels(self):
        res = []
        for kind in ('global_label', 'label', 'hierarchical_label'):
            for l in findall(self.tree, kind):
                at = find(l, 'at')
                res.append((l, str(l[1]), (R(fl(at[1])), R(fl(at[2])))))
        return res
    def no_connects(self):
        return [(n, (R(fl(find(n, 'at')[1])), R(fl(find(n, 'at')[2])))) for n in findall(self.tree, 'no_connect')]
    def pin_net_map(self):
        """naive connectivity: pin -> wire -> label (the generator's 1-wire-1-label style)."""
        wires = self.wires(); labels = self.labels(); ncs = self.no_connects()
        lab_at = {}
        for l, t, p in labels: lab_at.setdefault(p, []).append((l, t))
        res = {}
        for s in self.symbols():
            ref = str(prop(s, 'Reference')[2])
            for p in self.pin_positions(s):
                pt = (p['ax'], p['ay'])
                info = dict(pin=p, wire=None, label=None, nc=None, labtext=None)
                for n, q in ncs:
                    if q == pt: info['nc'] = n
                if pt in lab_at: info['label'], info['labtext'] = lab_at[pt][0]
                for w, pts in wires:
                    if pt in (pts[0], pts[-1]):
                        other = pts[-1] if pts[0] == pt else pts[0]
                        info['wire'] = w
                        if other in lab_at:
                            info['label'], info['labtext'] = lab_at[other][0]
                            info['labat'] = other
                res[(ref, p['num'])] = info
        return res
    def save(self, path=None):
        open(path or self.path, 'w', newline='').write(sexp.dumps(self.tree) + self.eol)

def new_uuid():
    return Sym(str(uuid.uuid4()))
