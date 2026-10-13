import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';
process.on('uncaughtException', e=>{console.error(e.stack);process.exit(1);});
process.on('unhandledRejection', e=>{console.error(e?.stack||e);process.exit(1);});

const root = 'C:/Users/Admin/Documents/亚马逊图片/SmartVio-R3-最新方案与工程资料-20261013/engineering';
const out = 'C:/Users/Admin/Documents/亚马逊图片/SmartVio-R3-最新方案与工程资料-20261013/reports';
const qaDir = 'C:/Users/Admin/Documents/亚马逊图片/.r3-workbook-build-20261013';
const file = `${out}/SmartVio-R3-首样工作测试与候选BOM.xlsx`;
const srcNames = ['pre-sample/current-design-status.json','pre-sample/work-and-test-plan.json','pre-sample/candidate-bom-and-placement.json','firmware/handoff/R2_逐线接线表.json','firmware/handoff/R2_首样线束受控规格.json'];
const srcs = [];
for (const name of srcNames) { const raw = await fs.readFile(`${root}/${name}`); srcs.push({name, sha256:crypto.createHash('sha256').update(raw).digest('hex'), data:JSON.parse(raw.toString('utf8').replace(/^\uFEFF/,''))}); }
const [st, plan, bom, wires, spec] = srcs.map(s=>s.data);
const ordinary = wires.filter(r=>r.proposed_implementation === 'ORDINARY_WIRE_ROUTE_NOT_CLOSED');
const flex = wires.filter(r=>r.proposed_implementation === 'CUSTOM_STATIC_FPC_CANDIDATE');
if ([ordinary.length,flex.length,plan.work.length,plan.tests.length,plan.metrics.length,plan.instrumentTests.length,bom.length].join() !== '16,21,25,23,70,12,333') throw new Error('Source count mismatch');
if (plan.metrics.some(r=>r.measured !== null)) throw new Error('Unexpected recorded measurement');
if (st.boards.some(r=>r.unconnected !== 0 || r.violations !== 0 || r.ignoredChecks.length)) throw new Error('Native board evidence drift');
const wb = Workbook.create();
const names=['当前版本','待闭合互连','前置工作','测试阶段','测量记录','小提琴测试','候选BOM','供应商回签'];
const sheets = Object.fromEntries(names.map(n=>[n,wb.worksheets.add(n)]));
const C={ink:'#253448',head:'#344860',line:'#C9D2DD',input:'#FFF3CC',pale:'#EEF2F7',error:'#FBE5E2',white:'#FFFFFF'};
const col = n => {let s=''; for(n++;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s; return s;};
const ranges=[];
function base(name,title,note,headers,rows,widths,inputCols=[],height=48) {
 const sh=sheets[name], last=col(headers.length-1), end=6+rows.length;
 const normalize=v=>typeof v==='string'?v.replace(/(?<!engineering\/)\b(pre-sample|firmware|project|verification|mechanical)\//g,'engineering/$1/'):v;
 rows=rows.map(r=>r.map(normalize)); note=normalize(note);
 sh.showGridLines=false;
 sh.getRange(`A1:${last}${end}`).format={font:{name:'Arial',size:10,color:C.ink},verticalAlignment:'center'};
 sh.getRange('A2').values=[[title]]; sh.getRange('A2').format.font={name:'Arial',size:15,bold:true,color:C.ink};
 sh.getRange(`A3:${last}3`).format.borders={bottom:{style:'thin',color:C.line}};
 sh.getRange('A4').values=[[note]]; sh.getRange('A4').format.font={name:'Arial',size:10,italic:true,color:'#66758A'};
 sh.getRange(`A6:${last}${end}`).values=[headers,...rows];
 sh.getRange(`A6:${last}6`).format={fill:C.head,font:{name:'Arial',size:10,bold:true,color:C.white},horizontalAlignment:'center',verticalAlignment:'center',wrapText:true,rowHeight:30};
 sh.getRange(`A7:${last}${end}`).format.wrapText=true;
 sh.getRange(`A7:${last}${end}`).format.rowHeight=32;
 widths.forEach((v,i)=>{sh.getRange(`${col(i)}1:${col(i)}${end}`).format.columnWidth=v;});
 inputCols.forEach(i=>sh.getRange(`${col(i)}7:${col(i)}${end}`).format.fill=C.input);
 sh.freezePanes.freezeRows(6); sh.freezePanes.freezeColumns(name==='候选BOM'?2:1);
 const t=sh.tables.add(`A6:${last}${end}`,true,`R3Table${names.indexOf(name)+1}`); t.showFilterButton=true; t.showBandedColumns=false; t.style='TableStyleLight1';
 rows.forEach((row,i)=>{const lines=row.map((v,j)=>v===null||v===undefined||v instanceof Date?1:String(v).split('\n').reduce((sum,line)=>sum+Math.max(1,Math.ceil([...line].reduce((w,c)=>w+(c.charCodeAt(0)>255?1.9:1),0)/Math.max(8,widths[j]*0.93))),0));sh.getRange(`A${i+7}:${last}${i+7}`).format.rowHeight=Math.max(28,Math.max(...lines)*13+10);});
 ranges.push({name,headerRow:6,startRow:7,endRow:end,rows:rows.length,cols:headers.length,headers,inputCols});
 return sh;
}
function statuses(sh,range,values) {
 sh.getRange(range).dataValidation={rule:{type:'list',values}};
 for (const text of ['不通过','HOLD','待完成','未测试','未测','待复核','待回签']) sh.getRange(range).conditionalFormats.add('containsText',{text,format:{fill: text==='不通过'?C.error:C.input,font:{color:text==='不通过'?'#9D2922':C.ink}}});
}
const currentRows=[
 ['资料编制日',new Date('2026-10-13T00:00:00Z'),'当前 R3 工程资料汇编','本工作簿'],
 ['源状态日期',new Date(`${st.date}T00:00:00Z`),'软件/原生 CAD 核查日期，不代表实物合格','current-design-status.json'],
 ['制造放行','HOLD','16 条普通互连、拾音方案、供应商 DFM 及实物测试待闭合',st.releaseNote],
 ['原生 ERC 违规',st.ercViolations,'无忽略项','verification/independent/erc.json'],
 ['主板未连接项',st.boards.find(r=>r.role==='main').unconnected,'原生 PCB 核查','verification/independent/revision-audit.json'],
 ['主板 DRC 违规',st.boards.find(r=>r.role==='main').violations,'未放宽规则或忽略检查','verification/current/main-drc.json'],
 ['原生 PCB 数',st.boards.length,'主板、USB、音频、面板、传感器共 5 块','project/selected-boards.json'],
 ['原生 FPC 数',st.flexNativeAudit.boards.length,'四组 FPC 均 0 未连接、0 DRC；加工与弯折未实测','verification/flex-bus-audit.json'],
 ['FPC 功能互连数',flex.length,'在 37 条板间互连中已完成候选 FPC 设计','firmware/handoff/R2_逐线接线表.json'],
 ['普通互连待闭合',ordinary.length,'路径、半径、长度、成端与实物装配未闭合','见待闭合互连表'],
 ['STEP 制造件',st.mechanicalParts,'当前模型 20 个有效实体','mechanical/assembly-status.json'],
 ['已建模范围干涉',st.mechanicalIntersectionsCurrentScope,'不包含完整 16 条普通互连与全部供应商公差','mechanical/assembly-status.json'],
 ['主机回归条目',st.firmwareHostGroupsPassed,'目标编译与主机测试通过，未运行真实硬件','firmware/artifacts/build-result.json'],
 ['实物测试次数',st.physicalTestsPerformed,'全部 70 行实测栏留空','见测量记录表'],
 ['普通充电',st.normalCharging,'固件保持禁用；专项保护和电池测试待完成','firmware/status.json'],
 ['最终 Gerber 生成许可',st.finalGerberPermitted?'已允许':'未允许','整机设计与加工条件未冻结','verification/prototype-assembly-gate.json'],
 ['采购 BOM 放行','未放行','333 条为候选位号与放置记录，含 DNP / 铜焊盘 / 外接元件','见候选BOM表'],
 ['拾音结构','J101 两线单通道','四弦独立输入需求保留；硬件与对应固件尚未实现','pre-sample/current-design-status.json'],
 ['测量已填写',null,'仅统计数值记录，不代表测量或整机通过','见测量记录表'],
 ['测量待记录',null,'空白与零值分别处理','见测量记录表'],
 ['供应商已填回签结果',null,'结果、签字和证据均需填写；本表不自动放行制造','见供应商回签表'],
 ['电子源 SHA256',st.sourceSHA256,'319 原理图元件与当前板卡绑定','project/electrical/native-components.json'],
 ...st.boards.map(r=>[r.name,r.sha256,`${r.layers} 层 / ${r.thicknessMm} mm / ${r.footprints} 封装；DRC ${r.violations}，未连接 ${r.unconnected}`,r.file]),
 ...st.flexNativeAudit.boards.map(r=>[r.id,r.sha256,`${r.functionalConnections} 条功能连接 / ${r.copperLayers} 层；候选叠层 ${r.nominalStackMm} mm`,r.file]),
 ...srcs.map(s=>[`源文件：${s.name}`,s.sha256,'工作簿仅汇编当前源数据，未替换原始 JSON',s.name])
];
const cur=base('当前版本','SmartVio R3 首样工作与测试记录','黄色单元格供现场填写。源核查通过与实物合格分别记录。',['项目','数值或状态','范围说明','证据或出处'],currentRows,[34,52,70,68],[],44);
cur.tabColor='#253448'; cur.freezePanes.unfreeze(); cur.getRange('B7:B8').setNumberFormat('yyyy-mm-dd');
cur.getRange('B25').formulas=[["=COUNT('测量记录'!H7:H76)"]];
cur.getRange('B26').formulas=[["=COUNTBLANK('测量记录'!H7:H76)"]];
cur.getRange('B27').formulas=[["=COUNTA('供应商回签'!G7:G16)"]];

const wireTypes=Object.fromEntries(spec.wire_types.map(x=>[x.id,x]));
const wrows=ordinary.map(r=>[r.id,r.net,`${r.from_board} / ${r.from_ref}.${r.from_pad}`,`${r.to_board} / ${r.to_ref}.${r.to_pad}`,r.wire_spec,wireTypes[r.wire_spec].OD_max_mm,wireTypes[r.wire_spec].static_bend_radius_min_mm,r.CAD_route_centerline_mm,r.first_article_finished_mm,null,'待完成',null,null,r.assembly_note]);
const wsh=base('待闭合互连','16 条普通板间互连待闭合','源：firmware/handoff/R2_逐线接线表.json。USB D+/D− 使用同一有规格书的屏蔽双绞对。',['ID','网络','起点及焊盘','终点及焊盘','线材规范','最大外径 mm','最小静态弯曲 R mm','CAD 路径 mm','实物成端长度 mm','供方型号及批次','现场状态','证据文件','签字 / 日期','成端要求'],wrows,[10,28,30,30,14,15,19,18,20,24,15,26,24,66],[7,8,9,10,11,12],66);
statuses(wsh,'K7:K22',['待完成','进行中','待复核','不通过','现场核验完成']);
const workRows=plan.work.map(r=>[r.id,r.phase,r.item,r.acceptance,r.owner,r.status,r.id==='P02'?'verification/independent/erc.json':r.evidence,r.date?new Date(`${r.date}T00:00:00Z`):null,r.actual_result||null,r.note||null,null,null]);
const work=base('前置工作','25 项首样前置工作','源：pre-sample/work-and-test-plan.json。源状态保留，现场结论单列；原生检查通过不代表已制造。',['ID','阶段','工作项目','验收要求','责任角色','源状态','现有证据 / 应交证据','源核查日期','现场实际结果','整改记录','现场签字','现场日期'],workRows,[10,20,30,82,26,16,68,16,40,42,22,16],[8,9,10,11],78);
work.getRange('H7:H31').setNumberFormat('yyyy-mm-dd'); work.getRange('L7:L31').setNumberFormat('yyyy-mm-dd');

const testRows=plan.tests.map(r=>[r.id,r.stage??r.phase,r.titleZh,(r.depends||[]).join(', '),r.currentLimitMa??null,r.methodZh,r.stop||'依批准阶段与夹具；触发异常即停机。',r.checks?r.checks.join('\n'):r.acceptance,r.physicalStatus,null,null,null]);
const tsh=base('测试阶段','23 个首板测试阶段','源：engineering/pre-sample/work-and-test-plan.json。顺序与停机条件以逐阶段计划为准，普通充电保持 HOLD。',['阶段 ID','顺序 / 阶段','测试项目','前置阶段','阶段限流 mA','执行方法','立即停止条件','检查项','当前实物状态','现场结论','测试人','日期 / 原始证据'],testRows,[15,22,34,22,18,84,90,66,18,30,22,40],[9,10,11],110);
statuses(tsh,'J7:J29',['未测试','测试中','待复核','不通过','现场阶段通过']);
const eqStart=34; tsh.getRange(`A${eqStart}:C${eqStart+plan.equipment.length}`).values=[['设备类别','设备及要求','使用条件'],...plan.equipment];
tsh.getRange(`A${eqStart}:C${eqStart}`).format={fill:C.head,font:{name:'Arial',size:10,bold:true,color:C.white}};
tsh.getRange(`A${eqStart+1}:C${eqStart+plan.equipment.length}`).format={font:{name:'Arial',size:10,color:C.ink},wrapText:true,rowHeight:140};

const metricRows=plan.metrics.map(r=>[r.testId,r.metricId,r.name,r.unit,r.min,r.max,r.basis,null,null,null,null,null,null,null]);
const msh=base('测量记录','70 行首板实测记录','源：engineering/pre-sample/work-and-test-plan.json。阈值为候选工程范围；填写实测值和证据后由工程师复核。',['阶段 ID','测量 ID','指标','单位','候选下限','候选上限','阈值依据','实测值','范围提示','原始证据文件','仪器 / 校准','测试人','测试日期','复核结论'],metricRows,[16,42,32,12,15,15,62,18,20,36,32,22,18,32],[7,9,10,11,12,13],62);
for(let i=7;i<=76;i++) msh.getRange(`I${i}`).formulas=[[`=IF(ISBLANK(H${i}),"未测",IF(ISNUMBER(H${i}),IF(OR(AND(ISNUMBER(E${i}),H${i}<E${i}),AND(ISNUMBER(F${i}),H${i}>F${i})),"超候选范围","待复核"),"需数值"))`]];
msh.getRange('E7:H76').setNumberFormat('0.000'); msh.getRange('M7:M76').setNumberFormat('yyyy-mm-dd');
statuses(msh,'N7:N76',['待复核','不通过','范围内且证据已复核','需重测']);
msh.getRange('I7:I76').conditionalFormats.add('containsText',{text:'超候选范围',format:{fill:C.error,font:{color:'#9D2922',bold:true}}});

const viRows=plan.instrumentTests.map(r=>[...r,'未测试',null,null,null,null,null]);
const vi=base('小提琴测试','12 项真实小提琴测试','源：engineering/pre-sample/work-and-test-plan.json。保留四弦独立功能目标，未落实的硬件不能用模拟数据代替。',['ID','测试项目','实物执行方法','评价和记录要求','初始状态','现场测量 / 观察','现场结论','证据文件','测试人','测试日期'],viRows,[10,30,92,86,18,54,28,36,22,18],[5,6,7,8,9],110);
statuses(vi,'G7:G18',['未测试','测试中','待复核','不通过','现场测试完成']); vi.getRange('J7:J18').setNumberFormat('yyyy-mm-dd');

const bRows=bom.map(r=>[r.reference,r.board,r.value,r.mpn||null,r.footprint,r.side,r.xMm??null,r.yMm??null,r.rotationDegrees??null,r.dnp,r.excludeFromBOM,r.assemblyMethod,r.release,r.sourceBoardSHA256||null,null,null]);
const bs=base('候选BOM','333 条候选元件与放置记录','源：engineering/pre-sample/candidate-bom-and-placement.json。332 个板载封装及外置 RT1921；采购与贴片未放行。',['位号','板卡','标值 / 名称','候选 MPN','封装','面','X mm','Y mm','旋转 °','DNP','不计 BOM','装配方式','源放行状态','源 PCB SHA256','供方实物 / 批号','供方差异与证据'],bRows,[20,15,40,42,70,9,14,14,14,10,14,24,32,68,38,52],[14,15],42);
bs.getRange('G7:I339').setNumberFormat('0.000');

const gateRows=[
 ['DFM01','PCB 板厂','5 块刚板叠层、材料、厚度及公差；主板 8 层 0.8 mm；0.15 mm 孔 / 0.35 mm 焊盘；阻抗与加工工艺','板厂 DFM、受控叠层图、阻抗复核与变更清单','未回签',null,null,null,null,null],
 ['DFM02','FPC 厂','四组 FPC 0.099 mm 名义 / 来料≤0.11 mm，静态内 R≥1.2 mm；叠层、覆盖膜、通孔与端子实物确认','定制 FPC 可加工回签、样件厚度与弯折验收','未回签',null,null,null,null,null],
 ['DFM03','线束厂','16 条普通互连的实际路线、长度、半径、屏蔽接续与成端包络；四组 FPC 接续','实际型号 / 批次、逐线记录、装配照片和验收证据','未回签',null,null,null,null,null],
 ['DFM04','琴体工厂','实测琴体腔与安装基面；4 个预留洞按实琴安装；装配基准、螺钉和不伤琴固定','原琴尺寸、基准、装配定位与受力确认','未回签',null,null,null,null,null],
 ['DFM05','拾音器供方 / 电气工程师','实际拾音器型号、路数、极性、外形与输出；保留四弦独立要求并修订 AFE/ADC','受控规格书、接口图、原型及逐弦测量','未回签',null,null,null,null,null],
 ['DFM06','结构加工厂','20 个 STEP 零件材料、加工方式、配合与公差；全线束、实际元件及最差公差装配','DFM / 工艺图、尺寸报告、合盖与拆装实测','未回签',null,null,null,null,null],
 ['DFM07','电池组件供方','候选整包型号和三线 NTC、批次、保护与来料尺寸；充电保护保持 HOLD','完整电池包资料、来料记录和独立充电保护验证','未回签',null,null,null,null,null],
 ['DFM08','PCBA 厂 / 固件工程师','物料替代、DNP / 铜焊盘排除、焊接工艺、镜像版本与烧录；关键电气人工评审','确认的生产 BOM / CPL、版本哈希、焊接与烧录记录','未回签',null,null,null,null,null],
 ['DFM09','测试工程师','夹具、限流、测量设备校准、测试顺序、候选阈值审核及全部原始记录','B00 批准、23 阶段记录、70 行数据和 12 项真琴报告','未回签',null,null,null,null,null],
 ['DFM10','项目负责人','前述问题闭合，当前硬件 / 固件 / 壳体 / 供应商文件一致；独立复核','首样生产范围批准文件与最终制造数据签发；本表不自动授权','未回签',null,null,null,null,null]
];
const sup=base('供应商回签','供应商 DFM 与首样范围回签','填写回签结果必须同时填写签字、日期与证据；工作簿不会自动解除 HOLD 或批准生产。',['ID','责任方','需确认的具体内容','必须返回的证据','初始状态','实际供方名称','回签结果','签字人','回签日期','证据文件 / 变更号'],gateRows,[13,30,94,86,18,32,26,26,20,52],[5,6,7,8,9],110);
statuses(sup,'G7:G16',['待回签','补充资料','不接受当前设计','接受当前设计并附证据']); sup.getRange('I7:I16').setNumberFormat('yyyy-mm-dd');

// Evidence-sensitive formula checks: numeric zero remains a measurement; all in-range values require manual review.
const simulations=[];
for(const v of [null,0,0.05,0.11,'text']) { msh.getRange('H7').values=[[v]]; wb.recalculate(); const actual=msh.getRange('I7').values[0][0]; const expected=v===null?'未测':v==='text'?'需数值':v>0.1?'超候选范围':'待复核'; if(actual!==expected)throw new Error(`Formula boundary ${v}: ${actual} != ${expected}`); simulations.push({input:v,result:actual}); }
msh.getRange('H7').values=[[null]];
sup.getRange('G7').values=[['接受当前设计并附证据']]; wb.recalculate();
if(cur.getRange('B9').values[0][0]!=='HOLD')throw new Error('Review input unexpectedly released manufacturing');
sup.getRange('G7').values=[[null]];
wb.recalculate();
if(cur.getRange('B25:B26').values.flat().join()!=='0,70')throw new Error('Empty measurement summary mismatch');
const inspect=await wb.inspect({kind:'table',range:'当前版本!A7:D27',include:'values,formulas',tableMaxRows:21,tableMaxCols:4,maxChars:8000});
await fs.writeFile(`${qaDir}/inspection.ndjson`,inspect.ndjson);
const errorScan=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},summary:'final formula error scan',maxChars:3000});
await fs.writeFile(`${qaDir}/formula-errors.ndjson`,errorScan.ndjson);
await fs.mkdir(out,{recursive:true});
const xlsx=await SpreadsheetFile.exportXlsx(wb); await xlsx.save(file);
const previewSpecs=[['当前版本','A1:D18'],['待闭合互连','A1:G11'],['待闭合互连','H6:N11'],['前置工作','A1:F11'],['前置工作','G6:L11'],['测试阶段','A1:F10'],['测试阶段','G6:L10'],['测量记录','A1:I11'],['测量记录','J6:N11'],['小提琴测试','A1:E10'],['小提琴测试','F6:J10'],['候选BOM','A1:F11'],['候选BOM','G6:P11'],['供应商回签','A1:E10'],['供应商回签','F6:J10']];
const previews=[];
for(let i=0;i<previewSpecs.length;i++){const [name,range]=previewSpecs[i]; const blob=await wb.render({sheetName:name,range,scale:1,format:'png'}); const p=`${qaDir}/preview-${String(i+1).padStart(2,'0')}.png`; await fs.writeFile(p,new Uint8Array(await blob.arrayBuffer())); previews.push({sheet:name,range,file:p});}
const qa={schema:'smartvio.r3.workbook-qa.v1',date:'2026-10-13',workbook:file,counts:{sheets:names.length,ordinaryInterconnections:ordinary.length,flexFunctionalInterconnections:flex.length,prework:plan.work.length,testStages:plan.tests.length,measurementRows:plan.metrics.length,violinTests:plan.instrumentTests.length,candidateBOM:bom.length,supplierGates:gateRows.length},sources:srcs.map(({name,sha256})=>({name:`engineering/${name}`,sha256})),sheets:ranges,checks:{sourceCountsMatch:true,noSourceMeasurements:true,nativeBoardEvidenceClean:true,measurementBoundaryCases:simulations,manufacturingHoldPreservedWithOneSupplierResult:true,unfilledMeasurementCount:70,physicalTestsRecorded:0,allMeasuredCellsBlank:true,artifactRecalculated:true},previews,sha256:crypto.createHash('sha256').update(await fs.readFile(file)).digest('hex'),limitations:['No physical test has been performed.','Numeric in-range data yields review required, never production approval.','Candidate BOM is not procurement release.','Native Excel application was not opened.']};
await fs.writeFile(`${out}/workbook-qa.json`,JSON.stringify(qa,null,2));
console.log(JSON.stringify({file,counts:qa.counts,sha256:qa.sha256,previews:previews.length}));
