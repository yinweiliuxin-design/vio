from pathlib import Path
import json, html, hashlib, shutil
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle

ROOT=Path(__file__).resolve().parent/'SmartVio-R3-最新方案与工程资料-20261013'
ENG=ROOT/'engineering'; REP=ROOT/'reports'; REP.mkdir(exist_ok=True)
pdfmetrics.registerFont(TTFont('ZH','C:/Windows/Fonts/simhei.ttf'))
pdfmetrics.registerFont(TTFont('Latin','C:/Windows/Fonts/arial.ttf'))
PAPER=A4; W,H=PAPER; M=44; CW=W-M*2
INK=colors.HexColor('#203c41'); GREEN=colors.HexColor('#12695e'); GRAY=colors.HexColor('#566b70'); AMBER=colors.HexColor('#a9582c')
styles={
 'body':ParagraphStyle('body',fontName='ZH',fontSize=10,leading=15.7,textColor=INK,spaceAfter=8,wordWrap='CJK'),
 'small':ParagraphStyle('small',fontName='ZH',fontSize=8,leading=11.4,textColor=GRAY,wordWrap='CJK'),
 'cell':ParagraphStyle('cell',fontName='ZH',fontSize=8.7,leading=12.8,textColor=INK,wordWrap='CJK'),
 'h2':ParagraphStyle('h2',fontName='ZH',fontSize=12,leading=18,textColor=GREEN,spaceAfter=7,wordWrap='CJK')}
out=REP/'SmartVio-R3-当前方案与缺项清单.pdf'
c=canvas.Canvas(str(out),pagesize=PAPER)
c.setTitle('SmartVio R3 当前方案与缺项清单 | 2026-10-13')
c.setAuthor('SmartVio engineering review')
page=0;y=0; textpages=[]; pagecontent=[]
def para(t,kind='body',gap=8):
 global y
 p=Paragraph(t,styles[kind]); _,h=p.wrap(CW,H)
 assert y-h>48, f'Page {page} overflow at {t[:30]}'
 p.drawOn(c,M,y-h);y-=h+gap;pagecontent.append(t)
def title(t):
 global page,y,pagecontent
 if page:
  textpages.append(pagecontent);c.showPage()
 page+=1;pagecontent=[];y=H-77
 c.setFillColor(GREEN);c.setFont('ZH',9);c.drawString(M,H-31,'SMARTVIO  /  R3工程 + WEB V12  /  2026-10-13')
 c.setStrokeColor(colors.HexColor('#d1e1dd'));c.line(M,43,W-M,43)
 c.setFont('ZH',8);c.setFillColor(GRAY);c.drawString(M,29,'当前资料归档版 · 整机生产待闭合 · 实物测试 0 项')
 c.drawRightString(W-M,29,str(page))
 c.setFont('ZH',20);c.setFillColor(INK);c.drawString(M,y,t);y-=32
 pagecontent.append(t)
def table(rows,widths=None,head=True):
 global y
 widths=widths or [CW/len(rows[0])]*len(rows[0])
 data=[[Paragraph(html.escape(str(v)).replace('\n','<br/>'),styles['cell']) for v in row] for row in rows]
 t=Table(data,colWidths=widths,hAlign='LEFT')
 cmds=[('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.45,colors.HexColor('#c5d9d5')),
 ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]
 if head:cmds.append(('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e4efeb')))
 t.setStyle(TableStyle(cmds));_,h=t.wrap(CW,H)
 assert y-h>50,f'Page {page} table overflow {h}/{y}'
 t.drawOn(c,M,y-h);y-=h+14;pagecontent.extend(' | '.join(map(str,r)) for r in rows)

