"""blender -b --python glb_preview.py -- OUT.png GLB [GLB ...] : textured preview of generated objects (Eevee, 3/4 view)."""
import bpy, sys, math, mathutils
args = sys.argv[sys.argv.index("--") + 1:]; out, glbs = args[0], args[1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "FLAT"; sc.display.shading.color_type = "TEXTURE"
sc.render.resolution_x, sc.render.resolution_y = int(__import__("os").environ.get("TILE", 200)) * min(len(glbs), 7), int(__import__("os").environ.get("TILE", 200)) * ((len(glbs) + 6) // 7)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[1].default_value = 1.5
for i, g in enumerate(glbs):
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=g)
    objs = [o for o in set(bpy.data.objects) - before if o.type == "MESH"]
    pts = [o.matrix_world @ mathutils.Vector(c) for o in objs for c in o.bound_box]
    lo = mathutils.Vector([min(p[k] for p in pts) for k in range(3)]); hi = mathutils.Vector([max(p[k] for p in pts) for k in range(3)])
    s = 1.0 / max(hi - lo)
    for o in set(bpy.data.objects) - before:
        if o.parent is None:
            o.matrix_world = mathutils.Matrix.Translation(((i % 7) * 1.2, 0, -(i // 7) * 1.2)) @ mathutils.Matrix.Scale(s, 4) @ mathutils.Matrix.Translation(-(lo + hi) / 2) @ o.matrix_world
cam = bpy.data.cameras.new("c"); cam.type = "ORTHO"; cam.ortho_scale = 1.2 * min(len(glbs), 7)
co = bpy.data.objects.new("c", cam); sc.collection.objects.link(co); sc.camera = co
rows = (len(glbs) + 6) // 7; cx = (min(len(glbs), 7) - 1) * 0.6; co.location = (cx, -6, -(rows - 1) * 0.6 + 1.5); co.rotation_euler = (math.radians(76), 0, 0)
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
