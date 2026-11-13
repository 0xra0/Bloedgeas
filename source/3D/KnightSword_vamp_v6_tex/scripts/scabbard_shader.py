"""Procedural material 'Scabbard_vamp_proc' for Scabbard_LP (object coords, long axis +Y, flats facing +-Z).
Same palette as the sword (vamp_shader_v6.py): blackened silver fittings, rubies; plus oxblood leather with
grain, saddle stitching along both edges and a silver-tooled pentagram sigil on each flat between the bands.
vpart: 0 leather, 1 silver, 2 ruby.
"""
import bpy, math

TEX6 = "/mnt/ssd/ComfyUI/output/3D/KnightSword_vamp_v6_tex"

mat = bpy.data.materials.get("Scabbard_vamp_proc") or bpy.data.materials.new("Scabbard_vamp_proc")
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()
N, L = nt.nodes, nt.links
_x = [0]


def node(t, **kw):
    n = N.new(t)
    n.location = (_x[0] * 40 % 4000, -(_x[0] // 100) * 200)
    _x[0] += 1
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def sock(v):
    return v if isinstance(v, bpy.types.NodeSocket) else None


def math_(op, a, b=0.0, c=0.0, clamp=False):
    n = node("ShaderNodeMath", operation=op, use_clamp=clamp)
    for i, v in enumerate((a, b, c)):
        s = sock(v)
        if s is not None:
            L.new(s, n.inputs[i])
        else:
            n.inputs[i].default_value = v
    return n.outputs[0]


def mix(fac, a, b):  # float lerp
    return math_("ADD", math_("MULTIPLY", math_("SUBTRACT", 1.0, fac), a), math_("MULTIPLY", fac, b))


def cmix(fac, a, b):  # colour lerp
    n = node("ShaderNodeMix", data_type="RGBA")
    for s, v in ((0, fac), (6, a), (7, b)):
        if sock(v) is not None:
            L.new(v, n.inputs[s])
        else:
            n.inputs[s].default_value = v
    return n.outputs[2]


def rgb(r, g, b):
    return (r, g, b, 1.0)


def step(edge0, edge1, x):
    n = node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
    L.new(x, n.inputs[0])
    n.inputs[1].default_value, n.inputs[2].default_value = edge0, edge1
    return n.outputs[0]


def noise(v, scale, detail=6.0, rough=0.6):
    n = node("ShaderNodeTexNoise", noise_dimensions="3D")
    L.new(v, n.inputs["Vector"]); n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail; n.inputs["Roughness"].default_value = rough
    return n.outputs["Fac"]


def voronoi(v, scale, feat="F1"):
    n = node("ShaderNodeTexVoronoi", feature=feat)
    L.new(v, n.inputs["Vector"]); n.inputs["Scale"].default_value = scale
    return n.outputs["Distance"]


def image(path, vec):
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = "Non-Color"
    n = node("ShaderNodeTexImage", image=img, extension="CLIP", interpolation="Cubic")
    L.new(vec, n.inputs[0])
    return n.outputs["Color"]


def combine(x, y, z=0.0):
    n = node("ShaderNodeCombineXYZ")
    for i, v in enumerate((x, y, z)):
        if sock(v) is not None:
            L.new(v, n.inputs[i])
        else:
            n.inputs[i].default_value = v
    return n.outputs[0]


tc = node("ShaderNodeTexCoord")
P = tc.outputs["Object"]
sep = node("ShaderNodeSeparateXYZ"); L.new(P, sep.inputs[0])
X, Y, Z = sep.outputs
geo = node("ShaderNodeNewGeometry")
sepn = node("ShaderNodeSeparateXYZ"); L.new(geo.outputs["Normal"], sepn.inputs[0])
NZ = sepn.outputs[2]
AX = math_("ABSOLUTE", X)
attr = node("ShaderNodeAttribute", attribute_name="vpart", attribute_type="GEOMETRY")
VP = attr.outputs["Fac"]
m_metal = math_("MULTIPLY", step(0.5, 0.6, VP), math_("SUBTRACT", 1.0, step(1.5, 1.6, VP)))
m_ruby = step(1.5, 1.6, VP)
m_leather = math_("SUBTRACT", 1.0, step(0.5, 0.6, VP))
m_flat = step(0.55, 0.75, math_("ABSOLUTE", NZ))              # faces looking along +-Z

# ---------------- leather: oxblood, pebbled grain, creases ----------------
grain = voronoi(P, 1400.0)
crease = noise(P, 60.0, 6, 0.7)
l_n = noise(P, 25.0, 5, 0.6)
leather_col = cmix(l_n, rgb(0.016, 0.004, 0.005), rgb(0.040, 0.009, 0.009))
leather_col = cmix(math_("MULTIPLY", crease, 0.35), leather_col, rgb(0.009, 0.002, 0.003))
leather_rough = mix(grain, 0.52, 0.70)
leather_h = math_("ADD", math_("MULTIPLY", grain, 0.10), math_("MULTIPLY", crease, -0.05))

# saddle stitching: dashed silver thread 4 mm in from each edge, on the flats only
stitch_band = math_("SUBTRACT", 1.0, step(0.0004, 0.0008, math_("ABSOLUTE", math_("SUBTRACT", AX, 0.0215))))
dash = step(0.2, 0.5, math_("SINE", math_("MULTIPLY", Y, 2 * math.pi / 0.0045)))
stitch = math_("MULTIPLY", math_("MULTIPLY", stitch_band, dash), m_flat)
groove = math_("MULTIPLY", math_("MULTIPLY", stitch_band, m_flat), math_("SUBTRACT", 1.0, dash))

# silver-tooled pentagram sigil between the bands (centre y 0.113, 46 mm), mirrored on the back flat
SC, SY = 0.046, 0.113
su = math_("ADD", math_("DIVIDE", X, SC), 0.5)
sv = math_("ADD", math_("DIVIDE", math_("SUBTRACT", Y, SY), SC), 0.5)
sig_f = image(f"{TEX6}/vamp_pommel_sigil.png", combine(su, math_("SUBTRACT", 1.0, sv)))
sig_b = image(f"{TEX6}/vamp_pommel_sigil.png", combine(math_("SUBTRACT", 1.0, su), math_("SUBTRACT", 1.0, sv)))
front = step(-0.1, 0.1, NZ)
sig = mix(front, math_("MULTIPLY", sig_b, 1.0), sig_f)
sig = math_("MULTIPLY", step(0.35, 0.6, sig), m_flat)

# ---------------- blackened silver (sword palette) ----------------
iron_n = noise(P, 90.0, 8, 0.65)
iron_col = cmix(iron_n, rgb(0.055, 0.052, 0.058), rgb(0.13, 0.125, 0.135))
chase = voronoi(P, 180.0)                                      # chased / hammered fittings
iron_rough = mix(chase, 0.30, 0.42)
iron_h = math_("MULTIPLY", chase, 0.12)
SILVER = rgb(0.40, 0.40, 0.42)

# ruby, as on the sword
ruby_core = noise(P, 400.0, 2, 0.5)
ruby_col = cmix(ruby_core, rgb(0.16, 0.0, 0.008), rgb(0.42, 0.005, 0.02))

# ---------------- assemble ----------------
deco = math_("MAXIMUM", stitch, sig)                         # silver on leather
col = cmix(m_metal, leather_col, iron_col)
col = cmix(math_("MULTIPLY", deco, m_leather), col, SILVER)
col = cmix(m_ruby, col, ruby_col)
metal = mix(math_("MAXIMUM", m_metal, math_("MULTIPLY", deco, m_leather)), 0.0, 1.0)
metal = mix(m_ruby, metal, 0.0)
rough = mix(m_metal, leather_rough, iron_rough)
rough = mix(math_("MULTIPLY", deco, m_leather), rough, 0.32)
rough = mix(m_ruby, rough, 0.06)
lh = math_("ADD", leather_h, math_("ADD", math_("MULTIPLY", groove, -0.5), math_("MULTIPLY", sig, 0.4)))
lh = math_("ADD", lh, math_("MULTIPLY", stitch, 0.3))
height = mix(m_metal, lh, iron_h)
height = mix(m_ruby, height, 0.0)
glow = math_("MULTIPLY", m_ruby, 0.35)

bsdf = node("ShaderNodeBsdfPrincipled")
L.new(col, bsdf.inputs["Base Color"]); L.new(metal, bsdf.inputs["Metallic"]); L.new(rough, bsdf.inputs["Roughness"])
L.new(glow, bsdf.inputs["Emission Strength"]); bsdf.inputs["Emission Color"].default_value = (1.0, 0.04, 0.02, 1.0)
bump = node("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.5
bump.inputs["Distance"].default_value = 0.0006
L.new(height, bump.inputs["Height"])
L.new(bump.outputs[0], bsdf.inputs["Normal"])
out = node("ShaderNodeOutputMaterial"); L.new(bsdf.outputs[0], out.inputs[0])

for name, s in (("BAKE_col", col), ("BAKE_rough", rough), ("BAKE_metal", metal), ("BAKE_glow", glow)):
    e = node("ShaderNodeEmission", label=name, name=name); L.new(s, e.inputs[0])

o = bpy.data.objects["Scabbard_LP"]
o.data.materials[0] = mat
print("nodes", len(N))
