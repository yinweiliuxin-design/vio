"""SmartVio R4.1 worst-case + RSS tolerance stacks (review M13). Prints JSON; tolerance-stack.md quotes it.
Each contributor: (name, nominal contribution with sign, +tol, -tol, source). Symmetric bilateral unless noted.
RSS uses each contributor's half-range (shifted to its mean) - i.e. treats tolerances as +/-3 sigma."""
import json, math
def chain(name, contrib, limit_lo=None, limit_hi=None, unit="mm"):
    nom = sum(c[1] for c in contrib)
    mean = sum(c[1] + (c[2] - c[3]) / 2 for c in contrib)          # c[2]=+tol, c[3]=|-tol|
    half = [(c[2] + c[3]) / 2 for c in contrib]
    wc_lo, wc_hi = mean - sum(half), mean + sum(half)
    r = math.sqrt(sum(h * h for h in half)); rs_lo, rs_hi = mean - r, mean + r
    ok = lambda lo, hi: (limit_lo is None or lo >= limit_lo - 1e-9) and (limit_hi is None or hi <= limit_hi + 1e-9)
    return dict(chain=name, nominal=round(nom, 4), mean=round(mean, 4), wc=[round(wc_lo, 4), round(wc_hi, 4)], rss=[round(rs_lo, 4), round(rs_hi, 4)],
                limit=[limit_lo, limit_hi], wc_pass=ok(wc_lo, wc_hi), rss_pass=ok(rs_lo, rs_hi),
                contributors=[dict(name=c[0], nominal=c[1], plus=c[2], minus=c[3], source=c[4]) for c in contrib])
KY = 0.15   # Kycon title-block tolerance: NOT in the package (catalog page has none) -> assumption
GCT = 0.25  # GCT USB4120 title-block tolerance as used by R3 occupancy basis (6.50 + 0.25)
R = []
# 1 total height (jack mouth is the highest non-wheel point; cup hangs on the window bottom)
R.append(chain("1 总高（插口顶→杯底）≤25", [
 ("Kycon 肩面→插口 2.40", 2.40, KY, KY, "Kycon 目录图 2.40；公差假设 ±0.15（未取得图框公差）"),
 ("上盖 压台面 Z1.455（至基准 A）", 1.455, .03, .03, "U6"),
 ("上盖 卡扣窗下沿 −Z2.32", 2.32, .03, .03, "U10"),
 ("下杯 钩下面→外底 18.50（R4.1b：底 0.55 + 底绝缘 0.05）", 18.50, .05, .05, "L2"),
], None, 25.0))
# 1b with Kycon tolerance that just closes WC
# 2 non-wheel protrusion
R.append(chain("2 非滚轮外突（插口顶，至琴面）≤5", [
 ("压台面 Z1.455", 1.455, .03, .03, "U6"), ("Kycon 肩面→插口 2.40", 2.40, KY, KY, "假设 ±0.15"),
 ("PCB+PET 叠厚顶起上盖（键1–2区）", 0.0, .05, 0.0, "0.4±0.04 + 0.1±0.01 − 0.50 承托面"),
], None, 5.0))
R.append(chain("2b 按键顶外突", [("沉槽顶 Z3.10（=3.80−0.70）", 3.10, .03, .03, "U2/U3"), ("键 法兰顶→键顶 0.75", .75, .02, .02, "K4"),
 ("PCB+PET 顶起", 0, .05, 0, "同上")], None, 5.0))
