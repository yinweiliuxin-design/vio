(function (global) {
  'use strict';
  if (global.SVTutorial) return;

  const copy = {
    zh: {
      tutorial: '新手图文教学', skip: '跳过教程', back: '上一步', next: '下一步',
      progress: (n, total) => `第 ${n} / ${total} 步`,
      goTuner: '开始调音', goHome: '返回首页', replay: '之后可在设置中重看教程。',
      illustration: '按钮示意 · 不会开启麦克风或连接设备',
      steps: [
        { title: '先找到调音器', lead: '从首页调音器开始，一次只拉一根空弦。',
          items: [['进入调音器', '在首页点“打开调音器”。'], ['听参考音', '点 G / D / A / E 弦按钮，听对应参考音。'], ['开始检测', '点“开始麦克风调音”后，按浏览器提示允许麦克风。']],
          note: '麦克风只在你点检测后申请。教程中的 A4 / 440 Hz 是示意，实琴检测还需校准。',
          labels: ['打开调音器', '参考音', '开始麦克风调音'] },
        { title: '找到一首喜欢的曲子', lead: '曲库可以搜索、收藏，再进入练习。',
          items: [['搜索曲目', '在曲库输入曲名或作者，也可以按分类浏览。'], ['收藏曲目', '点爱心；之后到“我的收藏”快速找到。'], ['开始练习', '点曲目旁的“练习”，打开谱面。']],
          note: '收藏保存在当前浏览器。曲库为开发候选谱本，正式使用前仍需核验谱本权利。',
          labels: ['搜索曲名或作者', '我的收藏', '练习'] },
        { title: '先听，再慢慢练', lead: '把速度放慢，用 A–B 小节反复练一个短句。',
          items: [['示范聆听', '点“示范聆听”，先熟悉旋律，不需要麦克风。'], ['调整速度和片段', '展开“练习设置”，调整速度、起始和结束小节，勾选重复聆听。'], ['跟奏练习', '准备好后点“跟奏练习”；只有这时才申请麦克风。']],
          note: '聆听不会生成演奏成绩。跟奏结果是单音检测参考，没有可靠输入时不生成成绩。',
          labels: ['示范聆听', '速度', '从', '到', '跟奏练习'] },
        { title: '录下来，停止后保存', lead: '在录音创作页选择来源，留下一个乐句。',
          items: [['选择录制来源', '“浏览器合成”不申请麦克风；“真实麦克风”需要你的授权。'], ['录音与停止', '点“录音”，结束后点“停止并保存”，等待保存结果。'], ['回听和下载', '在“我的录音与视频”回听，点下载按钮另存文件。']],
          note: '录音留在当前浏览器和地址，没有云端音频备份。“仅内存”时请及时下载；工程不等于音频文件。',
          labels: ['录音', '停止并保存', '下载', '录制来源'] },
        { title: '设备连接，要分开看', lead: '音频输入、参数控制和 MIDI 是不同的连接。',
          items: [['先看连接帮助', '打开“我的设备”，点“查看连接步骤”。'], ['音频按系统选择', '麦克风需要浏览器授权；USB 声卡由手机系统识别和选择。'], ['只信真实状态', 'MIDI 检测仅枚举端口；琴端蓝牙、音色写入和升级仍待硬件联调。']],
          note: '教程不会扫描、配对或申请权限。HTTPS 页面不代表已连接琴，也不能保证用蓝牙传输琴声。',
          labels: ['我的设备', '查看连接步骤', '音频输入', '参数控制', 'MIDI 端口'] },
        { title: '把琴房设成你的习惯', lead: '在设置中选择模式、国家和语言，随时重看教学。',
          items: [['选择使用模式', '“当前模式”查看完整界面。“离线免注册”无需账号；首次先联网点“准备离线资源”。'], ['选择国家和语言', '国家设置默认语言与品牌，也可以单独改变界面语言。'], ['随时重看', '在设置中点“重新查看教学”。现在可以去调音，或先返回首页。']],
          note: '两种模式共用当前浏览器记录，切换不会清空。离线需先成功下载资源；麦克风仍需授权，录音没有云端备份。',
          labels: ['当前模式', '离线免注册', '重新选择国家', '重新查看教学'] }
      ]
    },
    en: {
      tutorial: 'Quick start guide', skip: 'Skip tutorial', back: 'Back', next: 'Next',
      progress: (n, total) => `Step ${n} of ${total}`,
      goTuner: 'Start tuning', goHome: 'Go to home', replay: 'Replay this guide any time in Settings.',
      illustration: 'Button guide · no microphone or device is activated',
      steps: [
        { title: 'Start with the tuner', lead: 'Open the chromatic tuner from Home and play one open string at a time.',
          items: [['Open the tuner', 'Tap “Open tuner” on Home.'], ['Hear a reference', 'Tap G / D / A / E to hear the reference for that string.'], ['Start detection', 'Tap “Start microphone tuning”, then allow the microphone when your browser asks.']],
          note: 'Microphone permission is requested only after you start detection. A4 / 440 Hz here is an illustration; instrument detection still needs calibration.',
          labels: ['Open tuner', 'Reference tone', 'Start microphone tuning'] },
        { title: 'Find a piece you like', lead: 'Search the library, save a favourite, then open Practice.',
          items: [['Search for music', 'Type a title or composer in the library, or browse a category.'], ['Save a favourite', 'Tap the heart. Find it again under “Favourites”.'], ['Open the score', 'Tap “Practice” beside the piece.']],
          note: 'Favourites stay in this browser. Library scores are development candidates; rights still need review before formal use.',
          labels: ['Search by title or composer', 'Favourites', 'Practice'] },
        { title: 'Listen first, then slow it down', lead: 'Lower the tempo and repeat a short phrase with A–B bars.',
          items: [['Listen to the demo', 'Tap “Listen to the demo” to learn the melody. No microphone is needed.'], ['Set the tempo and range', 'Open “Practice settings”, adjust the tempo and start/end bars, and enable repeat.'], ['Play along', 'When ready, tap “Microphone play-along”. This is when microphone permission is requested.']],
          note: 'Listening does not create a performance score. Play-along results are single-note practice guidance; unreliable input produces no score.',
          labels: ['Listen to the demo', 'Tempo', 'From', 'To', 'Microphone play-along'] },
        { title: 'Record, stop, then save', lead: 'Choose a source in Create and capture a short phrase.',
          items: [['Choose a source', '“Browser synthesis” needs no microphone. “Microphone input” requires your permission.'], ['Record and stop', 'Tap “Audio recording”, then “Stop & save”. Wait for the save result.'], ['Listen and download', 'Play it under “My recordings & videos”, then tap Download to keep a file.']],
          note: 'Audio stays in this browser at this address, with no cloud audio backup. Download promptly if it is memory-only; a project is not an audio file.',
          labels: ['Audio recording', 'Stop & save', 'Download', 'Recording source'] },
        { title: 'Check each connection separately', lead: 'Audio input, parameter control and MIDI are different routes.',
          items: [['Read the connection help', 'Open “Devices”, then “View connection steps”.'], ['Let the system select audio', 'Microphone access needs browser permission. Your phone manages USB audio interfaces.'], ['Trust actual status', 'MIDI detection only lists ports. Instrument Bluetooth, tone transfer and updates still need hardware integration.']],
          note: 'This guide does not scan, pair or request permissions. HTTPS does not mean an instrument is connected or that Bluetooth audio is available.',
          labels: ['Devices', 'View connection steps', 'Audio input', 'Parameter control', 'MIDI ports'] },
        { title: 'Make the studio yours', lead: 'Choose your mode, country and language in Settings. Replay the guide whenever you need it.',
          items: [['Choose a mode', '“Current mode” shows the complete interface. “Offline, no account required” needs no account; first go online and tap “Prepare offline resources”.'], ['Choose country and language', 'Country sets the default language and brand. You can also change the interface language separately.'], ['Replay any time', 'Tap “View the guide again” in Settings. Now start tuning, or return to Home.']],
          note: 'Both modes share the records in this browser, and switching does not erase them. Offline resources must be downloaded successfully first. The microphone still needs permission; audio has no cloud backup.',
          labels: ['Current mode', 'Offline, no account required', 'Choose another country', 'View the guide again'] }
      ]
    },
    ja: {
      tutorial: 'はじめての使い方', skip: '説明をスキップ', back: '戻る', next: '次へ',
      progress: (n, total) => `${total} ステップ中 ${n}`,
      goTuner: '調弦を始める', goHome: 'ホームへ', replay: 'この説明は設定からいつでも見直せます。',
      illustration: 'ボタンの見本 · マイクや機器は起動しません',
      steps: [
        { title: 'まずはチューナーから', lead: 'ホームからチューナーを開き、開放弦を1本ずつ弾きます。',
          items: [['チューナーを開く', 'ホームで「チューナーを開く」をタップします。'], ['基準音を聴く', 'G / D / A / E をタップすると、その弦の基準音が鳴ります。'], ['検出を始める', '「マイクで調弦を開始」をタップし、ブラウザの案内に従ってマイクを許可します。']],
          note: 'マイクの許可は検出を始めたときだけ求めます。図の A4 / 440 Hz は見本です。実際の楽器の検出には校正が必要です。',
          labels: ['チューナーを開く', '基準音', 'マイクで調弦を開始'] },
        { title: '好きな曲を見つける', lead: '曲を検索し、お気に入りに入れて練習を開きます。',
          items: [['曲を検索する', '曲ライブラリで曲名や作者を入力するか、カテゴリから探します。'], ['お気に入りに追加', 'ハートをタップすると「お気に入り」からすぐに見つかります。'], ['楽譜を開く', '曲の横の「練習」をタップします。']],
          note: 'お気に入りはこのブラウザに保存されます。楽譜は開発用の候補です。正式な利用前には権利の確認が必要です。',
          labels: ['曲名・作者で検索', 'お気に入り', '練習'] },
        { title: 'まず聴いて、ゆっくり練習', lead: 'テンポを落とし、A–B の小節を指定して短いフレーズを繰り返します。',
          items: [['お手本を聴く', '「お手本を聴く」で旋律を覚えます。マイクは不要です。'], ['速さと範囲を設定', '「練習設定」を開き、テンポと開始・終了小節を変え、繰り返しを有効にします。'], ['合わせて弾く', '準備ができたら「マイクで合わせて弾く」をタップします。このときマイクの許可を求めます。']],
          note: '聴くだけでは演奏の採点は行いません。結果は単音検出による練習の目安です。十分に確かな入力がない場合は採点しません。',
          labels: ['お手本を聴く', 'テンポ', '開始', '終了', 'マイクで合わせて弾く'] },
        { title: '録音して、停止後に保存', lead: '録音・創作で入力を選び、短いフレーズを残します。',
          items: [['録音元を選ぶ', '「ブラウザ合成音」はマイク不要です。「実際のマイク入力」は許可が必要です。'], ['録音して停止', '「録音」をタップし、終わったら「停止して保存」。保存結果を待ちます。'], ['聴き直してダウンロード', '「録音と動画」で再生し、ダウンロードでファイルを保存します。']],
          note: '音声はこのブラウザとURL内に保存され、クラウド音声バックアップはありません。「メモリのみ」の場合は早めにダウンロードしてください。プロジェクトは音声ファイルではありません。',
          labels: ['録音', '停止して保存', 'ダウンロード', '録音ソース'] },
        { title: '接続は種類ごとに確認', lead: '音声入力、パラメーター操作、MIDI は別の接続です。',
          items: [['接続手順を読む', '「デバイス」を開き、「接続手順を見る」をタップします。'], ['音声入力はシステムで選ぶ', 'マイクはブラウザの許可が必要です。USB オーディオ機器はスマートフォンのシステムが管理します。'], ['実際の状態を確認', 'MIDI 検出はポート一覧のみです。楽器の Bluetooth、音色転送、更新はハードウェア連携待ちです。']],
          note: 'この説明はスキャン、ペアリング、許可の要求を行いません。HTTPS で開けても、楽器の接続や Bluetooth 音声の利用を意味しません。',
          labels: ['デバイス', '接続手順を見る', '音声入力', 'パラメータ制御', 'MIDIポート'] },
        { title: '自分に合った設定に', lead: '設定でモード、国、言語を選び、説明をいつでも見直せます。',
          items: [['モードを選ぶ', '「現在のモード」は全体の画面を表示します。「登録不要のオフラインモード」はアカウント不要です。最初はネットに接続し「オフライン用データを準備」をタップします。'], ['国と言語を選ぶ', '国に応じた初期言語とブランドになります。表示言語だけを変更することもできます。'], ['いつでも見直す', '設定の「ガイドをもう一度見る」をタップします。今は調弦を始めるか、ホームへ戻れます。']],
          note: '両モードはこのブラウザの記録を共有し、切り替えても消えません。オフライン用データを先に正常にダウンロードしてください。マイクは許可が必要で、音声のクラウドバックアップはありません。',
          labels: ['現在のモード', '登録不要のオフラインモード', '国を選び直す', 'ガイドをもう一度見る'] }
      ]
    },
    de: {
      tutorial: 'Kurzanleitung', skip: 'Überspringen', back: 'Zurück', next: 'Weiter',
      progress: (n, total) => `Schritt ${n} von ${total}`,
      goTuner: 'Jetzt stimmen', goHome: 'Zur Startseite', replay: 'Du kannst die Anleitung in den Einstellungen erneut öffnen.',
      illustration: 'Tastenübersicht · Mikrofon und Gerät bleiben aus',
      steps: [
        { title: 'Mit dem Stimmgerät beginnen', lead: 'Öffne das Stimmgerät auf der Startseite und spiele jeweils eine leere Saite.',
          items: [['Stimmgerät öffnen', 'Tippe auf der Startseite auf „Stimmgerät öffnen“.'], ['Referenzton hören', 'Tippe auf G / D / A / E, um den Referenzton der Saite zu hören.'], ['Erkennung starten', 'Tippe auf „Stimmen mit Mikrofon starten“ und erlaube den Mikrofonzugriff im Browser.']],
          note: 'Die Mikrofonfreigabe wird erst beim Start angefragt. A4 / 440 Hz ist hier nur ein Beispiel; die Instrumentenerkennung muss noch kalibriert werden.',
          labels: ['Stimmgerät öffnen', 'Referenzton', 'Stimmen mit Mikrofon starten'] },
        { title: 'Ein passendes Stück finden', lead: 'Suche in der Bibliothek, merke einen Favoriten und öffne die Übung.',
          items: [['Musik suchen', 'Gib einen Titel oder Komponisten ein oder durchsuche eine Kategorie.'], ['Als Favorit merken', 'Tippe auf das Herz. Unter „Favoriten“ findest du das Stück wieder.'], ['Noten öffnen', 'Tippe neben dem Stück auf „Üben“.']],
          note: 'Favoriten bleiben in diesem Browser. Die Noten sind Entwicklungskandidaten; vor einer regulären Nutzung müssen die Rechte geprüft werden.',
          labels: ['Titel oder Komponist suchen', 'Favoriten', 'Üben'] },
        { title: 'Erst hören, dann langsamer üben', lead: 'Senke das Tempo und wiederhole eine kurze Phrase mit A–B-Takten.',
          items: [['Vorführung hören', 'Tippe auf „Demo anhören“, um die Melodie kennenzulernen. Dafür ist kein Mikrofon nötig.'], ['Tempo und Abschnitt wählen', 'Öffne „Übungseinstellungen“, ändere Tempo sowie Start- und Endtakt und aktiviere Wiederholen.'], ['Mitspielen', 'Tippe danach auf „Mit Mikrofon mitspielen“. Erst jetzt wird die Mikrofonfreigabe angefragt.']],
          note: 'Zuhören erzeugt keine Spielbewertung. Ergebnisse dienen als Übungshilfe für Einzeltöne. Ohne zuverlässiges Signal gibt es keine Bewertung.',
          labels: ['Demo anhören', 'Tempo', 'Von', 'Bis', 'Mit Mikrofon mitspielen'] },
        { title: 'Aufnehmen, stoppen und speichern', lead: 'Wähle im Aufnahmebereich eine Quelle und halte eine kurze Phrase fest.',
          items: [['Quelle wählen', '„Browser-Synthese“ braucht kein Mikrofon. Für „Mikrofoneingang“ ist deine Freigabe nötig.'], ['Aufnehmen und stoppen', 'Tippe auf „Audioaufnahme“, danach auf „Stoppen & speichern“. Warte auf das Speicherergebnis.'], ['Anhören und herunterladen', 'Spiele die Datei unter „Meine Aufnahmen & Videos“ ab und lade sie herunter.']],
          note: 'Audio bleibt in diesem Browser unter dieser Adresse; es gibt kein Cloud-Audio-Backup. Lade reine Speicher-Aufnahmen zeitnah herunter. Ein Projekt ist keine Audiodatei.',
          labels: ['Audioaufnahme', 'Stoppen & speichern', 'Herunterladen', 'Aufnahmequelle'] },
        { title: 'Verbindungen einzeln prüfen', lead: 'Audioeingang, Parametersteuerung und MIDI sind getrennte Verbindungen.',
          items: [['Verbindungshilfe lesen', 'Öffne „Geräte“ und tippe auf „Verbindungsschritte ansehen“.'], ['Audio im System auswählen', 'Das Mikrofon braucht Browserfreigabe. USB-Audiointerfaces werden vom Telefonsystem verwaltet.'], ['Echten Status beachten', 'Die MIDI-Erkennung listet nur Ports. Instrumenten-Bluetooth, Klangübertragung und Updates warten noch auf die Hardwareanbindung.']],
          note: 'Diese Anleitung scannt und koppelt keine Geräte und fordert keine Freigaben an. HTTPS bedeutet weder eine Instrumentenverbindung noch verfügbares Bluetooth-Audio.',
          labels: ['Geräte', 'Verbindungsschritte ansehen', 'Audioeingang', 'Parametersteuerung', 'MIDI-Anschlüsse'] },
        { title: 'Das Studio nach Wunsch einrichten', lead: 'Wähle Modus, Land und Sprache in den Einstellungen. Die Anleitung bleibt jederzeit verfügbar.',
          items: [['Modus wählen', '„Aktueller Modus“ zeigt die gesamte Oberfläche. „Offline, ohne Registrierung“ braucht kein Konto. Gehe zuerst online und tippe auf „Offline-Ressourcen vorbereiten“.'], ['Land und Sprache wählen', 'Das Land bestimmt die Standardsprache und Marke. Die Anzeigesprache lässt sich separat ändern.'], ['Anleitung erneut öffnen', 'Tippe in den Einstellungen auf „Anleitung erneut ansehen“. Du kannst jetzt stimmen oder zur Startseite zurückkehren.']],
          note: 'Beide Modi teilen die Aufzeichnungen in diesem Browser; ein Wechsel löscht sie nicht. Offline-Ressourcen müssen zuerst erfolgreich heruntergeladen werden. Das Mikrofon benötigt weiter eine Freigabe; Audio hat kein Cloud-Backup.',
          labels: ['Aktueller Modus', 'Offline, ohne Registrierung', 'Land neu auswählen', 'Anleitung erneut ansehen'] }
      ]
    }
  };

  const visualCopy = {
    zh: { title:'新手入门，从这一小步开始', lead:'看一张照片，认识一个按钮，再亲手试一次。', start:'开始新手模式', resume:'继续新手模式', restart:'重新学习', try:'跟着我操作', later:'稍后继续', done:'完成这一步', next:'看下一步', coached:'操作小提示', source:'AI 原创情境照片 · 按钮以应用实际界面为准', welcome:'欢迎来到你的琴房', welcomeLead:'不用一次学会所有功能。我们先找到首页、曲库和调音器。', welcomeItems:[['看看首页','调音器在首页上方，曲库和练习在底部导航。'],['选择你的节奏','每一步可以先看照片，再前往应用亲手操作。'],['随时暂停','可以跳过，也可以稍后回来继续。']], welcomeNote:'教学不会自动开启麦克风、录音或设备连接。完成步骤由你确认，不代表演奏能力评测。', photoAlt:'小提琴与手机的原创练习场景', local:'进度保存在本机；登录后可同步账号进度。', lesson:'照片入门', lessonNote:'照片展示练习情境；持琴、运弓和指法请结合实际指导。' },
    en: { title:'A small step into your studio', lead:'See a photo, learn one control, then try it yourself.', start:'Start beginner mode', resume:'Continue beginner mode', restart:'Start again', try:'Try it with me', later:'Continue later', done:'Finish this step', next:'See the next step', coached:'Your next small action', source:'Original AI scene photo · use the controls in the actual app', welcome:'Welcome to your studio', welcomeLead:'You do not need to learn every feature at once. Start with Home, Library and the tuner.', welcomeItems:[['Explore Home','The tuner is near the top. Library and Practice are in the bottom navigation.'],['Go at your pace','Look at each photo, then try the corresponding controls in the app.'],['Pause any time','Skip the guide or return later to continue.']], welcomeNote:'The guide never starts the microphone, recording or instrument connection automatically. You confirm each step; this is not a playing assessment.', photoAlt:'Original violin and phone practice scene', local:'Progress stays on this device and can sync after sign-in.', lesson:'Photo introduction', lessonNote:'Photos show the practice setting. Use practical guidance for posture, bowing and fingering.' },
    ja: { title:'小さな一歩から、はじめよう', lead:'写真を見て、ボタンを一つ覚え、実際に試してみましょう。', start:'初心者モードを始める', resume:'初心者モードを続ける', restart:'最初から見る', try:'一緒に操作する', later:'あとで続ける', done:'このステップを完了', next:'次の説明を見る', coached:'次に試すこと', source:'AIによるオリジナル情景写真・実際のアプリのボタンを使用', welcome:'マイスタジオへようこそ', welcomeLead:'すべてを一度に覚える必要はありません。ホーム、曲ライブラリ、チューナーから始めましょう。', welcomeItems:[['ホームを確認','チューナーはホーム上部。曲ライブラリと練習は下のメニューにあります。'],['自分のペースで','各写真を見てから、アプリで実際に操作してみましょう。'],['いつでも中断','スキップしたり、あとから続けたりできます。']], welcomeNote:'説明だけではマイク、録音、楽器接続を開始しません。完了は自分で確認します。演奏能力の判定ではありません。', photoAlt:'バイオリンとスマートフォンのオリジナル練習風景', local:'進捗は端末に保存され、ログイン後にアカウントと同期できます。', lesson:'写真で入門', lessonNote:'写真は練習の情景です。構え、運弓、指使いは実際の指導と合わせて学びましょう。' },
    de: { title:'Mit einem kleinen Schritt beginnen', lead:'Ein Foto ansehen, eine Funktion kennenlernen und selbst ausprobieren.', start:'Einsteigermodus starten', resume:'Einsteigermodus fortsetzen', restart:'Erneut beginnen', try:'Gemeinsam ausprobieren', later:'Später fortsetzen', done:'Schritt abschließen', next:'Nächsten Schritt ansehen', coached:'Dein nächster kleiner Schritt', source:'Originales KI-Szenenfoto · die Bedienelemente der App verwenden', welcome:'Willkommen in deinem Studio', welcomeLead:'Du musst nicht alles auf einmal lernen. Beginne mit Startseite, Bibliothek und Stimmgerät.', welcomeItems:[['Startseite erkunden','Das Stimmgerät ist oben. Bibliothek und Üben findest du in der unteren Navigation.'],['Dein eigenes Tempo','Sieh dir das Foto an und probiere die Funktionen anschließend selbst aus.'],['Jederzeit pausieren','Du kannst überspringen und später fortsetzen.']], welcomeNote:'Die Anleitung startet Mikrofon, Aufnahme und Instrumentenverbindung niemals automatisch. Du bestätigst jeden Schritt; dies bewertet keine Spielleistung.', photoAlt:'Originale Übungsszene mit Violine und Smartphone', local:'Der Fortschritt bleibt auf diesem Gerät und kann nach der Anmeldung synchronisiert werden.', lesson:'Einstieg mit Fotos', lessonNote:'Die Fotos zeigen Übungssituationen. Haltung, Bogenführung und Fingersatz mit praktischer Anleitung lernen.' }
  };
  const coachHints = {
    zh:['点亮框中的“打开调音器”，先认识四根空弦。','点亮框中的 G，听一听 G 弦基准音；需要检测时再手动开启麦克风。','在亮框中搜索曲名，再选一首喜欢的曲目进入练习。','先调低速度，再点亮框中的播放按钮，听一句、练一句。','准备好后点亮框中的音频录制；录完先停止并保存，再继续教学。','打开亮框中的连接说明，先确认手机和乐器支持的输入方式。','需要免注册使用时，点亮框中的准备离线资源；首次准备需要联网。'],
    en:['Tap the highlighted Open tuner button to meet the four open strings.','Tap the highlighted G to hear its reference tone. Start microphone detection only when ready.','Search for a song in the highlighted field, then choose a piece to practice.','Lower the tempo, then tap the highlighted playback button. Listen to one phrase and try it.','When ready, tap the highlighted audio recording control. Stop and save before continuing.','Open the highlighted connection help and check which input routes your phone and instrument support.','For use without registration, prepare offline resources with the highlighted button. The first download needs a connection.'],
    ja:['ハイライトされた「チューナーを開く」をタップして、4本の開放弦を確認しましょう。','ハイライトされた G をタップして基準音を聴きます。検出は準備ができてからマイクで開始します。','ハイライトされた欄で曲を検索し、練習する曲を選びましょう。','テンポを下げ、ハイライトされた再生ボタンをタップします。一句ずつ聴いて練習しましょう。','準備ができたら、ハイライトされた音声録音をタップします。停止・保存してから説明を続けましょう。','ハイライトされた接続ヘルプを開き、スマホと楽器が対応する入力方法を確認します。','登録なしで使う場合は、ハイライトされたボタンでオフライン用データを準備します。初回は通信が必要です。'],
    de:['Tippe auf das hervorgehobene Stimmgerät, um die vier leeren Saiten kennenzulernen.','Tippe auf das hervorgehobene G und höre den Referenzton. Starte die Mikrofonerkennung erst, wenn du bereit bist.','Suche im hervorgehobenen Feld nach einem Lied und wähle ein Stück zum Üben.','Senke das Tempo und tippe auf die hervorgehobene Wiedergabe. Höre und übe eine Phrase.','Wenn du bereit bist, starte die hervorgehobene Audioaufnahme. Stoppe und speichere, bevor du fortfährst.','Öffne die hervorgehobene Verbindungshilfe und prüfe die unterstützten Eingänge von Telefon und Instrument.','Bereite mit der hervorgehobenen Taste Offline-Daten für die Nutzung ohne Registrierung vor. Der erste Download benötigt eine Verbindung.']
  };
  const journey = [
    {id:'welcome',image:'welcome',page:'home',target:'[data-go="tuner"]'},
    {id:'tuner',image:'tuner',page:'tuner',target:'[data-action="reference"][data-id="G3"]'},
    {id:'library',image:'listen',page:'library',target:'#song-search'},
    {id:'practice',image:'phrase',page:'practice',target:'[data-action="play"]'},
    {id:'record',image:'record',page:'studio',target:'[data-action="record-audio"]'},
    {id:'device',image:'confidence',page:'device',target:'[data-action="connection-help"]'},
    {id:'settings',image:'confidence',page:'profile',target:'[data-action="prepare-offline"]'}
  ];
  for (const lang of Object.keys(copy)) {
    const v=visualCopy[lang];
    copy[lang].steps.unshift({title:v.welcome,lead:v.welcomeLead,items:v.welcomeItems,note:v.welcomeNote,labels:[]});
  }
  const E = value => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  function brandMarkup(name) {
    const logos = { Silvio: { file: 'silvio-wordmark.png', className: 'silvio', width: 1915, height: 821 }, VELLEN: { file: 'vellen-wordmark.png', className: 'vellen', width: 2135, height: 736 } };
    const logo = Object.hasOwn(logos, name) ? logos[name] : null;
    return logo ? `<span class="brand-wordmark brand-wordmark-${logo.className}" role="img" aria-label="${E(name)}" data-brand-wordmark="${E(name)}"><img src="brands/${logo.file}" alt="${E(name)}" width="${logo.width}" height="${logo.height}" decoding="async" draggable="false"><span class="brand-wordmark-fallback" aria-hidden="true">${E(name)}</span></span>` : E(name);
  }
  const paths = {
    tuner: '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    search: '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
    heart: '<path d="M20 5c-3-3-6-1-8 1-2-2-5-4-8-1-5 5 3 12 8 15 5-3 13-10 8-15Z"/>',
    play: '<path d="m7 4 13 8-13 8Z"/>',
    mic: '<rect x="8" y="2" width="8" height="13" rx="4"/><path d="M5 11v2a7 7 0 0 0 14 0v-2M12 20v3M8 23h8"/>',
    stop: '<rect x="5" y="5" width="14" height="14" rx="2"/>',
    download: '<path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4"/>',
    bluetooth: '<path d="m8 4 11 12-7 5V3l7 5L8 20"/>',
    settings: '<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="8" cy="6" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="10" cy="18" r="2"/>',
    globe: '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
    arrow: '<path d="M5 12h14m-5-5 5 5-5 5"/>',
    check: '<path d="m5 12 4 4L19 6"/>'
  };
  const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${paths[name] || paths.check}</svg>`;
  const mock = (label, name, strong) => `<div class="svt-mock-button${strong ? ' svt-mock-primary' : ''}">${icon(name)}<span>${E(label)}</span></div>`;
  const waveform = () => `<svg class="svt-wave" viewBox="0 0 320 64" aria-hidden="true" focusable="false"><path d="M8 32h304" class="svt-wave-axis"/>${Array.from({ length: 41 }, (_, i) => { const height = 5 + Math.round(Math.abs(Math.sin(i * .76) * Math.cos(i * .31)) * 45); return `<path d="M${12 + i * 7.4} ${32 - height / 2}v${height}"/>`; }).join('')}</svg>`;
  let active = null;
  let coach = null;
  let generation = 0;

  function report(state,status='in_progress') {
    if(typeof state.options.onProgress==='function')state.options.onProgress({guideVersion:2,step:state.step,status});
  }
  function clearCoach(){if(!coach)return;coach.target?.classList.remove('svt-highlight');coach.root.remove();document.body.classList.remove('svt-coaching');coach=null;}
  function refreshCoach(){
    if(!coach)return;coach.target?.classList.remove('svt-highlight');
    const target=document.querySelector(journey[coach.state.step].target);coach.target=target;
    if(target){target.classList.add('svt-highlight');const current=coach;requestAnimationFrame(()=>{if(coach!==current||!target.isConnected)return;const rect=target.getBoundingClientRect(),limit=current.root.getBoundingClientRect().top-18,top=96;if(rect.bottom>limit||rect.top<top)window.scrollBy({top:rect.top-Math.max(top,(limit+top-rect.height)/2),behavior:'instant'});});}
  }
  function startCoach(state){
    clearCoach();const v=visualCopy[state.lang],step=copy[state.lang].steps[state.step];
    const root=document.createElement('aside');root.className='svt-coach';root.setAttribute('data-no-i18n','');root.setAttribute('data-i18n-ignore','');root.setAttribute('aria-label',v.coached);root.lang=state.lang;
    root.innerHTML=`<div class="svt-coach-content"><img src="learning/${journey[state.step].image}.jpg" alt="" width="96" height="64"><div><small>${E(v.coached)} · ${state.step+1}/7</small><strong>${E(step.title)}</strong><p>${E(coachHints[state.lang][state.step])}</p></div><button type="button" class="svt-coach-later" data-coach-action="later" aria-label="${E(v.later)}">×</button></div><div class="svt-coach-actions"><button type="button" data-coach-action="read">${E(v.next)}</button><button type="button" data-coach-action="done">${E(v.done)}</button></div>`;
    coach={root,state,target:null};document.body.classList.add('svt-coaching');document.body.appendChild(root);refreshCoach();
    root.addEventListener('click',async event=>{const button=event.target.closest('[data-coach-action]');if(!button||button.disabled)return;const action=button.dataset.coachAction;if(action==='later'){report(state);clearCoach();return;}const current=coach;root.querySelectorAll('button').forEach(el=>el.disabled=true);try{if(typeof state.options.beforeAdvance==='function'&&!await state.options.beforeAdvance())return;if(coach!==current)return;const last=state.step===6;clearCoach();if(last&&action==='done'){report(state,'completed');state.options.onFinish?.('completed');return;}const next=Math.min(6,state.step+1);open({...state.options,step:next});}finally{if(coach===current)root.querySelectorAll('button').forEach(el=>el.disabled=false);}});
    coach.target?.scrollIntoView({block:'center',behavior:'auto'});
  }

  function illustration(index, labels) {
    if (index === 0) return `${mock(labels[0], 'tuner', true)}<div class="svt-tuner-figure"><span class="svt-note">A4</span><span class="svt-frequency">440 Hz</span><div class="svt-meter"><i></i><i></i><i></i><b></b><i></i><i></i><i></i></div><div class="svt-strings">${['G', 'D', 'A', 'E'].map(s => `<span${s === 'A' ? ' class="svt-selected"' : ''}>${s}</span>`).join('')}</div></div>${mock(labels[2], 'mic')}`;
    if (index === 1) return `<div class="svt-search-field">${icon('search')}<span>${E(labels[0])}</span></div><div class="svt-piece-row"><div class="svt-score-mini" aria-hidden="true"><svg viewBox="0 0 72 48" focusable="false"><path d="M4 10h64M4 17h64M4 24h64M4 31h64M4 38h64"/><ellipse cx="23" cy="28" rx="5" ry="3"/><path d="M28 28V7"/><ellipse cx="45" cy="20" rx="5" ry="3"/><path d="M50 20V3"/></svg></div><span class="svt-piece-placeholder"><i></i><i></i></span><span class="svt-heart">${icon('heart')}</span></div><div class="svt-mock-row">${mock(labels[1], 'heart')}${mock(labels[2], 'play', true)}</div>`;
    if (index === 2) return `${mock(labels[0], 'play', true)}<div class="svt-tempo"><span>${E(labels[1])}</span><strong>60 <small>BPM</small></strong><div class="svt-slider"><i></i></div></div><div class="svt-range"><div><small>${E(labels[2])}</small><strong>1</strong></div><span>A–B</span><div><small>${E(labels[3])}</small><strong>2</strong></div></div>${mock(labels[4], 'mic')}`;
    if (index === 3) return `<div class="svt-source-label">${icon('mic')}<span>${E(labels[3])}</span></div>${waveform()}<div class="svt-record-row">${mock(labels[0], 'mic', true)}${mock(labels[1], 'stop')}</div>${mock(labels[2], 'download')}`;
    if (index === 4) return `${mock(labels[1], 'bluetooth', true)}<div class="svt-connection-rows">${[[labels[2], 'mic'], [labels[3], 'settings'], [labels[4], 'play']].map(([label, name]) => `<div>${icon(name)}<span>${E(label)}</span><i aria-hidden="true"></i></div>`).join('')}</div>`;
    return `<div class="svt-mode-example">${mock(labels[0], 'settings', true)}${mock(labels[1], 'check')}</div>${mock(labels[2], 'globe')}${mock(labels[3], 'play')}`;
  }

  function focusables(state) {
    return Array.from(state.root.querySelectorAll('button:not([disabled]), summary, [tabindex="0"]')).filter(el => !el.hidden && !el.disabled && el.getAttribute('aria-hidden') !== 'true' && el.getClientRects().length);
  }

  function focusHeading(state) {
    if (active !== state) return;
    state.root.querySelector('.svt-title')?.focus({ preventScroll: true });
  }

  function render(state) {
    const text = copy[state.lang];
    const v = visualCopy[state.lang];
    const step = text.steps[state.step];
    const last = state.step === text.steps.length - 1;
    state.root.innerHTML = `<section class="svt-card" role="dialog" aria-modal="true" aria-labelledby="svt-title" aria-describedby="svt-lead"><header class="svt-header"><div class="svt-brand">${brandMarkup(state.brand)}</div><button type="button" class="svt-skip" data-svt-action="skip">${E(text.skip)}</button></header><div class="svt-body"><div class="svt-heading"><span class="svt-step" aria-live="polite">${E(text.progress(state.step + 1, text.steps.length))}</span><h2 class="svt-title" id="svt-title" tabindex="-1">${E(step.title)}</h2><p class="svt-lead" id="svt-lead">${E(step.lead)}</p></div><div class="svt-content"><figure class="svt-figure"><img class="svt-photo" src="learning/${journey[state.step].image}.jpg" alt="${E(v.photoAlt)}" width="960" height="640" decoding="async"><figcaption>${E(v.source)}</figcaption>${state.step>0?`<details class="svt-controls"><summary>${E(text.illustration)}</summary><div class="svt-preview" aria-hidden="true">${illustration(state.step-1,step.labels)}</div></details>`:''}</figure><div class="svt-instructions"><ol>${step.items.map(([title, detail]) => `<li><strong>${E(title)}</strong><p>${E(detail)}</p></li>`).join('')}</ol><p class="svt-note-box">${E(step.note)}</p></div></div></div><footer class="svt-footer"><div class="svt-dots" aria-hidden="true">${text.steps.map((_, i) => `<i${i === state.step ? ' class="svt-current"' : ''}></i>`).join('')}</div><button type="button" class="svt-button svt-primary svt-try" data-svt-action="try">${E(v.try)}${icon('arrow')}</button><div class="svt-actions${last ? ' svt-last-actions' : ''}"><button type="button" class="svt-button svt-back" data-svt-action="back" ${state.step === 0 ? 'disabled' : ''}>${E(text.back)}</button>${last ? `<button type="button" class="svt-button" data-svt-action="home">${E(v.done)}</button>` : `<button type="button" class="svt-button" data-svt-action="next">${E(text.next)}${icon('arrow')}</button>`}<button type="button" class="svt-button svt-later" data-svt-action="later">${E(v.later)}</button></div><p class="svt-replay">${E(text.replay)}</p></footer></section>`;
    state.root.querySelector('.svt-body').scrollTop = 0;
    focusHeading(state);
  }

  async function finish(state, status, destination, practice=false) {
    if (active !== state || state.closed) return;
    state.closed = true;
    active = null;
    const closingGeneration = ++generation;
    state.root.removeEventListener('click', state.onClick);
    state.root.removeEventListener('error', state.onError, true);
    document.removeEventListener('keydown', state.onKey, true);
    document.removeEventListener('focusin', state.onFocus, true);
    state.root.remove();
    report(state,status==='paused'?'in_progress':status);
    let callbackError = null;
    try { if (typeof state.options.onFinish === 'function') await state.options.onFinish(status); }
    catch (error) { callbackError = error; }
    if (!active && closingGeneration === generation && destination && typeof state.options.navigate === 'function') {
      try { await state.options.navigate(destination); }
      catch (error) { callbackError = callbackError || error; }
    }
    if(practice&&!callbackError&&!active&&closingGeneration===generation)startCoach(state);
    if (!active && closingGeneration === generation) {
      const saved = state.previousFocus;
      const canRestore = saved?.isConnected && !saved.closest?.('[inert]') && !saved.disabled;
      const target = canRestore ? saved : document.querySelector('main[tabindex], #main');
      target?.focus?.({ preventScroll: true });
    }
    if (callbackError) {
      // The caller owns persistence and navigation failures; no successful save is claimed here.
      global.console?.warn?.('SVTutorial: completion callback or navigation did not finish.');
    }
  }

  function open(options) {
    if (active) return false;
    clearCoach();
    const opts = options && typeof options === 'object' ? options : {};
    const lang = Object.hasOwn(copy, opts.lang) ? opts.lang : 'zh';
    const uk = ['uk', 'gb'].includes(String(opts.region || '').toLowerCase());
    const fallbackBrand = uk || lang === 'de' ? 'VELLEN' : 'Silvio';
    const suppliedBrand = typeof opts.brand === 'string' && opts.brand.trim() ? opts.brand.trim() : fallbackBrand;
    const state = { options: opts, lang, brand: suppliedBrand === 'SILVIO' ? 'Silvio' : suppliedBrand, step: Number.isInteger(opts.step)?Math.min(6,Math.max(0,opts.step)):0, root: document.createElement('div'), previousFocus: document.activeElement, closed: false };
    state.root.className = 'svt-overlay';
    state.root.lang = lang;
    state.root.setAttribute('data-i18n-ignore', '');
    state.root.setAttribute('data-no-i18n', '');
    state.root.setAttribute('data-sv-tutorial', '');
    state.onClick = event => {
      const button = event.target.closest?.('[data-svt-action]');
      if (!button || !state.root.contains(button) || button.disabled) return;
      event.preventDefault();
      const action = button.dataset.svtAction;
      if (action === 'skip') { void finish(state, 'skipped'); return; }
      if (action === 'later') { void finish(state, 'paused'); return; }
      if (action === 'try') { void finish(state, 'paused',journey[state.step].page,true); return; }
      if (action === 'tuner' || action === 'home') { void finish(state, 'completed', action === 'tuner' ? 'tuner' : 'home'); return; }
      if (action === 'next' && state.step < copy[lang].steps.length - 1) state.step++;
      else if (action === 'back' && state.step > 0) state.step--;
      else return;
      report(state);
      render(state);
    };
    state.onKey = event => {
      if (active !== state) return;
      if (event.key === 'Escape') {
        event.preventDefault(); event.stopPropagation(); void finish(state, 'skipped');
      } else if (event.key === 'Tab') {
        const list = focusables(state);
        if (!list.length) { event.preventDefault(); focusHeading(state); return; }
        const index = list.indexOf(document.activeElement);
        if (event.shiftKey && index <= 0) { event.preventDefault(); list[list.length - 1].focus(); }
        else if (!event.shiftKey && (index === -1 || index === list.length - 1)) { event.preventDefault(); list[0].focus(); }
      }
    };
    state.onFocus = event => { if (active === state && !state.root.contains(event.target)) focusHeading(state); };
    state.onError = event => { if (event.target?.matches?.('.brand-wordmark img')) event.target.parentElement.classList.add('is-failed'); };
    active = state;
    generation++;
    state.root.addEventListener('click', state.onClick);
    state.root.addEventListener('error', state.onError, true);
    document.addEventListener('keydown', state.onKey, true);
    document.addEventListener('focusin', state.onFocus, true);
    document.body.appendChild(state.root);
    state.options.onOpen?.();
    report(state);
    render(state);
    return true;
  }

  function entry(options={}){const lang=Object.hasOwn(copy,options.lang)?options.lang:'zh',v=visualCopy[lang],p=options.progress||{},step=Number.isInteger(p.step)?Math.min(6,Math.max(0,p.step)):0;return `<section class="beginner-entry" data-i18n-ignore data-no-i18n><img src="learning/welcome.jpg" alt="${E(v.photoAlt)}" width="960" height="640" loading="lazy"><div><span class="eyebrow">${E(copy[lang].progress(step+1,7))}</span><h2>${E(v.title)}</h2><p>${E(v.lead)}</p><button class="button primary" data-action="tutorial">${E(p.status==='in_progress'?v.resume:v.start)}</button>${p.status&&p.status!=='pending'?`<button class="button secondary" data-action="tutorial-restart">${E(v.restart)}</button>`:''}<small>${E(v.local)}</small></div></section>`;}
  const api = { open, entry, refreshCoach, close(status) {clearCoach(); if (!active) return Promise.resolve(); return finish(active, status === 'completed' ? 'completed' : 'skipped'); } };
  Object.defineProperty(api, 'isOpen', { enumerable: true, get: () => Boolean(active) });
  Object.defineProperty(api, 'isCoaching', { enumerable: true, get: () => Boolean(coach) });
  global.SVTutorial = Object.freeze(api);
})(window);
