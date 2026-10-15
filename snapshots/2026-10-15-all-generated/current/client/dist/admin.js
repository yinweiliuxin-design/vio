(function (global) {
  'use strict';
  const rows = [
    ['app','社区管理','Community management','コミュニティ管理','Community-Verwaltung'],
    ['cloud','云端工作台','Cloud workspace','クラウド管理画面','Cloud-Arbeitsbereich'],
    ['language','界面语言','Interface language','表示言語','Anzeigesprache'],
    ['studio','返回琴房','Back to studio','スタジオに戻る','Zum Studio'],
    ['skip','跳到管理内容','Skip to management content','管理内容へ移動','Zum Verwaltungsinhalt'],
    ['serverPermissions','操作权限由服务端检查','Permissions are checked by the server','操作権限はサーバーで確認します','Berechtigungen werden serverseitig geprüft'],
    ['footer','云记录以服务端响应为准','Cloud records follow the server response','クラウド記録はサーバーの応答を基準にします','Cloud-Einträge richten sich nach der Serverantwort'],
    ['overview','总览','Overview','概要','Übersicht'],
    ['moderation','内容审核','Content review','コンテンツ審査','Inhaltsprüfung'],
    ['reports','举报处理','Reports','通報の処理','Meldungen'],
    ['users','用户概览','Users','ユーザー概要','Nutzerübersicht'],
    ['settings','社区设置','Community settings','コミュニティ設定','Community-Einstellungen'],
    ['catalog','曲库显示','Library visibility','曲ライブラリの表示','Sichtbarkeit der Bibliothek'],
    ['audit','操作审计','Audit log','操作履歴','Prüfprotokoll'],
    ['plans','后续模块','Planned modules','今後の機能','Geplante Module'],
    ['connecting','正在连接云社区…','Connecting to the cloud community…','クラウドコミュニティに接続中…','Verbindung zur Cloud-Community wird hergestellt…'],
    ['ready','云社区已连接 · 管理权限已确认','Cloud community connected · admin access confirmed','クラウド接続済み・管理権限を確認しました','Cloud-Community verbunden · Verwaltungsrecht bestätigt'],
    ['readyNote','当前访问云端社区数据；审核与保存由服务端执行。','Showing cloud community data. Reviews and saves are performed by the server.','クラウドのコミュニティデータを表示しています。審査と保存はサーバーで実行します。','Cloud-Community-Daten werden angezeigt. Prüfung und Speicherung erfolgen auf dem Server.'],
    ['userOffline','用户琴房为离线免注册模式；云管理仍需联网。','The user studio is in offline mode; cloud management still needs internet access.','スタジオは登録不要のオフラインモードです。クラウド管理には通信が必要です。','Das Studio nutzt den Offline-Modus; Cloud-Verwaltung benötigt weiterhin Internet.'],
    ['lastRead','上次读取：{at}','Last loaded: {at}','最終読込：{at}','Zuletzt geladen: {at}'],
    ['refresh','刷新云数据','Refresh cloud data','クラウドデータを更新','Cloud-Daten aktualisieren'],
    ['signin','使用 ChatGPT 登录','Sign in with ChatGPT','ChatGPT でログイン','Mit ChatGPT anmelden'],
    ['authRequired','需要站点登录身份','Site sign-in is required','サイトへのログインが必要です','Anmeldung auf der Website erforderlich'],
    ['authNote','请使用站点登录入口。登录身份本身不代表拥有管理员权限。','Use the site sign-in link. Signing in does not itself grant admin permissions.','サイトのログイン入口をご利用ください。ログインだけでは管理権限は付与されません。','Nutze den Anmeldelink der Website. Eine Anmeldung allein erteilt kein Verwaltungsrecht.'],
    ['forbidden','当前身份没有管理权限','This identity has no admin permission','現在のアカウントに管理権限がありません','Diese Identität hat kein Verwaltungsrecht'],
    ['forbiddenNote','服务端返回 403。请由站点所有者配置管理员权限，再刷新。','The server returned 403. Ask the site owner to configure admin access, then refresh.','サーバーが 403 を返しました。サイト所有者が管理権限を設定してから更新してください。','Der Server meldet 403. Der Website-Inhaber muss den Verwaltungszugriff konfigurieren; aktualisiere danach.'],
    ['unavailable','云管理服务未就绪','Cloud management is unavailable','クラウド管理サービスは利用できません','Cloud-Verwaltung nicht verfügbar'],
    ['actionNotCompleted','操作尚未完成','The action is not complete','操作は完了していません','Aktion noch nicht abgeschlossen'],
    ['unavailableNote','请检查网络和云端部署。此页不会把本机笔记作为云社区数据。','Check the connection and cloud deployment. Local notes are not used as cloud community data.','通信とクラウドの公開状態をご確認ください。この画面は端末内のノートをクラウドデータとして扱いません。','Prüfe Verbindung und Cloud-Bereitstellung. Lokale Notizen werden nicht als Cloud-Community-Daten verwendet.'],
    ['dbUnavailable','服务端返回 503：云数据库或服务尚未就绪。','The server returned 503: the cloud database or service is not ready.','サーバーが 503 を返しました。クラウドDBまたはサービスが準備できていません。','Serverantwort 503: Cloud-Datenbank oder Dienst ist noch nicht bereit.'],
    ['conflict','记录版本已变化，请刷新后重新核对。','The record version changed. Refresh and review it again.','記録のバージョンが変わりました。更新して再確認してください。','Die Datensatzversion hat sich geändert. Aktualisiere und prüfe erneut.'],
    ['invalid','内容不符合服务端要求，请检查填写内容与长度。','The server rejected the input. Check the fields and their length.','入力がサーバーの条件に合いません。内容と文字数をご確認ください。','Die Eingabe erfüllt die Serveranforderungen nicht. Prüfe Felder und Länge.'],
    ['notFound','目标不存在或接口尚未部署，请刷新核对。','The target is missing or the API is not deployed. Refresh to check.','対象がないか、APIが未公開です。更新してご確認ください。','Ziel fehlt oder API wurde nicht bereitgestellt. Aktualisiere zur Prüfung.'],
    ['tooMany','请求过于频繁，请稍后重试。','Too many requests. Try again later.','要求が多すぎます。しばらくしてから再試行してください。','Zu viele Anfragen. Versuche es später erneut.'],
    ['unconfirmed','提交结果未确认。请刷新核对后再操作，不要重复提交。','The submission result is unconfirmed. Refresh before trying again; avoid duplicate submissions.','送信結果を確認できません。重複送信を避け、更新してから操作してください。','Ergebnis unbestätigt. Aktualisiere vor dem nächsten Versuch und vermeide doppelte Übermittlungen.'],
    ['readError','无法读取云数据，请重试。','Could not load cloud data. Try again.','クラウドデータを読み込めません。再試行してください。','Cloud-Daten konnten nicht geladen werden. Versuche es erneut.'],
    ['apiInvalid','接口未返回预期的管理数据。','The API did not return the expected admin data.','APIが必要な管理データを返しませんでした。','Die API lieferte nicht die erwarteten Verwaltungsdaten.'],
    ['requestTicket','请求编号：{id}','Request ID: {id}','要求ID：{id}','Anfrage-ID: {id}'],
    ['stale','显示上次读取的记录；写操作已暂停，请刷新。','Showing previously loaded records. Writes are paused; refresh first.','前回読み込んだ記録です。書き込みを停止しています。更新してください。','Zuletzt geladene Einträge werden angezeigt. Änderungen sind pausiert; bitte aktualisieren.'],
    ['saved','云端已确认保存。','The cloud service confirmed the save.','クラウドでの保存を確認しました。','Cloud-Dienst hat die Speicherung bestätigt.'],
    ['working','正在提交…','Submitting…','送信中…','Wird übermittelt…'],
    ['publishedPosts','已发布帖子','Published posts','公開済み投稿','Veröffentlichte Beiträge'],
    ['pendingPosts','待审帖子','Pending posts','審査待ち投稿','Ausstehende Beiträge'],
    ['pendingComments','待审评论','Pending comments','審査待ちコメント','Ausstehende Kommentare'],
    ['openReports','待处理举报','Open reports','未処理の通報','Offene Meldungen'],
    ['totalUsers','社区用户','Community users','コミュニティユーザー','Community-Nutzer'],
    ['overviewIntro','核对真实联通状态，再处理社区内容。','Check the live connection, then review community content.','実際の接続状態を確認してから、コミュニティの内容を審査します。','Prüfe die echte Verbindung und bearbeite dann Community-Inhalte.'],
    ['publishing','帖子发布入口','Post submissions','投稿の受付','Beitragseinreichung'],
    ['commenting','评论入口','Comment submissions','コメントの受付','Kommentarfunktion'],
    ['liking','点赞入口','Likes','いいね','Gefällt-mir-Funktion'],
    ['links','外链附件','External link attachments','外部リンクの添付','Externe Link-Anhänge'],
    ['enabled','已启用','Enabled','有効','Aktiviert'],
    ['disabled','已停用','Disabled','無効','Deaktiviert'],
    ['recentAudit','最近操作','Recent actions','最近の操作','Letzte Aktionen'],
    ['openReview','查看审核队列','Open review queue','審査一覧を開く','Prüfwarteschlange öffnen'],
    ['contentIntro','按状态筛选已加载的帖子与评论。预览后执行审核，状态以服务端为准。','Filter loaded posts and comments. Preview before reviewing; the server confirms their status.','読み込んだ投稿とコメントを状態で絞り込みます。プレビュー後に審査し、状態はサーバーで確認します。','Filtere geladene Beiträge und Kommentare. Prüfe die Vorschau; den Status bestätigt der Server.'],
    ['search','搜索','Search','検索','Suchen'],
    ['searchContent','搜索标题、内容或作者','Search title, text or author','題名・本文・投稿者を検索','Titel, Text oder Autor suchen'],
    ['searchUsers','搜索名称或用户编号','Search name or user ID','名前・ユーザーIDを検索','Name oder Nutzer-ID suchen'],
    ['searchCatalog','搜索曲名、作者或编号','Search title, author or ID','曲名・作者・IDを検索','Titel, Autor oder ID suchen'],
    ['searchAudit','搜索操作、目标或管理员编号','Search action, target or admin ID','操作・対象・管理者IDを検索','Aktion, Ziel oder Admin-ID suchen'],
    ['searchReports','搜索原因或目标编号','Search reason or target ID','理由・対象IDを検索','Grund oder Ziel-ID suchen'],
    ['type','类型','Type','種類','Typ'],
    ['status','状态','Status','状態','Status'],
    ['all','全部','All','すべて','Alle'],
    ['post','帖子','Post','投稿','Beitrag'],
    ['comment','评论','Comment','コメント','Kommentar'],
    ['parentPost','所属帖子','Parent post','元の投稿','Zugehöriger Beitrag'],
    ['draft','草稿','Draft','下書き','Entwurf'],
    ['pending','待审核','Pending review','審査待ち','Zur Prüfung'],
    ['published','已发布','Published','公開済み','Veröffentlicht'],
    ['rejected','已拒绝','Rejected','却下','Abgelehnt'],
    ['hidden','已隐藏','Hidden','非表示','Ausgeblendet'],
    ['deleted','已删除','Deleted','削除済み','Gelöscht'],
    ['open','待处理','Open','未処理','Offen'],
    ['resolved','已处理','Resolved','処理済み','Erledigt'],
    ['dismissed','已驳回举报','Dismissed','通報を却下','Meldung abgewiesen'],
    ['unknown','未知','Unknown','不明','Unbekannt'],
    ['loaded','本次显示 {n} 条','Showing {n} loaded records','今回表示：{n}件','{n} geladene Einträge angezeigt'],
    ['noResults','没有符合条件的记录','No matching records','条件に合う記録がありません','Keine passenden Einträge'],
    ['noResultsNote','可以更换筛选条件或刷新云数据。','Change a filter or refresh cloud data.','条件を変更するか、クラウドデータを更新してください。','Ändere den Filter oder aktualisiere die Cloud-Daten.'],
    ['preview','预览','Preview','プレビュー','Vorschau'],
    ['approve','通过审核','Approve','承認','Genehmigen'],
    ['reject','拒绝','Reject','却下','Ablehnen'],
    ['hide','隐藏','Hide','非表示にする','Ausblenden'],
    ['restore','恢复发布','Restore publication','公開を復元','Veröffentlichung wiederherstellen'],
    ['restoreDraft','恢复为草稿','Restore as draft','下書きに戻す','Als Entwurf wiederherstellen'],
    ['reason','处理理由','Reason','処理理由','Begründung'],
    ['reasonHint','拒绝和隐藏必须填写理由，最多500字。','Rejection and hiding require a reason, up to 500 characters.','却下・非表示には理由が必要です（最大500文字）。','Ablehnen und Ausblenden erfordern eine Begründung mit höchstens 500 Zeichen.'],
    ['reasonRequired','请填写处理理由。','Enter a reason.','処理理由を入力してください。','Gib eine Begründung ein.'],
    ['confirm','确认提交','Confirm submission','送信を確定','Übermittlung bestätigen'],
    ['cancel','取消','Cancel','キャンセル','Abbrechen'],
    ['close','关闭','Close','閉じる','Schließen'],
    ['author','作者','Author','投稿者','Autor'],
    ['id','编号','ID','ID','ID'],
    ['version','版本 {n}','Version {n}','バージョン {n}','Version {n}'],
    ['created','创建时间','Created','作成日時','Erstellt'],
    ['updated','更新时间','Updated','更新日時','Aktualisiert'],
    ['body','内容','Content','内容','Inhalt'],
    ['untitled','无标题','Untitled','無題','Ohne Titel'],
    ['moderationReason','审核理由','Review reason','審査理由','Prüfbegründung'],
    ['attachments','附件','Attachments','添付','Anhänge'],
    ['cloudImage','云端图片','Cloud image','クラウド画像','Cloud-Bild'],
    ['imageFailed','图片无法读取，可能是网络或访问权限变化。','The image could not be loaded; check the connection or access permissions.','画像を読み込めません。通信またはアクセス権限をご確認ください。','Bild konnte nicht geladen werden. Prüfe Verbindung und Zugriffsrecht.'],
    ['externalLink','打开外部链接','Open external link','外部リンクを開く','Externen Link öffnen'],
    ['localMedia','本机媒体清单 · 未上传','Local media metadata · not uploaded','端末内メディア情報・未アップロード','Lokale Mediendaten · nicht hochgeladen'],
    ['unavailableAttachment','附件预览不可用','Attachment preview unavailable','添付のプレビューは利用できません','Anhangsvorschau nicht verfügbar'],
    ['target','举报目标','Reported target','通報対象','Gemeldetes Ziel'],
    ['reportReason','举报原因','Report reason','通報理由','Meldegrund'],
    ['resolution','处理结论','Resolution note','処理結果','Bearbeitungsvermerk'],
    ['resolve','标为处理完成','Mark resolved','処理済みにする','Als erledigt markieren'],
    ['dismiss','驳回举报','Dismiss report','通報を却下','Meldung abweisen'],
    ['reportIntro','处理举报与审核目标是两项操作；处理完成不会自动更改帖子的发布状态。','Resolving a report and reviewing its target are separate actions. Resolution does not automatically change publication status.','通報の処理と対象の審査は別の操作です。処理完了だけでは公開状態は変わりません。','Meldung bearbeiten und Ziel prüfen sind getrennte Aktionen. Eine Erledigung ändert den Veröffentlichungsstatus nicht automatisch.'],
    ['missingTarget','目标不在本次加载的列表中。','The target is not in the loaded list.','対象が今回の読込一覧にありません。','Das Ziel ist nicht in der geladenen Liste.'],
    ['usersIntro','只展示服务端返回的社区身份与状态，不读取本机练习记录或录音。','Shows community identities and status returned by the server, without reading local practice or recordings.','サーバーが返すコミュニティのアカウントと状態のみ表示します。端末内の練習記録や録音は読みません。','Zeigt serverseitige Community-Identitäten und Status. Lokale Übungen und Aufnahmen werden nicht gelesen.'],
    ['name','名称','Name','名前','Name'],
    ['admin','管理员','Administrator','管理者','Administrator'],
    ['member','社区用户','Community member','コミュニティユーザー','Community-Mitglied'],
    ['role','权限','Role','権限','Rolle'],
    ['disableUser','停用用户','Disable user','ユーザーを無効化','Nutzer deaktivieren'],
    ['enableUser','启用用户','Enable user','ユーザーを有効化','Nutzer aktivieren'],
    ['adminProtected','管理员不能在此停用','Admins cannot be disabled here','管理者はここで無効にできません','Administratoren können hier nicht deaktiviert werden'],
    ['userConfirm','确认更改此用户的启用状态。服务端会再次检查管理权限。','Confirm the user status change. The server will check permissions again.','ユーザーの有効状態を変更します。サーバーで権限を再確認します。','Bestätige die Statusänderung. Der Server prüft das Verwaltungsrecht erneut.'],
    ['settingsIntro','更改发布入口与四语公告。所有保存都带版本检查。','Manage submission features and announcements in four languages. Every save checks the version.','投稿機能と4言語のお知らせを設定します。保存時にはバージョンを確認します。','Verwalte Einreichungen und Hinweise in vier Sprachen. Jede Speicherung prüft die Version.'],
    ['publicationSwitches','社区入口','Community features','コミュニティ機能','Community-Funktionen'],
    ['postSwitch','允许提交帖子','Allow post submissions','投稿の送信を許可','Beitragseinreichung erlauben'],
    ['commentSwitch','允许提交评论','Allow comments','コメントを許可','Kommentare erlauben'],
    ['likeSwitch','允许点赞','Allow likes','いいねを許可','Gefällt mir erlauben'],
    ['linkSwitch','允许 HTTPS 外链附件','Allow HTTPS link attachments','HTTPS 外部リンクの添付を許可','HTTPS-Link-Anhänge erlauben'],
    ['presetSwitch','允许新的私人云预设备份','Allow new private preset backups','新しい非公開プリセットのバックアップを許可','Neue private Preset-Sicherungen erlauben'],
    ['presetOwners','使用云预设的账号总数','Accounts with preset backups','プリセット保存アカウント数','Konten mit Preset-Sicherungen'],
    ['presetCount','云预设总数','Total backed-up presets','バックアップ済みプリセット数','Gesicherte Presets insgesamt'],
    ['presetPrivacy','这里只统计总数；不会读取或展示用户的预设名称、分组、参数或录音。关闭入口后，用户仍可读取或清空已有备份。','Only totals are shown; private names, groups, parameters and recordings are not exposed. Users can still read or clear existing backups when new backups are disabled.','集計数のみを表示し、個人の名前・グループ・設定・録音は公開しません。新規保存を無効にしても既存バックアップの読込と削除は可能です。','Hier werden nur Summen angezeigt, keine privaten Namen, Gruppen, Parameter oder Aufnahmen. Bestehende Sicherungen bleiben lesbar und löschbar.'],
    ['announcement','管理员公告','Admin announcement','管理者からのお知らせ','Administrator-Hinweis'],
    ['announcementNote','按语言保存纯文本，每种语言最多1000字。公告内容不会自动翻译。','Plain text is stored per language, up to 1,000 characters each. Announcement content is not automatically translated.','各言語のテキストを最大1000文字で保存します。お知らせ本文は自動翻訳しません。','Speichere Klartext je Sprache mit höchstens 1.000 Zeichen. Der Inhalt wird nicht automatisch übersetzt.'],
    ['saveSettings','保存社区设置','Save community settings','コミュニティ設定を保存','Community-Einstellungen speichern'],
    ['langZh','中文','Chinese','中国語','Chinesisch'],
    ['langEn','英文','English','英語','Englisch'],
    ['langJa','日语','Japanese','日本語','Japanisch'],
    ['langDe','德语','German','ドイツ語','Deutsch'],
    ['catalogIntro','对随包曲目设置云端显示或隐藏，不新增或删除谱本。','Set cloud visibility for packaged pieces; this does not add or delete scores.','同梱曲のクラウド表示を切り替えます。楽譜の追加・削除は行いません。','Steuere die Cloud-Sichtbarkeit mitgelieferter Stücke; Noten werden nicht hinzugefügt oder gelöscht.'],
    ['catalogRights','显示开关不代表版权授权。候选谱本仍需按原权利流程核验。','Visibility is not a copyright clearance. Candidate scores still require the existing rights review.','表示設定は著作権の許諾ではありません。候補楽譜は既存の権利確認が必要です。','Sichtbarkeit ist keine Rechtefreigabe. Kandidatennoten benötigen weiterhin die vorgesehene Rechteprüfung.'],
    ['piece','曲目','Piece','曲','Stück'],
    ['visible','显示','Visible','表示','Sichtbar'],
    ['notVisible','隐藏','Hidden','非表示','Ausgeblendet'],
    ['rightsStatus','权利登记状态','Rights record status','権利の記録状態','Status der Rechteeintragung'],
    ['rightsPending','待核验','Review pending','確認待ち','Prüfung ausstehend'],
    ['rightsReviewed','已登记','Recorded','記録済み','Erfasst'],
    ['visibility','显示配置','Visibility','表示設定','Sichtbarkeit'],
    ['catalogWaiting','尚未取得服务端曲目配置。','No server catalog configuration has been received.','サーバーの曲設定を取得できていません。','Noch keine serverseitige Katalogkonfiguration erhalten.'],
    ['auditIntro','服务端记录谁在何时操作了哪条记录。界面不会生成本机审计冒充服务端记录。','Server records identify the actor, time and target. This interface does not create local audit entries as server records.','サーバーが操作した人・時刻・対象を記録します。この画面は端末内の履歴をサーバー記録として作成しません。','Der Server protokolliert Akteur, Zeit und Ziel. Die Oberfläche erzeugt keine lokalen Einträge als Serverprotokoll.'],
    ['time','时间','Time','日時','Zeit'],
    ['actor','操作者','Actor','操作者','Akteur'],
    ['action','动作','Action','操作','Aktion'],
    ['details','详情','Details','詳細','Details'],
    ['detailsTruncated','详情过长，仅显示前3000字符。','Details are long; only the first 3,000 characters are shown.','詳細が長いため、最初の3000文字のみ表示します。','Die Details sind lang; nur die ersten 3.000 Zeichen werden angezeigt.'],
    ['planIntro','产品、课程、设备发布与商业业务保留在规划中。以下模块没有接入此云后台。','Products, lessons, device releases and business features remain planned. The modules below are not connected to this cloud console.','製品・講座・機器公開・商用機能は計画として保持します。以下はこのクラウド管理画面に未接続です。','Produkte, Kurse, Gerätefreigaben und Geschäftsfunktionen bleiben geplant. Diese Module sind noch nicht mit der Cloud-Konsole verbunden.'],
    ['planned','待接入','Not integrated','未連携','Noch nicht angebunden'],
    ['products','产品管理','Product management','製品管理','Produktverwaltung'],
    ['productPlan','产品规格、地区信息与商品编辑待独立服务接入。','Specifications, regional data and product editing await a separate service.','仕様・地域情報・製品編集は専用サービスとの連携待ちです。','Spezifikationen, Regionsdaten und Produktbearbeitung warten auf einen eigenen Dienst.'],
    ['courses','课程与内容','Courses and content','講座とコンテンツ','Kurse und Inhalte'],
    ['coursePlan','课程内容、进度同步与授权管理尚未接入。','Course content, progress sync and licensing are not yet integrated.','講座内容・進捗同期・利用権の管理は未連携です。','Kursinhalte, Fortschrittssynchronisierung und Lizenzverwaltung sind noch nicht angebunden.'],
    ['devices','设备与固件发布','Devices and firmware','機器とファームウェア','Geräte und Firmware'],
    ['devicePlan','真实设备、签名升级和硬件验收需要独立接口与实机验证。','Real devices, signed updates and hardware acceptance need separate interfaces and physical testing.','実機・署名付き更新・ハードウェア検証には専用接口と実機試験が必要です。','Echte Geräte, signierte Updates und Hardwareabnahme benötigen eigene Schnittstellen und reale Tests.'],
    ['orders','订单与权益','Orders and entitlements','注文と利用権','Bestellungen und Ansprüche'],
    ['orderPlan','真实支付、库存、物流和订阅权益尚未接入。','Payments, inventory, shipping and subscription access are not integrated.','実際の決済・在庫・配送・サブスクリプション権限は未連携です。','Zahlungen, Bestand, Versand und Abonnements sind noch nicht angebunden.'],
    ['noData','尚未取得云管理数据','Cloud admin data has not been loaded','クラウド管理データは未取得です','Cloud-Verwaltungsdaten noch nicht geladen'],
    ['noDataNote','先确认登录身份、管理权限和云数据库连接。','First check sign-in, admin permissions and the cloud database connection.','ログイン・管理権限・クラウドDBへの接続をご確認ください。','Prüfe zuerst Anmeldung, Verwaltungsrecht und Cloud-Datenbankverbindung.']
  ];
  const dictionary = new Map(rows.map(row => [row[0], row.slice(1)]));
  const supported = ['zh', 'en', 'ja', 'de'];
  const E = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const $ = selector => document.querySelector(selector);
  let prefs = {};
  try { const parsed = JSON.parse(localStorage.getItem('sv12-prefs') || '{}'); if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) prefs = parsed; } catch { /* Display preferences are optional; they never authorize admin access. */ }
  let lang = supported.includes(prefs.lang) ? prefs.lang : 'zh';
  const region = typeof prefs.region === 'string' ? prefs.region.toLowerCase() : 'cn';
  let data = null, view = 'overview', error = null, busy = false, loading = false, stale = false, loadedAt = null, readGeneration = 0, readAbort = null, noticeTimer, modalFocus = null;
  const filters = { moderation: { query: '', status: 'pending', type: 'all' }, reports: { query: '', status: 'open' }, users: { query: '', status: 'all' }, catalog: { query: '', status: 'all' }, audit: { query: '' } };
  const t = (key, values = {}) => (dictionary.get(key)?.[supported.indexOf(lang)] || key).replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? ''));
  const brand = () => region === 'uk' || region === 'gb' || lang === 'de' ? 'VELLEN' : 'Silvio';
  function brandMarkup() {
    const name = brand(), info = name === 'Silvio' ? ['silvio', 1915, 821] : name === 'VELLEN' ? ['vellen', 2135, 736] : null;
    return info ? `<span class="brand-wordmark brand-wordmark-${info[0]}" role="img" aria-label="${E(name)}"><img src="/brands/${info[0]}-wordmark.png" alt="${E(name)}" width="${info[1]}" height="${info[2]}" decoding="async" draggable="false"><span class="brand-wordmark-fallback" aria-hidden="true">${E(name)}</span></span>` : E(name);
  }
  const iconPaths = {
    overview: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    moderation: '<path d="M12 3 3 7v6c0 5 9 9 9 9s9-4 9-9V7Z"/><path d="m8 12 3 3 5-6"/>', reports: '<path d="M5 22V3m0 0h13l-2 4 2 4H5"/>',
    users: '<circle cx="9" cy="8" r="4"/><path d="M2 21v-3a7 7 0 0 1 14 0v3M17 4a4 4 0 0 1 0 8m2 3a6 6 0 0 1 3 5"/>',
    settings: '<path d="M3 6h18M3 12h18M3 18h18"/><circle cx="8" cy="6" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="10" cy="18" r="2"/>',
    catalog: '<path d="M4 3h15v18H4zM8 7h7M8 12h7M8 17h5"/>', audit: '<path d="M5 3h14v18H5zM9 7h6M9 12h6M9 17h4"/>',
    plans: '<path d="M3 6h7l2 3h9v12H3Z"/>', refresh: '<path d="M21 8V3l-3 3a8 8 0 1 0 2 11M21 3h-5"/>', close: '<path d="m6 6 12 12M6 18 18 6"/>'
  };
  const icon = key => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${iconPaths[key] || iconPaths.audit}</svg>`;
  const nav = ['overview', 'moderation', 'reports', 'users', 'settings', 'catalog', 'audit', 'plans'];
  function stamp(value) { if (!value) return '—'; try { const date = new Date(value); if (!Number.isFinite(date.getTime())) return '—'; return new Intl.DateTimeFormat({ zh: 'zh-CN', en: region === 'uk' ? 'en-GB' : 'en-US', ja: 'ja-JP', de: 'de-DE' }[lang], { dateStyle: 'short', timeStyle: 'short' }).format(date); } catch { return '—'; } }
  const mutable = () => Boolean(data?.viewer?.isAdmin && !stale && !loading && !busy && !error?.forbidden);
  const statusName = status => dictionary.has(status) ? t(status) : t('unknown');
  const badge = status => `<span class="admin-badge ${['pending','published','rejected','hidden','deleted','open','disabled','enabled'].includes(status) ? status : ''}">${E(statusName(status))}</span>`;
  const btn = (label, action, attrs = '', primary = false, mutation = false) => `<button type="button" class="admin-button ${primary ? 'primary' : ''}" data-act="${E(action)}" ${attrs} ${mutation ? 'data-mutate ' + (!mutable() ? 'disabled' : '') : ''}>${E(t(label))}</button>`;
  const empty = (title = 'noResults', detail = 'noResultsNote') => `<div class="admin-empty"><strong>${E(t(title))}</strong><p>${E(t(detail))}</p></div>`;
  const head = (key, intro) => `<div class="admin-page-head"><div><h1>${E(t(key))}</h1><p>${E(t(intro))}</p></div>${btn('refresh','refresh')}</div>`;
  const arr = key => Array.isArray(data?.[key]) ? data[key] : [];
  function announce(message) { const node = $('#admin-notice'); node.textContent = message; node.hidden = false; clearTimeout(noticeTimer); noticeTimer = setTimeout(() => { node.hidden = true; }, 5200); }

  class ApiError extends Error { constructor(status, code, requestId, uncertain) { super(code); this.status = status; this.code = code; this.requestId = requestId; this.uncertain = Boolean(uncertain); this.forbidden = status === 401 || status === 403; } }
  async function request(path, body, signal) {
    const controller = new AbortController(), isWrite = body !== undefined;
    const stop = () => controller.abort(); signal?.addEventListener('abort', stop, { once: true });
    if (signal?.aborted) controller.abort();
    const timeout = setTimeout(() => controller.abort(), 18000);
    try {
      const response = await fetch(path, { method: isWrite ? 'POST' : 'GET', credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json', ...(isWrite ? { 'Content-Type': 'application/json' } : {}) }, body: isWrite ? JSON.stringify(body) : undefined, signal: controller.signal });
      let result;
      try { result = await response.json(); } catch { throw new ApiError(response.status === 401 || response.status === 403 ? response.status : 0, 'INVALID_RESPONSE', null, isWrite); }
      if (!response.ok || result?.ok !== true) throw new ApiError(response.status, String(result?.error?.code || 'REQUEST_FAILED'), result?.requestId, isWrite && response.status >= 500);
      return result;
    } catch (failure) { if (failure instanceof ApiError) throw failure; throw new ApiError(0, controller.signal.aborted ? 'TIMEOUT' : 'NETWORK', null, isWrite); }
    finally { clearTimeout(timeout); signal?.removeEventListener('abort', stop); }
  }
  function validateState(value) {
    if (!value || value.ok !== true || !value.viewer || value.viewer.isAdmin !== true) throw new ApiError(value?.viewer ? 403 : 0, 'INVALID_ADMIN_STATE');
    const settings = value.settings;
    if (!settings || !Number.isInteger(settings.version) || settings.version < 0 || !['postingEnabled','commentsEnabled','likesEnabled','allowExternalLinks','cloudPresetBackupEnabled'].every(key => typeof settings[key] === 'boolean') || !settings.announcement || !supported.every(key => typeof settings.announcement[key] === 'string') || !Array.isArray(settings.catalogHiddenIds) || settings.catalogHiddenIds.some(id => typeof id !== 'string') || !value.counts || !['postsPublished','postsPending','commentsPending','reportsOpen','users','presetOwners','presetCount'].every(key => Number.isFinite(value.counts[key]) && value.counts[key] >= 0) || !['posts','comments','reports','users','audit','catalog'].every(key => Array.isArray(value[key]))) throw new ApiError(0, 'INVALID_ADMIN_STATE');
    return value;
  }
  function errorText(failure) {
    if (failure?.uncertain) return t('unconfirmed');
    return t(({ 400: 'invalid', 401: 'authNote', 403: 'forbiddenNote', 404: 'notFound', 409: 'conflict', 422: 'invalid', 429: 'tooMany', 503: 'dbUnavailable' })[failure?.status] || (failure?.code?.startsWith('INVALID_') ? 'apiInvalid' : 'readError'));
  }
  function ticket(failure) { const id = String(failure?.requestId || ''); return /^[A-Za-z0-9_-]{1,120}$/.test(id) ? `<div class="admin-error-detail">${E(t('requestTicket', { id }))}</div>` : ''; }
  function renderConnection() {
    const node = $('#admin-connection'); let title, note, cls = '';
    if (loading) { title = t('connecting'); note = ''; }
    else if (error) { title = t(error.status === 401 ? 'authRequired' : error.status === 403 ? 'forbidden' : [409,422,429].includes(error.status) ? 'actionNotCompleted' : 'unavailable'); note = errorText(error); cls = error.forbidden ? 'is-forbidden' : 'is-error'; }
    else if (data) { title = t('ready'); note = t('readyNote') + '\n' + t('actor') + ': ' + String(data.viewer.name || data.viewer.id || '—') + '\n' + t('lastRead', { at: stamp(loadedAt) }); }
    else { title = t('unavailable'); note = t('unavailableNote'); }
    if (prefs.appMode === 'offline') note += '\n' + t('userOffline');
    if (stale && data) note += '\n' + t('stale');
    node.className = 'admin-connection ' + cls;
    node.innerHTML = `<div><strong>${E(title)}</strong><p>${E(note)}</p>${ticket(error)}</div><div class="admin-connection-actions">${error?.status === 401 ? `<a class="admin-button primary" href="/signin-with-chatgpt?return_to=/admin" target="_top">${E(t('signin'))}</a>` : ''}${btn('refresh','refresh',loading || busy ? 'disabled' : '')}</div>`;
  }
  function shell() {
    document.documentElement.lang = { zh: 'zh-CN', en: 'en', ja: 'ja', de: 'de' }[lang]; document.title = brand() + ' · ' + t('app');
    $('#admin-brand').innerHTML = brandMarkup(); $('#admin-brand').setAttribute('aria-label',t('studio'));
    $('#admin-app-title').textContent = t('app'); $('#admin-mode').textContent = t('cloud'); $('#admin-language-label').textContent = t('language'); $('#admin-language').setAttribute('aria-label',t('language')); $('#admin-language').value = lang;
    $('#admin-studio-link').textContent = t('studio'); $('.admin-skip-link').textContent = t('skip'); $('#admin-sidebar-note').textContent = t('serverPermissions'); $('#admin-footer').textContent = t('footer');
    $('#admin-navigation').setAttribute('aria-label',t('app'));
    $('#admin-navigation').innerHTML = nav.map(key => `<button type="button" class="admin-nav-button ${view === key ? 'active' : ''}" data-view="${key}" ${view === key ? 'aria-current="page"' : ''}>${icon(key)}<span>${E(t(key))}</span></button>`).join('');
  }
  function titleOf(row) { const value = row?.titles?.[lang] || row?.titles?.zh || (typeof row?.title === 'object' ? row.title[lang] || row.title.zh : row?.title); return String(value || t('untitled')); }
  function contentMeta(row, type) { return `<div class="admin-row-meta"><span>${E(t(type))}</span><span>${E(row.authorName || row.userId || '—')}</span><span>${E(stamp(row.createdAt))}</span><span>${E(t('version',{n:row.version ?? '—'}))}</span></div>`; }
  function moderateButtons(row, type) {
    const attrs = `data-target-type="${type}" data-id="${E(row.id)}"`;
    if (row.status === 'pending') return `${btn('approve','review',attrs+' data-decision="approve"',true,true)}${btn('reject','review',attrs+' data-decision="reject"',false,true)}`;
    if (row.status === 'published') return btn('hide','review',attrs+' data-decision="hide"',false,true);
    if (row.status === 'hidden') return btn('restore','review',attrs+' data-decision="restore"',false,true);
    if (row.status === 'deleted' && type === 'post') return btn('restoreDraft','review',attrs+' data-decision="restore"',false,true);
    return '';
  }
  function contentCard(row, type) { return `<article class="admin-content-card"><div class="admin-content-top"><h3>${E(type === 'post' ? titleOf(row) : t('comment'))}</h3>${badge(row.status)}</div>${contentMeta(row,type)}<div class="admin-content-text">${E(row.text || '')}</div>${row.moderationReason ? `<p class="admin-note">${E(t('moderationReason'))}: ${E(row.moderationReason)}</p>` : ''}<div class="admin-action-row">${btn('preview','preview',`data-target-type="${type}" data-id="${E(row.id)}"`)}${type === 'comment' && row.postId ? btn('parentPost','preview',`data-target-type="post" data-id="${E(row.postId)}"`) : ''}${moderateButtons(row,type)}</div></article>`; }
  function selectFilter(key, values, filter) { return `<label class="admin-field"><span>${E(t(key))}</span><select data-filter="${key}" aria-label="${E(t(key))}">${values.map(value => `<option value="${value}" ${filter[key] === value ? 'selected' : ''}>${E(t(value))}</option>`).join('')}</select></label>`; }
  function toolbar(placeholder, filter, options = '') { return `<div class="admin-toolbar"><label class="admin-field search"><span>${E(t('search'))}</span><input type="search" data-filter="query" value="${E(filter.query)}" placeholder="${E(t(placeholder))}" aria-label="${E(t(placeholder))}"></label>${options}</div>`; }
  const includes = (row, query, keys) => !query || keys.some(key => String(row[key] ?? '').toLocaleLowerCase().includes(query.toLocaleLowerCase()));

  function overviewPage() {
    const metrics = [['postsPublished','publishedPosts'],['postsPending','pendingPosts'],['commentsPending','pendingComments'],['reportsOpen','openReports'],['users','totalUsers'],['presetOwners','presetOwners'],['presetCount','presetCount']];
    return `${head('overview','overviewIntro')}<div class="admin-metrics">${metrics.map(([key,label])=>`<div class="admin-metric ${key.includes('Pending')||key==='reportsOpen'?'pending':''}"><strong>${Number.isFinite(data.counts[key]) ? E(data.counts[key]) : '—'}</strong><span>${E(t(label))}</span></div>`).join('')}</div><div class="admin-grid-two"><section class="admin-panel"><div class="admin-panel-header"><h2>${E(t('publicationSwitches'))}</h2>${btn('settings','go', 'data-destination="settings"')}</div><div class="admin-compact-lines">${[['postingEnabled','publishing'],['commentsEnabled','commenting'],['likesEnabled','liking'],['allowExternalLinks','links'],['cloudPresetBackupEnabled','presetSwitch']].map(([key,label])=>`<div class="admin-compact-line"><span>${E(t(label))}</span>${badge(data.settings[key]?'enabled':'disabled')}</div>`).join('')}</div></section><section class="admin-panel"><div class="admin-panel-header"><h2>${E(t('recentAudit'))}</h2>${btn('audit','go','data-destination="audit"')}</div>${arr('audit').slice(0,5).map(row=>`<div class="admin-compact-line"><span>${E(stamp(row.at))}</span><strong>${E(actionLabel(row.action))}</strong></div>`).join('')||empty()}</section></div>${btn('openReview','go','data-destination="moderation"',true)}`;
  }
  function moderationPage() {
    const f=filters.moderation, result=[...arr('posts').map(row=>({row,type:'post'})),...arr('comments').map(row=>({row,type:'comment'}))].filter(item=>(f.type==='all'||f.type===item.type)&&(f.status==='all'||f.status===item.row.status)&&includes(item.row,f.query,['title','text','authorName','id'])).sort((a,b)=>String(b.row.createdAt||'').localeCompare(String(a.row.createdAt||'')));
    return `${head('moderation','contentIntro')}${toolbar('searchContent',f,selectFilter('type',['all','post','comment'],f)+selectFilter('status',['all','pending','published','hidden','rejected','draft','deleted'],f))}<p class="admin-note">${E(t('loaded',{n:result.length}))}</p><div class="admin-cards">${result.map(({row,type})=>contentCard(row,type)).join('')||empty()}</div>`;
  }
  function reportsPage() {
    const f=filters.reports, result=arr('reports').filter(row=>(f.status==='all'||row.status===f.status)&&includes(row,f.query,['reason','targetId','id']));
    return `${head('reports','reportIntro')}${toolbar('searchReports',f,selectFilter('status',['all','open','resolved','dismissed'],f))}<p class="admin-note">${E(t('loaded',{n:result.length}))}</p><div class="admin-cards">${result.map(row=>`<article class="admin-content-card"><div class="admin-content-top"><h3>${E(t(row.targetType==='comment'?'comment':'post'))} · ${E(row.targetId)}</h3>${badge(row.status)}</div><p class="admin-content-text">${E(row.reason||'')}</p><div class="admin-row-meta"><span>${E(stamp(row.createdAt))}</span><span>${E(t('version',{n:row.version}))}</span></div>${row.resolution?`<p class="admin-note">${E(t('resolution'))}: ${E(row.resolution)}</p>`:''}<div class="admin-action-row">${btn('preview','report-preview',`data-id="${E(row.id)}"`)}${row.status==='open'?btn('resolve','report',`data-id="${E(row.id)}" data-resolution-status="resolved"`,true,true)+btn('dismiss','report',`data-id="${E(row.id)}" data-resolution-status="dismissed"`,false,true):''}</div></article>`).join('')||empty()}</div>`;
  }
  function usersPage() {
    const f=filters.users, result=arr('users').filter(row=>(f.status==='all'||(f.status==='disabled')===Boolean(row.disabled))&&includes(row,f.query,['id','name']));
    return `${head('users','usersIntro')}${toolbar('searchUsers',f,selectFilter('status',['all','enabled','disabled'],f))}<p class="admin-note">${E(t('loaded',{n:result.length}))}</p><div class="admin-table-wrap"><table class="admin-users-table"><thead><tr>${['name','role','status','created','action'].map(key=>`<th scope="col">${E(t(key))}</th>`).join('')}</tr></thead><tbody>${result.map(row=>`<tr><td>${E(row.name||'—')}<span class="admin-table-meta">${E(row.id)}</span></td><td>${E(t(row.isAdmin?'admin':'member'))}</td><td>${badge(row.disabled?'disabled':'enabled')}</td><td>${E(stamp(row.createdAt))}</td><td>${row.isAdmin?`<small>${E(t('adminProtected'))}</small>`:btn(row.disabled?'enableUser':'disableUser','user',`data-id="${E(row.id)}"`,false,true)}</td></tr>`).join('')}</tbody></table></div>${result.length?'':empty()}`;
  }
  function settingsPage() {
    const s=data.settings;
    return `${head('settings','settingsIntro')}<form id="admin-settings-form" data-version="${E(s.version)}"><section class="admin-panel"><h2>${E(t('publicationSwitches'))}</h2><p class="admin-note">${E(t('version',{n:s.version}))}</p><div class="admin-settings-switches">${[['postingEnabled','postSwitch'],['commentsEnabled','commentSwitch'],['likesEnabled','likeSwitch'],['allowExternalLinks','linkSwitch'],['cloudPresetBackupEnabled','presetSwitch']].map(([key,label])=>`<label class="admin-switch"><input type="checkbox" name="${key}" ${s[key]?'checked':''} data-mutate ${!mutable()?'disabled':''}><span>${E(t(label))}</span></label>`).join('')}</div><p class="admin-note">${E(t('presetPrivacy'))}</p><h2>${E(t('announcement'))}</h2><p>${E(t('announcementNote'))}</p><div class="admin-announcements">${supported.map(key=>`<label class="admin-field"><span>${E(t('lang'+key[0].toUpperCase()+key.slice(1)))}</span><textarea name="announcement-${key}" lang="${key}" maxlength="1000" rows="5" data-mutate ${!mutable()?'disabled':''}>${E(s.announcement[key])}</textarea></label>`).join('')}</div><div class="admin-settings-submit"><button type="submit" class="admin-button primary" data-mutate ${!mutable()?'disabled':''}>${E(t('saveSettings'))}</button></div></section></form>`;
  }
  function catalogPage() {
    const f=filters.catalog,result=arr('catalog').filter(row=>(f.status==='all'||(f.status==='visible')===Boolean(row.visible))&&(!f.query||[titleOf(row),row.author,row.id].some(value=>String(value||'').toLocaleLowerCase().includes(f.query.toLocaleLowerCase()))));
    return `${head('catalog','catalogIntro')}<div class="admin-warning">${E(t('catalogRights'))}</div>${toolbar('searchCatalog',f,selectFilter('status',['all','visible','notVisible'],f))}<p class="admin-note">${E(t('loaded',{n:result.length}))}</p>${arr('catalog').length?`<div class="admin-table-wrap"><table class="admin-catalog-table"><thead><tr>${['piece','author','rightsStatus','visibility'].map(key=>`<th scope="col">${E(t(key))}</th>`).join('')}</tr></thead><tbody>${result.map(row=>`<tr><td>${E(titleOf(row))}<span class="admin-table-meta">${E(row.id)}</span></td><td>${E(row.author||'—')}</td><td>${E(row.rightsStatus==='pending'?t('rightsPending'):row.rightsStatus==='reviewed'?t('rightsReviewed'):row.rightsStatus||t('unknown'))}</td><td><label class="admin-switch"><input type="checkbox" data-catalog="${E(row.id)}" data-version="${E(data.settings.version)}" ${row.visible?'checked':''} data-mutate ${!mutable()?'disabled':''} aria-label="${E(t('visibility')+' · '+titleOf(row))}"><span>${E(t(row.visible?'visible':'notVisible'))}</span></label></td></tr>`).join('')}</tbody></table></div>`:empty('catalogWaiting','catalogRights')}`;
  }
  function actionLabel(value) { const raw=String(value||''); const key=raw==='moderate'?'moderation':raw==='report-resolve'?'reports':raw==='user-set'?'users':raw==='settings-save'?'settings':raw==='catalog-set'?'catalog':null; return key?t(key):raw; }
  function auditTable(result) {
    return `<div class="admin-table-wrap"><table class="admin-audit-table"><thead><tr>${['time','actor','action','target','details'].map(key=>`<th scope="col">${E(t(key))}</th>`).join('')}</tr></thead><tbody>${result.map(row=>{let detail=typeof row.detail==='string'?row.detail:JSON.stringify(row.detail??{});return `<tr><td>${E(stamp(row.at))}</td><td>${E(row.actorId||'—')}</td><td>${E(actionLabel(row.action))}</td><td>${E(row.targetType||'—')}<span class="admin-table-meta">${E(row.targetId||'—')}</span></td><td><details><summary>${E(t('details'))}</summary><pre class="admin-audit-detail">${E(detail.slice(0,3000))}</pre>${detail.length>3000?`<small>${E(t('detailsTruncated'))}</small>`:''}</details></td></tr>`;}).join('')}</tbody></table></div>`;
  }
  function auditPage() {const f=filters.audit,result=arr('audit').filter(row=>includes(row,f.query,['action','targetId','actorId']));return `${head('audit','auditIntro')}${toolbar('searchAudit',f)}<p class="admin-note">${E(t('loaded',{n:result.length}))}</p>${auditTable(result)}${result.length?'':empty()}`;}
  function plansPage() {return `${head('plans','planIntro')}<div class="admin-plan-list">${[['products','productPlan'],['courses','coursePlan'],['devices','devicePlan'],['orders','orderPlan']].map(([key,intro])=>`<section class="admin-plan-item"><h2>${E(t(key))}</h2><span class="admin-badge pending">${E(t('planned'))}</span><p>${E(t(intro))}</p></section>`).join('')}</div>`;}
  const views={overview:overviewPage,moderation:moderationPage,reports:reportsPage,users:usersPage,settings:settingsPage,catalog:catalogPage,audit:auditPage,plans:plansPage};
  function render() {shell();renderConnection();$('#admin-main').setAttribute('aria-busy',String(loading||busy));$('#admin-main').innerHTML=view==='plans'?plansPage():data?views[view]():loading?`<div class="admin-loading">${E(t('connecting'))}</div>`:empty('noData','noDataNote');}
  async function load() {
    if(busy)return;const current=++readGeneration;readAbort?.abort();readAbort=new AbortController();loading=true;error=null;render();
    try{const value=await request('/api/admin/state',undefined,readAbort.signal);if(current!==readGeneration)return;data=validateState(value);stale=false;loadedAt=new Date().toISOString();error=null;}
    catch(failure){if(current!==readGeneration)return;error=failure;stale=Boolean(data);if(failure.forbidden){data=null;stale=false;closeDialog();}}
    finally{if(current===readGeneration){loading=false;render();}}
  }
  function lockForms(value) {document.querySelectorAll('[data-mutate]').forEach(node=>{if(value){node.dataset.wasDisabled=node.disabled?'1':'0';node.disabled=true;}else{node.disabled=node.dataset.wasDisabled==='1'||!mutable();delete node.dataset.wasDisabled;}});$('#admin-main').setAttribute('aria-busy',String(value));}
  async function mutate(payload) {
    if(!mutable())return false;busy=true;readGeneration++;readAbort?.abort();lockForms(true);const modalError=$('.admin-modal-error');if(modalError)modalError.textContent='';let succeeded=false;
    try{const result=await request('/api/admin/action',payload);if(!result.state)throw new ApiError(0,'INVALID_ADMIN_STATE',null,true);data=validateState(result.state);stale=false;error=null;loadedAt=new Date().toISOString();succeeded=true;closeDialog();announce(t('saved'));return true;}
    catch(failure){error=failure;if(failure.forbidden){data=null;stale=false;closeDialog();}else if(failure.uncertain||failure.status===409||failure.status===503||failure.status===0){stale=Boolean(data);}const message=errorText(failure);if(modalError&&$('#admin-modal').open)modalError.textContent=message;announce(message);return false;}
    finally{busy=false;lockForms(false);if(data&&($('#admin-modal').open||(!succeeded&&payload.type==='settings-save')))renderConnection();else render();}
  }

  function closeDialog() {const modal=$('#admin-modal');if(modal.open)modal.close();}
  function dialog(title, html) {modalFocus=document.activeElement;$('#admin-modal-body').innerHTML=`<div class="admin-modal-head"><h2 id="admin-modal-title">${E(title)}</h2>${btn('close','close')}</div>${html}`;const modal=$('#admin-modal');if(!modal.open)modal.showModal();}
  function safeHttps(value) {try{const url=new URL(value);return url.protocol==='https:'&&!url.username&&!url.password?url.href:null;}catch{return null;}}
  function safeVideo(value){try{const u=new URL(value,location.origin);return u.origin===location.origin&&/^\/api\/community\/videos\/[A-Za-z0-9_-]+$/.test(u.pathname)&&!u.search&&!u.hash?u.pathname:null;}catch{return null;}}
  function safeMedia(value) {try{const url=new URL(value,location.origin);return url.origin===location.origin&&url.pathname.startsWith('/api/community/media/')?url.pathname+url.search:null;}catch{return null;}}
  function attachmentMarkup(attachments) {
    if(!Array.isArray(attachments)||!attachments.length)return '';
    return `<h3>${E(t('attachments'))}</h3><div class="admin-attachment-list">${attachments.map(item=>{if(item.kind==='video'){const url=safeVideo(item.url);return url?`<figure class="admin-media-figure"><video src="${E(url)}" controls playsinline preload="none" style="width:100%;max-height:60vh" aria-label="Performance video"></video><figcaption>${E(item.mime||'')} · ${E(Math.round(Number(item.duration)||0))} s · ${E(item.size??'—')}</figcaption></figure>`:`<p>${E(t('unavailableAttachment'))}</p>`;}if(item.kind==='media'){const url=safeMedia(item.url);return url?`<figure class="admin-media-figure"><img src="${E(url)}" alt="${E(t('cloudImage'))}" loading="lazy" decoding="async"><div class="admin-media-error" hidden>${E(t('imageFailed'))}</div><figcaption>${E(t('cloudImage'))} · ${E(item.mime||'')} · ${E(item.size??'—')}</figcaption></figure>`:`<p class="admin-note">${E(t('unavailableAttachment'))}</p>`;}if(item.kind==='url'){const url=safeHttps(item.url);return url?`<a class="admin-external-link" href="${E(url)}" target="_blank" rel="nofollow noopener noreferrer">${E(item.title||t('externalLink'))}<br><small>${E(url)}</small></a>`:`<p class="admin-note">${E(t('unavailableAttachment'))}</p>`;}if(item.kind==='local')return `<div class="admin-local-meta"><strong>${E(t('localMedia'))}</strong><br>${E(item.name||item.id||'—')} · ${E(item.mime||'')}</div>`;return `<p class="admin-note">${E(t('unavailableAttachment'))}</p>`;}).join('')}</div>`;
  }
  function findContent(type,id){return arr(type==='comment'?'comments':'posts').find(row=>row.id===id);}
  function contentPreview(row,type){return `${contentMeta(row,type)}${badge(row.status)}<div class="admin-modal-text">${E(row.text||'')}</div>${attachmentMarkup(row.attachments)}${row.moderationReason?`<p class="admin-note">${E(t('moderationReason'))}: ${E(row.moderationReason)}</p>`:''}<div class="admin-modal-actions">${type==='comment'&&row.postId?btn('parentPost','preview',`data-target-type="post" data-id="${E(row.postId)}"`):''}${moderateButtons(row,type)}${btn('close','close')}</div>`;}
  function preview(type,id){const row=findContent(type,id);if(!row){announce(t('missingTarget'));return;}dialog(type==='post'?titleOf(row):t('comment'),contentPreview(row,type));}
  function openReview(type,id,decision){const row=findContent(type,id);if(!row||!mutable())return;const required=decision==='reject'||decision==='hide',label=decision==='restore'&&row.status==='deleted'?'restoreDraft':decision;
    dialog(t(label),`<p class="admin-note">${E(type==='post'?titleOf(row):t('comment'))} · ${E(row.id)} · ${E(t('version',{n:row.version}))}</p><form id="admin-review-form" data-id="${E(id)}" data-type="${type}" data-decision="${E(decision)}" data-version="${E(row.version)}"><label class="admin-field"><span>${E(t('reason'))}</span><textarea name="reason" maxlength="500" rows="4" ${required?'required':''} data-mutate></textarea></label><p class="admin-note">${E(t('reasonHint'))}</p><div class="admin-modal-error" role="alert"></div><div class="admin-modal-actions">${btn('cancel','close')}<button type="submit" class="admin-button primary" data-mutate>${E(t('confirm'))}</button></div></form>`);
  }
  function openReport(id,status){const row=arr('reports').find(item=>item.id===id);if(!row||!mutable())return;dialog(t(status==='resolved'?'resolve':'dismiss'),`<p class="admin-note">${E(t('target'))}: ${E(row.targetType)} · ${E(row.targetId)}</p><div class="admin-modal-text">${E(row.reason||'')}</div><form id="admin-report-form" data-id="${E(id)}" data-version="${E(row.version)}" data-status="${status}"><label class="admin-field"><span>${E(t('resolution'))}</span><textarea name="resolution" maxlength="500" rows="4" required data-mutate></textarea></label><div class="admin-modal-error" role="alert"></div><div class="admin-modal-actions">${btn('cancel','close')}<button type="submit" class="admin-button primary" data-mutate>${E(t('confirm'))}</button></div></form>`);}
  function openUser(id){const row=arr('users').find(item=>item.id===id);if(!row||row.isAdmin||!mutable())return;dialog(t(row.disabled?'enableUser':'disableUser'),`<p>${E(t('userConfirm'))}</p><div class="admin-modal-text">${E(row.name||'—')}<br>${E(row.id)}</div><form id="admin-user-form" data-id="${E(id)}" data-version="${E(row.version)}" data-disabled="${String(!row.disabled)}"><div class="admin-modal-error" role="alert"></div><div class="admin-modal-actions">${btn('cancel','close')}<button type="submit" class="admin-button primary" data-mutate>${E(t('confirm'))}</button></div></form>`);}

  document.addEventListener('click',event=>{const target=event.target.closest('[data-view],[data-act]');if(!target||target.disabled)return;
    if(target.dataset.view){view=target.dataset.view;if(!views[view])view='overview';render();$('#admin-main').focus({preventScroll:true});return;}
    const action=target.dataset.act,id=target.dataset.id,type=target.dataset.targetType;
    if(action==='refresh'){void load();return;}if(action==='go'){view=views[target.dataset.destination]?target.dataset.destination:'overview';render();return;}
    if(action==='close'){closeDialog();return;}if(action==='preview'){preview(type,id);return;}if(action==='review'){openReview(type,id,target.dataset.decision);return;}
    if(action==='report-preview'){const row=arr('reports').find(item=>item.id===id);if(row)preview(row.targetType,row.targetId);return;}if(action==='report'){openReport(id,target.dataset.resolutionStatus);return;}if(action==='user')openUser(id);
  });
  document.addEventListener('change',event=>{const target=event.target;if(target.id==='admin-language'){lang=supported.includes(target.value)?target.value:'zh';closeDialog();render();return;}if(target.dataset.catalog){const row=arr('catalog').find(item=>item.id===target.dataset.catalog);if(!row)return;const visible=target.checked;target.checked=Boolean(row.visible);void mutate({type:'catalog-set',id:row.id,visible,version:Number(target.dataset.version)});return;}if(target.dataset.filter&&filters[view]){filters[view][target.dataset.filter]=target.value;render();}});
  document.addEventListener('input',event=>{const target=event.target;if(target.dataset.filter!=='query'||!filters[view])return;const pos=target.selectionStart;filters[view].query=target.value;$('#admin-main').innerHTML=views[view]();const next=$('[data-filter="query"]');next?.focus({preventScroll:true});try{next?.setSelectionRange(pos,pos);}catch{/* Search inputs may not expose selection ranges. */}});
  document.addEventListener('submit',event=>{const form=event.target;if(!['admin-review-form','admin-report-form','admin-user-form','admin-settings-form'].includes(form.id))return;event.preventDefault();if(!form.reportValidity()||!mutable())return;const fields=new FormData(form);let payload;
    if(form.id==='admin-review-form'){const reason=String(fields.get('reason')||'').trim();if(['reject','hide'].includes(form.dataset.decision)&&!reason){const node=$('.admin-modal-error');if(node)node.textContent=t('reasonRequired');return;}payload={type:'moderate',targetType:form.dataset.type,id:form.dataset.id,version:Number(form.dataset.version),action:form.dataset.decision,reason};}
    else if(form.id==='admin-report-form'){const resolution=String(fields.get('resolution')||'').trim();if(!resolution){$('.admin-modal-error').textContent=t('reasonRequired');return;}payload={type:'report-resolve',id:form.dataset.id,version:Number(form.dataset.version),status:form.dataset.status,resolution};}
    else if(form.id==='admin-user-form')payload={type:'user-set',id:form.dataset.id,version:Number(form.dataset.version),disabled:form.dataset.disabled==='true'};
    else payload={type:'settings-save',version:Number(form.dataset.version),postingEnabled:fields.has('postingEnabled'),commentsEnabled:fields.has('commentsEnabled'),likesEnabled:fields.has('likesEnabled'),allowExternalLinks:fields.has('allowExternalLinks'),cloudPresetBackupEnabled:fields.has('cloudPresetBackupEnabled'),announcement:Object.fromEntries(supported.map(key=>[key,String(fields.get('announcement-'+key)||'').trim()]))};
    void mutate(payload);
  });
  $('#admin-modal').addEventListener('close',()=>{const old=modalFocus;modalFocus=null;if(old?.isConnected&&!old.disabled)old.focus({preventScroll:true});else $('#admin-main').focus({preventScroll:true});});
  document.addEventListener('error',event=>{if(event.target?.matches?.('.brand-wordmark img'))event.target.parentElement.classList.add('is-failed');if(event.target?.matches?.('.admin-media-figure img')){event.target.hidden=true;const message=event.target.parentElement.querySelector('.admin-media-error');if(message)message.hidden=false;}},true);
  render();void load();
})(window);

document.addEventListener('play',event=>{if(event.target.tagName==='VIDEO')for(const v of document.querySelectorAll('video'))if(v!==event.target)v.pause();},true);document.addEventListener('visibilitychange',()=>{if(document.hidden)for(const v of document.querySelectorAll('video'))v.pause();});
