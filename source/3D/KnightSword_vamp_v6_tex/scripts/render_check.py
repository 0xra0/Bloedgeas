"""Cycles check renders of the baked v6 material: full sword and hilt close-up, dark studio with a cold rim + warm key."""
import bpy, math, sys
from mathutils import Vector
OUTD = sys.argv[sys.argv.index("--") + 1]
s = bpy.context.scene
for ob in [o for o in s.objects if o.type in ("LIGHT", "CAMERA")]: bpy.data.objects.remove(ob, do_unlink=True)
s.render.engine = "CYCLES"; s.cycles.device = "CPU"; s.cycles.samples = 48; s.cycles.use_denoising = True
s.render.resolution_x, s.render.resolution_y = 1600, 900
w = s.world or bpy.data.worlds.new("w"); s.world = w; w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND"); bg.inputs[0].default_value = (0.012, 0.010, 0.012, 1); bg.inputs[1].default_value = 1
def light(name, loc, power, col, size):
    d = bpy.data.lights.new(name, "AREA"); d.energy = power; d.color = col; d.size = size
    o = bpy.data.objects.new(name, d); s.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
light("key", (0.6, -0.5, 0.9), 15, (1.0, 0.85, 0.75), 0.6)
light("rim", (-0.7, 0.6, 0.4), 25, (0.6, 0.7, 1.0), 0.4)
light("fill", (0.0, -0.2, -0.9), 2, (0.9, 0.85, 0.85), 1.0)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); s.collection.objects.link(cam); s.camera = cam
for name, loc, tgt, lens in (("full", (0.0, 0.0, 1.9), None, 50), ("hilt", (0.16, -0.48, 0.30), (0, -0.33, 0), 50)):
    cam.location = loc; cam.data.lens = lens
    cam.rotation_euler = (0, 0, math.pi / 2) if tgt is None else \
        (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()      # full: top-down, blade horizontal
    s.render.filepath = f"{OUTD}/{name}.png"; bpy.ops.render.render(write_still=True)
    print("render", name, flush=True)
