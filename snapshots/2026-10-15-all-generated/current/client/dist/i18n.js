/* Mobile studio localisation. UI text only; user content and stored data are never rewritten. */
(function(root){
'use strict';
const supported=['zh','en','ja','de'];
const markets=['us','uk','jp','de','cn','fr'];
let language='zh',market='cn';
const dictionary=new Map(),aliases=new Map(),renderedSources=new Map();
const originalText=new WeakMap(),originalAttributes=new WeakMap();
const ignored='[data-i18n-ignore],[data-no-i18n],[data-user-content],[contenteditable],script,style,code,pre,kbd';
let observer=null,queued=false;
function normalize(value){const key=String(value||'zh').toLowerCase().split(/[-_]/)[0];return supported.includes(key)?key:'zh';}
function normalizeMarket(value){
  if(typeof value!=='string')throw new TypeError('Market must be a country code');
  const key=value.trim().toLowerCase();
  if(!markets.includes(key))throw new RangeError('Unsupported market: '+key);
  return key;
}
function brand(value=language,region=market){const lang=normalize(value),country=normalizeMarket(region);return country==='uk'||lang==='de'?'VELLEN':'Silvio';}
function add(source,zh,en,ja,de){
  const entry={source,zh,en,ja,de};dictionary.set(source,entry);
  for(const value of [zh,en,ja,de])if(value&&!value.includes('{'))aliases.set(value,entry);
}
for(const [zh,en,ja,de] of [
  ['功能可行性与验收报告','Feature feasibility and validation','機能の実現性と検証レポート','Machbarkeit und Validierung'],
  ['阅读报告','Read report','レポートを読む','Bericht lesen'],
  ['下载 PDF 报告','Download PDF report','PDFレポートを保存','PDF-Bericht herunterladen'],
  ['伴奏与弦乐','Backing & strings','伴奏と弦楽','Begleitung und Streicher'],
  ['MIDI 工作台','MIDI studio','MIDIスタジオ','MIDI-Studio'],
  ['接收真实音符，编辑旋律，导出标准 MIDI 文件。','Receive real notes, edit melodies and export standard MIDI files.','実際の音符を受信し、旋律を編集して標準MIDIファイルを書き出します。','Echte Noten empfangen, Melodien bearbeiten und Standard-MIDI-Dateien exportieren.'],
  ['连接蓝牙 MIDI','Connect Bluetooth MIDI','Bluetooth MIDIを接続','Bluetooth MIDI verbinden'],
  ['收录蓝牙 MIDI','Record Bluetooth MIDI','Bluetooth MIDIを記録','Bluetooth MIDI aufnehmen'],
  ['停止 MIDI 收录','Stop MIDI recording','MIDI記録を停止','MIDI-Aufnahme stoppen'],
  ['蓝牙 MIDI 与琴端参数','Bluetooth MIDI & instrument settings','Bluetooth MIDIと楽器設定','Bluetooth MIDI und Instrumentparameter'],
  ['当前浏览器支持蓝牙 MIDI 配对。','This browser supports Bluetooth MIDI pairing.','このブラウザはBluetooth MIDIのペアリングに対応しています。','Dieser Browser unterstützt Bluetooth-MIDI-Kopplung.'],
  ['当前浏览器不支持网页蓝牙，请使用系统 MIDI 或原生适配器。','This browser does not support web Bluetooth. Use system MIDI or a native adapter.','このブラウザはWeb Bluetoothに未対応です。システムMIDIまたはネイティブアダプターを使用してください。','Dieser Browser unterstützt kein Web Bluetooth. Nutze System-MIDI oder einen nativen Adapter.'],
  ['断开设备','Disconnect instrument','楽器を切断','Instrument trennen'],
  ['将当前预设保存至琴','Save this preset on the instrument','この設定を楽器に保存','Preset im Instrument speichern'],
  ['连接琴端参数','Connect instrument controls','楽器の操作を接続','Instrumentsteuerung verbinden'],
  ['蓝牙 MIDI 传送音符事件，不是实时演奏音频。低延迟监听建议使用琴的有线耳机或音频输出。','Bluetooth MIDI carries note events. Use wired headphones or the instrument audio output for low-latency monitoring.','Bluetooth MIDIは音符イベントを送信します。低遅延モニターには楽器の有線ヘッドホンまたは音声出力を使用してください。','Bluetooth MIDI überträgt Notenereignisse. Für latenzarmes Mithören nutze Kabelkopfhörer oder den Audioausgang des Instruments.'],
  ['写入琴内存储需要型号适配器和设备确认；无适配器不会发送参数。','Saving on the instrument needs a compatible adapter and device confirmation.','楽器への保存には対応アダプターと楽器側の確認が必要です。','Speichern im Instrument erfordert einen passenden Adapter und eine Gerätebestätigung.'],
  ['蓝牙 MIDI 已连接','Bluetooth MIDI connected','Bluetooth MIDI接続済み','Bluetooth MIDI verbunden'],
  ['蓝牙 MIDI 未连接','Bluetooth MIDI disconnected','Bluetooth MIDI未接続','Bluetooth MIDI getrennt'],
  ['琴端参数适配器已连接','Instrument controls connected','楽器の操作に接続済み','Instrumentsteuerung verbunden'],
  ['琴端参数待型号适配','Instrument controls need a compatible model adapter','楽器の操作には対応機種のアダプターが必要です','Instrumentparameter benötigen einen Modelladapter'],
  ['琴端到输出设备的时延尚未实测。','Instrument-to-output latency has not been measured.','楽器から出力機器までの遅延は未測定です。','Latenz vom Instrument zum Ausgabegerät noch nicht gemessen.'],
  ['浏览器音频缓冲估计','Browser audio-buffer estimate','ブラウザの音声バッファ推定値','Geschätzter Browser-Audiopuffer'],
  ['麦克风输入增益','Microphone input gain','マイク入力ゲイン','Mikrofon-Eingangsverstärkung'],
  ['只调节本机麦克风录音，不改变琴内拾音器硬件灵敏度。','Adjusts local microphone recording only. Instrument pickup sensitivity stays unchanged.','端末のマイク録音のみを調整します。楽器のピックアップ感度は変更しません。','Regelt nur lokale Mikrofonaufnahmen. Die Tonabnehmerempfindlichkeit des Instruments bleibt unverändert.'],
  ['导入预设','Import presets','プリセットを読み込む','Presets importieren'],
  ['分组','Group','グループ','Gruppe'],
  ['未分组','Ungrouped','未分類','Ohne Gruppe'],
  ['改名','Rename','名前を変更','Umbenennen'],
  ['修改预设名称和分组','Change preset name and group','名前とグループを変更','Preset-Namen und Gruppe ändern'],
  ['按工程长度循环','Loop using project length','プロジェクトの長さで繰り返す','Mit Projektlänge wiederholen'],
  ['仅统一循环长度，补静音或截取播放副本；原始录音保留。','Pads or trims playback copies to a common loop length. Original recordings are kept.','再生用の複製を無音追加または切り詰めで同じ長さにします。元の録音は保持します。','Wiedergabekopien werden mit Stille ergänzt oder gekürzt. Originalaufnahmen bleiben erhalten.'],
  ['全部','All','すべて','Alle'],
  ['本国特色','Local traditions','この国の曲','Landestypisch'],
  ['全球通用','Shared classics','共通レパートリー','International'],
  ['曲库范围','Library collection','曲の範囲','Repertoire-Auswahl'],
  ['首曲目','pieces','曲','Stücke'],
  ['练习短版','Practice excerpt','練習用の短い抜粋','Kurzer Übungsauszug'],
  ['来源已核对','Source checked','出典確認済み','Quelle geprüft'],
  ['文部省唱歌（1910年原谱）','Japanese school songs (1910 edition)','文部省唱歌（1910年原譜）','Japanische Schullieder (Ausgabe von 1910)'],
  ['中国传统旋律（1884年采录谱）','Chinese traditional melody (1884 transcription)','中国の伝承旋律（1884年採譜）','Traditionelle chinesische Melodie (Notierung von 1884)'],
  ['来源','Source','出典','Quelle'],
  ['查看曲目来源','View score source','楽譜の出典を見る','Notenquelle ansehen'],
  ['原谱版本','Source edition','原譜の版','Quellenausgabe'],
  ['原谱乐器','Original instrument','原譜の楽器','Originalinstrument'],
  ['许可标注','Licence stated by the source','出典に記載されたライセンス','Lizenzangabe der Quelle'],
  ['署名','Attribution','クレジット','Quellenangabe'],
  ['查看公开谱本','Open the source score','公開楽譜を開く','Quellennoten öffnen'],
  ['查看许可说明','Open licence details','ライセンスの説明を開く','Lizenzhinweise öffnen'],
  ['练习短版仅节选旋律；来源核对不等于全球发行授权。','Practice excerpts contain selected melody passages. Checking a source does not grant worldwide publication rights.','練習用の短い抜粋は旋律の一部です。出典の確認は世界各国での公開許可を意味しません。','Übungsauszüge enthalten ausgewählte Melodiepassagen. Die Quellenprüfung erteilt keine weltweiten Veröffentlichungsrechte.'],
  ['谱面与示范为练习用节选，不代表完整原作录音。','The score and demo are practice excerpts, not a complete recording of the original work.','楽譜とお手本は練習用の抜粋であり、原作全曲の録音ではありません。','Noten und Demo sind Übungsauszüge und keine vollständige Aufnahme des Originalwerks.'],
  ['练习短版 · 节选旋律','Practice excerpt · selected melody','練習用の短い抜粋 · 旋律の一部','Kurzer Übungsauszug · Melodiepassage']
])add(zh,zh,en,ja,de);
const entries="我的琴房|My studio|マイスタジオ|Mein Studio\n曲库|Music library|楽曲ライブラリ|Musikbibliothek\n练习|Practice|練習|Üben\n录音创作|Record & create|録音・制作|Aufnehmen & gestalten\n音色工作台|Sound studio|音色スタジオ|Klangstudio\n调音与节拍|Tune & keep time|調弦・メトロノーム|Stimmen & Takt\n我的设备|My instrument|マイ楽器|Mein Instrument\n学习路径|Learning path|学習コース|Lernpfad\n练习笔记|Practice notes|練習ノート|Übungsnotizen\n产品探索|Explore instruments|製品を見る|Instrumente entdecken\n我的设置|My settings|設定|Meine Einstellungen\n我的手机琴房|My mobile studio|スマホのマイスタジオ|Mein mobiles Studio\n我的琴房设置|Studio settings|スタジオ設定|Studio-Einstellungen\n更多|More|その他|Mehr\n设置|Settings|設定|Einstellungen\n中文|中文|中文|中文\n主要功能|Main navigation|メインメニュー|Hauptnavigation\n手机主要功能|Mobile navigation|スマホのメニュー|Mobile Navigation\n桌面导航|Desktop navigation|デスクトップのメニュー|Desktop-Navigation\n打开全部功能|Open all tools|すべての機能を開く|Alle Funktionen öffnen\n跳到主要内容|Skip to main content|メインコンテンツへ移動|Zum Hauptinhalt\n关闭|Close|閉じる|Schließen\n切换深色模式|Toggle dark mode|ダークモードを切り替える|Dunkelmodus umschalten\n浅色|Light|ライト|Hell\n深色|Dark|ダーク|Dunkel\n外观|Appearance|表示テーマ|Darstellung\n界面语言|Interface language|表示言語|Anzeigesprache\n地区|Region|地域|Region\n美国|United States|米国|USA\n英国|United Kingdom|英国|Vereinigtes Königreich\n日本|Japan|日本|Japan\n德国|Germany|ドイツ|Deutschland\n中国|China|中国|China\n法国|France|フランス|Frankreich\n今天，让音乐近一点。|Make room for music today.|今日は、音楽をもっと身近に。|Heute ist Zeit für Musik.\n一首旋律，一段专注，属于你的练习时间。|One melody, a little focus, and time to practise at your pace.|ひとつの旋律に集中する、自分のための練習時間。|Eine Melodie, ein wenig Ruhe und Zeit zum Üben.\n继续你的旋律|Continue your melody|旋律の続きを練習|Spiele deine Melodie weiter\n从第一段旋律开始|Start your first melody|最初の旋律から始める|Starte mit deiner ersten Melodie\n放慢一点，把每一个音拉得更从容。|Slow down and give every note room to breathe.|少しゆっくり、一音ずつ落ち着いて弾きましょう。|Spiele langsamer und gib jedem Ton Raum.\n进入练习|Start practising|練習を始める|Üben starten\n发现曲目|Discover music|曲を探す|Musik entdecken\n无需连接琴，即可试听与看谱练习|Listen and read the score without connecting an instrument.|楽器を接続せずに試聴・譜読みができます。|Höre zu und lies die Noten, auch ohne verbundenes Instrument.\n今日练习|Today's practice|今日の練習|Heute geübt\n设置练习目标|Set a practice goal|練習目標を設定|Übungsziel festlegen\n最近练习|Recent practice|最近の練習|Letzte Übungen\n全部记录|All sessions|すべての記録|Alle Einheiten\n还没有练习记录|No practice sessions yet|練習記録はまだありません|Noch keine Übungseinheiten\n完成一次聆听或跟奏后，会显示在这里。|Finish a listening or play-along session to see it here.|試聴または合わせて弾く練習を終えると、ここに表示されます。|Beende eine Hör- oder Mitspieleinheit, damit sie hier erscheint.\n统计当前浏览器保存的练习与聆听记录|Based on practice and listening sessions saved in this browser.|このブラウザに保存された練習・試聴記録の集計です。|Erfasst die in diesem Browser gespeicherten Übungs- und Höreinheiten.\n先把声音调准|Tune before you play|まずは調弦から|Stimme zuerst dein Instrument\n挑一个音色|Choose a sound|音色を選ぶ|Wähle einen Klang\n找到喜欢的声音|Find a sound you love|お気に入りの音色を探す|Finde deinen Lieblingsklang\n录一段灵感|Record an idea|ひらめきを録音|Nimm eine Idee auf\n留住这一刻|Capture the moment|今の演奏を残す|Halte den Moment fest\n连接我的琴|Connect my instrument|楽器を接続する|Mein Instrument verbinden\n查看设备与路由|Check connections and audio routing|接続と音声経路を確認|Verbindungen und Audiowege prüfen\n选一首，开始拉琴|Choose a piece and start playing|曲を選んで弾き始める|Wähle ein Stück und spiele los\n查看曲库|Open the library|ライブラリを見る|Bibliothek öffnen\n从持琴到第一首旋律|From holding the violin to your first melody|構え方から最初の旋律まで|Vom Halten der Geige zur ersten Melodie\n认识空弦、放松运弓、慢速分句。|Learn the open strings, relax your bowing, and practise short phrases slowly.|開放弦を覚え、力を抜いて運弓し、短いフレーズをゆっくり練習。|Lerne die leeren Saiten, entspanne die Bogenführung und übe kurze Phrasen langsam.\n按照自己的节奏，建立演奏习惯。|Build a playing habit at your own pace.|自分のペースで、演奏の習慣を作りましょう。|Entwickle eine Spielroutine in deinem eigenen Tempo.\n查看学习路径|View the learning path|学習コースを見る|Lernpfad ansehen\n找到下一首想拉的旋律|Find your next melody|次に弾きたい曲を探す|Finde deine nächste Melodie\n收藏喜欢的曲目，用自己的速度练习。|Save favourite pieces and practise at your own pace.|好きな曲をお気に入りに登録し、自分の速さで練習しましょう。|Speichere deine Lieblingsstücke und übe in deinem Tempo.\n搜索曲名或作者|Search by title or composer|曲名・作者で検索|Titel oder Komponist suchen\n搜索曲目|Search music|楽曲を検索|Musik suchen\n全部曲目|All pieces|すべての曲|Alle Stücke\n入门|Beginner|入門|Einstieg\n入门练习|Beginner practice|入門練習|Übungen für Einsteiger\n经典|Classical|クラシック|Klassik\n经典旋律|Classical melodies|クラシックの旋律|Klassische Melodien\n民谣|Folk|民謡|Volksmusik\n民谣小品|Folk pieces|民謡の小品|Kleine Volksmusikstücke\n我的收藏|Favourites|お気に入り|Favoriten\n收藏|Save to favourites|お気に入りに登録|Als Favorit speichern\n取消收藏|Remove from favourites|お気に入りを解除|Aus Favoriten entfernen\n收藏当前曲目|Save this piece|この曲をお気に入りに登録|Dieses Stück speichern\n卡片视图|Card view|カード表示|Kartenansicht\n列表视图|List view|リスト表示|Listenansicht\n没有找到曲目|No pieces found|曲が見つかりません|Keine Stücke gefunden\n换一个关键词或分类试试。|Try another search term or category.|別のキーワードやカテゴリをお試しください。|Versuche einen anderen Suchbegriff oder eine andere Kategorie.\n候选谱本|Draft score|確認待ちの楽譜|Notenentwurf\n已登记发布|Publication registered|公開登録済み|Veröffentlichung registriert\n权利待核验|Rights not yet verified|権利確認待ち|Rechte noch ungeprüft\n演示审核已登记|Demo review recorded|デモ審査の記録あり|Demo-Prüfung erfasst\n自建|Custom|自作|Eigene\n自建练习|Custom practice|自作の練習|Eigene Übung\n旋律|Melody|旋律|Melodie\n把一首曲子，练成自己的声音。|Make the piece your own.|一曲を、自分らしい演奏へ。|Mach das Stück zu deiner Musik.\n先听，再慢练。选定段落，逐句推进。|Listen first, then practise slowly, one passage at a time.|まず聴いて、ゆっくり練習。区間を選び、一句ずつ進めましょう。|Höre zuerst zu und übe dann langsam, Abschnitt für Abschnitt.\n更换曲目|Choose another piece|曲を変更|Anderes Stück wählen\n谱面与播放共用时间刻度|The score and playback share one timeline.|楽譜と再生は同じ時間軸で動きます。|Noten und Wiedergabe verwenden dieselbe Zeitachse.\n开发候选谱本 · 尚未核验正式发行权利|Development draft · publication rights not verified|開発用の楽譜案 · 正式な公開権利は未確認|Entwicklungsentwurf · Veröffentlichungsrechte ungeprüft\n示范聆听|Listen to the demo|お手本を聴く|Demo anhören\n跟奏练习|Microphone play-along|マイクで合わせて弾く|Mit Mikrofon mitspielen\n麦克风跟奏|Microphone practice|マイクでの練習|Mikrofonübung\n停止|Stop|停止|Stopp\n练习设置|Practice settings|練習設定|Übungseinstellungen\n练习速度|Practice tempo|練習テンポ|Übungstempo\n速度|Tempo|テンポ|Tempo\n拍号|Time signature|拍子|Taktart\n移调|Transpose|移調|Transponieren\nA–B 分段|A–B passage|A–B区間|A–B-Abschnitt\n按小节|By bar|小節単位|Nach Takten\n从|From|開始|Von\n到|To|終了|Bis\n起始小节|First bar|開始小節|Erster Takt\n结束小节|Last bar|終了小節|Letzter Takt\n从小节|From bar|開始小節|Ab Takt\n到小节|To bar|終了小節|Bis Takt\n0 = 曲末|0 = end of piece|0 = 曲の終わり|0 = Stückende\n重复聆听选定段落|Repeat the selected passage|選択した区間を繰り返し聴く|Gewählten Abschnitt wiederholen\n重复这个片段|Repeat this passage|この区間を繰り返す|Diesen Abschnitt wiederholen\n重复聆听|Repeat listening|繰り返し試聴|Wiederholt anhören\n单次|Once|1回|Einmal\n循环|Loop|ループ|Schleife\n更换|Change|変更|Ändern\n跟奏使用单音麦克风检测，80–3000 Hz。结果仅作练习参考，尚未完成实琴标定。|Play-along detects single notes from the microphone at 80–3000 Hz. Results are practice guides, not calibrated violin measurements.|マイクで80〜3000 Hzの単音を検出します。結果は練習の参考値で、実際のバイオリンでの校正は未完了です。|Beim Mitspielen werden einzelne Mikrofontöne von 80–3000 Hz erkannt. Die Ergebnisse dienen als Übungshilfe; eine Kalibrierung mit echter Geige steht aus.\n给旋律一点伴奏|Add a little accompaniment|旋律に伴奏を添える|Begleite deine Melodie\n原创合成和弦 · 点击开启，再次点击停止|Original synthesised chords · tap to start, tap again to stop|オリジナルの合成和音 · タップで開始、もう一度で停止|Eigene Synthesizer-Akkorde · antippen zum Starten, erneut zum Stoppen\n伴奏方式|Accompaniment style|伴奏スタイル|Begleitstil\n分解和弦|Arpeggio|アルペジオ|Arpeggio\n扫弦|Strum|ストローク|Anschlag\n长音铺底|Sustained pad|持続音パッド|Liegender Klang\n麦克风跟奏会关闭参考播放与伴奏，减少扬声器串音。|Microphone practice stops reference playback and accompaniment to reduce speaker bleed.|マイク練習ではスピーカー音の混入を減らすため、参考音と伴奏を止めます。|Mikrofonübungen stoppen Referenzwiedergabe und Begleitung, um Lautsprechereinstreuungen zu verringern.\n谱面与段落|Score & passage|楽譜と区間|Noten & Abschnitt\n参考结果|Practice result|参考結果|Übungsergebnis\n找到你的声音。|Find your sound.|自分の音色を見つけよう。|Finde deinen Klang.\n从干净的原声，到带一点空间的个人音色。|From a clean tone to a sound with a little space, make it yours.|すっきりした音から空間を感じる音まで、自分らしい音色に。|Vom klaren Grundklang bis zu deinem persönlichen Raumklang.\n保存当前预设|Save this preset|現在のプリセットを保存|Aktuelles Preset speichern\n原声素描|Acoustic sketch|アコースティック|Akustische Skizze\n暖木色|Warm wood|あたたかな木の響き|Warmer Holzklang\n明亮弦声|Bright strings|明るい弦の音|Helle Saiten\n电音线条|Electric lines|エレクトリック|Elektrische Linien\n低音空间|Bass space|低音の空間|Bassraum\n琴键瞬间|Piano moments|ピアノのひととき|Klaviermomente\n复古风琴|Vintage organ|ヴィンテージオルガン|Vintage-Orgel\n弦乐铺陈|String ensemble|ストリングス|Streicherfläche\n氛围云层|Ambient cloud|アンビエント|Ambient-Wolke\n清晰 · 基础练习|Clear · basic practice|クリア · 基礎練習|Klar · Grundlagen\n柔和 · 慢板|Soft · slow passages|柔らかい · ゆったりした曲|Sanft · langsame Passagen\n清亮 · 旋律|Bright · melody|明るい · メロディ|Hell · Melodie\n锐利 · 流行|Edgy · pop|シャープ · ポップス|Markant · Pop\n厚实 · 低音|Full · bass|厚みのある音 · 低音|Voll · Bass\n短音 · 轻巧|Short · light|短い音 · 軽やか|Kurz · leicht\n持续 · 复古|Sustained · vintage|持続音 · レトロ|Anhaltend · Vintage\n绵长 · 合奏|Flowing · ensemble|伸びやか · 合奏|Fließend · Ensemble\n缓起 · 空间|Soft attack · spacious|緩やかな立ち上がり · 空間|Sanfter Einsatz · Raum\n浏览器合成预览|Browser synthesiser preview|ブラウザ合成音のプレビュー|Vorschau mit Browser-Synthesizer\n试听旋律|Preview the melody|旋律を試聴|Melodie anhören\n声音细节|Shape the sound|音の細部を調整|Klangdetails\n固定效果路由|Fixed effect routing|固定のエフェクト経路|Feste Effektwege\n压缩|Compression|コンプレッサー|Kompression\n收稳动态|Smooth the dynamics|音量の変化を整える|Dynamik glätten\n延时|Delay|ディレイ|Delay\n加入回声|Add echoes|エコーを加える|Echo hinzufügen\n混响|Reverb|リバーブ|Hall\n增加空间|Add space|空間の響きを加える|Raum hinzufügen\n音量|Volume|音量|Lautstärke\n控制输出|Adjust output level|出力音量を調整|Ausgangspegel regeln\n我的预设|My presets|マイプリセット|Meine Presets\n导出|Export|書き出す|Exportieren\n应用|Apply|適用|Anwenden\n保存一个喜欢的音色|Save a favourite sound|好きな音色を保存|Speichere deinen Lieblingsklang\n你的音色与效果参数会保存在当前手机浏览器。|Your sound and effect settings are saved in this mobile browser.|音色とエフェクト設定は、このスマホのブラウザに保存されます。|Deine Klang- und Effekteinstellungen werden in diesem mobilen Browser gespeichert.\n琴端音色|Instrument sounds|楽器側の音色|Klänge im Instrument\n待接入|Not connected yet|接続機能は未実装|Noch nicht angebunden\n现在的音色控制作用于浏览器示范与合成录音。连接琴后，需要确认型号和 DSP 协议才能写入设备。|These controls affect browser demos and synthesised recordings. Writing sounds to an instrument requires its model and DSP protocol.|現在の設定はブラウザのお手本再生と合成録音に適用されます。楽器への書き込みには、機種とDSPプロトコルの確認が必要です。|Diese Regler wirken auf Browser-Demos und Synthesizer-Aufnahmen. Für das Schreiben ins Instrument werden Modell und DSP-Protokoll benötigt.\n查看设备能力|View instrument capabilities|楽器の機能を確認|Instrumentfunktionen ansehen\n九种音色为原创合成音源，未使用竞品音色包或采样。|All nine sounds are original synthesis presets, with no competitor sound packs or samples.|9種類の音色は独自の合成音源です。他社の音色パックやサンプルは使用していません。|Alle neun Klänge sind eigene Synthese-Presets, ohne Klangpakete oder Samples anderer Anbieter.\n保存当前音色|Save the current sound|現在の音色を保存|Aktuellen Klang speichern\n预设名称|Preset name|プリセット名|Preset-Name\n保存预设|Save preset|プリセットを保存|Preset speichern\n当前效果参数一起保存|Effect settings are saved too|現在のエフェクト設定も保存|Effekteinstellungen werden mitgespeichert\n删除这个音色预设？|Delete this sound preset?|この音色プリセットを削除しますか？|Dieses Klang-Preset löschen?\n只删除当前浏览器中的预设记录。|Only the preset saved in this browser will be deleted.|このブラウザ内のプリセット記録のみ削除します。|Nur das Preset in diesem Browser wird gelöscht.\n确认删除|Confirm deletion|削除する|Löschen bestätigen\n把灵感，留在这里。|Keep your ideas here.|ひらめきを、ここに残そう。|Halte deine Ideen hier fest.\n四轨循环、独立录音与视频，让每一次尝试有迹可循。|Capture your experiments with four loop tracks, separate recordings and video.|4トラックのループ、個別の録音・動画で、試した演奏を残しましょう。|Halte deine Versuche mit vier Loop-Spuren, Einzelaufnahmen und Videos fest.\n保存工程|Save project|プロジェクトを保存|Projekt speichern\n播放四轨|Play all tracks|全トラックを再生|Alle Spuren abspielen\n回放中|Playing back|再生中|Wiedergabe läuft\n录制来源|Recording source|録音ソース|Aufnahmequelle\n浏览器合成|Browser synthesis|ブラウザ合成音|Browser-Synthese\n真实麦克风|Microphone input|実際のマイク入力|Mikrofoneingang\n麦克风|Microphone|マイク|Mikrofon\n工程小节|Project bars|プロジェクトの小節数|Projekttakte\n工程小节数|Project bar count|プロジェクトの小節数|Anzahl der Projekttakte\n轨道同一时刻启动，各自按录制长度循环；工程小节是备注，尚未做录音量化与延迟补偿。|Tracks start together and each loops at its own recorded length. Bar count is a note only; quantisation and latency compensation are not implemented.|各トラックは同時に開始し、それぞれの録音長でループします。小節数はメモのみで、録音のクオンタイズと遅延補正は未実装です。|Die Spuren starten gemeinsam und loopen jeweils in ihrer Aufnahmelänge. Die Taktzahl ist nur eine Notiz; Quantisierung und Latenzausgleich sind noch nicht umgesetzt.\n录一段声音，让灵感从这里开始|Record a sound and start your next idea|音を録って、ここからアイデアを広げよう|Nimm einen Klang auf und beginne deine nächste Idee\n读取真实音频波形…|Reading the recorded waveform…|録音データの波形を読み込み中…|Aufgezeichnete Wellenform wird geladen…\n已录音频的相对波形（按峰值归一显示）|Relative recorded waveform, normalised to its peak|録音の相対波形（ピークで正規化）|Relative Aufnahmewellenform, auf den Spitzenwert normiert\n空轨|Empty track|空のトラック|Leere Spur\n等待录制|Ready to record|録音待ち|Bereit zur Aufnahme\n已存本机|Saved in this browser|このブラウザに保存済み|In diesem Browser gespeichert\n仅内存，需下载|Memory only · download now|メモリのみ · ダウンロード推奨|Nur im Arbeitsspeicher · herunterladen\n仅内存|Memory only|メモリのみ|Nur im Arbeitsspeicher\n准备录制。浏览器合成来源会播放当前练习旋律。|Ready to record. Browser synthesis plays the current practice melody.|録音の準備ができました。ブラウザ合成音を選ぶと、現在の練習曲を再生します。|Bereit zur Aufnahme. Die Browser-Synthese spielt die aktuelle Übungsmelodie.\n正在录制，点击停止后保存。|Recording. Tap Stop to save.|録音中です。停止すると保存されます。|Aufnahme läuft. Tippe zum Speichern auf Stopp.\n等待录制权限…|Waiting for recording permission…|録音の許可を待っています…|Warten auf Aufnahmeberechtigung…\n录下你的演奏|Record your playing|演奏を録音する|Nimm dein Spiel auf\n独立录音不覆盖循环轨。视频会单独请求相机与麦克风。|Separate recordings do not overwrite loop tracks. Video requests camera and microphone access separately.|個別録音はループトラックを上書きしません。動画ではカメラとマイクの許可を別途求めます。|Einzelaufnahmen überschreiben keine Loop-Spuren. Video fordert gesondert Zugriff auf Kamera und Mikrofon an.\n录音|Audio recording|録音|Audioaufnahme\n录视频|Record video|動画を撮る|Video aufnehmen\n停止并保存|Stop & save|停止して保存|Stoppen & speichern\n媒体只保存在当前浏览器与地址。请下载备份；没有云端音频上传。|Media is saved only in this browser at this site address. Download a backup; no audio is uploaded to the cloud.|録音・動画は、このブラウザとサイトアドレス内にだけ保存されます。バックアップをダウンロードしてください。クラウドへの音声アップロードはありません。|Medien bleiben in diesem Browser unter dieser Website-Adresse. Lade eine Sicherung herunter; Audio wird nicht in eine Cloud hochgeladen.\n我的工程|My projects|マイプロジェクト|Meine Projekte\n保存你的第一个工程|Save your first project|最初のプロジェクトを保存|Speichere dein erstes Projekt\n工程保存参数与本机轨道引用；音频另存浏览器。|Projects store settings and local track references; audio is stored separately in this browser.|プロジェクトには設定とローカルトラックへの参照を保存します。音声はブラウザ内に別途保存されます。|Projekte speichern Einstellungen und lokale Spurverweise; Audio wird separat im Browser gespeichert.\n打开|Open|開く|Öffnen\n我的录音与视频|My recordings & videos|録音と動画|Meine Aufnahmen & Videos\n还没有录音|No recordings yet|録音はまだありません|Noch keine Aufnahmen\n录下一个乐句，停止后即可回听与下载。|Record a phrase, then stop to listen back or download it.|フレーズを録音し、停止後に聴き直したりダウンロードしたりできます。|Nimm eine Phrase auf und stoppe, um sie anzuhören oder herunterzuladen.\n保存本机工程|Save a local project|ローカルプロジェクトを保存|Lokales Projekt speichern\n保存速度、小节备注与当前四轨引用。音频存于当前浏览器，不会上传云端。|Save tempo, bar notes and references to the four tracks. Audio stays in this browser and is not uploaded.|テンポ、小節数のメモ、現在の4トラックへの参照を保存します。音声はこのブラウザ内に残り、クラウドには送信されません。|Speichere Tempo, Taktnotiz und Verweise auf die vier Spuren. Audio bleibt in diesem Browser und wird nicht hochgeladen.\n工程名称|Project name|プロジェクト名|Projektname\n文件不在当前浏览器中，可能被清理、覆盖或保存在另一个地址。工程只有引用，没有云端音频。|Files are missing from this browser. They may have been cleared, replaced or saved at another address. Projects contain references, not cloud audio.|このブラウザにファイルがありません。削除・上書きされたか、別のアドレスに保存された可能性があります。プロジェクトは参照のみで、クラウド音声はありません。|Die Dateien fehlen in diesem Browser. Sie wurden möglicherweise gelöscht, ersetzt oder unter einer anderen Adresse gespeichert. Projekte enthalten Verweise, keine Cloud-Audiodateien.\n所有轨道音频均已在当前浏览器找到。|All track audio was found in this browser.|すべてのトラック音声が、このブラウザ内に見つかりました。|Alle Spuraufnahmen wurden in diesem Browser gefunden.\n播放这个工程|Play this project|このプロジェクトを再生|Dieses Projekt abspielen\n删除这个工程？|Delete this project?|このプロジェクトを削除しますか？|Dieses Projekt löschen?\n删除工程参数与引用；原音频保留在当前浏览器。|Delete project settings and references; keep the audio in this browser.|プロジェクト設定と参照のみ削除し、元の音声はブラウザに残します。|Projekteinstellungen und Verweise löschen; Audio bleibt im Browser.\n删除这段媒体？|Delete this recording?|この録音・動画を削除しますか？|Diese Aufnahme löschen?\n删除当前浏览器的媒体文件。请先下载需要保留的内容。|Delete the media stored in this browser. Download anything you want to keep first.|このブラウザに保存されたメディアを削除します。残したい内容は先にダウンロードしてください。|Lösche die Medien in diesem Browser. Lade zuerst alles herunter, was du behalten möchtest.\n清空这条循环轨？|Clear this loop track?|このループトラックを消去しますか？|Diese Loop-Spur leeren?\n删除本机媒体后，引用它的工程将显示缺失。|Projects that reference this media will show it as missing after deletion.|削除後、このメディアを参照するプロジェクトでは「見つかりません」と表示されます。|Nach dem Löschen zeigen Projekte, die diese Medien verwenden, sie als fehlend an.\n先调准，再出发。|Tune first, then play.|調弦してから、始めよう。|Erst stimmen, dann spielen.\n四根弦，一次平静而准确的开始。|Four strings, a calm start in tune.|4本の弦を整えて、落ち着いたスタートを。|Vier Saiten für einen ruhigen, gestimmten Start.\n单音检测 · 80–3000 Hz|Single-note detection · 80–3000 Hz|単音検出 · 80〜3000 Hz|Einzeltonerkennung · 80–3000 Hz\n尚未检测声音|No sound detected yet|音はまだ検出されていません|Noch kein Ton erkannt\n尚未检测到可靠单音|No reliable single note detected|安定した単音はまだ検出されていません|Noch kein verlässlicher Einzelton erkannt\n允许麦克风后，慢拉一根空弦。|Allow microphone access, then bow one open string slowly.|マイクを許可したら、開放弦を1本ゆっくり弾いてください。|Erlaube den Mikrofonzugriff und streiche dann langsam eine leere Saite.\n开始麦克风调音|Start microphone tuning|マイクで調弦を開始|Stimmen mit Mikrofon starten\n停止检测|Stop detection|検出を停止|Erkennung stoppen\n点击弦按钮播放参考音。参考音与练习移调独立，麦克风检测尚未完成实琴标定。|Tap a string to hear its reference tone. Reference tuning is independent of practice transposition; microphone detection has not been calibrated with a real violin.|弦のボタンをタップすると基準音を再生します。基準音は練習の移調と独立しており、マイク検出の実楽器校正は未完了です。|Tippe auf eine Saite für den Referenzton. Die Referenzstimmung ist unabhängig von der Übungstransposition; die Mikrofonerkennung ist noch nicht mit einer echten Geige kalibriert.\n调音设置|Tuning settings|調弦設定|Stimmeinstellungen\nA4 基准频率|A4 reference frequency|A4の基準周波数|A4-Referenzfrequenz\nA4基准频率|A4 reference frequency|A4の基準周波数|A4-Referenzfrequenz\n环境噪声门限|Noise gate threshold|ノイズゲートのしきい値|Schwelle des Noise-Gates\n嘈杂环境请提高门限；检测不到时靠近麦克风并慢拉单音。|Raise the threshold in noisy surroundings. If detection fails, move closer to the microphone and play one slow note.|周囲が騒がしいときはしきい値を上げてください。検出できない場合はマイクに近づき、単音をゆっくり弾いてください。|Erhöhe die Schwelle bei Umgebungsgeräuschen. Wird kein Ton erkannt, gehe näher ans Mikrofon und spiele einen langsamen Einzelton.\n节拍器|Metronome|メトロノーム|Metronom\n开始节拍|Start metronome|メトロノームを開始|Metronom starten\n停止节拍|Stop metronome|メトロノームを停止|Metronom stoppen\n节拍器拍号|Metronome time signature|メトロノームの拍子|Metronom-Taktart\n第一拍为重音，音频时钟负责安排节拍。|The first beat is accented; the audio clock schedules each beat.|1拍目にアクセントを付け、音声クロックでタイミングを制御します。|Der erste Schlag ist betont; die Audio-Uhr steuert die Schläge.\n请慢拉单音，避免环境噪声。|Play one slow note and reduce background noise.|周囲の雑音を避け、単音をゆっくり弾いてください。|Spiele einen langsamen Einzelton und vermeide Umgebungsgeräusche.\n音准接近基准|Close to the reference pitch|基準音に近い音程です|Nahe am Referenzton\n偏低 · 稍微调紧琴弦|Flat · tighten the string slightly|低め · 弦を少し張ってください|Zu tief · Saite etwas spannen\n偏高 · 稍微调松琴弦|Sharp · loosen the string slightly|高め · 弦を少し緩めてください|Zu hoch · Saite etwas lockern\n你的琴，你的连接方式。|Your instrument, your connections.|自分の楽器に合った接続を。|Dein Instrument, deine Verbindungen.\n控制、录音和 MIDI，分别查看真实状态。|Check control, recording and MIDI connections separately.|制御、録音、MIDIの状態を個別に確認できます。|Prüfe Steuerung, Aufnahme und MIDI getrennt.\n琴端联调待完成|Instrument integration pending|楽器との連携検証は未完了|Instrumentintegration steht aus\n未连接真实设备|No physical instrument connected|実際の楽器は未接続|Kein echtes Instrument verbunden\n设备未连接|Instrument not connected|楽器は未接続|Instrument nicht verbunden\n设备型号、固件、电量与时延均未取得实测值。|Instrument model, firmware, battery level and latency have not been measured.|機種、ファームウェア、電池残量、遅延の実測情報はまだ取得していません。|Modell, Firmware, Akkustand und Latenz sind noch nicht gemessen.\n查看连接步骤|View connection steps|接続手順を見る|Verbindungsschritte ansehen\n连接与路由|Connections & routing|接続と信号経路|Verbindungen & Signalwege\n参数控制|Parameter control|パラメータ制御|Parametersteuerung\nBLE 协议和设备握手待接入|BLE protocol and instrument handshake not implemented|BLEプロトコルと楽器の接続確認は未実装|BLE-Protokoll und Instrument-Handschlag noch nicht umgesetzt\n音频输入|Audio input|音声入力|Audioeingang\n录音页可请求系统麦克风；USB 声卡由系统管理|Recording can request the system microphone; USB audio interfaces are managed by the operating system.|録音ではシステムのマイクを使用できます。USBオーディオ機器はOS側で管理されます。|Aufnahmen können das Systemmikrofon verwenden; USB-Audiointerfaces werden vom Betriebssystem verwaltet.\n由系统选择|Selected by the system|システム側で選択|Vom System ausgewählt\nMIDI 端口|MIDI ports|MIDIポート|MIDI-Anschlüsse\n枚举真实输入与输出端口；音符收发尚未接入|Lists real input and output ports; sending and receiving notes is not implemented.|実際の入出力ポートを一覧表示します。音符の送受信は未実装です。|Listet echte Ein- und Ausgänge auf; das Senden und Empfangen von Noten ist noch nicht umgesetzt.\n未检测|Not checked|未確認|Nicht geprüft\n检测 MIDI 端口|Check MIDI ports|MIDIポートを確認|MIDI-Anschlüsse prüfen\n未命名端口|Unnamed port|名称のないポート|Unbenannter Anschluss\n设备能力|Instrument capabilities|楽器の対応機能|Instrumentfunktionen\n等待型号确认|Model confirmation pending|機種の確認待ち|Modellbestätigung ausstehend\n琴内 DSP 音色|Instrument DSP sounds|楽器内DSPの音色|DSP-Klänge im Instrument\n固件升级|Firmware update|ファームウェア更新|Firmware-Update\n设备内录|Instrument recording|楽器内録音|Aufnahme im Instrument\n真实时延测量|Measured latency|実測遅延|Gemessene Latenz\n待硬件验证|Hardware verification pending|ハードウェア検証待ち|Hardware-Prüfung ausstehend\n网页可用功能：参考音、示范播放、麦克风调音、浏览器录音与四轨回放。|Browser tools: reference tones, demo playback, microphone tuning, local recording and four-track playback.|ブラウザで使える機能：基準音、お手本再生、マイク調弦、録音、4トラック再生。|Browser-Funktionen: Referenztöne, Demo-Wiedergabe, Mikrofonstimmung, lokale Aufnahme und Vierspur-Wiedergabe.\n开始使用的三个步骤|Three steps to get started|使い始めるための3ステップ|Drei Schritte zum Start\n先建立有线监听|Start with wired monitoring|まずは有線で音を確認|Zuerst per Kabel abhören\n连接琴与耳机，确认琴本身可以发声。|Connect headphones to the instrument and check that it produces sound.|楽器にヘッドホンをつなぎ、楽器自体から音が出ることを確認してください。|Verbinde Kopfhörer mit dem Instrument und prüfe, ob es selbst Klang erzeugt.\n选择录音输入|Choose the recording input|録音入力を選ぶ|Aufnahmeeingang wählen\n在浏览器权限与系统输入中选择麦克风或 USB 声卡。|Choose your microphone or USB audio interface in browser permissions and system input settings.|ブラウザの許可とシステム入力設定で、マイクまたはUSBオーディオ機器を選んでください。|Wähle Mikrofon oder USB-Audiointerface in den Browserberechtigungen und Systemeinstellungen.\n调音，再练一句|Tune, then practise a phrase|調弦して、ひとつのフレーズを練習|Stimmen, dann eine Phrase üben\n确认 G / D / A / E，进入练习页慢速跟奏。|Check G / D / A / E, then practise slowly on the Practice page.|G・D・A・Eの音を確認し、練習ページでゆっくり合わせて弾きましょう。|Prüfe G / D / A / E und spiele dann auf der Übungsseite langsam mit.\n连接电子小提琴|Connect an electric violin|電子バイオリンを接続|Elektrische Geige verbinden\n先用琴本身的耳机或有线输出确认发声。|First check the instrument's headphone or wired output.|まず楽器のヘッドホン端子または有線出力で音を確認してください。|Prüfe zuerst den Kopfhörer- oder Kabelausgang des Instruments.\n录音时，在系统和浏览器中选择正确的麦克风 / USB 声卡输入。|For recording, select the correct microphone or USB audio input in both system and browser settings.|録音時は、OSとブラウザで正しいマイク・USBオーディオ入力を選んでください。|Wähle für Aufnahmen den richtigen Mikrofon- oder USB-Audioeingang im System und Browser.\nBLE 参数控制需要真实设备服务 UUID、协议与握手；当前版本尚未接入。|BLE control requires the instrument's service UUIDs, protocol and handshake. It is not connected in this version.|BLE制御には楽器のサービスUUID、プロトコル、接続確認が必要です。現在のバージョンでは未接続です。|BLE-Steuerung benötigt die Service-UUIDs, das Protokoll und den Handshake des Instruments. Diese Version ist noch nicht angebunden.\nMIDI 端口可以实际枚举，但端口出现不代表琴的音频已经接通。|MIDI ports can be listed, but a visible port does not mean the instrument's audio is connected.|MIDIポートを確認できますが、表示されても楽器の音声が接続済みとは限りません。|MIDI-Anschlüsse können angezeigt werden; ein sichtbarer Anschluss bedeutet nicht, dass das Instrument-Audio verbunden ist.\n固件版本、电量和端到端时延须从真实设备取得，当前不显示模拟值。|Firmware, battery and end-to-end latency must come from a real instrument. Simulated values are not shown.|ファームウェア、電池残量、全体の遅延は実機から取得する必要があります。模擬値は表示しません。|Firmware, Akkustand und Gesamtlatenz müssen vom echten Instrument stammen. Simulierte Werte werden nicht angezeigt.\n稍后查看连接帮助|View connection help later|接続ガイドは後で見る|Verbindungshilfe später ansehen\n每一次小进步，都算数。|Every small step counts.|小さな進歩を、大切に。|Jeder kleine Fortschritt zählt.\n从零开始到独立演奏，跟着路径练习。|Follow a path from the first steps to playing on your own.|基礎から自分で演奏できるまで、コースに沿って練習しましょう。|Folge dem Lernpfad von den ersten Schritten bis zum selbstständigen Spiel.\n从第一根空弦开始|Start with an open string|最初の開放弦から|Beginne mit einer leeren Saite\n起步 · 3 个步骤|Getting started · 3 steps|入門 · 3ステップ|Einstieg · 3 Schritte\n持琴与放松|Hold the violin comfortably|構え方とリラックス|Geige halten und entspannen\n轻放左手，找到舒适的肩颈位置。先在镜前检查姿势，不急着加快。|Keep your left hand relaxed and find a comfortable shoulder and neck position. Check your posture in a mirror before increasing the pace.|左手の力を抜き、肩と首が楽な位置を探しましょう。鏡で姿勢を確認し、速さは急いで上げなくて大丈夫です。|Halte die linke Hand locker und finde eine bequeme Schulter- und Kopfhaltung. Prüfe sie zuerst im Spiegel, bevor du das Tempo erhöhst.\n认识 G / D / A / E 空弦|Learn the G / D / A / E open strings|G・D・A・Eの開放弦を覚える|Die leeren Saiten G / D / A / E kennenlernen\n用调音器确认四根弦。每根弦慢拉四拍，听稳定的长音。|Check all four strings with the tuner. Bow each for four slow beats and listen for a steady tone.|チューナーで4本の弦を確認します。各弦をゆっくり4拍ずつ弾き、安定した長い音を聴きましょう。|Prüfe alle vier Saiten mit dem Stimmgerät. Streiche jede Saite langsam über vier Schläge und höre auf einen gleichmäßigen Ton.\n平稳运弓|Steady bowing|安定した運弓|Gleichmäßige Bogenführung\n在弓的中段开始。手腕放松，让四拍长音保持均匀。|Start in the middle of the bow. Relax your wrist and keep the four-beat tone even.|弓の中央から始めます。手首の力を抜き、4拍の長い音を均一に保ちましょう。|Beginne in der Bogenmitte. Entspanne dein Handgelenk und halte den Ton über vier Schläge gleichmäßig.\n把旋律拉得更连贯|Connect your melody|旋律をなめらかにつなぐ|Verbinde die Melodie\n进阶 · 3 个步骤|Moving forward · 3 steps|ステップアップ · 3ステップ|Weiterkommen · 3 Schritte\n第一把位音准|Intonation in first position|第1ポジションの音程|Intonation in der ersten Lage\n先听参考音，再慢拉。用 A–B 段落反复练习困难的两个小节。|Listen to the reference tone, then play slowly. Repeat two difficult bars with an A–B passage.|基準音を聴いてから、ゆっくり弾きます。難しい2小節をA–B区間にして繰り返し練習しましょう。|Höre den Referenzton und spiele dann langsam. Wiederhole zwei schwierige Takte als A–B-Abschnitt.\n换弦与节奏|String crossing & rhythm|移弦とリズム|Saitenwechsel & Rhythmus\n节拍器从 60 BPM 开始，先空弦换弦，再加入左手。|Start the metronome at 60 BPM. Practise open-string crossings before adding the left hand.|メトロノームを60 BPMに設定。まず開放弦で移弦し、その後に左手を加えましょう。|Starte das Metronom bei 60 BPM. Übe Saitenwechsel zuerst auf leeren Saiten und nimm dann die linke Hand dazu.\n完整乐句|A complete phrase|フレーズを通して弾く|Eine vollständige Phrase\n先示范聆听，再跟奏。连续演奏一个乐句后休息并复盘。|Listen to the demo, then play along. Complete a phrase, take a break and review it.|お手本を聴いてから合わせて弾きます。フレーズを通して弾いたら休憩し、振り返りましょう。|Höre zuerst die Demo und spiele dann mit. Beende eine Phrase, mache eine Pause und höre sie noch einmal an.\n留下属于你的声音|Capture your own sound|自分の音を残す|Halte deinen eigenen Klang fest\n创作 · 3 个步骤|Create · 3 steps|制作 · 3ステップ|Gestalten · 3 Schritte\n选择合适的音色|Choose the right sound|合う音色を選ぶ|Den passenden Klang wählen\n试听基础音色，少量添加混响。当前音色作用于浏览器示范。|Preview a basic sound and add a little reverb. These sounds apply to browser demos.|基本の音色を試聴し、リバーブを少し加えます。音色はブラウザのお手本再生に適用されます。|Höre einen Grundklang an und füge etwas Hall hinzu. Die Klänge wirken auf die Browser-Demo.\n录下第一段旋律|Record your first melody|最初の旋律を録音|Die erste Melodie aufnehmen\n在录音页选择真实麦克风，录下慢速乐句。停止后回听并下载备份。|Choose microphone input on the recording page and play a slow phrase. Stop, listen back and download a backup.|録音ページで実際のマイクを選び、ゆっくりフレーズを録音します。停止後に聴き直し、バックアップをダウンロードしましょう。|Wähle auf der Aufnahmeseite den Mikrofoneingang und spiele eine langsame Phrase. Stoppe, höre sie an und lade eine Sicherung herunter.\n尝试四轨循环|Try four-track looping|4トラックのループを試す|Vierspur-Loops ausprobieren\n先录简单长音，再加入旋律。每轨按自己的录制长度循环。|Record a simple sustained note, then add a melody. Each track loops at its own recorded length.|まず簡単な長い音を録り、その後に旋律を加えます。各トラックはそれぞれの録音長でループします。|Nimm zuerst einen einfachen gehaltenen Ton und dann eine Melodie auf. Jede Spur loopt in ihrer eigenen Aufnahmelänge.\n原创文字练习 · 自行标记进度|Original written exercises · mark your own progress|独自の文章レッスン · 進み具合は自分で記録|Eigene Textübungen · Fortschritt selbst markieren\n看完一步，就练一句。|Read a step, then play a phrase.|ひとつ読んだら、ひとつ弾こう。|Lies einen Schritt und spiele eine Phrase.\n把学习内容放到实际演奏中。先慢练，再记录，最后回听。|Put each lesson into practice. Play slowly, record, then listen back.|学んだことを演奏に取り入れましょう。ゆっくり練習し、録音して聴き返します。|Setze jede Lektion beim Spielen um. Übe langsam, nimm auf und höre danach zu.\n开始练习|Start practice|練習を始める|Übung starten\n原创文字指导。没有复制竞品课程视频或教学内容。|Original written guidance. No competitor course videos or lessons have been copied.|独自の文章によるガイドです。他社の講座動画や教材は複製していません。|Eigene schriftliche Anleitung. Es wurden keine Kursvideos oder Lehrinhalte anderer Anbieter kopiert.\n去练一句|Practise a phrase|ひとつのフレーズを練習|Eine Phrase üben\n记录练习中的小发现。|Keep your practice discoveries.|練習の発見を記録しよう。|Halte deine Entdeckungen beim Üben fest.\n当前为浏览器私有笔记，不会上网发布或提交真人审核。|These are private browser notes. They are not published online or sent to anyone for review.|このブラウザ内の個人ノートです。インターネットでの公開や、人による審査への送信は行いません。|Dies sind private Browser-Notizen. Sie werden weder online veröffentlicht noch zur Prüfung an andere gesendet.\n写一条练习笔记|Write a practice note|練習ノートを書く|Übungsnotiz schreiben\n私有草稿|Private draft|個人用の下書き|Privater Entwurf\n本机示例|Local example|ローカルの例|Lokales Beispiel\n本机隐藏|Hidden locally|ローカルで非表示|Lokal verborgen\n仅当前浏览器可见|Visible only in this browser|このブラウザだけで表示|Nur in diesem Browser sichtbar\n反馈|Feedback|フィードバック|Rückmeldung\n写下第一条练习笔记|Write your first practice note|最初の練習ノートを書こう|Schreibe deine erste Übungsnotiz\n可以记录一个难点、一个收获，或下一次练习目标。|Note a challenge, an achievement, or a goal for your next practice.|難しかったこと、できたこと、次の練習目標を書き留めましょう。|Notiere eine Schwierigkeit, einen Erfolg oder ein Ziel für die nächste Übung.\n作品分享|Sharing your recordings|録音・作品の共有|Aufnahmen teilen\n录音与视频可在创作页下载。云端发布、真实账号和 AI 制谱尚未接入。|Download recordings and videos on the Create page. Cloud publishing, user accounts and AI score generation are not connected.|制作ページで録音・動画をダウンロードできます。クラウド公開、ユーザーアカウント、AI楽譜生成は未接続です。|Lade Aufnahmen und Videos auf der Gestaltungsseite herunter. Cloud-Veröffentlichung, Benutzerkonten und KI-Notenerstellung sind noch nicht angebunden.\n查看我的录音|View my recordings|自分の録音を見る|Meine Aufnahmen ansehen\n今天的收获|What I learned today|今日の収穫|Das habe ich heute gelernt\n例如：今天用 60 BPM 练了第二小节，换弦更稳定了。|For example: I practised bar 2 at 60 BPM today, and my string crossings felt steadier.|例：今日は2小節目を60 BPMで練習。移弦が安定してきた。|Zum Beispiel: Heute habe ich Takt 2 bei 60 BPM geübt. Meine Saitenwechsel waren gleichmäßiger.\n只保存于当前浏览器，不会上网发布或提交真人审核。|Saved only in this browser; not published online or sent to anyone for review.|このブラウザ内にのみ保存され、公開や人による審査は行いません。|Wird nur in diesem Browser gespeichert, nicht online veröffentlicht oder an andere zur Prüfung gesendet.\n保存笔记|Save note|ノートを保存|Notiz speichern\n记录这条笔记的反馈|Add feedback to this note|このノートに感想を残す|Rückmeldung zur Notiz hinzufügen\n原因|Reason|理由|Grund\n提交反馈|Save feedback|フィードバックを保存|Rückmeldung speichern\n琴友|Fellow player|楽器仲間|Mitspieler\n本地记录|Local record|ローカル記録|Lokaler Eintrag\n探索 SmartVio 的可能。|Explore {brand}.|{brand}の可能性を探そう。|Entdecke {brand}.\n产品方向与概念外观，具体规格和价格待确认。|Product concepts and design previews. Specifications and prices are not final.|製品の方向性とコンセプト外観です。仕様・価格は未確定です。|Produktideen und Designvorschauen. Spezifikationen und Preise stehen noch nicht fest.\n产品规划|Product planning|製品計画|Produktplanung\n产品方向|Product concept|製品コンセプト|Produktidee\n价格待定|Price to be confirmed|価格未定|Preis noch offen\n查看产品方向|View the product concept|製品コンセプトを見る|Produktidee ansehen\n概念外观 · 非实物|Concept design · not a physical product|コンセプト外観 · 実物ではありません|Designkonzept · kein reales Produkt\n概念外观 · 非实物样机|Concept design · not a physical prototype|コンセプト外観 · 実機試作ではありません|Designkonzept · kein realer Prototyp\n电子小提琴概念外观|Electric violin concept design|電子バイオリンのコンセプト外観|Designkonzept einer elektrischen Geige\nSmartVio 电子小提琴概念外观|{brand} electric violin concept|{brand}電子バイオリンのコンセプト|{brand} Konzept einer elektrischen Geige\n此页用于验证产品信息布局。未接入真实支付、库存、物流和订阅权益。|This page previews product information. Payments, inventory, shipping and subscriptions are not connected.|製品情報のレイアウトを確認するためのページです。決済、在庫、配送、サブスクリプションは未接続です。|Diese Seite zeigt eine Vorschau der Produktinformationen. Zahlung, Bestand, Versand und Abonnements sind nicht angebunden.\n概念外观用于产品规划。完整规格、量产状态、价格与上市时间待确认。|Concept designs support product planning. Full specifications, production status, price and release date remain unconfirmed.|外観は製品計画用のコンセプトです。正式仕様、量産状況、価格、発売日は未確定です。|Die Designkonzepte dienen der Produktplanung. Vollständige Spezifikationen, Serienstatus, Preis und Erscheinungsdatum sind noch offen.\n把琴房，设成你的习惯。|Make your studio fit your routine.|自分の習慣に合うスタジオへ。|Richte dein Studio für deine Routine ein.\n管理目标、界面与本地记录。|Manage goals, appearance and local records.|目標、表示設定、ローカル記録を管理します。|Verwalte Ziele, Darstellung und lokale Aufzeichnungen.\n导出记录|Export records|記録を書き出す|Aufzeichnungen exportieren\n每日练习目标|Daily practice goal|1日の練習目標|Tägliches Übungsziel\n保存每日目标|Save daily goal|1日の目標を保存|Tagesziel speichern\n五种语言已覆盖导航和曲目标题，专业内容的完整本地化待完成。地区只影响候选曲目与展示。|Language affects labels and piece titles. The region changes the draft catalogue and display only.|言語によって表示と曲名が変わります。地域は確認待ち曲目と表示のみに反映されます。|Die Sprache bestimmt Beschriftungen und Stücktitel. Die Region ändert nur den Entwurfskatalog und die Anzeige.\n数据与保存|Data & storage|データと保存|Daten & Speicherung\n当前浏览器地址的 IndexedDB|IndexedDB for this browser and site|このブラウザ・サイトのIndexedDB|IndexedDB für diesen Browser und diese Website\n当前浏览器的练习与设置记录|Practice and settings saved in this browser|このブラウザに保存された練習・設定|Übungen und Einstellungen in diesem Browser\n云同步 / 原生 App|Cloud sync / native app|クラウド同期・ネイティブアプリ|Cloud-Sync / native App\n尚未接入，不代表账号云备份|Not connected; this is not a cloud account backup.|未接続です。アカウントのクラウドバックアップではありません。|Nicht angebunden; dies ist keine Cloud-Sicherung eines Kontos.\n导出练习 CSV|Export practice CSV|練習記録をCSVで書き出す|Übungen als CSV exportieren\n清除当前浏览器数据|Clear this browser's data|このブラウザのデータを消去|Daten dieses Browsers löschen\nJSON导出含练习、预设、工程与媒体清单，不含录音文件或私有笔记、反馈。删除前请下载录音，另行保留需要的笔记。浏览器清理可能移除记录。|JSON exports include practice, presets, projects and a media list, not recording files, private notes or feedback. Download recordings and keep needed notes separately before deleting. Browser cleanup may remove records.|JSONには練習、プリセット、プロジェクト、メディア一覧が含まれます。録音ファイル、個人ノート、フィードバックは含まれません。削除前に録音をダウンロードし、必要なノートを別途保存してください。ブラウザの消去で記録が失われる場合があります。|Der JSON-Export enthält Übungen, Presets, Projekte und eine Medienliste, aber keine Aufnahmedateien, privaten Notizen oder Rückmeldungen. Lade Aufnahmen herunter und sichere benötigte Notizen separat vor dem Löschen. Browser-Bereinigungen können Einträge entfernen.\n练习历史|Practice history|練習履歴|Übungsverlauf\n真实操作记录|Recorded activity|実際の操作記録|Aufgezeichnete Aktivitäten\n日期|Date|日付|Datum\n曲目|Piece|曲名|Stück\n方式|Mode|方法|Modus\n时长|Duration|時間|Dauer\n参考分|Reference score|参考スコア|Referenzwert\n参考结果|Practice result|参考結果|Übungsergebnis\n评分版本|Scoring version|採点バージョン|Bewertungsversion\n日期,曲目,方式,时长秒,参考分,评分版本|Date,Piece,Mode,Duration (s),Reference score,Scoring version|日付,曲名,方法,時間（秒）,参考スコア,採点バージョン|Datum,Stück,Modus,Dauer (s),Referenzwert,Bewertungsversion\n示范聆听不生成演奏成绩。跟奏记录保留输入来源、评分版本与段落范围。|Listening does not produce a playing score. Practice records keep the input source, scoring version and passage range.|お手本の試聴では演奏スコアを生成しません。練習記録には入力元、採点バージョン、区間を保存します。|Anhören erzeugt keine Spielbewertung. Übungseinträge speichern Eingangsquelle, Bewertungsversion und Abschnitt.\n暂无记录|No records yet|記録はまだありません|Noch keine Einträge\n选择你的国家|Choose your country|国を選択|Land auswählen\n为你设置语言和品牌|Set your language and brand|言語とブランドを設定|Sprache und Marke einstellen\n国家决定默认语言，也可以单独更改语言。|Your country sets the default language. You can change the language separately.|国に応じて初期言語を設定します。言語は個別に変更できます。|Das Land legt die Standardsprache fest. Du kannst die Sprache auch separat ändern.\n请选择国家或地区|Choose a country or region|国・地域を選択してください|Land oder Region auswählen\n继续进入琴房|Continue to your studio|スタジオへ進む|Weiter zum Studio\n重新选择国家|Choose another country|国を選び直す|Land neu auswählen\n国家与语言|Country & language|国と言語|Land & Sprache\n开机动画|Welcome animation|起動アニメーション|Startanimation\n跳过动画|Skip animation|アニメーションをスキップ|Animation überspringen\n轻触，开启你的音乐|Tap to begin your music|タップして、音楽を始めよう|Antippen und deine Musik starten\n四种语言覆盖页面、操作提示与帮助|Pages, prompts and help in four languages|ページ・操作案内・ヘルプを4言語で表示|Seiten, Hinweise und Hilfe in vier Sprachen\n跟随所选语言显示品牌|Brand follows your selected language|選択した言語に合わせてブランドを表示|Die Marke folgt deiner gewählten Sprache\nSilvio / VELLEN|Silvio / VELLEN|Silvio / VELLEN|Silvio / VELLEN\n记录只保存在当前浏览器，不会因为切换国家或语言而清空。|Records stay in this browser. Changing country or language does not erase them.|記録はこのブラウザ内に保存されます。国や言語を変えても消去されません。|Aufzeichnungen bleiben in diesem Browser. Ein Wechsel von Land oder Sprache löscht sie nicht.\n请先停止并保存录制，再更改国家或语言。|Stop and save the recording before changing country or language.|国や言語を変更する前に、録音を停止して保存してください。|Stoppe und speichere die Aufnahme, bevor du Land oder Sprache wechselst.\n已切换国家、语言和品牌。|Country, language and brand updated.|国・言語・ブランドを切り替えました。|Land, Sprache und Marke aktualisiert.\n不能保存国家选择|Could not save your country selection|国の選択を保存できません|Länderauswahl konnte nicht gespeichert werden\n本次仅在当前页面使用，请检查浏览器存储权限。|This choice applies to this page only. Check browser storage permissions.|今回はこのページ内だけに反映されます。ブラウザの保存権限を確認してください。|Diese Auswahl gilt nur für die aktuelle Seite. Prüfe die Speicherberechtigungen des Browsers.\n手机浏览器入口 · 数据留在本设备|Mobile browser edition · data stays here|スマホブラウザ版 · データはこの端末内に保存|Mobile Browser-Version · Daten bleiben hier\n保存于当前手机浏览器|Saved in this mobile browser|このスマホのブラウザに保存|In diesem mobilen Browser gespeichert\n正在读取当前浏览器数据|Loading this browser's data|このブラウザのデータを読み込み中|Browser-Daten werden geladen\n正在打开你的琴房…|Opening your studio…|スタジオを開いています…|Dein Studio wird geöffnet…\n手机浏览器保存 · 浏览器音源 · 设备待接入|Local browser storage · browser sounds · instrument not connected|ブラウザ内保存 · ブラウザ音源 · 楽器接続は未実装|Lokaler Browserspeicher · Browser-Klänge · Instrument noch nicht angebunden\n数据与隐私|Data & privacy|データとプライバシー|Daten & Datenschutz\nSmartVio 手机琴房|{brand} mobile studio|{brand} モバイルスタジオ|{brand} Mobiles Studio\nSmartVio 首页|{brand} home|{brand} ホーム|{brand} Startseite\nSmartVio 电子小提琴琴房：练习、调音、音色与录音创作。|{brand} electric violin studio: practice, tuning, sounds and recording.|{brand}電子バイオリンスタジオ：練習、調弦、音色、録音・制作。|{brand} Studio für elektrische Geige: Üben, Stimmen, Klänge und Aufnahme.\n我的电子小提琴|My electric violin|マイ電子バイオリン|Meine elektrische Geige\n设置暂存于内存；浏览器未允许保存。|Settings are in memory only; this browser did not allow saving.|設定はメモリ内だけです。ブラウザが保存を許可しませんでした。|Einstellungen bleiben nur im Arbeitsspeicher; der Browser erlaubt das Speichern nicht.\n本机媒体读取失败，请保留文件并稍后重试。|Could not read local media. Keep your files and try again later.|ローカルメディアを読み込めません。ファイルを残したまま、後で再試行してください。|Lokale Medien konnten nicht gelesen werden. Behalte deine Dateien und versuche es später erneut.\n当前段落没有音符，请调整 A–B 小节。|No notes in this passage. Adjust the A–B bars.|この区間に音符がありません。A–B小節を調整してください。|Dieser Abschnitt enthält keine Noten. Passe die A–B-Takte an.\n当前浏览器不支持视频录制。|This browser does not support video recording.|このブラウザは動画録画に対応していません。|Dieser Browser unterstützt keine Videoaufnahme.\n视频录制失败|Video recording failed|動画の録画に失敗しました|Videoaufnahme fehlgeschlagen\n视频没有可用数据|No usable video data|利用できる動画データがありません|Keine nutzbaren Videodaten\n请先停止当前录制。|Stop the current recording first.|先に現在の録音を停止してください。|Stoppe zuerst die laufende Aufnahme.\n已取消等待中的录制请求。|Pending recording request cancelled.|許可待ちの録音リクエストを取り消しました。|Ausstehende Aufnahmeanfrage abgebrochen.\n请先停止并完成当前录制。|Stop and finish the current recording first.|先に現在の録音を停止して完了してください。|Stoppe und beende zuerst die laufende Aufnahme.\n媒体删除尚未确认。|Media deletion has not been confirmed.|メディアの削除はまだ確認できていません。|Das Löschen der Medien ist noch nicht bestätigt.\n正在试听当前音色。|Previewing the current sound.|現在の音色を試聴中です。|Aktueller Klang wird vorgespielt.\n请填写预设名称。|Enter a preset name.|プリセット名を入力してください。|Gib einen Preset-Namen ein.\n预设已保存到当前手机浏览器。|Preset saved in this mobile browser.|プリセットをこのスマホのブラウザに保存しました。|Preset in diesem mobilen Browser gespeichert.\n已应用到浏览器音色。|Applied to the browser sound.|ブラウザの音色に適用しました。|Auf den Browser-Klang angewendet.\n媒体读取失败，轨道未删除。|Media could not be read; the track was not deleted.|メディアを読み込めなかったため、トラックは削除していません。|Medien konnten nicht gelesen werden; die Spur wurde nicht gelöscht.\n请先停止并保存录制。|Stop and save the recording first.|先に録音を停止して保存してください。|Stoppe und speichere zuerst die Aufnahme.\n请填写工程名称。|Enter a project name.|プロジェクト名を入力してください。|Gib einen Projektnamen ein.\n工程参数已保存；音频仍在当前浏览器。|Project settings saved; audio remains in this browser.|プロジェクト設定を保存しました。音声はこのブラウザ内に残ります。|Projekteinstellungen gespeichert; Audio bleibt in diesem Browser.\n本机音频读取失败。|Local audio could not be read.|ローカル音声を読み込めません。|Lokales Audio konnte nicht gelesen werden.\n工程媒体读取失败。|Project media could not be read.|プロジェクトのメディアを読み込めません。|Projektmedien konnten nicht gelesen werden.\n工程缺少媒体。|Project media is missing.|プロジェクトのメディアが見つかりません。|Projektmedien fehlen.\n工程没有可播放的音频。|This project has no playable audio.|このプロジェクトに再生可能な音声がありません。|Dieses Projekt enthält kein abspielbares Audio.\n本机工程正在播放。|The local project is playing.|ローカルプロジェクトを再生中です。|Das lokale Projekt wird abgespielt.\n当前浏览器不支持 Web MIDI。|This browser does not support Web MIDI.|このブラウザはWeb MIDIに対応していません。|Dieser Browser unterstützt kein Web MIDI.\n未发现 MIDI 端口。|No MIDI ports found.|MIDIポートは見つかりませんでした。|Keine MIDI-Anschlüsse gefunden.\n已保存为当前浏览器的私有草稿。|Saved as a private draft in this browser.|このブラウザに個人用の下書きとして保存しました。|Als privater Entwurf in diesem Browser gespeichert.\n反馈已保存在当前浏览器，不会发送给他人。|Feedback saved in this browser; it will not be sent to anyone.|フィードバックはこのブラウザ内に保存され、他の人には送信されません。|Rückmeldung in diesem Browser gespeichert; sie wird an niemanden gesendet.\n每日目标已保存。|Daily goal saved.|1日の目標を保存しました。|Tagesziel gespeichert.\n当前录制未完成，未执行删除。|Recording is unfinished; nothing was deleted.|録音が未完了のため、削除は行っていません。|Aufnahme noch nicht abgeschlossen; nichts wurde gelöscht.\n浏览器媒体删除未确认，浏览器文字记录保留。|Media deletion is unconfirmed; browser text records were kept.|メディアの削除を確認できないため、ブラウザ内の文字記録は残しています。|Medienlöschung unbestätigt; die Texteinträge bleiben erhalten.\n媒体已清除，但浏览器文字记录保存失败，请重试。|Media was cleared, but updating browser text records failed. Try again.|メディアは消去されましたが、文字記録の更新に失敗しました。再試行してください。|Medien wurden gelöscht, aber die Texteinträge konnten nicht aktualisiert werden. Bitte erneut versuchen.\n请先停止并保存录制，再修改播放或输入设置。|Stop and save the recording before changing playback or input settings.|再生・入力設定を変更する前に、録音を停止して保存してください。|Stoppe und speichere die Aufnahme, bevor du Wiedergabe- oder Eingangseinstellungen änderst.\n文字格式或长度不正确。|Invalid text format or length.|文字の形式または長さが正しくありません。|Textformat oder Länge ungültig.\n此页面的数据版本不兼容，请保留已有浏览器数据。|This page uses an incompatible data version. Keep your existing browser data.|このページのデータ形式は互換性がありません。既存のブラウザデータを残してください。|Die Datenversion dieser Seite ist nicht kompatibel. Behalte deine bisherigen Browser-Daten.\n当前浏览器不允许读取本地记录；可试听，保存功能暂不可用。|The browser blocked local records. Preview is available, but saving is unavailable.|ブラウザがローカル記録の読み込みを許可しません。試聴はできますが、保存は利用できません。|Der Browser blockiert lokale Einträge. Anhören ist möglich, Speichern derzeit nicht.\n当前浏览器记录无法解析，原数据已保留；请勿清理网站数据。|Browser records could not be read. Original data was kept; do not clear site data.|ブラウザの記録を解析できません。元のデータは残っています。サイトデータを消去しないでください。|Browser-Einträge konnten nicht gelesen werden. Originaldaten bleiben erhalten; lösche keine Website-Daten.\n当前浏览器记录版本不兼容，原数据已保留。|Browser records use an incompatible version; original data was kept.|ブラウザ記録のバージョンに互換性がありません。元のデータは残しています。|Browser-Einträge haben eine inkompatible Version; Originaldaten bleiben erhalten.\n当前浏览器记录格式异常，原数据已保留。|Browser records have an invalid format; original data was kept.|ブラウザ記録の形式が正しくありません。元のデータは残しています。|Browser-Einträge haben ein ungültiges Format; Originaldaten bleiben erhalten.\n当前浏览器记录版本号异常，原数据已保留。|The browser record revision is invalid; original data was kept.|ブラウザ記録の版番号が正しくありません。元のデータは残しています。|Die Versionsnummer der Browser-Einträge ist ungültig; Originaldaten bleiben erhalten.\n当前浏览器练习设置异常，原数据已保留。|Browser practice settings are invalid; original data was kept.|ブラウザの練習設定が正しくありません。元のデータは残しています。|Browser-Übungseinstellungen sind ungültig; Originaldaten bleiben erhalten.\n当前浏览器保存失败，变更未提交；请检查存储空间或浏览器权限后重试。|Browser save failed. Changes were not committed. Check free space or storage permissions and try again.|ブラウザへの保存に失敗し、変更は反映されていません。空き容量や保存権限を確認し、再試行してください。|Speichern fehlgeschlagen. Änderungen wurden nicht übernommen. Prüfe Speicherplatz und Berechtigungen und versuche es erneut.\n当前浏览器记录未就绪 · 仅预览|Browser data not ready · preview only|ブラウザの記録は未準備 · プレビューのみ|Browser-Daten nicht bereit · nur Vorschau\n浏览器媒体列表读取失败，未生成不完整导出。|The media list could not be read; an incomplete export was not created.|メディア一覧を読み込めなかったため、不完全な書き出しは作成していません。|Die Medienliste konnte nicht gelesen werden; kein unvollständiger Export wurde erstellt.\n手机浏览器版本不提供此管理接口。|This management feature is not available in the mobile browser edition.|スマホブラウザ版では、この管理機能を利用できません。|Diese Verwaltungsfunktion ist in der mobilen Browser-Version nicht verfügbar.\n当前浏览器记录可读 · 保存不可用|Browser records readable · saving unavailable|ブラウザ記録は閲覧可能 · 保存不可|Browser-Einträge lesbar · Speichern nicht verfügbar\n当前手机浏览器数据已就绪|Data ready in this mobile browser|このスマホのブラウザデータは準備できています|Daten in diesem mobilen Browser sind bereit\n请提供完整效果参数。|Provide all effect settings.|すべてのエフェクト設定を指定してください。|Gib alle Effekteinstellungen an.\n效果参数须为0到1。|Effect values must be between 0 and 1.|エフェクト値は0〜1の範囲で指定してください。|Effektwerte müssen zwischen 0 und 1 liegen.\n没有找到要更新的浏览器记录。|The browser record to update was not found.|更新対象のブラウザ記録が見つかりません。|Der zu aktualisierende Browser-Eintrag wurde nicht gefunden.\n最多保存100条，请先导出或删除不再使用的记录。|Up to 100 records can be saved. Export or remove unused records first.|保存できる記録は100件までです。先に書き出すか、不要な記録を削除してください。|Maximal 100 Einträge möglich. Exportiere oder entferne zuerst nicht mehr benötigte Einträge.\n没有找到要删除的浏览器记录。|The browser record to delete was not found.|削除対象のブラウザ記録が見つかりません。|Der zu löschende Browser-Eintrag wurde nicht gefunden.\n手机浏览器版本不提供后台、权利或设备管理操作。|The mobile browser edition does not provide administration, rights or device management.|スマホブラウザ版では、管理者操作、権利管理、機器管理は利用できません。|Die mobile Browser-Version bietet keine Admin-, Rechte- oder Geräteverwaltung.\n没有找到练习曲目。|Practice piece not found.|練習曲が見つかりません。|Übungsstück nicht gefunden.\n练习时长不正确。|Invalid practice duration.|練習時間が正しくありません。|Übungsdauer ungültig.\n参考成绩不正确。|Invalid reference score.|参考スコアが正しくありません。|Referenzwert ungültig.\n缺少评分版本。|Scoring version is missing.|採点バージョンがありません。|Bewertungsversion fehlt.\n练习来源不正确。|Invalid practice input source.|練習の入力元が正しくありません。|Übungsquelle ungültig.\n合成聆听不能保存演奏成绩。|Synthesised listening cannot save a playing score.|合成音の試聴では演奏スコアを保存できません。|Synthesizer-Wiedergabe kann keine Spielbewertung speichern.\n练习段落不正确。|Invalid practice passage.|練習区間が正しくありません。|Übungsabschnitt ungültig.\n练习指标格式不正确。|Invalid practice metrics format.|練習指標の形式が正しくありません。|Format der Übungswerte ungültig.\n练习指标须为0到1。|Practice metrics must be between 0 and 1.|練習指標は0〜1の範囲で指定してください。|Übungswerte müssen zwischen 0 und 1 liegen.\n请填写名称并选择有效音色。|Enter a name and choose a valid sound.|名前を入力し、有効な音色を選んでください。|Gib einen Namen ein und wähle einen gültigen Klang.\n工程名称、速度或小节数不正确。|Invalid project name, tempo or bar count.|プロジェクト名、テンポ、小節数が正しくありません。|Projektname, Tempo oder Taktzahl ungültig.\n工程最多引用4条轨道。|A project can reference up to four tracks.|プロジェクトが参照できるトラックは4本までです。|Ein Projekt kann auf höchstens vier Spuren verweisen.\n轨道引用不能为空或重复。|Track references cannot be empty or duplicated.|トラック参照は空欄・重複にできません。|Spurverweise dürfen nicht leer oder doppelt sein.\n每日目标须为1到240分钟。|The daily goal must be 1–240 minutes.|1日の目標は1〜240分で設定してください。|Das Tagesziel muss 1–240 Minuten betragen.\n学习进度格式不正确。|Invalid learning progress format.|学習進度の形式が正しくありません。|Format des Lernfortschritts ungültig.\n学习进度超过本机保存上限。|Learning progress exceeds the local storage limit.|学習進度がローカル保存の上限を超えています。|Lernfortschritt überschreitet die lokale Speichergrenze.\n练习笔记不能为空。|A practice note cannot be empty.|練習ノートを空欄にはできません。|Eine Übungsnotiz darf nicht leer sein.\n没有找到可标记的本机内容。|No local content available for this action.|操作対象のローカル内容が見つかりません。|Keine lokalen Inhalte für diese Aktion gefunden.\n没有找到反馈对应的本机内容。|The local content for this feedback was not found.|フィードバック対象のローカル内容が見つかりません。|Der lokale Inhalt zu dieser Rückmeldung wurde nicht gefunden.\n记录版本已到上限，请导出后清理。|The record revision limit was reached. Export before clearing.|記録の版番号が上限に達しました。消去前に書き出してください。|Die Versionsgrenze der Einträge ist erreicht. Exportiere vor dem Löschen.\n当前浏览器保存未就绪；请检查存储权限后刷新，音频试听仍可使用。|Browser saving is not ready. Check storage permissions and reload. Audio preview still works.|ブラウザへの保存は未準備です。保存権限を確認して再読み込みしてください。音の試聴は利用できます。|Browserspeicherung nicht bereit. Prüfe die Speicherberechtigung und lade neu. Die Klangvorschau funktioniert weiterhin.\n当前浏览器变更未提交|Changes were not saved in this browser|ブラウザの変更は保存されていません|Änderungen im Browser nicht gespeichert\n浏览器保存失败，原记录未变。|Browser save failed; previous records are unchanged.|保存に失敗しました。元の記録は変更されていません。|Speichern fehlgeschlagen; bisherige Einträge bleiben unverändert.\n速度必须为30至240 BPM|Tempo must be 30–240 BPM.|テンポは30〜240 BPMで設定してください。|Das Tempo muss 30–240 BPM betragen.\n音频引擎已关闭|The audio engine is closed.|音声エンジンは終了しています。|Die Audio-Engine ist geschlossen.\n当前浏览器不支持Web Audio|This browser does not support Web Audio.|このブラウザはWeb Audioに対応していません。|Dieser Browser unterstützt kein Web Audio.\n浏览器音频尚未运行，请再次点击启动|Browser audio has not started. Tap Start again.|ブラウザの音声はまだ開始していません。もう一度開始をタップしてください。|Browser-Audio ist noch nicht gestartet. Tippe erneut auf Start.\n音频未启动|Audio did not start.|音声を開始できませんでした。|Audio wurde nicht gestartet.\n未知浏览器合成音色|Unknown browser synthesiser sound.|不明なブラウザ合成音色です。|Unbekannter Browser-Synthesizerklang.\n音效参数必须为对象|Effect settings must be an object.|エフェクト設定の形式が正しくありません。|Effekteinstellungen müssen als Objekt vorliegen.\n未知音效参数|Unknown effect setting.|不明なエフェクト設定です。|Unbekannter Effektparameter.\n曲谱计划为空或过长|The score is empty or too long.|楽譜が空、または長すぎます。|Der Notenplan ist leer oder zu lang.\n曲谱音符时间或频率无效|Invalid note timing or frequency.|音符の時間または周波数が正しくありません。|Notenzeit oder Frequenz ungültig.\n片段超过两小时|The passage is longer than two hours.|区間が2時間を超えています。|Der Abschnitt ist länger als zwei Stunden.\n曲谱调度密度过高|Too many notes to schedule at once.|同時に処理する音符が多すぎます。|Zu viele Noten für die Zeitplanung.\n合成播放失败|Synthesiser playback failed.|合成音の再生に失敗しました。|Synthesizer-Wiedergabe fehlgeschlagen.\n拍号必须为1至12|The beat count must be 1–12.|拍数は1〜12で設定してください。|Die Schlagzahl muss 1–12 betragen.\n拍号分母须为2、4、8或16|The time-signature denominator must be 2, 4, 8 or 16.|拍子の分母は2・4・8・16にしてください。|Der Taktartnenner muss 2, 4, 8 oder 16 sein.\n节拍器未能继续播放|Metronome playback stopped unexpectedly.|メトロノームの再生を続けられませんでした。|Metronom-Wiedergabe unerwartet beendet.\n不支持的和弦名称|Unsupported chord name.|未対応の和音名です。|Akkordname nicht unterstützt.\n伴奏方式须为strum、arp或pad|Choose strum, arpeggio or sustained pad accompaniment.|伴奏はストローク・アルペジオ・持続音パッドから選んでください。|Wähle Anschlag, Arpeggio oder liegenden Klang als Begleitung.\n和弦伴奏未能继续播放|Chord accompaniment stopped unexpectedly.|和音伴奏の再生を続けられませんでした。|Akkordbegleitung unerwartet beendet.\n参考频率无效|Invalid reference frequency.|基準周波数が正しくありません。|Referenzfrequenz ungültig.\n静音状态必须为布尔值|Mute state must be on or off.|ミュートはオンまたはオフにしてください。|Der Stummschaltstatus muss ein oder aus sein.\n最多播放四轨|Up to four tracks can play.|再生できるトラックは4本までです。|Höchstens vier Spuren können abgespielt werden.\n循环轨未完成、无音频或轨号重复|A loop track is unfinished, empty, or has a duplicate track number.|ループトラックが未完了・空、またはトラック番号が重複しています。|Eine Loop-Spur ist unvollständig, leer oder hat eine doppelte Nummer.\n循环音频解码失败，未开始播放|Loop audio could not be decoded; playback did not start.|ループ音声を読み解けなかったため、再生は開始していません。|Loop-Audio konnte nicht dekodiert werden; Wiedergabe nicht gestartet.\n循环音频时长无效|Invalid loop audio duration.|ループ音声の長さが正しくありません。|Loop-Audiodauer ungültig.\n循环未启动|The loop did not start.|ループを開始できませんでした。|Loop wurde nicht gestartet.\n录音来源须为microphone或synth|Choose microphone or browser synthesis as the recording source.|録音元はマイクまたはブラウザ合成音を選んでください。|Wähle Mikrofon oder Browser-Synthese als Aufnahmequelle.\n当前浏览器不支持录音|This browser does not support audio recording.|このブラウザは録音に対応していません。|Dieser Browser unterstützt keine Audioaufnahme.\n录音请求已取消|Recording request cancelled.|録音リクエストを取り消しました。|Aufnahmeanfrage abgebrochen.\n当前浏览器不支持麦克风|This browser does not support microphone access.|このブラウザはマイク入力に対応していません。|Dieser Browser unterstützt keinen Mikrofonzugriff.\n录音未完成|Recording did not finish.|録音が完了していません。|Aufnahme nicht abgeschlossen.\n录音没有可用音频数据|No usable audio was recorded.|利用できる録音データがありません。|Keine nutzbaren Audiodaten aufgenommen.\n未开始录音|Recording did not start.|録音を開始できませんでした。|Aufnahme nicht gestartet.\n调音需要回调函数|The tuner callback is missing.|チューナーのコールバックがありません。|Stimmgerät-Rückruffunktion fehlt.\n当前环境不支持麦克风调音|Microphone tuning is not supported in this environment.|この環境ではマイク調弦に対応していません。|Diese Umgebung unterstützt kein Stimmen mit Mikrofon.\n调音请求已取消|Tuning request cancelled.|調弦リクエストを取り消しました。|Stimmanfrage abgebrochen.\n麦克风调音未启动|Microphone tuning did not start.|マイク調弦を開始できませんでした。|Stimmen mit Mikrofon nicht gestartet.\n音频不能解码，仍可下载原文件|Audio cannot be decoded, but the original file can still be downloaded.|音声を読み解けませんが、元のファイルはダウンロードできます。|Audio kann nicht dekodiert werden; die Originaldatei kann trotzdem heruntergeladen werden.\n浏览器媒体已删除。|Browser media deleted.|ブラウザ内のメディアを削除しました。|Browser-Medien gelöscht.\n当前内存媒体已移除；历史持久媒体删除未确认。|In-memory media was removed; deletion of previously stored files is unconfirmed.|メモリ内のメディアを削除しました。以前保存されたファイルの削除は未確認です。|Medien im Arbeitsspeicher entfernt; das Löschen früher gespeicherter Dateien ist unbestätigt.\n已保存到当前浏览器，请下载备份。|Saved in this browser. Download a backup.|このブラウザに保存しました。バックアップをダウンロードしてください。|In diesem Browser gespeichert. Lade eine Sicherung herunter.\n浏览器未能持久保存；目前仅在内存，请立即下载。|Persistent saving failed. This is in memory only; download it now.|永続保存に失敗しました。現在はメモリ内のみなので、すぐにダウンロードしてください。|Dauerhaftes Speichern fehlgeschlagen. Nur im Arbeitsspeicher; bitte sofort herunterladen.\n四轨按各自录制长度循环播放。|Tracks loop at their individual recorded lengths.|各トラックは、それぞれの録音長でループします。|Spuren loopen jeweils in ihrer eigenen Aufnahmelänge.\n还没有循环轨，先录一段。|No loop tracks yet. Record one first.|ループトラックはまだありません。まず録音してください。|Noch keine Loop-Spuren. Nimm zuerst eine auf.\n示范聆听已记录。继续练一句。|Listening saved. Try another phrase.|試聴を記録しました。次のフレーズを練習しましょう。|Anhören gespeichert. Übe eine weitere Phrase.\n聆听结束，记录未保存。|Listening ended; the session was not saved.|試聴は終了しましたが、記録は保存されませんでした。|Anhören beendet; die Einheit wurde nicht gespeichert.\n未取得足够可靠的单音输入，本次不生成成绩。|Not enough reliable single-note input; no score was generated.|安定した単音入力が足りないため、今回はスコアを生成しません。|Zu wenig verlässliche Einzelton-Eingabe; keine Bewertung erzeugt.\n等待麦克风权限…|Waiting for microphone permission…|マイクの許可を待っています…|Warten auf Mikrofonberechtigung…\n正在跟奏 · 等待可靠的单音输入|Playing along · waiting for a reliable single note|合わせて弾く練習中 · 安定した単音を待っています|Mitspielen · Warten auf einen verlässlichen Einzelton\n当前浏览器不支持 IndexedDB；录音仅保留在本页内存，刷新后会丢失。|IndexedDB is not supported. Recordings stay in this page's memory and will be lost on reload.|IndexedDBに対応していません。録音はこのページのメモリ内だけで、再読み込みすると失われます。|IndexedDB wird nicht unterstützt. Aufnahmen bleiben nur im Arbeitsspeicher dieser Seite und gehen beim Neuladen verloren.\n浏览器未允许本机存储；录音仅保留在本页内存，刷新后会丢失。|Local storage was blocked. Recordings are in memory only and will be lost on reload.|ローカル保存が許可されませんでした。録音はメモリ内だけで、再読み込みすると失われます。|Lokaler Speicher blockiert. Aufnahmen bleiben nur im Arbeitsspeicher und gehen beim Neuladen verloren.\n浏览器存储空间不足；录音仅保留在本页内存，请立即下载。|Browser storage is full. The recording is in memory only; download it now.|ブラウザの保存容量が不足しています。録音はメモリ内のみなので、すぐにダウンロードしてください。|Browserspeicher voll. Aufnahme nur im Arbeitsspeicher; bitte sofort herunterladen.\n无法打开本机录音库；本页录音可下载，但未确认持久保存。|Could not open the recording store. This page's recordings can be downloaded, but lasting storage is unconfirmed.|録音ライブラリを開けません。このページの録音はダウンロードできますが、永続保存は未確認です。|Aufnahmespeicher konnte nicht geöffnet werden. Aufnahmen dieser Seite lassen sich herunterladen, dauerhafte Speicherung ist jedoch unbestätigt.\n录音未提交到本机录音库；仅保留在本页内存，请下载备份。|The recording was not committed to storage. It remains in memory; download a backup.|録音は保存ライブラリに反映されていません。メモリ内にしかないため、バックアップをダウンロードしてください。|Aufnahme wurde nicht in den Speicher übernommen. Sie bleibt im Arbeitsspeicher; lade eine Sicherung herunter.\n无法读取本机录音库；当前列表可能不完整，请保留本页并重试。|Could not read the recording store. The list may be incomplete; keep this page open and retry.|録音ライブラリを読み込めません。一覧が不完全な場合があります。このページを開いたまま再試行してください。|Aufnahmespeicher konnte nicht gelesen werden. Die Liste kann unvollständig sein; lasse die Seite offen und versuche es erneut.\n浏览器存储提交失败；删除未确认，请重试。|The storage update failed. Deletion is unconfirmed; retry.|保存の更新に失敗しました。削除は未確認です。再試行してください。|Speicheraktualisierung fehlgeschlagen. Löschung unbestätigt; erneut versuchen.\n删除未提交；本机录音仍需确认删除，请重试。|Deletion was not committed. The recording may remain; retry.|削除は反映されていません。録音が残っている可能性があるため、再試行してください。|Löschung nicht übernommen. Die Aufnahme kann noch vorhanden sein; erneut versuchen.\n清空未提交；本机录音仍需确认删除，请重试。|Clearing was not committed. Recordings may remain; retry.|消去は反映されていません。録音が残っている可能性があるため、再試行してください。|Leeren nicht übernommen. Aufnahmen können noch vorhanden sein; erneut versuchen.\n录音库被其他页面占用，请关闭旧页面后刷新；本页录音尚未持久保存。|Another page is using the recording store. Close it and reload; this page's recording is not yet saved permanently.|別のページが録音ライブラリを使用しています。古いページを閉じて再読み込みしてください。このページの録音はまだ永続保存されていません。|Eine andere Seite verwendet den Aufnahmespeicher. Schließe sie und lade neu; die aktuelle Aufnahme ist noch nicht dauerhaft gespeichert.\n录音库版本已被其他页面更新；请刷新后再保存。|Another page updated the recording store. Reload before saving.|別のページで録音ライブラリが更新されました。保存前に再読み込みしてください。|Eine andere Seite hat den Aufnahmespeicher aktualisiert. Lade vor dem Speichern neu.\n录音库已关闭；本页新增录音尚未持久保存。|The recording store is closed. New recordings on this page have not been saved permanently.|録音ライブラリは閉じられています。このページで追加した録音はまだ永続保存されていません。|Aufnahmespeicher geschlossen. Neue Aufnahmen dieser Seite sind noch nicht dauerhaft gespeichert.\n无法取得浏览器容量估算；可用容量未知。|Browser storage capacity could not be estimated; free space is unknown.|ブラウザの容量を推定できません。空き容量は不明です。|Browserspeicher konnte nicht geschätzt werden; freier Platz ist unbekannt.\n部分录音仅保留在本页内存；刷新后会丢失，请下载备份。|Some recordings are in page memory only and will be lost on reload. Download a backup.|一部の録音はページのメモリ内だけで、再読み込みすると失われます。バックアップをダウンロードしてください。|Einige Aufnahmen liegen nur im Arbeitsspeicher und gehen beim Neuladen verloren. Lade eine Sicherung herunter.\n仅当前浏览器与同源地址保存；协议、主机或端口改变后不会读取到原录音。|Saved only for this browser and site origin. A different protocol, host or port will not access these recordings.|このブラウザと同一オリジンのアドレス内にのみ保存します。プロトコル・ホスト・ポートが変わると元の録音は読み込めません。|Nur für diesen Browser und Website-Ursprung gespeichert. Ein anderes Protokoll, ein anderer Host oder Port kann diese Aufnahmen nicht lesen.\n这是本机浏览器存储，不是云备份；未停止且未完成的录音不会恢复。|This is local browser storage, not a cloud backup. Unfinished recordings cannot be restored.|これはローカルのブラウザ保存であり、クラウドバックアップではありません。停止・完了していない録音は復元できません。|Dies ist lokaler Browserspeicher, keine Cloud-Sicherung. Nicht beendete Aufnahmen werden nicht wiederhergestellt.\n容量由浏览器配额决定，隐私模式、清理网站数据或浏览器回收可能删除录音。重要录音请另行下载。|Capacity depends on browser limits. Private mode, site-data cleanup or browser eviction may remove recordings. Download important recordings separately.|容量はブラウザの制限によります。プライベートモード、サイトデータの消去、ブラウザの自動整理で録音が削除される場合があります。大切な録音は別途ダウンロードしてください。|Die Kapazität hängt vom Browser ab. Privatmodus, Website-Bereinigung oder automatische Speicherfreigabe können Aufnahmen löschen. Lade wichtige Aufnahmen separat herunter.\n录音编号无效。|Invalid recording ID.|録音IDが正しくありません。|Aufnahme-ID ungültig.\n录音类别无效。|Invalid recording type.|録音の種類が正しくありません。|Aufnahmetyp ungültig.\n仅能保存已停止且完成的非空录音；需要有效编号、名称、Blob和completed:true。|Only completed, non-empty recordings can be saved. A valid ID, name, Blob and completion marker are required.|停止・完了済みで空ではない録音のみ保存できます。有効なID、名前、Blob、完了情報が必要です。|Nur abgeschlossene, nicht leere Aufnahmen lassen sich speichern. Gültige ID, Name, Blob und Abschlussmarkierung erforderlich.\nLooper轨号必须为0至3。|Loop track numbers must be 0–3.|ループのトラック番号は0〜3です。|Loop-Spurnummern müssen 0–3 sein.\n录音元数据中的数值无效。|Invalid numeric value in recording metadata.|録音情報の数値が正しくありません。|Numerischer Wert in Aufnahme-Metadaten ungültig.\n当前浏览器媒体与文字记录已清除。|This browser's media and text records were cleared.|このブラウザのメディアと文字記録を消去しました。|Medien und Texteinträge dieses Browsers gelöscht.\n浏览器文字记录已清除；媒体持久存储不可用，历史媒体删除未确认。|Text records cleared. Persistent media storage is unavailable; deletion of earlier media is unconfirmed.|文字記録を消去しました。メディアの永続保存は利用できず、以前のメディア削除は未確認です。|Texteinträge gelöscht. Dauerhafter Medienspeicher ist nicht verfügbar; das Löschen früherer Medien ist unbestätigt.\n操作没有完成，请重试。|The action did not finish. Try again.|操作は完了していません。再試行してください。|Die Aktion wurde nicht abgeschlossen. Bitte erneut versuchen.\n未命名录音|Untitled recording|名称未設定の録音|Unbenannte Aufnahme\n视频|Video|動画|Video\n下载|Download|ダウンロード|Herunterladen\n删除|Delete|削除|Löschen\n静音|Mute|ミュート|Stummschalten\n取消静音|Unmute|ミュート解除|Stummschaltung aufheben\n一闪一闪亮晶晶（小星星）|Twinkle, Twinkle, Little Star|きらきら星|Funkel, funkel, kleiner Stern\n热十字面包|Hot Cross Buns|ホット・クロス・バンズ|Hot Cross Buns\n轻轻划船|Lightly Row|軽く漕げ|Sanft rudern (Lightly Row)\n欢乐颂|Ode to Joy|喜びの歌|Ode an die Freude\nG大调小步舞曲|Minuet in G major|ト長調のメヌエット|Menuett in G-Dur\nD大调卡农|Canon in D major|ニ長調のカノン|Kanon in D-Dur\n加沃特舞曲|Gavotte|ガヴォット|Gavotte\n四季·春|Spring from The Four Seasons|「四季」より「春」|Der Frühling aus Die vier Jahreszeiten\nG大调弦乐小夜曲|Eine kleine Nachtmusik|アイネ・クライネ・ナハトムジーク|Eine kleine Nachtmusik\n致爱丽丝|Für Elise|エリーゼのために|Für Elise\n查尔达什舞曲|Csárdás|チャルダッシュ|Csárdás\n第24号随想曲|Caprice No. 24|カプリース第24番|Caprice Nr. 24\n噢！苏珊娜|Oh! Susanna|おおスザンナ|Oh! Susanna\n坎普敦赛马|Camptown Races|キャンプタウン・レース|Camptown Races\n牧场之家|Home on the Range|ホーム・オン・ザ・レンジ|Home on the Range\n扬基歌|Yankee Doodle|ヤンキー・ドゥードゥル|Yankee Doodle\n奇异恩典|Amazing Grace|アメイジング・グレイス|Amazing Grace\n斯卡布罗集市|Scarborough Fair|スカボロー・フェア|Scarborough Fair\n绿袖子|Greensleeves|グリーンスリーブス|Greensleeves\n友谊地久天长|Auld Lang Syne|蛍の光|Nehmt Abschied, Brüder\n伦敦德里小调|Londonderry Air|ロンドンデリーの歌|Londonderry Air\n樱花|Sakura Sakura|さくらさくら|Sakura Sakura\n荒城之月|The Moon over the Ruined Castle|荒城の月|Mond über der Burgruine\n海滨之歌|Song of the Seashore|浜辺の歌|Lied am Meeresstrand\n红叶|Autumn Leaves (Momiji)|紅葉（もみじ）|Herbstlaub (Momiji)\n茉莉花|Jasmine Flower (Mo Li Hua)|茉莉花（ジャスミン）|Jasminblüte (Mo Li Hua)\n紫竹调|Purple Bamboo Tune|紫竹調|Lied vom Purpurbambus\n孟姜女|Lady Meng Jiang|孟姜女|Meng Jiang\n凤阳花鼓|Fengyang Flower Drum|鳳陽花鼓|Blumentrommel von Fengyang\n沂蒙山小调|Yimeng Mountain Ditty|沂蒙山の小調|Lied aus dem Yimeng-Gebirge\n小汉斯|Little Hans (Hänschen klein)|ヘンシェン・クライン|Hänschen klein\n哦，圣诞树|O Christmas Tree|もみの木|O Tannenbaum\n两只老虎（雅克兄弟）|Brother John (Frère Jacques)|フレール・ジャック|Bruder Jakob\n阿维尼翁桥上|On the Bridge of Avignon|アヴィニョンの橋の上で|Auf der Brücke von Avignon\n我的太阳|O Sole Mio|オー・ソレ・ミオ|O Sole Mio\nAir 整琴|Air violin|Air バイオリン|Air Violine\nPro 旗舰|Pro flagship violin|Pro フラッグシップ|Pro Flaggschiff-Violine\nSV-210 加装模块|{brand} add-on module|{brand} 増設モジュール|{brand} Nachrüstmodul\n课程 / 音色订阅|Course / sound subscription|講座・音色サブスクリプション|Kurs- / Klangabonnement\n配件与服务|Accessories & service|アクセサリーとサービス|Zubehör & Service\n独立基础演奏与有线监听|Standalone playing with wired monitoring|単独演奏と有線モニタリング|Eigenständiges Spielen mit kabelgebundenem Monitoring\n高级音源、联网与扩展功能|Advanced sound engine, connectivity and extensions|高度な音源・ネット接続・拡張機能|Erweiterte Klangerzeugung, Vernetzung und Zusatzfunktionen\n适配范围待实测|Compatibility requires real-world testing|対応範囲は実機での確認待ち|Kompatibilität muss praktisch geprüft werden\n内容授权和地区支付策略待确认|Content licensing and regional payment options are not final|コンテンツの利用権と地域別決済は未確定|Inhaltslizenzen und regionale Zahlungsoptionen sind noch offen\n拾音器、线材、电池及维护|Pickups, cables, batteries and maintenance|ピックアップ・ケーブル・電池・メンテナンス|Tonabnehmer, Kabel, Batterien und Wartung\n日本古谣|Japanese traditional song|日本の伝承曲|Japanische Volksweise\n中国传统民歌|Chinese traditional song|中国の伝承曲|Chinesische Volksweise\n江南丝竹·传统|Traditional Jiangnan sizhu|江南絲竹の伝統曲|Traditionelle Jiangnan-Sizhu-Musik\n安徽传统民歌|Anhui traditional song|安徽の伝承曲|Volksweise aus Anhui\n山东传统民歌|Shandong traditional song|山東の伝承曲|Volksweise aus Shandong\n滝廉太郎|Rentaro Taki|滝廉太郎|Rentaro Taki\n成田為三|Tamezo Narita|成田為三|Tamezo Narita\n岡野貞一|Teiichi Okano|岡野貞一|Teiichi Okano";
for(const line of entries.split('\n')){const parts=line.split('|');if(parts.length===4)add(parts[0],parts[0],parts[1],parts[2],parts[3]);}
const foreign=[["PERSONAL MUSIC STUDIO","个人音乐琴房","PERSONAL MUSIC STUDIO","自分だけの音楽スタジオ","PERSÖNLICHES MUSIKSTUDIO"],["MY WORKSPACE","我的琴房","MY STUDIO","マイスタジオ","MEIN STUDIO"],["FIND YOUR NEXT MELODY","寻找下一首旋律","FIND YOUR NEXT MELODY","次の旋律を見つけよう","FINDE DEINE NÄCHSTE MELODIE"],["ONE PHRASE AT A TIME","一次练好一个乐句","ONE PHRASE AT A TIME","ひとつのフレーズから","EINE PHRASE NACH DER ANDEREN"],["CAPTURE YOUR SOUND","记录你的声音","CAPTURE YOUR SOUND","自分の音を残そう","HALTE DEINEN KLANG FEST"],["SHAPE YOUR SOUND","打造自己的音色","SHAPE YOUR SOUND","音色を作ろう","GESTALTE DEINEN KLANG"],["IN TUNE, IN TIME","调准音，跟上拍","IN TUNE, IN TIME","音程もリズムも","RICHTIG GESTIMMT, IM TAKT"],["YOUR INSTRUMENT","你的乐器","YOUR INSTRUMENT","あなたの楽器","DEIN INSTRUMENT"],["BUILD YOUR CONFIDENCE","一步步练出信心","BUILD YOUR CONFIDENCE","少しずつ自信を育てよう","GEWINNE SELBSTVERTRAUEN"],["PLAY. SHARE. CONNECT.","演奏与练习笔记","PLAY. WRITE. REFLECT.","弾く、記録する、振り返る","SPIELEN. NOTIEREN. REFLEKTIEREN."],["SMARTVIO COLLECTION","品牌产品系列","{brand} COLLECTION","{brand} 製品シリーズ","{brand} PRODUKTE"],["MAKE IT YOURS","设置为你的习惯","MAKE IT YOURS","自分らしく設定","PASSEND FÜR DICH"],["YOUR NEXT MOMENT","下一段音乐时光","YOUR NEXT MOMENT","次の音楽のひととき","DEIN NÄCHSTER MUSIKMOMENT"],["A LITTLE EVERY DAY","每天练一点","A LITTLE EVERY DAY","毎日少しずつ","JEDEN TAG EIN WENIG"],["A GOOD START","从这里起步","A GOOD START","ここから始めよう","EIN GUTER ANFANG"],["CURRENT SOUND","当前音色","CURRENT SOUND","現在の音色","AKTUELLER KLANG"],["A LITTLE CHARACTER","声音细节","SOUND DETAILS","音の細部","KLANGDETAILS"],["CHROMATIC TUNER","半音调音器","CHROMATIC TUNER","クロマチックチューナー","CHROMATISCHES STIMMGERÄT"],["SMARTVIO INSTRUMENT","你的电子小提琴","{brand} INSTRUMENT","{brand} の楽器","{brand} INSTRUMENT"],["PUT IT INTO PRACTICE","学完就练","PUT IT INTO PRACTICE","学んだら、弾こう","SETZE ES IN DIE PRAXIS UM"],["SMARTVIO PRACTICE NOTE","原创练习指导","{brand} PRACTICE GUIDE","{brand} 練習ガイド","{brand} ÜBUNGSANLEITUNG"],["Traditional","传统曲","Traditional","伝承曲","Volksweise"],["American Traditional","美国传统曲","American traditional","米国の伝承曲","Amerikanische Volksweise"],["English Traditional","英国传统曲","English traditional","英国の伝承曲","Englische Volksweise"],["Scottish Traditional","苏格兰传统曲","Scottish traditional","スコットランドの伝承曲","Schottische Volksweise"],["Irish Traditional","爱尔兰传统曲","Irish traditional","アイルランドの伝承曲","Irische Volksweise"],["Deutsches Volkslied","德国传统曲","German traditional","ドイツの伝承曲","Deutsches Volkslied"],["Chanson traditionnelle","法国传统曲","French traditional","フランスの伝承曲","Französische Volksweise"],["Beethoven","贝多芬","Beethoven","ベートーヴェン","Beethoven"],["C. Petzold (attr. Bach)","C.佩措尔德（旧归巴赫）","C. Petzold (formerly attributed to Bach)","C.ペツォールト（旧バッハ作と伝承）","C. Petzold (früher Bach zugeschrieben)"],["Pachelbel","帕赫贝尔","Pachelbel","パッヘルベル","Pachelbel"],["Gossec","戈塞克","Gossec","ゴセック","Gossec"],["Vivaldi","维瓦尔第","Vivaldi","ヴィヴァルディ","Vivaldi"],["Mozart","莫扎特","Mozart","モーツァルト","Mozart"],["Monti","蒙蒂","Monti","モンティ","Monti"],["Paganini","帕格尼尼","Paganini","パガニーニ","Paganini"],["Stephen Foster (†1864)","斯蒂芬·福斯特（1864年逝世）","Stephen Foster (d. 1864)","スティーブン・フォスター（1864年没）","Stephen Foster (†1864)"],["di Capua","迪·卡普阿","di Capua","ディ・カプア","di Capua"],["Time to play","开始演奏","Time to play","演奏を始めよう","Zeit zum Spielen"],["PLAY","演奏","PLAY","演奏","SPIELEN"],["STUDIO","琴房","STUDIO","スタジオ","STUDIO"]];
for(const row of foreign)add(...row);
add('SV-210 加装模块','SV-210 加装模块','SV-210 add-on module','SV-210 増設モジュール','SV-210 Nachrüstmodul');
add('跟随所选语言显示品牌','英国使用 VELLEN；其他地区按所选语言显示品牌。','The United Kingdom uses VELLEN; other regions follow the selected language.','英国では VELLEN、それ以外の地域では選択した言語に応じたブランドを表示します。','Im Vereinigten Königreich gilt VELLEN; in anderen Regionen folgt die Marke der gewählten Sprache.');

for(const row of [
 ['日','日','Sun','日','So'],['一','一','Mon','月','Mo'],['二','二','Tue','火','Di'],['三','三','Wed','水','Mi'],['四','四','Thu','木','Do'],['五','五','Fri','金','Fr'],['六','六','Sat','土','Sa'],
 ['SmartVio Studio · V12','{brand} 琴房 · V12','{brand} Studio · V12','{brand} スタジオ · V12','{brand} Studio · V12']
])add(...row);
for(const row of [
 ['取消','取消','Cancel','キャンセル','Abbrechen'],
 ['YOUR MUSIC, YOUR WAY','你的音乐，你的方式','YOUR MUSIC, YOUR WAY','自分らしく、音楽を','Deine Musik, dein Weg'],
 ['选择国家与界面语言','选择国家与界面语言','Choose country and interface language','国と表示言語を選択','Land und Anzeigesprache wählen'],
 ['设备与输入路由','设备与输入路由','Instrument and input routing','楽器と入力経路','Instrument und Eingangswege'],
 ['我的版本','我的版本','My version','マイバージョン','Meine Version'],
 ['我的旋律','我的旋律','My melody','自分の旋律','Meine Melodie'],
 ['小节','小节','bars','小節','Takte'],
 ['四种语言覆盖页面、操作提示与帮助。国家决定默认语言，你也可以单独更改语言。','四种语言覆盖页面、操作提示与帮助。国家决定默认语言，你也可以单独更改语言。','Pages, prompts and help are available in four languages. Your country sets the default; you can change the language separately.','ページ・操作案内・ヘルプを4言語で表示します。国に応じて初期言語を設定しますが、言語は個別に変更できます。','Seiten, Hinweise und Hilfe sind in vier Sprachen verfügbar. Das Land legt die Standardsprache fest; du kannst sie separat ändern.'],
 ['不能保存国家选择；本次仅在当前页面使用，请检查浏览器存储权限。','不能保存国家选择；本次仅在当前页面使用，请检查浏览器存储权限。','Could not save your country selection. It applies to this page only; check browser storage permissions.','国の選択を保存できません。今回はこのページ内だけに反映されます。ブラウザの保存権限を確認してください。','Die Länderauswahl konnte nicht gespeichert werden. Sie gilt nur auf dieser Seite; prüfe die Speicherberechtigung.'],
 ['将删除当前浏览器的练习、笔记、工程、预设和媒体库。JSON不含录音文件或私有笔记、反馈，请先分别备份需要保留的内容。','将删除当前浏览器的练习、笔记、工程、预设和媒体库。JSON不含录音文件或私有笔记、反馈，请先分别备份需要保留的内容。','This clears practice, notes, projects, presets and media in this browser. JSON does not include recording files, private notes or feedback. Back up anything you need separately first.','このブラウザの練習、ノート、プロジェクト、プリセット、メディアを消去します。JSONには録音ファイル、個人ノート、フィードバックは含まれません。必要なものを先に個別保存してください。','Dies löscht Übungen, Notizen, Projekte, Presets und Medien in diesem Browser. JSON enthält keine Aufnahmedateien, privaten Notizen oder Rückmeldungen. Sichere benötigte Inhalte zuerst separat.'],
 ['练习、调音、音色与录音创作。','练习、调音、音色与录音创作。','Practice, tuning, sounds and recording.','練習、調弦、音色、録音・制作。','Üben, Stimmen, Klänge und Aufnahme.'],
 ['预览','预览','Preview','プレビュー','Vorschau'],
 ['下载备份','下载备份','Download a backup','バックアップをダウンロード','Sicherung herunterladen'],
 ['时长秒','时长秒','Duration (seconds)','時間（秒）','Dauer (Sekunden)'],
 ['Invalid tuning','调弦设置无效','Invalid tuning settings','調弦設定が正しくありません','Stimmeinstellungen ungültig'],
 ['Invalid score timebase','谱面时间基准无效','Invalid score timebase','楽譜の時間基準が正しくありません','Zeitbasis der Noten ungültig'],
 ['Empty melody','旋律为空','The melody is empty','旋律が空です','Die Melodie ist leer'],
 ['Invalid BPM','速度无效','Invalid tempo','テンポが正しくありません','Tempo ungültig'],
 ['Invalid pitch','音高无效','Invalid pitch','音高が正しくありません','Tonhöhe ungültig'],
 ['Invalid melody token','音符格式无效','Invalid note format','音符の形式が正しくありません','Notenformat ungültig'],
 ['Invalid note duration','音符时长无效','Invalid note duration','音符の長さが正しくありません','Notendauer ungültig']
])add(...row);
// Community has its own authenticated cloud records; musical media remains device-local.
for(const row of [
 ['社区','社区','Community','コミュニティ','Community'],
 ['练习留在本机 · 社区联网','练习留在本机 · 社区联网','Practice on this device · community online','端末内の練習・オンラインのコミュニティ','Übungen lokal · Community online'],
 ['本机练习 · 云端社区','本机练习 · 云端社区','Local practice · cloud community','端末内の練習・クラウドのコミュニティ','Lokale Übungen · Cloud-Community'],
 ['练习与音频留本机 · 社区云端保存 · 设备待接入','练习与音频留本机 · 社区云端保存 · 设备待接入','Practice and audio local · community in the cloud · instrument integration pending','練習と音声は端末内・コミュニティはクラウド・楽器連携は準備中','Übungen und Audio lokal · Community in der Cloud · Instrumentenanbindung ausstehend'],
 ['社区暂不可用','社区暂不可用','Community is temporarily unavailable','コミュニティは一時的に利用できません','Community vorübergehend nicht verfügbar'],
 ['请联网刷新页面后重试，练习与调音仍可使用。','请联网刷新页面后重试，练习与调音仍可使用。','Reconnect and reload. Practice and tuning remain available.','オンラインで再読み込みしてください。練習と調弦は利用できます。','Verbinde dich und lade neu. Üben und Stimmen bleiben verfügbar.'],
 ['PLAY. SHARE. CONNECT.','演奏与分享','PLAY. SHARE. CONNECT.','演奏と共有','SPIELEN UND TEILEN'],
 ['保留当前完整功能，社区发布需要联网登录。','保留当前完整功能，社区发布需要联网登录。','Use the full feature set. Community posting needs an online sign-in.','すべての機能を利用できます。コミュニティへの投稿にはオンラインでのログインが必要です。','Alle Funktionen nutzen. Community-Beiträge benötigen eine Online-Anmeldung.'],
 ['练习备份 / 原生 App','练习备份 / 原生 App','Practice backup / native app','練習バックアップ・ネイティブアプリ','Übungssicherung / native App'],
 ['练习与音频仍在本机；社区内容单独保存云端。','练习与音频仍在本机；社区内容单独保存云端。','Practice and audio stay on this device. Community content is stored separately in the cloud.','練習と音声は端末内に保存されます。コミュニティ内容は別途クラウドに保存されます。','Übungen und Audio bleiben lokal. Community-Inhalte werden separat in der Cloud gespeichert.']
])add(...row);
for(const row of [
  [
    "调音器",
    "调音器",
    "Tuner",
    "チューナー",
    "Stimmgerät"
  ],
  [
    "节拍器",
    "节拍器",
    "Metronome",
    "メトロノーム",
    "Metronom"
  ],
  [
    "首页调音器",
    "首页调音器",
    "Home tuner",
    "ホームのチューナー",
    "Stimmgerät auf der Startseite"
  ],
  [
    "先调音，再开始练习。",
    "先调音，再开始练习。",
    "Tune first, then start practising.",
    "まず調弦してから、練習を始めましょう。",
    "Erst stimmen, dann üben."
  ],
  [
    "四根空弦参考音与麦克风音准检测。",
    "四根空弦参考音与麦克风音准检测。",
    "Reference tones for all four open strings and microphone pitch detection.",
    "4本の開放弦の基準音と、マイクによる音程検出。",
    "Referenztöne für alle vier leeren Saiten und Tonhöhenerkennung per Mikrofon."
  ],
  [
    "打开调音器",
    "打开调音器",
    "Open tuner",
    "チューナーを開く",
    "Stimmgerät öffnen"
  ],
  [
    "节拍与速度独立设置。",
    "节拍与速度独立设置。",
    "Set the time signature and tempo separately.",
    "拍子とテンポを個別に設定できます。",
    "Taktart und Tempo getrennt einstellen."
  ],
  [
    "使用模式",
    "使用模式",
    "Usage mode",
    "使用モード",
    "Nutzungsmodus"
  ],
  [
    "当前模式",
    "当前模式",
    "Current mode",
    "現在のモード",
    "Aktueller Modus"
  ],
  [
    "离线免注册",
    "离线免注册",
    "Offline, no account required",
    "登録不要のオフラインモード",
    "Offline, ohne Registrierung"
  ],
  [
    "保留当前完整功能，在浏览器保存记录。",
    "保留当前完整功能，在浏览器保存记录。",
    "Keep the current feature set and save records in this browser.",
    "現在の機能をそのまま使い、記録をこのブラウザに保存します。",
    "Alle aktuellen Funktionen nutzen und Aufzeichnungen in diesem Browser speichern."
  ],
  [
    "无需注册。下载离线资源后，可断网使用调音、练习和录音。",
    "无需注册。下载离线资源后，可断网使用调音、练习和录音。",
    "No account required. Download the offline resources to tune, practise and record without an internet connection.",
    "登録は不要です。オフライン用データをダウンロードすると、通信なしで調弦・練習・録音ができます。",
    "Keine Registrierung erforderlich. Lade die Offline-Ressourcen herunter, um ohne Internet zu stimmen, zu üben und aufzunehmen."
  ],
  [
    "离线资源",
    "离线资源",
    "Offline resources",
    "オフライン用データ",
    "Offline-Ressourcen"
  ],
  [
    "准备离线资源",
    "准备离线资源",
    "Prepare offline resources",
    "オフライン用データを準備",
    "Offline-Ressourcen vorbereiten"
  ],
  [
    "重新准备离线资源",
    "重新准备离线资源",
    "Prepare offline resources again",
    "オフライン用データを再準備",
    "Offline-Ressourcen erneut vorbereiten"
  ],
  [
    "正在下载离线资源…",
    "正在下载离线资源…",
    "Downloading offline resources…",
    "オフライン用データをダウンロード中…",
    "Offline-Ressourcen werden heruntergeladen…"
  ],
  [
    "离线资源已就绪",
    "离线资源已就绪",
    "Offline resources are ready",
    "オフライン用データの準備完了",
    "Offline-Ressourcen sind bereit"
  ],
  [
    "离线资源尚未就绪",
    "离线资源尚未就绪",
    "Offline resources are not ready yet",
    "オフライン用データはまだ準備できていません",
    "Offline-Ressourcen sind noch nicht bereit"
  ],
  [
    "此浏览器暂不支持离线缓存。",
    "此浏览器暂不支持离线缓存。",
    "This browser does not currently support offline caching.",
    "このブラウザは現在、オフラインキャッシュに対応していません。",
    "Dieser Browser unterstützt derzeit keinen Offline-Cache."
  ],
  [
    "首次下载需要联网；录音和麦克风仍需要浏览器授权。",
    "首次下载需要联网；录音和麦克风仍需要浏览器授权。",
    "The first download requires internet access. Recording and microphone access still require browser permission.",
    "初回ダウンロードには通信が必要です。録音とマイクの使用には、引き続きブラウザの許可が必要です。",
    "Der erste Download erfordert Internet. Aufnahme und Mikrofonzugriff benötigen weiterhin die Erlaubnis des Browsers."
  ],
  [
    "离线缓存准备失败，请联网后重试。",
    "离线缓存准备失败，请联网后重试。",
    "Could not prepare the offline cache. Connect to the internet and try again.",
    "オフラインキャッシュを準備できませんでした。通信を確認して、再試行してください。",
    "Der Offline-Cache konnte nicht vorbereitet werden. Stelle eine Internetverbindung her und versuche es erneut."
  ],
  [
    "离线使用图文教学",
    "离线使用图文教学",
    "Illustrated guide to offline use",
    "オフライン利用の図解ガイド",
    "Bildanleitung zur Offline-Nutzung"
  ],
  [
    "图文使用教学",
    "图文使用教学",
    "Illustrated usage guide",
    "図解ガイド",
    "Bildanleitung zur Nutzung"
  ],
  [
    "重新查看教学",
    "重新查看教学",
    "View the guide again",
    "ガイドをもう一度見る",
    "Anleitung erneut ansehen"
  ],
  [
    "下次进入显示教学",
    "下次进入显示教学",
    "Show the guide next time",
    "次回もガイドを表示",
    "Anleitung beim nächsten Besuch zeigen"
  ],
  [
    "教学已完成",
    "教学已完成",
    "Guide completed",
    "ガイド完了",
    "Anleitung abgeschlossen"
  ],
  [
    "教学已跳过，可在设置中重新查看。",
    "教学已跳过，可在设置中重新查看。",
    "Guide skipped. You can view it again in settings.",
    "ガイドをスキップしました。設定からもう一度確認できます。",
    "Anleitung übersprungen. Du kannst sie in den Einstellungen erneut ansehen."
  ],
  [
    "离线模式已启用。",
    "离线模式已启用。",
    "Offline mode enabled.",
    "オフラインモードを有効にしました。",
    "Offline-Modus aktiviert."
  ],
  [
    "当前模式已启用。",
    "当前模式已启用。",
    "Current mode enabled.",
    "現在のモードを有効にしました。",
    "Aktueller Modus aktiviert."
  ],
  [
    "当前模式与离线模式共用本机记录，切换不会清空。",
    "当前模式与离线模式共用本机记录，切换不会清空。",
    "Current and offline modes share this browser’s records. Switching modes does not clear them.",
    "現在のモードとオフラインモードは、このブラウザの記録を共有します。切り替えても記録は消えません。",
    "Aktueller Modus und Offline-Modus verwenden dieselben lokalen Browserdaten. Beim Wechsel werden sie nicht gelöscht."
  ],
  [
    "查看使用模式",
    "查看使用模式",
    "View usage modes",
    "使用モードを確認",
    "Nutzungsmodi ansehen"
  ],
  [
    "在线",
    "在线",
    "Online",
    "オンライン",
    "Online"
  ],
  [
    "当前已断网",
    "当前已断网",
    "Currently offline",
    "現在オフラインです",
    "Derzeit ohne Internet"
  ],
  [
    "调音器只在点击开始后申请麦克风权限。",
    "调音器只在点击开始后申请麦克风权限。",
    "The tuner requests microphone permission only when you tap Start.",
    "チューナーは開始を押したときだけ、マイクの許可を求めます。",
    "Das Stimmgerät fragt erst nach einem Tipp auf Start nach der Mikrofonberechtigung."
  ],
  [
    "浏览器暂不允许保存模式与教学设置。",
    "浏览器暂不允许保存模式与教学设置。",
    "The browser does not currently allow mode and guide settings to be saved.",
    "現在、このブラウザではモードとガイドの設定を保存できません。",
    "Der Browser erlaubt derzeit nicht, Modus- und Anleitungseinstellungen zu speichern."
  ],
  [
    "设置图文引导与使用模式。",
    "设置图文引导与使用模式。",
    "Set up the illustrated guide and usage mode.",
    "図解ガイドと使用モードを設定します。",
    "Bildanleitung und Nutzungsmodus einstellen."
  ],
  [
    "请先停止并保存录制，再切换模式或查看教学。",
    "请先停止并保存录制，再切换模式或查看教学。",
    "Stop and save your recording before switching modes or viewing the guide.",
    "録音を停止して保存してから、モードの切り替えやガイドの確認をしてください。",
    "Beende und speichere die Aufnahme, bevor du den Modus wechselst oder die Anleitung ansiehst."
  ]
])add(...row);
add('YOUR WAY TO PLAY','你的演奏方式','YOUR WAY TO PLAY','自分に合う演奏スタイル','DEIN WEG ZUM SPIELEN');
add("TUNE YOUR STRINGS","调准每一根弦","TUNE YOUR STRINGS","一本ずつ調弦","STIMME DEINE SAITEN");
add("KEEP YOUR TIME","保持节奏","KEEP YOUR TIME","リズムを保とう","HALTE DEINEN TAKT");
const rules=[];
function rule(pattern,en,ja,de,make){rules.push({pattern,en,ja,de,make});}
function count(n,one,many){return Number(n)===1?one:many;}
rule(/^([+-]?\d+(?:\.\d+)?) 半音$/,'{n} {unit}','{n} 半音','{n} {unit}',m=>({n:m[1],unit:language==='de'?count(Math.abs(Number(m[1])),'Halbton','Halbtöne'):count(Math.abs(Number(m[1])),'semitone','semitones')}));
rule(/^([\d.]+) 分钟$/,'{n} {unit}','{n} 分','{n} Min.',m=>({n:m[1],unit:count(m[1],'minute','minutes')}));
rule(/^\/ ([\d.]+) 分钟$/,'/ {n} min','/ {n} 分','/ {n} Min.',m=>({n:m[1]}));
rule(/^(\d+) 次跟奏$/,'{n} microphone {unit}','マイク練習 {n} 回','{n} {unit} mit Mikrofon',m=>({n:m[1],unit:language==='de'?count(m[1],'Übung','Übungen'):count(m[1],'session','sessions')}));
rule(/^(\d+) 次聆听$/,'{n} listening {unit}','試聴 {n} 回','{n} {unit}',m=>({n:m[1],unit:language==='de'?count(m[1],'Höreinheit','Höreinheiten'):count(m[1],'session','sessions')}));
rule(/^(\d+) 次练习$/,'{n} practice {unit}','練習 {n} 回','{n} {unit}',m=>({n:m[1],unit:language==='de'?count(m[1],'Übungseinheit','Übungseinheiten'):count(m[1],'session','sessions')}));
rule(/^(\d+) 个$/,'{n} {unit}','{n} 件','{n} {unit}',m=>({n:m[1],unit:language==='de'?count(m[1],'Projekt','Projekte'):count(m[1],'project','projects')}));
rule(/^(\d+) 段$/,'{n} {unit}','{n} 件','{n} {unit}',m=>({n:m[1],unit:language==='de'?count(m[1],'Aufnahme','Aufnahmen'):count(m[1],'recording','recordings')}));
rule(/^(\d+) 段本机媒体$/,'{n} local media {unit}','ブラウザ内メディア {n} 件','{n} lokale {unit}',m=>({n:m[1],unit:language==='de'?count(m[1],'Mediendatei','Mediendateien'):count(m[1],'file','files')}));
rule(/^(\d+) 小节$/,'{n} {unit}','{n} 小節','{n} {unit}',m=>({n:m[1],unit:language==='de'?count(m[1],'Takt','Takte'):count(m[1],'bar','bars')}));
rule(/^(\d+(?:\.\d+)?) 拍$/,'{n} {unit}','{n} 拍','{n} {unit}',m=>({n:m[1],unit:language==='de'?count(m[1],'Schlag','Schläge'):count(m[1],'beat','beats')}));
rule(/^(\d+) 轨$/,'{n} {unit}','{n} トラック','{n} {unit}',m=>({n:m[1],unit:language==='de'?count(m[1],'Spur','Spuren'):count(m[1],'track','tracks')}));
rule(/^轨道 (\d+)$/,'Track {n}','トラック {n}','Spur {n}',m=>({n:m[1]}));
rule(/^已完成 (\d+) \/ (\d+)$/,'{n} / {total} complete','{n} / {total} 完了','{n} von {total} abgeschlossen',m=>({n:m[1],total:m[2]}));
rule(/^(\d+) 条媒体缺失$/,'{n} media {unit} missing','メディア {n} 件が見つかりません','{n} {unit} fehlen',m=>({n:m[1],unit:language==='de'?count(m[1],'Mediendatei','Mediendateien'):count(m[1],'file','files')}));
rule(/^([\d.]+)% 音高覆盖$/,'{n}% pitch coverage','音高カバー率 {n}%','{n} % Tonhöhenabdeckung',m=>({n:m[1]}));
rule(/^(\d+)–(\d+) 小节(?: · 重复聆听)?$/,'Bars {a}–{b}{repeat}','{a}〜{b} 小節{repeat}','Takte {a}–{b}{repeat}',m=>({a:m[1],b:m[2],repeat:m[0].includes('重复')?(language==='ja'?' · 繰り返し':language==='de'?' · Wiederholen':' · Repeat'):''}));
rule(/^准备好了，从第 (\d+) 小节开始。$/,'Ready. Start from bar {n}.','準備完了。{n}小節目から始めましょう。','Bereit. Beginne bei Takt {n}.',m=>({n:m[1]}));
rule(/^本段音高覆盖 (\d+)% · 有效输入 (\d+)% · 参考结果$/,'Pitch coverage {n}% · reliable input {valid}% · practice result','音高カバー率 {n}% · 有効入力 {valid}% · 参考結果','Tonhöhenabdeckung {n} % · gültige Eingabe {valid} % · Übungsergebnis',m=>({n:m[1],valid:m[2]}));
rule(/^正在跟奏 · (.+) · ([+-]?\d+) 音分$/,'Playing along · {note} · {cents} cents','合わせて弾く練習中 · {note} · {cents} セント','Mitspielen · {note} · {cents} Cent',m=>({note:m[1],cents:m[2]}));
rule(/^([\d.]+) Hz · ([+-]?\d+) 音分$/,'{hz} Hz · {cents} cents','{hz} Hz · {cents} セント','{hz} Hz · {cents} Cent',m=>({hz:m[1],cents:m[2]}));
rule(/^检测到 (\d+) 个实际 MIDI 端口。$/,'Found {n} real MIDI {unit}.','実際のMIDIポートが{n}個見つかりました。','{n} echte MIDI-{unit} gefunden.',m=>({n:m[1],unit:language==='de'?count(m[1],'Anschluss','Anschlüsse'):count(m[1],'port','ports')}));
rule(/^(\d+) 个端口$/,'{n} {unit}','{n} ポート','{n} {unit}',m=>({n:m[1],unit:language==='de'?count(m[1],'Anschluss','Anschlüsse'):count(m[1],'port','ports')}));
rule(/^(\d+) 首 · (.+)候选曲库 · 谱本权利待核验，当前用于本地开发演示$/,'{n} draft pieces · {region} · Rights not verified; local development preview only.','確認待ち {n} 曲 · {region} · 権利は未確認。ローカル開発用の表示です。','{n} Notenentwürfe · {region} · Rechte ungeprüft; nur lokale Entwicklungsvorschau.',m=>({n:m[1],region:text(m[2],language,market)}));
rule(/^● 正在录制 (\d+:\d+) · (.+)，点击停止保存。$/,'● Recording {time} · {source}. Tap Stop to save.','● 録音中 {time} · {source}。停止すると保存されます。','● Aufnahme {time} · {source}. Zum Speichern Stopp drücken.',m=>({time:m[1],source:text(m[2],language,market)}));
rule(/^正在示范聆听 · (\d+)–(\d+) 小节 · (循环|单次)$/,'Demo playback · bars {a}–{b} · {mode}','お手本再生中 · {a}〜{b}小節 · {mode}','Demo-Wiedergabe · Takte {a}–{b} · {mode}',m=>({a:m[1],b:m[2],mode:text(m[3],language,market)}));
rule(/^(.+)，(\d+)小节，([\d/]+)拍五线谱$/,'{title}, {bars} bars, {meter} staff notation','{title}、{bars}小節、{meter}拍子の五線譜','{title}, {bars} Takte, Notenschrift im {meter}-Takt',m=>({title:m[1],bars:m[2],meter:m[3]}));
rule(/^(.+) · ([\d/]+) 拍 · (\d+) 小节$/,'{author} · {meter} time · {bars} bars','{author} · {meter}拍子 · {bars}小節','{author} · {meter}-Takt · {bars} Takte',m=>({author:m[1],meter:m[2],bars:m[3]}));
for(const [verb,en,ja,de] of [
 ['录制','Record track {n}','トラック{n}を録音','Spur {n} aufnehmen'],
 ['停止','Stop track {n}','トラック{n}を停止','Spur {n} stoppen'],
 ['清空','Clear track {n}','トラック{n}を消去','Spur {n} leeren'],
 ['下载','Download track {n}','トラック{n}をダウンロード','Spur {n} herunterladen'],
 ['静音','Mute track {n}','トラック{n}をミュート','Spur {n} stummschalten'],
 ['取消静音','Unmute track {n}','トラック{n}のミュートを解除','Spur {n} wieder hörbar machen']
])rule(new RegExp('^'+verb+'轨道 (\\d+)$'),en,ja,de,m=>({n:m[1]}));
rule(/^轨道 (\d+) 音量$/,'Track {n} volume','トラック{n}の音量','Lautstärke von Spur {n}',m=>({n:m[1]}));
rule(/^共\s*(\d+)\s*小节$/,'{n} bars in total','全{n}小節','Insgesamt {n} Takte',m=>({n:m[1]}));
rule(/^([\d/]+)\s*拍$/,'{meter} time','{meter}拍子','{meter}-Takt',m=>({meter:m[1]}));
rule(/^(\d+)\.\s*(.+)$/,'{n}. {title}','{n}. {title}','{n}. {title}',m=>({n:m[1],title:text(m[2],language,market)}));
rule(/^·\s*(.+)$/,'· {rest}','· {rest}','· {rest}',m=>({rest:text(m[1],language,market)}));
rule(/^(.+)概念外观$/,'{name} concept design','{name}のコンセプト外観','{name} Designkonzept',m=>({name:text(m[1],language,market)}));
rule(/^(.+) · 当前效果参数一起保存$/,'{name} · effect settings are included','{name} · 現在のエフェクト設定も保存','{name} · Effekteinstellungen werden mitgespeichert',m=>({name:m[1]}));
rule(/^(\d+) · 赞$/,'{n} likes','いいね {n} 件','{n} Gefällt-mir-Angaben',m=>({n:m[1]}));
for(const [verb,en,ja,de] of [
 ['收藏','Add {name} to favourites','{name}をお気に入りに登録','{name} als Favorit speichern'],
 ['取消收藏','Remove {name} from favourites','{name}のお気に入りを解除','{name} aus Favoriten entfernen'],
 ['练习','Practise {name}','{name}を練習','{name} üben'],
 ['删除','Delete {name}','{name}を削除','{name} löschen'],
 ['下载','Download {name}','{name}をダウンロード','{name} herunterladen'],
 ['删除工程','Delete project {name}','プロジェクト{name}を削除','Projekt {name} löschen'],
 ['标记完成','Mark {name} complete','{name}を完了にする','{name} als abgeschlossen markieren'],
 ['取消完成','Mark {name} incomplete','{name}の完了を解除','Abschluss von {name} zurücknehmen']
])rule(new RegExp('^'+verb+' (.+)$'),en,ja,de,m=>({name:['标记完成','取消完成'].includes(verb)?text(m[1],language,market):m[1]}));
function interpolate(template,values,lang,region){
  // Only controlled UI templates change brand; substituted user values stay intact.
  return template.replace(/\bSmartVio\b/g,brand(lang,region)).replace(/\{(\w+)\}/g,(_,key)=>key==='brand'?brand(lang,region):String(values[key]??''));
}
function canonical(value){return dictionary.has(value)?value:(aliases.get(value)?.source||renderedSources.get(value)||value);}
function remember(output,source){if(output!==source){renderedSources.set(output,source);if(renderedSources.size>2000)renderedSources.delete(renderedSources.keys().next().value);}}
function localize(source,lang,region){
  const entry=dictionary.get(source)||aliases.get(source);
  if(entry)return interpolate(entry[lang]||entry.zh,{},lang,region);
  if(lang==='zh')return source.replace(/\bSmartVio\b/g,brand(lang,region));
  for(const item of rules){
    const m=source.match(item.pattern);if(!m)continue;
    const oldLanguage=language,oldMarket=market;language=lang;market=region;let values;
    try{values=item.make(m);}finally{language=oldLanguage;market=oldMarket;}
    return interpolate(item[lang],values,lang,region);
  }
  // Metadata uses a deliberate separator; translate complete segments, not words.
  if(source.includes(' · ')){
    const parts=source.split(' · '),translated=[];
    for(let i=0;i<parts.length;){
      let end=i+1;
      for(let j=parts.length;j>i+1;j--){const phrase=parts.slice(i,j).join(' · ');if(dictionary.has(phrase)||aliases.has(phrase)){end=j;break;}}
      translated.push(text(parts.slice(i,end).join(' · '),lang,region));i=end;
    }
    return translated.join(' · ');
  }
  const detail=source.match(/^([^：:]+)[：:](.+)$/s);
  if(detail&&(dictionary.has(detail[1])||aliases.has(detail[1])))return text(detail[1],lang,region)+': '+detail[2].trim();
  return source.replace(/\bSmartVio\b/g,brand(lang,region));
}
function text(value,requested=language,requestedMarket=market){
  if(value===null||value===undefined)return '';
  const raw=String(value),lang=normalize(requested),region=normalizeMarket(requestedMarket);
  // File names are user data, not UI labels.
  if(/\.(?:webm|mp4|wav|ogg|mp3|json|csv)$/i.test(raw.trim()))return raw;
  const match=raw.match(/^(\s*)([\s\S]*?)(\s*)$/),core=match[2];
  if(!core)return raw;
  const source=canonical(core),output=localize(source,lang,region);remember(output,source);
  return match[1]+output+match[3];
}
function isIgnored(element,forText){
  if(!element||element.nodeType!==1)return false;
  if(element.closest?.(ignored))return true;
  return !!(forText&&element.closest?.('svg,input,textarea'));
}
function translateNode(node){
  if(node.nodeType!==3||isIgnored(node.parentElement,true))return;
  const current=node.nodeValue;if(!current||!current.trim())return;
  let record=originalText.get(node);
  if(!record||current!==record.last){record={source:canonical(current.trim()),prefix:current.match(/^\s*/)[0],suffix:current.match(/\s*$/)[0],last:current};originalText.set(node,record);}
  const next=record.prefix+text(record.source,language,market)+record.suffix;
  if(current!==next)node.nodeValue=next;record.last=next;
}
const attrs=['aria-label','aria-description','placeholder','title','alt','label'];
function translateAttributes(element){
  if(isIgnored(element,false))return;
  let record=originalAttributes.get(element);if(!record){record=new Map();originalAttributes.set(element,record);}
  for(const name of attrs){
    if(!element.hasAttribute?.(name))continue;
    const current=element.getAttribute(name);let entry=record.get(name);
    if(!entry||current!==entry.last){entry={source:canonical(current),last:current};record.set(name,entry);}
    const next=text(entry.source,language,market);if(next!==current)element.setAttribute(name,next);entry.last=next;
  }
}
function translate(target=root.document){
  if(!target)return target;
  if(target.nodeType===3){translateNode(target);return target;}
  const doc=target.ownerDocument||(target.nodeType===9?target:root.document);
  if(target.nodeType===1)translateAttributes(target);
  if(doc?.createTreeWalker){const walker=doc.createTreeWalker(target,4);let node;while((node=walker.nextNode()))translateNode(node);}
  for(const element of target.querySelectorAll?.('[aria-label],[aria-description],[placeholder],[title],[alt],[label]')||[])translateAttributes(element);
  return target;
}
function observe(){
  if(observer||!root.MutationObserver||!root.document?.body)return;
  observer=new root.MutationObserver(records=>{
    if(queued)return;queued=true;
    const run=()=>{queued=false;translate(root.document.body);};
    if(root.queueMicrotask)root.queueMicrotask(run);else Promise.resolve().then(run);
  });
  observer.observe(root.document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:attrs});
}
function setLanguage(value,region){
  // Validate both before changing committed context; a welcome draft uses text(), not this setter.
  const nextLanguage=normalize(value),nextMarket=region===undefined?market:normalizeMarket(region);
  language=nextLanguage;market=nextMarket;
  if(root.document?.documentElement)root.document.documentElement.lang={zh:'zh-CN',en:'en',ja:'ja',de:'de'}[language];
  translate(root.document);observe();return language;
}
function getLanguage(){return language;}
add('照片入门','照片入门','Photo introduction','写真で入門','Einstieg mit Fotos');
function getMarket(){return market;}
root.SVLocale={text,translate,setLanguage,getLanguage,getMarket,normalizeMarket,brand,t:text,T:text,apply:translate,observe,languages:Object.freeze(supported.slice()),markets:Object.freeze(markets.slice()),dictionarySize:dictionary.size};
if(root.document?.readyState==='loading')root.document.addEventListener('DOMContentLoaded',()=>{observe();translate(root.document);},{once:true});else{observe();translate(root.document);}
})(typeof window!=='undefined'?window:globalThis);