title('01  当前电子小提琴方案')
para('本次交付汇总目前已知最新成果：R3电子模块硬件、结构与固件，另附独立版本的 Web V12 客户端/本机后台。归档日期为2026-10-13，R3设计核查证据主要形成于2026-10-12；软件回归本次重新运行。')
para('产品定位','h2')
para('在既有4/4小提琴上装配电子模块，提供拾音输入、音频处理/监听、设备控制及后续数字学习扩展。当前真实工程对象是电子模块与相关板件、外壳和接口；原木琴体、琴颈与琴桥的完整制造CAD未取得。四个安装孔已预留，工厂按实际琴体配装。')
table([['子系统','当前选用/设计','验证边界'],['计算与采集','STM32H743 + PCM1864 + 模拟前端','原生连接及目标编译通过；实际信号未测'],['无线','ESP32-MINI-1U-N4 + TX2400-FPC3-2509','保留无线诊断源码/镜像；整机射频未测'],['电路与装配','主板、USB、音频、控制、传感器5板；4组FPC','5板/4FPC原生检查通过；16条普通互连待闭合'],['结构','148×49mm上盖、下杯及按钮/隔片等20件STEP','模型范围内零碰撞；整体名义约24.90mm'],['软件','R3诊断固件 + Web V12 浏览器演示','两者独立版本；无真实硬件联调结果']],[85,220,CW-305])
para('当前最关键的结论','h2')
para('主板未连接项已从15降为0，5块电路板与4组FPC的原生DRC均为0，且没有以忽略检查或删除网络消除问题。20件结构STEP为有效实体，已建模装配范围无穿透。以上支持继续工程评审与供应商DFM，不构成整机合格或首批代工放行。')
para('本包不含最终生产Gerber。当前状态仍是制造HOLD；正常充电HOLD；实物测试0项。',gap=3)

title('02  音频、拾音与功能边界')
para('当前硬件信号关系','h2')
table([['路径','已存在的设计','尚缺证据/实现'],['琴弦信号','J101：1=PZ_RAW、2=GND，两线单路拾音输入','真实拾音器型号、尺寸、电容、极性、最大输出'],['模拟采集','U601 PCM1864：拾音 + AUX L/R，共3路已接输入；第4路未接','四弦独立输入前端与至少6路同时采集方案'],['实时音频','MCU本地采集/处理/监听代码与SAI/DMA框架','实物时钟、串扰、噪声、失真、延迟及掉帧'],['外部接口','USB子板、音频接口、控制键与传感器板','USB权限/设备协议、接口电气与实际插拔测试'],['数字学习','Web端调音、单音跟奏参考评分及节拍等','硬件拾音驱动的四弦识别、评分数据集与标定']],[75,225,CW-300])
para('四弦独立需求保留，当前单路接口不能算作已完成','h2')
para('四根琴弦独立拾音并保留立体声AUX，需要至少6路同时输入。现板把4通道ADC中的3路用于拾音与AUX，因此不能将多音算法或模拟页面视作四弦独立电路。未取得用户删减功能授权，交付仍保留这一需求并将其列为硬件冻结前缺项。')
para('后续候选方向为增加独立高阻前端/第二采集器与相应接口，保持已有AUX和返回功能。该方向尚未制成已验证原理图/PCB/固件：必须先取得真实拾音规格，再核对时钟、SAI/TDM、引脚资源、DMA、通道映射与输出争用。禁止直接并接两个有效数字输出。')
para('外观与安装范围','h2')
para('visuals内的R3模块装配、内部和爆炸图依据当前STEP生成。concept-history中的整琴图是历史外观意向，不代表当前电路、尺寸或完整线束的加工结构。既有琴腔78×47×22mm仅为历史几何依据，仍需实物测量。')

title('03  板间连接与生产前整改')
para('37条板间功能互连中，AUDIO6、COVER6、POTS3、KEYS6四组FPC承载21条。它们已有原生铜线与安装/展开模型；供应商叠层、孔、覆盖膜与实装仍待确认。其余16条如下，线长、弯曲及完整装配路线未冻结。')
harness=json.loads((ENG/'firmware/handoff/R2_逐线接线表.json').read_text('utf-8-sig'))
left=[r for r in harness if not r.get('proposed_fpc')]
assert len(left)==16
rows=[['编号','网络','端点','线规']]
for r in left:
 rows.append([r['id'],r['net'],f"{r['from_ref']}.{r['from_pad']} → {r['to_ref']}.{r['to_pad']}",r['wire_spec']])
table(rows,[39,139,267,CW-445])
para('P26/S30/A32/U90为受控线规类别，未替代供应商实际型号。USB差分对须成对同路，不能凭两条网络MATCH认定阻抗/眼图合格。新增的3条电池线、2条独立热敏线、2条原拾音线，以及扬声器触点和天线整件，还需独立核查；37不是整机导线总数。','small')

