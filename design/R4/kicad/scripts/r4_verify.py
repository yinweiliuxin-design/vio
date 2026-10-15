#!/usr/bin/env python3
"""Verify the R4 schematic netlist against the R3 netlist and every ECO expectation.

usage: r4_verify.py ECO_SCH_JSON ECO_PCB_JSON OUT_JSON
Reads work/r3/r3-netlist.xml, work/r4/r4-netlist.xml, R3 PCB files (for endpoint parity).
Every component/field/pin-net difference must be claimed by an ECO check, otherwise it is
listed under diff.unexplained (target: empty).
"""
import sys, os, re, json, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import netxml

WORK = os.path.abspath(os.path.join(HERE, '..'))
eco_s = json.load(open(sys.argv[1]))
eco_p = json.load(open(sys.argv[2]))
OUT = sys.argv[3]
c3, n3, p3 = netxml.load(os.path.join(WORK, 'r3', 'r3-netlist.xml'))
c4, n4, p4 = netxml.load(os.path.join(WORK, 'r4', 'r4-netlist.xml'))
refmap = json.load(open(os.path.join(WORK, 'r4', 'sch-endpoint-refmap.json')))
ep2ref = {v['endpoint_id']: k for k, v in refmap.items()}

def nc(n):
    return n is None or n.startswith('unconnected-')

def norm(n):
    return 'NC' if nc(n) else n

def pins_of(p2n, ref):
    return {k[1]: v for k, v in p2n.items() if k[0] == ref}

def fields(c):
    if c is None: return None
    return dict(value=c['value'], footprint=c['footprint'], mpn=c['fields'].get('MPN', ''),
                spec=c['fields'].get('Specification', ''), dnp=('dnp' in c['props']))

# ---- explained sets
EXPL_PIN = {}    # (ref,pin) -> eco id
EXPL_COMP = {}   # ref -> eco id (added/removed)
EXPL_FIELD = {}  # (ref, field) -> eco id
results = []

def check(eco, desc, ok, detail=None):
    results.append(dict(eco=eco, check=desc, result='pass' if ok else 'FAIL', detail=detail))
    return ok

def pin_key(s):
    """'61 (PD14)' -> '61'; '1 G' -> '1'; 'K' -> 'K'."""
    return str(s).split()[0]

DIODE_KA = {'D401': {'K': '1', 'A': '2'}}

