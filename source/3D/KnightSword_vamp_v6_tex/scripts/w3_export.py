"""REDkit hand-off for the v6 sword.

1) Blender (headless):  blender -b KnightSword_vamp_v6.blend --python w3_export.py -- fbx
   FBX copy with the blade along +Z and the pivot at the centre of the grip (where the hand holds it).
2) System python:       python3 -I w3_export.py textures [vamp_v6 w3_sword_vamp | scb_v6 w3_scabbard_vamp]
   Witcher 3 texture sets from the metal/rough bake:
     *_d.png       diffuse, metals darkened (spec workflow) -> 'Diffuse' (import as TCM_DXTNoAlpha)
     *_albedo.png  plain metal/rough albedo, for reference
     *_n.png       normal RGB, GLOSS in alpha                -> 'Normal'  (import as TCM_NormalsGloss)
                   (+ *_n_dx.png with green flipped)
     *_s.png       specular colour RGB, glossiness alpha     -> pbr_spec 'SpecularTexture'
     *_e.png       emissive mask (runes, rubies)             -> optional glow
Checked against the retail dwarven_sword_lv1: blade +Z, flats facing Y, pivot mid-grip, guard ~+0.09,
1.28 m long; its diffuse averages 0.15 and its normal xbm is TCM_NormalsGloss (alpha = gloss).
"""
import sys

D = "/mnt/ssd/ComfyUI/output/3D/KnightSword_vamp_v6_tex"
W3 = f"{D}/w3"
GRIP_Y = -0.328          # middle of the grip (-0.397 .. -0.259)
SCALE = 1.25             # 1.01 m -> 1.26 m, the length of retail witcher-sized swords


def w3_matrix():
    import math
    from mathutils import Matrix
    # pivot to grip centre, then blade +Y -> +Z, flats facing Y, then retail size
    return (Matrix.Scale(SCALE, 4) @ Matrix.Rotation(math.radians(90), 4, "X")
            @ Matrix.Translation((0, -GRIP_Y, 0)))


def w3_axes(path):
    """Stamp REDkit's own axis header (FrontAxisSign +1, CoordAxisSign -1, as in a wcc_lite export) on a binary FBX.
    wcc_lite import converts from the header's axis system: Blender's header for axis_forward Y turns the mesh
    180 deg about Z (a back scabbard lands on the chest), axis_forward -Y moves that turn onto the root nodes instead.
    So export with axis_forward Y (raw data stay in W3 space, no node rotation) and patch the two signs here."""
    import struct
    data = bytearray(open(path, "rb").read())
    for name, val in ((b"FrontAxisSign", 1), (b"CoordAxisSign", -1)):
        o = data.index(b"S" + struct.pack("<I", len(name)) + name) + 5 + len(name)
        for _ in range(3):                                   # skip the 'int', 'Integer', '' strings of the P record
            assert data[o:o + 1] == b"S"; o += 5 + struct.unpack_from("<I", data, o + 1)[0]
        assert data[o:o + 1] == b"I"
        struct.pack_into("<i", data, o + 1, val)
    open(path, "wb").write(data)


def export_fbx(objs, path):
    import bpy, os
    vl = bpy.context.view_layer
    for ob in vl.objects: ob.select_set(False)
    for o in objs: o.select_set(True)
    vl.objects.active = objs[0]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, axis_forward="Y", axis_up="Z",
                             apply_unit_scale=True, global_scale=1.0, mesh_smooth_type="FACE",
                             use_tspace=True, path_mode="STRIP", bake_space_transform=False)
    w3_axes(path)
    print("fbx", path, [(o.name, len(o.data.polygons)) for o in objs])


def fbx():
    import bpy
    src = bpy.data.objects["Sword_LP"]
    o = src.copy(); o.data = src.data.copy(); o.name = "w3_sword_vamp"
    bpy.context.scene.collection.objects.link(o)
    o.data.transform(w3_matrix())
    export_fbx([o], f"{W3}/w3_sword_vamp.fbx")


