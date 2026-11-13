"""Procedural 'vampire' (v6) material for Sword_LP, derived from the c.1150 v5 shader (object coords, long axis +Y).
Blackened steel blade with blood-red runes in the fuller, dark tarnished silver hilt with red enamel sigil,
black leather grip with silver wire, rubies. Point attribute 'vpart' tells the add-on parts apart:
0 original mesh, 1 vampire silverwork, 2 ruby.

v5 regions: pommel + ferrule/neck y<-0.397, grip -0.397..-0.259, guard + collar -0.259..-0.226,
blade above. Pommel inlay recentred on the v5 wheel (0, -0.4495). Outputs a material 'Sword_c1150_proc' whose
Principled BSDF is driven by per-part colour / metallic / roughness / height.
"""
import bpy, math

TEX = "/mnt/ssd/ComfyUI/output/3D/KnightSword_c1150_tex"
TEX6 = "/mnt/ssd/ComfyUI/output/3D/KnightSword_vamp_v6_tex"

mat = bpy.data.materials.get("Sword_vamp_proc") or bpy.data.materials.new("Sword_vamp_proc")
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


def step(edge0, edge1, x):  # smoothstep-ish via map range
    n = node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
    L.new(x, n.inputs[0]) if sock(x) is not None else None
    n.inputs[1].default_value, n.inputs[2].default_value = edge0, edge1
    return n.outputs[0]


def vec_scale(v, sx, sy, sz):
    n = node("ShaderNodeVectorMath", operation="MULTIPLY")
    L.new(v, n.inputs[0]); n.inputs[1].default_value = (sx, sy, sz)
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


def image(path, vec, noncolor=True, ext="CLIP"):
    img = bpy.data.images.load(path, check_existing=True)
    if noncolor:
        img.colorspace_settings.name = "Non-Color"
    n = node("ShaderNodeTexImage", image=img, extension=ext, interpolation="Cubic")
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
m_vmetal = math_("MULTIPLY", step(0.5, 0.6, VP), math_("SUBTRACT", 1.0, step(1.5, 1.6, VP)))
m_ruby = step(1.5, 1.6, VP)
m_orig = math_("SUBTRACT", 1.0, step(0.5, 0.6, VP))

# ---------------- region masks (soft 1 mm transitions) ----------------
m_pommel = math_("SUBTRACT", 1.0, step(-0.3975, -0.3965, Y))
m_grip_up = step(-0.3975, -0.3965, Y)
m_guard_lo = step(-0.2590, -0.2580, Y)
m_blade = math_("MULTIPLY", step(-0.2270, -0.2250, Y), m_orig)
m_grip = math_("MULTIPLY", math_("MULTIPLY", m_grip_up, math_("SUBTRACT", 1.0, m_guard_lo)), m_orig)
m_guard = math_("MULTIPLY", m_guard_lo, math_("SUBTRACT", 1.0, m_blade))

# ---------------- shared iron (guard + pommel): dark forged iron ----------------
hammer = voronoi(vec_scale(P, 1, 1, 1), 180.0)               # hammer facets
iron_n = noise(P, 90.0, 8, 0.65)
iron_col = cmix(iron_n, rgb(0.055, 0.052, 0.058), rgb(0.13, 0.125, 0.135))   # blackened silver
# raised edges rubbed back to bright silver, recesses stay black (pointiness = convexity, Cycles bake)
pointy = step(0.64, 0.72, geo.outputs["Pointiness"])
iron_col = cmix(math_("MULTIPLY", pointy, 0.5), iron_col, rgb(0.45, 0.45, 0.47))
iron_rough = mix(iron_n, 0.38, 0.58)
iron_rough = mix(pointy, iron_rough, 0.22)
iron_h = math_("MULTIPLY", hammer, 0.35)

# latten (brass-like copper alloy) inlay look
LATTEN = rgb(0.20, 0.004, 0.008)   # name kept from v5: here a blood-red enamel