title('04  已有代码与仍缺的代码')
table([['模块','已交付内容','缺口与测试'],['STM32 R3','共享控制/遥测、音频框架、服务故障清除、充电会话保护、BRINGUP/SERVICE镜像；16个host入口通过','尚未烧录实测；USB实际授权、校准及电池/独立温度资格适配仍不完整；正常充电禁用'],['ESP32','无线诊断、应答/重试、PCM相关源码与已核SHA的历史编译产物','当前版本实物RF、音频吞吐、失联/恢复、时钟漂移、干扰和闭壳性能未测'],['Web V12','曲库/收藏、浏览器原创合成音色、真实麦克风调音、录音视频、4轨Looper、练习/预设/工程保存；本机后台','尚无R3真实BLE/USB接入；Web MIDI枚举不代表设备协议闭环'],['正式服务','本机HTTP API、持久数据及运营页面','多用户认证/权限、生产部署、支付订阅、云同步、签名OTA和设备身份未完成生产验收'],['原生客户端','现有浏览器代码与UI源可继续开发','iOS、Android、HarmonyOS原生工程/安装包及系统音频/蓝牙适配未交付为合格版本'],['四弦算法','需求与扩展路线保留；现有单音调音/评分逻辑','四路前端/采集驱动、独立通道DSP、标定数据集、多音/弓法/力度与评分准确性缺实证']],[70,226,CW-296])
para('本次软件复核：Web V12共73/73项Node测试通过，保留V11共11/11项通过。原固件16个host测试的源码/产物哈希已再次核对。浏览器真麦克风、相机、实琴、设备协议、硬件与现场稳定性均不能由这些测试替代。')
para('代码与工具环境','h2')
para('自有源码、测试、构建脚本、STM32/ESP产物及STM32使用的现有CMSIS/HAL/DSP源随包保留。ESP-IDF 5.4.3、交叉编译器、KiCad 10.0.6、CadQuery 2.8等开发工具需在目标电脑配置；历史构建脚本含本机路径，包不是免安装编译环境。详见根目录复现环境与范围.txt。')

title('05  缺项、责任与测试顺序')
table([['优先级','交付前需要补齐','完成证据'],['P0 加工前','四弦拾音真实选型、前端/ADC通道与协议方案','原厂规格、更新电路/PCB/固件及一致性审查'],['P0 加工前','16条互连与全部外接引线/插头/焊点完整装配','实际线材MPN、长度/弯曲、CAD及断电试装'],['P0 加工前','主板8层叠层、细孔/FPC叠层、壳体工艺与材料DFM','供应商书面回签、可制造参数、批准的版本SHA'],['P0 加工前','真实琴体/琴腔/电池/插座尺寸与装配公差链','实物尺寸记录，25mm总高检具与间隙验收'],['首样阶段','来料、短路/极性、限流分步上电、故障/断电恢复','操作者、仪器/夹具、原始电压电流/波形与结果'],['首样阶段','音频/USB/RF、真琴演奏、温升、接触与可靠性','23阶段/70项测量与12项小提琴专项记录'],['放行阶段','问题关闭、版本复查、首件合格和代工工艺批准','签字记录与最终Gerber/钻孔/贴装/工艺版本']],[69,227,CW-296])
para('样机前能完成：设计检查、材料/工艺询价、夹具与测试计划、资料同步。只有做出实物后才能完成：实际音色、音量、噪声、端到端延迟、续航、温升、射频、装配强度和演奏测试。两类证据不能互相替代。')
para('工作簿已准备25项前置工作、23个测试阶段、70项候选测量记录、12项小提琴专项和333条候选电子位号。所有未测记录保持空白/未测试；阈值为工程候选，需要测试负责人确认方法、仪器与适用条件。333条位号不等于333种采购物料，也不是已放行采购单。')
para('供应商待回签：PCB/FPC叠层及孔工艺、USB阻抗、来料高度/公差、壳体加工可达性与材料、线束成端、拾音器规格、首批数量、测试与返修责任。当前没有供应商加工批准记录。')

