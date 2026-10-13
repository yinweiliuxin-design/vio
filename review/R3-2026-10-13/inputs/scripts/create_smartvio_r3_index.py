from pathlib import Path
import json,html,shutil
R=Path(__file__).resolve().parent/'SmartVio-R3-最新方案与工程资料-20261013'
def a(path,label):return f'<a href="{html.escape(path,quote=True)}">{html.escape(label)}</a>'
cards=[
 ('reports/SmartVio-R3-当前方案与缺项清单.pdf','当前方案与缺项清单','6页说明：架构、完成情况、缺失功能、测试与放行条件'),
 ('reports/SmartVio-R3-首样工作测试与候选BOM.xlsx','工作、测试与候选BOM','8张工作表；实测与供应商回签留空，可另存填写'),
 ('drawings/M-R3-机械图与装配效果图.pdf','机械工程图与实际CAD效果图','20件STEP对应的结构图、装配、内部与爆炸视图'),
 ('drawings/E-R3-PCB与FPC审查图.pdf','5块PCB与4组FPC审查图','按选中原生设计导出；全部0未连接/0 DRC'),
 ('drawings/E-R3-24页当前原理图.pdf','24页当前原理图','原生工程另附于engineering/project/eda'),
 ('engineering/mechanical/cad/mechanical_parts_assembly.step','模块总装STEP','20件设计件另附；参考体不是加工件'),
 ('engineering/firmware/handoff/R2_装配接线说明.html','接线、外线与触点说明','37条板间互连的21条FPC与16条待闭合路线'),
 ('review/current-feature-gap-review.txt','代码功能与缺项详细审计','已实现/待补齐逐项区分，JSON含源码行号与哈希'),
 ('software/SmartVio-Web-V12/00-效果与验收.html','Web V12界面效果与验收','当前客户端/后台截图；独立于R3硬件版本'),
 ('software/SmartVio-Web-V12/01-启动新版.cmd','启动Web V12本机演示','需Node 22+；也可在文件夹内双击该CMD'),
 ('engineering/project/selected-boards.json','选中板与版本绑定','准确文件名、主板及4子板SHA；部分稳定文件名保留R2'),
 ('复现环境与范围.txt','代码复现环境','已附源码/测试/镜像；外部工具链与历史路径需配置')]