# 3 cup vs cavity, per side
R.append(chain("3X 下杯↔原腔 X 单边间隙 ≥0", [
 ("原腔长 78 半差", 0.5, .10, .10, "腔 78±0.2（假设，须实测）; 杯 77 名义"),
 ("下杯长 77 半公差", 0, .025, .025, "L1 ±0.05"),
 ("下杯在上盖内 X 浮动", 0, .20, .20, "音频框端面↔杯内壁 0.2（CAD）"),
 ("上盖相对原腔定位（配钻导孔）", 0, .15, .15, "配钻样板 ±0.15（假设）"),
], 0.0, None))
R.append(chain("3Y 下杯↔原腔 Y 单边间隙 ≥0", [
 ("原腔宽 47 半差", 1.0, .10, .10, "47±0.2（假设）"), ("下杯宽 45 半公差", 0, .025, .025, "L1"),
 ("下杯 Y 浮动（R4.1 定位筋）", 0, .05, .05, "筋→刀片 0.05"), ("上盖相对原腔定位", 0, .15, .15, "假设"),
], 0.0, None))
R.append(chain("3Z 杯底↔原腔底 间隙 ≥0", [
 ("原腔深 22", 22.0, .2, .2, "假设，须实测"), ("−窗下沿 Z2.32", -2.32, .03, .03, "U10"), ("−钩→外底 18.50", -18.50, .05, .05, "L2"),
 ("琴面平面度（螺钉区）", 0, 0, .05, "假设"),
], 0.0, None))
# 4 key travel chain keys 3-5
R.append(chain("4a 按键空行程（键3–5，不修整）0…0.10", [
 ("上盖 沉槽顶→承托面 2.60", 2.60, .03, .03, "U3"), ("−按键 法兰顶→触头 0.90", -0.90, .03, .03, "K3"),
 ("−开关高 1.50 +0.15/−0", -1.50, 0.0, .15, "SKQGABE010（native-components.json）"),
 ("背撑架平面度/PCB 局部厚差", 0, .03, .03, "B1 0.03 + PCB 局部 ±0.01"),
], 0.0, 0.10))
R.append(chain("4b 按键空行程（键3–5，按实测修整，目标 0.05）", [
 ("目标间隙", 0.05, 0, 0, "L = Dm − Rc − 0.05"), ("Dm 深度千分尺", 0, .01, .01, "实测"), ("Rc 测量", 0, .01, .01, "实测"),
 ("修整精度", 0, .02, .02, "K3 修整后"), ("背撑架/PCB（干装已含，剩余）", 0, .01, .01, "重装复位"),
], 0.0, 0.10))
R.append(chain("4c 按键空行程（键1–2，按实测修整，平台代替琴面）", [
 ("目标间隙", 0.05, 0, 0, ""), ("测量+修整", 0, .04, .04, "同 4b"), ("琴面平面度（键1–2区）", 0, .03, .03, "要求 ≤0.03（须实测）"),
 ("PET 背垫换片厚差", 0, .01, .01, "I1"),
], 0.0, 0.10))
# 5 snap engagement (far side, cup pushed fully the other way)
R.append(chain("5a 卡扣搭接（R4 原设计，无定位筋）≥0.10", [
 ("刀片外侧面间距 43.00", 43.00, .05, .05, "U11"), ("−杯内宽 43.40", -43.40, .05, .05, "L4"), ("钩凸出 0.45（R4）", 0.45, .03, .03, "原 CAD"),
], 0.10, None))
R.append(chain("5b 卡扣搭接（R4.1：筋 0.15 + 钩 0.55）≥0.10", [
 ("刀片外侧面间距 43.00", 43.00, .05, .05, "U11"), ("+定位筋高 0.15", 0.15, .02, .02, "L5"), ("−杯内宽 43.40", -43.40, .05, .05, "L4"),
 ("钩凸出 0.55", 0.55, .03, .03, "L3"),
], 0.10, None))
R.append(chain("5c 卡扣入位最大挠曲（近侧搭接 = 钩凸出 − 筋高）≤ 刀片导入 0.55", [
 ("钩凸出 0.55", 0.55, .03, .03, "L3"), ("−定位筋高 0.15（近侧筋贴刀片）", -0.15, .02, .02, "L5"),
], None, 0.55))
# 6 jack shoulder vs roof pad loop
R.append(chain("6 插座肩面↔屋顶压台 间隙（0…0.05）", [
 ("上盖 压台面→唇顶 12.605", 12.605, .05, .05, "U7"), ("−Kycon 肩面→座面 11.10", -11.10, KY, KY, "假设 ±0.15"),
 ("−音频板厚 1.00 ±10%", -1.00, .10, .10, "PCB ±10%"), ("−音频框底网 0.50", -0.50, .02, .02, "F1"), ("插座焊接座落（浮高）", 0, 0, .03, "THT 座面"),
], 0.0, 0.05))
R.append(chain("6b 插座环链（选配后：腹板 0.40/0.50/0.60 + 0.05 PET）", [
 ("残余间隙（选配目标）", 0.025, .025, .025, "选配后 0…0.05"), ("测量误差", 0, .01, .01, "高度规"),
], -0.02, 0.06))
# 7 USB-C
R.append(chain("7a USB-C 本体↔开口 单边间隙（居中）≥0", [
 ("开口 9.39 半值", 4.695, .025, 0, "U8 +0.05/0"), ("−本体 8.94 半值", -4.47, .125, .125, "GCT 图框 ±0.25（R3 依据）"),
], 0.0, None))
R.append(chain("7b USB-C 位置失配 ≤ 浮动+最小间隙 0.20", [
 ("J401 相对 USB 板孔", 0, .10, .10, "贴装+定位脚 ±0.10"), ("USB 板孔位", 0, .05, .05, "PCB 钻孔"), ("屋顶底孔位", 0, .03, .03, "U16"), ("开口位置", 0, .03, .03, "U8"),
], None, 0.20))
R.append(chain("7c 插头包胶↔面槽 单边间隙 ≥0（R4.1 面槽 13.0）", [
 ("面槽 13.0 半值", 6.5, .05, 0, "U8 +0.1/0"), ("−包胶 12.35 半值", -6.175, 0, 0, "USB-C 规范参考最大（需核对原文）"),
 ("插座在开口内偏位", 0, .10, .10, "7a 间隙"), ("包胶对壳体偏心", 0, .05, .05, "线缆厂，假设"),
], 0.0, None))
R.append(chain("7d 插座面低于屋顶顶面 ≤ 面槽深 0.95（R4.1b）", [
 ("屋顶顶面 3.80 − 压柱端面 −3.30", 7.10, .04, .04, "U2/U9"), ("−GCT 高 6.50", -6.50, GCT, GCT, "GCT 图框 ±0.25"),
], None, 0.95))
# 8 main board latch (extra)
R.append(chain("8 主板卡齿间隙（附加）0…0.05", [
 ("卡齿下面→托台面 0.80", 0.80, .03, .03, "L10"), ("−主板厚 0.80 ±10%", -0.80, .08, .08, "PCB"),
], 0.0, 0.05))
for c in R:
    print(json.dumps(c, ensure_ascii=False))
open(__file__.replace("tolerance_stack.py", "tolerance_stack_result.json"), "w").write(json.dumps(R, ensure_ascii=False, indent=1))
