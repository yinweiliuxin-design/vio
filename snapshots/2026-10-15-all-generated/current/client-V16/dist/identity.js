/* Read-only, same-site account diagnostics for administrator configuration. */
(() => {
  'use strict';
  const panel=document.getElementById('admin-identity');
  if(!panel)return;
  let lang='zh';try{lang=JSON.parse(localStorage.getItem('sv12-prefs')||'{}').lang||'zh';}catch{}
  const labels={zh:['当前站点账号编号','管理权限已确认','尚未获得管理权限','该编号用于核对本站的管理员授权。'],en:['Your Site account ID','Administrator access confirmed','Administrator access not granted','Use this ID to check administrator authorization for this Site.'],ja:['このサイトのアカウントID','管理権限を確認済み','管理権限は未付与','このIDでサイトの管理者権限を確認できます。'],de:['Deine Site-Konto-ID','Administratorzugriff bestätigt','Kein Administratorzugriff','Mit dieser ID kann die Administratorberechtigung dieser Site geprüft werden.']};
  let viewer=null;
  function draw(){
    if(!viewer)return;const copy=labels[lang]||labels.zh;
    const heading=document.createElement('strong'),id=document.createElement('code'),note=document.createElement('small');
    heading.textContent=copy[0]+' · '+copy[viewer.isAdmin===true?1:2];id.textContent=viewer.id;note.textContent=copy[3];
    panel.replaceChildren(heading,id,note);panel.hidden=false;
  }
  document.getElementById('admin-language')?.addEventListener('change',event=>{lang=event.target.value;draw();});
  fetch('/api/identity',{credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}}).then(async response=>{
    const data=await response.json();
    if(!response.ok||data.ok!==true||typeof data.viewer?.id!=='string'||data.viewer.id.length>256)return;
    viewer=data.viewer;draw();
  }).catch(()=>{});
})();
