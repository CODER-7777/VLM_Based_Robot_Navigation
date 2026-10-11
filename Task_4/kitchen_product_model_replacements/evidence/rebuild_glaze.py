"""Fit downloaded products while preserving their separate geometry and PBR data.

Procedural colour is baked as an unlit base-colour map, not as reflections.
The web viewer still computes reflections, roughness and glass transmission.
"""
from pathlib import Path
import bpy, json, math, sys
import numpy as np
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parent.parent
REMOTE=Path('/data/robotics/toshith/rxr_author/refined')
OUT=ROOT/'objects';OUT.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.use_scripts_auto_execute=False
bpy.context.preferences.filepaths.save_version=0
reports=[]

def reset():
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.context.preferences.filepaths.use_scripts_auto_execute=False

def objects():return [o for o in bpy.context.scene.objects if o.type=='MESH']
def points(obs):
 dg=bpy.context.evaluated_depsgraph_get();v=[]
 for o in obs:
  e=o.evaluated_get(dg);me=e.to_mesh();v.extend(list(e.matrix_world@p.co) for p in me.vertices);e.to_mesh_clear()
 return np.array(v)
def freeze(obs):
 bpy.context.view_layer.update();ws={o.name:o.matrix_world.copy() for o in obs}
 for o in obs:o.parent=None;o.matrix_world=ws[o.name]
def clear_other(obs):
 freeze(obs)
 for o in list(bpy.context.scene.objects):
  if o not in obs:bpy.data.objects.remove(o,do_unlink=True)
def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.select_set(True)
 bpy.context.view_layer.objects.active=obs[0]
def import_clean(uid):
 reset();bpy.ops.wm.open_mainfile(filepath=str(ROOT/'prepared'/uid/'clean_original.blend'),use_scripts=False)
 return objects()
def apply(obs,m):
 for o in obs:o.matrix_world=m@o.matrix_world
 bpy.context.view_layer.update()
def normalise(obs,height,anchor='floor'):
 v=points(obs);lo=v.min(0);hi=v.max(0)
 if anchor=='floor':
  near=v[v[:,2]<lo[2]+max(.00001,(hi[2]-lo[2])*.0005)]
  center=np.median(near,axis=0);center[2]=lo[2]
 else:center=(lo+hi)/2;center[2]=lo[2]
 scale=height/(hi[2]-lo[2]);apply(obs,Matrix.Scale(scale,4)@Matrix.Translation(-Vector(center)))
 return scale
def smooth(obs):
 for o in obs:
  for p in o.data.polygons:p.use_smooth=True
