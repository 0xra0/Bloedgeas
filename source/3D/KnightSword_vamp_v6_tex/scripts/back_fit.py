"""Fit the sheathed v6 pair onto Geralt's back, where his vanilla steel scabbard hangs.

    blender -b KnightSword_vamp_v6_scabbard.blend --python back_fit.py -- check  KnightSword_vamp_v6_tex/geralt_ref.blend
    blender -b KnightSword_vamp_v6_scabbard.blend --python back_fit.py -- skin   KnightSword_vamp_v6_tex/geralt_ref.blend
    blender -b --python back_fit.py -- verify w3/w3_scabbard_vamp_skinned.fbx <w3ref/.../scabbard_steel_1_01.w2mesh>
      hangs Sword_LP + Scabbard_LP on steel_sword_back_slot as the game would (grip pivot on the slot bone),
      prints clearance to Geralt's body/head/ponytail next to the vanilla scabbard's, renders 3 views.
Geralt's parts and the vanilla back scabbards come from the game bundles (romance mod tools/unbundle.py),
imported with witcher3_tools; the character faces +Y, back is -Y, +X is his right.
"""
import sys, math
import bpy, numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

D = "/mnt/ssd/ComfyUI/output/3D/KnightSword_vamp_v6_tex"
Y_TOP = -0.150            # scabbard mouth in Sword_LP space (scabbard.py)
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GERALT_PARTS = ("t_01_mg__body_hires", "h_00_mg__geralt", "c_02_mg__halftail_pony", "l_01_mg__body")


def append_geralt(path):
    with bpy.data.libraries.load(path) as (src, dst):
        dst.objects = [n for n in src.objects]
    for o in dst.objects:
        bpy.context.scene.collection.objects.link(o)


# steel_sword_back_slot = bone steel_sword_back of geralt_player's scabbards_skeleton (scabbards_crossbow.w2rig),
# in character space; rig root solved from the 3+3 scabbard bones of the vanilla steel/silver meshes (0.6 mm residual).
STEEL_SLOT = Matrix(((-0.877, -0.251, -0.409, 0.1754),
                     (-0.275, 0.961, -0.001, -0.2357),
                     (0.393, 0.111, -0.913, 1.7368),
                     (0, 0, 0, 1)))


def w3_lib():
    ns = {"__name__": "w3_export_lib"}
    exec(open(f"{D}/scripts/w3_export.py").read().rsplit("\nargv", 1)[0], ns)
    return ns


def lp_to_back():
    """Sword_LP space -> character space, the way the game hangs the W3 sword (pivot mid-grip) on the slot."""
    return STEEL_SLOT @ w3_lib()["w3_matrix"]()


def clearance(objs, body):
    """Signed distance of every vertex to the body surface (negative = inside), per object."""
    out = {}
    for o in objs:
        P = [o.matrix_world @ v.co for v in o.data.vertices]
        best = []
        for p in P:
            d = 1e9
            for name, tree in body.items():
                hit, nrm, _, dist = tree.find_nearest(p)
                if hit is None: continue
                s = dist if (p - hit).dot(nrm) >= 0 else -dist
                if abs(s) < abs(d): d = s
            best.append(d)
        out[o.name] = np.array(best)
    return out


def body_trees():
    trees = {}
    dg = bpy.context.evaluated_depsgraph_get()
    for o in bpy.data.objects:
        if o.type == "MESH" and any(o.name.startswith(p) for p in GERALT_PARTS):
            me = o.evaluated_get(dg).to_mesh()
            trees[o.name] = BVHTree.FromPolygons([o.matrix_world @ v.co for v in me.vertices], [f.vertices[:] for f in me.polygons])
    return trees


def clay(name, rgb, rough=0.6):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    return m


def render_views():
    s = bpy.context.scene
    s.render.engine = "CYCLES"; s.cycles.device = "CPU"; s.cycles.samples = 32
    s.render.resolution_x, s.render.resolution_y = 1100, 1300
    for ob in list(bpy.data.objects):
        if ob.type in ("LIGHT", "CAMERA"): bpy.data.objects.remove(ob, do_unlink=True)
    w = s.world or bpy.data.worlds.new("W"); s.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.35, 0.38, 0.42, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); s.collection.objects.link(sun)
    sun.data.energy = 3.5; sun.rotation_euler = (math.radians(50), 0, math.radians(200))
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); s.collection.objects.link(cam); s.camera = cam
    views = [("back", (0.05, -2.6, 1.35), (0.02, -0.2, 1.25), 50),
             ("shoulder", (0.75, -1.05, 1.95), (0.12, -0.2, 1.62), 50),
             ("side", (2.3, -0.25, 1.35), (0.0, -0.2, 1.25), 50)]
    for tag, loc, tgt, lens in views:
        cam.location = loc; cam.data.lens = lens
        cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        s.render.filepath = f"{D}/back_fit_{tag}.png"
        bpy.ops.render.render(write_still=True)
        print("render", s.render.filepath, flush=True)


