"""Generate SmartVio R3 review report v2 (native package round) from workflow results."""
import json, sys, html, re

S = sys.argv[1]
out = json.load(open(S + '/wf_all.json'))
v1 = open(S + '/report_v1.html', encoding='utf-8').read()
E = html.escape

# ---------- corrections to agent text that relied on the retracted A1 ----------
def patch(f):
    if f['key'] == 'FW-NO-CHARGE-PATH':
        f['title'] = '固件永不允许充电，EN1/EN2 恒为 USB100（100 mA）：插着 USB 时重负载仍会从电池补电'
        f['impact'] = f['impact'].replace('将来即便固件放行，A1 的 U1921 也会把 CHARGE_GATE 钳低。', '')
        f['fix'] = f['fix'].replace('按 A1 修正 U1921 窗口；', '（U1921 窗口接法本身正确，无需改动）；')
        f['evidence'] = f['evidence'].replace('（A1）', '')
    if f['key'] == 'M16':
        f['impact'] = f['impact'].replace('需与A1、C13一起评估', '需与 C13 一起评估')
    if f['key'] == 'SCH-HPDET-J301':
        f['title'] = '耳机插座 J301：Kycon 原厂图上触点⑤压在插头尖端（左声道）上，现接法把⑤当作独立检测脚'
        f['impact'] = ('原厂“Schematic (Plug In)”图中触点⑤直接接触插头尖端。若插入时⑤与⑥闭合，⑥接 GND，左声道 HP_L 被短接到地；'
                       '若不闭合，HP_DETECT_RAW 实际读的是尖端直流电平，100 kΩ 上拉还会向耳机左声道注入约 33 µA。'
                       '两种情况都不是原理图标注的“独立常开检测开关”。资料包自己也挂着“isolated switch sample qualification”待验。')
        f['fix'] = ('先用一只实物插座和万用表确认：不插/插 TRS 插头时 4–5、5–6 之间是否导通。若⑤与尖端导通，改为 ⑤ 接 HP_L_PORT、'
                    '⑥ 作检测脚（上拉 + 1 kΩ 送 PA4，插入时被耳机直流通路拉低），或换用带独立绝缘检测开关的插座型号。'
                    'J102/J201/J202 的⑤⑥目前悬空，不受影响。')
    return f

AREA = {'schematic': '原理图', 'pcb': 'PCB 版图', 'mechanical': '结构 CAD', 'firmware': '固件',
        'harness-bom': '线束与 BOM', 'docs': '交付文档与脚本', 'web': 'Web V12 软件'}
SEVZH = {'critical': '致命', 'high': '高', 'medium': '中', 'low': '低', 'info': '提示'}
SEVCLS = {'critical': 'sa', 'high': 'sb', 'medium': 'sc', 'low': 'sd', 'info': 'sd'}
ORDER = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}

allf = []; refuted = []
for area in AREA:
    rv = out.get('review:' + area); vf = out.get('verify:' + area) or {}
    vmap = {v['key']: v for v in vf.get('verdicts', [])}
    for f in rv['findings']:
        f = patch(dict(f)); v = vmap.get(f['key'], {})
        f['area'] = area; f['verdict'] = v.get('verdict', 'unverified'); f['sev'] = v.get('severity', f['severity'])
        f['vreason'] = v.get('reason', '')
        if f['key'] == 'SCH-A1-REVERSAL':
            continue
        if f['key'] == 'SCH-HPDET-J301':
            f['sev'] = 'high'
        if f['verdict'] == 'refuted':
            refuted.append(f); continue
        allf.append(f)
allf.sort(key=lambda f: (ORDER[f['sev']], list(AREA).index(f['area'])))
cnt = {s: sum(1 for f in allf if f['sev'] == s) for s in ORDER}
nconf = sum(1 for f in allf if f['verdict'] == 'confirmed'); nunc = sum(1 for f in allf if f['verdict'] == 'uncertain')

def br(t):
    return E(t).replace('\n', '<br>')

