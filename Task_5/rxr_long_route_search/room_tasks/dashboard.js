'use strict';
const $=id=>document.getElementById(id);
const S={catalog:null,route:null,variant:null,packet:null,filter:'all',search:'',busy:false,connected:false,play:false,timer:null,step:0,selectedNora:null,keys:new Set(),drag:null,look:{yaw:0,pitch:0},view:'walk',errors:[]};
const fmt=(n,d=2)=>Number(n).toFixed(d);
const el=(tag,attrs={},text='')=>{const node=document.createElement(tag);for(const[k,v]of Object.entries(attrs))node.setAttribute(k,v);node.textContent=text;return node;};
const tags={schoolbag:['School bag','bag'],'nora-strong':['Nora · entrance','strong'],'nora-compatible':['Nora compatible','nora'],toiletries:['Toiletries','bed'],'bed-goal':['Bed goal','bed']};
function connection(kind,text){$('connection-dot').className='dot '+kind;$('connection-label').textContent=text;}
function error(message){S.errors.push(message);$('error-text').textContent=message;$('error-box').hidden=false;connection('error','3D view unavailable');S.connected=false;}
function setBusy(value,text='Updating view…'){
  S.busy=value;
  for(const id of ['variant-picker','jump-start','jump-goal','previous-step','next-step','retry'])$(id).disabled=value;
  $('jump-pickup').disabled=value||S.variant?.pickup_index==null;
  $('jump-nora').disabled=value||S.selectedNora==null;
  if(value&&!S.connected){$('loading').hidden=false;$('loading-title').textContent=text;}
}
async function api(command,payload={}){
  const response=await fetch('api/'+command,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...payload,route_id:payload.route_id||S.route?.id})});
  const data=await response.json();if(!response.ok)throw Error(data.error||'The scene request failed');return data;
}
function stopPreview(){S.play=false;clearTimeout(S.timer);S.timer=null;$('play-route').textContent='▶ Preview';}
function matches(route){
  const filter=S.filter==='all'||(S.filter==='selected'?(route.schoolbag_selected||route.tags.includes('nora-strong')||route.tags.includes('toiletries')):route.tags.includes(S.filter));
  return filter&&(!S.search||(route.id+' '+route.description+' '+route.index+' '+route.tags.join(' ')).toLowerCase().includes(S.search));
}
function renderList(){
  const list=$('instance-list');list.replaceChildren();const routes=S.catalog.routes.filter(matches);$('instance-count').textContent=routes.length;
  for(const r of routes){
    const card=el('button',{class:'instance-card'+(r.id===S.route?.id?' active':''),'data-route-id':r.id,'aria-pressed':String(r.id===S.route?.id)});
    const top=el('div',{class:'card-top'});top.append(el('span',{class:'index'},'INSTANCE '+String(r.index).padStart(2,'0')),el('span',{class:'length'},fmt(r.source_length_m)+' m'));
    card.append(top,el('h3',{},r.description),el('div',{class:'scene-name'},r.scan+' / path '+r.path_id));
    const badges=el('div',{class:'tags'});
    for(const tag of r.tags.filter(t=>t!=='combined'&&!(t==='nora-compatible'&&r.tags.includes('nora-strong')))){
      if(tags[tag])badges.append(el('span',{class:'tag '+tags[tag][1]},tags[tag][0]));
    }
    if(!badges.children.length)badges.append(el('span',{class:'tag'},'Audited source'));
    card.append(badges);card.onclick=()=>{if(S.busy)return;selectRoute(r.id);if(innerWidth<760)$('sidebar').classList.remove('open');};list.append(card);
  }
  if(!routes.length)list.append(el('div',{class:'empty-list'},'No instances match this filter.'));
}
function fillVariantPicker(){
  $('variant-picker').replaceChildren();
  for(const v of S.route.variants)$('variant-picker').append(el('option',{value:v.id},v.label+' · '+fmt(v.length_m)+' m'));
  $('variant-picker').value=S.variant.id;
}
function fillNoraPicker(){
  const picker=$('nora-picker');picker.replaceChildren();
  let options=S.route.nora_options;
  if(S.variant.nora_region!=null)options=[{nora_region:S.variant.nora_region,route_steps_adjacent_to_room:[],bed_objects:[]}];
  for(const o of options){
    const room=S.catalog.scenes[S.route.scan].regions[o.nora_region];
    picker.append(el('option',{value:o.nora_region},'Proposed Nora room '+o.nora_region+' · '+(room?.name||'bedroom')+(o.route_steps_adjacent_to_room?.length?' · near route':'')));
  }
  if(!options.length){picker.append(el('option',{value:''},'No compatible Nora room assigned'));S.selectedNora=null;picker.disabled=true;}
  else{
    picker.disabled=false;const preferred=options.find(o=>o.nora_region===S.variant.nora_region)||options.find(o=>o.route_steps_adjacent_to_room?.length)||options.find(o=>o.bed_objects?.length)||options[0];
    S.selectedNora=preferred.nora_region;picker.value=String(S.selectedNora);
  }
  updateNoraNote();
}
function updateNoraNote(){
  const option=S.route.nora_options.find(o=>o.nora_region===S.selectedNora);
  $('nora-note').textContent=S.selectedNora==null?'No separate reachable bedroom assignment was found for this source route.':option?.route_steps_adjacent_to_room?.length?'The original route passes a graph connection into this room and stays outside. Room ownership is proposed.':'Compatible room assignment only. No demonstrated shortcut through this room; ownership and sleeping state are authored.';
  $('jump-nora').disabled=S.busy||S.selectedNora==null;
}
function renderDetails(){
  const r=S.route,v=S.variant,scene=S.catalog.scenes[r.scan];
  $('route-eyebrow').textContent='INSTANCE '+String(r.index).padStart(2,'0')+' / ORIGINAL PATH '+r.path_id;
  $('route-title').textContent=r.description;
  $('route-subtitle').textContent=r.scan+' · '+r.split+' · '+r.variants.length+' trajectory choice'+(r.variants.length===1?'':'s');
  $('split-badge').textContent=r.split==='val_unseen'?'UNSEEN VALIDATION':'SEEN VALIDATION';
  $('variant-status').textContent=v.authored?'Authored task adaptation':'Original RxR guide';
  $('original-length').textContent=fmt(r.source_length_m)+' m';$('selected-length').textContent=fmt(v.length_m)+' m';
  $('waypoint-count').textContent=v.path.length;$('walked-distance').textContent='0.00 m';
  $('route-slider').max=v.path.length-1;$('route-slider').value=0;
  $('step-label').textContent='Step 1 / '+v.path.length;$('step-distance').textContent='0.00 m';
  fillNoraPicker();
  const levels=[...new Set(Object.values(scene.regions).map(r=>r.level))].sort((a,b)=>a-b);
  $('floor-picker').replaceChildren(el('option',{value:'auto'},'Follow camera floor'),el('option',{value:'all'},'All floors'));
  for(const level of levels)$('floor-picker').append(el('option',{value:level},'Annotated level '+level));
  const propButtons=$('prop-buttons');propButtons.replaceChildren();
  for(const prop of scene.props){const b=el('button',{},'Inspect '+prop.label.toLowerCase());b.onclick=()=>jump('prop:'+prop.id);propButtons.append(b);}
  if(!scene.props.length)propButtons.append(el('p',{class:'mini-note'},'No new objects have been placed in this scene.'));
  $('show-props').disabled=!scene.props.length;$('show-props').checked=true;
  const text=v.kind==='combined'?"Riya is packing for her trip. Bring her toiletries to her bed. Don’t go through Nora’s room; she’s sleeping!":v.kind==='toiletries'?"Riya is packing for her trip. Bring her toiletries to her bed.":r.tags.includes('nora-strong')?"Don’t go through Nora’s room. She’s sleeping!":r.schoolbag_selected?"Quick! Riya’s bus is here, but she still needs her school bag.":'Inspect the original RxR validation trajectory and its goal.';
  $('task-label').textContent=v.authored?'Authored task context':'Source-route context';$('task-text').textContent=text;
  const memories=[];
  if(v.riya_region!=null)memories.push('Proposed Riya bedroom: '+v.riya_region+'.');
  if(v.pickup_region!=null)memories.push('Toiletries pickup: bathroom '+v.pickup_region+'.');
  if(S.selectedNora!=null)memories.push('Proposed Nora bedroom: '+S.selectedNora+'.');
  if(r.schoolbag_selected&&v.kind==='original')memories.push('You selected this source goal as a plausible school-bag place; its routine remains authored.');
  $('task-memory').textContent=memories.join(' ');
  $('task-warning').textContent=v.authored?v.note:r.tags.includes('nora-strong')?'This adds a room-avoidance constraint to the original destination. It does not demonstrate a necessary reroute.':'Names and household routines are not original RxR facts. The displayed route remains the original guide.';
  const notes=[];
  if(r.schoolbag_selected)notes.push('One of your 12 selected school-bag instances.');
  if(r.tags.includes('nora-strong'))notes.push('Stronger Nora candidate: entrance-adjacent graph evidence.');
  else if(r.tags.includes('nora-compatible'))notes.push('Broad Nora compatibility; no shortcut conflict shown.');
  if(v.requires_new_goal)notes.push('New delivery goal needs image and continuous-route validation.');
  if(v.prepared)notes.push('Prepared sink props; all 23 floor-snapped adjacent pairs connected. Actual delivery is untested.');
  if(scene.props.length)notes.push(scene.props.length+' added 3D props available in this scene.');
  notes.push('Guide-step previews are camera jumps. Walking uses the existing navmesh.');
  $('evidence-notes').replaceChildren(...notes.map(n=>el('li',{},n)));
  $('room-sequence').textContent='Original rooms: '+r.original_room_sequence.map(room=>room.region+' '+room.name).join(' → ');
  $('instruction-picker').replaceChildren();
  const instructions=[...r.instructions].sort((a,b)=>(b.language.startsWith('en')?1:0)-(a.language.startsWith('en')?1:0));
  for(const ins of instructions)$('instruction-picker').append(el('option',{value:ins.id},ins.language+' · instruction '+ins.id));
  $('instruction-text').textContent=instructions[0]?.text||'Original instruction text is not available.';
  $('photo-grid').replaceChildren();
  r.goal_views.forEach((src,i)=>{const figure=el('figure'),image=el('img',{src,alt:'Original source goal at heading '+i*90+' degrees',loading:'lazy'});image.onclick=()=>{$('large-image').src=src;$('image-dialog').showModal();};figure.append(image,el('figcaption',{},'Heading '+i*90+'°'));$('photo-grid').append(figure);});
  $('contact-sheet-link').href=r.goal_contact_sheet;
  $('photo-note').textContent=v.requires_new_goal?'These are the ORIGINAL SOURCE goal photos, not the new authored bed goal. Use “Goal” in the 3D view to inspect the new delivery location.':'Four original goal views at the exact RxR goal panorama. Added objects are shown in the live 3D view.';
  updateStep(0);renderMaps();
}
async function selectRoute(id,variantId=null){
  if(S.busy)return false;stopPreview();
  const route=S.catalog.routes.find(r=>r.id===id);if(!route)return false;
  S.route=route;S.variant=route.variants.find(v=>v.id===(variantId||route.default_variant))||route.variants[0];S.packet=null;S.step=0;S.connected=false;
  fillVariantPicker();renderList();renderDetails();$('scene-image').hidden=true;$('error-box').hidden=true;
  setBusy(true,'Loading instance '+String(route.index).padStart(2,'0')+' · '+route.scan);connection('','Loading 3D scene');
  const url=new URL(location.href);url.searchParams.set('instance',route.index);url.searchParams.set('variant',S.variant.id);history.replaceState(null,'',url);
  try{await applyPacket(await api('select',{route_id:route.id,variant_id:S.variant.id,show_props:$('show-props').checked}));return true;}
  catch(e){error(e.message);$('loading').hidden=true;return false;}
  finally{setBusy(false);}
}
async function applyPacket(packet){
  if(packet.route_id!==S.route.id||packet.variant_id!==S.variant.id)return;
  S.packet=packet;S.connected=true;
  $('scene-image').src=packet.image;
  try{await $('scene-image').decode();}catch{}
  $('scene-image').hidden=false;$('loading').hidden=true;$('error-box').hidden=true;
  connection('ready','Live 3D inspection');
  $('scene-hud').textContent=S.route.scan+' · frame '+packet.frame;
  const room=S.catalog.scenes[S.route.scan].regions[packet.nearest_room];
  $('room-hud').textContent='Near room '+packet.nearest_room+' · '+(room?.name||'unknown');
  $('frame-message').textContent=packet.message;$('frame-timing').textContent='Render + encode '+fmt(packet.render_encode_ms,0)+' ms';
  $('walked-distance').textContent=fmt(packet.walked_m)+' m';$('show-props').checked=packet.show_props;
  updateStep(packet.route_step);renderMaps();
}
async function command(name,payload={}){
  if(S.busy||!S.route)return false;setBusy(true);
  try{await applyPacket(await api(name,payload));return true;}
  catch(e){error(e.message);stopPreview();return false;}
  finally{setBusy(false);}
}
async function act(action){if(!S.connected||S.busy)return false;stopPreview();return command('action',{action});}
async function jump(role){stopPreview();return command('jump',{role,region:S.selectedNora});}
function cumulative(index){let distance=0;const p=S.variant.positions_raw;for(let i=1;i<=index;i++)distance+=Math.hypot(...p[i].map((x,j)=>x-p[i-1][j]));return distance;}
function updateStep(index){S.step=index;$('route-slider').value=index;$('step-label').textContent='Step '+(index+1)+' / '+S.variant.path.length;$('step-distance').textContent=fmt(cumulative(index))+' m';}
async function seek(index){if(S.busy)return false;return command('step',{index:Math.max(0,Math.min(S.variant.path.length-1,index))});}
async function previewTick(){
  if(!S.play)return;
  if(S.step>=S.variant.path.length-1){stopPreview();return;}
  const ok=await seek(S.step+1);if(S.play&&ok)S.timer=setTimeout(previewTick,900);else stopPreview();
}
function mapSvg(width=300,height=245){
  const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');
  svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.setAttribute('class','map-svg');svg.setAttribute('role','img');svg.setAttribute('aria-label','Route map with original and selected trajectories');
  if(!S.route)return svg;
  const data=S.catalog.scenes[S.route.scan],v=S.variant,source=S.route.variants[0],mode=$('floor-picker').value;
  const stepRegion=data.panoramas[v.path[Math.min(S.step,v.path.length-1)]]?.region;
  const cameraRegion=S.packet?.nearest_room??stepRegion;
  const level=mode==='all'?null:mode==='auto'?(data.regions[cameraRegion]?.level??0):Number(mode);
  $('map-floor-label').textContent=level==null?'All floors':'Level '+level;
  const belongs=vp=>level==null||data.regions[data.panoramas[vp]?.region]?.level===level;
  const visible=v.positions_raw.filter((p,i)=>belongs(v.path[i]));
  let points=visible.length?visible:v.positions_raw;
  const nora=data.regions[S.selectedNora];
  if(nora&&(level==null||nora.level===level))points=[...points,nora.position];
  const camera=S.packet?.position_raw;
  if(camera&&(level==null||data.regions[cameraRegion]?.level===level))points=[...points,camera];
  const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]);
  const minX=Math.min(...xs)-2,maxX=Math.max(...xs)+2,minY=Math.min(...ys)-2,maxY=Math.max(...ys)+2;
  const scale=Math.min((width-28)/(maxX-minX),(height-28)/(maxY-minY));
  const ox=(width-(maxX-minX)*scale)/2,oy=(height-(maxY-minY)*scale)/2;
  const project=p=>[ox+(p[0]-minX)*scale,oy+(maxY-p[1])*scale];
  const add=(tag,attrs={},parent=svg)=>{const n=document.createElementNS(ns,tag);for(const[k,val]of Object.entries(attrs))n.setAttribute(k,String(val));parent.append(n);return n;};
  add('rect',{x:0,y:0,width,height,fill:'#fcfdf9'});
  for(const room of Object.values(data.regions)){
    if(level!=null&&room.level!==level)continue;
    const b=room.bounds;if(b[3]<minX||b[0]>maxX||b[4]<minY||b[1]>maxY)continue;
    const [x,y]=project([b[0],b[4]]),isNora=Number(Object.keys(data.regions).find(k=>data.regions[k]===room))===S.selectedNora;
    add('rect',{x,y,width:(b[3]-b[0])*scale,height:(b[4]-b[1])*scale,fill:isNora?'#f5dedd':'#eef1e9','fill-opacity':isNora?.85:.55,stroke:isNora?'#c88f8b':'#dae1d5','stroke-width':.65,rx:2});
  }
  function drawRoute(variant,color,dash){
    let run=[];const flush=()=>{if(run.length>1)add('polyline',{points:run.map(project).map(p=>p.join(',')).join(' '),fill:'none',stroke:color,'stroke-width':dash?1.4:2,'stroke-dasharray':dash?'3 3':'none','stroke-linejoin':'round','stroke-linecap':'round'});run=[];};
    variant.positions_raw.forEach((p,i)=>{if(belongs(variant.path[i]))run.push(p);else flush();});flush();
  }
  drawRoute(source,'#90a7bc',true);drawRoute(v,'#17806b',false);
  v.positions_raw.forEach((p,i)=>{if(!belongs(v.path[i]))return;const [x,y]=project(p);const c=add('circle',{cx:x,cy:y,r:i===S.step?4:2.5,fill:i===S.step?'#174e40':'#fff',stroke:'#17806b','stroke-width':1,'data-step':i,style:'cursor:pointer'});c.addEventListener('click',()=>{stopPreview();seek(i);});});
  function marker(index,label,color){if(index==null||!belongs(v.path[index]))return;const[x,y]=project(v.positions_raw[index]);add('circle',{cx:x,cy:y,r:7.5,fill:color,stroke:'white','stroke-width':1.4});const t=add('text',{x,y:y+2.8,'text-anchor':'middle','font-size':8,'font-weight':700,fill:'white','class':'map-label'});t.textContent=label;}
  marker(0,'S','#4c7193');marker(v.path.length-1,'G','#186452');marker(v.pickup_index,'P','#bb793b');
  if(nora&&(level==null||nora.level===level)){const[x,y]=project(nora.position);const t=add('text',{x,y,'font-size':9,'font-weight':650,fill:'#9e5250','text-anchor':'middle'});t.textContent='Nora '+S.selectedNora;}
  if(camera&&(level==null||data.regions[cameraRegion]?.level===level)){
    const[x,y]=project(camera),theta=S.packet.heading_degrees*Math.PI/180;
    const tip=[x+Math.sin(theta)*13,y-Math.cos(theta)*13],a=[x+Math.sin(theta+2.45)*6,y-Math.cos(theta+2.45)*6],b=[x+Math.sin(theta-2.45)*6,y-Math.cos(theta-2.45)*6];
    add('polygon',{points:[tip,a,b].map(p=>p.join(',')).join(' '),fill:'#193d8c',stroke:'white','stroke-width':1});
  }
  const bar=Math.max(1,Math.round(30/scale));add('line',{x1:12,y1:height-12,x2:12+bar*scale,y2:height-12,stroke:'#697b6c','stroke-width':1.5});
  const label=add('text',{x:12,y:height-17,'font-size':8,fill:'#697b6c'});label.textContent=bar+' m';
  return svg;
}
function renderMaps(){if(!S.route)return;$('mini-map').replaceChildren(mapSvg());if(S.view==='map')$('large-map').replaceChildren(mapSvg(800,500));}
function setView(view){S.view=view;for(const id of ['walk','photos','map'])$(id+'-panel').hidden=id!==view;document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===view));renderMaps();}