def subdivide(obs,levels=1):
 # Convert suitable triangle pairs back into quads, then refine curved surfaces.
 # Apply before fitting so changed extrema participate in the placement checks.
 for o in obs:
  select([o]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
  bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.tris_convert_to_quads(face_threshold=math.radians(40),shape_threshold=math.radians(40));bpy.ops.object.mode_set(mode='OBJECT')
  mod=o.modifiers.new('Curved_surface_subdivision','SUBSURF');mod.subdivision_type='CATMULL_CLARK';mod.levels=levels;mod.render_levels=levels;bpy.ops.object.modifier_apply(modifier=mod.name)
 smooth(obs)
def bsdf(m):return next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
def disconnect(m,input_name):
 b=bsdf(m)
 for link in list(b.inputs[input_name].links):m.node_tree.links.remove(link)
def colour(m,rgb,metal=0,rough=.25,trans=0):
 b=bsdf(m)
 for k in ['Base Color','Metallic','Roughness','Alpha','Transmission Weight']:disconnect(m,k)
 c=[((v/255)/12.92 if v/255<=.04045 else ((v/255+.055)/1.055)**2.4) for v in rgb]
 b.inputs['Base Color'].default_value=(*c,1);b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough;b.inputs['Alpha'].default_value=1;b.inputs['Transmission Weight'].default_value=trans
 b.inputs['IOR'].default_value=1.46 if trans else 1.5
 if trans:b.inputs['Coat Weight'].default_value=0
 return b
def material(name,rgb,metal=0,rough=.25,trans=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;colour(m,rgb,metal,rough,trans);return m
def assign(o,m):o.data.materials.clear();o.data.materials.append(m)
def lathe(name,profile,m,segments=128):
 # Catmull-Rom interpolation removes the straight ring transitions of old proxies.
 profile=np.array(profile,float);p=np.vstack([profile[0],profile,profile[-1]]);rings=[]
 for j in range(1,len(p)-2):
  for t in np.linspace(0,1,5,endpoint=False):
   z,r=.5*((2*p[j])+(-p[j-1]+p[j+1])*t+(2*p[j-1]-5*p[j]+4*p[j+1]-p[j+2])*t*t+(-p[j-1]+3*p[j]-3*p[j+1]+p[j+2])*t*t*t)
   rings.append((max(profile[0,0],min(profile[-1,0],z)),max(0.00001,r)))
 rings.append(tuple(profile[-1]));v=[(r*math.cos(2*math.pi*i/segments),r*math.sin(2*math.pi*i/segments),z) for z,r in rings for i in range(segments)];f=[]
 for j in range(len(rings)-1):
  for i in range(segments):f.append((j*segments+i,j*segments+(i+1)%segments,(j+1)*segments+(i+1)%segments,(j+1)*segments+i))
 f.extend([tuple(reversed(range(segments))),tuple((len(rings)-1)*segments+i for i in range(segments))])
 me=bpy.data.meshes.new(name);me.from_pydata(v,[],f);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);assign(o,m);smooth([o]);return o
def tube(name,path,r,m):
 c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.resolution_u=24;c.bevel_resolution=5;c.bevel_depth=r;c.use_fill_caps=True
 s=c.splines.new('BEZIER');s.bezier_points.add(len(path)-1)
 for b,co in zip(s.bezier_points,path):b.co=co;b.handle_left_type='AUTO';b.handle_right_type='AUTO'
 o=bpy.data.objects.new(name,c);bpy.context.collection.objects.link(o);o.data.materials.append(m);bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.convert(target='MESH');return bpy.context.object
def bake_colour(obs,m,colour_socket,name,size=1024):
 select(obs)
 for o in obs:
  if not o.data.uv_layers:
   bpy.context.view_layer.objects.active=o;bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
 if len(obs)>1:
  grid=math.ceil(math.sqrt(len(obs)))
  for j,o in enumerate(obs):
   layer=o.data.uv_layers.active
   for uv in layer.data:uv.uv=((uv.uv.x+j%grid)/grid,(uv.uv.y+j//grid)/grid)
 image=bpy.data.images.new(name,width=size,height=size,alpha=False);image.colorspace_settings.name='sRGB';image.filepath_raw=str(OUT/(name+'.png'));image.file_format='PNG'
 nt=m.node_tree;output=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL');b=bsdf(m);em=nt.nodes.new('ShaderNodeEmission');nt.links.new(colour_socket,em.inputs['Color']);nt.links.new(em.outputs[0],output.inputs['Surface']);target=nt.nodes.new('ShaderNodeTexImage');target.image=image
 for node in nt.nodes:node.select=False
 target.select=True;nt.nodes.active=target
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1;scene.render.threads_mode='FIXED';scene.render.threads=8
 bpy.ops.object.bake(type='EMIT',margin=8,use_clear=True);image.save();image.pack();nt.links.new(b.outputs['BSDF'],output.inputs['Surface']);disconnect(m,'Base Color');nt.links.new(target.outputs['Color'],b.inputs['Base Color']);nt.nodes.remove(em)
def glaze(obs,name,height):
 m=material(name,(94,178,176),rough=.19)
 for o in obs:assign(o,m)
 nt=m.node_tree;pos=nt.nodes.new('ShaderNodeNewGeometry');sep=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(pos.outputs['Position'],sep.inputs[0]);div=nt.nodes.new('ShaderNodeMath');div.operation='DIVIDE';div.inputs[1].default_value=height;nt.links.new(sep.outputs['Z'],div.inputs[0])
 noise=nt.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=105;noise.inputs['Detail'].default_value=4;nt.links.new(pos.outputs['Position'],noise.inputs['Vector']);mul=nt.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=.12;nt.links.new(noise.outputs['Fac'],mul.inputs[0]);add=nt.nodes.new('ShaderNodeMath');add.operation='ADD';nt.links.new(div.outputs[0],add.inputs[0]);nt.links.new(mul.outputs[0],add.inputs[1]);ramp=nt.nodes.new('ShaderNodeValToRGB');cr=ramp.color_ramp
 values=[(0,(40,35,30)),(.32,(47,37,28)),(.39,(124,84,39)),(.44,(85,172,170)),(1,(105,190,187))]
 for j,(p,rgb) in enumerate(values):
  e=cr.elements[j] if j<2 else cr.elements.new(p);e.position=p;e.color=tuple(((c/255)/12.92 if c/255<=.04045 else ((c/255+.055)/1.055)**2.4) for c in rgb)+(1,)
 nt.links.new(add.outputs[0],ramp.inputs[0]);bake_colour(obs,m,ramp.outputs['Color'],name)
 return m
def patina(obs):
 m=material('Photographed_aged_bronze',(102,83,56),metal=.88,rough=.27)
 for o in obs:assign(o,m)
 nt=m.node_tree;tex=nt.nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=125;tex.inputs['Detail'].default_value=5;cr=nt.nodes.new('ShaderNodeValToRGB');cr.color_ramp.elements[0].color=(.031,.023,.011,1);cr.color_ramp.elements[1].color=(.17,.13,.072,1);nt.links.new(tex.outputs['Fac'],cr.inputs[0]);bake_colour(obs,m,cr.outputs['Color'],'HotTap_bronze_patina')
 return m
def export_fit(slug,folder,obs,base,height,product,note,yaw=0):
 dest=OUT/folder;dest.mkdir(exist_ok=True);smooth(obs)
 for i,o in enumerate(obs):o.name='Kitchen_'+folder+'_'+o.name; o.data.name=folder+'_mesh_'+str(i)
 select(obs);bpy.ops.export_scene.gltf(filepath=str(dest/'product_pbr.glb'),export_format='GLB',use_selection=True,export_apply=True,export_animations=False)
 apply(obs,Matrix.Translation(Vector(base))@Matrix.Rotation(math.radians(yaw),4,'Z'))
 v=points(obs);lo=v.min(0);hi=v.max(0);assert abs(lo[2]-base[2])<1e-5,(slug,lo,base)
 select(obs);bpy.ops.export_scene.gltf(filepath=str(dest/'world_pbr.glb'),export_format='GLB',use_selection=True,export_apply=True,export_animations=False)
 # Export the evaluated geometry into a raw MP3D Z-up PLY for physical checks.
 vs=[];faces=[];dg=bpy.context.evaluated_depsgraph_get()
 for o in obs:
  ev=o.evaluated_get(dg);me=ev.to_mesh();w=ev.matrix_world;offset=len(vs);vs.extend(tuple(w@p.co) for p in me.vertices)
  me.calc_loop_triangles();faces.extend(tuple(offset+i for i in t.vertices) for t in me.loop_triangles);ev.to_mesh_clear()
 with (dest/'world.ply').open('w') as f:
  f.write('ply\nformat ascii 1.0\nelement vertex %d\nproperty float x\nproperty float y\nproperty float z\nelement face %d\nproperty list uchar int vertex_indices\nend_header\n'%(len(vs),len(faces)))
  for v0 in vs:f.write('%.9f %.9f %.9f\n'%v0)
  for tri in faces:f.write('3 %d %d %d\n'%tri)
 original=json.loads((ROOT/'current'/(slug+'_fit.json')).read_text());fit=dict(original);fit.update(name=folder,glb=str(REMOTE/'kitchen/objects'/folder/'world_pbr.glb'),world_mesh=str(REMOTE/'kitchen/objects'/folder/'world.ply'),matrix=np.eye(4).tolist(),base=list(base),height=float(hi[2]-lo[2]),product=product,geometry_changed=True,realism_notes=note,placement_refinement={'previous_fit':str(Path(original['glb']).parent/'fit.json'),'locked_height_m':height,'yaw_deg':yaw,'bounds_raw':[lo.tolist(),hi.tolist()]})
 old=np.array(original['delete_aabb']);fit['delete_aabb']=[np.minimum(old[0],lo).tolist(),np.maximum(old[1],hi).tolist()];fit['keep_below_z']=base[2]
 # Hull union is completed by the local trimesh helper after export.
 fit['delete_polygon']=original.get('delete_polygon',[])+[[float(v[0]),float(v[1])] for v in [lo,hi,[lo[0],hi[1],lo[2]],[hi[0],lo[1],lo[2]]]]
 (dest/'fit.json').write_text(json.dumps(fit,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(dest/'fitted.blend'))
 row={'id':slug,'folder':folder,'product':product,'bounds_raw':[lo.tolist(),hi.tolist()],'height_m':float(hi[2]-lo[2]),'triangles':len(faces),'mesh_parts':len(obs),'notes':note};reports.append(row);(OUT/'replacement_inventory.json').write_text(json.dumps(reports,indent=2));print('FITTED',row,flush=True)

reports=json.loads((OUT/'replacement_inventory.json').read_text());reports=[r for r in reports if r['id'] not in ['tea_tray','hot_tap']]
source_rows={r['uid']:r for r in json.loads((ROOT/'evidence/downloaded_models.json').read_text())}
def credit(uid):return {k:source_rows[uid][k] for k in ['uid','name','author','license','url']}
# Tea setting: downloaded ceramic teapot; existing tray and photo-shaped sugar jar.
obs=import_clean('0deff0a5da2546f9a52cdd42dcc2d4fb');subdivide(obs,1);normalise(obs,.155);smooth(obs);glaze(obs,'Photo_reactive_ceramic_glaze',.155)
apply(obs,Matrix.Translation(Vector((1.684,-4.008,.009)))@Matrix.Rotation(math.radians(104),4,'Z'));pot=obs[:]
bpy.ops.import_scene.gltf(filepath=str(ROOT/'current/tea_tray_old.glb'))
tray=[o for o in objects() if o not in pot and any(m and m.name.startswith('tea_tray_v3_bake_p0') for m in o.data.materials)];assert len(tray)==1
freeze(tray);apply(tray,Matrix.Translation(Vector((0,0,-.935))))
for o in list(objects()):
 if o not in pot+tray:bpy.data.objects.remove(o,do_unlink=True)
jar_profile=[(0,.030),(.005,.04),(.023,.051),(.047,.050),(.055,.046),(.058,.042),(.060,.043),(.067,.044),(.080,.034),(.086,.02),(.089,.010),(.095,.011),(.099,.003)]
jar=lathe('Sugar_jar',jar_profile,material('Sugar_jar_glaze',(92,177,176),rough=.2));subdivide([jar],1);normalise([jar],.099);glaze([jar],'Sugar_jar_reactive_glaze',.099);jar.location=(1.648,-3.852,.009);bpy.context.view_layer.update()
obs=pot+tray+[jar];clear_other(obs);apply(obs,Matrix.Translation(Vector((-1.67,3.94,0))))
export_fit('tea_tray','tea_tray_v5',obs,[1.67,-3.94,.935],.164,credit('0deff0a5da2546f9a52cdd42dcc2d4fb'),'Downloaded ceramic teapot with curved handle and spout, photo-coloured reactive glaze. Tray retained; sugar jar rebuilt from the photo. Decorative glaze details remain approximate.')

# Hot tap: use the licensed ornate spout, fitted to a photo-shaped slim stem.
reset();bpy.ops.import_scene.gltf(filepath=str(ROOT/'prepared/antique_spout.glb'));spout=objects();freeze(spout)
apply(spout,Matrix.Translation(Vector((0,0,.210))))
bronze=material('Aged_bronze_base',(101,81,55),metal=.88,rough=.27)
stem=lathe('Photo_tap_stem',[(0,.026),(.003,.031),(.009,.028),(.015,.020),(.021,.018),(.030,.021),(.040,.015),(.053,.017),(.064,.013),(.077,.009),(.183,.008),(.193,.010),(.202,.012),(.212,.011),(.215,.005)],bronze)
connector=tube('Spout_joint',[(0,0,.210),(-.015,.010,.208),(-.027,.010,.211)],.006,bronze)
valve=lathe('Valve_hub',[(0,.010),(.002,.014),(.009,.016),(.016,.012),(.021,.008)],bronze);valve.rotation_euler[0]=math.pi/2;valve.location=(0,-.009,.048)
lever=tube('Photo_lever',[(0,-.025,.048),(0,-.034,.060),(0,-.036,.086)],.0037,bronze)
obs=spout+[stem,connector,valve,lever];patina(obs);normalise(obs,.2321310144)
export_fit('hot_tap','hot_tap_s4_style_v5',obs,[5.975947467127271,-5.382445813460308,.929],.2321310144,credit('c30c4323bb124630bd49c3d9073880a3'),'Licensed antique-faucet spout combined with a photo-shaped slim stem, flange and lower lever. Bronze patina texture is procedural; the exact original tap is not reproduced.',yaw=-33)

print('REPLACEMENTS_BUILT',len(reports),flush=True)