def lods():
    """LOD1/LOD2 (gltfpack via 3D Gen Studio, in lods/) and convex collision hulls, as W3-space FBXs."""
    import bpy, bmesh
    import numpy as np
    for lv in (1, 2):
        bpy.ops.import_scene.gltf(filepath=f"{D}/lods/KnightSword vamp v6 LP_LOD{lv}.glb")
        o = bpy.context.selected_objects[0]
        o.name = f"w3_sword_vamp_lod{lv}"
        o.data.transform(o.matrix_world); o.matrix_world.identity()
        o.data.transform(w3_matrix())
        export_fbx([o], f"{W3}/w3_sword_vamp_lod{lv}.fbx")

    # collision: one convex hull per Y band (pommel+fangs / grip / guard+horns / blade in 3 pieces)
    src = bpy.data.objects["Sword_LP"]
    co = np.array([v.co[:] for v in src.data.vertices])
    bands = [(-1, -0.3975), (-0.3975, -0.259), (-0.259, -0.15), (-0.15, 0.05), (0.05, 0.25), (0.25, 1)]
    hulls = []
    for i, (a, b) in enumerate(bands):
        pts = co[(co[:, 1] >= a) & (co[:, 1] < b)]
        bm = bmesh.new()
        for p in pts: bm.verts.new(p)
        bmesh.ops.convex_hull(bm, input=bm.verts[:])
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        me = bpy.data.meshes.new(f"w3_sword_vamp_col{i}"); bm.to_mesh(me); bm.free()
        me.transform(w3_matrix())
        h = bpy.data.objects.new(me.name, me); bpy.context.scene.collection.objects.link(h)
        # physics wants few hull vertices: decimate, then re-hull so it stays convex
        if len(me.polygons) > 60:
            dm = h.modifiers.new("dec", "DECIMATE"); dm.ratio = 60 / len(me.polygons)
            me2 = bpy.data.meshes.new_from_object(h.evaluated_get(bpy.context.evaluated_depsgraph_get()))
            h.modifiers.clear()
            bm = bmesh.new(); bm.from_mesh(me2)
            bmesh.ops.convex_hull(bm, input=bm.verts[:])
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
            bm.to_mesh(me); bm.free()
        hulls.append(h)
    export_fbx(hulls, f"{W3}/w3_sword_vamp_collision.fbx")


def lodfbx():
    """One FBX with all LODs as Mesh_lod0..2 (the node names wcc_lite export uses), sharing Sword_LP's material."""
    import bpy
    src = bpy.data.objects["Sword_LP"]
    o = src.copy(); o.data = src.data.copy(); o.name = "Mesh_lod0"
    bpy.context.scene.collection.objects.link(o)
    o.data.transform(w3_matrix())
    objs = [o]
    for lv in (1, 2):
        bpy.ops.import_scene.gltf(filepath=f"{D}/lods/KnightSword vamp v6 LP_LOD{lv}.glb")
        l = bpy.context.selected_objects[0]
        l.name = f"Mesh_lod{lv}"
        l.data.transform(l.matrix_world); l.matrix_world.identity()
        l.data.transform(w3_matrix())
        l.data.materials.clear(); l.data.materials.append(src.data.materials[0])
        objs.append(l)
    export_fbx(objs, f"{W3}/w3_sword_vamp_lods.fbx")


def textures(src="vamp_v6", dst="w3_sword_vamp"):
    """src: bake prefix in D (vamp_v6 sword, scb_v6 scabbard); dst: W3 file prefix."""
    import os
    import numpy as np
    from PIL import Image
    os.makedirs(W3, exist_ok=True)
    ld = lambda n: np.asarray(Image.open(f"{D}/{src}_{n}.png").convert("RGB"), np.float32) / 255.0
    col, rough, metal, nrm, glow = ld("base_color"), ld("roughness")[..., 0], ld("metallic")[..., 0], ld("normal"), ld("glow")[..., 0]
    srgb2lin = lambda c: np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    lin2srgb = lambda c: np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(np.clip(c, 0, 1), 1 / 2.4) - 0.055)
    lin = srgb2lin(col)
    m = metal[..., None]
    diffuse = lin2srgb(lin * (1 - m) + lin * m * 0.25)        # metals keep a dark tint of their colour
    spec = lin2srgb(0.04 * (1 - m) + lin * m)                  # F0
    u8 = lambda a: (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(u8(col)).save(f"{W3}/{dst}_albedo.png")
    Image.fromarray(u8(diffuse)).save(f"{W3}/{dst}_d.png")
    gloss = 1 - rough
    Image.fromarray(u8(np.dstack([nrm, gloss]))).save(f"{W3}/{dst}_n.png")
    dx = nrm.copy(); dx[..., 1] = 1 - dx[..., 1]
    Image.fromarray(u8(np.dstack([dx, gloss]))).save(f"{W3}/{dst}_n_dx.png")
    Image.fromarray(u8(np.dstack([spec, 1 - rough]))).save(f"{W3}/{dst}_s.png")
    Image.fromarray(u8(glow)).save(f"{W3}/{dst}_e.png")
    print("textures ->", W3, sorted(os.listdir(W3)))


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
{"fbx": fbx, "lods": lods, "lodfbx": lodfbx, "textures": textures}[argv[0]](*argv[1:])
