"""Create the reviewed V16 design report and editable HTML; render all PDF pages."""
from pathlib import Path
from html import escape
import json, subprocess, hashlib
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image, ImageOps, ImageDraw
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'dist/reports';OUT.mkdir(exist_ok=True)
QA=ROOT.parent/'artifacts/v16-20261015/pdf-qa';QA.mkdir(exist_ok=True)
pdfmetrics.registerFont(TTFont('MSYH',r'C:\Windows\Fonts\msyh.ttc'))
pdfmetrics.registerFont(TTFont('MSYHB',r'C:\Windows\Fonts\msyhbd.ttc'))
P=ParagraphStyle('p',fontName='MSYH',fontSize=10,leading=17,textColor=colors.HexColor('#263c32'),spaceAfter=10,wordWrap='CJK')
H=ParagraphStyle('h',parent=P,fontName='MSYHB',fontSize=22,leading=31,spaceAfter=18)
S=ParagraphStyle('s',parent=P,fontName='MSYHB',fontSize=12,leading=20)
SM=ParagraphStyle('small',parent=P,fontSize=8,leading=13)
pages=[
 ('SmartVio V16 可行性与融合报告',[
  ('结论与实施顺序','先核对现状与来源，再审核每个功能方案，最后实施并单列验收记录。学习、MIDI 与社区方案已在代码实施前审查；音色在下载来源和 CC0 许可核对后批准。此报告描述设计决策，最终测试结果另附，避免把计划当成完成。'),
  ('四个结论','学习页采用六步主路径，每屏只有一个目标；曲库/练习增加独立的小提琴采样示范；MIDI 修复异步覆盖与生命周期问题；音乐社区新增有审核、可清理的短视频，并保留图文。'),
  ('可核验的现状','审核基线提交 2c7f0a7ce5ffd97372092a1cc4ccaafc36439fbd。现有九课、七步界面导览、68首曲库、四语、离线模式、录音与创作预设均需保留。当前 Acoust​​ic 示范实际是振荡器合成，并非真实小提琴录音。'),
  ('范围与实测边界','本轮可验证源代码、模拟 MIDI、SQLite/R2 协议以及本机浏览器。未连接真实电子琴，未取得各品牌手机实测数据，不声称蓝牙延迟、专业音质或所有设备兼容性已经达标。全部新文件和临时产物位于 E 盘。')]),
 ('01 学习路径：让新人知道下一步',[
  ('问题','九个练习卡与七步按钮导览同时占据主页面，课程进度、操作引导和演奏能力容易混淆。学习内容需要逐步呈现，不能通过看完动画就宣布学会拉琴。'),
  ('六步主路径','认识界面 → 调好四根弦 → 跟上四拍 → 练一个小乐句 → 录下来回听 → 选择下一小步。每屏提供一个目标、两句简单说明、原创 SVG/CSS 动画、上一步/下一步以及前往实际功能的按钮。'),
  ('进度与动画','只在用户主动点击“我看懂了”时记录 understood。允许随时跳过和返回，暂停与重播动画，并响应系统减少动态设置。动画是教学示意，不是已验证的真人运弓姿势。教程不会自动播放音频或申请麦克风、摄像头、蓝牙权限。'),
  ('历史数据','新路径使用独立稳定步骤 ID 和 schema/pathVersion。旧九课完成标记、guideV2 的 0–6 云端索引保持原义；旧入口收纳到“更多练习与按钮说明”。新进度当前保存在本机，纳入导出和明确清除流程。')]),
 ('02 声音选择：琴声与对音各司其职',[
  ('声学与用户体验','弓弦激励、谐波和琴体共振决定小提琴音色；单一振荡器不能代表真实琴声。对初学者和爱好者，真实单音采样更利于熟悉琴声；对演奏者，少量采样缺少连弓、换弦和力度句法，不能替代真人演奏教学。这是结合声学资料的产品判断，尚无用户听音评分。'),
  ('建议采用','曲库/练习示范、MIDI 回放与音阶试听统一使用独立“示范音色”：默认小提琴单音采样，并可选择纯净合成音。采样序列明确标识，不宣称真人整曲演奏。资源失败明确提示，让用户主动切换，避免静默替换。'),
  ('不连带替换','调音器使用稳定正弦参考音，不叠加揉弦和混响；伴奏/弦乐保留合成声部与低音，避免全变成独奏小提琴；真实麦克风仍录制原输入；九种创作音色保留，原声素描改名基础合成音。'),
  ('来源和性能门槛','VSCO-2-CE 的七个 Solo Violin Arco Vib 弱奏样本，固定提交 440300901dfe9275fd84e0b7763af1f8443ae62e，CC0-1.0。保留完整许可、作者和逐文件哈希。应用资源目标 ≤1MB、按需加载；转换为单声道 22050Hz PCM16。小提琴采样本身有揉弦，因此不用于调音基准。')]),
 ('03 MIDI：模拟验收和真实设备边界',[
  ('基线','MIDI 与 BLE MIDI 原有 60 项测试通过，但额外乱序探针发现两个 P1：先选的大文件晚返回覆盖后选文件；读取期间手改音符被导入结果覆盖。旧用例通过并不能证明这些竞态不存在。'),
  ('修复设计','为导入增加独立请求序号和文档修订号；编辑、清除、替换、开始采集和卸载使旧读取失效。卸载解绑 MIDIAccess 监听，重新挂载可复用已有授权而不重复索权。'),
  ('模拟验收清单','无 MIDI API、权限拒绝、无端口、热插拔、悬挂音符关闭、录入后编辑、速度保存、SMF 导出再导入，以及异步读取乱序/手改保护。必须检查结果文档与事件资源，不只检查按钮存在。'),
  ('待硬件验收','真实琴的 BLE MIDI 广播与服务、固件时戳、Web MIDI/系统适配、连接恢复、音符丢失和端到端延迟，需要对应型号和设备测试。模拟通过不会转写为真机通过。')]),
 ('04 音乐社区：参考交互并自行实现',[
  ('参考来源与边界','研究 TikTok、X、YouTube 官方公开的短视频/发布/互动说明，以及 PeerTube 与 WebRTC samples 的公开代码和许可证。没有取得这些商业平台的私有后台或原生 App 源码，也没有绕过登录抓取私人内容。'),
  ('融合方式','采用原创音乐主题页面：图文动态继续保留，新增短视频筛选与视频卡；原生播放控件、竖屏优先、评论、点赞和举报沿用现有社区身份与权限。首版按时间或热度排序，不包装成与大平台等价的推荐算法。'),
  ('发布闭环','用户确认素材权利后上传自己的 MP4/WebM，独立限制 60秒/20,000,000 字节；服务端检查真实容器、编码和时长。保存草稿 → 提交审核 → 管理员预览并审批 → 客户端可见。被隐藏或删除后，媒体读取仍复核权限。'),
  ('开放源码许可处理','PeerTube 为 AGPL-3.0-or-later，本轮仅参考架构，不复制其实现；WebRTC samples 为 BSD-3-Clause，本轮以浏览器标准接口自行实现。引用和许可证识别在社区可行性 JSON 留存，没有把公开可读等同于可任意复制。')]),
 ('05 视频端口、清理与性能设计',[
  ('接口','POST /api/community/videos 上传原文件；GET/HEAD /videos/:id 播放并支持单 Range；GET /:id/status 查询；POST /:id/cancel 和 /delete 取消或删除。post-save 只接受 kind:video + mediaId，服务端重建可信附件元数据。'),
  ('权限与审核','上传、读取、Range、状态和删除都校验当前身份与可见性。草稿/待审只对作者或管理员开放；已发布才向有社区权限的访问者开放。只有 ready 媒体可保存/提交/审批，多篇未删除帖子引用的资源不得直接删除。'),
  ('取消不等于已删除','文件上传可能在浏览器取消后仍继续写入。持久化状态和取消墓碑覆盖晚返回；cleanupPending 在 R2 或数据库结果不确定时保持。页面提供检查状态和重试清理，不把 AbortError 或网络超时称为删除成功。异常原文件由用户继续保留。'),
  ('移动性能与兼容','播放需用户点击；同一时刻只播放一个视频，离开视口、切页或后台时暂停，preload=none 控制流量。编码支持因系统不同，不可播放时明确提示。暂不加入转码集群、直播、无限推荐和第三方平台视频搬运。'),
  ('验收门槛','真实 MP4/WebM 夹具、伪 MIME/截断/超限拒绝、Range 逐字节、二账号隔离、草稿到发布再隐藏、取消晚写入、清理失败和重试、迁移不破坏原图文。移动浏览器样式及后台预览需另行交互检查。')]),
 ('06 审核结论与来源',[
  ('自审结论','学习：通过，保持“理解提示”和演奏能力的区别。MIDI：通过修复设计，新增竞态回归后采用。声音：来源与许可核对后有条件通过，需验证资源大小、取消与纯参考音隔离。社区：有条件通过，必须完成权限、容器、清理和前后台闭环测试。'),
  ('交付与回退','报告、原始审查 JSON、实现源码和最终测试记录分开保留。发布保持现有私密访问范围，源码备份到已授权的 yinweiliuxin-design/vio；不得备份用户录音、生产数据库和凭据。若任一功能未过门槛，明确列为待验收，不声称完成。'),
  ('主要证据','源代码审核：dist/tutorial.js、client.js、audio-engine.js、midi.js、community.js；worker/community.mjs；tests。报告 JSON 位于 E 盘 sites/artifacts/v16-20261015。公网资料为官方说明和许可，下列链接可复核。')])
]
sources=[('Violin acoustics, UNSW','https://www.phys.unsw.edu.au/jw/violintro.html'),('VSCO-2-CE / CC0','https://github.com/sgossner/VSCO-2-CE'),('TikTok official recommendations','https://support.tiktok.com/en/using-tiktok/exploring-videos/how-tiktok-recommends-content'),('X official video help','https://help.x.com/en/using-x/x-videos'),('YouTube Shorts help','https://support.google.com/youtube/answer/10059070?hl=en'),('PeerTube license','https://github.com/Chocobozzz/PeerTube/blob/develop/LICENSE'),('WebRTC samples license','https://github.com/webrtc/samples/blob/gh-pages/LICENSE.md'),('MediaStream Recording standard','https://www.w3.org/TR/mediastream-recording/')]
story=[];html=[]
for ix,(title,parts) in enumerate(pages):
 if ix:story.append(PageBreak())
 story.append(Paragraph(escape(title),H));html.append('<section><h1>'+escape(title)+'</h1>')
 story.append(Paragraph('2026.10.15 · Silvio / VELLEN · 审核与实施依据',SM))
 for sub,body in parts:
  story += [Paragraph(escape(sub),S),Paragraph(escape(body),P),Spacer(1,5)]
  html.append('<h2>'+escape(sub)+'</h2><p>'+escape(body)+'</p>')
 if ix==len(pages)-1:
  for label,url in sources:
   story.append(Paragraph('<link href="'+escape(url,quote=True)+'" color="#356e54">'+escape(label)+'</link>',SM))
   html.append('<p><a href="'+escape(url,quote=True)+'">'+escape(label)+'</a></p>')
 html.append('</section>')
