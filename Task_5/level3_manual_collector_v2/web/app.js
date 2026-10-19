'use strict';
const $ = id => document.getElementById(id);
let caseData, currentState, currentSession=null, active=false, finished=false;
let voice=null, screen=null, pendingUploads=0, lastVoiceRange=null;
let started=0, timerFrozen=0, actionQueue=[], pumpBusy=false, heldKeys=new Set();
let userTimer, userSequence=0, savedSessions=[], selectionSource='episode_default', imageMemory=null, imageIndex=0;
let pollBusy=false, reachedAnnounced=false, knownReadyJobs=new Set();
let stoppingSample=false, stopPromise=null;
let noticeTimer=null;
let savedRefreshBusy=false, previewSession=null, previewChoice=null, previewUserChosen=false;
let screenStarting=false;
let environmentChoices=[], environmentSwitching=false;
const environmentNames={
  QUCTc6BB5sX:'Mary & Riya',
  '2azQ1b91cZZ':'Asha & Maya',
  TbHJrupSAjP:'Nora & Leo',
  EU6Fwq7SyZv:'Riya, Oliver & Sam'
};
const episodeNames={
  QUCTc6BB5sX_6120:'Help Mary after exercise',
  QUCTc6BB5sX_8247:'Prepare the kids’ school clothes',
  '2azQ1b91cZZ_3919':'Asha’s morning tea',
  TbHJrupSAjP_7120:'Help Nora with her phone',
  TbHJrupSAjP_10286:'Another round of board games',
  QUCTc6BB5sX_3568:'Food for today’s outing',
  '2azQ1b91cZZ_4240':'Return parcel for the courier',
  EU6Fwq7SyZv_10664:'Riya’s school things',
  '2azQ1b91cZZ_7372':'Help Asha read after dinner',
  EU6Fwq7SyZv_5784:'Pack Riya’s toiletries for the trip'
};
function environmentName(environment){
  const index=environmentChoices.findIndex(item=>item.scene===environment.scene)+1;
  return environmentNames[environment.scene]?'Environment '+index+' · '+environmentNames[environment.scene]:environment.label;
}
function episodeName(episode){return episodeNames[episode.episode_key]||episode.title||episode.episode_key;}
const elapsed=()=>started ? Math.round(performance.now()-started) : 0;
function notice(message){
  clearTimeout(noticeTimer);$('message').textContent=message;
  if(message)noticeTimer=setTimeout(()=>{$('message').textContent='';},4500);
}
function event(message){
  const li=document.createElement('li');li.textContent=(elapsed()/1000).toFixed(1)+'s · '+message;
  $('timeline').append(li);
  while($('timeline').children.length>120)$('timeline').firstChild.remove();
}
async function api(path,data){
  const result=await fetch(path,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const value=await result.json();if(!result.ok)throw Error(value.error||'Request failed');return value;
}
function selected(){return [...document.querySelectorAll('.memory-choice:checked')].map(x=>x.value);}
function selectMemories(ids){
  const wanted=new Set(ids&&ids.length?ids:caseData.default_relevant_memory_ids);
  document.querySelectorAll('.memory-choice').forEach(x=>x.checked=wanted.has(x.value));
}
function banner(){
  $('task-title').textContent=$('request').value;
  $('task-state').textContent=$('current-state').value;
}
function episodeOptions(scene){
  const environment=environmentChoices.find(item=>item.scene===scene),selector=$('episode-select');
  selector.replaceChildren();
  for(const episode of environment?.episodes||[]){
    const option=document.createElement('option');option.value=episode.episode_key;
    option.textContent='Episode '+String(episode.index).padStart(2,'0')+' · '+episodeName(episode);
    option.title=episode.request||episode.title;selector.append(option);
  }
}
function syncEnvironmentSelection(){
  if(!caseData)return;
  $('environment-select').value=caseData.scene;episodeOptions(caseData.scene);
  $('episode-select').value=caseData.episode_key;
}
function applyCase(value){
  caseData=value;$('dashboard-title').textContent=episodeName(value)||'Level 3 navigation';
  document.title=(episodeName(value)||'Level 3 navigation')+' · Collector V2';
  $('request').value=value.default_request;$('current-state').value=value.default_current_state;
  $('memories').replaceChildren();value.memories.forEach((memory,index)=>$('memories').append(memoryCard(memory,index+1)));
  selectMemories(value.default_relevant_memory_ids);selectionSource='episode_default';
  $('template').textContent='State the task and what you already carry. Recall the relevant speaker’s exact statement. Describe what is visible now. Explain the next movement and how you will recognize arrival.';
  for(const part of ['before','decision','passing','correction','arrival']){
    if(value.voice_examples?.[part])$('voice-'+part).textContent='“'+value.voice_examples[part]+'”';
  }
  const environment=environmentChoices.find(item=>item.scene===value.scene);
  $('episode-info').textContent=(environment?environmentName(environment)+' · ':'')+value.scene+
    ' · Episode '+String(value.index||'').padStart(2,'0')+' · '+episodeName(value);
  imageMemory=null;if($('image-dialog').open)$('image-dialog').close();
  syncEnvironmentSelection();banner();
}
async function selectEpisode(episodeKey){
  if(active||voice||screen||screenStarting||pendingUploads||stoppingSample||environmentSwitching){
    notice('STOP & save the current sample before changing environments.');syncEnvironmentSelection();return;
  }
  if(currentState?.processing){notice('Wait for the MP4 exports before changing environments.');syncEnvironmentSelection();return;}
  environmentSwitching=true;update(currentState);$('connection').textContent='Loading environment…';
  try{
    const state=await api('/api/select',{episode_key:episodeKey});
    resetView();applyCase(state.case);update(state,true);
    notice('Environment loaded. Review the task and memories, then create a new sample.');
  }catch(e){notice(e.message);syncEnvironmentSelection();}
  finally{environmentSwitching=false;update(currentState);$('connection').textContent='Scene connected';}
}
function showLinks(id,items){
  const root=$(id),signature=JSON.stringify(items);
  if(root.dataset.signature===signature)return;
  root.dataset.signature=signature;root.replaceChildren();root.hidden=!items.length;
  for(const item of items){
    const link=document.createElement('a');link.href=item.url;link.download=item.filename;
    link.textContent=item.label||('Download reasoning audio · '+item.filename);root.append(link);
  }
}
function applyFrame(s){if(s.frame_data_url)$('scene').src=s.frame_data_url;}
function updatePreview(s){
  const panel=$('sample-preview'),video=$('sample-video'),selector=$('preview-recording');
  panel.hidden=!s.finished;
  if(!s.finished){
    if(video.dataset.source){video.pause();video.removeAttribute('src');video.load();delete video.dataset.source;}
    previewSession=null;return;
  }
  if(previewSession!==s.session_id){previewSession=s.session_id;previewChoice=null;previewUserChosen=false;}
  const recordings=(s.videos||[]).filter(item=>item.filename.endsWith('.mp4'));
  const signature=JSON.stringify(recordings);
  if(selector.dataset.signature!==signature){
    selector.replaceChildren();selector.dataset.signature=signature;
    for(const item of recordings){
      const option=document.createElement('option');option.value=item.filename;
      option.textContent=item.filename==='navigation.mp4'?'Navigation replay':'Screen recording · '+item.filename;
      selector.append(option);
    }
  }
  const recording=(previewUserChosen&&recordings.find(item=>item.filename===previewChoice))||
    recordings.find(item=>item.filename.startsWith('screen_'))||recordings[0];
  $('preview-choice').hidden=recordings.length<2;video.hidden=!recording;
  $('preview-note').textContent=recording?'Press Play to review the saved recording.':
    s.processing?'Preparing your video preview…':'No saved video is available for this sample.';
  if(recording){
    previewChoice=recording.filename;selector.value=previewChoice;
    if(video.dataset.source!==recording.url){video.pause();video.src=recording.url;video.dataset.source=recording.url;video.load();}
  }
}
function update(s,force=false){
  if(!force&&currentState&&s.session_id===currentSession&&s.actions<currentState.actions)return;
  const episodeJustFinished=s.finished&&!finished;
  let refreshSaved=s.finished&&(!finished||s.session_id!==currentSession);
  currentState=s;currentSession=s.session_id;active=s.active;finished=s.finished;applyFrame(s);
  $('steps').textContent=s.actions+' actions';$('distance').textContent=s.path_length_m.toFixed(2)+' m walked';
  $('record-status').textContent=active?'Recording':finished?'Completed':'No sample';
  timerFrozen=s.elapsed_seconds||0;
  $('annotator').disabled=active||!!voice||!!screen||screenStarting||pendingUploads>0;
  $('new-user').disabled=active||!!voice||!!screen||screenStarting||pendingUploads>0;
  $('start').disabled=active||!!voice||!!screen||screenStarting||pendingUploads>0||s.processing||environmentSwitching;
  for(const id of ['environment-select','episode-select']){
    $(id).disabled=active||!!voice||!!screen||screenStarting||pendingUploads>0||s.processing||stoppingSample||environmentSwitching;
  }
  const episodeCount=environmentChoices.find(item=>item.scene===caseData?.scene)?.episodes.length;
  $('environment-note').textContent=environmentSwitching?'Loading the selected environment…':
    active?'STOP & save before changing environments.':
    episodeCount?episodeCount+' episodes in this environment. Episode numbers match the full presentation.':
    'Choose an environment and episode from the presentation.';
  $('request').disabled=active||finished;$('current-state').disabled=active||finished;
  $('stop').disabled=!active||stoppingSample;
  document.querySelectorAll('[data-action]').forEach(x=>x.disabled=!active||stoppingSample);
  for(const id of ['voice','focus-voice']){
    $(id).disabled=pendingUploads>0||stoppingSample||screenStarting;
    $(id).textContent=voice?'Stop reasoning recording':'Record reasoning';
  }
  for(const id of ['screen','focus-screen']){
    $(id).disabled=pendingUploads>0||stoppingSample||screenStarting;
    $(id).textContent=screen?'Stop screen recording':'Record screen + microphone';
  }
  $('annotation').disabled=!currentSession;
  $('download').hidden=!s.download_url||!!voice||!!screen||pendingUploads>0||stoppingSample;
  $('download').href=s.download_url||'#';
  showLinks('video-downloads',s.videos||[]);showLinks('audio-downloads',s.audio||[]);
  updatePreview(s);
  if(episodeJustFinished&&document.body.classList.contains('recording-mode')){
    document.body.classList.add('tools-open');$('focus-tools').setAttribute('aria-expanded','true');
    requestAnimationFrame(()=>{
      const tools=$('sample-preview').closest('.record-panel');
      tools.scrollTop+=Math.max(0,$('sample-preview').getBoundingClientRect().top-tools.getBoundingClientRect().top-20);
    });
  }
  $('delete-current').hidden=!finished;
  $('delete-current').disabled=!!voice||!!screen||pendingUploads>0||s.processing;
  const working=(s.media_jobs||[]).filter(j=>['queued','processing'].includes(j.status));
  const failed=(s.media_jobs||[]).filter(j=>j.status==='error');
  $('processing-note').hidden=!working.length&&!failed.length;
  $('processing-note').textContent=failed.length?'MP4 export failed. Your source recording is retained for recovery.':
    working.length?'Preparing '+working.map(j=>j.kind==='voice'?'reasoning audio':j.kind+' MP4').join(', ')+'. You can keep moving.':'';
  for(const job of s.media_jobs||[]){
    if(job.status==='ready'&&!knownReadyJobs.has(job.id)){
      knownReadyJobs.add(job.id);event('MP4 saved · '+job.path);
      if(s.finished)refreshSaved=true;
      if(job.kind==='voice'&&lastVoiceRange)lastVoiceRange.path=job.path;
    }
  }
  const message=finished?'Episode completed. Create a new sample before recording another episode.':
    s.goal_reached?'Destination reached. Record your arrival reasoning and press STOP. A new episode needs a new sample.':'';
  $('completion-banner').hidden=!message;$('completion-banner').textContent=message;
  document.body.classList.toggle('has-completion',!!message);
  $('focus-status').textContent=active?(voice?'Reasoning microphone on':'Sample recording · '+(screen?'screen capture on':'screen capture off')):finished?'Episode completed':'Create a sample to begin.';
  if(s.goal_reached&&!reachedAnnounced){notice('Destination reached. Explain the match, then STOP and save.');reachedAnnounced=true;}
  if(refreshSaved)refreshSavedSessions();
}
function needSample(){
  if(active)return true;
  if(finished&&!$('new-sample-dialog').open)$('new-sample-dialog').showModal();
  notice('Create a new sample before recording another episode.');return false;
}
function resetView(){
  $('timeline').replaceChildren();$('media-list').replaceChildren();$('reasoning').value='';
  lastVoiceRange=null;started=0;timerFrozen=0;reachedAnnounced=false;heldKeys.clear();actionQueue=[];
  document.querySelectorAll('.memory-choice').forEach(x=>x.disabled=false);
}
async function createSample(){
  try{
    if(voice||screen||pendingUploads)throw Error('Stop recordings and wait for the upload first.');
    if(currentState?.processing)throw Error('Wait for the MP4 export to finish before creating the next sample.');
    const user=$('annotator').value.trim();
    if(!/^[A-Za-z0-9_-]{1,48}$/.test(user))throw Error('Enter a username using letters, digits, _ or -.');
    resetView();started=performance.now();
    const s=await api('/api/start',{annotator:user,request:$('request').value,current_state:$('current-state').value,
      episode_key:caseData.episode_key,
      relevant_memory_ids:selected(),memory_selection_source:selectionSource,client_elapsed_ms:0});
    update(s,true);event('New sample created');$('scene').focus({preventScroll:true});
    notice('Sample created. Record reasoning, or use Record screen + microphone for the focused view.');
    localStorage.setItem('collector_v2_username',user);
  }catch(e){notice(e.message);}
}
function act(action,repeat=false){
  if(action==='stop')return finishSample();
  if(stoppingSample)return Promise.resolve(null);
  return queueAction(action,repeat);
}
function finishSample(){
  if(stopPromise)return stopPromise;
  if(!needSample())return Promise.resolve(null);
  stoppingSample=true;heldKeys.clear();
  for(const item of actionQueue)item.resolve(null);actionQueue=[];
  const captures=[voice,screen].filter(Boolean);
  for(const capture of captures){
    if(capture.recorder.state!=='inactive')capture.recorder.stop();
  }
  update(currentState);notice('Stopping recordings and saving this sample…');
  stopPromise=(async()=>{
    try{
      const state=await queueAction('stop');
      await Promise.all(captures.map(capture=>capture.done));
      update(await api('/api/state'));pollState();
      return state;
    }finally{stoppingSample=false;stopPromise=null;update(currentState);}
  })();
  return stopPromise;
}
function queueAction(action,repeat=false){
  return new Promise((resolve,reject)=>{
    if(!needSample()){resolve(null);return;}
    if(repeat&&(actionQueue.length>0||pumpBusy)){resolve(null);return;}
    actionQueue.push({action,resolve,reject});pumpActions();
  });
}
async function pumpActions(){
  if(pumpBusy)return;pumpBusy=true;
  try{
    while(actionQueue.length){
      const item=actionQueue.shift();
      try{
        const s=await api('/api/action',{action:item.action,client_elapsed_ms:elapsed()});
        update(s);event(item.action==='forward'?'Forward 25 cm':item.action==='left'?'Left 15°':item.action==='right'?'Right 15°':'STOP · sample completed');
        item.resolve(s);
        if(s.finished){
          heldKeys.clear();for(const pending of actionQueue)pending.resolve(null);actionQueue=[];
          notice('Episode completed. Wait for the MP4 files, then download your sample.');
        }
      }catch(e){notice(e.message);item.reject(e);for(const pending of actionQueue)pending.resolve(null);actionQueue=[];heldKeys.clear();}
    }
  }finally{pumpBusy=false;if(currentState)update(currentState);}
}
function imageViewer(memory,index){
  imageMemory=memory;imageIndex=Math.max(0,Math.min(memory.image_urls.length-1,index));
  $('large-image').src=memory.image_urls[imageIndex];
  $('image-caption').textContent='Memory '+memory.number+' · original view '+memory.original_view_indices[imageIndex];
  $('image-description').textContent=memory.view_descriptions[imageIndex]||'';
  $('previous-image').disabled=imageIndex===0;$('next-image').disabled=imageIndex===memory.image_urls.length-1;
  if(!$('image-dialog').open)$('image-dialog').showModal();
}
function memoryCard(memory,number){
  memory.number=number;
  const section=document.createElement('details');section.className='memory';section.open=true;section.dataset.memory=memory.id;
  const summary=document.createElement('summary'),badge=document.createElement('span'),name=document.createElement('strong'),time=document.createElement('span');
  badge.className='memory-number';badge.textContent=number;name.textContent='Memory '+number;time.className='memory-time';time.textContent=memory.when;
  summary.append(badge,name,time);
  const content=document.createElement('div');content.className='memory-content';
  const speech=document.createElement('blockquote');speech.textContent=memory.who+' said \"'+memory.said+'\"';
  const images=document.createElement('div');images.className='images';
  memory.image_urls.forEach((url,index)=>{
    const button=document.createElement('button');button.className='image-button';button.type='button';
    const image=document.createElement('img');image.src=url;image.alt='Memory '+number+' · original view '+memory.original_view_indices[index];
    image.title='Click to enlarge this view';const label=document.createElement('span');label.textContent='View '+memory.original_view_indices[index];
    button.append(image,label);button.onclick=()=>imageViewer(memory,index);images.append(button);
  });
  images.onwheel=e=>{if(Math.abs(e.deltaY)>Math.abs(e.deltaX)&&images.scrollWidth>images.clientWidth){images.scrollLeft+=e.deltaY;e.preventDefault();}};
  const scroll=document.createElement('div');scroll.className='scroll-controls';
  for(const [text,amount] of [['← Views',-180],['Views →',180]]){
    const button=document.createElement('button');button.textContent=text;button.onclick=()=>images.scrollBy({left:amount,behavior:'smooth'});scroll.append(button);
  }
  new ResizeObserver(()=>{scroll.hidden=images.scrollWidth<=images.clientWidth+1;}).observe(images);
  const choice=document.createElement('label');choice.className='choice';const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.className='memory-choice';checkbox.value=memory.id;
  checkbox.onchange=()=>selectionSource='user_review';choice.append(checkbox,document.createTextNode('Relevant memory'));
  const description=document.createElement('details'),heading=document.createElement('summary'),paragraph=document.createElement('pre');
  heading.textContent='Visual description';paragraph.textContent=memory.navigation_paragraph;description.append(heading,paragraph);
  content.append(speech,images,scroll,choice,description);section.append(summary,content);return section;
}
async function loadSession(session){
  if(active||voice||screen||pendingUploads)throw Error('Finish the current recording before loading another sample.');
  const s=await api('/api/load',{session_id:session.id});resetView();
  if(s.case)applyCase(s.case);
  const inputs=s.inputs;$('request').value=inputs.request;$('current-state').value=inputs.current_state;
  selectMemories(inputs.human_selected_memory_ids);selectionSource='saved_sample';banner();update(s,true);
}
function renderSavedSessions(user,sessions,selectedId){
  savedSessions=sessions;
  const selector=$('saved-sessions'),signature=JSON.stringify(sessions.map(s=>s.id));
  if(selector.dataset.signature!==signature){
    selector.replaceChildren();selector.dataset.signature=signature;
    for(const session of sessions){
      const option=document.createElement('option');option.value=session.id;
      option.textContent=session.id.split('/').pop()+(session.episode_key?' · '+episodeName({episode_key:session.episode_key,title:session.episode_title}):'');selector.append(option);
    }
  }
  const selectedSession=sessions.find(session=>session.id===selectedId)||sessions[0];
  selector.value=selectedSession?.id||'';
  selector.hidden=!sessions.length;$('old-download').hidden=!sessions.length;$('delete-saved').hidden=!sessions.length;
  $('old-download').href=selectedSession?.download||'#';showLinks('old-videos',selectedSession?.videos||[]);
  $('session-note').textContent=sessions.length?user+' · '+sessions.length+' saved sample(s) · updates automatically.':user+' · no saved samples yet.';
}
async function refreshSavedSessions(){
  const user=$('annotator').value.trim(),sequence=userSequence;
  if(savedRefreshBusy||active||!/^[A-Za-z0-9_-]{1,48}$/.test(user))return;
  savedRefreshBusy=true;
  try{
    const sessions=await api('/api/sessions?annotator='+encodeURIComponent(user));
    if(sequence!==userSequence||$('annotator').value.trim()!==user)return;
    const newlySaved=finished&&sessions.some(s=>s.id===currentSession)&&!savedSessions.some(s=>s.id===currentSession);
    renderSavedSessions(user,sessions,newlySaved?currentSession:$('saved-sessions').value);
  }catch(e){/* Keep the existing list during a temporary connection failure. */}
  finally{savedRefreshBusy=false;}
}
async function loadUser(autoLoad=true){
  const user=$('annotator').value.trim(),sequence=++userSequence;
  if(!/^[A-Za-z0-9_-]{1,48}$/.test(user))return;
  if(active||voice||screen||pendingUploads||environmentSwitching)return;
  try{
    $('session-note').textContent='Loading '+user+'…';
    const sessions=await api('/api/sessions?annotator='+encodeURIComponent(user));
    if(sequence!==userSequence||$('annotator').value.trim()!==user)return;
    renderSavedSessions(user,sessions,sessions[0]?.id);
    localStorage.setItem('collector_v2_username',user);
    if(autoLoad&&sessions.length&&currentSession!==sessions[0].id)await loadSession(sessions[0]);
    if(!sessions.length){
      if(finished&&currentState?.annotator!==user){await api('/api/reset',{});update(await api('/api/state'),true);$('scene').src='/api/frame?t='+Date.now();}
      selectMemories(caseData.default_relevant_memory_ids);selectionSource='episode_default';
    }
  }catch(e){notice(e.message);$('session-note').textContent='Could not load saved samples.';}
}
async function pollState(){
  if(pollBusy||!currentSession)return;
  if(!currentState?.processing&&!pendingUploads)return;
  pollBusy=true;
  try{update(await api('/api/state'));}catch(e){notice(e.message);}finally{pollBusy=false;}
}
async function upload(blob,kind,mime,start,end,session){
  pendingUploads++;update(currentState);
  try{
    const query=new URLSearchParams({kind,mime,start_ms:String(start),end_ms:String(end),session});
    const result=await fetch('/api/upload?'+query,{method:'POST',headers:{'Content-Type':mime},body:blob});
    const saved=await result.json();if(!result.ok)throw Error(saved.error||'Upload failed');
    event('Upload saved · preparing '+kind+' MP4');return saved;
  }catch(e){notice(e.message+' · the source recording is retained in this browser.');throw e;}
  finally{
    try{update(await api('/api/state'));}
    finally{pendingUploads--;update(currentState);pollState();}
  }
}
function mimeFor(kind){
  const choices=kind==='voice'?['audio/mp4;codecs=mp4a.40.2','audio/mp4','audio/webm;codecs=opus','audio/ogg;codecs=opus']:
    ['video/mp4','video/mp4;codecs=avc1,mp4a.40.2','video/webm;codecs=vp8,opus','video/webm'];
  return choices.find(m=>MediaRecorder.isTypeSupported(m));
}
async function toggleVoice(){
  if(voice){if(voice.recorder.state!=='inactive')voice.recorder.stop();return;}
  if(!needSample())return;
  try{
    const stream=await navigator.mediaDevices.getUserMedia({audio:true}),mime=mimeFor('voice');
    const recorder=mime?new MediaRecorder(stream,{mimeType:mime}):new MediaRecorder(stream);
    const chunks=[],begin=elapsed(),session=currentSession;
    let resolveDone;const done=new Promise(resolve=>resolveDone=resolve);
    voice={recorder,stream,done};update(currentState);
    recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
    recorder.onstop=async()=>{
      const end=elapsed();stream.getTracks().forEach(t=>t.stop());voice=null;lastVoiceRange={start:begin,end,kind:'reasoning'};
      try{await upload(new Blob(chunks,{type:recorder.mimeType}),'voice',recorder.mimeType,begin,end,session);}
      catch(e){}finally{resolveDone();update(currentState);}
    };
    recorder.start(1000);event('Reasoning microphone started');$('scene').focus({preventScroll:true});
  }catch(e){notice(e.message);}
}
function enterRecordingView(){
  document.body.classList.add('recording-mode');document.body.classList.remove('tools-open','memories-hidden');
  $('memory-toggle').setAttribute('aria-expanded','true');banner();
}
async function toggleScreen(){
  if(screen){if(screen.recorder.state!=='inactive')screen.recorder.stop();return;}
  if(screenStarting||!needSample())return;
  enterRecordingView();
  if(document.fullscreenElement)return startScreenCapture();
  try{
    if(!document.documentElement.requestFullscreen)throw Error('Fullscreen is unavailable');
    await document.documentElement.requestFullscreen({navigationUI:'hide'});
  }catch(e){notice('The browser declined fullscreen. Press F11 to hide the browser toolbar.');}
  if(!active)return;
  $('screen-start-note').textContent=document.fullscreenElement?
    'Fullscreen is ready. Start recording, then choose the dashboard tab or window and allow microphone access.':
    'Press F11 for browser fullscreen, then start recording and choose the dashboard tab or window.';
  if(!$('screen-start-dialog').open)$('screen-start-dialog').showModal();
}
async function startScreenCapture(){
  if(screenStarting||screen||!needSample())return;
  const captureSession=currentSession;
  screenStarting=true;update(currentState);
  let display,mic;
  try{
    // This call runs directly from Start recording's fresh user activation.
    display=await navigator.mediaDevices.getDisplayMedia({video:{frameRate:15},audio:false});
    mic=await navigator.mediaDevices.getUserMedia({audio:true});
    if(!active||currentSession!==captureSession)throw Error('This sample has ended. Create a new sample before recording.');
    const stream=new MediaStream([...display.getVideoTracks(),...mic.getAudioTracks()]),mime=mimeFor('screen');
    const recorder=mime?new MediaRecorder(stream,{mimeType:mime}):new MediaRecorder(stream);
    const chunks=[],begin=elapsed(),session=currentSession;
    let resolveDone;const done=new Promise(resolve=>resolveDone=resolve);
    screen={recorder,display,mic,done};update(currentState);
    recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
    display.getVideoTracks()[0].onended=()=>{if(recorder.state!=='inactive')recorder.stop();};
    recorder.onstop=async()=>{
      const end=elapsed();display.getTracks().forEach(t=>t.stop());mic.getTracks().forEach(t=>t.stop());screen=null;
      try{await upload(new Blob(chunks,{type:recorder.mimeType}),'screen',recorder.mimeType,begin,end,session);}
      catch(e){}finally{resolveDone();update(currentState);}
    };
    recorder.start(1000);event('Screen and microphone started');$('scene').focus({preventScroll:true});
  }catch(e){
    display?.getTracks().forEach(t=>t.stop());mic?.getTracks().forEach(t=>t.stop());screen=null;
    update(currentState);notice('Screen recording: '+e.message);
  }finally{screenStarting=false;update(currentState);}
}
async function deleteSample(session){
  try{
    if(!session)return;
    if(voice||screen||pendingUploads)throw Error('Stop recordings and wait for uploads first.');
    if(!window.confirm('Delete this saved sample?\n\n'+session+'\n\nThe copy is recoverable in deleted_sessions.'))return;
    const s=await api('/api/delete',{session_id:session,confirm_session:session});
    if(currentSession===session)resetView();update(s.state,true);$('scene').src='/api/frame?t='+Date.now();
    await loadUser(false);notice('Sample removed from this dashboard copy and kept recoverable.');
  }catch(e){notice(e.message);}
}
$('start').onclick=createSample;
$('new-user').onclick=async()=>{
  try{
    if(active||voice||screen||pendingUploads)throw Error('Finish this sample before creating another user.');
    resetView();update(await api('/api/reset',{}),true);$('scene').src='/api/frame?t='+Date.now();
    $('request').value=caseData.default_request;$('current-state').value=caseData.default_current_state;banner();
    selectMemories(caseData.default_relevant_memory_ids);selectionSource='episode_default';await loadUser(false);$('annotator').focus();
  }catch(e){notice(e.message);}
};
$('annotator').oninput=()=>{clearTimeout(userTimer);userTimer=setTimeout(()=>loadUser(),300);};
$('annotator').onchange=()=>{clearTimeout(userTimer);loadUser();};
$('environment-select').onchange=()=>{
  const scene=$('environment-select').value;episodeOptions(scene);
  const key=$('episode-select').value;if(key)selectEpisode(key);
};
$('episode-select').onchange=()=>selectEpisode($('episode-select').value);
$('saved-sessions').onchange=async()=>{
  const s=savedSessions.find(x=>x.id===$('saved-sessions').value);if(!s)return;
  $('old-download').href=s.download;showLinks('old-videos',s.videos||[]);
  try{await loadSession(s);}catch(e){notice(e.message);}
};
$('preview-recording').onchange=()=>{
  previewChoice=$('preview-recording').value;previewUserChosen=true;updatePreview(currentState);
};
$('request').oninput=banner;$('current-state').oninput=banner;
document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>act(b.dataset.action).catch(()=>{}));
$('stop').onclick=()=>act('stop').catch(()=>{});
$('voice').onclick=toggleVoice;$('focus-voice').onclick=toggleVoice;
$('screen').onclick=toggleScreen;$('focus-screen').onclick=toggleScreen;
$('screen-start').onclick=()=>{$('screen-start-dialog').close();return startScreenCapture();};
$('cancel-screen-start').onclick=()=>$('screen-start-dialog').close();
$('annotation').onclick=async()=>{
  try{
    const text=$('reasoning').value.trim();if(!text)throw Error('Enter the corrected reasoning transcript first.');
    const range=lastVoiceRange;
    await api('/api/annotate',{text,memory_ids:selected(),kind:range?'human_corrected_reasoning_transcript':'human_reasoning',
      client_start_ms:range?.start??elapsed(),client_end_ms:range?.end??elapsed(),audio_path:range?.path});
    event('Reasoning text saved');$('reasoning').value='';lastVoiceRange=null;
  }catch(e){notice(e.message);}
};
$('delete-current').onclick=()=>deleteSample(currentSession);
$('delete-saved').onclick=()=>deleteSample($('saved-sessions').value);
$('memory-toggle').onclick=()=>{
  const collapsed=document.body.classList.toggle('memories-hidden');$('memory-toggle').setAttribute('aria-expanded',String(!collapsed));
};
$('focus-tools').onclick=()=>{$('focus-tools').setAttribute('aria-expanded',String(document.body.classList.toggle('tools-open')));};
$('fullscreen').onclick=async()=>{
  enterRecordingView();
  try{if(!document.fullscreenElement)await document.documentElement.requestFullscreen({navigationUI:'hide'});}
  catch(e){notice('The browser declined fullscreen. Press F11 to hide the browser toolbar.');}
};
$('exit-focus').onclick=async()=>{
  document.body.classList.remove('recording-mode','tools-open','memories-hidden');
  if(document.fullscreenElement)await document.exitFullscreen();
};
$('close-image').onclick=()=>$('image-dialog').close();
$('previous-image').onclick=()=>imageViewer(imageMemory,imageIndex-1);
$('next-image').onclick=()=>imageViewer(imageMemory,imageIndex+1);
$('dismiss-new-sample').onclick=()=>$('new-sample-dialog').close();
$('dialog-create-sample').onclick=async()=>{$('new-sample-dialog').close();await createSample();};
$('guide-refresh').onclick=async()=>{try{$('guidance').textContent=(await api('/api/guidance')).text;}catch(e){notice(e.message);}};
document.addEventListener('keydown',e=>{
  if(e.target.closest?.('textarea,input,select')||e.target.isContentEditable||document.querySelector('dialog[open]'))return;
  const key=e.key.toLowerCase();
  if(key==='s'){e.preventDefault();notice('No backward motion. Twelve D turns rotate 180°.');return;}
  const action={w:'forward',a:'left',d:'right',' ':'stop'}[key];if(!action)return;
  e.preventDefault();if(!active){needSample();return;}
  if(key===' '){heldKeys.clear();act('stop').catch(()=>{});return;}
  if(!e.repeat){heldKeys.add(key);act(action).catch(()=>{});}
});
document.addEventListener('keyup',e=>heldKeys.delete(e.key.toLowerCase()));
window.addEventListener('blur',()=>heldKeys.clear());
setInterval(()=>{
  if(active&&heldKeys.size){
    const key=[...heldKeys].at(-1);act({w:'forward',a:'left',d:'right'}[key],true).catch(()=>{});
  }
},85);
setInterval(()=>{
  const seconds=Math.floor(active?elapsed()/1000:timerFrozen);
  $('timer').textContent=String(Math.floor(seconds/60)).padStart(2,'0')+':'+String(seconds%60).padStart(2,'0');
},500);
setInterval(pollState,600);
setInterval(refreshSavedSessions,2500);
window.addEventListener('focus',refreshSavedSessions);
window.addEventListener('beforeunload',e=>{if(active||voice||screen||pendingUploads){e.preventDefault();e.returnValue='';}});
(async()=>{
  try{
    [caseData,environmentChoices]=await Promise.all([api('/api/case'),api('/api/environments')]);
    for(const environment of environmentChoices){
      const option=document.createElement('option');option.value=environment.scene;option.textContent=environmentName(environment);
      option.title='Scene '+environment.scene+' · '+environment.episodes.length+' episodes';
      option.disabled=!environment.available;$('environment-select').append(option);
    }
    applyCase(caseData);
    const s=await api('/api/state');update(s,true);$('scene').src='/api/frame?t='+Date.now();
    $('annotator').value=s.annotator||localStorage.getItem('collector_v2_username')||'';
    if(active)started=performance.now()-s.elapsed_seconds*1000;
    if(!active&&$('annotator').value)await loadUser();
    $('connection').textContent='Scene connected';
    notice(active?'Sample active. Use W/A/D to move and STOP & save to finish.':
      $('annotator').value?'Create a new sample to start recording.':'Enter your username, then create a new sample.');
  }catch(e){$('connection').textContent='Connection failed';notice(e.message);}
})();
