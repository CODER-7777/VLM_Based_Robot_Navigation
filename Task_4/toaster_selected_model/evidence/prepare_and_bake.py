"""Run with Blender. Preserve the selected asset's UVs and PBR maps.

The Habitat stage variant uses a separate reflection bake; the true PBR export
keeps the author's material maps and remains suitable for environment lighting.
"""
import bpy, json, math, struct
from pathlib import Path
from mathutils import Matrix, Vector

R = Path('/data/robotics/toshith/rxr_author/refined')
W = R / 'toaster_selected'
O = R / 'kitchen/objects/toaster_v4'
O.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(W / 'source/scene.gltf'))
objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
points = [o.matrix_world @ v.co for o in objects for v in o.data.vertices]
lo = Vector([min(p[i] for p in points) for i in range(3)])
hi = Vector([max(p[i] for p in points) for i in range(3)])
center = (lo + hi) / 2
center.z = lo.z
height = .20
scale = height / (hi.z - lo.z)
# The source control panel points along -Y. Rotate it toward the photo camera.
yaw = math.radians(176.7927672881334)
base = Vector((4.52, -5.19, .929))
transform = Matrix.Translation(base) @ Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Scale(scale, 4) @ Matrix.Translation(-center)
for obj in objects:
    matrix = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = transform @ matrix
bpy.context.view_layer.update()
points = [o.matrix_world @ v.co for o in objects for v in o.data.vertices]
shift = max(0, 4.425 - min(p.x for p in points))
if shift:
    for obj in objects:
        obj.location.x += shift
    base.x += shift
    bpy.context.view_layer.update()
points = [o.matrix_world @ v.co for o in objects for v in o.data.vertices]
low = [min(p[i] for p in points) for i in range(3)]
high = [max(p[i] for p in points) for i in range(3)]
assert abs(low[2] - .929) < 1e-5
assert low[0] >= 4.405 and low[1] >= -5.446
for img in bpy.data.images:
    img.name = 'AtTheSpeedOf_' + img.name
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = objects[0]
# Export the original maps, normals and UVs before any bake-related nodes exist.
bpy.ops.export_scene.gltf(filepath=str(O / 'world_pbr.glb'), export_format='GLB', use_selection=True, export_apply=True)
# A model-centered PBR copy is convenient for standalone product viewers.
for obj in objects:
    obj.location -= base
bpy.ops.export_scene.gltf(filepath=str(O / 'product_pbr.glb'), export_format='GLB', use_selection=True, export_apply=True)
for obj in objects:
    obj.location += base
bpy.context.view_layer.update()

vertices, faces = [], []
for obj in objects:
    obj.data.calc_loop_triangles()
    offset = len(vertices)
    vertices.extend([list(obj.matrix_world @ v.co) for v in obj.data.vertices])
    faces.extend([[offset + i for i in t.vertices] for t in obj.data.loop_triangles])
with (O / 'world.ply').open('wb') as out:
    out.write(('ply\nformat binary_little_endian 1.0\nelement vertex %d\nproperty float x\nproperty float y\nproperty float z\nelement face %d\nproperty list uchar int vertex_indices\nend_header\n' % (len(vertices), len(faces))).encode())
    for p in vertices:
        out.write(struct.pack('<3f', *p))
    for f in faces:
        out.write(struct.pack('<B3i', 3, *f))
placement = json.loads((R / 'toaster_upgrade/placement.json').read_text())
placement.update(base=list(base), dims=[b-a for a,b in zip(low,high)], bounds=[low,high], source_up='+Y in glTF; +Z in Blender', yaw_deg=math.degrees(yaw), uniform_scale=scale)
(W / 'placement.json').write_text(json.dumps(placement, indent=2))
print('FITTED_SELECTED_TOASTER', json.dumps(placement), flush=True)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 96
scene.cycles.use_denoising = True
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'CUDA'
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == 'CUDA'
    scene.cycles.device = 'GPU'
except Exception as exc:
    print('GPU_SETUP', exc, flush=True)
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.view_settings.exposure = 0
world = bpy.data.worlds.new('Observed kitchen illumination')
world.use_nodes = True
scene.world = world
env = world.node_tree.nodes.new('ShaderNodeTexEnvironment')
env.image = bpy.data.images.load(str(R / 'toaster_upgrade/kitchen_environment.jpg'))
world.node_tree.links.new(env.outputs['Color'], world.node_tree.nodes['Background'].inputs['Color'])
world.node_tree.nodes['Background'].inputs['Strength'].default_value = .8
# The JPEG panorama clips the radiance of the room's bright surfaces. Broad,
# neutral fill panels approximate that lost illumination for the Habitat bake.
# This is an appearance fit, not a measured HDR reconstruction.
def soft_fill(name, position, power, size):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = power
    data.shape = 'RECTANGLE'
    data.size = size
    data.size_y = size * 1.2
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = position
    light.rotation_euler = (base + Vector((0, 0, .10)) - light.location).to_track_quat('-Z', 'Y').to_euler()
soft_fill('Approximate broad room highlight', (4.78, -4.30, 1.65), 35, .65)
soft_fill('Approximate counter-side fill', (5.05, -5.0, 1.45), 10, .45)
camera_data = bpy.data.cameras.new('Calibrated photo camera')
camera = bpy.data.objects.new('Calibrated photo camera', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera.matrix_world = Matrix(placement['camera']['c2w'])
camera_data.sensor_width = 36
camera_data.lens = placement['camera']['K'][0] * 36 / 1280
scene.render.resolution_x = 1280
scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(W / 'selected_cycles_photo.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O / 'toaster_materials.blend'))
# All components share the artist's atlas. Join without changing the UV layout.
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = objects[0]
bpy.ops.object.join()
obj = bpy.context.object
obj.name = 'AtTheSpeedOf_Toaster_v4'
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
image = bpy.data.images.new('AtTheSpeedOf_KitchenReflections', width=2048, height=2048, alpha=False, float_buffer=True)
image.colorspace_settings.name = 'sRGB'
for material in obj.data.materials:
    node = material.node_tree.nodes.new('ShaderNodeTexImage')
    node.image = image
    material.node_tree.nodes.active = node
scene.render.bake.margin = 12
if hasattr(scene.render.bake, 'view_from'):
    scene.render.bake.view_from = 'ACTIVE_CAMERA'
bpy.ops.object.bake(type='COMBINED')
image.filepath_raw = str(O / 'kitchen_reflections.png')
image.file_format = 'PNG'
image.save()
material = bpy.data.materials.new('AtTheSpeedOf_HabitatReflectionBake')
material.use_nodes = True
bsdf = material.node_tree.nodes.get('Principled BSDF')
texture = material.node_tree.nodes.new('ShaderNodeTexImage')
texture.image = image
material.node_tree.links.new(texture.outputs['Color'], bsdf.inputs['Base Color'])
bsdf.inputs['Metallic'].default_value = 0
bsdf.inputs['Roughness'].default_value = 1
obj.data.materials.clear()
obj.data.materials.append(material)
for polygon in obj.data.polygons:
    polygon.material_index = 0
bpy.ops.export_scene.gltf(filepath=str(O / 'world_baked.glb'), export_format='GLB', use_selection=True, export_apply=True)
print('SELECTED_TOASTER_PREPARED', flush=True)