def footer(c,doc):
 c.setStrokeColor(colors.HexColor('#cbd9cf'));c.line(42,40,553,40)
 c.setFont('MSYH',8);c.setFillColor(colors.HexColor('#667c6b'));c.drawString(42,27,'SmartVio V16 | 可行性审查，非真机认证');c.drawRightString(553,27,str(doc.page))
pdf=OUT/'SmartVio-feasibility-20261015.pdf'
SimpleDocTemplate(str(pdf),pagesize=A4,rightMargin=43,leftMargin=43,topMargin=42,bottomMargin=54,title='SmartVio V16 可行性与融合报告',author='SmartVio').build(story,onFirstPage=footer,onLaterPages=footer)
HTML='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SmartVio V16 可行性与融合报告</title><style>body{font-family:system-ui,sans-serif;color:#263c32;background:#f2f5ef;margin:0}main{max-width:900px;margin:auto;padding:20px}section{background:white;margin:20px 0;padding:clamp(20px,5vw,48px);border-radius:20px}h1{font-size:28px}h2{font-size:19px;margin-top:28px}p{line-height:1.9;overflow-wrap:anywhere}a{color:#356e54}@media print{section{break-after:page}}</style><main>'+''.join(html)+'</main></html>'
(OUT/'feasibility-20261015.html').write_text(HTML,encoding='utf-8')
reader=PdfReader(pdf);assert len(reader.pages)==7,len(reader.pages)
poppler=Path(r'E:\codex\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe')
subprocess.run([str(poppler),'-png','-r','85',str(pdf),str(QA/'page')],check=True,capture_output=True)
images=[]
for file in sorted(QA.glob('page-*.png')):
 im=Image.open(file).convert('RGB');im.thumbnail((400,566));images.append(im)
sheet=Image.new('RGB',(400*4,600*2),'#dce5dd');draw=ImageDraw.Draw(sheet)
for ix,im in enumerate(images):sheet.paste(im,((ix%4)*400,(ix//4)*600));draw.text(((ix%4)*400+10,(ix//4)*600+570),str(ix+1),fill='black')
sheet.save(QA/'contact-sheet.jpg',quality=90)
proof={'pdf':str(pdf),'pages':len(reader.pages),'sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'renderedPages':len(images),'contactSheet':str(QA/'contact-sheet.jpg'),'scope':'design decisions; final execution results separately'}
(QA/'verification.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(proof,ensure_ascii=False))
