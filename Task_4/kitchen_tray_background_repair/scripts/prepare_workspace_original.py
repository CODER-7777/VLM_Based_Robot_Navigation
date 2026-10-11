"""Reconcile authoritative room geometry, private fits and UI catalog without shared writes."""
from pathlib import Path
import json,re,copy,sys
import numpy as np,trimesh
from shapely.geometry import MultiPoint,Polygon,Point,box
from shapely.ops import unary_union
import glb_tools as gt
ROOT=Path(__file__).resolve().parents[1];R=Path('/data/robotics/toshith/rxr_author/refined');P=R/'kitchen_product_replacements'
NEW={'tea_tray':'tea_tray_v7','frother':'frother_v7','coffee_machine2':'coffee_machine2_v7'}
CURRENT={re.sub(r'_v\d+$','',row['folder']):row['folder'] for row in json.loads((P/'replacement_inventory.json').read_text())}
CURRENT.update(NEW)
SLUGS={'soap_dish_p':'soap_dish','hot_tap_s4_style':'hot_tap','soap_pump_p_lathe':'soap_pump','air_gap_p_lathe':'air_gap','coffee_machine2':'coffee_machine'}

def source_fit(stem,old):
 path=ROOT/'objects'/NEW[stem]/'fit.json' if stem in NEW else Path(old)
 return path.parent.name,json.loads(path.read_text()),path

def classify(n,anc,entries):
 names=[n.get('name','')]+list(reversed(anc))
 for e in sorted(entries,key=lambda e:len(e['stem']),reverse=True):
  stem=e['stem'];pattern=(r'^Kitchen_'+re.escape(e['folder'])+r'(?:_|$)') if stem=='bottles' else (r'^Kitchen_'+re.escape(stem)+r'(?:_v\d+)?(?:_|$)')
  if any(re.match(pattern,name) for name in names):return e
 return None

def extraction(g,b,parts,path):
 # Preserve source material JSON and texture bytes. Geometry is flattened in world Y-up.
 from build_repairs import fresh,add_mesh
 out,blob=fresh();mats={};images={};textures={};samplers={}
 def tex(idx):
  if idx in textures:return textures[idx]
  t=copy.deepcopy(g['textures'][idx]);imidx=t['source']
  if imidx not in images:
   im=copy.deepcopy(g['images'][imidx]);v=g['bufferViews'][im['bufferView']];lo=v.get('byteOffset',0);blob.extend(b'\0'*((-len(blob))%4));o=len(blob);blob.extend(b[lo:lo+v['byteLength']]);vi=len(out.setdefault('bufferViews',[]));out['bufferViews'].append({'buffer':0,'byteOffset':o,'byteLength':v['byteLength']});im['bufferView']=vi;images[imidx]=len(out.setdefault('images',[]));out['images'].append(im)
  t['source']=images[imidx]
  if 'sampler' in t:
   old=t['sampler']
   if old not in samplers:samplers[old]=len(out.setdefault('samplers',[]));out['samplers'].append(copy.deepcopy(g['samplers'][old]))
   t['sampler']=samplers[old]
  textures[idx]=len(out.setdefault('textures',[]));out['textures'].append(t);return textures[idx]
 def remap(x):
  if isinstance(x,dict):
   for k,v in x.items():
    if k.endswith('Texture') and isinstance(v,dict) and 'index' in v:v['index']=tex(v['index'])
    else:remap(v)
  elif isinstance(x,list):
   for v in x:remap(v)
 for i,n,p,m,anc,v,f in parts:
  old=p.get('material',0)
  if old not in mats:
   mat=copy.deepcopy(g['materials'][old]);remap(mat);mats[old]=len(out['materials']);out['materials'].append(mat)
  uv=gt.accessor(g,b,p['attributes']['TEXCOORD_0']) if 'TEXCOORD_0' in p['attributes'] else None
  normal=None
  if 'NORMAL' in p['attributes']:
   normal=gt.accessor(g,b,p['attributes']['NORMAL'])@np.linalg.inv(m[:3,:3]);normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-10)
  add_mesh(out,blob,n['name'],v,f,mats[old],uv,normal)
 out['extensionsUsed']=copy.deepcopy(g.get('extensionsUsed',[]));gt.write(path,out,bytes(blob))

