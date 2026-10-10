"""Create a texture-free proxy in raw MP3D Z-up for Habitat's GLB loader."""
import bpy,math,json
from pathlib import Path
from mathutils import Matrix
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'split_visuals'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(R/'toaster_selected/test.glb'))
undo=Matrix.Rotation(-math.pi/2,4,'X')
for obj in [o for o in bpy.context.scene.objects if o.parent is None]:obj.matrix_world=undo@obj.matrix_world
bpy.context.view_layer.update()
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
for obj in objects:obj.data.materials.clear()
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:obj.select_set(True)
bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();obj=bpy.context.object
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
before=len(obj.data.polygons)
modifier=obj.modifiers.new('Conservative static navigation simplification','DECIMATE')
modifier.ratio=min(1.,120000/max(1,before));modifier.use_collapse_triangulate=True
bpy.ops.object.modifier_apply(modifier=modifier.name)
after=len(obj.data.polygons)
obj.name='InvisibleCollisionProxy'
bpy.ops.export_scene.gltf(filepath=str(W/'proxy.glb'),export_format='GLB',export_yup=False,use_selection=True,export_materials='NONE',export_normals=False,export_texcoords=False,export_apply=True)
(W/'proxy.json').write_text(json.dumps({'source':str(R/'toaster_selected/test.glb'),'coordinate_frame':'Raw MP3D Z-up metres; Habitat GLB stage loader applies (x,z,-y)','source_faces':before,'proxy_faces':after,'method':'Texture-free static mesh simplification, target 120000 faces; retains room topology rather than enclosing the entire room in a solid box','requires_validation':'NavMesh rebuilt and snapped kitchen start checked by physics service','dynamic_collision_objects':False},indent=2))
print('PROXY_READY',before,after,flush=True)