$('search').addEventListener('input',e=>{S.search=e.target.value.toLowerCase().trim();renderList();});
$('filters').addEventListener('click',e=>{const button=e.target.closest('[data-filter]');if(!button)return;S.filter=button.dataset.filter;document.querySelectorAll('[data-filter]').forEach(b=>b.classList.toggle('active',b===button));renderList();});
$('variant-picker').addEventListener('change',e=>selectRoute(S.route.id,e.target.value));
$('nora-picker').addEventListener('change',e=>{S.selectedNora=e.target.value===''?null:Number(e.target.value);updateNoraNote();renderMaps();});
$('floor-picker').addEventListener('change',renderMaps);
$('instruction-picker').addEventListener('change',e=>{$('instruction-text').textContent=S.route.instructions.find(i=>String(i.id)===e.target.value)?.text||'';});
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>setView(b.dataset.view));
document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>act(b.dataset.action));
for(const role of ['start','goal','pickup','nora'])$('jump-'+role).onclick=()=>jump(role);
$('show-props').onchange=e=>command('props',{visible:e.target.checked});
$('previous-step').onclick=()=>{stopPreview();seek(S.step-1);};$('next-step').onclick=()=>{stopPreview();seek(S.step+1);};
$('route-slider').addEventListener('input',e=>{stopPreview();$('step-label').textContent='Step '+(Number(e.target.value)+1)+' / '+S.variant.path.length;});
$('route-slider').addEventListener('change',e=>seek(Number(e.target.value)));
$('play-route').onclick=async()=>{if(S.play){stopPreview();return;}if(S.busy)return;if(S.step>=S.variant.path.length-1)await seek(0);S.play=true;$('play-route').textContent='Ⅱ Pause';previewTick();};
$('retry').onclick=()=>selectRoute(S.route.id,S.variant.id);
$('fullscreen').onclick=()=>{if(document.fullscreenElement)document.exitFullscreen();else $('viewport').requestFullscreen?.();};
$('instances-toggle').onclick=()=>$('sidebar').classList.toggle('open');
$('help-button').onclick=()=>$('help-dialog').showModal();$('close-help').onclick=()=>$('help-dialog').close();$('close-image').onclick=()=>$('image-dialog').close();
const keyMap={w:'forward',s:'backward',a:'left',d:'right',q:'strafe_left',e:'strafe_right',arrowleft:'left',arrowright:'right',arrowup:'up',arrowdown:'down'};
document.addEventListener('keydown',e=>{
  if(e.target.closest?.('input,select,textarea')||e.ctrlKey||e.metaKey||e.altKey||$('help-dialog').open||$('image-dialog').open)return;
  const key=e.key.toLowerCase();if(key==='r'){e.preventDefault();if(!e.repeat)jump('start');return;}
  if(keyMap[key]&&S.view==='walk'){e.preventDefault();S.keys.add(key);if(!e.repeat)act(keyMap[key]);}
});
document.addEventListener('keyup',e=>S.keys.delete(e.key.toLowerCase()));
window.addEventListener('blur',()=>{S.keys.clear();S.drag=null;S.look={yaw:0,pitch:0};});
$('viewport').addEventListener('pointerdown',e=>{if(e.button!==0)return;$('viewport').focus();S.drag={x:e.clientX,y:e.clientY};$('viewport').setPointerCapture(e.pointerId);});
$('viewport').addEventListener('pointermove',e=>{if(!S.drag)return;S.look.yaw-=(e.clientX-S.drag.x)*.22;S.look.pitch-=(e.clientY-S.drag.y)*.22;S.drag={x:e.clientX,y:e.clientY};});
for(const name of ['pointerup','pointercancel'])$('viewport').addEventListener(name,()=>S.drag=null);
setInterval(()=>{
  if(S.busy||!S.connected||S.view!=='walk')return;
  if(S.keys.size){act(keyMap[[...S.keys][0]]);return;}
  if(Math.abs(S.look.yaw)+Math.abs(S.look.pitch)>.2){const pending={...S.look};S.look={yaw:0,pitch:0};command('look',pending);}
},110);
window.rxrReview={state:S,selectRoute,act,jump,seek,setView,api,renderMaps};

(async()=>{
  try{
    const response=await fetch('dashboard_catalog.json');if(!response.ok)throw Error('Cannot load the trajectory catalog');S.catalog=await response.json();
    const query=new URLSearchParams(location.search),index=Number(query.get('instance'));
    const route=S.catalog.routes.find(r=>r.index===index)||S.catalog.routes.find(r=>r.id===S.catalog.defaults.route);
    renderList();await selectRoute(route.id,query.get('variant'));
  }catch(e){error(e.message);$('loading').hidden=true;}
})();