# guard: two incised latten bands near each arm end + bright worn tips
gx = math_("SUBTRACT", AX, 0.0)
band = math_("MAXIMUM",
             math_("MULTIPLY", step(0.0835, 0.0845, gx), math_("SUBTRACT", 1.0, step(0.0870, 0.0880, gx))),
             math_("MULTIPLY", step(0.0905, 0.0915, gx), math_("SUBTRACT", 1.0, step(0.0940, 0.0950, gx))))
guard_tip_wear = step(0.095, 0.108, gx)

# pommel: cross + ring inlay on the two flat faces (|Nz| high)
PCX, PCY, PR = 0.0, -0.4495, 0.042
pu = math_("ADD", math_("DIVIDE", math_("SUBTRACT", X, PCX), 2 * PR), 0.5)
pv = math_("ADD", math_("DIVIDE", math_("SUBTRACT", Y, PCY), 2 * PR), 0.5)
pom_mask_img = image(f"{TEX6}/vamp_pommel_sigil.png", combine(pu, pv))
pom_face = step(0.55, 0.8, math_("ABSOLUTE", NZ))
pom_inlay = math_("MULTIPLY", step(0.35, 0.65, pom_mask_img), pom_face)
# rim of the wheel is worn bright from handling
pr = math_("SQRT", math_("ADD", math_("POWER", math_("SUBTRACT", X, PCX), 2.0),
                         math_("POWER", math_("SUBTRACT", Y, PCY), 2.0)))
pom_rim = step(0.033, 0.041, pr)

# ---------------- blade: polished steel ----------------
# long grinding scratches run along the blade (stretch noise in Y)
scr = noise(vec_scale(P, 1.0, 0.02, 1.0), 900.0, 2, 0.5)
scr_l = step(0.55, 0.72, scr)
fold = noise(vec_scale(P, 1.0, 0.25, 1.0), 40.0, 5, 0.6)       # faint forge mottling
wave = noise(vec_scale(P, 3.0, 0.35, 3.0), 60.0, 4, 0.55)          # watered-steel banding
wave = math_("ABSOLUTE", math_("SINE", math_("MULTIPLY", wave, 28.0)))
steel_col = cmix(fold, rgb(0.030, 0.030, 0.035), rgb(0.055, 0.055, 0.062))
steel_col = cmix(math_("MULTIPLY", step(0.6, 0.95, wave), 0.55), steel_col, rgb(0.09, 0.09, 0.10))
steel_col = cmix(math_("MULTIPLY", scr_l, 0.35), steel_col, rgb(0.13, 0.13, 0.14))
steel_rough = mix(scr_l, 0.40, 0.26)
steel_rough = mix(fold, steel_rough, math_("ADD", steel_rough, 0.06))
# sharpened edge bevel: brighter + smoother, cross-hatched honing marks
edge = step(0.0160, 0.0185, AX)
hone = noise(vec_scale(combine(math_("ADD", X, Y), math_("SUBTRACT", Y, X), Z), 1.0, 1.0, 1.0), 1400.0, 1, 0.5)
steel_col = cmix(edge, steel_col, rgb(0.55, 0.55, 0.57))
steel_rough = mix(edge, steel_rough, mix(hone, 0.10, 0.20))
# light pitting / oxidation spots, more near the hilt where hands sweat
pit = math_("SUBTRACT", 1.0, step(0.0, 0.06, voronoi(P, 900.0)))
pit_amt = math_("MULTIPLY", pit, math_("MULTIPLY", step(0.3, 0.75, noise(P, 25.0, 3)),
                                       math_("SUBTRACT", 1.0, step(-0.20, 0.10, Y))))
steel_col = cmix(math_("MULTIPLY", pit_amt, 0.8), steel_col, rgb(0.10, 0.02, 0.015))
steel_rough = mix(pit_amt, steel_rough, 0.75)

# fuller: |x|<~7.5 mm, from the guard to ~3/4 of the blade, tapering out
f_end = step(0.30, 0.36, Y)
f_w = mix(f_end, 0.0078, 0.0)
fw_lo = math_("SUBTRACT", f_w, 0.0010)
fuller = math_("SUBTRACT", 1.0, math_("DIVIDE", math_("SUBTRACT", AX, fw_lo), 0.0010, clamp=False))
fuller = math_("MINIMUM", math_("MAXIMUM", fuller, 0.0), 1.0)
fuller = math_("MULTIPLY", fuller, step(-0.215, -0.205, Y))
steel_col = cmix(math_("MULTIPLY", fuller, 0.6), steel_col, rgb(0.05, 0.05, 0.055))
steel_rough = mix(fuller, steel_rough, math_("ADD", steel_rough, 0.10))

