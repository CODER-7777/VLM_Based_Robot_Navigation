import bpy
from pathlib import Path
O=Path('/data/robotics/toshith/rxr_author/refined/kitchen_all_upgrade')
bpy.ops.wm.open_mainfile(filepath=str(O/'ede86b7cc9804f39a9fcafd263873ee0.blend'))
s=bpy.context.scene;s.camera.data.clip_end=1e6
for mat in bpy.data.materials:
 if mat.use_nodes:
  node=mat.node_tree.nodes.get('Principled BSDF')
  if node:node.inputs['Base Color'].default_value=(.18,.18,.18,1)
s.render.filepath=str(O/'phone_inspect.png');bpy.ops.render.render(write_still=True)