page='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SmartVio 当前方案与工程资料 | 2026-10-13</title><style>
:root{--ink:#213c43;--green:#12695e;--line:#ccdcd6;--paper:#fff}*{box-sizing:border-box}body{margin:0;background:#f3f6f5;color:var(--ink);font:16px/1.65 'Microsoft YaHei',system-ui,sans-serif}main{max-width:1200px;padding:38px 24px;margin:auto}h1{font-size:38px;line-height:1.25;margin:10px 0 18px;letter-spacing:-.6px}h2{font-size:25px;margin:34px 0 16px}h3{font-size:18px;margin:6px 0}p{margin:10px 0}.eyebrow{letter-spacing:2px;font-size:13px;color:var(--green);font-weight:bold}.intro{max-width:900px;color:#52696e}.badge{background:#e0ece7;color:var(--green);padding:4px 11px;border-radius:25px;font-size:13px}.hold{border-left:5px solid #b06437;background:#fff1e5;padding:17px 20px;margin:24px 0}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.stat,.card{border:1px solid var(--line);background:var(--paper);padding:21px;border-radius:12px}.stat b{display:block;font-size:30px;color:var(--green)}.stat span{font-size:14px}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:15px}.card a{font-weight:bold;font-size:18px}.card p{font-size:14px;color:#52696e}.gallery{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}.gallery figure{margin:0;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:#fff}.gallery img{width:100%;height:340px;object-fit:contain;background:#fff}.gallery .hero{grid-column:1/-1}.gallery .hero img{height:auto;max-height:640px}.gallery figcaption{padding:13px 18px;font-size:14px;color:#51696e}a{color:var(--green);text-decoration:none;overflow-wrap:anywhere}a:hover{text-decoration:underline}.table-wrap{overflow-x:auto;border-radius:8px;border:1px solid var(--line)}table{width:100%;border-collapse:collapse;background:#fff;font-size:14px}th,td{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid var(--line)}th{background:#e3eee9}td code{overflow-wrap:anywhere;font-size:12px}ul,ol{padding-left:24px}li{margin:8px 0}details{border:1px solid var(--line);padding:16px;background:#fff;border-radius:9px;margin-top:15px}summary{cursor:pointer;font-weight:bold}footer{font-size:13px;color:#5e7478;border-top:1px solid var(--line);margin-top:34px;padding-top:20px}nav{display:flex;gap:15px;flex-wrap:wrap;margin:24px 0;font-size:14px}nav a{padding:7px 13px;border:1px solid var(--line);border-radius:20px;background:white}@media(max-width:760px){main{padding:22px 16px}h1{font-size:29px}.stats{grid-template-columns:repeat(2,1fr)}.cards,.gallery{grid-template-columns:1fr}.gallery .hero{grid-column:auto}.gallery img{height:auto}h2{font-size:22px}td,th{padding:9px}}
</style></head><body><main><div class="eyebrow">SMARTVIO / CURRENT ENGINEERING ARCHIVE</div><h1>电子小提琴<br>当前方案与完整资料</h1><span class="badge">2026-10-13归档 · 硬件R3 + Web V12</span><p class="intro">方案、图纸、实际CAD效果图、可编辑设计与代码集中在此。先看当前完成情况，再按下面入口查看和填写资料。</p>
<div class="hold"><strong>当前用于工程评审、工厂DFM和首样准备。</strong><br>16条普通互连、四弦独立拾音、供应商加工确认和实物验收仍待闭合。正常充电HOLD；本包不包含最终生产Gerber，也没有整机代工放行。</div>
<div class="stats"><div class="stat"><b>0</b><span>主板未连接项 / 原来15项</span></div><div class="stat"><b>5 + 4</b><span>5板、4FPC原生DRC通过</span></div><div class="stat"><b>20</b><span>有效结构STEP设计件</span></div><div class="stat"><b>0</b><span>实物测试已完成项</span></div></div>
<nav><a href="#files">资料入口</a><a href="#visuals">当前效果图</a><a href="#gaps">缺项与测试</a><a href="#source">代码与版本</a></nav><h2 id="files">资料入口</h2><div class="cards">'''
for path,label,desc in cards:page+=f'<section class="card">{a(path,label)}<p>{html.escape(desc)}</p></section>'
page+='</div><h2 id="visuals">当前R3模块效果图</h2><p>以下3张图直接依据当前结构STEP绘制。内部参考件使用实际/保守包络；尚未建模的16条互连不在图中，不以空白空间推定可安装。</p><div class="gallery">'
for i,(p,t) in enumerate([('R3-01-当前模块装配效果图.png','当前模块装配外观'),('R3-02-内部装配与软排线.png','内部板件与四组软排线'),('R3-03-结构分层爆炸效果图.png','结构分层爆炸视图')]):
 page+=f'<figure class="{"hero" if i==0 else ""}"><a href="visuals/{p}"><img src="visuals/{p}" alt="{t}"></a><figcaption>{t} · 点击查看原图</figcaption></figure>'
page+='''</div><details><summary>历史整琴外观意向图（不作为当前加工依据）</summary><p>该图为2026-10-09历史概念外观，未绑定当前R3全部尺寸、拾音器或完整线路。完整琴体制造图未取得。</p><img style="max-width:100%;max-height:750px;object-fit:contain" src="visuals/concept-history/SmartVio-整机外观效果图-20261009.png" alt="历史整琴外观意向图"></details>
<h2 id="gaps">现在还缺什么</h2><ol><li><strong>硬件/拾音：</strong>现有J101两线单路输入不足以证明四弦独立；需确认真实拾音器并更新前端、采集通道、DSP和协议。</li><li><strong>装配互连：</strong>37条板间互连已有21条候选FPC；另16条需真实线材、完整路径、裁长、弯曲、焊接与试装。外接电池/热敏/拾音引线也要验收。</li><li><strong>加工确认：</strong>主板叠层/细孔、FPC定制叠层、USB阻抗、外壳材料工艺、公差、真实琴腔与来料尺寸待工厂回签。</li><li><strong>代码：</strong>产品级USB Audio/MIDI、设备身份/配网、签名OTA、四弦独立算法、完整用户DSP、原生App及云端认证/支付等仍未形成合格版本。</li><li><strong>样机实测：</strong>烧录、分步上电、保护与掉电、时钟/音频/USB/RF、续航/温升、实琴演奏和装配可靠性尚未运行。</li></ol>
<p>固件已有16项host测试通过；Web V12本次73/73、保留V11本次11/11通过。它们均不等于设备和实物测试。工作簿准备了25项前置工作、23阶段、70项空白测量、12项小提琴专项和10项供应商回签。</p>'''
wire=json.loads((R/'engineering/firmware/handoff/R2_逐线接线表.json').read_text('utf-8-sig'))
page+='<details><summary>展开16条待闭合板间互连</summary><div class="table-wrap"><table><tr><th>编号</th><th>网名</th><th>端点</th><th>线规</th></tr>'
for r in wire:
 if r.get('proposed_fpc'):continue
 vals=[r['id'],r['net'],f"{r['from_ref']}.{r['from_pad']} → {r['to_ref']}.{r['to_pad']}",r['wire_spec']]
 page+='<tr>'+''.join('<td>'+html.escape(v)+'</td>' for v in vals)+'</tr>'
page+='</table></div></details><h2 id="source">源码、图纸原件与版本绑定</h2><p>可编辑设计和源码均已收录。部分文件沿用R2名称与接口编号，以当前选板清单、原生审计和SHA为准；历史说明不能覆盖当前HOLD状态。</p><div class="table-wrap"><table><tr><th>对象</th><th>当前源/入口</th><th>用途</th></tr>'
rows=[('原生电气','engineering/project/eda/SmartVio.kicad_pro','KiCad原理图工程、符号库与24页源'),('结构参数源','engineering/mechanical/cad/build_mechanics.py','CadQuery可编辑源，20零件与参考体分离'),('电子位号','engineering/pre-sample/candidate-bom-and-placement.json','333条候选记录，含DNP/外接RT1921/工艺分类'),('贴装与轮廓审阅','engineering/fabrication/export-manifest.json','座标CSV、DXF、SVG和测试网表；未放行生产'),('STM32与ESP固件','engineering/firmware/README_R2_先读我.txt','自有源码、诊断固件和测试；参照当前状态JSON'),('Web客户端和后台','software/SmartVio-Web-V12/demo/README.txt','Node回环服务、JS/CSS/HTML、测试和媒体存储说明'),('当前原生证据','engineering/verification/independent/revision-audit.json','元件/引脚/网络/原理图/PCB及全规则检查'),('结构证据','engineering/mechanical/assembly-status.json','20件有效实体与建模范围干涉报告'),('功能缺口证据','review/current-feature-gap-review.json','对应源码行号、版本哈希和待验收功能')]
for label,p,desc in rows:page+=f'<tr><td>{label}</td><td>{a(p,p)}</td><td>{desc}</td></tr>'
page+='</table></div><h3 style="margin-top:22px">当前选中电路板</h3><div class="table-wrap"><table><tr><th>板件</th><th>原生PCB</th><th>SHA-256前16位</th></tr>'
s=json.loads((R/'engineering/project/selected-boards.json').read_text('utf-8-sig'))
for role,p in s['boards'].items():page+=f'<tr><td>{role}</td><td>{a("engineering/project/"+p,Path(p).name)}</td><td><code>{s["boardSHA256"][role][:16]}</code></td></tr>'
page+='</table></div><footer>'+a('先读我_当前版本.txt','使用说明')+' · '+a('manifest-sha256.json','全部文件SHA清单')+' · '+a('review/package-content-qa.json','交付内容核查')+'<p>保留原始资料；实测表另存填写。文件校验只验证完整性，不代表加工、产品性能或认证合格。</p></footer></main></body></html>'
(R/'index.html').write_text(page,'utf8')
(R/'engineering/fabrication/先读我_审阅导出非生产指令.txt').write_text('''本目录是当前五块选中板的审阅导出。无Gerber/钻孔生产CAM。
native-all-placement为KiCad原生完整审阅座标；SMT及手工子集按原生物料属性派生；333条总表包含外置RT1921及铜端点，不是采购数量。
当前没有批准的整机BOM/板厂叠层/FPC工艺/贴装单，不能据此直接下整机加工订单。
''','utf8')
tools=R/'delivery-tools';tools.mkdir(exist_ok=True)
for name in ['build_smartvio_r3_delivery.py','create_smartvio_r3_overview.py','create_smartvio_r3_index.py']:
 shutil.copy2(Path(__file__).resolve().parent/name,tools/name)
for name in ['build_r3_workbook.mjs','verify_r3_workbook.py']:
 shutil.copy2(Path(__file__).resolve().parent/'.r3-workbook-build-20261013'/name,tools/name)
(tools/'README.txt').write_text('本目录保存生成本轮交付资料的脚本源码。脚本保留原工作区路径用于追溯，迁机需配置。不要将历史打包/迁移脚本作为产品启动器。当前查看入口是上一级index.html；Web启动器位于software/SmartVio-Web-V12。\n','utf8')
print('Created index, notices, and delivery source scripts')