# inscription in the fuller: front (z>0) and back (z<0) read correctly from their side
IY0, IL, IW = -0.145, 0.300, 0.0130
iu = math_("DIVIDE", math_("SUBTRACT", Y, IY0), IL)
iv = math_("ADD", math_("DIVIDE", X, IW), 0.5)
ins_f = image(f"{TEX6}/vamp_blade_runes.png", combine(iu, math_("SUBTRACT", 1.0, iv)))
ins_b = image(f"{TEX6}/vamp_blade_runes.png", combine(iu, iv))
side = step(-0.001, 0.001, Z)  # 1 on the front face
ins = mix(side, ins_b, ins_f)
ins = math_("MULTIPLY", step(0.3, 0.7, ins), step(0.5, 0.9, fuller))
RUNE = rgb(0.62, 0.02, 0.02)
steel_col = cmix(ins, steel_col, RUNE)
steel_rough = mix(ins, steel_rough, 0.32)
# dried blood: runs down from the fuller toward the guard, pooled in the fuller and near the hilt
drip = noise(vec_scale(P, 6.0, 0.18, 6.0), 30.0, 6, 0.65)
blood = math_("MULTIPLY", step(0.56, 0.66, drip), math_("SUBTRACT", 1.0, step(-0.12, 0.10, Y)))
blood = math_("MAXIMUM", blood, math_("MULTIPLY", math_("MULTIPLY", fuller, step(0.50, 0.62, drip)),
                                       math_("SUBTRACT", 1.0, step(0.05, 0.25, Y))))
blood = math_("MULTIPLY", blood, math_("SUBTRACT", 1.0, ins))
steel_col = cmix(math_("MULTIPLY", blood, 0.9), steel_col, rgb(0.09, 0.004, 0.004))
steel_rough = mix(blood, steel_rough, 0.30)

# ---------------- grip: spiral-wrapped leather over cord risers ----------------
ang = math_("DIVIDE", math_("ARCTAN2", Z, X), 2 * math.pi)
phase = math_("FRACT", math_("ADD", math_("DIVIDE", Y, 0.0145), ang))
groove = math_("SUBTRACT", 1.0, step(0.0, 0.10, math_("MINIMUM", phase, math_("SUBTRACT", 1.0, phase))))
grain = noise(P, 1200.0, 8, 0.7)
crease = math_("SUBTRACT", 1.0, step(0.0, 0.05, voronoi(P, 350.0, "DISTANCE_TO_EDGE")))
leather_col = cmix(grain, rgb(0.012, 0.007, 0.008), rgb(0.032, 0.009, 0.010))
leather_col = cmix(math_("MULTIPLY", groove, 0.85), leather_col, rgb(0.008, 0.004, 0.004))
# hand-polish in the middle of the grip (lighter, slicker)
polish = math_("MULTIPLY", step(-0.385, -0.345, Y), math_("SUBTRACT", 1.0, step(-0.30, -0.265, Y)))
polish = math_("MULTIPLY", polish, step(0.35, 0.7, noise(P, 60.0, 3)))
leather_col = cmix(math_("MULTIPLY", polish, 0.5), leather_col, rgb(0.050, 0.014, 0.016))
leather_rough = mix(polish, mix(grain, 0.58, 0.72), 0.42)
# linen-cord bindings at both ends of the grip
bind = math_("MAXIMUM",
             math_("MULTIPLY", step(-0.2725, -0.2715, Y), math_("SUBTRACT", 1.0, step(-0.2600, -0.2590, Y))),
             math_("MULTIPLY", step(-0.4055, -0.4045, Y), math_("SUBTRACT", 1.0, step(-0.3935, -0.3925, Y))))