def check(geralt_blend):
    append_geralt(geralt_blend)
    steel = bpy.data.objects["scabbard_steel_1_01_lod0"]
    M = lp_to_back()
    sw, sc = bpy.data.objects["Sword_LP"], bpy.data.objects["Scabbard_LP"]
    for o in (sw, sc): o.matrix_world = M
    print("our mouth", np.round(M @ Vector((0, Y_TOP, 0)), 3), "our tip", np.round(M @ Vector((0, 0.55, 0)), 3))

    trees = body_trees()
    ref = clearance([steel, bpy.data.objects["scabbard_silver_1_01_lod0"]], trees)
    ours = clearance([sw, sc], trees)
    for k, v in {**ref, **ours}.items():
        print(f"clear {k:28s} min {v.min():+.3f} m  inside {int((v < 0).sum())}/{len(v)}")
    # where the closest / penetrating vertices are, in LP Y (scabbard mouth -0.150, guard -0.26, pommel -0.52)
    for o in (sw, sc):
        v = ours[o.name]; ly = np.array([p.co.y for p in o.data.vertices])
        for a, b, tag in ((-1, -0.40, "pommel"), (-0.40, -0.259, "grip"), (-0.259, -0.15, "guard"),
                          (-0.15, -0.09, "locket"), (-0.09, 1, "blade/body")):
            m = (ly >= a) & (ly < b)
            if m.any(): print(f"  {o.name:12s} {tag:10s} min {v[m].min():+.3f}  inside {int((v[m] < 0).sum())}")

    skin = clay("geralt_clay", (0.55, 0.45, 0.40)); hair = clay("hair_clay", (0.75, 0.75, 0.72))
    leather = clay("vanilla_scb", (0.20, 0.12, 0.07), 0.5)
    for o in bpy.data.objects:
        if o.type != "MESH" or o in (sw, sc): continue
        o.data.materials.clear()
        o.data.materials.append(hair if o.name.startswith("c_02") else leather if "scabbard" in o.name else skin)
    steel.hide_render = True                        # ours takes the steel slot; vanilla silver stays as reference
    render_views()
    bpy.ops.wm.save_as_mainfile(filepath=f"{D}/back_fit.blend")


BONES = ("steel_sword_scabbard_1", "steel_sword_scabbard_2", "steel_sword_scabbard_3")


def vanilla_frames(arm):
    """True W3 bind frames of the scabbard bones; witcher3_tools shows them rolled by 90 deg (rot90 rig setting)."""
    rot90 = Matrix.Rotation(math.radians(90), 4, "Z")
    return {b.name: arm.matrix_world @ b.matrix_local @ rot90 for b in arm.data.bones}


def weight_profile(o, h1, ax, step=0.02):
    """Mean weight per bone along the scabbard axis (distance s from bone 1), as (s centres, n x 3 table)."""
    s = np.array([(np.array(o.matrix_world @ v.co) - h1) @ ax for v in o.data.vertices])
    gi = {g.index: BONES.index(g.name) for g in o.vertex_groups}
    W = np.zeros((len(s), 3))
    for i, v in enumerate(o.data.vertices):
        for g in v.groups: W[i, gi[g.group]] = g.weight
    cs, prof = [], []
    for a in np.arange(s.min(), s.max() + step, step):
        m = (s >= a) & (s < a + step)
        if m.any(): cs.append(s[m].mean()); prof.append(W[m].mean(0))
    return np.array(cs), np.array(prof)