for it in eco_s['items']:
    eid = it['id']
    for op in it.get('operations', []):
        a = op['action']; ref = op['ref']
        if a == 'change_value':
            refs = [ref]
            m = re.match(r'R(\d+)\.\.R(\d+)', ref)
            if m:
                refs = ['R%d' % i for i in range(int(m.group(1)), int(m.group(2)) + 1)]
            for r in refs:
                f3, f4 = fields(c3.get(r)), fields(c4.get(r))
                mpn = op['after'].split()[-1]
                exp_val = op['after'].replace(mpn, '').strip() if re.search(r'\d', mpn) and len(mpn) > 8 else op['after']
                # all value tokens of the ECO 'after' text must appear in the R4 value (R4 may append tolerance/TC as in R3 style)
                ok = f4 is not None and f4['mpn'] == mpn and all(t in f4['value'].split() for t in exp_val.split())
                if op.get('footprint'): ok = ok and f4['footprint'] == op['footprint']
                pins_ok = True
                if op.get('pins'):
                    pins_ok = all(norm(p4.get((r, k))) == v for k, v in op['pins'].items())
                    pins_ok = pins_ok and all(p3.get((r, k)) == p4.get((r, k)) for k in op['pins'])
                check(eid, '%s value %s -> %s' % (r, f3['value'] if f3 else None, op['after']), ok and pins_ok,
                      dict(r3=f3, r4=f4, pins_r4=pins_of(p4, r)))
                for fld in ('value', 'mpn', 'spec', 'footprint'):
                    if f3 and f4 and f3[fld] != f4[fld]: EXPL_FIELD[(r, fld)] = eid
        elif a == 'rewire':
            pin = pin_key(op['pin'])
            before, after = op['before'], op['after']
            b_ok = (nc(p3.get((ref, pin))) if before == 'no_connect' else p3.get((ref, pin)) == before)
            a_ok = p4.get((ref, pin)) == after
            check(eid, '%s.%s %s -> %s' % (ref, pin, before, after), b_ok and a_ok,
                  dict(r3=p3.get((ref, pin)), r4=p4.get((ref, pin))))
            EXPL_PIN[(ref, pin)] = eid
        elif a == 'add':
            f4 = fields(c4.get(ref))
            ok = f4 is not None and ref not in c3 and f4['mpn'] in op['mpn'] and f4['footprint'] == op['footprint'].split('（')[0].strip() if f4 else False
            if ref == 'D401' and f4:
                ok = f4['mpn'] == 'SMF12A' and f4['footprint'] == 'Diode_SMD:D_SOD-123F'
            pres = {}
            pins_ok = True
            for k, v in op['pins'].items():
                pk = DIODE_KA.get(ref, {}).get(pin_key(k), pin_key(k))
                got = p4.get((ref, pk))
                pres[pk] = got
                exp_nc = v == 'no_connect'
                if (exp_nc and not nc(got)) or (not exp_nc and got != v): pins_ok = False
            dnp_ok = (f4 or {}).get('dnp') == bool(op.get('dnp'))
            if f4 and len(pins_of(p4, ref)) != len(op['pins']): pins_ok = False
            check(eid, 'add %s %s pins %s%s' % (ref, op['value'], op['pins'], ' DNP' if op.get('dnp') else ''),
                  ok and pins_ok and dnp_ok, dict(r4=f4, pins_r4=pres))
            EXPL_COMP[ref] = eid
        elif a == 'keep':
            for r in [x.strip() for x in ref.split(',')]:
                if '.' in r:  # 'U1001.3 AUXOFF' -> keep that pin only
                    rr, pn = r.split()[0].split('.')
                    check(eid, 'keep %s.%s unchanged (%s)' % (rr, pn, norm(p4.get((rr, pn)))), norm(p3.get((rr, pn))) == norm(p4.get((rr, pn))))
                    continue
                same = fields(c3.get(r)) == fields(c4.get(r)) and pins_of(p3, r) == pins_of(p4, r)
                check(eid, 'keep %s unchanged' % r, same)
        elif a == 'change_symbol_pin':
            ok = (ref, 'EP') not in p4 and p4.get((ref, '17')) == 'GND' and p3.get((ref, 'EP')) == 'GND'
            check(eid, '%s pin EP -> 17 (GND)' % ref, ok, dict(r3_EP=p3.get((ref, 'EP')), r4_17=p4.get((ref, '17'))))
            EXPL_PIN[(ref, 'EP')] = eid; EXPL_PIN[(ref, '17')] = eid
        else:
            check(eid, 'unknown op %s' % a, False)
    for net in it.get('new_nets', []):
        nodes = n4.get(net, [])
        check(eid, 'new net %s exists with >=2 nodes and is new vs R3' % net, len(nodes) >= 2 and net not in n3,
              dict(nodes=nodes))

# ---- PCB/FPC ECO, schematic side
def r3_pcb_endpoints():
    out = {}
    for f in glob.glob(os.path.join(WORK, 'r3', 'pcb', '*.kicad_pcb')):
        s = open(f).read()
        for m in re.finditer(r'\(footprint "', s):
            blk = s[m.start():m.start() + 20000]
            depth = 0; j = 0
            for j, ch in enumerate(blk):
                if ch == '(': depth += 1
                elif ch == ')':
                    depth -= 1
                    if depth == 0: break
            blk = blk[:j + 1]
            ref = re.search(r'\(property "Reference" "([^"]+)"', blk).group(1)
            if ref.startswith(('H_', 'FPC_')) or ref in ('J1801', 'J1802'):
                pads = dict(re.findall(r'\(pad "([^"]*)"[^()]*(?:\([^()]*\)[^()]*)*?\(net (?:\d+ )?"([^"]*)"', blk))
                out[ref] = dict(board=os.path.basename(f), pads=pads)
    return out

r3eps = r3_pcb_endpoints()
items = {it['id']: it for it in eco_p['items']}

