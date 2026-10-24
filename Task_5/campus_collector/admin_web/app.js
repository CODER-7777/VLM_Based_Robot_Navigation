'use strict';
const $=id=>document.getElementById(id);
let state=null, selectedUser=null, selected=new Set(), dirty=false, busy=false;
function message(text,error=false){$('message').textContent=text;$('message').classList.toggle('error',error);}
async function request(path,data){
  const response=await fetch(path,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const value=await response.json();
  if(response.status===401){location.href='/login';throw Error('Sign in again.');}
  if(!response.ok)throw Error(value.error||'Request failed.');
  return value;
}
const cell=(row,text,tag='td')=>{const node=document.createElement(tag);node.textContent=text;row.append(node);return node;};
function person(){return state?.users.find(p=>p.username===selectedUser);}
function editable(){return person()?.role==='contributor';}
function filtered(){
  const search=$('search').value.trim().toLowerCase(),group=$('collection').value,min=Number($('length').value);
  return (state?.instructions||[]).filter(t=>(!group||t.collection===group)&&t.length_m>=min&&
    (!$('assigned-only').checked||selected.has(t.key))&&(!search||[t.instruction,t.key,t.scene,t.collection_label,t.source_folder].join(' ').toLowerCase().includes(search)));
}
function markDirty(){dirty=true;renderTasks();}
function renderTasks(){
  const p=person(),rows=filtered();$('tasks').replaceChildren();
  $('person-title').textContent=p?p.username:'Select a person';
  $('person-mode').textContent=p?(p.role==='admin'?'Administrator · full catalog':p.enabled?'Contributor':'Disabled'):'—';
  $('person-info').textContent=!p?'Choose an account on the left.':p.role==='admin'?'Administrators can preview every available instruction. Their full-catalog access is automatic.':
    'Select the instructions this person should see. Saving replaces their assignment; previous recordings stay unchanged.';
  for(const task of rows){
    const row=document.createElement('tr'),first=document.createElement('td'),check=document.createElement('input');
    check.type='checkbox';check.checked=selected.has(task.key);check.disabled=!editable()||!task.assignable;check.setAttribute('aria-label','Assign '+task.key);
    check.onchange=()=>{check.checked?selected.add(task.key):selected.delete(task.key);markDirty();};first.append(check);row.append(first);
    const detail=document.createElement('td'),link=document.createElement('button');link.className='task-link';link.textContent=task.instruction;
    link.onclick=()=>{$('task-detail').textContent=[task.key,task.instruction,'', 'Collection: '+task.collection_label,'Scene: '+task.scene,
      'Reference route: '+task.length_m.toFixed(2)+' m','Memories: '+task.memory_count,'Source folder: '+task.source_folder,'Source file: '+task.source_file,'',task.notes].join('\n');$('task-dialog').showModal();};
    detail.append(link);const id=document.createElement('small');id.className='task-id';id.textContent=task.key+(!task.available?' · scene unavailable':!task.assignable?' · source asset needs review':'');detail.append(id);row.append(detail);
    const group=cell(row,task.collection_label+'\n'+task.scene);group.className='collection-name';
    cell(row,task.length_m.toFixed(2)+' m');cell(row,String(task.memory_count));$('tasks').append(row);
  }
  $('result-count').textContent=rows.length+' shown';$('selected-count').textContent=selected.size+' selected';
  $('dirty-label').textContent=dirty?'Unsaved assignment changes':'No unsaved changes';
  $('save').disabled=!editable()||!dirty||busy;
  for(const id of ['select-filtered','clear-filtered'])$(id).disabled=!editable()||busy;
  const active=!!(p?.worker.active||p?.worker.processing);
  $('reset-password').disabled=!editable()||active||busy;
  $('toggle-enabled').disabled=!editable()||active||busy;
  $('toggle-enabled').textContent=p?.enabled?'Disable account':'Enable account';
}
function choose(username){
  if(dirty&&!confirm('Discard the unsaved assignment changes?'))return;
  selectedUser=username;selected=new Set(person()?.episode_keys||[]);dirty=false;renderPeople();renderTasks();
}
function renderPeople(){
  $('people').replaceChildren();
  for(const p of state.users){
    const button=document.createElement('button');button.className='person';button.setAttribute('aria-current',String(p.username===selectedUser));
    const strong=document.createElement('strong');strong.textContent=p.username;
    const info=document.createElement('small');info.textContent=(p.role==='admin'?'Admin · full catalog':p.episode_keys.length+' tasks')+' · '+p.saved_samples+' saved'+(!p.enabled?' · disabled':'')+(p.worker.active?' · recording':p.worker.processing?' · processing':'');
    button.append(strong,info);button.onclick=()=>choose(p.username);$('people').append(button);
  }
}
function renderSources(){
  $('sources').replaceChildren();
  for(const source of state.collections){const row=document.createElement('tr');cell(row,source.label);cell(row,String(source.count));
    for(const value of [source.source_folder,source.source_file]){const td=document.createElement('td'),code=document.createElement('code');code.textContent=value;td.append(code);row.append(td);}$('sources').append(row);}
  $('audit').replaceChildren();
  for(const event of state.audit){const row=document.createElement('tr');cell(row,new Date(event.created_at).toLocaleString());cell(row,event.actor);cell(row,event.action.replaceAll('_',' '));cell(row,event.target);
    cell(row,event.action==='assign_tasks'?(event.details.after?.length||0)+' instructions':event.action==='create_user'?(event.details.episode_keys?.length||0)+' instructions':'');$('audit').append(row);}
}
async function load(force=false){
  if(busy||(!force&&(dirty||document.querySelector('dialog[open]'))))return;
  const next=await request('/api/admin/state');state=next;$('identity').textContent=state.me+' · administrator';
  $('total-tasks').textContent=state.instructions.length;$('total-users').textContent=state.users.filter(p=>p.role!=='admin').length;
  $('total-samples').textContent=state.users.reduce((n,p)=>n+p.saved_samples,0);
  $('active-workers').textContent=state.users.filter(p=>p.worker.active||p.worker.processing).length+' / '+state.capacity;
  const old=$('collection').value;$('collection').replaceChildren(new Option('All collections',''));
  for(const group of state.collections)$('collection').append(new Option(group.label+' ('+group.count+')',group.id));$('collection').value=old;
  if(!state.users.some(p=>p.username===selectedUser))selectedUser=state.users.find(p=>p.role!=='admin')?.username||state.me;
  selected=new Set(person()?.episode_keys||[]);dirty=false;renderPeople();renderSources();renderTasks();
}
function credentials(value){$('issued-name').value=value.username;$('issued-password').value=value.password;$('issued-password').type='password';$('show-password').checked=false;$('copy-credentials').textContent='Copy login details';$('credentials-dialog').showModal();}
async function mutate(action,data){busy=true;renderTasks();try{return await request('/api/admin/'+action,data);}finally{busy=false;renderTasks();}}
for(const id of ['search','collection','length','assigned-only'])$(id).addEventListener(id==='search'?'input':'change',renderTasks);
$('select-filtered').onclick=()=>{for(const task of filtered())if(task.assignable)selected.add(task.key);markDirty();};
$('clear-filtered').onclick=()=>{for(const task of filtered())selected.delete(task.key);markDirty();};
$('save').onclick=async()=>{const p=person();if(!p||!confirm('Assign '+selected.size+' instructions to '+p.username+'? This replaces their current assignment.'))return;
  try{await mutate('assign',{username:p.username,episode_keys:[...selected],revision:p.revision});dirty=false;await load(true);message('Assignment saved. This account will see the selected tasks on its next dashboard load.');}catch(e){message(e.message,true);}};
$('refresh').onclick=()=>{if(dirty&&!confirm('Discard unsaved changes and refresh?'))return;dirty=false;load(true).catch(e=>message(e.message,true));};
$('new-user').onclick=()=>{$('create-form').reset();$('create-error').textContent='';$('create-with-selection').disabled=!selected.size;$('create-dialog').showModal();};
$('create-form').onsubmit=async event=>{event.preventDefault();const username=$('create-name').value.trim();
  try{const result=await mutate('create-user',{username,password:$('create-password').value,episode_keys:$('create-with-selection').checked?[...selected]:[]});
    $('create-password').value='';$('create-dialog').close();selectedUser=username;dirty=false;await load(true);credentials(result);message('Account created. Copy its login privately, then assign tasks if needed.');}catch(e){$('create-error').textContent=e.message;message(e.message,true);}};
$('reset-password').onclick=async()=>{const p=person();if(!p||!confirm('Generate a new password for '+p.username+'? Their old login will expire; recordings and assignments are preserved.'))return;
  try{credentials(await mutate('reset-password',{username:p.username}));message('Password reset. Share the new login privately.');}catch(e){message(e.message,true);}};
$('toggle-enabled').onclick=async()=>{const p=person();if(!p||!confirm((p.enabled?'Disable ':'Enable ')+p.username+'?'))return;
  try{await mutate('set-enabled',{username:p.username,enabled:!p.enabled});await load(true);message('Account access updated; recordings preserved.');}catch(e){message(e.message,true);}};
document.querySelectorAll('[data-close]').forEach(button=>button.onclick=()=>$(button.dataset.close).close());
$('credentials-dialog').addEventListener('close',()=>{$('issued-name').value='';$('issued-password').value='';$('show-password').checked=false;});
$('show-password').onchange=()=>{$('issued-password').type=$('show-password').checked?'text':'password';};
$('copy-credentials').onclick=async()=>{try{await navigator.clipboard.writeText('Website: '+location.origin+'\nUsername: '+$('issued-name').value+'\nPassword: '+$('issued-password').value);$('copy-credentials').textContent='Copied';message('Login copied. Share it only with this contributor.');}catch(e){message('Clipboard unavailable. Use Show password and copy the fields manually.',true);}};
$('signout').onclick=async()=>{try{await request('/auth/logout',{});location.href='/login';}catch(e){message(e.message,true);}};
addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
load(true).catch(e=>message(e.message,true));setInterval(()=>load().catch(e=>message(e.message,true)),15000);
