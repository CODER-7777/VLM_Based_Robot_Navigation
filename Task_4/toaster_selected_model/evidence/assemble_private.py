"""Replace only the named toaster in the existing private wall-repaired scene.

The input full-room GLB uses raw MP3D Z-up coordinates. Blender's standard glTF
import rotates it as if it were Y-up, so undo that once on scene roots.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector
R=Path('/data/robotics/toshith/rxr_author/refined')
W=R/'toaster_selected'
O=R/'kitchen/objects/toaster_v4'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(R/'toaster_wall_repair/test.glb'))
undo=Matrix.Rotation(-math.pi/2,4,'X')
roots=[o for o in bpy.context.scene.objects if o.parent is None]
for obj in roots:obj.matrix_world=undo@obj.matrix_world
bpy.context.view_layer.update()
old=[o for o in bpy.context.scene.objects if o.name.startswith('Kitchen_toaster_v3_')]
if not old:raise RuntimeError('Named old toaster not found; refusing duplicate insertion')
deleted=[o.name for o in old]
for obj in old:bpy.data.objects.remove(obj,do_unlink=True)
remaining=[o.name for o in bpy.context.scene.objects if o.type=='MESH']
before=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(O/'world_baked.glb'))
added=set(bpy.data.objects)-before
for obj in added:obj.name='Kitchen_toaster_v4_'+obj.name
bpy.context.view_layer.update()
points=[o.matrix_world@v.co for o in added if o.type=='MESH' for v in o.data.vertices]
low=[min(p[i] for p in points) for i in range(3)]
high=[max(p[i] for p in points) for i in range(3)]
expected=json.loads((W/'placement.json').read_text())['bounds']
assert max(abs(low[i]-expected[0][i]) for i in range(3))<1e-5
assert max(abs(high[i]-expected[1][i]) for i in range(3))<1e-5
bpy.ops.export_scene.gltf(filepath=str(W/'test.glb'),export_format='GLB',export_yup=False,use_visible=True,export_cameras=False,export_lights=False,export_animations=False,export_vertex_color='MATERIAL',export_apply=True)
(W/'assembly.json').write_text(json.dumps({'input_scene':str(R/'toaster_wall_repair/test.glb'),'old_toaster_nodes_removed':deleted,'new_nodes':[o.name for o in added],'other_meshes_preserved':len(remaining),'new_toaster_bounds':[low,high],'output':str(W/'test.glb')},indent=2))
print('SELECTED_PRIVATE_SCENE_COMPLETE',len(remaining),'other meshes retained',flush=True)