# L-10 USB16
pin_tab = items['L-10']['change']['pinout']
for role, old in (('main end', 'J_USB_M'), ('USB-board end', 'J_USB_U')):
    ref = ep2ref[old]
    got = pins_of(p4, ref)
    ok = all(got.get(str(p['pin'])) == p['net'] for p in pin_tab) and len(got) == 16
    check('L-10', '%s %s (%s) 16 pins per eco-pcb L-10 pin table' % (role, ref, old), ok, got)
    EXPL_COMP[ref] = 'L-10'
fref = ep2ref['FPC_USB16']
got = pins_of(p4, fref)
ok = all(got.get('S%d' % p['pin']) == p['net'] and got.get('T%d' % p['pin']) == p['net'] for p in pin_tab) and len(got) == 32
check('L-10', 'FPC body %s (FPC_USB16) S1-16/T1-16 per pin table' % fref, ok)
EXPL_COMP[fref] = 'L-10'
cnt = {}
for p in pin_tab: cnt[p['net']] = cnt.get(p['net'], 0) + 1
check('L-10', 'USB16 conductor budget: 4x VBUS_RAW, 5x GND, 16 total',
      cnt.get('VBUS_RAW') == 4 and cnt.get('GND') == 5 and len(pin_tab) == 16, cnt)
# every R3 harness wire W25-W33 now carried by USB16
for w in eco_p['wire_replacement']:
    if w['wire'].startswith('W') and int(w['wire'][1:]) >= 25:
        ok = any(p['net'] == w['net'] for p in pin_tab) and w['net'] in pins_of(p4, ep2ref['J_USB_M']).values()
        check('L-10', '%s (%s) carried by USB16' % (w['wire'], w['net']), ok)
for old in ('H_USB_1_M', 'H_USB_1_R', 'H_USB_2_M', 'H_USB_2_R'):
    check('L-10', '%s not in R4 schematic (replaced by USB16)' % old, old not in c4)

# L-12 TMP117 merged
for r in ('J1801', 'J1802'):
    check('L-12', '%s removed' % r, r in c3 and r not in c4)
    EXPL_COMP[r] = 'L-12'
    for k in pins_of(p3, r): EXPL_PIN[(r, k)] = 'L-12'
for r in ('U1801', 'C1801', 'R1801', 'R1802'):
    check('L-12', '%s unchanged (pins and fields)' % r, fields(c3[r]) == fields(c4[r]) and pins_of(p3, r) == pins_of(p4, r))
check('L-12', 'TEMP_SCL = R1801.2 + U1801.1 only', sorted(n4['TEMP_SCL']) == sorted([('R1801', '2', 'passive'), ('U1801', '1', 'input')]), n4['TEMP_SCL'])
check('L-12', 'TEMP_SDA = R1802.2 + U1801.6 only', sorted(x[:2] for x in n4['TEMP_SDA']) == [('R1802', '2'), ('U1801', '6')], n4['TEMP_SDA'])
check('L-12', 'A29 sheet renamed to main-board board temperature', '主板' in c4['U1801']['props'].get('Sheetname', ''), c4['U1801']['props'].get('Sheetname'))

# L-13 AUDIO4
a4 = items['L-13']['change']['pinout']
for old in ('H_AUDIO_2_M', 'H_AUDIO_2_R'):
    ref = ep2ref[old]; got = pins_of(p4, ref)
    ok = all(got.get(str(p['pin'])) == p['net'] for p in a4) and len(got) == 4
    check('L-13', '%s (%s) 4 pins incl. new GND pin 4' % (ref, old), ok, got)
    EXPL_COMP[ref] = 'L-13'
fref = ep2ref['FPC_AUDIO4']; got = pins_of(p4, fref)
check('L-13', 'FPC body %s (FPC_AUDIO4) S1-4/T1-4' % fref,
      all(got.get('S%d' % p['pin']) == p['net'] == got.get('T%d' % p['pin']) for p in a4) and len(got) == 8, got)
EXPL_COMP[fref] = 'L-13'

