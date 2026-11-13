"""Matching scabbard for the v6 vampire sword, in Sword_LP object space (long axis +Y, flats facing +-Z),
so the sheathed blade (y -0.226 .. 0.489) sits inside it and the langet stays visible above the locket.

Oxblood leather body following the blade profile, blackened-silver locket with fang horns and a ruby,
two bands with belt rings, silver edge strips, a fanged chape with a ruby, a silver-tooled pentagram sigil.
vpart: 0 leather, 1 silver, 2 ruby (same scheme as the sword shader).

  blender -b KnightSword_vamp_v6.blend --python scabbard.py -- build    -> KnightSword_vamp_v6_scabbard.blend
  blender -b KnightSword_vamp_v6_scabbard.blend --python scabbard.py -- bake | reshade_bake | render | w3
"""
import bpy, bmesh, math, sys
import numpy as np

S = "/mnt/ssd/ComfyUI/output/3D/KnightSword_vamp_v6_tex/scripts"
D = "/mnt/ssd/ComfyUI/output/3D/KnightSword_vamp_v6_tex"
OUT = "/mnt/ssd/ComfyUI/output/3D/KnightSword_vamp_v6_scabbard"
RES = 2048
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STAGE = argv[0] if argv else "build"

# blade profile (y, half-width, half-thickness) sampled from Sword_LP's original mesh
PY = [-0.150, -0.106, -0.026, 0.094, 0.254, 0.374, 0.414, 0.454, 0.489]
PW = [0.0217, 0.0213, 0.0206, 0.0201, 0.0201, 0.0198, 0.0149, 0.0082, 0.0015]
PT = [0.0051, 0.0051, 0.0052, 0.0053, 0.0053, 0.0053, 0.0041, 0.0025, 0.0010]
WALL = 0.0055                      # leather over a wooden core
Y_TOP, Y_END = -0.150, 0.514


def body_ab(y):
    """Outer half-width / half-thickness of the leather at y; rounds off past the blade tip."""
    a = np.interp(y, PY, PW) + WALL
    b = np.interp(y, PY, PT) + WALL
    if y > 0.489:
        t = (y - 0.489) / (Y_END - 0.489)
        k = math.sqrt(max(1 - t * t, 0.0))
        a, b = a * (0.35 + 0.65 * k), b * (0.35 + 0.65 * k)
    return a, b


def ring(bm, y, a, b, n=28, e=2.6):
    """Superellipse section (flat-ish sides, rounded edges) in the XZ plane at height y."""
    vs = []
    for k in range(n):
        t = 2 * math.pi * k / n
        c, s = math.cos(t), math.sin(t)
        vs.append(bm.verts.new((a * math.copysign(abs(c) ** (2 / e), c), y, b * math.copysign(abs(s) ** (2 / e), s))))
    return vs


