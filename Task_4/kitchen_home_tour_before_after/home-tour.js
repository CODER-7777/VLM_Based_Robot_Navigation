import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';

const viewport=document.getElementById('viewport');
const status=document.getElementById('status');
const loading=document.getElementById('loading');
const requested=new URLSearchParams(location.search).get('object')||'toaster';
const state={ready:false,mode:'walk',error:null,frame:0,toasterParts:0,originalPbr:false,pose:null,selectedObject:requested,items:{},captureMode:false};
state.version='after';state.beforeReady=false;state.versionLoading=false;
window.homeTour=state;
const scene=new THREE.Scene();
scene.background=new THREE.Color(0x18221e);
const camera=new THREE.PerspectiveCamera(54,1,.015,150);
camera.up.set(0,1,0);
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(window.devicePixelRatio,1.5));
renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure=1;
renderer.shadowMap.enabled=true;
renderer.shadowMap.type=THREE.PCFSoftShadowMap;
renderer.shadowMap.autoUpdate=false;
renderer.shadowMap.needsUpdate=true;
let renderDirty=true;
const renderedPosition=new THREE.Vector3(Infinity,Infinity,Infinity),renderedQuaternion=new THREE.Quaternion();
viewport.appendChild(renderer.domElement);
const pmrem=new THREE.PMREMGenerator(renderer);
const environment=pmrem.fromScene(new RoomEnvironment(),.04);
scene.environment=environment.texture;
scene.add(new THREE.HemisphereLight(0xffffff,0x927859,.45));
const light=new THREE.DirectionalLight(0xffffff,1.2);
light.position.set(3.5,3,4.8);
light.target.position.set(4.52,.929,5.19);
light.castShadow=true;
light.shadow.mapSize.set(2048,2048);
Object.assign(light.shadow.camera,{left:-4,right:4,top:4,bottom:-4,near:.1,far:12});
light.shadow.bias=-.0001;
light.shadow.normalBias=.0005;
scene.add(light,light.target);
const controls=new OrbitControls(camera,renderer.domElement);
controls.addEventListener('change',()=>{renderDirty=true;});
Object.assign(controls,{enabled:false,enableDamping:true,dampingFactor:.10,enablePan:false,rotateSpeed:.5,zoomSpeed:.6});
const C=new THREE.Matrix4().set(1,0,0,0,0,0,1,0,0,-1,0,0,0,0,0,1);
const targetPosition=new THREE.Vector3(),targetQuaternion=new THREE.Quaternion();
let busy=false,lastAction=0,catalog=[],byId={},kitchenEnvironment=null;
let repairedRoot=null,beforeRoot=null,beforePromise=null,versionRequest=0;
const versionPicker=document.getElementById('scene-version');

function drawRoom(){
  if(!repairedRoot){renderer.render(scene,camera);return;}
  const width=renderer.domElement.clientWidth,height=renderer.domElement.clientHeight;
  if(state.version==='compare'&&beforeRoot){
    renderer.setScissorTest(true);
    const half=width/2;
    renderer.setViewport(0,0,half,height);renderer.setScissor(0,0,half,height);
    repairedRoot.visible=false;beforeRoot.visible=true;
    renderer.shadowMap.needsUpdate=true;renderer.render(scene,camera);
    renderer.setViewport(half,0,width-half,height);renderer.setScissor(half,0,width-half,height);
    beforeRoot.visible=false;repairedRoot.visible=true;
    renderer.shadowMap.needsUpdate=true;renderer.render(scene,camera);
    renderer.setScissorTest(false);renderer.setViewport(0,0,width,height);
  }else{
    repairedRoot.visible=state.version==='after';
    if(beforeRoot)beforeRoot.visible=state.version==='before';
    renderer.setScissorTest(false);renderer.setViewport(0,0,width,height);
    renderer.render(scene,camera);
  }
}