def item(f):
    tag = '' if f['verdict'] == 'confirmed' else '<span class="chip c-u">待实测确认</span>'
    return f'''<article class="issue {SEVCLS[f['sev']]}"><div class="id">{SEVZH[f['sev']]}</div><div class="body">
<h4>{E(f['title'])} {tag}</h4>
<div class="meta2"><span class="mono">{E(f['key'])}</span> · {AREA[f['area']]}</div>
<dl><dt>依据</dt><dd class="ev">{br(f['evidence'])}</dd><dt>后果</dt><dd>{br(f['impact'])}</dd><dt>改法</dt><dd>{br(f['fix'])}</dd></dl>
</div></article>'''

# ---------- top priorities ----------
TOP = ['FW-PARSER-WHITELIST', 'FW-PORT-ENABLE-HP', 'M1', 'HB-01', 'SCH-HPDET-J301', 'M10', 'M5', 'FW-NO-UVLO',
       'FW-USB-SHUTDOWN-LATCH', 'PCB-01', 'PCB-05', 'HB-02', 'M7', 'FW-FAULT-LATCH']
byk = {f['key']: f for f in allf}
toprows = ''.join(f'<li><b>{E(byk[k]["title"])}</b> <span class="mono small">{k} · {AREA[byk[k]["area"]]} · {SEVZH[byk[k]["sev"]]}</span></li>' for k in TOP if k in byk)

# ---------- prior status ----------
prior = {}
for k, v in out.items():
    if k.startswith('review:'):
        for p in v.get('priorFindingStatus', []):
            if p['status'] != 'not-checked':
                prior.setdefault(p['id'], []).append((k[7:], p['status'], p['note']))
PRIOR_TITLE = {
 'A1': 'TPS3700 充电温度窗口接反', 'A2': '关机漏电约 0.48 mA', 'B1': '无 USB-C 供电能力识别', 'B2': 'TPD2S300 死电池 Rd',
 'B3': '模拟电源与 ESP32 共节点', 'B4': '7 个 PhotoMOS 常耗与串入耳机', 'B5': '音频 ESD 离插座太远', 'B6': 'USB 子板 9 根散线',
 'B7': 'PLAY 总线并联跨电源域', 'B8': '天线紧贴金属格栅', 'B9': '四弦独立拾音未实现', 'C1': 'TPS63070 PG 未用',
 'C2': '大尺寸 C0G 电容', 'C3': '扬声器无背腔', 'C4': '滚轮几乎齐平', 'C5': '按键帽尺寸矛盾', 'C6': '无字符/灯条变点灯',
 'C7': 'TMP117 位置与标题不符', 'C8': '琴背平面度与螺钉边距', 'C9': '键 3/轮 2 跨腔边', 'C10': '插头朝身体/PWR 误触',
 'C11': '插 USB 无法关机', 'C12': '64 MHz 实时预算', 'C13': '包内 NTC 规格', 'C14': '8 层板成本', 'D1': '版本命名混用',
 'D2': '缺 A31 页', 'D3': '原理图无板间连接器', 'D4': '机械图无方向基准', 'D5': '原理图缺型号', 'D6': '数值格式与放置页',
 'D7': '剖面无视向箭头', 'D8': 'V26/R3 基线混用'}
def pid_key(s):
    return (s[0], int(re.sub(r'\D', '', s) or 0))
prow = ''
for pid in sorted(PRIOR_TITLE, key=pid_key):
    lst = prior.get(pid, [])
    sts = [s for _, s, _ in lst]
    if pid == 'A1':
        st, cls = '撤回（原设计正确）', 'c-a'
        note = ('TPS3700 的 INA+ 是欠压比较器（低于 0.4 V 时 OUTA 拉低），INB− 是过压比较器（高于 0.4 V 时 OUTB 拉低）。'
                '现接法下 CHARGE_GATE 在 0.40 V < CELL_NTC_SENSE < 1.03 V 时释放，对应约 5–40 °C，窗口正确。'
                '我第一版报告把两路极性都写反了；照“对调”去改反而会让它永远无法充电。原设计不需要修改。')
    elif not lst:
        st, cls, note = '未复核', 'c-d', '本轮未涉及。'
    elif 'refined' in sts:
        st, cls = '成立，已修正细节', 'c-b'
        note = next(n for _, s, n in lst if s == 'refined')
    else:
        st, cls = '确认成立', 'c-ok'
        note = lst[0][2]
    areas = '、'.join(sorted({AREA[a] for a, _, _ in lst})) if lst else ''
    prow += f'<tr><td class="mono">{pid}</td><td>{E(PRIOR_TITLE[pid])}</td><td><span class="chip {cls}">{st}</span></td><td class="small">{E(note)}{("<br><span class=muted>复核方向：" + areas + "</span>") if areas else ""}</td></tr>'

