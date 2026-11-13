"""v6 vampire build, in two stages so the slow bake can run headless (the GUI crashed mid-bake on v5).

build (GUI via MCP, file holding v5's Sword_LP):  exec with STAGE="build"  -> add-on parts, join, UV, shader, save .blend
bake  (headless):  blender -b KnightSword_vamp_v6.blend --python vamp_pipeline.py -- bake | reshade_bake
"""
import bpy, bmesh, sys
import numpy as np

S = "/mnt/ssd/ComfyUI/output/3D/KnightSword_vamp_v6_tex/scripts"
D = "/mnt/ssd/ComfyUI/output/3D/KnightSword_vamp_v6_tex"
OUT = "/mnt/ssd/ComfyUI/output/3D/KnightSword_vamp_v6"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STAGE = globals().get("STAGE") or (argv[0] if argv else "build")
RES = 2048
MAPS = [("vamp_v6_base_color", False), ("vamp_v6_roughness", True), ("vamp_v6_metallic", True),
        ("vamp_v6_glow", True), ("vamp_v6_normal", True)]


def set_vpart(ob, value):
    a = ob.data.attributes.get("vpart") or ob.data.attributes.new("vpart", "FLOAT", "POINT")
    a.data.foreach_set("value", np.full(len(ob.data.vertices), value, np.float32))


def build():
    o = bpy.data.objects["Sword_LP"]
    ns = {}
    exec(open(f"{S}/vamp_geometry.py").read(), ns)
    parts = ns["build"]()
    set_vpart(o, 0.0)
    for p in parts:
        set_vpart(p, 2.0 if "ruby" in p.name and "bezel" not in p.name else 1.0)
        p.data.uv_layers.new(name="UVMap")
    nold = len(o.data.polygons)
    vl = bpy.context.view_layer
    for ob in vl.objects: ob.select_set(False)
    for p in parts: p.select_set(True)
    o.select_set(True); vl.objects.active = o
    with bpy.context.temp_override(active_object=o, object=o, selected_editable_objects=parts + [o],
                                   selected_objects=parts + [o]):
        bpy.ops.object.join()
    me = o.data
    me.polygons.foreach_set("material_index", np.zeros(len(me.polygons), int))
    while len(me.materials) > 1: me.materials.pop()
    print("joined", len(me.polygons), "faces, new from", nold)

    # UV: Smart UV only the new faces, then equalise texel density and repack the whole atlas
    bm = bmesh.new(); bm.from_mesh(me)
    for f in bm.faces: f.select = f.index >= nold
    bm.to_mesh(me); bm.free()
    with bpy.context.temp_override(active_object=o, object=o):
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_mode(type="FACE")
        bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.0, area_weight=0.0, correct_aspect=True,
                                 scale_to_bounds=False)
        bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.uv.average_islands_scale()
        bpy.ops.uv.pack_islands(rotate=True, margin=0.003)
        bpy.ops.object.mode_set(mode="OBJECT")

    exec(open(f"{S}/vamp_shader_v6.py").read(), {})
    bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}.blend")
    print("saved", f"{OUT}.blend")


def bake():
    s = bpy.context.scene
    o = bpy.data.objects["Sword_LP"]
    s.render.engine = "CYCLES"; s.cycles.device = "CPU"; s.render.bake.margin = 8
    for nm, nc in MAPS:
        im = bpy.data.images.get(nm) or bpy.data.images.new(nm, RES, RES, alpha=False)
        if nc: im.colorspace_settings.name = "Non-Color"
        im.filepath_raw = f"{D}/{nm}.png"; im.file_format = "PNG"
    vl = bpy.context.view_layer
    for ob in vl.objects: ob.select_set(False)
    o.select_set(True); vl.objects.active = o
    nt = bpy.data.materials["Sword_vamp_proc"].node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    jobs = [("vamp_v6_metallic", "BAKE_metal", 1), ("vamp_v6_base_color", "BAKE_col", 4),
            ("vamp_v6_roughness", "BAKE_rough", 4), ("vamp_v6_glow", "BAKE_glow", 4), ("vamp_v6_normal", None, 16)]
    for name, src, samples in jobs:
        uv = nt.nodes.new("ShaderNodeUVMap")
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images[name]; nt.links.new(uv.outputs[0], t.inputs[0])
        for n in nt.nodes: n.select = False
        t.select = True; nt.nodes.active = t
        nt.links.new((nt.nodes[src] if src else bsdf).outputs[0], out.inputs[0]); s.cycles.samples = samples
        if src: bpy.ops.object.bake(type="EMIT")
        else: bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT")
        t.image.save()
        nt.nodes.remove(t); nt.nodes.remove(uv); nt.links.new(bsdf.outputs[0], out.inputs[0])
        print("baked", name, flush=True)

    # final image material: what the GLB / FBX carries
    m = bpy.data.materials.get("Sword_vamp_v6") or bpy.data.materials.new("Sword_vamp_v6")
    m.use_nodes = True; mt = m.node_tree; mt.nodes.clear()
    b = mt.nodes.new("ShaderNodeBsdfPrincipled"); mo = mt.nodes.new("ShaderNodeOutputMaterial")
    mt.links.new(b.outputs[0], mo.inputs[0])

    def tex(name, y):
        t = mt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images[name]; t.location = (-500, y); return t
    mt.links.new(tex("vamp_v6_base_color", 300).outputs[0], b.inputs["Base Color"])
    mt.links.new(tex("vamp_v6_metallic", 0).outputs[0], b.inputs["Metallic"])
    mt.links.new(tex("vamp_v6_roughness", -300).outputs[0], b.inputs["Roughness"])
    mt.links.new(tex("vamp_v6_glow", -900).outputs[0], b.inputs["Emission Strength"])
    b.inputs["Emission Color"].default_value = (1.0, 0.04, 0.02, 1.0)
    nm_ = mt.nodes.new("ShaderNodeNormalMap"); nm_.location = (-200, -600)
    mt.links.new(tex("vamp_v6_normal", -600).outputs[0], nm_.inputs["Color"])
    mt.links.new(nm_.outputs[0], b.inputs["Normal"])
    o.data.materials[0] = m
    s.render.engine = "BLENDER_EEVEE"
    bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}.blend")
    for ob in vl.objects: ob.select_set(False)
    o.select_set(True); vl.objects.active = o
    bpy.ops.export_scene.gltf(filepath=f"{OUT}_LP.glb", export_format="GLB", use_selection=True)
    print("saved", OUT, flush=True)


def reshade_bake():
    """Rebuild only the procedural material (geometry/UVs kept), then bake."""
    exec(open(f"{S}/vamp_shader_v6.py").read(), {})
    bake()


{"build": build, "bake": bake, "reshade_bake": reshade_bake}[STAGE]()