async function loadBefore(){
  if(beforeRoot)return beforeRoot;
  if(!beforePromise)beforePromise=(async()=>{
    const result=await new GLTFLoader().loadAsync('/before-home-scene.glb',event=>{
      loading.textContent='Loading earlier saved mesh… '+(event.total?Math.round(event.loaded/event.total*100)+'%':Math.round(event.loaded/1048576)+' MB');
    });
    result.scene.rotation.x=-Math.PI/2;
    result.scene.traverse(object=>{
      if(!object.isMesh)return;
      const photographic=material=>new THREE.MeshBasicMaterial({name:material.name+'_before_photographic',map:material.map,color:material.color,vertexColors:material.vertexColors,side:material.side,transparent:material.transparent,opacity:material.opacity,alphaTest:material.alphaTest,toneMapped:false});
      object.material=Array.isArray(object.material)?object.material.map(photographic):photographic(object.material);
    });
    beforeRoot=result.scene;beforeRoot.visible=false;scene.add(beforeRoot);beforeRoot.updateMatrixWorld(true);
    state.beforeReady=true;return beforeRoot;
  })().catch(error=>{beforePromise=null;throw error;});
  return beforePromise;
}

state.setVersion=async function(version){
  if(!['before','after','compare'].includes(version)||!state.ready)return false;
  const request=++versionRequest;
  state.versionLoading=true;versionPicker.disabled=true;
  try{
    if(version!=='after'){
      loading.classList.remove('hidden');await loadBefore();
    }
    if(request!==versionRequest)return false;
    state.version=version;versionPicker.value=version;
    state.captureMode=false;
    document.getElementById('comparison-labels').hidden=version!=='compare';
    document.getElementById('version-note').textContent=version==='before'
      ?'Before: earliest available saved mesh, before the current replacement models. This export is not verified as the untouched dataset.'
      :version==='compare'
      ?'Left: earlier saved mesh. Right: repaired room with fitted 3D models. Both use the same live camera; walk, inspect or turn to compare.'
      :'After: repaired room with downloaded and photo-built 3D models and PBR materials.';
    renderer.shadowMap.needsUpdate=true;resize();drawRoom();
    return true;
  }catch(error){status.textContent='Earlier mesh could not load: '+error.message;versionPicker.value=state.version;return false;}
  finally{if(request===versionRequest){state.versionLoading=false;versionPicker.disabled=false;loading.classList.add('hidden');}}
};
versionPicker.addEventListener('change',event=>state.setVersion(event.target.value));