# ---------- coverage ----------
cov = ''
for area in AREA:
    ok = out['review:' + area].get('checkedOK', [])
    cov += f'<div class="card"><h4>{AREA[area]} · {len(ok)} 项</h4><ul class="tight small">' + ''.join(f'<li>{E(x)}</li>' for x in ok) + '</ul></div>'

refrows = ''.join(f'<li><span class="mono">{E(f["key"])}</span> {E(f["title"])}：<span class="muted">{E(f["vreason"][:260])}</span></li>' for f in refuted)

# ---------- reuse v1 parts ----------
style = v1[v1.index('<style>'):v1.index('</style>') + 8]
style = style.replace('</style>', '''
.c-u{background:var(--sev-c-soft);color:var(--sev-c);font-size:12px;padding:1px 8px;margin-left:6px;vertical-align:2px}
.meta2{font-size:12.5px;color:var(--muted);margin:-2px 0 8px}
.small{font-size:13px}.muted{color:var(--muted)}
dd.ev{font-size:13px;color:var(--muted);white-space:normal;overflow-wrap:anywhere}
.fix-box{background:var(--sev-a-soft);border:1px solid var(--sev-a);border-radius:10px;padding:16px 18px;display:grid;gap:8px}
.fix-box h3{margin:0;color:var(--sev-a)}
.fix-box p{max-width:none;margin:0}
ol.top{margin:0;padding-left:1.4em}ol.top li{margin:6px 0}
.covgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
@media (max-width:760px){.covgrid{grid-template-columns:minmax(0,1fr)}}
</style>''')
prop = v1[v1.index('<section id="proposal">'):v1.index('<!-- ============ 5 ============ -->')]
prop = prop.replace('<li>U1921 输入对调（A1）。</li>\n', '')
prop = prop.replace('<li>改原理图：A1、A2、B1、B3、B4、B5、B7，以及四弦前端（若确认做），补"板间互连"页（D3）。</li>',
                    '<li>先修致命项：固件串口白名单、耳机 PORT_ENABLE、KEYS6 FPC 镜像、上盖可装配性、按键帽、J301 检测接法（见 2.1）。</li>\n    <li>改原理图：A2、B1、B2、B3、B4、B5、B7，以及四弦前端（若确认做），补"板间互连"页（D3）。</li>')
prop = prop.replace('首样按工作簿 B00–B12 分阶段上电；新增两项实测：A1 温度窗口（冷/热两点）和关机电流。',
                    '首样按工作簿 B00–B12 分阶段上电；新增实测：关机电流、J301 插入通断、C-to-C 充电器死电池唤醒、温度窗口冷/热两点。')
prop = prop.replace('<p class="note">需要原生文件才能动手修改：这次上传的是 PDF 和工作簿，R3 的 KiCad 工程、STEP 和固件源码还没有收到。仓库里只有 V26 存档。</p>',
                    '<p class="note">原生 KiCad、STEP、CadQuery 和固件源码已收到并审查；按你的要求，确认方向前不改动任何原设计文件。</p>')
prop = prop.replace('<li>BQ24074 路径管理、0.45 A 充电电流、TPS259470 eFuse 的 UV/OV 设定。</li>',
                    '<li>BQ24074 路径管理、0.45 A 充电电流、TPS259470 eFuse 的 UV/OV 设定。</li>\n      <li>U1921（TPS3700）温度窗口接法：复核确认正确，约 5–40 °C。</li>')