def skin(geralt_blend):
    """Skinned scabbard in character space on the vanilla steel scabbard's 3 bones -> w3_scabbard_vamp_skinned.fbx."""
    append_geralt(geralt_blend)
    van, varm = bpy.data.objects["scabbard_steel_1_01_lod0"], bpy.data.objects["scabbard_steel_1_01_ARM"]
    F = vanilla_frames(varm)
    h1 = np.array(F[BONES[0]].translation); ax = np.array(F[BONES[2]].translation) - h1; ax /= np.linalg.norm(ax)
    cs, prof = weight_profile(van, h1, ax)

    sc = bpy.context.scene; vl = bpy.context.view_layer
    # the armature object is exported as a bone too; name it after the scabbard rig's root so it maps onto it
    arm = bpy.data.objects.new("Root", bpy.data.armatures.new("w3_scabbard_vamp_rig"))
    sc.collection.objects.link(arm)
    for ob in vl.objects: ob.select_set(False)
    arm.select_set(True); vl.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for n in BONES:
        eb = arm.data.edit_bones.new(n); eb.head = (0, 0, 0); eb.tail = (0, 0.05, 0); eb.matrix = F[n]
    bpy.ops.object.mode_set(mode="OBJECT")
    err = max(abs(a - b) for n in BONES for ra, rb in zip(arm.data.bones[n].matrix_local, F[n]) for a, b in zip(ra, rb))
    print("bone frame error", round(err, 6))

    o = bpy.data.objects.new("w3_scabbard_vamp", bpy.data.objects["Scabbard_LP"].data.copy())
    sc.collection.objects.link(o)
    o.data.transform(lp_to_back())
    P = np.array([v.co[:] for v in o.data.vertices]); s = (P - h1) @ ax
    W = np.stack([np.interp(s, cs, prof[:, j]) for j in range(3)], 1)   # np.interp holds the end values
    W[W < 0.01] = 0; W /= W.sum(1, keepdims=True)
    for j, n in enumerate(BONES):
        g = o.vertex_groups.new(name=n)
        for i in np.nonzero(W[:, j])[0]: g.add([int(i)], float(W[i, j]), "REPLACE")
    o.parent = arm; o.modifiers.new("Armature", "ARMATURE").object = arm
    print("s range %.3f..%.3f" % (s.min(), s.max()), "verts per dominant bone", np.bincount(W.argmax(1), minlength=3))

    for ob in vl.objects: ob.select_set(False)
    for ob in (arm, o): ob.select_set(True)
    vl.objects.active = arm
    path = f"{D}/w3/w3_scabbard_vamp_skinned.fbx"
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"ARMATURE", "MESH"},
                             axis_forward="Y", axis_up="Z", apply_unit_scale=True, global_scale=1.0,
                             mesh_smooth_type="FACE", use_tspace=True, path_mode="STRIP", bake_space_transform=False,
                             add_leaf_bones=False, use_armature_deform_only=True, bake_anim=False,
                             primary_bone_axis="Y", secondary_bone_axis="X")
    w3_lib()["w3_axes"](path)
    print("fbx", path)
    bpy.ops.wm.save_as_mainfile(filepath=f"{D}/back_fit_skinned.blend")


def verify(fbx_path, vanilla_w2mesh):
    """Re-import the skinned FBX: bone frames vs the vanilla bind, rest bounds, influences, and a bend test."""
    import importlib
    for ob in list(bpy.data.objects): bpy.data.objects.remove(ob)
    # read the raw W3-space data: the REDkit axis header (w3_axes) would make Blender turn it 180 deg
    bpy.ops.import_scene.fbx(filepath=fbx_path, automatic_bone_orientation=False,
                             primary_bone_axis="Y", secondary_bone_axis="X",
                             use_manual_orientation=True, axis_forward="Y", axis_up="Z")
    arm = next(ob for ob in bpy.data.objects if ob.type == "ARMATURE")
    me = next(ob for ob in bpy.data.objects if ob.type == "MESH")
    print("bones", [b.name for b in arm.data.bones], "groups", [g.name for g in me.vertex_groups])
    im = importlib.import_module("bl_ext.user_default.witcher3_tools.importers.import_mesh")
    im.import_mesh(vanilla_w2mesh, do_import_mats=False, do_import_armature=True)
    F = vanilla_frames(bpy.data.objects["scabbard_steel_1_01_ARM"])
    for n in BONES:
        A = arm.matrix_world @ arm.data.bones[n].matrix_local
        print(f"  {n}: pos err {(A.translation - F[n].translation).length * 1000:.2f} mm, rot err "
              f"{math.degrees(A.to_quaternion().rotation_difference(F[n].to_quaternion()).angle):.3f} deg")
    P = np.array([me.matrix_world @ v.co for v in me.data.vertices])
    print("rest bounds", P.min(0).round(3), P.max(0).round(3),
          "max influences", max(len(v.groups) for v in me.data.vertices))
    # bend: swing the tip bone 15 deg; the upper half must stay put
    pb = arm.pose.bones[BONES[2]]; pb.rotation_mode = "XYZ"; pb.rotation_euler = (0, 0, math.radians(15))
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    Q = np.array([me.matrix_world @ v.co for v in me.evaluated_get(dg).to_mesh().vertices])
    moved = np.linalg.norm(Q - P, axis=1); top = P[:, 2] > 1.35
    print(f"bend test: upper part max move {moved[top].max() * 1000:.1f} mm, tip max move {moved.max() * 1000:.1f} mm")


{"check": check, "skin": skin, "verify": verify}[argv[0]](*argv[1:])
