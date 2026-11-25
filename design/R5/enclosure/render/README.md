# R5 外壳 V0.2 装琴效果图（渲染流程）

效果图按外壳 V0.2 的 3D 模型（与图纸 M-R5-00…06 同一套参数）渲染，再合成到白色电子小提琴的实拍照片上。

| 文件 | 作用 |
|---|---|
| `export_meshes.py` | 用 `build_enclosure.py` 生成面盖（分出刻字凹面）、旋钮、按键帽、导光柱、螺钉和一段琴身中央梁，导出三角网格 `meshes.json` |
| `render.html` | three.js 场景：`view=top` 正视俯视（琴头朝上，G 弦侧在右，透明背景，带旋钮阴影）；`view=hero` 装在中央梁上的透视图 |
| `shoot.js` | 用无头 Chromium 打开 `render.html` 并保存 PNG |
| `compose_showcase.py` | 去掉照片上的原控制板，按 3.18 px/mm 把模块放在中央梁中线上（原琴孔中心高度），排版成展示图 |

运行（需要 CadQuery、node、playwright、three@0.170.0，`render.html` 和 `node_modules`、`meshes.json` 放在同一目录，用本地 HTTP 服务打开）：

```
python3 export_meshes.py <dir>/meshes.json
python3 -m http.server 8765 --bind 127.0.0.1      # 在 <dir> 里运行
node shoot.js http://127.0.0.1:8765 "view=top&pxmm=24&lit=1" top24.png
node shoot.js http://127.0.0.1:8765 "view=hero&w=2400&h=1500&az=-100&el=36&dist=400&fov=19&tx=4&exp=1.18" hero.png
node shoot.js http://127.0.0.1:8765 "view=hero&w=2400&h=1200&az=-62&el=9&dist=300&fov=17&tx=-6&tz=1&exp=1.15" hero2.png
python3 compose_showcase.py <小提琴背面照片.jpg> top24.png hero.png hero2.png <输出目录>
```

输出：`../preview/07_on_violin_showcase.jpg`（展示图 2560 × 1600）、`../preview/08_on_violin_full.jpg`（整琴合成 2000 × 2000）。

示意说明：插座、USB-C、编码器套筒按 M-R5-06 的建议尺寸画；刻字按图纸“不填色”画成略浅的凹面；只点亮了电源灯，颜色未定。