if __name__=='__main__':
 g,b=gt.read(ROOT/'home_pbr_products.glb');parts=list(gt.parts(g,b));entries=[]
 for old in json.loads(Path('/data/robotics/toshith/vivekananda/kitchen_repair_20261011/private_manifest.json').read_text()):
  stem=re.sub(r'_v\d+$','',Path(old).parent.name);folder,fit,fp=source_fit(stem,old);entries.append({'stem':stem,'folder':folder,'input_fit':str(fp),'fit':fit,'parts':[]})
 for part in parts:
  e=classify(part[1],part[4],entries)
  if e is not None:e['parts'].append(part)
 manifest=[];inventory=[];objects=[];supports=[];absent=[]
 for e in entries:
  stem=e['stem'];pr=e['parts'];folder=ROOT/'objects'/e['folder'];folder.mkdir(parents=True,exist_ok=True)
  if not pr:
   absent.append({'input_fit':e['input_fit'],'reason':'No active mesh node in the authoritative saved room','name':stem});continue
  v=np.concatenate([p[5] for p in pr]);faces=[];offset=0
  for p in pr:faces.extend(p[6]+offset);offset+=len(p[5])
  mesh=trimesh.Trimesh(v,np.array(faces),process=False);mesh.export(folder/'world.ply')
  if stem not in NEW:extraction(g,b,pr,folder/'world_pbr.glb')
  fit=copy.deepcopy(e['fit']);lo,hi=v.min(0),v.max(0)
  fit.update(name=e['folder'],glb=str(folder/'world_pbr.glb'),world_mesh=str(folder/'world.ply'),matrix=np.eye(4).tolist(),bounds_raw=[lo.tolist(),hi.tolist()],height=float(hi[2]-lo[2]),source_fit=e['input_fit'],authoritative_scene=str(ROOT/'home_pbr_products.glb'))
  if stem=='frogs':
   fit.pop('product',None);fit['provenance']={'geometry':'Existing photo-guided articulated frog reconstruction; retained from reference room.','external_license':'No external source licence verified. Prior synthetic Sketchfab frog URL and royalty-free claim removed from this workspace copy.'}
  (folder/'fit.json').write_text(json.dumps(fit,indent=2));manifest.append(str(folder/'fit.json'));hull=MultiPoint(v[:,:2]).convex_hull
  item={'name':stem,'folder':e['folder'],'input_fit':e['input_fit'],'fit_path':str(folder/'fit.json'),'bounds_raw':[lo.tolist(),hi.tolist()],'vertices':len(v),'triangles':len(faces),'nodes':list(dict.fromkeys(p[1]['name'] for p in pr)),'parts':len(set(p[0] for p in pr)),'geometry_in_revision':stem in ['soap_bottle','soap_dish_p','blue_jug','phone_dock']}
  inventory.append(item);e['item']=item;e['v']=v;e['hull']=hull;e['fit_path']=str(folder/'fit.json')
  if stem.startswith('counter_'):
   for p in pr:
    if p[1]['name'].endswith('_top'):
     polys=[Polygon(t[:,:2]) for t in p[5][p[6]] if np.ptp(t[:,2])<1e-5 and Polygon(t[:,:2]).area>1e-10];supports.append((stem,unary_union(polys),float(hi[2])))
  elif not stem.startswith('sink_'):objects.append(e)
 (ROOT/'private_manifest.json').write_text(json.dumps(manifest,indent=2));(ROOT/'evidence/scene_inventory.json').write_text(json.dumps({'manifest_input_entries':len(entries),'active_entries':len(inventory),'objects':inventory,'absent_entries':absent},indent=2))
 checks=[]
 rangepoly=box(6.405,-3.995,7.114,-3.081)
 for e in objects:
  v=e['v'];stem=e['stem'];hull=e['hull'];lo=v.min(0);hi=v.max(0);footpts=v[v[:,2]<lo[2]+.002];foot=MultiPoint(footpts[:,:2]).convex_hull;support=None
  if stem=='rangetop':support=('built-in',rangepoly,None)
  elif rangepoly.contains(hull.centroid):support=('stovetop_grate',rangepoly,.991)
  else:
   eligible=[s for s in supports if s[1].buffer(.003).intersects(foot) and s[2]<=lo[2]+.03]
   if eligible:support=max(eligible,key=lambda s:s[1].intersection(foot).area)
  issues=[];gap=None;fraction=None
  if not support:issues.append('No counter under supporting foot')
  elif support[2] is not None:
   gap=float((lo[2]-support[2])*1000);fraction=foot.intersection(support[1]).area/max(foot.area,1e-10)
   if gap>4:issues.append('Floats more than 4 mm')
   if gap<-6:issues.append('Sunk more than 6 mm')
   if fraction<.95:issues.append('Supporting foot extends beyond counter or cutout')
  checks.append({'name':e['folder'],'support':support[0] if support else None,'gap_mm':gap,'foot_support_fraction':fraction,'bounds_raw':[lo.tolist(),hi.tolist()],'issues':issues,'size_review':('Cord-inclusive phone bounds are 36 cm; casing and handset checked separately.' if stem=='phone' else 'Miniature creamer remains about 5 cm tall; size preserved from photo fit.' if stem=='blue_jug' else None)})
 collisions=[]
 for j,e in enumerate(objects):
  for other in objects[j+1:]:
   if e['stem']=='rangetop' or other['stem']=='rangetop':continue
   zlo=max(e['v'][:,2].min(),other['v'][:,2].min());zhi=min(e['v'][:,2].max(),other['v'][:,2].max());over=e['hull'].intersection(other['hull']).area
   if zhi-zlo>.004 and over>5e-5:collisions.append({'a':e['folder'],'b':other['folder'],'plan_overlap_cm2':over*1e4,'status':'Conservative plan hull flag; exact geometry review required'})
 report={'scene':str(ROOT/'home_pbr_products.glb'),'scene_sha256':gt.sha(ROOT/'home_pbr_products.glb'),'manifest_entries_checked':len(entries),'active_entries':len(inventory),'props_checked':len(checks),'absent_entries':absent,'support_checks':checks,'conservative_collision_flags':collisions,'method':'Evaluated active saved GLB triangles in raw Z-up metres; contact footprints tested against actual counter top triangle unions, including sink cutouts. Convex hull overlap is a screening test, not proof of collision.','browser_review':'pending: no browser runtime or local socket access in this session'}
 (ROOT/'evidence/placement_audit.json').write_text(json.dumps(report,indent=2))
 cat=json.loads(Path('/data/robotics/toshith/vivekananda/kitchen_repair_20261011/comparison/items/catalog.json').read_text());by={SLUGS.get(e['stem'],e['stem']):e for e in entries if e.get('item')}
 for item in cat['items']:
  chosen=[e for e in entries if e['stem']=='bottles' and e.get('item')] if item['id']=='bottles' else [by[item['id']]]
  item['fit_paths']=[e['fit_path'] for e in chosen];item['nodes']=sum([e['item']['nodes'] for e in chosen],[]);v=np.concatenate([e['v'] for e in chosen]);item['bounds_raw']=[v.min(0).tolist(),v.max(0).tolist()];item['target_raw']=v.mean(0).tolist();item['mesh_parts']=sum(e['item']['parts'] for e in chosen);item['updated_in_revision']=any(e['stem'] in NEW for e in chosen);item['counter_z']=.935 if item['id'] in ['tea_tray','glass_kettle','frother','coffee_machine'] else .991 if item['id']=='range_kettle' else .929
  item['render_provenance']='Direct OpenGL PBR render of the saved room at the dataset camera; browser verification pending.'
  if item['updated_in_revision']:item['notes']=chosen[0]['fit'].get('realism_notes',item['notes']);item['method']='photo-guided geometry with PBR finish'
  if item['id']=='frogs':item['product']=None;item['method']='retained photo-guided articulated reconstruction';item['notes']='Existing later articulated frog pair retained. Heads, proportions and decoration remain approximate. No downloaded frog asset or external licence is claimed.'
 cat.update(revision='kitchen_workspace_v7_20261011',source_scene=str(ROOT/'home_pbr_products.glb'),scene_refresh='Three photo-guided shape repairs; active-scene fit and model reconciliation',validation={'renderer':'Direct OpenGL PBR; saved triangles and original textures','browser':'pending','publication':'not performed','manifest_input_entries':len(entries),'active_entries':len(inventory)})
 (ROOT/'comparison/items/catalog.json').write_text(json.dumps(cat,indent=2));print('PREPARED',len(inventory),'active entries,',len(checks),'props,',len(absent),'absent entries; support issues',[(c['name'],c['issues']) for c in checks if c['issues']], 'collision flags',collisions,flush=True)