def loft(name, secs, mat, cap0=True, cap1=True):
    """secs: [(y, a, b), ...] -> closed tube; recalc_face_normals settles the winding."""
    bm = bmesh.new()
    rings = [ring(bm, *s) for s in secs]
    for r0, r1 in zip(rings, rings[1:]):
        n = len(r0)
        for k in range(n):
            bm.faces.new((r0[k], r0[(k + 1) % n], r1[(k + 1) % n], r1[k]))
    for r, on in ((rings[0], cap0), (rings[-1], cap1)):
        if on:
            c = bm.verts.new(sum((v.co for v in r), r[0].co * 0) / len(r))
            for k in range(len(r)):
                bm.faces.new((r[k], r[(k + 1) % len(r)], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return G["_obj"](name, bm, mat)


def sleeve(name, y0, y1, lift=0.0013, bead=0.0024, top_slot=False):
    """Metal fitting hugging the body from y0 to y1 with a rolled bead at both ends."""
    secs = []
    if top_slot:      # open mouth: the blade slot drops into the locket
        hw, ht = PW[0] + 0.0006, PT[0] + 0.0006
        secs += [(y0 + 0.012, hw, ht), (y0, hw, ht)]
    ys = [y0, y0 + 0.002, y0 + 0.004] + list(np.linspace(y0 + 0.006, y1 - 0.006, 6)) + [y1 - 0.004, y1 - 0.002, y1]
    lifts = [bead * 0.8, bead, lift] + [lift] * 6 + [lift, bead, bead * 0.8]
    for y, l in zip(ys, lifts):
        a, b = body_ab(min(y, Y_END - 0.001))
        secs.append((y, a + l, b + l))
    return loft(name, secs, "Vamp_metal", cap0=not top_slot, cap1=True)


def torus(name, center, R, r, axis="Z", n1=20, n2=8):
    bm = bmesh.new()
    cx, cy, cz = center
    grid = []
    for i in range(n1):
        a = 2 * math.pi * i / n1
        row = []
        for j in range(n2):
            b = 2 * math.pi * j / n2
            u, w = (R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a)
            h = r * math.sin(b)
            row.append(bm.verts.new((cx + u, cy + w, cz + h) if axis == "Z" else (cx + h, cy + w, cz + u)))
        grid.append(row)
    for i in range(n1):
        for j in range(n2):
            bm.faces.new((grid[i][j], grid[(i + 1) % n1][j], grid[(i + 1) % n1][(j + 1) % n2], grid[i][(j + 1) % n2]))
    return G["_obj"](name, bm, "Vamp_metal")


def set_vpart(ob, value):
    a = ob.data.attributes.get("vpart") or ob.data.attributes.new("vpart", "FLOAT", "POINT")
    a.data.foreach_set("value", np.full(len(ob.data.vertices), value, np.float32))


def build():
    global G
    G = {}
    exec(open(f"{S}/vamp_geometry.py").read(), G)          # horn(), cabochon(), _obj()
    horn, cabochon = G["horn"], G["cabochon"]
    for ob in list(bpy.data.objects):
        if ob.name.startswith(("Scb_", "Scabbard")): bpy.data.objects.remove(ob, do_unlink=True)

    ys = sorted(set(np.round(np.concatenate([np.linspace(-0.146, 0.40, 40), np.linspace(0.40, Y_END, 16)]), 5)))
    parts = [loft("Scb_body", [(y, *body_ab(y)) for y in ys], "Scb_leather")]
    leather = parts[0]

    parts.append(sleeve("Scb_locket", Y_TOP - 0.002, -0.092, top_slot=True))
    parts.append(sleeve("Scb_band_1", -0.004, 0.010))
    parts.append(sleeve("Scb_band_2", 0.216, 0.228))
    parts.append(sleeve("Scb_chape", 0.360, Y_END))
    # belt rings hanging off the +x edge of each band
    for k, yb in enumerate((0.003, 0.222)):
        a, _ = body_ab(yb)
        parts.append(torus(f"Scb_ring_{k}", (a + 0.0085, yb, 0.0), 0.0072, 0.0016))
    # silver edge strips between the fittings
    for sx in (1, -1):
        pts = []
        for y in (-0.094, 0.05, 0.20, 0.362):
            a, _ = body_ab(y)
            pts.append((sx * (a + 0.0002), y, 0.0))
        parts.append(horn(f"Scb_edge_{'r' if sx > 0 else 'l'}", pts, 0.0017, 0.0015, sides=8, steps=40))
    # fang horns curling off the locket toward the tip, like the guard's
    for sx in (1, -1):
        a, _ = body_ab(Y_TOP)
        parts.append(horn(f"Scb_horn_{'r' if sx > 0 else 'l'}",
                          [(sx * (a + 0.001), Y_TOP + 0.004, 0.0), (sx * (a + 0.016), Y_TOP - 0.006, 0.0),
                           (sx * (a + 0.026), Y_TOP + 0.018, 0.0), (sx * (a + 0.019), Y_TOP + 0.050, 0.0)],
                          0.0048, 0.0004))
    # fang at the chape tip and two small ones flaring from its top bead
    parts.append(horn("Scb_tip_fang", [(0, Y_END - 0.006, 0), (0, Y_END + 0.008, 0), (0, Y_END + 0.022, 0),
                                        (0, Y_END + 0.036, 0)], 0.0062, 0.0004))
    for sx in (1, -1):
        a, _ = body_ab(0.362)
        parts.append(horn(f"Scb_chape_fang_{'r' if sx > 0 else 'l'}",
                          [(sx * (a + 0.001), 0.364, 0), (sx * (a + 0.008), 0.366, 0),
                           (sx * (a + 0.012), 0.376, 0), (sx * (a + 0.010), 0.392, 0)], 0.0030, 0.0003))
    # rubies on both flats: locket (large) and chape (small)
    for s in (1, -1):
        _, b = body_ab(-0.121)
        parts += cabochon(f"Scb_ruby_locket_{'f' if s > 0 else 'b'}", (0, -0.121, s * (b + 0.0012)), 0.0058, 0.0046, s)
        _, b = body_ab(0.400)
        parts += cabochon(f"Scb_ruby_chape_{'f' if s > 0 else 'b'}", (0, 0.400, s * (b + 0.0012)), 0.0034, 0.0026, s)

    for p in parts:
        set_vpart(p, 0.0 if p is leather else 2.0 if "ruby" in p.name and "bezel" not in p.name else 1.0)
        if not p.data.uv_layers: p.data.uv_layers.new(name="UVMap")
    vl = bpy.context.view_layer
    for ob in vl.objects: ob.select_set(False)
    for p in parts: p.select_set(True)
    vl.objects.active = leather
    with bpy.context.temp_override(active_object=leather, object=leather, selected_editable_objects=parts,
                                   selected_objects=parts):
        bpy.ops.object.join()
    o = leather; o.name = o.data.name = "Scabbard_LP"
    me = o.data
    me.polygons.foreach_set("material_index", np.zeros(len(me.polygons), int))
    while len(me.materials) > 1: me.materials.pop()
    for p in me.polygons: p.use_smooth = True
    with bpy.context.temp_override(active_object=o, object=o):
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.0, area_weight=0.0, correct_aspect=True,
                                 scale_to_bounds=False)
        bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.uv.average_islands_scale()
        bpy.ops.uv.pack_islands(rotate=True, margin=0.003)
        bpy.ops.object.mode_set(mode="OBJECT")
    print("scabbard", len(me.polygons), "faces")
    exec(open(f"{S}/scabbard_shader.py").read(), {})
    bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}.blend")
    print("saved", f"{OUT}.blend")


