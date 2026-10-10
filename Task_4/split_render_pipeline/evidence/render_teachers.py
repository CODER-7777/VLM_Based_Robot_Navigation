"""Render the selected toaster's PBR material at the actual training poses."""
import bpy,json
from pathlib import Path
from mathutils import Matrix
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'split_visuals'
bpy.ops.wm.open_mainfile(filepath=str(R/'kitchen/objects/toaster_v4/toaster_materials.blend'))
scene=bpy.context.scene;scene.cycles.samples=32;scene.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='CUDA';prefs.get_devices()
for device in prefs.devices:device.use=device.type=='CUDA'
scene.cycles.device='GPU'
scene.render.resolution_x=640;scene.render.resolution_y=512;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.color_mode='RGBA'
for record in json.loads((W/'data/cameras.json').read_text()):
 scene.camera.matrix_world=Matrix(record['c2w_raw_gl'])
 scene.camera.data.lens=record['K'][0][0]*36/record['width']
 # Match the calibrated principal point, including vertical sensor fit.
 scene.camera.data.sensor_fit='HORIZONTAL'
 scene.camera.data.shift_x=(record['width']/2-record['K'][0][2])/record['width']
 scene.camera.data.shift_y=(record['K'][1][2]-record['height']/2)/record['width']
 scene.render.filepath=str(W/'data/teacher'/(record['name']+'.png'))
 bpy.ops.render.render(write_still=True)
print('PBR_TEACHER_VIEWS_READY',flush=True)
