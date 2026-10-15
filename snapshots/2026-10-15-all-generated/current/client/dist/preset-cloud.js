(function(root){
  'use strict';
  const tones=new Set(['Acoustic','Warm','Bright','Electric','Bass','Piano','Organ','Strings','Pad']);
  const languages=['zh','en','ja','de'];
  const messages={
    title:['私人云预设备份','Private preset backup','非公開プリセットのバックアップ','Private Preset-Sicherung'],
    lead:['保存命名、分组、音色和浏览器效果参数。录音与视频保留在本机，不会随预设上传。','Back up names, groups, tones and browser effects. Audio and video stay on this device.','名前・グループ・音色・ブラウザー効果を保存。録音と動画は端末内に残ります。','Sichere Namen, Gruppen, Klänge und Browser-Effekte. Audio und Video bleiben auf diesem Gerät.'],
    offline:['离线模式可保存本机预设。使用云备份时请切换到当前模式并联网登录。','Local presets work offline. Switch to the online mode and sign in to use cloud backup.','ローカル保存はオフラインで利用可能です。クラウド保存にはオンラインモードとログインが必要です。','Lokale Presets funktionieren offline. Für Cloud-Sicherung zum Online-Modus wechseln und anmelden.'],
    privacy:['仅当前登录账号可读取这份备份。它不包含录音，也不会自动写入琴身。','Only the signed-in account can read this backup. It contains no recordings and is not automatically written to the instrument.','このバックアップはログイン中のアカウントだけが読めます。録音を含まず、楽器に自動転送されません。','Nur das angemeldete Konto kann diese Sicherung lesen. Aufnahmen sind nicht enthalten; sie wird nicht automatisch ins Instrument übertragen.'],
    refresh:['读取云备份','Load cloud backup','クラウド保存を読込','Cloud-Sicherung laden'],
    save:['备份本机预设','Back up local presets','端末のプリセットを保存','Lokale Presets sichern'],
    restore:['恢复到本机','Restore to this device','端末に復元','Auf diesem Gerät wiederherstellen'],
    clear:['清空云备份','Clear cloud backup','クラウド保存を消去','Cloud-Sicherung leeren'],
    initial:['先读取当前账号的云备份，再保存或恢复。','Load the current account’s backup before saving or restoring.','保存・復元する前に現在のアカウントのバックアップを読み込んでください。','Lade vor dem Sichern oder Wiederherstellen die Sicherung des aktuellen Kontos.'],
    count:['云端 {n} 套 · 版本 {v}','{n} cloud presets · version {v}','クラウド {n} 件・バージョン {v}','{n} Cloud-Presets · Version {v}'],
    disabled:['新的云备份暂时关闭。已有备份仍可读取、恢复或清空。','New cloud backups are disabled. Existing backups can still be loaded, restored or cleared.','新しい保存は無効です。既存の保存は読込・復元・消去できます。','Neue Cloud-Sicherungen sind deaktiviert. Bestehende bleiben lesbar, wiederherstellbar und löschbar.'],
    busy:['正在处理…','Working…','処理中…','Wird verarbeitet…'],
    saved:['云端已确认备份；本机预设保留。','Cloud backup confirmed. Local presets were kept.','クラウド保存を確認しました。端末のプリセットは保持されます。','Cloud-Sicherung bestätigt. Lokale Presets wurden beibehalten.'],
    restored:['云端预设已恢复到当前浏览器。','Cloud presets restored to this browser.','クラウドのプリセットをこのブラウザーに復元しました。','Cloud-Presets in diesem Browser wiederhergestellt.'],
    cleared:['云备份已清空；本机预设和录音保留。','Cloud backup cleared. Local presets and recordings were kept.','クラウド保存を消去しました。端末のプリセットと録音は保持されます。','Cloud-Sicherung geleert. Lokale Presets und Aufnahmen bleiben erhalten.'],
    replace:['将用当前本机预设替换这份云备份。确认前可先恢复旧备份。','Replace this cloud backup with the current local presets. Restore the old backup first if you want to keep it.','現在の端末設定でクラウド保存を置き換えます。古い設定が必要なら先に復元してください。','Diese Cloud-Sicherung durch die aktuellen lokalen Presets ersetzen. Bei Bedarf zuerst die alte Sicherung wiederherstellen.'],
    clearConfirm:['仅清空当前账号的云预设备份。本机预设和媒体不受影响。','Clear only this account’s cloud preset backup. Local presets and media are kept.','現在のアカウントのクラウド保存のみを消去します。端末のプリセットとメディアは保持されます。','Nur die Cloud-Preset-Sicherung dieses Kontos leeren. Lokale Presets und Medien bleiben erhalten.'],
    confirm:['确认','Confirm','確認','Bestätigen'],cancel:['取消','Cancel','キャンセル','Abbrechen'],
    signIn:['使用站点账号登录','Sign in to this site','サイトにログイン','Auf dieser Website anmelden'],
    auth:['请先使用站点入口登录。离线基础功能仍可使用。','Sign in using the site entry. Basic offline features remain available.','サイトの入口からログインしてください。基本的なオフライン機能は使えます。','Melde dich über den Website-Einstieg an. Grundfunktionen bleiben offline nutzbar.'],
    conflict:['云备份或登录账号已变化。请重新读取后核对，不会覆盖本机预设。','The backup or signed-in account changed. Reload and review it. Local presets were not overwritten.','保存またはログインアカウントが変わりました。再読込して確認してください。端末設定は上書きされません。','Sicherung oder Konto geändert. Neu laden und prüfen. Lokale Presets wurden nicht überschrieben.'],
    uncertain:['保存结果尚未确认。请读取云备份核对，再进行下一次操作。','The save result is unconfirmed. Load the cloud backup before the next operation.','保存結果を確認できません。次の操作前にクラウド保存を読込んで確認してください。','Speicherung nicht bestätigt. Vor dem nächsten Vorgang die Cloud-Sicherung laden.'],
    unavailable:['云预设备份暂不可用，请检查网络或稍后重试。','Cloud preset backup is unavailable. Check the connection or try again later.','クラウド保存を利用できません。通信を確認するか後ほど再試行してください。','Cloud-Sicherung nicht verfügbar. Verbindung prüfen oder später erneut versuchen.'],
    invalid:['预设格式或长度不符合要求，请保留本机数据并检查。','Preset format or length is invalid. Keep local data and review the presets.','設定の形式または長さが条件を満たしません。端末のデータを保持して確認してください。','Preset-Format oder Länge ungültig. Lokale Daten behalten und prüfen.'],
    suspended:['当前账号已暂停云端提交；本机功能仍可使用。','Cloud submissions are suspended for this account. Local features remain available.','このアカウントのクラウド送信は停止されています。端末内の機能は使えます。','Cloud-Übermittlungen für dieses Konto gesperrt. Lokale Funktionen bleiben nutzbar.'],
    none:['本机没有可备份的预设。请先保存一套音色。','There are no local presets to back up. Save a tone first.','保存する端末設定がありません。まず音色を保存してください。','Keine lokalen Presets vorhanden. Zuerst einen Klang speichern.'],
    full:['恢复未完成：请检查本机保存空间或预设数量，云备份保留。','Restore did not finish. Check local storage and preset count. The cloud backup was kept.','復元が完了しませんでした。端末の容量と設定数を確認してください。クラウド保存は保持されます。','Wiederherstellung nicht abgeschlossen. Speicher und Preset-Anzahl prüfen. Cloud-Sicherung bleibt erhalten.']
  };
  const escape=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  function records(value){
    if(!Array.isArray(value)||value.length>100)throw Error('invalid');const ids=new Set();
    return value.map(item=>{
      if(!item||typeof item!=='object'||Array.isArray(item)||typeof item.id!=='string'||!/^[a-zA-Z0-9_-]{1,160}$/.test(item.id)||ids.has(item.id)||typeof item.name!=='string'||!item.name.trim()||item.name.length>80||!tones.has(item.preset))throw Error('invalid');
      ids.add(item.id);const group=item.group??'',inputGain=item.inputGain??1;if(typeof group!=='string'||group.length>60||typeof inputGain!=='number'||!Number.isFinite(inputGain)||inputGain<0||inputGain>2)throw Error('invalid');
      const effects={};for(const key of ['volume','reverb','delay','compression']){const number=item.effects?.[key];if(typeof number!=='number'||!Number.isFinite(number)||number<0||number>1)throw Error('invalid');effects[key]=number;}
      return {id:item.id,name:item.name.trim(),group:group.trim(),preset:item.preset,effects,inputGain};
    });
  }
  async function request(body){
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);let response;
    try{response=await root.fetch('/api/presets',{method:body?'POST':'GET',credentials:'same-origin',cache:'no-store',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined,signal:controller.signal});var data=await response.json();}
    catch(cause){const error=Error('unavailable');error.uncertain=!!body;error.cause=cause;throw error;}
    finally{clearTimeout(timeout);}
    if(!response.ok||data?.ok!==true){const error=Error(data?.error?.code||'unavailable');error.status=response.status;error.uncertain=!!body&&response.status>=500;throw error;}
    try{if(typeof data.viewer?.id!=='string'||!data.viewer.id||!Number.isSafeInteger(data.backup?.version)||data.backup.version<0||typeof data.features?.cloudPresetBackupEnabled!=='boolean')throw Error();return {viewer:{id:data.viewer.id},backup:{version:data.backup.version,updatedAt:data.backup.updatedAt,presets:records(data.backup.presets)},features:data.features};}
    catch{const error=Error('unavailable');error.uncertain=!!body;throw error;}
  }
  function mount(container,options={}){
    if(typeof container==='string')container=root.document.querySelector(container);if(!container)return null;
    let state=null,busy=false,pending=null,message='',kind='info',disposed=false;const lang=languages.includes(options.lang)?options.lang:'zh';
    function text(key,args={}){let value=messages[key]?.[languages.indexOf(lang)]||key;for(const [name,replacement]of Object.entries(args))value=value.replace('{'+name+'}',String(replacement));return value;}
    const local=()=>records(typeof options.getPresets==='function'?options.getPresets():[]);
    function render(){if(disposed||!container.isConnected)return;const offline=options.mode==='offline',cloud=state?.backup;
      container.innerHTML='<section class="panel preset-cloud-panel" aria-label="'+escape(text('title'))+'"><div class="panel-header"><h3>'+escape(text('title'))+'</h3></div><p class="help-text">'+escape(text('lead'))+'</p>'+(offline?'<p class="preset-cloud-status">'+escape(text('offline'))+'</p>':'<p class="preset-cloud-status">'+escape(cloud?text('count',{n:cloud.presets.length,v:cloud.version}):text('initial'))+'</p>'+(cloud?.updatedAt?'<small>'+escape(new Date(cloud.updatedAt).toLocaleString({zh:'zh-CN',en:'en',ja:'ja-JP',de:'de-DE'}[lang]))+'</small>':'')+(state&&!state.features.cloudPresetBackupEnabled?'<p class="help-text">'+escape(text('disabled'))+'</p>':'')+'<div class="preset-cloud-actions">'+[['refresh',false],['save',!state||!state.features.cloudPresetBackupEnabled],['restore',!cloud?.presets.length],['clear',!cloud?.presets.length]].map(([key,disabled])=>'<button type="button" class="button '+(key==='save'?'primary':'secondary')+'" data-preset-cloud="'+key+'"'+(busy||disabled?' disabled':'')+'>'+escape(text(key))+'</button>').join('')+'</div>')+(pending?'<div class="preset-cloud-confirm"><p>'+escape(text(pending==='save'?'replace':'clearConfirm'))+'</p><div class="preset-cloud-actions"><button type="button" class="button primary" data-preset-cloud="confirm">'+escape(text('confirm'))+'</button><button type="button" class="button secondary" data-preset-cloud="cancel">'+escape(text('cancel'))+'</button></div></div>':'')+(message?'<p class="preset-cloud-feedback '+escape(kind)+'" role="status" aria-live="polite">'+escape(message)+'</p>':'')+'<p class="help-text">'+escape(text('privacy'))+'</p>'+(kind==='auth'?'<a class="button secondary" href="/signin-with-chatgpt?return_to=%2F%23tones">'+escape(text('signIn'))+'</a>':'')+'</section>';
    }
    function notice(key,type='info'){message=text(key);kind=type;render();if(typeof options.onNotice==='function')options.onNotice(message);}
    async function execute(action){if(disposed||busy||options.mode==='offline')return;
      if(action==='cancel'){pending=null;render();return;}
      if(action==='confirm'){action=pending;pending=null;if(!action)return;}
      else if(['save','clear'].includes(action)&&state?.backup?.presets.length){pending=action;render();return;}
      busy=true;message=text('busy');kind='info';render();
      try{
        if(action==='refresh'){state=await request();message='';kind='info';}
        else if(action==='restore'){
          if(!state?.backup?.presets.length||typeof options.onRestore!=='function')throw Error('full');
          const expected=state,latest=await request();
          if(latest.viewer.id!==expected.viewer.id||latest.backup.version!==expected.backup.version){const error=Error('conflict');error.status=409;throw error;}
          state=latest;
          const result=await options.onRestore(structuredClone(state.backup.presets),{accountId:state.viewer.id,version:state.backup.version});if(result===false)throw Error('full');notice('restored');
        }else if(action==='save'||action==='clear'){
          if(!state)throw Error('conflict');const value=action==='save'?local():[];if(action==='save'&&!value.length)throw Error('none');
          const payload={type:action,version:state.backup.version,accountId:state.viewer.id,...(action==='save'?{presets:value}:{})};
          if(new TextEncoder().encode(JSON.stringify(payload)).length>32768)throw Error('invalid');
          state=await request(payload);notice(action==='save'?'saved':'cleared');
        }
      }catch(error){pending=null;
        if(error.uncertain){state=null;notice('uncertain','error');}
        else if(error.status===401){state=null;notice('auth','auth');}
        else if(error.status===409){state=null;notice('conflict','error');}
        else if(error.message==='FEATURE_DISABLED'){if(state)state.features.cloudPresetBackupEnabled=false;notice('disabled','error');}
        else if(error.message==='USER_DISABLED')notice('suspended','error');
        else notice(error.status===422||error.status===413?'invalid':messages[error.message]?error.message:'unavailable','error');
      }finally{busy=false;render();}
    }
    const listener=event=>{const button=event.target.closest('[data-preset-cloud]');if(button&&container.contains(button)&&!button.disabled)void execute(button.dataset.presetCloud);};
    container.addEventListener('click',listener);render();return {dispose(){disposed=true;container.removeEventListener('click',listener);}};
  }
  root.SVPresetCloud=Object.freeze({mount,normalize:records});
})(window);
