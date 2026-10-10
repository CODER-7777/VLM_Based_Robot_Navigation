import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'kitchen_all_upgrade'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(W/'ede86b7cc9804f39a9fcafd263873ee0/extracted/scene.gltf'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];points=[o.matrix_world@v.co for o in objects for v in o.data.vertices];lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)]);center=(lo+hi)/2;center.z=lo.z;scale=.32/max(hi.x-lo.x,hi.y-lo.y)
for o in objects:
 m=o.matrix_world.copy();o.parent=None;o.matrix_world=Matrix.Scale(scale,4)@Matrix.Translation(-center)@m
 for mat in o.data.materials:
  if mat.use_nodes:
   b=mat.node_tree.nodes.get('Principled BSDF')
   if b:b.inputs['Base Color'].default_value=(.16,.18,.19,1);b.inputs['Roughness'].default_value=.43
bpy.ops.object.select_all(action='DESELECT')
for o in objects:o.select_set(True)
bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();o=bpy.context.object;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
# Keep the author's detailed original separately, use a 110k-face navigation/display mesh.
bpy.ops.export_scene.gltf(filepath=str(W/'phone_canonical_full.glb'),export_format='GLB',use_selection=True)
mod=o.modifiers.new('Display detail reduction','DECIMATE');mod.ratio=min(1,110000/len(o.data.polygons));bpy.ops.object.modifier_apply(modifier=mod.name)
for face in o.data.polygons:face.use_smooth=True
bpy.ops.export_scene.gltf(filepath=str(W/'phone_canonical.glb'),export_format='GLB',use_selection=True)
print('CANONICAL_PHONE',len(o.data.vertices),len(o.data.polygons),flush=True)