cord = math_("ABSOLUTE", math_("SINE", math_("MULTIPLY", Y, 2 * math.pi / 0.0016)))
leather_col = cmix(bind, leather_col, cmix(cord, rgb(0.04, 0.04, 0.045), rgb(0.28, 0.28, 0.30)))   # silver wire
leather_rough = mix(bind, leather_rough, mix(cord, 0.55, 0.25))
leather_h = math_("ADD", math_("MULTIPLY", groove, -0.6),
                  math_("ADD", math_("MULTIPLY", grain, 0.08), math_("MULTIPLY", crease, -0.04)))
leather_h = mix(bind, leather_h, math_("MULTIPLY", cord, 0.35))

# ---------------- assemble ----------------
iron_part = math_("MAXIMUM", math_("MULTIPLY", math_("MAXIMUM", m_guard, m_pommel), m_orig), m_vmetal)
inlay_iron = math_("MULTIPLY", math_("MAXIMUM", math_("MULTIPLY", band, m_guard), math_("MULTIPLY", pom_inlay, m_pommel)), m_orig)
wear_iron = math_("MULTIPLY", math_("MAXIMUM", math_("MULTIPLY", guard_tip_wear, m_guard), math_("MULTIPLY", pom_rim, m_pommel)), m_orig)
iron_c = cmix(math_("MULTIPLY", wear_iron, 0.6), iron_col, rgb(0.55, 0.55, 0.57))
iron_c = cmix(inlay_iron, iron_c, LATTEN)
iron_r = mix(wear_iron, iron_rough, 0.28)
iron_r = mix(inlay_iron, iron_r, 0.45)
iron_hh = mix(inlay_iron, iron_h, -0.25)

# ruby: deep red, darker toward the rim, bright pinpoint core
ruby_core = noise(P, 400.0, 2, 0.5)
ruby_col = cmix(ruby_core, rgb(0.16, 0.0, 0.008), rgb(0.42, 0.005, 0.02))
col = cmix(m_blade, cmix(iron_part, leather_col, iron_c), steel_col)
col = cmix(m_ruby, col, ruby_col)
metal = mix(m_grip, 1.0, 0.0)
metal = mix(inlay_iron, metal, 0.0)              # enamel is not metal
metal = mix(blood, metal, math_("MULTIPLY", metal, math_("SUBTRACT", 1.0, m_blade)))   # dried blood on blade: dielectric
metal = mix(ins, metal, math_("MULTIPLY", metal, math_("SUBTRACT", 1.0, m_blade)))     # rune lacquer: dielectric
metal = mix(m_ruby, metal, 0.0)
rough = mix(m_blade, mix(iron_part, leather_rough, iron_r), steel_rough)
rough = mix(m_ruby, rough, 0.06)
blade_h = math_("ADD", math_("MULTIPLY", ins, -0.35), math_("MULTIPLY", pit_amt, -0.3))
height = mix(m_blade, mix(iron_part, leather_h, iron_hh), blade_h)
height = mix(m_ruby, height, 0.0)
# glow mask: runes (and a faint ember in the rubies) for the W3 emissive / an optional glow pass
glow = math_("MAXIMUM", math_("MULTIPLY", ins, m_blade), math_("MULTIPLY", m_ruby, 0.35))

bsdf = node("ShaderNodeBsdfPrincipled")
L.new(col, bsdf.inputs["Base Color"]); L.new(metal, bsdf.inputs["Metallic"]); L.new(rough, bsdf.inputs["Roughness"])
L.new(glow, bsdf.inputs["Emission Strength"]); bsdf.inputs["Emission Color"].default_value = (1.0, 0.04, 0.02, 1.0)
bump = node("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.5
bump.inputs["Distance"].default_value = 0.0006
L.new(height, bump.inputs["Height"])
L.new(bump.outputs[0], bsdf.inputs["Normal"])
out = node("ShaderNodeOutputMaterial"); L.new(bsdf.outputs[0], out.inputs[0])

# expose channels for emission bakes
for name, s in (("BAKE_col", col), ("BAKE_rough", rough), ("BAKE_metal", metal), ("BAKE_glow", glow)):
    e = node("ShaderNodeEmission", label=name, name=name); L.new(s, e.inputs[0])

o = bpy.data.objects["Sword_LP"]
o.data.materials[0] = mat
print("nodes", len(N))
