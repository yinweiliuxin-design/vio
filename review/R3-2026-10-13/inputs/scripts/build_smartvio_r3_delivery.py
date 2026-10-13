"""Read-only snapshot of selected R3 engineering; never emit CAM or a release."""
from pathlib import Path
import os, json, hashlib, shutil, stat

BASE=Path(__file__).resolve().parent
SRC=BASE/'SmartVio-工程整改-20261012-R3'
DEST=BASE/'SmartVio-R3-最新方案与工程资料-20261013'
ENG=DEST/'engineering'
def read(p): return json.loads(p.read_text('utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')
copied=[]; omitted=[]
def add(rel):
    p=SRC/rel
    assert p.is_file(),p
    dst=ENG/rel; dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(p,dst)
    assert sha(dst)==sha(p)
    copied.append({'source':p.relative_to(SRC).as_posix(),'snapshot':'engineering/'+p.relative_to(SRC).as_posix(),'sha256':sha(p)})
def tree(rel):
    skip={'__pycache__','node_modules','build','eb','tmp','ccache','.git','tools'}
    for root,dirs,files in os.walk(SRC/rel,followlinks=False):
        dirs[:]=[d for d in dirs if d not in skip and not (Path(root)/d).is_junction() and not (Path(root)/d).is_symlink()]
        for name in files:
            p=Path(root)/name
            if p.is_symlink() or p.suffix.lower() in {'.pyc','.lck','.kicad_prl'} or name=='sdkconfig.old': continue
            add(p.relative_to(SRC))

state=read(SRC/'pre-sample/current-design-status.json')
sel=read(SRC/'project/selected-boards.json')
audit=read(SRC/'verification/independent/revision-audit.json')
flex=read(SRC/'verification/flex-bus-audit.json')
mech=read(SRC/'mechanical/assembly-status.json')
assert audit['pass'] and not audit['errors']
assert all(b['unconnected']==b['violations']==0 for b in state['boards'])
assert flex['functionalConnections']==21 and flex['remainingBoardInterconnections']==16
assert len(mech['file_manifest'])==20 and not mech['intersections']
assert not sel['productionApproved'] and not sel['freezePermitted']
assert sha(SRC/'project/electrical/native-components.json')==sel['sourceSHA256']
assert sha(SRC/'project/selected-boards.json')==audit['selectionSHA256']
for name,digest in audit['schematicSHA256'].items(): assert sha(SRC/'project/eda'/name)==digest
for b in state['boards']: assert sha(SRC/b['file'])==b['sha256']==sel['boardSHA256'][b['role']]
for b in flex['boards']: assert sha(SRC/'project'/b['file'])==b['sha256'] and b['drcViolations']==b['unconnected']==0
for b in mech['file_manifest']+mech['reference_components']: assert sha(SRC/'mechanical'/b['file'])==b['sha256']

for rel in ['project/eda','project/electrical','project/footprints','verification/current','verification/independent',
            'firmware/base','firmware/stm32','firmware/esp32','firmware/tests','firmware/artifacts','firmware/handoff','firmware/reproduce','reproduce']:
    tree(rel)
for rel in ['project/selected-boards.json','project/pcb/fp-lib-table','r3-work-state.json',
    'pre-sample/current-design-status.json','pre-sample/work-and-test-plan.json','pre-sample/candidate-bom-and-placement.json','pre-sample/candidate-bom-check.json',
    'verification/flex-bus-audit.json','verification/r3-eco-preservation-audit.json','verification/prototype-assembly-gate.json',
    'verification/electrical-candidate-sync.json','verification/electrical-freeze.json','verification/frozen-board-components.json',
    'verification/official-checks.json','verification/rf-selection.json','verification/revision-decisions.json',
    'firmware/build.py','firmware/build-esp.ps1','firmware/README_R2_先读我.txt','firmware/source-copy-manifest.json','firmware/status.json','firmware/artifacts-SHA256.json',
    'mechanical/parameters.json','mechanical/assembly-status.json','mechanical/pcb-interface-eco.json','mechanical/requirements.txt','mechanical/制造与装配说明.txt']:
    add(rel)
for rel in sel['boards'].values():
    for ext in ['.kicad_pcb','.kicad_pro','.kicad_dru']: add('project/'+Path(rel).with_suffix(ext).as_posix())
for b in flex['boards']:
    for ext in ['.kicad_pcb','.kicad_pro','.kicad_dru','.independent-drc.json']: add('project/'+Path(b['file']).with_suffix(ext).as_posix())
for b in mech['file_manifest']+mech['reference_components']: add('mechanical/'+b['file'])
for name in ['build_mechanics.py','engineering_drawings.py','extract_board_geometry.py','rf_reference.py','flex_reference.py',
    'mechanical_parts_assembly.step','reference_components_NOT_MANUFACTURING.step','stock/button_blank_TRIM_TIP_TO_MEASURED_SWITCH.step']:
    add('mechanical/cad/'+name)
for name in ['current-native-geometry.json','native-board-body-ledger.json','component-occupancy-ledger.json','flex-installed-and-unfolded.json',
    'instrument-fit-basis.json','rf-installed-route.json','provenance.json','legacy-occupancy-sources.json',
    'main-native.step','usb-native.step','audio-native.step','cover-native.step','sensor-native.step']:
    add('mechanical/reference/'+name)
for name in ['STX-353K7A-6N-KTTR_rA1.STEP','Kycon-STX-353K7A-catalog.pdf','EBYTE-TX2400-FPC3-2509.pdf','Espressif-ESP32-MINI-1-U.pdf','I-PEX-MHF-III-catalog.pdf']:
    add('verification/references/'+name)

# Provide the actual small STM32 vendor source trees used by the build, with their license files.
vendor=Path('E:/codex/Codex/2026-10-01/99/work/v26/firmware/vendor')
vendorfiles=[]
for folder in ['cmsis','cmsis-dsp-1.16.2','st','stm32h7xx-hal-driver-1.11.4']:
    for root,dirs,files in os.walk(vendor/folder,followlinks=False):
        dirs[:]=[d for d in dirs if d not in {'.git','__pycache__'} and not (Path(root)/d).is_junction()]
        for name in files:
            p=Path(root)/name; dest=ENG/'firmware/vendor-source'/p.relative_to(vendor)
            dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,dest)
            vendorfiles.append({'file':dest.relative_to(DEST).as_posix(),'source':str(p),'sha256':sha(p)})