prop = prop.replace('<h2>4 建议方案</h2>', '<h2>5 建议方案（第一版，已按复核修订）</h2>')
ques = v1[v1.index('<section id="questions">'):v1.index('<footer>')]
ques = ques.replace('<h2>5 需要你确认的问题</h2>', '<h2>6 需要你确认的问题</h2>')
ques = ques.replace('</div>\n</section>', '''  <div class="card"><h4>Q7 实物核对</h4><p>能否找一只 Kycon STX-353K7A-6N 实物，用万用表量一下插入 TRS 插头前后 4–5、5–6 之间是否导通？这决定 J301 检测脚怎么改。</p></div>
  </div>
</section>''')
r3old = v1[v1.index('<section id="renders">'):v1.index('<!-- ============ 4 ============ -->')]
r3old = r3old.replace('<h2>3 R3 当前设计效果图</h2>', '<h3>按图纸尺寸重建的模型（第一版）</h3>').replace('<section id="renders">', '<div>').replace('</section>', '</div>')

body = f'''<title>SmartVio R3 审核报告</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&family=Noto+Serif+SC:wght@600;700&family=JetBrains+Mono:wght@400;600&display=swap">
{style}
<div class="wrap">
<header>
  <div class="eyebrow">SmartVio R3 · 电子小提琴模块 · 第二轮：原生工程包审查</div>
  <h1>SmartVio R3 审核报告</h1>
  <div class="meta">第二版 · 2026-10-15 · 输入：完整交付包 1417 个文件（SHA256 全部与 manifest 一致）：KiCad 原理图/PCB、CadQuery 结构源与 STEP、STM32/ESP32 固件源码与构建产物、线束与 BOM 数据、交付脚本、Web V12 · 主板 <span class="mono">bd2740bea32d…</span></div>
  <div class="fix-box">
    <h3>更正：第一版的 A1 撤回</h3>
    <p>第一版说 U1921（TPS3700）充电温度窗口的两个输入接反，建议对调。这是我的错误：我把 TPS3700 两路比较器的极性写反了。原接法正确，允许充电约 5–40 °C；如果照第一版去对调，反而会永远无法充电。<b>请不要按第一版 A1 修改。</b>其余第一版结论的复核状态见第 3 节。</p>
  </div>
  <div class="verdict">
    <p><strong>结论：</strong>原生包本身完整，版本绑定和 DRC/ERC 记录一致，但按现文件做首样，样机会<b>无法装配、开机后无声、无法充电</b>。最严重的是固件串口白名单把实际使用的帧类型全部丢弃（开机自检必失败）、耳机路由没打开 PORT_ENABLE、KEYS6 FPC 制造文件是镜像件、上盖一体件让三块板装不进去、按键帽两端都比孔大。本轮 7 个方向共 {len(allf)} 条有效发现，每条都由独立复核员尝试推翻：{nconf} 条确认，{nunc} 条需实物确认，另有 {len(refuted)} 条被推翻已剔除。</p>
    <div class="chips">
      <span class="chip c-a"><b>{cnt['critical']}</b>致命</span>
      <span class="chip c-b"><b>{cnt['high']}</b>高</span>
      <span class="chip c-c"><b>{cnt['medium']}</b>中</span>
      <span class="chip c-d"><b>{cnt['low'] + cnt['info']}</b>低 / 提示</span>
      <span class="chip c-ok"><b>{sum(len(out["review:" + a].get("checkedOK", [])) for a in AREA)}</b>项核对通过</span>
    </div>
  </div>
</header>
<nav class="sec" aria-label="章节">
  <a href="#top">1 先处理</a><a href="#findings">2 全部发现</a><a href="#prior">3 第一版复核</a><a href="#renders">4 效果图</a><a href="#proposal">5 建议方案</a><a href="#questions">6 需你确认</a><a href="#coverage">7 覆盖范围</a>
</nav>

<section id="top">
  <h2>1 最需要先处理的 {len([k for k in TOP if k in byk])} 项</h2>
  <p class="lead">按“不改就做不成样机”排序。详细依据和改法在第 2 节同名条目。</p>
  <div class="card"><ol class="top">{toprows}</ol></div>
</section>

<section id="findings">
  <h2>2 全部发现（按严重度）</h2>
  <p class="lead">“依据”里的行号、位号、网络名都已由复核员重新打开文件核对过。标“待实测确认”的条目，证据成立但结论取决于实物或包外规格书。</p>
  <div class="issues">{''.join(item(f) for f in allf)}</div>
  <h3>被复核推翻、已剔除的 {len(refuted)} 条</h3>
  <ul class="tight small">{refrows}</ul>
</section>

<section id="prior">
  <h2>3 第一版结论的复核状态</h2>
  <p class="lead">用原生网表、PCB、CAD 和固件逐条重查第一版的 A1–D8。</p>
  <div class="tbl"><table><thead><tr><th>ID</th><th>第一版结论</th><th>状态</th><th>说明</th></tr></thead><tbody>{prow}</tbody></table></div>
</section>

<section id="renders">
  <h2>4 效果图</h2>
  <h3>原生 CAD 渲染（第二版新增）</h3>
  <p class="lead">直接读取包内 STEP：20 件结构件（上盖、下杯、按键、导光柱、格栅、垫片与绝缘片）和 337 件参考体（Kycon 原厂插座、板件、元件占位、电池、FPC、天线）。滚轮在 CAD 里只有包络体，没有实体零件。</p>
  <figure><img src="img/cad-01-hero.jpg" alt="原生 CAD 外观：模块装在琴背木面"><figcaption>原生 CAD 外观：按键几乎与面板齐平（顶面 Z3.85），滚轮开孔内只有包络体。</figcaption></figure>
  <div class="gal">
    <figure><img src="img/cad-03-internal.jpg" alt="原生 CAD 内部装配，上盖隐藏"><figcaption>内部装配：扬声器直接坐在控制板上，FPC 天线贴在格栅下缘，同轴线横跨控制板。</figcaption></figure>
    <figure><img src="img/cad-04-exploded.jpg" alt="原生 CAD 分层爆炸图"><figcaption>分层爆炸：上盖带 USB/传感器托架（M1 指出三块板因此装不进去）。</figcaption></figure>
  </div>
  <div class="gal">
    <figure><img src="img/cad-05-section.jpg" alt="原生 CAD A-A 剖切"><figcaption>A-A 剖切（Y=37）：插座、音频板、主板、电池、下杯逐层可见，可与 M-R3-02 的 Z 链对照。</figcaption></figure>
    <figure><img src="img/cad-02-product.jpg" alt="原生 CAD 含下杯"><figcaption>含下杯外观。</figcaption></figure>
  </div>
  {r3old}
</section>

{prop}
{ques}

<section id="coverage">
  <h2>7 覆盖范围与未完成项</h2>
  <p class="lead">各方向审查员核对后认为正确的项目。</p>
  <div class="covgrid">{cov}</div>
  <h3>本轮未完成</h3>
  <ul class="tight">
    <li>查漏员提出的 3 项补充检查因额度中断：J301 几何（已由我按 Kycon 原厂图核对，见 2 节同名条目）、PCM1864 时钟与 SAI 配置交叉核对、电源 IC（U501/U1001/U1101/U1301）封装逐脚核对。后两项仍待做。</li>
    <li>TI 的 TPS3700、TPD2S300、TPS259470 规格书不在包内，网络策略也拦截了 ti.com；相关结论按器件常识判断，已标注。</li>
  </ul>
</section>

<footer>
  <p>方法：7 个方向各一名审查员读原生文件（网表、PCB S 表达式、CadQuery 源、固件源码与 ELF、线束 JSON、交付脚本、Web 代码并实际运行测试），每个方向再由一名独立复核员逐条尝试推翻，最后由查漏员找遗漏。效果图由包内 STEP 经 OCCT 网格化后渲染。按你的要求，确认方向前未修改任何原设计文件。</p>
</footer>
</div>
'''
body = body.replace('.diag{overflow-x:auto;', '.diag{min-width:0;overflow-x:auto;', 1)
body = body.replace('.issue .body{padding:13px 16px 12px;min-width:0}', '.issue{min-width:0}\n.card,.covgrid>*{min-width:0;overflow-wrap:anywhere}\n.issue .body{padding:13px 16px 12px;min-width:0;overflow-wrap:anywhere}', 1)
assert '.diag{min-width:0;' in body and 'overflow-wrap:anywhere' in body
open(S + '/report2/index.html', 'w', encoding='utf-8').write(body)
print('findings', len(allf), cnt, 'confirmed', nconf, 'uncertain', nunc, 'refuted', len(refuted), 'bytes', len(body))