MAPS = [("scb_v6_base_color", "BAKE_col", 4, False), ("scb_v6_roughness", "BAKE_rough", 4, True),
        ("scb_v6_metallic", "BAKE_metal", 1, True), ("scb_v6_glow", "BAKE_glow", 4, True),
        ("scb_v6_normal", None, 16, True)]


def bake():
    s = bpy.context.scene
    o = bpy.data.objects["Scabbard_LP"]
    s.render.engine = "CYCLES"; s.cycles.device = "CPU"; s.render.bake.margin = 8
    vl = bpy.context.view_layer
    for ob in vl.objects: ob.select_set(False)
    o.select_set(True); vl.objects.active = o
    nt = bpy.data.materials["Scabbard_vamp_proc"].node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    for name, src, samples, nc in MAPS:
        im = bpy.data.images.get(name) or bpy.data.images.new(name, RES, RES, alpha=False)
        if nc: im.colorspace_settings.name = "Non-Color"
        im.filepath_raw = f"{D}/{name}.png"; im.file_format = "PNG"
        uv = nt.nodes.new("ShaderNodeUVMap")
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = im; nt.links.new(uv.outputs[0], t.inputs[0])
        for n in nt.nodes: n.select = False
        t.select = True; nt.nodes.active = t
        nt.links.new((nt.nodes[src] if src else bsdf).outputs[0], out.inputs[0]); s.cycles.samples = samples
        if src: bpy.ops.object.bake(type="EMIT")
        else: bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT")
        im.save()
        nt.nodes.remove(t); nt.nodes.remove(uv); nt.links.new(bsdf.outputs[0], out.inputs[0])
        print("baked", name, flush=True)

    m = bpy.data.materials.get("Scabbard_vamp_v6") or bpy.data.materials.new("Scabbard_vamp_v6")
    m.use_nodes = True; mt = m.node_tree; mt.nodes.clear()
    b = mt.nodes.new("ShaderNodeBsdfPrincipled"); mo = mt.nodes.new("ShaderNodeOutputMaterial")
    mt.links.new(b.outputs[0], mo.inputs[0])

    def tex(name):
        t = mt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images[name]; return t
    mt.links.new(tex("scb_v6_base_color").outputs[0], b.inputs["Base Color"])
    mt.links.new(tex("scb_v6_metallic").outputs[0], b.inputs["Metallic"])
    mt.links.new(tex("scb_v6_roughness").outputs[0], b.inputs["Roughness"])
    mt.links.new(tex("scb_v6_glow").outputs[0], b.inputs["Emission Strength"])
    b.inputs["Emission Color"].default_value = (1.0, 0.04, 0.02, 1.0)
    nm = mt.nodes.new("ShaderNodeNormalMap")
    mt.links.new(tex("scb_v6_normal").outputs[0], nm.inputs["Color"]); mt.links.new(nm.outputs[0], b.inputs["Normal"])
    o.data.materials[0] = m
    s.render.engine = "BLENDER_EEVEE"
    bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}.blend")
    for ob in vl.objects: ob.select_set(False)
    o.select_set(True); vl.objects.active = o
    bpy.ops.export_scene.gltf(filepath=f"{OUT}_LP.glb", export_format="GLB", use_selection=True)
    print("saved", OUT, flush=True)


