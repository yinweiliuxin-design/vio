#!/usr/bin/env python3
"""SmartVio R4 schematic ECO editor (S-expression aware).

Rebuilds work/r4/eda from the pristine R3 copy (work/r3/eda) on every run, so it is
idempotent and reviewable. Applies eco-schematic.json E-01..E-14 and the schematic side
of eco-pcb.json L-10 / L-12 / L-13 / L-19.  Writes an edit log to work/r4/sch-eco-log.json.
"""
import sys, os, shutil, copy, uuid, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sexp
from sexp import Sym, QStr, find, findall, prop
import schlib

WORK = os.path.abspath(os.path.join(HERE, '..'))
SRC = os.path.join(WORK, 'r3', 'eda')
DST = os.path.join(WORK, 'r4', 'eda')
ROOT_UUID = '688ce4c7-cd63-5d1a-8608-cca940cc1bf4'
DATE = '2026-10-15'
REV = 'R4 SAMPLE ECO / HOLD'
LOG = []

def log(eco, action, **kw):
    d = dict(eco=eco, action=action); d.update(kw); LOG.append(d)

def num(x):
    s = ('%.4f' % x).rstrip('0').rstrip('.')
    return Sym(s if s not in ('-0', '') else '0')

def g(k):  # 1.27 grid
    return round(k * 1.27, 4)

def eol(path):
    return '\r\n' if open(path, newline='').read().endswith('\r\n') else '\n'

def write_like(path, text, src):
    open(path, 'w', newline='').write(text + eol(src))

def U():
    return Sym(str(uuid.uuid4()))

# ---------------------------------------------------------------- load
if os.path.isdir(DST):
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)
ROOT_PATH = os.path.join(DST, 'SmartVio.kicad_sch')
root = sexp.parse(open(ROOT_PATH).read())
SHEET_UUID = {}
for sh in findall(root, 'sheet'):
    SHEET_UUID[prop(sh, 'Sheetfile')[2]] = str(find(sh, 'uuid')[1])
LIB_PATH = os.path.join(DST, 'SmartVio.kicad_sym')
lib = sexp.parse(open(LIB_PATH).read())
SHEETS = {}

def sheet(name):
    if name not in SHEETS:
        SHEETS[name] = schlib.Sheet(os.path.join(DST, name + '.kicad_sch'))
    return SHEETS[name]

def lib_sym(name):
    for e in findall(lib, 'symbol'):
        if e[1] == name:
            return e
    return None

def emb_lib(sh, ref):
    return sh.libs['SmartVio:' + ref]

def set_prop(node, name, value):
    p = prop(node, name)
    p[2] = QStr(value)

def add_hidden_prop(sym, name, value):
    if prop(sym, name):
        set_prop(sym, name, value); return
    at = find(sym, 'at')
    newp = [Sym('property'), QStr(name), QStr(value), [Sym('at'), at[1], at[2], Sym('0')],
            [Sym('effects'), [Sym('font'), [Sym('size'), Sym('1'), Sym('1')]], Sym('hide')]]
    idx = sym.index(find(sym, 'instances'))
    sym.insert(idx, newp)

