import bpy,sys,json,math,os
from pathlib import Path
from mathutils import Matrix,Vector
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'toaster_upgrade';O=R/'kitchen/objects/toaster_v3'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(O/'world_pbr.glb'))
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=64;sc.cycles.use_denoising=True
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='CUDA';prefs.get_devices()
 for device in prefs.devices:device.use=device.type=='CUDA'
 sc.cycles.device='GPU'
except Exception as e:print('GPU_SETUP',e,flush=True)
sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.view_settings.exposure=0;sc.view_settings.gamma=1
world=bpy.data.worlds.new('Kitchen lighting from source photos');world.use_nodes=True;sc.world=world
n=world.node_tree.nodes;links=world.node_tree.links;env=n.new('ShaderNodeTexEnvironment');env.image=bpy.data.images.load(str(W/'kitchen_environment.jpg'));links.new(env.outputs['Color'],n.get('Background').inputs['Color']);n.get('Background').inputs['Strength'].default_value=.8
for mat in bpy.data.materials:
 if not mat.use_nodes:continue
 bs=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
 if not bs:continue
 if mat.name.startswith('steel'):
  bs.inputs['Metallic'].default_value=1;bs.inputs['Roughness'].default_value=.18
  if 'Anisotropic IOR Level' in bs.inputs:bs.inputs['Anisotropic IOR Level'].default_value=.45
  nd=mat.node_tree.nodes;lk=mat.node_tree.links
  tex=nd.new('ShaderNodeTexCoord');mapping=nd.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(1,1,45)
  noise=nd.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1800;noise.inputs['Detail'].default_value=2
  bump=nd.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.10;bump.inputs['Distance'].default_value=.000025
  lk.new(tex.outputs['Generated'],mapping.inputs[0]);lk.new(mapping.outputs[0],noise.inputs['Vector']);lk.new(noise.outputs['Fac'],bump.inputs['Height']);lk.new(bump.outputs['Normal'],bs.inputs['Normal'])
 elif mat.name.startswith('plastic'):bs.inputs['Roughness'].default_value=.28

objs=[o for o in sc.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in objs:o.select_set(True)
bpy.context.view_layer.objects.active=objs[0];bpy.ops.object.join();obj=bpy.context.object;obj.name='Toaster_Cuisinart_v3'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
for p in obj.data.polygons:p.use_smooth=True
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(68),island_margin=.008);bpy.ops.object.mode_set(mode='OBJECT')
data=json.load(open(W/'placement.json'));cd=bpy.data.cameras.new('Photo camera');camera=bpy.data.objects.new('Photo camera',cd);sc.collection.objects.link(camera);sc.camera=camera
camera.matrix_world=Matrix(data['camera']['c2w']);cd.type='PERSP';cd.sensor_width=36;cd.lens=data['camera']['K'][0]*36/1280
sc.render.resolution_x=1280;sc.render.resolution_y=1024;sc.render.resolution_percentage=100;sc.render.film_transparent=True
sc.render.image_settings.file_format='PNG';sc.render.filepath=str(W/'toaster_cycles_photo.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'toaster_materials.blend'))
sc.render.bake.margin=12
if hasattr(sc.render.bake,'view_from'):sc.render.bake.view_from='ACTIVE_CAMERA';print('BAKE_VIEW',sc.render.bake.view_from,flush=True)
materials=list(obj.data.materials)
def bake(name,kind,colorspace='sRGB'):
 image=bpy.data.images.new(name,width=2048,height=2048,alpha=False,float_buffer=True);image.colorspace_settings.name=colorspace
 for mat in materials:
  node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=image;mat.node_tree.nodes.active=node
 bpy.context.view_layer.objects.active=obj;obj.select_set(True)
 bpy.ops.object.bake(type=kind)
 image.filepath_raw=str(O/(name+'.png'));image.file_format='PNG';image.save()
 print('BAKED',name,flush=True);return image
combined=bake('kitchen_reflections','COMBINED')
normal=bake('brushed_normal','NORMAL','Non-Color')
rough=bake('brushed_roughness','ROUGHNESS','Non-Color')
# Keep a true PBR export with normal and roughness maps for renderers with environment lighting.
for mat in materials:
 bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');nd=mat.node_tree.nodes;lk=mat.node_tree.links
 for link in list(lk):
  if link.to_node==bs and link.to_socket.name in ['Normal','Roughness']:lk.remove(link)
 tx=nd.new('ShaderNodeTexImage');tx.image=normal;nm=nd.new('ShaderNodeNormalMap');lk.new(tx.outputs['Color'],nm.inputs['Color']);lk.new(nm.outputs['Normal'],bs.inputs['Normal'])
 tx=nd.new('ShaderNodeTexImage');tx.image=rough;lk.new(tx.outputs['Color'],bs.inputs['Roughness'])
bpy.ops.export_scene.gltf(filepath=str(O/'world_pbr_textured.glb'),export_format='GLB',use_selection=True,export_apply=True)
# Habitat-compatible surface appearance retains actual kitchen reflections rather than a flat gray recolor.
mat=bpy.data.materials.new('Toaster_KitchenReflectionBake');mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');tx=mat.node_tree.nodes.new('ShaderNodeTexImage');tx.image=combined
mat.node_tree.links.new(tx.outputs['Color'],bs.inputs['Base Color']);bs.inputs['Metallic'].default_value=0;bs.inputs['Roughness'].default_value=1
obj.data.materials.clear();obj.data.materials.append(mat)
for p in obj.data.polygons:p.material_index=0
bpy.ops.export_scene.gltf(filepath=str(O/'world_baked.glb'),export_format='GLB',use_selection=True,export_apply=True)
print('TOASTER_FINISHED',flush=True)