def w3():
    """W3-space FBX, same transform as the sword so a sheathed pair lines up at one pivot."""
    ns = {"__name__": "w3_export_lib"}
    exec(open(f"{S}/w3_export.py").read().rsplit("\nargv", 1)[0], ns)
    src = bpy.data.objects["Scabbard_LP"]
    o = src.copy(); o.data = src.data.copy(); o.name = "w3_scabbard_vamp"
    bpy.context.scene.collection.objects.link(o)
    o.data.transform(ns["w3_matrix"]())
    ns["export_fbx"]([o], f"{ns['W3']}/w3_scabbard_vamp.fbx")


def render():
    """Sheathed pair and a close-up of the locket, at the dimmed check-render lighting."""
    import mathutils
    s = bpy.context.scene
    s.render.engine = "CYCLES"; s.cycles.device = "CPU"; s.cycles.samples = 48
    s.render.resolution_x, s.render.resolution_y = 1600, 900
    for ob in list(bpy.data.objects):
        if ob.type in ("LIGHT", "CAMERA"): bpy.data.objects.remove(ob, do_unlink=True)
    w = s.world or bpy.data.worlds.new("W"); s.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.012, 0.012, 0.014, 1)
    for name, loc, power, size in (("key", (0.35, 0.1, 0.6), 15, 0.6), ("rim", (-0.4, 0.2, -0.3), 25, 0.5),
                                   ("fill", (0.0, -0.5, 0.4), 2, 1.0)):
        ld = bpy.data.lights.new(name, "AREA"); ld.energy = power; ld.size = size
        lo = bpy.data.objects.new(name, ld); s.collection.objects.link(lo); lo.location = loc
        lo.rotation_euler = (mathutils.Vector((0, 0.05, 0)) - mathutils.Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); s.collection.objects.link(cam); s.camera = cam
    sw, sc = bpy.data.objects["Sword_LP"], bpy.data.objects["Scabbard_LP"]
    shots = [("pair", (0.0, 0.03, 0.0), 1.10, (0.0, 0.04, 0.0)), ("locket", (0.0, -0.15, 0.0), 0.30, (0.0, -0.17, 0.0)),
             ("chape", (0.0, 0.43, 0.0), 0.26, (0.0, 0.43, 0.0))]
    sw.location = (0, 0, 0); sc.location = (0.075, 0, 0)          # side by side for the first shot
    for tag, target, dist, _ in shots:
        if tag != "pair": sw.location = (10, 0, 0); sc.location = (0, 0, 0)
        tgt = mathutils.Vector(target) + (sc.location if tag == "pair" else mathutils.Vector())
        tgt.x = 0.037 if tag == "pair" else 0.0
        cam.location = tgt + mathutils.Vector((0.25 * dist, 0.0, dist))
        cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "X").to_euler()
        cam.data.lens = 50
        s.render.filepath = f"{D}/scabbard_{tag}.png"
        bpy.ops.render.render(write_still=True)
        print("render", s.render.filepath, flush=True)


def reshade_bake():
    exec(open(f"{S}/scabbard_shader.py").read(), {})
    bake()


{"build": build, "bake": bake, "reshade_bake": reshade_bake, "w3": w3, "render": render}[STAGE]()