# L-19 parity: every R3 PCB-only endpoint (other than retired H_USB_*/J180x) has a symbol whose pins
# equal the R3 pad nets (AUDIO4 endpoints: R3 pads 1-3 + new pad 4)
for old, d in sorted(r3eps.items()):
    if old.startswith('H_USB') or old in ('J1801', 'J1802'):
        continue
    ref = ep2ref.get(old)
    if ref is None:
        check('L-19', '%s (%s) has an R4 symbol' % (old, d['board']), False); continue
    got = pins_of(p4, ref)
    exp = dict(d['pads'])
    if old.startswith('H_AUDIO_2'): exp['4'] = 'GND'
    ok = got == exp
    check('L-19', '%s on %s -> %s pins == R3 PCB pad nets%s' % (old, d['board'], ref, ' (+pin4 GND, L-13)' if old.startswith('H_AUDIO_2') else ''), ok,
          dict(r3_pads=d['pads'], r4=got))
    EXPL_COMP[ref] = EXPL_COMP.get(ref, 'L-19')
for k, v in refmap.items():
    EXPL_COMP.setdefault(k, 'L-19')
    check('L-19', '%s (%s) present in R4 netlist with footprint %s' % (k, v['endpoint_id'], v['footprint']),
          k in c4 and c4[k]['footprint'] == v['footprint'])
check('L-19', 'all R4 references KiCad-annotated (end in a digit, unique)',
      all(re.search(r'\d$', r) for r in c4) and len(c4) == len(set(c4)))

# ---- full diff, everything must be explained
unexplained = []
added = sorted(set(c4) - set(c3)); removed = sorted(set(c3) - set(c4))
for r in added + removed:
    if r not in EXPL_COMP: unexplained.append(dict(kind='component', ref=r, change='added' if r in added else 'removed'))
for r in sorted(set(c3) & set(c4)):
    f3, f4 = fields(c3[r]), fields(c4[r])
    for fld in f3:
        if f3[fld] != f4[fld] and (r, fld) not in EXPL_FIELD:
            unexplained.append(dict(kind='field', ref=r, field=fld, r3=f3[fld], r4=f4[fld]))
pin_changes = []
for key in sorted(set(p3) | set(p4)):
    a, b = p3.get(key), p4.get(key)
    if norm(a) == norm(b): continue
    if key[0] in added or key[0] in removed: continue
    pin_changes.append(dict(pin='%s.%s' % key, r3=a, r4=b, eco=EXPL_PIN.get(key)))
    if key not in EXPL_PIN: unexplained.append(dict(kind='pin', pin='%s.%s' % key, r3=a, r4=b))
nets_added = sorted(n for n in set(n4) - set(n3) if not nc(n))
nets_removed = sorted(n for n in set(n3) - set(n4) if not nc(n))
declared_new = set(n for it in eco_s['items'] for n in it.get('new_nets', []))
for n in nets_added:
    if n not in declared_new: unexplained.append(dict(kind='net_added', net=n))
for n in nets_removed:
    unexplained.append(dict(kind='net_removed', net=n))
check('DIFF', 'no unexplained R3->R4 difference', not unexplained, unexplained)

npass = sum(1 for r in results if r['result'] == 'pass')
out = dict(
    schema='smartvio.r4.eco-verification.v1', date='2026-10-15',
    inputs=dict(r3_netlist='work/r3/r3-netlist.xml', r4_netlist='work/r4/r4-netlist.xml',
                eco_schematic='design/R4/eco/eco-schematic.json', eco_pcb='design/R4/eco/eco-pcb.json'),
    summary=dict(checks=len(results), passed=npass, failed=len(results) - npass,
                 r3_components=len(c3), r4_components=len(c4), r3_nets=len(n3), r4_nets=len(n4)),
    diff=dict(components_added=added, components_removed=removed, nets_added=nets_added, nets_removed=nets_removed,
              nc_nets_added=sorted(n for n in set(n4) - set(n3) if nc(n)),
              nc_nets_removed=sorted(n for n in set(n3) - set(n4) if nc(n)),
              field_changes=sorted(['%s.%s' % k for k in EXPL_FIELD]), pin_net_changes=pin_changes,
              unexplained=unexplained),
    endpoint_refmap=refmap,
    checks=results)
json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=1)
print('checks %d pass %d fail %d unexplained %d' % (len(results), npass, len(results) - npass, len(unexplained)))
for r in results:
    if r['result'] != 'pass': print('FAIL', r['eco'], r['check'], json.dumps(r['detail'], ensure_ascii=False)[:600])
