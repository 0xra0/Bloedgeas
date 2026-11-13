"""Inventory icon for the Bloedgeas DLC sword, in the style of the vanilla 64x128 weapon icons
(pommel top-right, blade running off the bottom-left, tilted ~20 deg, dark rim).

1) Blender:  blender -b KnightSword_vamp_v6.blend --python icon_render.py -- render <out_big.png>
   Cycles, orthographic top view onto the blade flats, transparent film, 4x size.
2) Python:   python3 -I icon_render.py finish <out_big.png> <icon_64x128.png>
   Downscale, then a 1 px dark rim from the dilated alpha, as the vanilla icons have.
"""
import sys

W, H = 64, 128
TILT = 22            # degrees; vanilla icons lean the pommel to the right
FRAME = (-0.60, 0.20)  # Sword_LP Y range shown: pommel cap .. upper blade (the rest runs off the icon)


def render(out):
    import math, bpy
    from mathutils import Vector
    sc = bpy.context.scene
    src = bpy.data.objects["Sword_LP"]
    for o in sc.objects:
        o.hide_render = o is not src
    lo, hi = FRAME
    mid = src.matrix_world @ Vector((0, (lo + hi) / 2, 0))
    cam_d = bpy.data.cameras.new("icon_cam"); cam_d.type = "ORTHO"
    cam_d.ortho_scale = (hi - lo) * 1.02
    cam = bpy.data.objects.new("icon_cam", cam_d); sc.collection.objects.link(cam)
    cam.location = (mid.x, mid.y, 2.0); cam.rotation_euler = (0, 0, math.radians(180 + TILT))  # roll the view: pommel up, blade down-left
    sc.camera = cam
    for name, rot, energy in (("key", (math.radians(35), math.radians(-25), 0), 4.0),
                              ("rim", (math.radians(-50), math.radians(40), 0), 2.0)):
        ld = bpy.data.lights.new(name, "SUN"); ld.energy = energy
        lo_ = bpy.data.objects.new(name, ld); lo_.rotation_euler = rot; sc.collection.objects.link(lo_)
    try:
        sc.render.engine = "CYCLES"
    except TypeError as e:
        print(e)
    sc.cycles.samples = 96; sc.cycles.device = "CPU"
    sc.render.film_transparent = True
    sc.view_settings.exposure = 1.0          # the vanilla icons are lit much brighter than the game
    sc.render.resolution_x, sc.render.resolution_y = W * 4, H * 4
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print("rendered", out)


def finish(big, out):
    from PIL import Image, ImageFilter, ImageEnhance
    im = Image.open(big).convert("RGBA").resize((W, H), Image.LANCZOS)
    im = ImageEnhance.Contrast(im).enhance(1.15).filter(ImageFilter.UnsharpMask(1, 60, 2))
    a = im.getchannel("A")
    rim = Image.new("RGBA", im.size, (8, 4, 4, 0))
    rim.putalpha(a.filter(ImageFilter.MaxFilter(3)).point(lambda v: v * 0.8))
    rim.alpha_composite(im)
    rim.save(out)
    print("icon", out, rim.size)


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
{"render": render, "finish": finish}[argv[0]](*argv[1:])