function resize(){
  renderDirty=true;
  renderer.setSize(viewport.clientWidth,viewport.clientHeight);
  camera.aspect=viewport.clientWidth/viewport.clientHeight/(state.version==='compare'?2:1);
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(viewport);
resize();

function applyPose(packet,instant=false){
  const matrix=new THREE.Matrix4().set(...packet.c2w_raw_gl.flat()).premultiply(C);
  matrix.decompose(targetPosition,targetQuaternion,new THREE.Vector3());
  state.pose=packet;
  state.frame=packet.frame_id;
  if(instant){camera.position.copy(targetPosition);camera.quaternion.copy(targetQuaternion);}
  status.textContent='Ready · walking through the kitchen · frame '+packet.frame_id;
}

function setMode(mode){
  state.mode=mode;
  controls.enabled=mode==='inspect';
  document.getElementById('walk').setAttribute('aria-pressed',String(mode==='walk'));
  document.getElementById('inspect').setAttribute('aria-pressed',String(mode==='inspect'));
  document.getElementById('mode').textContent=mode==='inspect'?'Inspecting '+(byId[state.selectedObject]?.label||'object'):'Walking';
  document.getElementById('help').textContent=mode==='inspect'
    ?'Drag: orbit from the room side · scroll: zoom · choose Walk through home to resume navigation'
    :'W/S: move · A/D: turn · arrow keys: look · drag: turn the camera · R: toaster reference';
}

function objectTitle(item){
  document.getElementById('object-picker').value=item.id;
  document.getElementById('inspect').textContent='Inspect '+item.label;
  document.getElementById('item-notes').textContent=item.notes;
  if(location.pathname==='/kitchen-room'){
    document.title=item.label+' in the kitchen';
    document.querySelector('h1').textContent=item.label+' in the kitchen';
    document.getElementById('intro').textContent='See this item in its kitchen position. Drag to inspect it, scroll to zoom, or use the walking controls.';
  }
}

function focusObject(id){
  const item=byId[id];
  if(!item)return false;
  state.selectedObject=id;
  objectTitle(item);
  if(!state.ready)return false;
  controls.enabled=false;
  controls.enableDamping=false;
  controls.update();
  const target=new THREE.Vector3(item.target_raw[0],item.target_raw[2],-item.target_raw[1]);
  const raw=item.camera.c2w_raw_gl;
  const eye=new THREE.Vector3(raw[0][3],raw[2][3],-raw[1][3]);
  if(id==='toaster'){
    target.set(4.52,1.045,5.19);
    eye.set(4.85,1.38,4.73);
    Object.assign(controls,{minDistance:.48,maxDistance:1.25,minPolarAngle:Math.PI*.25,maxPolarAngle:Math.PI*80/180,minAzimuthAngle:Math.PI*135/180,maxAzimuthAngle:Math.PI});
  }else{
    const spherical=new THREE.Spherical().setFromVector3(eye.clone().sub(target));
    const bounds=state.items[id]?.bounds;
    const size=bounds?new THREE.Vector3().fromArray(bounds.max).sub(new THREE.Vector3().fromArray(bounds.min)):new THREE.Vector3(.12,.15,.12);
    const minimum=Math.min(spherical.radius*.8,Math.max(.18,Math.max(size.x,size.y,size.z)*1.3));
    const distance=Math.max(minimum,Math.min(spherical.radius,Math.max(size.x,size.y,size.z)*3+.18));
    eye.copy(target).add(new THREE.Vector3().setFromSpherical(spherical.clone().set(distance,spherical.phi,spherical.theta)));
    Object.assign(controls,{minDistance:minimum,maxDistance:Math.max(spherical.radius*1.25,minimum+.1),
      minPolarAngle:Math.max(.1,spherical.phi-.13),maxPolarAngle:Math.min(Math.PI-.1,spherical.phi+.13),
      minAzimuthAngle:spherical.theta-.32,maxAzimuthAngle:spherical.theta+.32});
  }
  controls.target.copy(target);
  camera.position.copy(eye);
  controls.update();
  controls.enableDamping=true;
  controls.saveState();
  setMode('inspect');
  state.captureMode=false;
  status.textContent=item.label+' in the kitchen · '+item.method;
  if(window.parent!==window)window.parent.postMessage({type:'kitchen-object-selected',id},location.origin);
  return true;
}
state.focusObject=focusObject;
document.getElementById('object-picker').addEventListener('change',event=>focusObject(event.target.value));
document.getElementById('inspect').addEventListener('click',()=>focusObject(state.selectedObject));
document.getElementById('walk').addEventListener('click',async()=>{
  try{setMode('walk');applyPose(await fetch('/state').then(response=>response.json()),true);}
  catch(error){status.textContent=error.message;}
});

async function act(action){
  if(!state.ready||busy)return;
  busy=true;
  try{
    if(state.mode==='inspect')setMode('walk');
    const response=await fetch('/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action})});
    const packet=await response.json();
    if(!response.ok)throw Error(packet.error||'Navigation failed');
    applyPose(packet);lastAction=performance.now();
  }catch(error){status.textContent=error.message;}
  finally{busy=false;}
}
document.querySelectorAll('[data-action]').forEach(element=>element.addEventListener('click',()=>act(element.dataset.action)));
const keys=new Set(),mapping={w:'forward',s:'backward',a:'left',d:'right',ArrowLeft:'left',ArrowRight:'right',ArrowUp:'up',ArrowDown:'down',r:'reference'};
document.addEventListener('keydown',event=>{
  if(event.target.closest('select,input,textarea'))return;
  const key=event.key.length===1?event.key.toLowerCase():event.key;
  if(mapping[key]&&state.mode==='walk'){event.preventDefault();keys.add(key);if(!event.repeat)act(mapping[key]);}
});
document.addEventListener('keyup',event=>keys.delete(event.key.length===1?event.key.toLowerCase():event.key));
window.addEventListener('blur',()=>keys.clear());
let drag=null;
renderer.domElement.addEventListener('pointerdown',event=>{
  if(state.mode!=='walk')return;
  drag={x:event.clientX,y:event.clientY,dx:0,dy:0};renderer.domElement.setPointerCapture(event.pointerId);
});
renderer.domElement.addEventListener('pointermove',event=>{
  if(!drag||state.mode!=='walk')return;
  drag.dx+=event.clientX-drag.x;drag.dy+=event.clientY-drag.y;
  drag.x=event.clientX;drag.y=event.clientY;
  if(busy)return;
  if(Math.abs(drag.dx)>24){act(drag.dx>0?'right':'left');drag.dx=0;}
  else if(Math.abs(drag.dy)>24){act(drag.dy>0?'down':'up');drag.dy=0;}
});
for(const name of ['pointerup','pointercancel'])renderer.domElement.addEventListener(name,()=>drag=null);
document.getElementById('lighting').addEventListener('change',async event=>{
  try{
    if(event.target.value==='kitchen'){
      if(!kitchenEnvironment){
        const texture=await new THREE.TextureLoader().loadAsync('/tour-assets/kitchen_environment.jpg');
        texture.colorSpace=THREE.SRGBColorSpace;texture.mapping=THREE.EquirectangularReflectionMapping;
        kitchenEnvironment=pmrem.fromEquirectangular(texture);texture.dispose();
      }
      scene.environment=kitchenEnvironment.texture;
    }else scene.environment=environment.texture;
    renderDirty=true;
  }catch(error){status.textContent='Kitchen lighting could not load; studio reflections remain available.';}
});

// Evidence capture renders actual scene triangles at a supplied calibrated photo camera.
state.capturePhoto=async function(packet){
  if(!state.ready)throw Error('Scene not ready');
  state.captureMode=true;
  controls.enabled=false;
  const matrix=new THREE.Matrix4().set(...packet.c2w_raw_gl.flat()).premultiply(C);
  matrix.decompose(camera.position,camera.quaternion,new THREE.Vector3());
  const K=packet.K,n=camera.near;
  camera.projectionMatrix.makePerspective(-K[0][2]/K[0][0]*n,(packet.width-K[0][2])/K[0][0]*n,K[1][2]/K[1][1]*n,-(packet.height-K[1][2])/K[1][1]*n,n,camera.far);
  camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
  renderer.setPixelRatio(1);renderer.setSize(packet.width,packet.height,false);
  await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
  // Preserve the existing calibrated-capture API: it captures the repaired mesh.
  repairedRoot.visible=true;if(beforeRoot)beforeRoot.visible=false;
  renderer.setScissorTest(false);renderer.setViewport(0,0,packet.width,packet.height);
  renderer.render(scene,camera);
  return renderer.domElement.toDataURL('image/png');
};
state.resumeInspection=()=>{resize();return focusObject(state.selectedObject);};

let previous=performance.now();
function animate(now){
  requestAnimationFrame(animate);
  const dt=Math.min(.1,(now-previous)/1000);previous=now;
  if(!state.captureMode){
    if(state.mode==='inspect')controls.update();
    else if(state.ready){
      const alpha=1-Math.exp(-dt*14);camera.position.lerp(targetPosition,alpha);camera.quaternion.slerp(targetQuaternion,alpha);
      if(keys.size&&!busy&&now-lastAction>160)act(mapping[[...keys][0]]);
    }
  }
  if(!state.captureMode&&(renderDirty||camera.position.distanceToSquared(renderedPosition)>1e-10||camera.quaternion.angleTo(renderedQuaternion)>1e-7)){
    drawRoom();renderDirty=false;renderedPosition.copy(camera.position);renderedQuaternion.copy(camera.quaternion);
  }
}
requestAnimationFrame(animate);

try{
  const index=await fetch('/tour-assets/comparison/items/catalog.json').then(response=>response.json());
  catalog=index.room_items||index.items;byId=Object.fromEntries(catalog.map(item=>[item.id,item]));
  if(!byId[state.selectedObject])state.selectedObject='toaster';
  const picker=document.getElementById('object-picker');
  for(const item of catalog){const option=document.createElement('option');option.value=item.id;option.textContent=item.label;picker.appendChild(option);}
  objectTitle(byId[state.selectedObject]);
  try{applyPose(await fetch('/state').then(response=>{if(!response.ok)throw Error('Camera service unavailable');return response.json();}),true);}
  catch(error){state.navigationAvailable=false;applyPose({c2w_raw_gl:byId[state.selectedObject].camera.c2w_raw_gl,frame_id:0},true);document.getElementById('walk').disabled=true;document.querySelectorAll('[data-action]').forEach(button=>button.disabled=true);document.getElementById('intro').textContent='Inspect the saved kitchen objects. The existing walking service is currently unavailable.';}
  const loaded=await new GLTFLoader().loadAsync('/home-scene.glb',event=>{
    const text=event.total?'Loading kitchen… '+Math.min(100,Math.round(event.loaded/event.total*100))+'%':'Loading kitchen… '+Math.round(event.loaded/1048576)+' MB';
    loading.textContent=text;status.textContent=text;
  });
  loaded.scene.rotation.x=-Math.PI/2;
  const meshes={},counterShadows=[];
  const photographic=material=>new THREE.MeshBasicMaterial({name:material.name+'_photographic',map:material.map,color:material.color,vertexColors:material.vertexColors,side:material.side,transparent:material.transparent,opacity:material.opacity,alphaTest:material.alphaTest,toneMapped:false});
  loaded.scene.traverse(object=>{
    if(object.name)meshes[object.name]=object;
    if(!object.isMesh)return;
    meshes[object.name]=object;
    let kitchenName=object.name;
    for(let parent=object.parent;parent&&!kitchenName.startsWith('Kitchen_');parent=parent.parent){if(parent.name.startsWith('Kitchen_'))kitchenName=parent.name;}
    if(kitchenName.startsWith('Kitchen_')){
      object.castShadow=!kitchenName.startsWith('Kitchen_counter_')&&!kitchenName.startsWith('Kitchen_wall_');
      if(kitchenName.startsWith('Kitchen_counter_')){
        // These textures already contain the photographed illumination. Preserve
        // their colour, then add contact shadows separately instead of lighting twice.
        object.material=Array.isArray(object.material)?object.material.map(photographic):photographic(object.material);
        if(object.name.endsWith('_top'))counterShadows.push(object);
      }else if(kitchenName.startsWith('Kitchen_rangetop_'))object.receiveShadow=true;
    }else if(!object.name.startsWith('WallRepair_')){
      object.material=Array.isArray(object.material)?object.material.map(photographic):photographic(object.material);
    }
  });
  for(const counter of counterShadows){
    const material=new THREE.ShadowMaterial({opacity:.28,side:THREE.DoubleSide,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-1,polygonOffsetUnits:-1});
    const shadow=new THREE.Mesh(counter.geometry,material);
    shadow.name='Counter_contact_shadow';shadow.position.copy(counter.position);shadow.quaternion.copy(counter.quaternion);shadow.scale.copy(counter.scale);shadow.receiveShadow=true;
    counter.parent.add(shadow);
  }
  repairedRoot=loaded.scene;
  scene.add(loaded.scene);loaded.scene.updateMatrixWorld(true);renderDirty=true;renderer.shadowMap.needsUpdate=true;
  for(const item of catalog){
    const parts=item.nodes.map(name=>meshes[name]||meshes[THREE.PropertyBinding.sanitizeNodeName(name)]);
    if(parts.some(part=>!part))throw Error('Missing latest mesh parts for '+item.label);
    const box=new THREE.Box3();
    const materials=[];
    parts.forEach(part=>{box.union(new THREE.Box3().setFromObject(part));part.traverse(o=>{if(o.isMesh)materials.push(...(Array.isArray(o.material)?o.material:[o.material]));});});
    state.items[item.id]={parts:parts.length,bounds:parts.length?{min:box.min.toArray(),max:box.max.toArray()}:null,
      standardMaterials:materials.filter(material=>material.isMeshStandardMaterial).length,
      method:item.method};
  }
  const toaster=catalog.find(item=>item.id==='toaster').nodes.map(name=>meshes[name]||meshes[THREE.PropertyBinding.sanitizeNodeName(name)]);
  state.toasterParts=toaster.length;
  state.originalPbr=toaster.every(part=>{const material=Array.isArray(part.material)?part.material[0]:part.material;return Boolean(material.map&&material.normalMap&&material.metalnessMap&&material.roughnessMap);});
  state.toasterBounds=state.items.toaster.bounds;
  if(toaster.length!==11||!state.originalPbr)throw Error('Original toaster material maps were not retained');
  window.homeTourScene=scene;window.homeTourCamera=camera;window.homeTourRenderer=renderer;
  state.ready=true;versionPicker.disabled=false;loading.classList.add('hidden');
  status.textContent='Ready · '+catalog.length+' kitchen items available';
  if(location.pathname==='/kitchen-room'||state.navigationAvailable===false)focusObject(state.selectedObject);
  const requestedVersion=new URLSearchParams(location.search).get('version');
  if(requestedVersion)await state.setVersion(requestedVersion);
}catch(error){state.error=error.message;loading.textContent=error.message;status.textContent=error.message;console.error(error);}