title('06  压缩包使用与版本控制')
table([['目录/入口','内容与用途'],['index.html / 打开全部资料.cmd','总导航：方案、当前效果图、图纸、代码、缺项与证据'],['reports/','当前方案PDF、可填写测试/物料工作簿'],['drawings/ + visuals/','当前工程查看图与24页原理图；结构装配/内部/爆炸图；历史概念另标'],['engineering/project/','选中5板+4FPC，24页原生原理图、符号封装库、canonical source'],['engineering/mechanical/','20件STEP、总装STEP、参考体、可编辑CadQuery源与尺寸参数'],['engineering/fabrication/','审阅用装配/铜层SVG、轮廓DXF、座标CSV、IPC测试网表；非生产CAM'],['engineering/firmware/','R3固件、测试、构建产物、版本绑定、接线/线规与首板计划'],['software/SmartVio-Web-V12/','当前Web客户端/本机后台、V11保留源、双击启动及界面设计源'],['review/ + delivery-tools/','当前缺项审计、哈希/复制与校验记录；本次制包和文档源码']],[165,CW-165])
para('解压后先打开index.html。工程文件以engineering/project/selected-boards.json及其SHA选择；部分子板、FPC和固件仍沿用R2文件名/稳定接口编号，已按当前哈希绑定，不能只按文件名中的版本数字选择。')
para('本包保留当前源代码与必要的历史兼容上下文，未将失败候选PCB、旧15项未连接报告、旧22条线报告或机器缓存混作现行交付。原件仍保留在原工作目录；复制/文字校正记录见review/source-copy-ledger.json。')
para('当前电气主板 SHA-256（用于核对，非批准签字）','h2')
para('bd2740bea32d6123404d4e7e5cab2b5f80<br/>c005b24658d96b6ebe3b7cc8e2bc7b','small')
para('交付结论：现在可以将本包交给研发/工厂进行技术评审、DFM回签和首样准备。仍需关闭前述设计/加工缺项后才能下首样加工任务；整机样品通过实测后再决定首批代工放行。')
textpages.append(pagecontent);c.save()
(REP/'当前方案与缺项_可编辑文本.txt').write_text('\n\n'.join('\n'.join(x) for x in textpages),'utf8')
(ROOT/'先读我_当前版本.txt').write_text('''SmartVio 当前资料归档版｜2026-10-13
硬件/结构/固件：R3。客户端/本机后台：Web V12（独立版本，未与R3硬件实物联调）。
1 解压到本地，双击“打开全部资料.cmd”。
2 主板未连接0、5块板与4组FPC原生DRC0；4FPC建模21/37条互连。
3 仍缺16条普通互连完整路线、四弦拾音硬件方案、供应商DFM回签与全部实物测试。正常充电HOLD。
4 原理图/PCB/STEP/源码/固件/候选BOM与测试工作簿均在包内。参考几何不是加工件；历史整琴效果图不是R3实装验证。
5 当前版本是工程评审与首样准备资料；没有最终Gerber、没有完整琴体制造图，也未获首批整机代工放行。
6 所有未测值保持未测试。先另存Excel记录副本再填写，保留原始波形、操作人和版本SHA。
7 部分文件沿用R2名称，以selected-boards.json和SHA为准。旧脚本/基线说明的历史状态不得覆盖当前状态。
8 manifest-sha256.json列出包内文件SHA。校验只能证明文件完整，不能证明产品合格。
''','utf8')
(ROOT/'打开全部资料.cmd').write_bytes(b'@echo off\r\nstart "" "%~dp0index.html"\r\n')
(ROOT/'复现环境与范围.txt').write_text('''SmartVio R3 2026-10-13 复现范围
查看：PDF查看器；STEP用FreeCAD等；KiCad 10.0.6打开原理图和PCB。
Web：Node.js 22或更新；本包software/SmartVio-Web-V12/01-启动新版.cmd使用本机回环服务，不启公网。无需npm安装。
固件：Python 3.12、PowerShell、TinyCC host编译器、arm-none-eabi工具链；ESP-IDF5.4.3及对应Xtensa工具。
已附：自有C/H/汇编/链接脚本、所有当前测试、STM32/ESP镜像及构建结果；firmware/vendor-source含实际使用的现有CMSIS/HAL/DSP源与其许可文件。
未附：完整ESP-IDF/工具链安装包、Node/Python/KiCad/CAD运行库。这些不是本项目独立开发的源代码。
engineering/firmware/build.py仍保留证据生成时E盘ROOT与编译器路径；迁机需将VENDOR映射到附带vendor-source并配置同版本工具路径。原构建报告的绝对路径用于追溯。
结构：CadQuery2.8/OCP7.9，见mechanical/requirements.txt；extract_board_geometry.py用KiCad自带pcbnew Python运行。标准Python不能导入pcbnew。
复核：engineering/reproduce/verify_revision.py；FPC以verify_flex_buses.py复核；当前CAD与原生板SHA必须重新匹配。模型通过不替代实物测试。
历史prepare/route/merge/finalize及旧打包脚本不是批量启动入口，部分依赖未随包带出的历史中间文件。禁止盲目执行全部脚本。
包内正常充电禁用，不提供自动刷机或充电开放操作。
''','utf8')
print(json.dumps({'file':str(out),'pages':page,'status':'CREATED_PENDING_RENDER_QA'},ensure_ascii=False))
