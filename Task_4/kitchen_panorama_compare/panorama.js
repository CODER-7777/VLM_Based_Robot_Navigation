import * as THREE from 'three';

const config = await fetch('/config.json').then(r => r.json());
const navigation = new URL(location.href); navigation.port = '8767'; navigation.pathname = '/';
for (const [id,path] of [['comparisons','/'],['room','/kitchen-room'],['models','/models']]) {
  const link = new URL(navigation); link.pathname = path; document.getElementById(id).href = link.href;
}
const status = document.getElementById('status');
const orientation = {yaw:0,pitch:-.23,fov:100};
const panels = ['before','after'].map(id => {
  const element = document.getElementById(id);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(orientation.fov,1,.1,10);
  const renderer = new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
  renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  element.append(renderer.domElement);
  const material = new THREE.ShaderMaterial({
    uniforms:{image:{value:null}},
    vertexShader:'varying vec3 direction;void main(){direction=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
    fragmentShader:'uniform sampler2D image;varying vec3 direction;void main(){vec3 d=normalize(direction);float u=atan(d.x,-d.z)/6.28318530718+0.5;float v=asin(clamp(d.y,-1.0,1.0))/3.14159265359+0.5;gl_FragColor=texture2D(image,vec2(u,v));#include <colorspace_fragment>}',
    side:THREE.BackSide,
  });
  // Keep the include on a separate preprocessor line.
  material.fragmentShader = material.fragmentShader.replace(';#include',';\n#include').replace('fragment>}', 'fragment>\n}');
  const sphere = new THREE.Mesh(new THREE.SphereGeometry(5,64,48),material); scene.add(sphere);
  const panel = {id,element,scene,camera,renderer,material,texture:null};
  new ResizeObserver(()=>render()).observe(element);
  let drag=null;
  element.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY};element.setPointerCapture(e.pointerId);});
  element.addEventListener('pointermove',e=>{
    if(!drag)return;
    orientation.yaw-=(e.clientX-drag.x)*.004;
    orientation.pitch=Math.max(-1.45,Math.min(1.45,orientation.pitch+(e.clientY-drag.y)*.004));
    drag={x:e.clientX,y:e.clientY};render();
  });
  for(const name of ['pointerup','pointercancel'])element.addEventListener(name,()=>drag=null);
  element.addEventListener('wheel',e=>{e.preventDefault();orientation.fov=Math.max(40,Math.min(120,orientation.fov+Math.sign(e.deltaY)*4));render();},{passive:false});
  return panel;
});
let ready=false, current=null, generation=0;
function render(){
  for(const p of panels){
    p.renderer.setSize(p.element.clientWidth,p.element.clientHeight,false);
    p.camera.aspect=p.element.clientWidth/p.element.clientHeight;p.camera.fov=orientation.fov;p.camera.updateProjectionMatrix();
    p.camera.lookAt(Math.sin(orientation.yaw)*Math.cos(orientation.pitch),Math.sin(orientation.pitch),-Math.cos(orientation.yaw)*Math.cos(orientation.pitch));
    if(p.texture)p.renderer.render(p.scene,p.camera);
  }
  document.getElementById('fov').value=orientation.fov;
  document.getElementById('fov-value').textContent=Math.round(orientation.fov)+'°';
}
const select=document.getElementById('position');
const defaultYaw={sink:0,corner:.65,range:1.3,tea:-1.64,coffee:2.05};
for(const view of config.views){const option=document.createElement('option');option.value=view.id;option.textContent=view.label;select.append(option);}
async function choose(id){
  ready=false;const request=++generation;current=config.views.find(v=>v.id===id);
  select.value=id;window.panorama.error=null;
  status.textContent='Loading '+current.label+'…';
  try{
    const textures=await Promise.all(panels.map(p=>new THREE.TextureLoader().loadAsync('/images/'+id+'_'+p.id+'.jpg')));
    if(request!==generation){textures.forEach(t=>t.dispose());return;}
    panels.forEach((p,i)=>{p.texture?.dispose();p.texture=textures[i];p.texture.colorSpace=THREE.SRGBColorSpace;p.texture.wrapS=THREE.RepeatWrapping;p.material.uniforms.image.value=p.texture;});
    for(const p of panels)document.getElementById('download-'+p.id).href='/images/'+id+'_'+p.id+'.jpg';
    document.getElementById('download-pair').href='/images/'+id+'_comparison.jpg';
    document.getElementById('strip').src='/images/'+id+'_comparison.jpg';
    document.getElementById('coverage').textContent='Objects photographed from this position: '+current.objects.map(v=>v.replaceAll('_',' ')).join(', ')+'.';
    orientation.yaw=defaultYaw[id];orientation.pitch=-.23;
    ready=true;render();status.textContent=current.label+' · linked rotation and zoom · 4096 × 2048 panoramas';
  }catch(error){status.textContent='This panorama is not ready: '+error.message;window.panorama.error=error.message;}
}
window.panorama={get ready(){return ready;},get view(){return current?.id;},orientation,panels,choose,render,config,error:null};
select.addEventListener('change',()=>choose(select.value));
document.getElementById('reset').addEventListener('click',()=>{orientation.yaw=defaultYaw[current.id];orientation.pitch=-.23;orientation.fov=100;render();});
document.getElementById('fov').addEventListener('input',e=>{orientation.fov=+e.target.value;render();});
choose('sink');
