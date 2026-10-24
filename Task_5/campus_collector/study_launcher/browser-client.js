/* Local launcher lifetime and account-scoped crash recovery. No passwords stored. */
(()=>{
  'use strict';
  if(window.StudyLauncher)return;
  const nativeFetch=window.fetch.bind(window),page=crypto.randomUUID();
  const writers=new Set(),captures=new Map();let owner='',database,storageFailed=false;
  let presence,connected=false;
  function connectPresence(){
    if(presence?.readyState!==undefined&&presence.readyState!==EventSource.CLOSED)return;
    presence=new EventSource('/_study/presence/'+page);
    presence.onopen=()=>connected=true;presence.onerror=()=>connected=false;
  }
  function heartbeat(open=true){
    if(open&&connected)return;
    const body=JSON.stringify({id:page,open});
    if(!open&&navigator.sendBeacon){navigator.sendBeacon('/_study/page',new Blob([body],{type:'application/json'}));return;}
    nativeFetch('/_study/page',{method:'POST',headers:{'Content-Type':'application/json'},body,keepalive:true}).catch(()=>{});
  }
  connectPresence();heartbeat();setInterval(()=>heartbeat(),15000);
  addEventListener('pageshow',()=>{connectPresence();heartbeat()});
  addEventListener('focus',()=>heartbeat());
  document.addEventListener('visibilitychange',()=>heartbeat());
  addEventListener('pagehide',()=>{saveDraft();presence?.close();connected=false;heartbeat(false)});

  // Keep current and older worker pages consistent with the study's live
  // narration protocol. Upload/capture controls and saved media stay intact.
  function narrationGuidance(){
    const instruction='Speak while navigating. Explain what you see, which memory it matches, and why you turn, move forward, change direction or stop. Record screen + microphone captures your voice.';
    const template=document.getElementById('template');
    if(template&&template.textContent!==instruction)template.textContent=instruction;
    for(const id of ['voice','focus-voice']){const button=document.getElementById(id);if(button)button.hidden=true;}
    const label=document.getElementById('clip-kind')?.closest('label');if(label)label.hidden=true;
    const summary=document.querySelector('#voice-template > summary');
    if(summary&&summary.textContent!=='What to say while navigating')summary.textContent='What to say while navigating';
    for(const part of ['before','decision','passing','correction','arrival']){
      const example=document.getElementById('voice-'+part);
      if(example?.textContent==='Use your overall explanation for the current task.')example.textContent='I will [turn left / turn right / move forward / stop] because [evidence in my current view and the relevant memory].';
    }
    const hint=document.getElementById('annotation')?.nextElementSibling;
    if(hint?.classList.contains('hint')&&hint.textContent!==instruction)hint.textContent=instruction;
    const message=document.getElementById('message');
    if(message?.textContent==='Sample created. Record reasoning, or use Record screen + microphone for the focused view.'){
      message.textContent='Sample created. Click Record screen + microphone and explain your decisions aloud while navigating.';
    }
  }
  function installNarrationGuidance(){
    narrationGuidance();
    for(const id of ['voice-template','message']){
      const target=document.getElementById(id);
      if(target)new MutationObserver(narrationGuidance).observe(target,{childList:true,subtree:true,characterData:true});
    }
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',installNarrationGuidance,{once:true});
  else installNarrationGuidance();

  const ready=new Promise(resolve=>{
    try{
      const request=indexedDB.open('task5-launcher-recovery',2);
      request.onupgradeneeded=()=>{
        if(!request.result.objectStoreNames.contains('clips'))request.result.createObjectStore('clips',{keyPath:'id'});
        if(!request.result.objectStoreNames.contains('chunks')){
          const chunks=request.result.createObjectStore('chunks',{keyPath:['clip','index']});chunks.createIndex('clip','clip');
        }
        if(!request.result.objectStoreNames.contains('drafts'))request.result.createObjectStore('drafts',{keyPath:'id'});
      };
      request.onsuccess=()=>{database=request.result;resolve()};
      request.onerror=()=>{storageFailed=true;resolve()};
    }catch(e){storageFailed=true;resolve()}
  });
  async function transaction(names,mode,operation){
    await ready;if(!database)throw Error('Local recovery storage is unavailable.');
    return new Promise((resolve,reject)=>{
      let tx;try{tx=database.transaction(names,mode,{durability:'strict'})}catch(e){tx=database.transaction(names,mode)}
      let result;try{result=operation(tx)}catch(e){tx.abort();reject(e);return}
      tx.oncomplete=()=>resolve(result?.result);
      tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error||Error('Recovery write interrupted.'));
    });
  }
  const clips=()=>transaction(['clips'],'readonly',tx=>tx.objectStore('clips').getAll());
  async function removeClip(id){
    await transaction(['clips','chunks'],'readwrite',tx=>{
      tx.objectStore('clips').delete(id);
      const request=tx.objectStore('chunks').index('clip').openCursor(IDBKeyRange.only(id));
      request.onsuccess=()=>{const cursor=request.result;if(cursor){cursor.delete();cursor.continue()}};
    });
  }
  function warning(){
    storageFailed=true;
    status('Local backup could not be saved. Keep this page open and finish uploading before closing.');
  }
  function status(text){
    let box=document.getElementById('study-launcher-recovery-note');
    if(!box){box=document.createElement('p');box.id='study-launcher-recovery-note';box.setAttribute('role','status');
      box.style.cssText='background:#fff3cd;color:#392c00;padding:12px;border:1px solid #ab8100;';document.body?.prepend(box)}
    box.textContent=text;
  }
  const identity=nativeFetch('/auth/me').then(async response=>{
    if(response.ok){const value=await response.json();owner=value.username||'';}return owner;
  }).catch(()=>'');
  function context(){
    try{
      if(typeof currentSession!=='undefined'&&currentSession&&/^sessions\/[A-Za-z0-9_-]+\/[^/]+$/.test(currentSession)){
        return {session:currentSession,start:typeof elapsed==='function'?elapsed():0};
      }
    }catch(e){}
    return null;
  }
  function track(promise){writers.add(promise);promise.finally(()=>writers.delete(promise)).catch(()=>{});return promise}
  if(window.MediaRecorder){
    const Original=window.MediaRecorder;
    window.MediaRecorder=class extends Original{
      constructor(stream,options){
        const study=context(),kind=stream.getVideoTracks().length?'screen':'voice';
        const mime=kind==='screen'?'video/webm;codecs=vp8,opus':'audio/webm;codecs=opus';
        super(stream,study&&Original.isTypeSupported(mime)?{...options,mimeType:mime}:options);
        let record,chain=Promise.resolve(),index=0;
        this.addEventListener('start',()=>{
          const sample=context();if(!sample)return;
          record={id:crypto.randomUUID(),session:sample.session,start:sample.start,end:sample.start,
            kind,mime:this.mimeType,bytes:0,created:new Date().toISOString(),complete:false};
          captures.set(record.id,record);
          chain=identity.then(async()=>{
            if(!owner||sample.session.split('/')[1]!==owner){record=null;return}
            record.owner=owner;
            await transaction(['clips'],'readwrite',tx=>tx.objectStore('clips').put(record));
            navigator.storage?.persist?.().catch(()=>{});
          }).catch(warning);
          track(chain);
        });
        this.addEventListener('dataavailable',event=>{
          if(!record||!event.data.size)return;
          const blob=event.data,sequence=index++;
          chain=chain.then(async()=>{
            if(!record?.owner)return;
            record.bytes+=blob.size;record.end=context()?.start??record.end;
            await transaction(['clips','chunks'],'readwrite',tx=>{
              tx.objectStore('chunks').put({clip:record.id,index:sequence,blob});
              tx.objectStore('clips').put(record);
            });
          }).catch(warning);
          track(chain);
        });
        this.addEventListener('stop',()=>{
          if(!record)return;
          chain=chain.then(async()=>{
            if(!record?.owner)return;
            record.complete=true;record.end=context()?.start??record.end;
            await transaction(['clips'],'readwrite',tx=>tx.objectStore('clips').put(record));
          }).catch(warning);
          track(chain);
        });
      }
    };
  }

  // Retire only the matching backup after its complete original upload is accepted.
  window.fetch=async function(input,options){
    const url=new URL(input instanceof Request?input.url:String(input),location.href);
    const uploading=url.origin===location.origin&&url.pathname==='/api/upload'&&options?.body instanceof Blob;
    let matching=[];
    if(uploading){
      await Promise.all([...writers]);
      try{matching=(await clips()).filter(clip=>clip.owner===owner&&clip.complete&&clip.session===url.searchParams.get('session')&&clip.kind===url.searchParams.get('kind')&&clip.bytes===options.body.size)}catch(e){}
    }
    const response=await nativeFetch(input,options);
    if(uploading&&response.ok){
      for(const clip of matching){await removeClip(clip.id).catch(warning);captures.delete(clip.id)}
    }
    return response;
  };

  let restoredKey='',lastDraft='',restoring=false;const editedDrafts=new Set();
  function draftContext(){
    if(!owner)return null;
    try{
      if(location.pathname==='/admin'&&typeof state!=='undefined'&&state?.users&&typeof selectedUser!=='undefined'){
        return {key:'study-launcher-draft:'+owner+':admin',admin:true};
      }
      if(typeof caseData!=='undefined'&&caseData?.episode_key&&document.getElementById('reasoning')){
        return {key:'study-launcher-draft:'+owner+':'+(context()?.session||'episode:'+caseData.episode_key),admin:false};
      }
    }catch(e){}
    return null;
  }
  function saveDraft(){
    const info=draftContext();if(!info)return;
    try{
      let value;
      if(info.admin){
        value={user:selectedUser,keys:[...selected],dirty:!!dirty,revision:state.users.find(p=>p.username===selectedUser)?.revision};
      }else{
        value={text:document.getElementById('reasoning').value,memory_ids:[...document.querySelectorAll('.memory-choice:checked')].map(x=>x.value)};
      }
      const encoded=JSON.stringify(value);
      if(encoded!==lastDraft){
        try{localStorage.setItem(info.key,encoded)}catch(e){}
        lastDraft=encoded;
        track(transaction(['drafts'],'readwrite',tx=>tx.objectStore('drafts').put({id:info.key,owner,value:encoded})).catch(warning));
      }
    }catch(e){warning()}
  }
  async function restoreDraft(){
    if(restoring)return;
    const info=draftContext();if(!info)return;
    if(restoredKey!==info.key){
      restoredKey=info.key;lastDraft='';restoring=true;
      try{
        let record;try{record=await transaction(['drafts'],'readonly',tx=>tx.objectStore('drafts').get(info.key))}catch(e){}
        const saved=JSON.parse(record?.value||localStorage.getItem(info.key)||'null');
        if(saved&&!editedDrafts.has(info.key)){
          if(info.admin&&saved.dirty){
            const person=state.users.find(p=>p.username===saved.user);
            if(person?.role==='contributor'){
              const allowed=new Set(state.instructions.filter(t=>t.assignable).map(t=>t.key));
              selectedUser=saved.user;selected=new Set(saved.keys.filter(key=>allowed.has(key)));dirty=true;
              renderPeople();renderTasks();
              message('Unsaved assignment restored. Review it, then click Save.');
            }
          }else if(!info.admin){
            document.getElementById('reasoning').value=saved.text||'';
            const wanted=new Set(saved.memory_ids||[]);
            document.querySelectorAll('.memory-choice').forEach(box=>box.checked=wanted.has(box.value));
          }
        }
      }catch(e){}finally{restoring=false}
    }
    saveDraft();
  }
  function changed(){const info=draftContext();if(info){editedDrafts.add(info.key);saveDraft()}}
  document.addEventListener('input',changed);
  document.addEventListener('change',changed);

  let noticeShown=false;
  async function showRecovery(){
    const records=(await clips()).filter(clip=>clip.owner===owner&&clip.bytes>0);
    let dialog=document.getElementById('study-launcher-recovery');
    if(!dialog){dialog=document.createElement('dialog');dialog.id='study-launcher-recovery';document.body.append(dialog)}
    dialog.replaceChildren();const title=document.createElement('h2');title.textContent='Recover interrupted recordings';dialog.append(title);
    const note=document.createElement('p');note.textContent='These are locally saved parts. The final seconds may be missing. Upload only to the original sample.';dialog.append(note);
    for(const clip of records){
      const line=document.createElement('p');line.textContent=clip.kind+' · '+(clip.bytes/1048576).toFixed(1)+' MB · '+clip.created;dialog.append(line);
      const upload=document.createElement('button');upload.textContent='Upload saved part';
      upload.disabled=context()?.session!==clip.session;
      const download=document.createElement('button');download.textContent='Download saved part';
      async function blob(){
        const rows=await transaction(['chunks'],'readonly',tx=>tx.objectStore('chunks').index('clip').getAll(IDBKeyRange.only(clip.id)));
        return new Blob(rows.sort((a,b)=>a.index-b.index).map(row=>row.blob),{type:clip.mime});
      }
      upload.onclick=async()=>{
        upload.disabled=true;
        try{
          const data=await blob(),query=new URLSearchParams({session:clip.session,kind:clip.kind,mime:clip.mime,start_ms:clip.start,end_ms:clip.end});
          const response=await nativeFetch('/api/upload?'+query,{method:'POST',headers:{'Content-Type':clip.mime},body:data});
          if(!response.ok){const value=await response.json();throw Error(value.error||'Upload failed')}
          await removeClip(clip.id);line.textContent='Saved part uploaded. Video preparation continues on the server.';download.remove();upload.remove();
        }catch(e){line.textContent=e.message;upload.disabled=context()?.session!==clip.session;}
      };
      download.onclick=async()=>{
        const url=URL.createObjectURL(await blob()),link=document.createElement('a');
        link.href=url;link.download=clip.kind+'_recovered.webm';link.click();setTimeout(()=>URL.revokeObjectURL(url),60000);
      };
      dialog.append(upload,download);
    }
    const close=document.createElement('button');close.textContent='Later';close.onclick=()=>dialog.close();dialog.append(close);
    if(!dialog.open)dialog.showModal();
  }
  async function checkRecovery(){
    if(!owner||noticeShown)return;
    try{
      const pending=(await clips()).filter(clip=>clip.owner===owner&&clip.bytes>0&&!captures.has(clip.id));
      if(!pending.length)return;noticeShown=true;
      status('An interrupted recording was found. Continue the same sample and recover its saved part.');
      const button=document.createElement('button');button.id='study-launcher-recover';button.textContent='Recover recording';button.onclick=()=>showRecovery().catch(warning);
      document.getElementById('study-launcher-recovery-note').append(' ',button);
    }catch(e){warning()}
  }
  setInterval(()=>{restoreDraft();checkRecovery()},1000);
  window.StudyLauncher={flush:()=>Promise.all([...writers]),recover:showRecovery};
})();
