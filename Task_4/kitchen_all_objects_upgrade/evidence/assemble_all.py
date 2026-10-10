"""Private full-room copy: repaired supports and all prop finishes, named replacements only."""
import bpy,json,math,struct
from pathlib import Path
from mathutils import Matrix,Vector
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'kitchen_all_upgrade';OD=R/'kitchen/objects'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(R/'toaster_selected/test.glb'))
undo=Matrix.Rotation(-math.pi/2,4,'X')
for o in [o for o in bpy.context.scene.objects if o.parent is None]:o.matrix_world=undo@o.matrix_world
bpy.context.view_layer.update()
original=[o.name for o in bpy.context.scene.objects if o.type=='MESH'];manifest=json.loads((R/'toaster_selected/manifest.json').read_text());report=[]
for row in json.loads((W/'counter_materials.json').read_text()):
 name=row['name'];lo=row['xy_min'];hi=row['xy_max'];objs=[o for o in bpy.context.scene.objects if o.name=='Kitchen_counter_'+name+'_top']
 assert len(objs)==1,objs
 for o in objs:
  mat=bpy.data.materials.new('Photographed_'+name+'_stone');mat.use_nodes=True;bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Roughness'].default_value=.32;bsdf.inputs['IOR'].default_value=1.52
  tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(row['texture']);tex.image.name='KitchenAll_'+name+'_stone';mat.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
  o.data.materials.clear();o.data.materials.append(mat)
  uv=o.data.uv_layers.active or o.data.uv_layers.new()
  for f in o.data.polygons:
   f.material_index=0
   for li in f.loop_indices:
    p=o.matrix_world@o.data.vertices[o.data.loops[li].vertex_index].co;uv.data[li].uv=((p.x-lo[0])/(hi[0]-lo[0]),(p.y-lo[1])/(hi[1]-lo[1]))
# Preserve photographed labels, wood grain and fitted geometry. Restore physical
# finish parameters to the real PBR copy; the display copy retains those textures.
for entry in manifest:
 if not isinstance(entry,str):continue
 oldfit=Path(entry);oldfit=oldfit if oldfit.is_absolute() else R/oldfit;fit=json.loads(oldfit.read_text());name=fit['name']
 if name in ['toaster_v4','rangetop'] or name.startswith('sink_'):continue
 newname=name.replace('_v2','_v3') if '_v2' in name else name+'_v3'
 if name.startswith('counter_'):newname=name+'_photo_v3'
 objs=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('Kitchen_'+name+'_')]
 if not objs:print('NO_NAMED_MATCH',name,flush=True);continue
 out=OD/newname;out.mkdir(exist_ok=True)
 for o in objs:
  if name=='blue_jug_v2':
   base=Vector(fit['base']);height=fit['height'];inverse=o.matrix_world.inverted()
   for vertex in o.data.vertices:
    world=o.matrix_world@vertex.co;t=(world.z-base.z)/height
    world.z=base.z+(world.z-base.z)*(.085/height)
    factor=1.10 if t<.55 else (1.10-(t-.55)*.65)
    world.x=base.x+(world.x-base.x)*factor;world.y=base.y+(world.y-base.y)*factor
    vertex.co=inverse@world
   o.data.update();bpy.context.view_layer.update()
  o.name=o.name.replace('Kitchen_'+name+'_','Kitchen_'+newname+'_',1)
  for i,mat0 in enumerate(o.data.materials):
   if not mat0:continue
   mat=mat0.copy();mat.name=newname+'_'+mat0.name;o.data.materials[i]=mat
   bs=mat.node_tree.nodes.get('Principled BSDF') if mat.use_nodes else None
   if not bs:continue
   tag=(o.name+' '+mat0.name).lower()
   rough=.58;metal=0.
   if any(t in tag for t in ['chrome','steel','brass','metal','rim','flange','tap','faucet','air_gap','button']):rough=.22;metal=.86
   if any(t in tag for t in ['ceramic','glaze','jug','canister','tea_tray']):rough=.17;metal=0.
   if any(t in tag for t in ['wood','caddy','basket','block']):rough=.48
   if any(t in tag for t in ['black','handle','pump','phone','remote']):rough=.34;metal=0.
   if name.startswith('counter_'):rough=.32;metal=0.
   bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
   if any(t in tag for t in ['jug','ceramic','canister']):bs.inputs['Coat Weight'].default_value=.35;bs.inputs['Coat Roughness'].default_value=.15
  # Smooth the curving parts without rounding knife edges or changing supports.
  if any(t in o.name.lower() for t in ['jug','bottle','frog','kettle','canister']):
   for f in o.data.polygons:f.use_smooth=True
 bpy.ops.object.select_all(action='DESELECT')
 for o in objs:o.select_set(True)
 bpy.context.view_layer.objects.active=objs[0]
 bpy.ops.export_scene.gltf(filepath=str(out/'world_pbr.glb'),export_format='GLB',use_selection=True,export_apply=True)
 # Preserve raw-Z mesh for independent support and overlap audits.
 vertices=[];faces=[]
 for o in objs:
  o.data.calc_loop_triangles();offset=len(vertices);vertices.extend([list(o.matrix_world@v.co) for v in o.data.vertices]);faces.extend([[offset+i for i in tri.vertices] for tri in o.data.loop_triangles])
 with (out/'world.ply').open('wb') as f:
  f.write(('ply\nformat binary_little_endian 1.0\nelement vertex %d\nproperty float x\nproperty float y\nproperty float z\nelement face %d\nproperty list uchar int vertex_indices\nend_header\n'%(len(vertices),len(faces))).encode())
  for v in vertices:f.write(struct.pack('<3f',*v))
  for face in faces:f.write(struct.pack('<B3i',3,*face))
 if name=='blue_jug_v2':fit['height']=.085;fit['realism_notes']='Photo-guided squat blue pitcher; unseen mouth and handle remain approximate.'
 fit.update(name=newname,glb=str(out/'world_pbr.glb'),world_mesh=str(out/'world.ply'),appearance_revision='Kitchen all-object photo support and physical finish v3',geometry_changed=False)
 (out/'fit.json').write_text(json.dumps(fit,indent=2));manifest[manifest.index(entry)]=str(out/'fit.json');report.append({'old':name,'new':newname,'fit':str(out/'fit.json'),'nodes':len(objs),'method':'Whole-run photo stone' if name.startswith('counter_') else 'Retained photo-fit geometry and textures; physical roughness/metal/coat restored'})
 bpy.ops.object.select_all(action='DESELECT')
