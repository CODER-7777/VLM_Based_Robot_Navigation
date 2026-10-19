/* Keep source clips until the server has accepted their upload. */
'use strict';
window.CampusUploads=(()=>{
  const memory=new Map();let database;let account='';let rows=[];let downloadUrls=[];
  function clearUrls(){for(const url of downloadUrls)URL.revokeObjectURL(url);downloadUrls=[]}
  const ready=new Promise(resolve=>{
    try{
      const request=indexedDB.open('task5-campus-pending-media',1);
      request.onupgradeneeded=()=>request.result.createObjectStore('clips',{keyPath:'id'});
      request.onsuccess=()=>{database=request.result;resolve()};request.onerror=()=>resolve();
    }catch(e){resolve()}
  });
  function transaction(mode,operation){return new Promise((resolve,reject)=>{
    if(!database){resolve(null);return}
    const tx=database.transaction('clips',mode);const result=operation(tx.objectStore('clips'));
    tx.oncomplete=()=>resolve(result?.result);tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);
  })}
  async function refresh(){
    await ready;let saved=[];try{saved=await transaction('readonly',s=>s.getAll())||[]}catch(e){}
    const merged=new Map(saved.map(r=>[r.id,r]));for(const [id,r] of memory)merged.set(id,r);
    rows=[...merged.values()].filter(r=>!account||r.owner===account);
    document.dispatchEvent(new CustomEvent('campus-pending-media',{detail:{count:rows.length}}));
    return rows;
  }
  async function keep(blob,metadata){
    await ready;const record={id:crypto.randomUUID(),blob,...metadata,created:new Date().toISOString(),owner:metadata.session.split('/')[1]};
    memory.set(record.id,record);
    try{await transaction('readwrite',s=>s.put(record))}catch(e){/* RAM copy and local download remain available. */}
    await refresh();return record.id;
  }
  async function done(id){memory.delete(id);try{await transaction('readwrite',s=>s.delete(id))}catch(e){}await refresh()}
  async function show(){
    await refresh();let dialog=document.getElementById('campus-recovery');
    if(!dialog){dialog=document.createElement('dialog');dialog.id='campus-recovery';dialog.addEventListener('close',clearUrls);document.body.appendChild(dialog)}
    clearUrls();
    dialog.replaceChildren();const title=document.createElement('h2');title.textContent='Recordings waiting for upload';dialog.appendChild(title);
    const intro=document.createElement('p');intro.textContent='Keep this browser open until clips upload. You can also download the source file for recovery.';dialog.appendChild(intro);
    if(!rows.length){const p=document.createElement('p');p.textContent='No source clips are waiting for upload.';dialog.appendChild(p)}
    for(const clip of rows){
      const item=document.createElement('div');item.className='campus-recovery-row';
      const label=document.createElement('p');label.textContent=clip.kind+' · '+(clip.blob.size/1048576).toFixed(1)+' MB · '+clip.created;item.appendChild(label);
      const download=document.createElement('a');const url=URL.createObjectURL(clip.blob);downloadUrls.push(url);download.href=url;
      const ext=clip.mime.includes('mp4')?'mp4':clip.mime.includes('ogg')?'ogg':'webm';
      download.download=clip.owner+'_'+clip.kind+'_'+clip.id+'.'+ext;download.textContent='Download source';item.appendChild(download);
      const retry=document.createElement('button');retry.textContent='Retry upload';item.appendChild(retry);
      retry.onclick=async()=>{
        retry.disabled=true;
        try{
          const query=new URLSearchParams({kind:clip.kind,mime:clip.mime,start_ms:clip.start,end_ms:clip.end,session:clip.session});
          const response=await fetch('/api/upload?'+query,{method:'POST',headers:{'Content-Type':clip.mime},body:clip.blob});
          const value=await response.json();if(!response.ok)throw Error(value.error||'Upload failed');
          await done(clip.id);await show();
        }catch(e){label.textContent=e.message+' You can keep or download the source clip.';retry.disabled=false;}
      };dialog.appendChild(item);
    }
    const close=document.createElement('button');close.textContent='Close';close.onclick=()=>dialog.close();dialog.appendChild(close);
    if(!dialog.open)dialog.showModal();
  }
  return {keep,done,show,refresh,setAccount:async value=>{account=value;return refresh()},pending:()=>rows.length};
})();
