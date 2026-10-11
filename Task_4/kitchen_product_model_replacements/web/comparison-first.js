const base='/tour-assets/comparison/items/';
const picker=document.getElementById('item-picker'),room=document.getElementById('room');
let items=[],selected=null;

function focusRoom(){
  if(!selected)return;
  const target=room.contentWindow?.homeTour;
  if(target?.focusObject)target.focusObject(selected.id);
}

function showItem(id,push=true){
  selected=items.find(item=>item.id===id)||items[0];
  picker.value=selected.id;
  document.title=selected.label+' — comparison and kitchen view';
  document.getElementById('comparison-heading').textContent='1. '+selected.label+' — real photo and current scene';
  document.getElementById('render-caption').textContent='Current '+selected.label.toLowerCase()+' in the kitchen';
  const real=document.getElementById('real-image'),render=document.getElementById('render-image');
  real.src=base+selected.real_image;render.src=base+selected.render_image;document.getElementById('before-image').src=base+selected.id+'_before.jpg';
  real.alt='Real photograph of '+selected.label;
  render.alt='Current '+selected.label+' rendered at the same calibrated photograph camera';
  document.getElementById('item-notes').textContent=selected.notes;
  const source=document.getElementById('item-source');source.replaceChildren();
  source.append(document.createTextNode('Method: '+selected.method+'.'));
  if(selected.product){
    const product=selected.product;
    source.append(document.createTextNode(' Source: '));
    const link=document.createElement('a');link.href=product.url;link.textContent=product.name||'Product model';source.append(link);
    const licence={by:'CC BY', 'by-sa':'CC BY-SA',cc0:'CC0'}[product.license]||product.license||'';
    source.append(document.createTextNode((product.author?' by '+product.author:'')+(licence?' · '+licence:'')));
  }
  const model=document.getElementById('model-link');model.hidden=!selected.fit_paths.length;model.href='/item-viewer?object='+encodeURIComponent(selected.id);
  document.getElementById('earlier-image').src='/all-preview/'+selected.earlier_comparison;
  document.getElementById('earlier').open=false;
  document.getElementById('room-heading').textContent='2. See '+selected.label.toLowerCase()+' in the kitchen';
  document.getElementById('show-room').textContent='Show '+selected.label.toLowerCase()+' in the kitchen';
  document.getElementById('room-link').href='/kitchen-room?object='+encodeURIComponent(selected.id);
  document.getElementById('room-image').src=base+selected.room_image;
  document.getElementById('room-image').alt=selected.label+' within its kitchen surroundings';
  document.getElementById('item-count').textContent=(items.indexOf(selected)+1)+' of '+items.length;
  document.getElementById('catalog-status').textContent=(selected.updated_in_revision?'Updated in this revision · ':'Retained from the earlier mesh revision · ')+selected.label;
  if(push)history.replaceState({},'', '/?object='+encodeURIComponent(selected.id));
  if(room.getAttribute('src'))focusRoom();
}

room.addEventListener('load',focusRoom);
window.addEventListener('message',event=>{if(event.origin===location.origin&&event.source===room.contentWindow&&event.data?.type==='kitchen-object-selected'&&items.some(item=>item.id===event.data.id)&&event.data.id!==selected?.id)showItem(event.data.id);});
document.getElementById('show-room').addEventListener('click',()=>{
  if(!selected)return;
  if(!room.getAttribute('src'))room.src='/kitchen-room?object='+encodeURIComponent(selected.id);
  else focusRoom();
  room.hidden=false;document.getElementById('room-preview').hidden=true;
  document.getElementById('room-status').textContent='The room may take about a minute to load. Once ready, change the selected item without reloading the scene.';
  room.scrollIntoView({behavior:'smooth',block:'start'});
});
picker.addEventListener('change',()=>showItem(picker.value));
for(const [button,direction] of [['previous',-1],['next',1]]){
  document.getElementById(button).addEventListener('click',()=>showItem(items[(items.indexOf(selected)+direction+items.length)%items.length].id));
}
try{
  const response=await fetch(base+'catalog.json');
  if(!response.ok)throw Error('Kitchen item catalog is unavailable');
  items=(await response.json()).items;
  for(const item of items){const option=document.createElement('option');option.value=item.id;option.textContent=item.label;picker.appendChild(option);}
  showItem(new URLSearchParams(location.search).get('object')||'toaster',false);
  for(const element of [picker,document.getElementById('previous'),document.getElementById('next'),document.getElementById('show-room')])element.disabled=false;
}catch(error){document.getElementById('catalog-status').textContent=error.message;console.error(error);}
