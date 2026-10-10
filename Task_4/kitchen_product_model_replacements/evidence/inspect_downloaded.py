"""Inspect licensed native assets in isolation; embedded Python is disabled."""
from pathlib import Path
import bpy, json, math
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'prepared';OUT.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.use_scripts_auto_execute=False
sources=json.loads((ROOT/'evidence/downloaded_models.json').read_text())
sources=[r for r in sources if r['uid']!='51768654adf74b38a360b848e0e59ef6']
sources.append(dict(json.loads((ROOT/'evidence/frother_source.json').read_text()),native=True))
report=[]
for row in sources:
 uid=row['uid'];dest=OUT/uid;dest.mkdir(exist_ok=True)
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.context.preferences.filepaths.use_scripts_auto_execute=False
 if row.get('native'):
  bpy.ops.wm.open_mainfile(filepath=str(ROOT/'evidence/aeroccino4_2k.blend'),use_scripts=False)
 else:bpy.ops.import_scene.gltf(filepath=str(ROOT/'sources'/(uid+'.glb')))
 meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
 if uid=='ra8feUCmFGxTrwlug7qOe9i8gme':meshes=[o for o in meshes if o.name.startswith('nespresso maquina_') or o.name=='metal_0']
 if uid=='3f646a36c0a142cfa451af70357f4235':meshes=[o for o in meshes if not any(m and m.name=='Floor' for m in o.data.materials)]
 if uid=='0deff0a5da2546f9a52cdd42dcc2d4fb':meshes=[o for o in meshes if any(m and m.name.startswith(('Ceramic_TeaPot_Body','Ceramic_TeaPot_Up')) for m in o.data.materials)]
 bpy.context.view_layer.update()
 saved_world={o.name:o.matrix_world.copy() for o in meshes}
 for o in list(bpy.context.scene.objects):
  if o not in meshes:bpy.data.objects.remove(o,do_unlink=True)
 # Reify parent transformations. Preserve separate meshes, UVs and materials.
 bpy.context.view_layer.update()
 originals=[]
 for o in meshes:
  w=saved_world[o.name];o.parent=None;o.matrix_world=w
  points=[w@v.co for v in o.data.vertices]
  originals.append({'name':o.name,'bounds':[[min(v[k] for v in points) for k in range(3)],[max(v[k] for v in points) for k in range(3)]],'faces':len(o.data.polygons),'materials':[m.name if m else None for m in o.data.materials],'modifiers':[m.type for m in o.modifiers]})
 points=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
 lo=Vector([min(v[k] for v in points) for k in range(3)]);hi=Vector([max(v[k] for v in points) for k in range(3)])
 centre=(lo+hi)/2;centre.z=lo.z;scale=.25/(hi.z-lo.z)
 transform=Matrix.Scale(scale,4)@Matrix.Translation(-centre)
 for o in meshes:o.matrix_world=transform@o.matrix_world
 bpy.context.view_layer.update()
 bpy.ops.object.select_all(action='DESELECT')
 for o in meshes:o.select_set(True)
 bpy.context.view_layer.objects.active=meshes[0]
 bpy.ops.export_scene.gltf(filepath=str(dest/'clean_original.glb'),export_format='GLB',use_selection=True,export_apply=True,export_animations=False)
 bpy.ops.wm.save_as_mainfile(filepath=str(dest/'clean_original.blend'))
 item={'uid':uid,'source':row,'original_meshes':originals,'source_bounds':[list(lo),list(hi)],'materials':[]}
 for m in bpy.data.materials:
  item['materials'].append({'name':m.name,'nodes':[(n.name,n.type) for n in m.node_tree.nodes] if m.use_nodes else [],'images':[n.image.name for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image] if m.use_nodes else []})
 report.append(item);(OUT/'inspection.json').write_text(json.dumps(report,indent=2))
 s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=8
 s.render.resolution_x=560;s.render.resolution_y=560;s.render.resolution_percentage=100;s.view_settings.view_transform='AgX'
 world=bpy.data.worlds.new('Inspection world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.4,.4,.4,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.4;s.world=world
 bpy.ops.mesh.primitive_plane_add(size=3,location=(0,0,-.0001));floor=bpy.context.object;m=bpy.data.materials.new('Studio floor');m.diffuse_color=(.2,.2,.2,1);floor.data.materials.append(m)
 for name,loc,energy,size in [('softbox',(1,-1,1.4),120,1),('rim',(-1,.5,.8),70,.7)]:
  d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);s.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,.12))-o.location).to_track_quat('-Z','Y').to_euler()
 d=bpy.data.cameras.new('Inspection camera');cam=bpy.data.objects.new('Inspection camera',d);s.collection.objects.link(cam);s.camera=cam;d.lens=48;d.clip_start=.001
 for i,pos in enumerate([(.43,-.52,.39),(-.43,.52,.39)]):
  cam.location=pos;cam.rotation_euler=(Vector((0,0,.12))-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(dest/('view%d.png'%i));bpy.ops.render.render(write_still=True)
 print('INSPECTED',uid,len(meshes),list((hi-lo)*scale),flush=True)
