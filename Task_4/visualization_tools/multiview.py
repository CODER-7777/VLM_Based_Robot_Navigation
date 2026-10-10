"""blender -b --python multiview.py -- OUT.png GLB [GLB ...] : one row per GLB, 4 azimuths (0,90,180,270) + top, studio light."""
import bpy, sys, math, mathutils
args = sys.argv[sys.argv.index("--") + 1:]; out, glbs = args[0], args[1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "SINGLE"
sc.display.shading.single_color = (0.7, 0.7, 0.7); sc.display.shading.show_cavity = True
T = 300; VIEWS = [(0, 10), (90, 10), (180, 10), (270, 10), (45, 70)]
sc.render.resolution_x, sc.render.resolution_y = T * len(VIEWS), T * len(glbs)
cam = bpy.data.cameras.new("c"); cam.type = "ORTHO"; co = bpy.data.objects.new("c", cam); sc.collection.objects.link(co); sc.camera = co
import numpy as np, os
tiles = []
for i, g in enumerate(glbs):
    for o in list(bpy.data.objects):
        if o.type != "CAMERA": bpy.data.objects.remove(o)
    bpy.ops.import_scene.gltf(filepath=g)
    objs = [o for o in bpy.data.objects if o.type == "MESH"]
    pts = [o.matrix_world @ mathutils.Vector(c) for o in objs for c in o.bound_box]
    lo = mathutils.Vector([min(p[k] for p in pts) for k in range(3)]); hi = mathutils.Vector([max(p[k] for p in pts) for k in range(3)])
    c = (lo + hi) / 2; r = max(hi - lo); cam.ortho_scale = 1.15 * r; cam.clip_start = 0.01 * r; cam.clip_end = 20 * r
    for j, (az, el) in enumerate(VIEWS):
        a, e = math.radians(az), math.radians(el)
        d = mathutils.Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        co.location = c + 5 * r * d; co.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        sc.render.resolution_x = sc.render.resolution_y = T; p = "/tmp/_mv_%d_%d.png" % (i, j); sc.render.filepath = p
        bpy.ops.render.render(write_still=True); tiles.append((i, j, p))
# stitch
img = bpy.data.images.new("o", T * len(VIEWS), T * len(glbs)); px = np.zeros((T * len(glbs), T * len(VIEWS), 4), np.float32)
for i, j, p in tiles:
    im = bpy.data.images.load(p); a = np.array(im.pixels[:], np.float32).reshape(T, T, 4)
    px[(len(glbs) - 1 - i) * T:(len(glbs) - i) * T, j * T:(j + 1) * T] = a; bpy.data.images.remove(im); os.remove(p)
img.pixels = px.ravel(); img.filepath_raw = out; img.file_format = "PNG"; img.save(); print("MV", out)
