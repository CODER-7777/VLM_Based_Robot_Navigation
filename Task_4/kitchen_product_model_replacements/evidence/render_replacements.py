from pathlib import Path
import bpy,json,math
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent
for row in json.loads((ROOT/'objects/replacement_inventory.json').read_text()):
 dest=ROOT/'objects'/row['folder']
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.gltf(filepath=str(dest/'product_pbr.glb'))
 s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=8
 s.render.resolution_x=560;s.render.resolution_y=560;s.render.resolution_percentage=100;s.view_settings.view_transform='AgX'
 world=bpy.data.worlds.new('Inspection world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.4,.4,.4,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.4;s.world=world
 bpy.ops.mesh.primitive_plane_add(size=3,location=(0,0,-.0001));floor=bpy.context.object;m=bpy.data.materials.new('Studio floor');m.diffuse_color=(.2,.2,.2,1);floor.data.materials.append(m)
 for name,loc,energy,size in [('softbox',(1,-1,1.4),120,1),('rim',(-1,.5,.8),70,.7)]:
  d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);s.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,.12))-o.location).to_track_quat('-Z','Y').to_euler()
 d=bpy.data.cameras.new('Inspection camera');cam=bpy.data.objects.new('Inspection camera',d);s.collection.objects.link(cam);s.camera=cam;d.lens=48;d.clip_start=.001
 for i,pos in enumerate([(.43,-.52,.39),(-.43,.52,.39)]):
  cam.location=pos;cam.rotation_euler=(Vector((0,0,.12))-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(ROOT/'images'/(row['id']+'_new_%d.png'%i));bpy.ops.render.render(write_still=True)
