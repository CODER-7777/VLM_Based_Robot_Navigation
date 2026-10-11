import bpy,json
from pathlib import Path
r=Path(__file__).resolve().parent.parent
for slug in ['knife_block_round','phone','grinder']:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(r/'current'/(slug+'_old.glb')))
 for o in bpy.context.scene.objects:
  if o.type=='MESH':
   print('CURRENT_PART',slug,o.name,len(o.data.polygons),[m.name for m in o.data.materials],[[min((o.matrix_world@v.co)[i] for v in o.data.vertices) for i in range(3)],[max((o.matrix_world@v.co)[i] for v in o.data.vertices) for i in range(3)]],flush=True)
