'use strict';
const $=s=>document.querySelector(s), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const mode=location.pathname==='/blind'?'blind':location.pathname==='/naturalness'?'naturalness':location.pathname==='/props'?'props':'review';
const state={catalog:null,current:null,variant:'level3',tab:'navigate',token:null,busy:false,filter:'',batch:'all',imageURL:null,selection:0,drafts:{}};
const localKey='step8_reviewer';
let noticeTimer;
function notify(text){$('#notice').textContent=text;$('#notice').style.display='block';clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>$('#notice').style.display='none',6500);}
async function api(path,data){const r=await fetch(path,data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{});const v=await r.json();if(!r.ok)throw Error(v.error||`Request failed (${r.status})`);return v;}
function reviewer(){return $('#reviewer').value.trim();}
function header(){return `<header class="bar"><div class="brand"><div class="brandmark">⌂</div><div><div class="brandname">House review</div><div class="eyebrow">2azQ1b91cZZ · Step 8</div></div></div><nav class="links">${mode==='blind'?'<span>Independent blind review</span>':mode==='naturalness'?'<span>Naturalness review</span>':`<a class="${mode==='review'?'active':''}" href="/review">Case review</a><a class="${mode==='props'?'active':''}" href="/props">Props first</a><a href="/blind" target="_blank" rel="noopener">Blind review ↗</a><a href="/naturalness" target="_blank" rel="noopener">Naturalness ↗</a>`}</nav><div class="session"><span class="pill green">Navigation recording off</span><input id="reviewer" aria-label="Reviewer name" placeholder="Your name" value="${esc(localStorage.getItem(localKey)||'')}"></div></header>`;}
function wireHeader(){ $('#reviewer').addEventListener('input',e=>localStorage.setItem(localKey,e.target.value)); }
function variantList(c){return [{id:'level3',name:mode==='blind'?'Request B':'Level 3 · memory request',text:c.instruction},...(c.need?[{id:'level2',name:mode==='blind'?'Request A':'Level 2 · everyday need',text:c.need}]:[]),...c.forms.map((f,i)=>({id:`form${i}`,name:mode==='blind'?`Request ${String.fromCharCode(67+i)}`:f.form.replaceAll('_',' ')+(f.text===c.instruction?' · same request':''),text:f.text}))];}
function activeVariant(){return variantList(state.current).find(v=>v.id===state.variant);}
function selectedForm(){
  if(state.variant==='level2')return null;
  if(state.variant.startsWith('form'))return state.current.forms[Number(state.variant.slice(4))];
  return state.current.forms.find(f=>f.text===state.current.instruction)||null;
}
function requestProps(){
  if(state.variant==='level2')return [];
  const c=state.current,form=selectedForm();
  const formOnly=new Set(c.forms.filter(f=>f.text!==c.instruction).flatMap(f=>f.props||[]).map(p=>p.item));
  const selected=new Set((form?.props||[]).map(p=>p.item));
  return c.props.filter(p=>!formOnly.has(p.item)||selected.has(p.item));
}
function requestGuidance(){
  if(state.variant==='level2')return {label:'Everyday need',check:'Can you find a place where this activity is possible? More than one place can be correct.'};
  const c=state.current,form=selectedForm();
  const code=form&&state.variant.startsWith('form')?{multi_goal:'M1',next_place:'M2',off_limits:'C1'}[form.form]:c.primary;
  const simple={C1:'Find the destination from the memories. Can you get there without entering the forbidden room?',M1:'Can you visit every place in the order given?',M2:'Check the first place, then the next place. Is the item missing at the first and present at the next?',L1:'Do the memories make the nickname of the place clear?'};
  return {code,label:`${code} · ${state.catalog.types[code][0]}`,check:simple[code]||state.catalog.types[code][1]};
}
function typeReviewLabels(code){
  const specific={
    S1:{grounding:'Do the spatial clues identify one object, even after checking similar nearby objects?'},
    S2:{navigation:'Is the chosen object nearest by walking distance from the named place?'},
    S3:{grounding:'Do the floor and position clues identify the correct place?'},
    C1:{form:'Can you reach the destination without entering the forbidden room?'},
    C2:{alternatives:'Can you exclude the forbidden place and identify every allowed destination?'},
    C3:{memory:'Do the earlier memories explain the household condition that applies at this request time?'},
    M1:{memory:'Is there enough information to identify every stop?',form:'Can you visit the first stop, then the next stop, in the required order?'},
    M2:{form:'Can you check the first place, then the fallback place, with the item absent first and present next?'},
    M3:{memory:'Do the earlier memories identify where to collect the item and where to find its recipient?',grounding:'Are the pickup place and the recipient\'s location clear at this request time?',navigation:'Can you reach both the pickup place and the delivery place?',form:'Can you infer the pickup, then deliver the item to the intended recipient?'},
    T1:{memory:'Do the dated memories make clear which information applies now and replaces the older information?'},
    T2:{grounding:'Can you identify the event or time meant by the request, rather than another event?'},
    T3:{memory:'Do the earlier memories establish a routine that applies on this day and at this time?'},
    L1:{grounding:'Do the earlier memories clearly connect the nickname to the intended place?'},
    L2:{grounding:'Can you tell what words such as there, our room, or in there refer to?'},
    L3:{grounding:'Can you identify the person or place from the speaker\'s family relationship?'},
    K1:{alternatives:'Does the activity fit the intended place, and could another place fit just as well?'},
    K2:{memory:'Do the earlier memories explain where this household keeps the requested item?'},
    K3:{navigation:'Can you stop at the requested privacy boundary, such as outside the bathroom?'},
    P1:{grounding:'Do the earlier memories identify whose object or place is meant and distinguish it from others?'},
    V1:{visuals:'Is the attached request image clear enough to recognize the matching object or place in the house?'}
  };
  return specific[code]||{};
}
function requestFlags(){
  const flags=state.current.flags;
  if(state.variant==='level2')return flags.filter(f=>f.startsWith('Level 2')||f.startsWith('p42'));
  return flags.filter(f=>!f.startsWith('Level 2')&&(!f.startsWith('Requires explicit scene props')||requestProps().length)&&(!f.startsWith('Inspect the exact')||/outside|don't go in|nightstand|fireplace|table in here/i.test(activeVariant().text)));
}
function requestMemories(){
  const c=state.current;
  if(mode==='blind')return c.memories;
  if(state.variant==='level2')return [];
  const form=selectedForm();
  const extraKeys=new Set([...(form?.key||[]),...(form?.room_memory_ids||[]),...(form?.first_stop_memory_ids||[])]);
  return c.memories.filter(m=>m.roles?.some(r=>r==='key'||r==='competitor')||extraKeys.has(m.id));
}
function rememberDraft(){
  if(!state.current)return;
  const key=`${reviewer()}|${state.current.id}|${state.variant}`;
  if($('#reviewForm'))state.drafts[key]={ratings:Object.fromEntries(new FormData($('#reviewForm'))),note:$('#reviewNote').value,walked:$('#walked').checked};
  if($('#blindAnswer'))state.drafts[key]={answer:$('#blindAnswer').value,note:$('#blindNote').value,confidence:$('#confidence').value};
}
function saveReviewPlace(){
  if(mode!=='review'||!state.current||!$('#reviewer'))return;
  rememberDraft();
  try{sessionStorage.setItem(`step8_return_${reviewer()}`,JSON.stringify({fingerprint:state.catalog.summary.source_fingerprint,caseId:state.current.id,variant:state.variant,tab:state.tab,token:state.token,filter:state.filter,batch:state.batch,scrollY:window.scrollY,sidebarScroll:$('.sidebar')?.scrollTop||0,drafts:state.drafts}));}catch(e){/* The current page still works if browser storage is unavailable. */}
}
function reviewPlace(){
  if(mode!=='review')return null;
  try{const saved=JSON.parse(sessionStorage.getItem(`step8_return_${reviewer()}`));return saved&&saved.fingerprint===state.catalog.summary.source_fingerprint&&state.catalog.cases.some(c=>c.id===saved.caseId)?saved:null;}catch(e){return null;}
}
window.addEventListener('pagehide',saveReviewPlace);
async function init(){
  try{
    if(mode==='props')return await propsPage();
    if(mode==='naturalness')return await naturalnessPage();
    state.catalog=await api(`/api/catalog?mode=${mode}`);
    $('#app').innerHTML=header()+`<div class="layout"><aside class="sidebar"><div class="eyebrow">${mode==='blind'?'40 requests':'40 cases · 20 + 20'}</div><input id="search" aria-label="Find case" placeholder="Find a case${mode==='blind'?'':' or type'}"><select id="batch" aria-label="Filter cases"><option value="all">All cases</option>${mode==='blind'?'':'<option value="general">General pilot · 01–20</option><option value="typed">Difficulty types · 21–40</option>'}</select><div id="caseList"></div>${mode==='review'?'<p class="footer-note">Every slight ambiguity counts. Review each request variant separately.</p><a class="small" href="/api/export">Download judgments</a>':''}</aside><main class="workspace" id="workspace"></main></div>`;
    wireHeader();$('#search').oninput=e=>{state.filter=e.target.value.toLowerCase();renderList();};$('#batch').onchange=e=>{state.batch=e.target.value;renderList();};
    const resume=reviewPlace();
    if(resume){state.drafts=resume.drafts||{};state.filter=resume.filter||'';state.batch=['all','general','typed'].includes(resume.batch)?resume.batch:'all';$('#search').value=state.filter;$('#batch').value=state.batch;}
    renderList();await loadCase(resume?.caseId||state.catalog.cases[0].id,resume);
    if(resume){let restoring=true;const deadline=Date.now()+2000;['wheel','touchstart','pointerdown','keydown'].forEach(event=>window.addEventListener(event,()=>{restoring=false;},{once:true,passive:true}));const restoreScroll=()=>{if(restoring&&Date.now()<deadline){window.scrollTo(0,resume.scrollY||0);$('.sidebar').scrollTop=resume.sidebarScroll||0;}};requestAnimationFrame(restoreScroll);document.querySelectorAll('#workspace img').forEach(img=>img.addEventListener('load',restoreScroll,{once:true}));}
  }catch(e){$('#app').innerHTML=`<main class="workspace"><h1>Review desk unavailable</h1><p>${esc(e.message)}</p><p>Use the private reviewer link printed by the launcher, or open <a href="/blind">blind review</a>.</p></main>`;}
}
function renderList(){
  let group='';$('#caseList').innerHTML=state.catalog.cases.filter(c=>(state.batch==='all'||(state.batch==='general'?c.number<=20:c.number>20))&&`${c.number} ${c.primary||''} ${state.catalog.types?.[c.primary]?.[0]||''}`.toLowerCase().includes(state.filter)).map(c=>{
    let heading='';if(mode==='review'&&group!==c.batch){group=c.batch;heading=`<div class="case-group eyebrow">${esc(group)}</div>`;}
    const reviews=Object.values(state.catalog.reviews||{}).filter(r=>r.case_id===c.id&&r.reviewer===reviewer());const passed=reviews.length===c.variant_count&&reviews.every(r=>r.decision==='pass');
    return heading+`<button class="case-row ${state.current?.id===c.id?'active':''}" data-case="${esc(c.id)}"><span class="dot ${reviews.length?(passed?'passed':'reviewed'):''}"></span><span class="case-num">${String(c.number).padStart(2,'0')}</span><span class="case-type">${esc(c.primary||'')}</span>${mode==='review'?`<span class="muted small">${c.length.toFixed(1)} m</span>`:''}</button>`;
  }).join('');document.querySelectorAll('[data-case]').forEach(b=>b.onclick=()=>loadCase(b.dataset.case));
}
async function loadCase(cid,resume=null){
  rememberDraft();const seq=++state.selection;try{const c=await api(`/api/case?mode=${mode}&id=${encodeURIComponent(cid)}`);if(seq!==state.selection)return;
    state.current=c;state.variant=resume&&variantList(c).some(v=>v.id===resume.variant)?resume.variant:'level3';state.tab=resume&&['navigate','memories','photos'].includes(resume.tab)?resume.tab:'navigate';state.token=resume?.token||null;if(state.imageURL)URL.revokeObjectURL(state.imageURL);state.imageURL=null;renderList();renderCase();
    if(state.token&&!await act('none')){state.token=null;state.imageURL=null;if(state.tab==='navigate')renderTab();notify('Your case is restored. The earlier navigation session ended; open navigation again.');}
  }catch(e){notify(e.message);}
}
function renderCase(){
  const c=state.current,v=activeVariant(),author=mode==='review',guide=author?requestGuidance():null;
  $('#workspace').innerHTML=`<div class="heading"><div><div class="eyebrow">${author?esc(c.batch):'Independent check'} · Case ${String(c.number).padStart(2,'0')} of 40</div><h1>${author?'Read it. Resolve it. Walk it.':'Where should the robot go?'}</h1><div class="overview">${author?`${state.variant==='level2'?'':`<span><b>${c.length.toFixed(1)}</b>m reference route</span>`}<span><b>${requestMemories().length}</b>relevant memories</span><span><b>${variantList(c).length}</b>request variants</span>`:`<span>Use only the request, earlier memories, and floor plans.</span>`}</div></div><div class="badges">${author?`<span class="pill">${esc(guide.label)}</span>`:'<span class="pill">Answers and type labels hidden</span>'}<button id="nextCase" class="tiny">Next case →</button></div></div>
  <div class="columns"><div><section class="card"><div class="variants">${variantList(c).map(i=>`<button class="tiny ${i.id===state.variant?'active':''}" data-variant="${i.id}">${esc(i.name)}</button>`).join('')}</div>
  <p class="instruction">“${esc(v.text)}”</p><div class="context">${esc(c.start.speaker)} · ${esc(c.start.day)} ${esc(c.start.time)}<br>Starting in ${esc(c.start.label)} ${c.start.room}</div>
  ${state.variant==='level3'&&c.image?`<div class="small muted" style="margin-top:12px">Attached image: ${esc(c.image_description)}</div><img class="request-image zoom" src="/assets/${esc(c.image)}" alt="${esc(c.image_description)}">`:''}
  ${author?`<div class="type-note"><b>${esc(guide.label)}</b><br>${esc(guide.check)}</div>${(state.variant==='level3'&&c.forms.some(f=>f.text===c.instruction))||(state.variant.startsWith('form')&&selectedForm()?.text===c.instruction)?`<p class="small same-request-note">Both buttons show the same instruction. The selected button changes the review focus to ${esc(guide.label)}. Follow the questions on the right. Ratings and notes are saved separately for each button.</p>`:''}${requestFlags().map(f=>`<div class="alert">${esc(f)}</div>`).join('')}`:''}</section>
  <section class="card"><div class="tabs"><button data-tab="navigate">Navigate</button><button data-tab="memories">Memories (${requestMemories().length})</button><button data-tab="photos">${author?'Photos & expected places':'Floor plans'}</button></div><div id="tabContent"></div></section>
  </div><aside class="rubric" id="rubric"></aside></div>`;
  $('#nextCase').onclick=()=>{const i=state.catalog.cases.findIndex(x=>x.id===c.id);loadCase(state.catalog.cases[(i+1)%40].id);};
  document.querySelectorAll('[data-variant]').forEach(b=>b.onclick=()=>{rememberDraft();state.variant=b.dataset.variant;state.token=null;if(state.imageURL)URL.revokeObjectURL(state.imageURL);state.imageURL=null;renderCase();});document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{state.tab=b.dataset.tab;renderTab();});
  renderTab();renderRubric();wireZoom();
}
function locatorHTML(){
  if(mode!=='review')return '';
  if(!state.token)return '<p class="small muted">Open navigation to see your position on the floor plan.</p>';
  return `<p class="small"><b>Your position:</b> blue dot. The arrow shows which way you face. Click the map to enlarge it.</p><img class="zoom locator-map" src="/api/nav/map?token=${encodeURIComponent(state.token)}&v=${Date.now()}" alt="Your current position and facing direction on the floor plan">`;
}
function renderTab(){
  const c=state.current;document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b.dataset.tab===state.tab));
  if(state.tab==='navigate'){
    $('#tabContent').innerHTML=`<div class="nav-frame" id="navFrame" tabindex="0" aria-label="Navigation view. W A S D to move, arrow up and down to look.">${state.imageURL?`<img id="view" src="${state.imageURL}" alt="Current first-person scene">`:`<div class="empty">Walk the scene from this request’s start. No video, audio, frames, or trajectory will be saved.</div><button id="startNav" class="primary">Open navigation</button>`}</div><div id="navStatus" class="nav-status">${state.token?'Navigation ready. Click the view to use the keyboard.':'The five review props are present throughout the house.'}</div><div class="controls"><div class="dpad"><button class="up" data-action="w" aria-label="Move forward">W ↑</button><button data-action="a" aria-label="Turn left">A ↶</button><button data-action="s" aria-label="Move backward">S ↓</button><button data-action="d" aria-label="Turn right">D ↷</button></div><div class="control-right"><button class="tiny" data-action="up">Look up</button><button class="tiny" data-action="down">Look down</button><button class="tiny" data-action="reset">Restart</button></div></div>${mode==='review'&&state.variant!=='level2'?'<label class="checklabel"><input type="checkbox" id="overlays">Show reference route for inspection</label>':''}<p class="note">W/S: 25 cm · A/D: 15° · ↑/↓: look. Navigation stays in memory. Submit your review separately.</p>${mode==='review'?'<div id="locator"></div>':''}`;
    if($('#locator'))$('#locator').innerHTML=locatorHTML();wireZoom();
    if($('#startNav'))$('#startNav').onclick=startNav;
    document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>act(b.dataset.action));$('#navFrame').onkeydown=e=>{const k={w:'w',a:'a',s:'s',d:'d',arrowup:'up',arrowdown:'down',r:'reset'}[e.key.toLowerCase()];if(k){e.preventDefault();act(k);}};
    if($('#overlays'))$('#overlays').onchange=()=>act('none');
  }else if(state.tab==='memories'){
    const form=mode==='review'?selectedForm():null;
    $('#tabContent').innerHTML=`${form?.form==='off_limits'?`<p><b>Room to avoid: ${esc(form.room_name)}</b></p>${form.room_memory_ids?.length?'<p class="small muted">The memory marked “room to avoid” shows which room this name refers to.</p>':'<p class="alert">No earlier photo memory identifies this room. Check the other earlier memories before judging it missing.</p>'}`:''}${form&&(form.goal1||form.first)?`<p><b>First stop: ${esc(form.goal1_name||form.first_name)}</b></p>${form.first_stop_direct?'':`<p class="alert">No photo memory is linked directly to this first stop. A room photo may help, but does not prove the exact object is clear. Check the other earlier memories before marking information missing.</p>`}`:''}<p class="small muted">${mode==='review'?'These are selected memories, not a guaranteed complete list. If something seems missing, check the other earlier memories below before judging the request.':'Every memory below is earlier than this request. Later memories and answer hints are hidden.'}</p><div id="memories"></div>${mode==='review'&&state.variant!=='level2'?'<details id="otherMemories"><summary>Check other earlier memories</summary><div id="otherMemoryList"></div></details>':''}`;
    renderMemories();
    if($('#otherMemories'))$('#otherMemories').ontoggle=()=>{if($('#otherMemories').open&&!$('#otherMemoryList').children.length){const selected=new Set(requestMemories().map(m=>m.id));$('#otherMemoryList').innerHTML=c.memories.filter(m=>!selected.has(m.id)).map(memoryCard).join('');wireZoom();}};
  }else{
    const form=selectedForm();
    const places=mode==='review'&&state.variant!=='level2'?[{id:c.expected.selected_route_goal,name:'Destination'},{id:c.expected.competitor.id,name:'Other possible place'},...(form&&(form.goal1||form.first)?[{id:form.goal1||form.first,name:form.first?'First search place':'First stop'}]:[])]:[];
    $('#tabContent').innerHTML=`${mode==='review'?`<button id="reveal" class="tiny">Reveal expected destinations</button><div id="expected"></div>${places.length?'<p class="small muted" style="margin-top:15px">These comparison sheets predate the added props. Memory and request images are rendered with the current props.</p>':''}<div class="photos-grid">${places.map(p=>`<figure><img class="zoom" loading="lazy" src="/assets/sheet_${esc(p.id)}.jpg" alt="${esc(p.name)} comparison"><figcaption>${esc(p.name)} · ${esc(p.id)}</figcaption></figure>`).join('')}</div>`:''}<h3 style="margin-top:20px">Floor plans</h3>${locatorHTML()}<div class="photos-grid">${[0,1].map(i=>`<figure><img class="zoom" src="/assets/2azQ1b91cZZ_floor${i}.png" alt="Floor ${i} plan"><figcaption>${i===0?'Ground floor':'Upstairs'}</figcaption></figure>`).join('')}</div>`;
    if($('#reveal'))$('#reveal').onclick=()=>{$('#expected').innerHTML=`<div class="expected"><p style="margin-top:12px"><b>Allowed destinations for this request:</b></p><ul>${(state.variant==='level2'?(c.expected.level2||[]):c.expected.level3.map(x=>x.name)).map(x=>`<li>${esc(x)}</li>`).join('')}</ul>${form?.goal1_name||form?.first_name?`<p><b>First stop:</b> ${esc(form.goal1_name||form.first_name)}</p>`:''}${form?.form==='off_limits'?'<p>Reach the destination without entering the room forbidden in this instruction.</p>':''}</div>`;};
    wireZoom();
  }
}
function memoryCard(m){return `<article class="memory"><div class="memory-head"><b>${esc(m.id)}</b><span>${esc(m.day)} ${esc(m.time)} · ${esc(m.who)}</span><span>${esc(m.mode)}</span>${(m.roles||[]).map(r=>`<span class="role">${esc(r)}</span>`).join('')}</div><blockquote>“${esc(m.quote)}”</blockquote>${m.photo?`<details><summary class="small">View clean memory photo</summary><img class="zoom" loading="lazy" src="/assets/${esc(m.photo)}" alt="Clean photo for memory ${esc(m.id)}"></details>`:''}</article>`;}
function renderMemories(){const memories=requestMemories();$('#memories').innerHTML=memories.length?memories.map(memoryCard).join(''):'<p class="empty-check muted">This everyday need has no authored memory dependency.</p>';wireZoom();}
async function startNav(){if(state.busy)return;const seq=state.selection;try{if($('#startNav'))$('#startNav').disabled=true;$('#navStatus').textContent='Opening the scene and placing the five props…';const r=await api('/api/nav/start',{case_id:state.current.id,mode});if(seq!==state.selection)return;state.token=r.token;await act('none');$('#navFrame').focus();}catch(e){notify(e.message);if($('#startNav'))$('#startNav').disabled=false;if($('#navStatus'))$('#navStatus').textContent=e.message;}}
async function act(action){if(!state.token){notify('Open navigation first.');return;}if(state.busy)return;state.busy=true;const seq=state.selection;try{const r=await fetch('/api/nav/act',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:state.token,action,overlays:!!$('#overlays')?.checked})});if(!r.ok)throw Error((await r.json()).error);const blob=await r.blob();if(seq!==state.selection)return;const info=JSON.parse(r.headers.get('X-Review-State'));if($('#locator')){$('#locator').innerHTML=locatorHTML();wireZoom();}if(state.imageURL)URL.revokeObjectURL(state.imageURL);state.imageURL=URL.createObjectURL(blob);if($('#navFrame'))$('#navFrame').innerHTML=`<img id="view" src="${state.imageURL}" alt="Current first-person scene">`;if($('#navStatus'))$('#navStatus').textContent=`${info.steps} actions this visit · navigation recording off${state.variant!=='level2'&&info.goal_distance!==undefined?` · ${info.goal_distance.toFixed(2)} m from selected route end (straight line)`:''}`;return true;}catch(e){notify(e.message);return false;}finally{state.busy=false;}}
function renderRubric(){
  const draft=state.drafts[`${reviewer()}|${state.current.id}|${state.variant}`];
  if(mode==='blind'){
    $('#rubric').innerHTML=`<section class="card"><h2>Your interpretation</h2><p class="small muted">For the selected request, name the destination and any stops or restrictions. Mention even a small ambiguity.</p><label>Where should the robot go?<textarea id="blindAnswer" placeholder="Room/object; ordered stops if needed…"></textarea></label><label>Clarity<select id="confidence"><option value="clear">Clear</option><option value="minor">Slightly ambiguous</option><option value="major">Ambiguous</option><option value="unsolved">Cannot resolve</option></select></label><label>Why / what is unclear?<textarea id="blindNote" placeholder="Which memory supports the answer? What else could it mean?"></textarea></label><button id="saveBlind" class="primary">Save blind judgment</button><p class="small muted" style="margin-top:12px">Only the submitted answer and notes are saved.</p><div id="saveResult" class="save-result"></div></section>`;
    if(draft){$('#blindAnswer').value=draft.answer;$('#blindNote').value=draft.note;$('#confidence').value=draft.confidence;}
    $('#saveBlind').onclick=async()=>{try{await api('/api/blind',{reviewer:reviewer(),case_id:state.current.id,variant:state.variant,answer:$('#blindAnswer').value,confidence:$('#confidence').value,note:$('#blindNote').value});$('#saveResult').textContent='Saved. No answer key is revealed.';notify('Blind judgment saved.');}catch(e){notify(e.message);}};return;
  }
  const saved=Object.values(state.catalog.reviews).find(r=>r.reviewer===reviewer()&&r.case_id===state.current.id&&r.variant===state.variant);
  const form=selectedForm(),skip=new Set();
  if(state.variant==='level2'){skip.add('memory');skip.add('grounding');}
  if(!form)skip.add('form');
  if(!requestProps().length)skip.add('props');
  const labels={instruction:'Is the instruction clear?',memory:'Do the memories give enough clear information?',grounding:'Are the names, places and times clear?',navigation:'Can you reach the right place and stop correctly?',alternatives:'Are the allowed destinations clear?',form:form?.form==='off_limits'?'Can you get there without entering the forbidden room?':form?.form==='next_place'?'Is the item missing at the first place and present at the next?':'Can you visit the places in the right order?',visuals:'Do the pictures match the words and the house?',props:'Are the needed objects visible in the right places?'};
  Object.assign(labels,typeReviewLabels(requestGuidance().code));
  $('#rubric').innerHTML=`<section class="card"><h2>Check this request</h2><p class="small"><b>Review focus: ${esc(requestGuidance().label)}</b></p><p class="small muted">Answer the questions below for this selection. Mention even a small doubt.</p><form class="rubric-form" id="reviewForm">${Object.entries(state.catalog.dimensions).map(([key,label])=>skip.has(key)?`<input type="hidden" name="${key}" value="na">`:`<label>${esc(labels[key]||label)}<select name="${key}"><option value="">Choose…</option><option value="pass">Yes / clear</option><option value="minor">A little confusing</option><option value="major">Very confusing</option><option value="fail">Does not work</option><option value="unsure">Not checked yet</option><option value="na">Does not apply</option></select></label>`).join('')}<label class="wide">What is confusing or wrong?<textarea id="reviewNote" placeholder="Example: two rooms seem to fit, or a memory does not explain the room name."></textarea></label><label class="checklabel wide"><input id="walked" type="checkbox">I checked this request by navigating the scene.</label><div class="wide"><button class="primary" type="submit">Save review judgment</button><div class="save-result" id="saveResult"></div></div></form></section>`;
  if(saved){for(const [k,v]of Object.entries(saved.ratings)){const el=$(`#reviewForm [name="${k}"]`);if(el.type!=='hidden')el.value=v;}$('#reviewNote').value=saved.note;$('#walked').checked=saved.walked;$('#saveResult').textContent=`Previously saved: ${saved.decision}`;}
  if(draft){for(const [k,v]of Object.entries(draft.ratings)){const el=$(`#reviewForm [name="${k}"]`);if(el.type!=='hidden')el.value=v;}$('#reviewNote').value=draft.note;$('#walked').checked=draft.walked;}
  $('#reviewForm').onsubmit=async e=>{e.preventDefault();try{const ratings=Object.fromEntries(new FormData(e.target));const record=await api('/api/review',{reviewer:reviewer(),case_id:state.current.id,variant:state.variant,ratings,note:$('#reviewNote').value,walked:$('#walked').checked});state.catalog.reviews[`${reviewer()}|${state.current.id}|${state.variant}`]=record;$('#saveResult').textContent=`Saved: ${record.decision==='pass'?'passes':'needs attention · '+record.decision}`;renderList();notify('Review judgment saved.');}catch(e){notify(e.message);}};
}
async function propsPage(){
  $('#app').innerHTML=header()+`<main class="workspace full"><div class="heading"><div><div class="eyebrow">Prepare the house first</div><h1>Five explicitly requested props</h1></div><span class="pill green">One shared scene</span></div><p class="section-intro">All five props coexist in the review scene. Check that each one is recognizable, rests on the right surface, and does not conflict with another case. The original scene file is preserved. These are procedural review models, so their appearance needs your judgment.</p><div id="propGrid" class="prop-grid"><div class="card">Opening the simulator and finding support surfaces…</div></div></main>`;wireHeader();
  try{const d=await api('/api/props');$('#propGrid').innerHTML=d.props.map(p=>{const authored=d.authored.find(x=>x.item===p.item);return `<section class="card"><div class="eyebrow">${esc(p.at)} · case ${authored?.cases.map(x=>x.slice(-2)).join(', ')}</div><h2>${esc(p.item)}</h2><img class="zoom" src="/api/prop-image/${esc(p.id)}" alt="Current placement of ${esc(p.item)}"><p class="small muted">${p.support_ray_hit?'Placed on a depth-measured support surface.':'No support surface found. Placement needs correction.'}${authored?.absent.length?` Must be absent at ${esc(authored.absent.join(', '))}.`:''}</p><label class="small" for="note_${p.id}">Placement and appearance notes</label><textarea id="note_${p.id}" placeholder="Is it recognizable and clearly visible from a normal approach?">${esc(d.judgments[p.item]?.note||'')}</textarea><div class="prop-fields"><select id="rating_${p.id}" aria-label="Judge ${esc(p.item)}"><option value="unsure">Needs checking</option><option value="pass">Placement and appearance pass</option><option value="minor">Minor issue</option><option value="major">Major issue</option><option value="fail">Fails</option></select><button class="primary tiny" data-save-prop="${esc(p.id)}">Save judgment</button></div></section>`;}).join('');
    d.props.forEach(p=>{const el=$(`#rating_${p.id}`);if(d.judgments[p.item])el.value=d.judgments[p.item].rating;});document.querySelectorAll('[data-save-prop]').forEach(b=>b.onclick=async()=>{const p=d.props.find(x=>x.id===b.dataset.saveProp);try{await api('/api/prop-review',{reviewer:reviewer(),item:p.item,rating:$(`#rating_${p.id}`).value,note:$(`#note_${p.id}`).value});notify('Prop judgment saved.');}catch(e){notify(e.message);}});wireZoom();
  }catch(e){$('#propGrid').innerHTML=`<div class="card">${esc(e.message)}</div>`;}
}
async function naturalnessPage(){
  const d=await api('/api/naturalness');$('#app').innerHTML=header()+`<main class="workspace full"><div class="eyebrow">Blind language judgment</div><h1>Would a family member say this?</h1><p class="section-intro">${d.requests.length} distinct requests, shuffled without case IDs, type labels, or answers. Mark even a slightly awkward or unclear request “odd” and say why. These are the current house-first requests; a matched request-first comparison has not been added.</p>${d.requests.map(r=>`<section class="card natural-row"><span class="muted small">${r.id}</span><div><p class="sentence">“${esc(r.text)}”</p><textarea id="natNote${r.id}" aria-label="Note for request ${r.id}" placeholder="What sounds odd or could be misunderstood?"></textarea></div><div class="vote"><select id="natRating${r.id}" aria-label="Naturalness for request ${r.id}"><option value="">Choose…</option><option value="yes">Yes</option><option value="odd">Odd / slightly unclear</option><option value="no">No</option></select><button class="tiny" data-natural="${r.id}">Save rating</button></div></section>`).join('')}</main>`;wireHeader();document.querySelectorAll('[data-natural]').forEach(b=>b.onclick=async()=>{const i=b.dataset.natural;try{await api('/api/naturalness',{reviewer:reviewer(),id:Number(i),rating:$(`#natRating${i}`).value,note:$(`#natNote${i}`).value});b.textContent='Saved ✓';notify('Naturalness rating saved.');}catch(e){notify(e.message);}});
}
function wireZoom(){document.querySelectorAll('img.zoom').forEach(img=>{img.onclick=()=>{$('#largeImage').src=img.src;$('#largeImage').alt=img.alt;$('#lightbox').showModal();};img.onerror=()=>{img.alt='Image unavailable — flag this in your review.';};});}
$('#closeLightbox').onclick=()=>$('#lightbox').close();$('#lightbox').addEventListener('click',e=>{if(e.target===$('#lightbox'))$('#lightbox').close();});
init();