# Patch only the thin backsplash strips in this private scene. Remove scanned
# fragments inside each strip, then insert a textured plane at the measured wall.
import bmesh
wall_report=json.loads((W/'wall_materials.json').read_text())
for row in wall_report:
 axis=row['axis'];fixed=row['fixed'];a,b=row['horizontal'];z0,z1=row['vertical'];removed=0
 for obj in list(bpy.context.scene.objects):
  if obj.type!='MESH' or (obj.name.startswith('Kitchen_') and not any(t in obj.name.lower() for t in ['wall','tile','patch','backsplash'])):continue
  coords=[obj.matrix_world@Vector(v) for v in obj.bound_box]
  ba=min(v[axis] for v in coords);bb=max(v[axis] for v in coords);fa=min(v[1-axis] for v in coords);fb=max(v[1-axis] for v in coords)
  if bb<a or ba>b or fb<fixed-.07 or fa>fixed+.07 or max(v.z for v in coords)<z0 or min(v.z for v in coords)>z1:continue
  bm=bmesh.new();bm.from_mesh(obj.data);faces=[]
  for face in bm.faces:
   p=obj.matrix_world@face.calc_center_median()
   if a<=p[axis]<=b and abs(p[1-axis]-fixed)<.065 and z0<=p.z<=z1:faces.append(face)
  removed+=len(faces)
  if faces:bmesh.ops.delete(bm,geom=faces,context='FACES');bm.to_mesh(obj.data)
  bm.free()
 points=[(a,fixed,z0),(b,fixed,z0),(b,fixed,z1),(a,fixed,z1)] if axis==0 else [(fixed,a,z0),(fixed,b,z0),(fixed,b,z1),(fixed,a,z1)]
 mesh=bpy.data.meshes.new('PhotoBacksplash_'+row['name']);mesh.from_pydata(points,[],[(3,2,1,0)]);obj=bpy.data.objects.new('Kitchen_wall_all_'+row['name'],mesh);bpy.context.collection.objects.link(obj);uv=mesh.uv_layers.new()
 for i,loop in enumerate(mesh.loops):uv.data[i].uv=[(0,0),(1,0),(1,1),(0,1)][loop.vertex_index]
 mat=bpy.data.materials.new('TilePhoto_'+row['name']);mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.6;tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(row['texture']);mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);mesh.materials.append(mat)
 row['scanned_faces_removed']=removed
(W/'wall_assembly.json').write_text(json.dumps(wall_report,indent=2))
# Save true materials for the product viewer and for normal-based Gaussian shading.
bpy.ops.wm.save_as_mainfile(filepath=str(W/'kitchen_materials.blend'))
bpy.ops.export_scene.gltf(filepath=str(W/'test_pbr.glb'),export_format='GLB',export_yup=False,use_visible=True,export_apply=True,export_cameras=False,export_lights=False,export_animations=False)
# Habitat stage uses existing baked radiance; avoid applying metallic a second time.
for mat in bpy.data.materials:
 if mat.use_nodes:
  bs=mat.node_tree.nodes.get('Principled BSDF')
  if bs:bs.inputs['Metallic'].default_value=0;bs.inputs['Roughness'].default_value=1
bpy.ops.export_scene.gltf(filepath=str(W/'test.glb'),export_format='GLB',export_yup=False,use_visible=True,export_apply=True,export_cameras=False,export_lights=False,export_animations=False)
(W/'manifest.json').write_text(json.dumps(manifest,indent=2));(W/'assembly.json').write_text(json.dumps({'source':str(R/'toaster_selected/test.glb'),'other_original_nodes':len(original),'replacements':report,'new_phone':str(OD/'phone_v3/fit.json'),'shared_files_modified':False},indent=2));print('ALL_OBJECTS_PRIVATE_BUILD_READY',len(report),flush=True)
