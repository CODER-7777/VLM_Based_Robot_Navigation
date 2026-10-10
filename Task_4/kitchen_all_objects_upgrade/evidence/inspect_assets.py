import bpy,json,math
from pathlib import Path
from mathutils import Vector
R=Path('/data/robotics/toshith/rxr_author/refined');O=R/'kitchen_all_upgrade'
uids=['ede86b7cc9804f39a9fcafd263873ee0','0a09b18567594cac9ad165fda5d7e17b','33168c1e12784aaea08ed4e727665884','3ee32fff29074d869949cfd61f8467c4']
report=[]
for uid in uids:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/uid/'extracted/scene.gltf'))
 meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];row={'uid':uid,'meshes':[]}
 points=[]
 for o in meshes:
  p=[o.matrix_world@v.co for v in o.data.vertices];points.extend(p)
  row['meshes'].append({'name':o.name,'vertices':len(p),'lo':[min(v[i] for v in p) for i in range(3)],'hi':[max(v[i] for v in p) for i in range(3)],'material':[m.name for m in o.data.materials]})
 lo=Vector([min(v[i] for v in points) for i in range(3)]);hi=Vector([max(v[i] for v in points) for i in range(3)]);center=(lo+hi)/2;size=max(hi-lo)
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.resolution_x=600;scene.render.resolution_y=500;scene.render.resolution_percentage=100;scene.view_settings.view_transform='Standard'
 world=bpy.data.worlds.new('Studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.5,.5,.5,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.6;scene.world=world
 lamp=bpy.data.lights.new('softbox','AREA');lamp.energy=500*size**2;lamp.size=size*2;l=bpy.data.objects.new('softbox',lamp);scene.collection.objects.link(l);l.location=center+Vector((size,-size,2*size));l.rotation_euler=(center-l.location).to_track_quat('-Z','Y').to_euler()
 cd=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.lens=45
 for i,pos in enumerate([(1.5,-2,1.5),(-1.5,2,1.5)]):
  cam.location=center+Vector(pos)*size;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(O/(uid+'_view%d.png'%i));bpy.ops.render.render(write_still=True)
 bpy.ops.wm.save_as_mainfile(filepath=str(O/(uid+'.blend')))
 report.append(row);print('ASSET_INSPECTED',uid,flush=True)
(O/'asset_geometry.json').write_text(json.dumps(report,indent=2))