def pin_dir(pin_angle):
    a = int(round(float(pin_angle))) % 360
    return {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[a]

def lib_pin_nodes(libsym):
    out = []
    def walk(n):
        for e in n:
            if isinstance(e, list) and e:
                if e[0] == 'pin': out.append(e)
                elif e[0] == 'symbol': walk(e)
    walk(libsym)
    return out

def pin_geom(sh, sym):
    """[(num, name, etype, (ax, ay), outward_dir)] -- symbols are all unrotated in this design."""
    at = find(sym, 'at')
    assert len(at) < 4 or float(at[3]) == 0, 'rotated symbol not supported'
    assert find(sym, 'mirror') is None
    x0, y0 = float(at[1]), float(at[2])
    res = []
    for p in lib_pin_nodes(sh.libs[str(find(sym, 'lib_id')[1])]):
        pa = find(p, 'at')
        res.append((str(find(p, 'number')[1]), str(find(p, 'name')[1]), str(p[1]),
                    (round(x0 + float(pa[1]), 3), round(y0 - float(pa[2]), 3)), pin_dir(pa[3])))
    return res

def add_wire_label(sh, pt, d, net, length=5.08):
    end = (pt[0] + d[0] * length, pt[1] + d[1] * length)
    w = [Sym('wire'), [Sym('pts'), [Sym('xy'), num(pt[0]), num(pt[1])], [Sym('xy'), num(end[0]), num(end[1])]],
         [Sym('stroke'), [Sym('width'), Sym('0')], [Sym('type'), Sym('default')]], [Sym('uuid'), U()]]
    # labels point outward (text extends away from the symbol), unlike the R3 generator's inward labels
    if d == (-1, 0):
        ang, just = '180', 'right'
    elif d == (1, 0):
        ang, just = '0', 'left'
    elif d == (0, 1):
        ang, just = '270', 'left'
    else:
        ang, just = '90', 'left'
    l = [Sym('global_label'), QStr(net), [Sym('shape'), Sym('passive')],
         [Sym('at'), num(end[0]), num(end[1]), Sym(ang)],
         [Sym('effects'), [Sym('font'), [Sym('size'), Sym('0.85'), Sym('0.85')]], [Sym('justify'), Sym(just)]],
         [Sym('uuid'), U()]]
    sh.tree.append(w); sh.tree.append(l)

def add_nc(sh, pt):
    sh.tree.append([Sym('no_connect'), [Sym('at'), num(pt[0]), num(pt[1])], [Sym('uuid'), U()]])

def add_text(sh, text, x, y, size=1.3):
    sh.tree.append([Sym('text'), QStr(text), [Sym('at'), num(x), num(y), Sym('0')],
                    [Sym('effects'), [Sym('font'), [Sym('size'), num(size), num(size)]], [Sym('justify'), Sym('left')]],
                    [Sym('uuid'), U()]])

def set_title(sh, title=None):
    tb = find(sh.tree, 'title_block')
    if title: find(tb, 'title')[1] = QStr(title)
    find(tb, 'rev')[1] = QStr(REV)
    find(tb, 'date')[1] = QStr(DATE)

# ---------------------------------------------------------------- primitive ECO operations
def change_value(eco, sname, ref, value, mpn, footprint=None, spec=None):
    sh = sheet(sname); sym = sh.sym_by_ref(ref)
    assert sym is not None, ref
    old = dict(value=prop(sym, 'Value')[2], mpn=prop(sym, 'MPN')[2], footprint=prop(sym, 'Footprint')[2])
    set_prop(sym, 'Value', value); set_prop(sym, 'Specification', spec or value); set_prop(sym, 'MPN', mpn)
    if footprint: set_prop(sym, 'Footprint', footprint)
    add_hidden_prop(sym, 'R4_ECO', eco)
    for ls in (emb_lib(sh, ref), lib_sym(ref)):
        set_prop(ls, 'Value', value)
    log(eco, 'change_value', sheet=sname, ref=ref, before=old,
        after=dict(value=value, mpn=mpn, footprint=footprint or old['footprint']))

def relabel(eco, sname, ref, pin, old, new, at):
    sh = sheet(sname); m = sh.pin_net_map(); info = m[(ref, pin)]
    assert info['labtext'] == old, (ref, pin, info['labtext'], old)
    assert abs(info['labat'][0] - at[0]) < 0.01 and abs(info['labat'][1] - at[1]) < 0.01, (ref, pin, info['labat'], at)
    # make sure this label serves only this pin
    users = [k for k, v in m.items() if v.get('label') is info['label']]
    assert users == [(ref, pin)], users
    info['label'][1] = QStr(new)
    log(eco, 'rewire', sheet=sname, ref=ref, pin=pin, before=old, after=new, label_at=list(at))

def set_pin_etype(sname, ref, pin, etype):
    sh = sheet(sname)
    for ls in (emb_lib(sh, ref), lib_sym(ref)):
        for p in lib_pin_nodes(ls):
            if str(find(p, 'number')[1]) == pin:
                p[1] = Sym(etype)

def connect_nc_pin(eco, sname, ref, pin, net, at, etype_if_nc='bidirectional'):
    sh = sheet(sname); sym = sh.sym_by_ref(ref)
    geo = {g_[0]: g_ for g_ in pin_geom(sh, sym)}[pin]
    pt = geo[3]
    assert abs(pt[0] - at[0]) < 0.01 and abs(pt[1] - at[1]) < 0.01, (ref, pin, pt, at)
    ncs = [n for n, q in sh.no_connects() if abs(q[0] - pt[0]) < 0.01 and abs(q[1] - pt[1]) < 0.01]
    assert len(ncs) == 1, (ref, pin, 'no_connect not found')
    sh.tree.remove(ncs[0])
    if geo[2] == 'no_connect':
        set_pin_etype(sname, ref, pin, etype_if_nc)
    add_wire_label(sh, pt, geo[4], net)
    log(eco, 'connect_nc_pin', sheet=sname, ref=ref, pin=pin, pin_name=geo[1], before='no_connect', after=net,
        pin_type_changed=(geo[2] == 'no_connect'))

def find_template_instance(libname):
    for f in sorted(os.listdir(DST)):
        if f.startswith('A') and f.endswith('.kicad_sch'):
            sh = sheet(f[:-10])
            for s in sh.symbols():
                if str(find(s, 'lib_id')[1]) == libname:
                    return sh, s
    raise KeyError(libname)

def clone_libsym(src, newname, value, pin_renames=None):
    """src: embedded lib symbol (named SmartVio:XXX). returns embedded copy named SmartVio:newname."""
    old = str(src[1]).split(':', 1)[1]
    c = copy.deepcopy(src)
    c[1] = QStr('SmartVio:' + newname)
    for sub in findall(c, 'symbol'):
        sub[1] = QStr(str(sub[1]).replace(old + '_', newname + '_', 1))
    set_prop(c, 'Value', value)
    if pin_renames:
        for p in lib_pin_nodes(c):
            n = str(find(p, 'number')[1])
            if n in pin_renames: find(p, 'name')[1] = QStr(pin_renames[n])
    return c

def register_libsym(sh, embedded):
    find(sh.tree, 'lib_symbols').append(embedded)
    sh.libs[str(embedded[1])] = embedded
    l = copy.deepcopy(embedded)
    l[1] = QStr(str(embedded[1]).split(':', 1)[1])
    assert lib_sym(str(l[1])) is None, l[1]
    lib.append(l)

def place_symbol(sh, sname, ref, libname, x, y, value, footprint, mpn, ref_off, val_off,
                 dnp=False, in_bom=True, extra=None):
    sym = [Sym('symbol'), [Sym('lib_id'), QStr(libname)], [Sym('at'), num(x), num(y), Sym('0')], [Sym('unit'), Sym('1')],
           [Sym('in_bom'), Sym('yes' if in_bom else 'no')], [Sym('on_board'), Sym('yes')],
           [Sym('dnp'), Sym('yes' if dnp else 'no')], [Sym('uuid'), U()],
           [Sym('property'), QStr('Reference'), QStr(ref), [Sym('at'), num(x), num(y + ref_off), Sym('0')],
            [Sym('effects'), [Sym('font'), [Sym('size'), Sym('1.0'), Sym('1.0')]]]],
           [Sym('property'), QStr('Value'), QStr(value), [Sym('at'), num(x), num(y + val_off), Sym('0')],
            [Sym('effects'), [Sym('font'), [Sym('size'), Sym('1.0'), Sym('1.0')]]]]]
    props = [('Footprint', footprint), ('Specification', value), ('MPN', mpn), ('Release', 'HOLD - design review required')]
    for k, v in (extra or []):
        props.append((k, v))
    for k, v in props:
        sym.append([Sym('property'), QStr(k), QStr(v), [Sym('at'), num(x), num(y), Sym('0')],
                    [Sym('effects'), [Sym('font'), [Sym('size'), Sym('1'), Sym('1')]], Sym('hide')]])
    sym.append([Sym('instances'), [Sym('project'), QStr('SmartVio'),
                [Sym('path'), QStr('/%s/%s' % (ROOT_UUID, SHEET_UUID[sname + '.kicad_sch'])),
                 [Sym('reference'), QStr(ref)], [Sym('unit'), Sym('1')]]]])
    # insert after the last existing symbol instance to keep file ordering natural
    sh.tree.append(sym)
    return sym

def add_part(eco, sname, ref, template, x, y, value, footprint, mpn, pins, dnp=False, pin_renames=None, note=None):
    sh = sheet(sname)
    assert sh.sym_by_ref(ref) is None
    tsh, tinst = find_template_instance(template)
    tat = find(tinst, 'at')
    ref_off = float(prop(tinst, 'Reference')[3][2]) - float(tat[2])
    val_off = float(prop(tinst, 'Value')[3][2]) - float(tat[2])
    emb = clone_libsym(tsh.libs[template], ref, value, pin_renames)
    register_libsym(sh, emb)
    sym = place_symbol(sh, sname, ref, 'SmartVio:' + ref, x, y, value, footprint, mpn, ref_off, val_off, dnp=dnp,
                       extra=[('R4_ECO', eco)])
    geo = pin_geom(sh, sym)
    names = {g_[0]: g_ for g_ in geo}
    assert set(names) == set(pins), (ref, sorted(names), sorted(pins))
    for n, net in pins.items():
        gg = names[n]
        if net is None:
            add_nc(sh, gg[3])
        else:
            add_wire_label(sh, gg[3], gg[4], net)
    log(eco, 'add', sheet=sname, ref=ref, value=value, mpn=mpn, footprint=footprint, dnp=dnp, at=[x, y],
        pins={n: (pins[n] or 'no_connect') for n in pins}, note=note)

def remove_part(eco, sname, ref, note=None):
    sh = sheet(sname); sym = sh.sym_by_ref(ref)
    geo = pin_geom(sh, sym)
    removed = {}
    for n, name, et, pt, d in geo:
        for w, pts in sh.wires():
            if pt in (pts[0], pts[-1]):
                other = pts[-1] if pts[0] == pt else pts[0]
                for l, t, q in sh.labels():
                    if q == other:
                        sh.tree.remove(l); removed[n] = t
                sh.tree.remove(w)
        for nc, q in sh.no_connects():
            if q == pt:
                sh.tree.remove(nc); removed[n] = 'no_connect'
    sh.tree.remove(sym)
    ls = sh.libs.pop('SmartVio:' + ref)
    find(sh.tree, 'lib_symbols').remove(ls)
    lib.remove(lib_sym(ref))
    log(eco, 'remove', sheet=sname, ref=ref, pins=removed, note=note)

# ---------------------------------------------------------------- E-01 .. E-14
def split_after(after, mpn):
    v = after.replace(mpn, '').strip()
    return v

# E-01 J301 headphone detect (A12)
change_value('E-01', 'A12', 'R322', '100k', 'RC0603FR-07100KL')
change_value('E-01', 'A12', 'C320', '100nF X7R 10V', 'CC0603KRX7R7BB104',
             footprint='Passive_V26_ManufacturerLand:CC0603KRX7R7BB104')
relabel('E-01', 'A12', 'J301', '6', 'GND', 'HP_DET_B', (388.62, 134.62))
add_text(sheet('A12'), 'R4 ECO E-01 (DECISIONS Q7): J301.6 -> HP_DET_B; R323 0R default DNP (fit only if 5-6 is an independent NC switch).  E-10: R324 1k series PA1 -> HP_EN_VALIDATED',
         46.99, g(136))
add_part('E-01', 'A12', 'R323', 'SmartVio:R322', 77.47, g(146), '0R', 'SmartVioV25:R_0603_1608Metric',
         'RC0603JR-070RL', {'1': 'HP_DET_B', '2': 'GND'}, dnp=True,
         note='DNP by default; fit only if first-article continuity shows J301 5-6 is an independent NC switch')

# E-02 off-state leakage (A28, A21, A32, A33)
for ref, val, mpn in [('R1705', '2.2M 1%', 'RC0603FR-072M2L'), ('R1706', '1.5M 1%', 'RC0603FR-071M5L'),
                      ('R1709', '2.2M 1%', 'RC0603FR-072M2L'), ('R1710', '1.5M 1%', 'RC0603FR-071M5L'),
                      ('R1707', '10M 1%', 'RC0603FR-0710ML'), ('R1711', '10M 1%', 'RC0603FR-0710ML')]:
    change_value('E-02', 'A28', ref, val, mpn)
change_value('E-02', 'A21', 'R1103', '2.2M 1%', 'RC0603FR-072M2L')
change_value('E-02', 'A32', 'R1304', '4.7M 1%', 'RC0603FR-074M7L')
relabel('E-02', 'A33', 'U1921', '5', 'SYS', 'USB_5V_SAFE', (95.25, 46.99))
relabel('E-02', 'A33', 'C1921', '1', 'SYS', 'USB_5V_SAFE', (182.88, 72.39))
add_text(sheet('A33'), 'R4 ECO E-02: U1921 (TPS3700) VDD and C1921 moved SYS -> USB_5V_SAFE (window only needed while USB present; U1922 reference already on USB_5V_SAFE).',
         34.29, g(110))
add_text(sheet('A28'), 'R4 ECO E-02/E-13: PACK/SYS dividers 2.2M/1.5M 1%, buffer loads 10M 1% (ratio 0.3722, FW factor 2.687, settle >=100 ms); C1707 100pF C0G.',
         46.99, g(200))

# E-03 PhotoMOS split into 3 groups (A22, A17)
for i in range(1, 8):
    change_value('E-03', 'A22', 'R120%d' % i, '390R', 'RC0603FR-07390RL')
relabel('E-03', 'A22', 'K1201', '2', 'SSR_SINK', 'SSR_SINK_HP', (187.96, 46.99))
relabel('E-03', 'A22', 'K1202', '2', 'SSR_SINK', 'SSR_SINK_HP', (327.66, 76.2))
relabel('E-03', 'A22', 'K1206', '2', 'SSR_SINK', 'SSR_SINK_RET', (46.99, 171.45))
relabel('E-03', 'A22', 'K1207', '2', 'SSR_SINK', 'SSR_SINK_RET', (187.96, 181.61))
add_text(sheet('A22'), 'R4 ECO E-03: PhotoMOS LED drive split in 3 groups. HP (K1201/K1202) <- Q1202 / PD14 HP_PORT_ENABLE; RETURN (K1206/K1207) <- Q1203 / PD15 RET_PORT_ENABLE; LINE+FX SEND (K1203-K1205) stay on Q1201 / PA3. R1201-R1207 270R -> 390R (5.3 mA).',
         46.99, g(176))
add_part('E-03', 'A22', 'Q1202', 'SmartVio:Q1201', 77.47, g(190), 'PMV30UN2R', 'SmartVioV25:SOT-23', 'PMV30UN2R',
         {'1': 'SSR_GATE_HP', '2': 'GND', '3': 'SSR_SINK_HP'})
add_part('E-03', 'A22', 'R1212', 'SmartVio:R1210', 218.44, g(188), '1k', 'SmartVioV25:R_0603_1608Metric',
         'RC0603FR-071KL', {'1': 'HP_PORT_ENABLE', '2': 'SSR_GATE_HP'})
add_part('E-03', 'A22', 'R1213', 'SmartVio:R1211', 358.14, g(188), '100k', 'SmartVioV25:R_0603_1608Metric',
         'RC0603FR-07100KL', {'1': 'SSR_GATE_HP', '2': 'GND'})
add_part('E-03', 'A22', 'Q1203', 'SmartVio:Q1201', 77.47, g(212), 'PMV30UN2R', 'SmartVioV25:SOT-23', 'PMV30UN2R',
         {'1': 'SSR_GATE_RET', '2': 'GND', '3': 'SSR_SINK_RET'})
add_part('E-03', 'A22', 'R1214', 'SmartVio:R1210', 218.44, g(210), '1k', 'SmartVioV25:R_0603_1608Metric',
         'RC0603FR-071KL', {'1': 'RET_PORT_ENABLE', '2': 'SSR_GATE_RET'})
add_part('E-03', 'A22', 'R1215', 'SmartVio:R1211', 358.14, g(210), '100k', 'SmartVioV25:R_0603_1608Metric',
         'RC0603FR-07100KL', {'1': 'SSR_GATE_RET', '2': 'GND'})
connect_nc_pin('E-03', 'A17', 'U801', '61', 'HP_PORT_ENABLE', (102.87, 69.85))
connect_nc_pin('E-03', 'A17', 'U801', '62', 'RET_PORT_ENABLE', (102.87, 72.39))

# E-04 BQ24074 default USB500 (A14)
relabel('E-04', 'A14', 'R590', '2', 'GND', 'V3D', (510.54, 100.33))
add_text(sheet('A14'), 'R4 ECO E-04: R590 now pulls CHG_EN1 UP to V3D (reset state EN2/EN1=0/1 = USB500). E-12: R2351 499R -> 3.32k (ITERM ~50 mA).',
         46.99, g(118))

# E-05 eFuse ILIM 1.34 A + ITIMER cap (A20)
change_value('E-05', 'A20', 'R1005', '2.49k 1%', 'RC0603FR-072K49L')
connect_nc_pin('E-05', 'A20', 'U1001', '10', 'EFUSE_ITIMER', (90.17, 54.61))
add_text(sheet('A20'), 'R4 ECO E-05: R1005 6.65k -> 2.49k (ILIM ~1.34 A); U1001.10 ITIMER -> C1004 10nF C0G.  E-06: R1003 37.4k -> 39.2k (OVLO ~5.90 V).',
         34.29, g(113))
add_part('E-05', 'A20', 'C1004', 'SmartVio:C1001', 64.77, g(124), '0.01uF C0G 25V 5%',
         'Passive_V26_ManufacturerLand:C0603C103J3GACTU', 'C0603C103J3GACTU', {'1': 'EFUSE_ITIMER', '2': 'GND'})

# E-06 OVLO (A20)
change_value('E-06', 'A20', 'R1003', '39.2k 1%', 'RC0603FR-0739K2L')

# E-07 VBUS TVS (A13)
add_text(sheet('A13'), 'R4 ECO E-07: D401 SMF12A TVS on VBUS_RAW (USB board, between J401 VBUS pins and C401). Footprint: KiCad stock Diode_SMD:D_SOD-123F (pad1=K, pad2=A).',
         34.29, g(96))
add_part('E-07', 'A13', 'D401', 'SmartVio:D1201', 64.77, g(107), 'SMF12A', 'Diode_SMD:D_SOD-123F', 'SMF12A',
         {'1': 'VBUS_RAW', '2': 'GND'}, pin_renames={'1': 'K', '2': 'A'},
         note='Littelfuse SMF12A (12 V Vrwm unidirectional TVS); symbol pin 1 = K, pin 2 = A')

# E-08 ESP32 supply V3LOAD -> V3D (A19)
relabel('E-08', 'A19', 'U901', '3', 'V3LOAD', 'V3D', (46.99, 49.53))
relabel('E-08', 'A19', 'C902', '1', 'V3LOAD', 'V3D', (205.74, 72.39))
relabel('E-08', 'A19', 'C903', '1', 'V3LOAD', 'V3D', (345.44, 72.39))
relabel('E-08', 'A19', 'R902', '2', 'V3LOAD', 'V3D', (510.54, 43.18))
relabel('E-08', 'A19', 'J902', '1', 'V3LOAD', 'V3D', (187.96, 158.75))
add_text(sheet('A19'), 'R4 ECO E-08: ESP32 U901 3V3, C902, C903, R902, J902.1 moved V3LOAD -> V3D.  E-14: U902 exposed pad pin number EP -> 17 (matches ADI_T1633_4 pad 17).',
         46.99, g(150))

# E-09 V3D +22uF (A21)
add_text(sheet('A21'), 'R4 ECO E-09: C1109 22uF 0805 added on V3D next to C1104/C1105.  E-02: R1103 33k -> 2.2M.', 46.99, g(136))
add_part('E-09', 'A21', 'C1109', 'SmartVio:C1104', 358.14, g(146), '22uF 10V', 'Passive_V26_ManufacturerLand:CC0805MKX5R6BB226',
         'CC0805MKX5R6BB226', {'1': 'V3D', '2': 'GND'})

# E-10 series 1k on DAC_UNMUTE / HP_EN (A17, A16, A12)
relabel('E-10', 'A17', 'U801', '22', 'DAC_UNMUTE', 'DAC_UNMUTE_MCU', (46.99, 97.79))
relabel('E-10', 'A17', 'U801', '23', 'HP_EN_VALIDATED', 'HP_EN_MCU', (46.99, 100.33))
add_text(sheet('A16'), 'R4 ECO E-10: R704 1k in series between MCU PA0 (DAC_UNMUTE_MCU) and U701 XSMT (DAC_UNMUTE).', 46.99, g(114))
add_part('E-10', 'A16', 'R704', 'SmartVio:R703', 77.47, g(124), '1k', 'SmartVioV25:R_0603_1608Metric', 'RC0603FR-071KL',
         {'1': 'DAC_UNMUTE_MCU', '2': 'DAC_UNMUTE'})
add_part('E-10', 'A12', 'R324', 'SmartVio:R322', 218.44, g(146), '1k', 'SmartVioV25:R_0603_1608Metric', 'RC0603FR-071KL',
         {'1': 'HP_EN_MCU', '2': 'HP_EN_VALIDATED'})

# E-11 PWR key sense to MCU PB12 (A24, A17)
add_text(sheet('A24'), 'R4 ECO E-11: D1303 BAS116 (A=PWR_PB_SENSE -> MCU PB12 with internal pull-up, K=PWR_PB). Reverse-biased when key released (PWR_PB = SYS).',
         34.29, g(76))
add_part('E-11', 'A24', 'D1303', 'SmartVio:D1301', 64.77, g(87), 'BAS116,215', 'SmartVioV25:SOT-23', 'BAS116,215',
         {'1': 'PWR_PB_SENSE', '2': None, '3': 'PWR_PB'})
connect_nc_pin('E-11', 'A17', 'U801', '51', 'PWR_PB_SENSE', (102.87, 44.45))
add_text(sheet('A17'), 'R4 ECO: PA0 -> DAC_UNMUTE_MCU, PA1 -> HP_EN_MCU (E-10, via R704/R324 1k); PB12 = PWR_PB_SENSE (E-11); PD14 = HP_PORT_ENABLE, PD15 = RET_PORT_ENABLE (E-03).',
         46.99, g(165))

# E-12 ITERM (A14)
change_value('E-12', 'A14', 'R2351', '3.32k 0.1% 25ppm/C', 'RT0603BRD073K32L')

# E-13 ISET monitor cap (A28)
change_value('E-13', 'A28', 'C1707', '100pF C0G 50V 5%', 'C0603C101J5GACTU', footprint='SmartVioV25:C_0603_1608Metric')

# E-14 U902 EP -> 17 (A19 + library)
sh19 = sheet('A19')
for ls in (emb_lib(sh19, 'U902'), lib_sym('U902')):
    for p in lib_pin_nodes(ls):
        if str(find(p, 'number')[1]) == 'EP':
            find(p, 'number')[1] = QStr('17')
log('E-14', 'change_symbol_pin', sheet='A19', ref='U902', before='EP', after='17')

# ---------------------------------------------------------------- L-12: TMP117 onto main board, J1801/J1802 removed
remove_part('L-12', 'A29', 'J1801', note='sensor sub-board deleted; TMP117 U1801 on main board B.Cu')
remove_part('L-12', 'A29', 'J1802', note='sensor sub-board deleted')
A29_TITLE = 'A29 主板（电池侧）板温 TMP117 / R4 并入主板'
set_title(sheet('A29'), A29_TITLE)
for t in findall(sheet('A29').tree, 'text'):
    if str(t[1]).startswith('A29 '):
        t[1] = QStr(A29_TITLE)
add_text(sheet('A29'), 'R4 ECO L-12: sensor sub-board, J1801/J1802 and wires S1-S4 removed. U1801/C1801 sit on the main board (B.Cu); TEMP_SCL/TEMP_SDA run R1801/R1802 -> U1801 directly.',
         34.29, g(70))
for shn in findall(root, 'sheet'):
    if prop(shn, 'Sheetfile')[2] == 'A29.kicad_sch':
        set_prop(shn, 'Sheetname', A29_TITLE)
log('L-12', 'rename_sheet', sheet='A29', after=A29_TITLE)

# ---------------------------------------------------------------- L-10 / L-13 / L-19: interconnect sheet A34
USB16 = ['USB_DATA_FAULT_N', 'USB_DATA_DISABLE', 'CC_FAULT_N', 'V3D', 'GND', 'USB_DM_MCU', 'USB_DP_MCU', 'GND',
         'USB_5V_SAFE', 'GND', 'GND', 'GND', 'VBUS_RAW', 'VBUS_RAW', 'VBUS_RAW', 'VBUS_RAW']
GROUPS = [
    # name, eco, nets (conductor order), M ref, M fp, FPC ref, FPC fp, R ref, R fp, R value/mpn
    ('AUDIO6', 'L-19', ['GND', 'HP_DETECT_RAW', 'HP_L_PORT', 'HP_R_PORT', 'LINE_L_PORT', 'LINE_R_PORT'],
     ('J3401', 'H_AUDIO_1_M'), 'SmartVioV25:WirePads_6_P1.5', ('FPC3401', 'FPC_AUDIO6'), 'SmartVioV26:FPC_AUDIO6',
     ('J3402', 'H_AUDIO_1_R'), 'SmartVioV25:WirePads_6_P1.5', 'main <-> audio board, FPC AUDIO6 (unchanged from R3)'),
    ('AUDIO4', 'L-13', ['RETURN_L_PORT', 'RETURN_R_PORT', 'SEND_T_PORT', 'GND'],
     ('J3403', 'H_AUDIO_2_M'), 'SmartVioV25:WirePads_4_P1.5', ('FPC3402', 'FPC_AUDIO4'), 'SmartVioV26:FPC_AUDIO4',
     ('J3404', 'H_AUDIO_2_R'), 'SmartVioV25:WirePads_4_P1.5', 'main <-> audio board, NEW FPC AUDIO4 replaces wires W07-W09 + new GND (pin 4)'),
    ('KEYS6', 'L-19', ['FX_RAW', 'GND', 'KEY_BT', 'KEY_FX', 'KEY_MIX', 'KEY_MODE'],
     ('J3405', 'H_COVER_1_M'), 'SmartVioV26:WirePads_Control6_2x3_R3', ('FPC3403', 'FPC_KEYS6'), 'SmartVioV26:FPC_KEYS6_R4',
     ('J3406', 'H_COVER_1_R'), 'SmartVioV25:WirePads_6_P1.5', 'main <-> cover board, FPC KEYS6-R4 (L-09 geometry only)'),
    ('COVER6', 'L-19', ['LED_ZONE_1_A', 'LED_ZONE_2_A', 'LED_ZONE_3_A', 'PWR_PB', 'SPK_N', 'SPK_P'],
     ('J3407', 'H_COVER_2_M'), 'SmartVioV25:WirePads_6_P1.5', ('FPC3404', 'FPC_COVER6'), 'SmartVioV26:FPC_COVER6',
     ('J3408', 'H_COVER_2_R'), 'SmartVioV25:WirePads_6_P1.5', 'main <-> cover board, FPC COVER6'),
    ('POTS3', 'L-19', ['TONE_RAW', 'V3D', 'VOL_RAW'],
     ('J3409', 'H_COVER_3_M'), 'SmartVioV25:WirePads_3_P1.5', ('FPC3405', 'FPC_POTS3'), 'SmartVioV26:FPC_POTS3',
     ('J3410', 'H_COVER_3_R'), 'SmartVioV25:WirePads_3_P1.5', 'main <-> cover board, FPC POTS3'),
    ('USB16', 'L-10', USB16,
     ('J3411', 'J_USB_M'), 'SmartVioV26:FPC_USB16_HotBar_Main_P0.70', ('FPC3406', 'FPC_USB16'), 'SmartVioV26:FPC_USB16',
     ('J3412', 'J_USB_U'), 'Connector_FFC-FPC:Hirose_FH12-16S-0.5SH_1x16-1MP_P0.50mm_Horizontal',
     'main <-> USB board, NEW 16-conductor FPC replaces wires W25-W33 (H_USB_1/H_USB_2 deleted)'),
]

def make_conn_libsym(name, refprefix, value, left, right, in_bom, hw=10.16):
    """left/right: [(number, pin_name)]; symbol body +-10.16, pins length 5.08 at +-15.24."""
    n = max(len(left), len(right))
    ys = [(n - 1) * 1.27 - i * 2.54 for i in range(n)]
    top = ys[0] + 2.54; bot = ys[-1] - 2.54
    pins = []
    for side, plist in (('L', left), ('R', right)):
        for i, (pn, pname) in enumerate(plist):
            x = -(hw + 5.08) if side == 'L' else (hw + 5.08)
            ang = '0' if side == 'L' else '180'
            pins.append([Sym('pin'), Sym('passive'), Sym('line'), [Sym('at'), num(x), num(ys[i]), Sym(ang)],
                         [Sym('length'), Sym('5.08')],
                         [Sym('name'), QStr(pname), [Sym('effects'), [Sym('font'), [Sym('size'), Sym('1.0'), Sym('1.0')]]]],
                         [Sym('number'), QStr(pn), [Sym('effects'), [Sym('font'), [Sym('size'), Sym('1.0'), Sym('1.0')]]]]])
    return [Sym('symbol'), QStr('SmartVio:' + name), [Sym('pin_names'), [Sym('offset'), Sym('0.508')]],
            [Sym('in_bom'), Sym('yes' if in_bom else 'no')], [Sym('on_board'), Sym('yes')],
            [Sym('property'), QStr('Reference'), QStr(refprefix), [Sym('at'), Sym('0'), num(-(abs(bot) + 5.08)), Sym('0')],
             [Sym('effects'), [Sym('font'), [Sym('size'), Sym('1.0'), Sym('1.0')]]]],
            [Sym('property'), QStr('Value'), QStr(value), [Sym('at'), Sym('0'), num(-(abs(bot) + 2.54)), Sym('0')],
             [Sym('effects'), [Sym('font'), [Sym('size'), Sym('1.0'), Sym('1.0')]]]],
            [Sym('symbol'), QStr(name + '_0_1'),
             [Sym('rectangle'), [Sym('start'), num(-hw), num(top)], [Sym('end'), num(hw), num(bot)],
              [Sym('stroke'), [Sym('width'), Sym('0.254')], [Sym('type'), Sym('default')]],
              [Sym('fill'), [Sym('type'), Sym('background')]]]],
            [Sym('symbol'), QStr(name + '_1_1')] + pins], top, bot

A34_FILE_UUID = str(uuid.uuid5(uuid.NAMESPACE_URL, 'smartvio/r4/A34.kicad_sch'))
A34_SHEET_UUID = str(uuid.uuid5(uuid.NAMESPACE_URL, 'smartvio/r4/root/A34'))
SHEET_UUID['A34.kicad_sch'] = A34_SHEET_UUID
A34_TITLE = 'A34 板间互连端点 / FPC（R4 schematic parity）'
a34 = [Sym('kicad_sch'), [Sym('version'), Sym('20260101')], [Sym('generator'), QStr('smartvio_r4_eco')],
       [Sym('uuid'), Sym(A34_FILE_UUID)], [Sym('paper'), QStr('A2')],
       [Sym('title_block'), [Sym('title'), QStr(A34_TITLE)], [Sym('date'), QStr(DATE)], [Sym('rev'), QStr(REV)],
        [Sym('company'), QStr('SmartVio')], [Sym('comment'), Sym('1'), QStr('ENGINEERING CAPTURE - NOT RELEASED FOR MANUFACTURE')]],
       [Sym('lib_symbols')]]
write_like(os.path.join(DST, 'A34.kicad_sch'), sexp.dumps(a34), os.path.join(SRC, 'A33.kicad_sch'))
sh34 = sheet('A34')
add_text(sh34, A34_TITLE, 15, 15, size=3)
add_text(sh34, 'R4 ECO L-19: every inter-board endpoint is a symbol here: J3401-J3412 = R3/ECO landings H_AUDIO_*/H_COVER_*/J_USB_M/J_USB_U (old name kept in field Endpoint_ID; KiCad needs numeric refdes), FPC3401-FPC3406 = FPC bodies (S pads = main-board end, T pads = remote end) so PCB parity can be checked. Wires W07-W09, W25-W33 and S1-S4 no longer exist (0 discrete wires).',
         15, 21, size=1.3)
REFMAP = {}
y = g(40)
for (gname, eco, nets, mref, mfp, fref, ffp, rref, rfp, desc) in GROUPS:
    n = len(nets)
    pinsM = [(str(i + 1), nets[i]) for i in range(n)]
    pinsS = [('S%d' % (i + 1), nets[i]) for i in range(n)]
    pinsT = [('T%d' % (i + 1), nets[i]) for i in range(n)]
    if gname == 'USB16':
        mval, mmpn, minbom = 'USB16 main-end hot-bar landing (J_USB_M)', '', False
        rval, rmpn, rinbom = 'FH12-16S-0.5SH(55)', 'FH12-16S-0.5SH(55)', True
    else:
        mval, mmpn, minbom = '%s main-end FPC landing (%s)' % (gname, mref[1]), '', False
        rval, rmpn, rinbom = '%s remote-end FPC landing (%s)' % (gname, rref[1]), '', False
    fval = 'FPC-%s custom flex (%s, DFM pending)' % (gname, fref[1])
    add_text(sh34, '%s  (%s): %s' % (gname, eco, desc), 30.48, y - 7.62, size=1.3)
    cols = [(mref, mfp, mval, mmpn, minbom, pinsM, [], 'J', 76.2),
            (fref, ffp, fval, '', False, pinsS, pinsT, 'FPC', 205.74),
            (rref, rfp, rval, rmpn, rinbom, pinsM, [], 'J', 335.28)]
    height = 0
    for ((ref, epid), fp, val, mpn, inbom, left, right, pfx, x) in cols:
        REFMAP[ref] = dict(endpoint_id=epid, group=gname, footprint=fp, eco=eco)
        emb, top, bot = make_conn_libsym(ref, pfx, val, [(a, b) for a, b in left], [(a, b) for a, b in right], inbom, hw=(20.32 if right else 10.16))
        register_libsym(sh34, emb)
        cy = y + top  # place so that the body top sits at row y
        sym = place_symbol(sh34, 'A34', ref, 'SmartVio:' + ref, x, cy, val, fp, mpn, -(top + 3.81), -(top + 1.27),
                           in_bom=inbom, extra=[('R4_ECO', eco), ('Endpoint_ID', epid)])
        pmap = dict(left + right)
        for gg in pin_geom(sh34, sym):
            add_wire_label(sh34, gg[3], gg[4], pmap[gg[0]])
        height = max(height, top - bot)
        log(eco if gname in ('USB16', 'AUDIO4') else 'L-19', 'add_endpoint', sheet='A34', ref=ref, endpoint_id=epid, value=val,
            footprint=fp, in_bom=inbom, pins={a: b for a, b in left + right})
    y = y + height + g(14)
    y = round(y / 1.27) * 1.27

# root sheet entry for A34
sheets_root = findall(root, 'sheet')
last = sheets_root[-1]
newsheet = [Sym('sheet'), [Sym('at'), Sym('440'), Sym('315')], [Sym('size'), Sym('120'), Sym('32')],
            [Sym('stroke'), [Sym('width'), Sym('0.254')], [Sym('type'), Sym('default')]],
            [Sym('fill'), [Sym('color'), Sym('0'), Sym('0'), Sym('0'), Sym('0')]], [Sym('uuid'), Sym(A34_SHEET_UUID)],
            [Sym('property'), QStr('Sheetname'), QStr(A34_TITLE), [Sym('at'), Sym('440'), Sym('313'), Sym('0')],
             [Sym('effects'), [Sym('font'), [Sym('size'), Sym('1.1'), Sym('1.1')]], [Sym('justify'), Sym('left'), Sym('bottom')]]],
            [Sym('property'), QStr('Sheetfile'), QStr('A34.kicad_sch'), [Sym('at'), Sym('440'), Sym('349'), Sym('0')],
             [Sym('effects'), [Sym('font'), [Sym('size'), Sym('1.1'), Sym('1.1')]], [Sym('justify'), Sym('left'), Sym('top')]]],
            [Sym('instances'), [Sym('project'), QStr('SmartVio'), [Sym('path'), QStr('/' + ROOT_UUID), [Sym('page'), QStr('25')]]]]]
root.insert(root.index(last) + 1, newsheet)
root.insert(root.index(newsheet) + 1,
            [Sym('text'), QStr('R4 ECO 2026-10-15 applied: E-01..E-14 (eco-schematic.json), L-10/L-12/L-13/L-19 (eco-pcb.json). See SCHEMATIC-CHANGES.md / eco-verification.json.'),
             [Sym('at'), Sym('20'), Sym('32'), Sym('0')], [Sym('effects'), [Sym('font'), [Sym('size'), Sym('1.3'), Sym('1.3')]], [Sym('justify'), Sym('left')]],
             [Sym('uuid'), U()]])
log('L-19', 'add_sheet', sheet='A34', uuid=A34_SHEET_UUID, page='25')

# ---------------------------------------------------------------- title blocks of changed sheets
for sname in ['A12', 'A13', 'A14', 'A16', 'A17', 'A19', 'A20', 'A21', 'A22', 'A24', 'A28', 'A32', 'A33']:
    set_title(sheet(sname))

# ---------------------------------------------------------------- write
for name, sh in SHEETS.items():
    sh.save()  # lossless re-serialisation; untouched sheets come out byte-identical
write_like(ROOT_PATH, sexp.dumps(root), os.path.join(SRC, 'SmartVio.kicad_sch'))
find(lib, 'generator')[1] = QStr('smartvio_r4_eco')
write_like(LIB_PATH, sexp.dumps(lib), os.path.join(SRC, 'SmartVio.kicad_sym'))
# project-local stock footprint libs used by D401 / J_USB_U
fpt = sexp.parse(open(os.path.join(DST, 'fp-lib-table')).read())
for nm, d in (('Diode_SMD', 'KiCad stock (D401 SMF12A, E-07)'), ('Connector_FFC-FPC', 'KiCad stock (J_USB_U FH12-16S, L-10)')):
    fpt.append([Sym('lib'), [Sym('name'), QStr(nm)], [Sym('type'), QStr('KiCad')],
                [Sym('uri'), QStr('${KICAD10_FOOTPRINT_DIR}/%s.pretty' % nm)], [Sym('options'), QStr('')], [Sym('descr'), QStr(d)]])
write_like(os.path.join(DST, 'fp-lib-table'), sexp.dumps(fpt), os.path.join(SRC, 'fp-lib-table'))
json.dump(REFMAP, open(os.path.join(WORK, 'r4', 'sch-endpoint-refmap.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(LOG, open(os.path.join(WORK, 'r4', 'sch-eco-log.json'), 'w'), ensure_ascii=False, indent=1)
print('edits:', len(LOG))