# Verify recorded firmware sources and output bytes without changing the historical build report.
build=read(SRC/'firmware/artifacts/build-result.json')
assert len(build['hostTests'])==16 and all(t['status'].startswith('HOST_PASS') for t in build['hostTests'])
inputs=[]
for row in build['inputs']+build['artifacts']:
    p=Path(row['path']); assert p.is_file() and sha(p)==row['sha256'],p
    if p.is_relative_to(SRC): target=ENG/p.relative_to(SRC)
    elif p.is_relative_to(vendor): target=ENG/'firmware/vendor-source'/p.relative_to(vendor)
    else: target=None
    if target is not None: assert target.is_file() and sha(target)==row['sha256'],target
    inputs.append({'originalPath':str(p),'sha256':row['sha256'],'verified':True,'snapshot':target.relative_to(DEST).as_posix() if target else None})
fwstatus=read(SRC/'firmware/status.json')
for row in fwstatus['esp_copied_artifacts']:
    p=SRC/'firmware'/row['path']; assert p.exists() and sha(p)==row['sha256']
write(ENG/'verification/delivery-input-validation.json',{'allCurrentHashesMatch':True,'nativeElectrical':True,'hostTests':16,'physicalTests':0,'firmwareInputs':inputs,'vendorFiles':vendorfiles})

# Retain bytes of source documents, while publishing explicit current reading guidance.
(ENG/'mechanical/当前R3阅读说明.txt').write_text('''当前R3结构由 assembly-status.json 与 reference/current-native-geometry.json 绑定。
制造与装配说明.txt及parameters.json保留了R2名称，是继承的几何/加工基线，不是本轮投产签字。
基线说明第4节的“三组FPC/15条/其余22条”已由当前证据更新为四组FPC/21条/其余16条。
当前主板为 SmartVio-main-r3-linked.kicad_pcb，SHA以project/selected-boards.json为准。
四个孔已按用户要求预留，工厂配实际琴体。整琴木作CAD、真实拾音器尺寸和完整线束均未形成加工冻结版。
CAD有效与模型范围无碰撞不代表实物或极限公差合格。当前工程图请打开交付根目录drawings与visuals。
''','utf8')
(ENG/'reproduce/先读我_脚本适用范围.txt').write_text('''此目录保留本项目的复现、检查及历次迁移脚本源码。
当前读取入口是上两级index.html，选中板只以project/selected-boards.json为准。
verify_revision.py用于原生一致性复查；export_frozen_design.py默认仅生成审阅导出，--cam须单独有效放行证据。
带prepare/route/merge/cover_eco/build_presample_pack/finalize_r2等名称的脚本包含历史迁移、候选生成或固定路径，不应批量执行。
旧build_presample_pack.py会断言15项未连接并指向20261012旧包，本次交付未运行它；本次打包脚本保存在根目录delivery-tools。
部分脚本依赖历史候选输入，已排除的中间PCB/失败布线保留在原R3工作目录；本包足以查看当前原生设计，不是完整运行时或所有历史候选的镜像。
修改任何原理图、PCB、FPC、CAD或固件后，都要重新检查并更新SHA，不得沿用旧PASS。
''','utf8')
plan=read(SRC/'pre-sample/work-and-test-plan.json')
for row in plan['work']:
    if row.get('id')=='P02': row['evidence']='verification/independent/erc.json'
write(ENG/'pre-sample/work-and-test-plan.json',plan)
write(DEST/'review/source-copy-ledger.json',{'date':'2026-10-13','sourceRoot':str(SRC),'copiedFiles':copied,
    'normalizations':[{'file':'engineering/pre-sample/work-and-test-plan.json','change':'P02 evidence corrected to current verification/independent/erc.json; no test value changed'}],
    'excluded':'Old R2 summary PDFs/XLSX/index, unsuccessful intermediate boards/routing dumps, runtime caches, junction targets, local personal state. Originals retained.'})
write(DEST/'review/current-snapshot.json',{'snapshotDate':'2026-10-13','engineeringEvidenceDate':'2026-10-12','engineeringRevision':'R3',
    'mainUnconnected':0,'nativeBoardsClean':5,'nativeFlexBoardsClean':4,'flexFunctionalConnections':21,'ordinaryConnectionsUnclosed':16,
    'mechanicalParts':20,'hostTestEntriesPassed':16,'physicalTests':0,'normalCharging':'HOLD','manufacturingReleased':False,
    'finalGerberIncluded':False,'sourceSHA256':sel['sourceSHA256'],'selectedBoardSHA256':sel['boardSHA256']})
print(json.dumps({'copiedR3Files':len(set(x['snapshot'] for x in copied)),'vendorSourceFiles':len(vendorfiles),'destination':str(DEST),'checks':'PASS','manufacturingReleased':False},ensure_ascii=False))
