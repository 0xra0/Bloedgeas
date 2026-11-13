"""v6 'vampire' hilt add-ons for Sword_LP (object coords, long axis +Y, blade flats face +-Z).

ruby_pommel - flattened cabochon in each pommel face (wheel centre (0,-0.4495), face |z|=0.0182) + bezel ring
horns       - tapered fang horns curling from the guard bulbs (x=+-0.104, y=-0.239) toward the blade
langet      - bat-head plate shrinkwrapped onto both blade flats over the ricasso, with a small ruby 'eye'
Every part is its own object named Vamp_*; build() returns them. Material slot names drive the shader:
'Vamp_metal' for silverwork, 'Vamp_ruby' for gems.
"""
import bpy, bmesh, math
from mathutils import Vector

COL = bpy.context.scene.collection


def _mat(name):
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)


def _obj(name, bm, mat):
    old = bpy.data.objects.get(name)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(_mat(mat))
    o = bpy.data.objects.new(name, me); COL.objects.link(o)
    for p in me.polygons: p.use_smooth = True
    return o


def cabochon(name, center, r, height, sign, segs=24, rings=6):
    """Dome of radius r and given height, base at center, bulging toward sign*Z; plus a bezel torus."""
    bm = bmesh.new()
    cx, cy, cz = center
    rows = []
    for i in range(rings + 1):
        t = i / rings                         # 0 base .. 1 apex
        a = t * math.pi / 2
        rr, zz = r * math.cos(a), height * math.sin(a)
        if i == rings:
            rows.append([bm.verts.new((cx, cy, cz + sign * zz))]); break
        rows.append([bm.verts.new((cx + rr * math.cos(k * 2 * math.pi / segs),
                                   cy + rr * math.sin(k * 2 * math.pi / segs), cz + sign * zz)) for k in range(segs)])
    for i in range(rings - 1):
        a, b = rows[i], rows[i + 1]
        for k in range(segs):
            bm.faces.new((a[k], a[(k + 1) % segs], b[(k + 1) % segs], b[k]) if sign > 0 else
                         (b[k], b[(k + 1) % segs], a[(k + 1) % segs], a[k]))
    a, apex = rows[rings - 1], rows[rings][0]
    for k in range(segs):
        bm.faces.new((a[k], a[(k + 1) % segs], apex) if sign > 0 else (apex, a[(k + 1) % segs], a[k]))
    bm.faces.new(rows[0][::sign])             # sealed base (hidden inside the hilt)
    gem = _obj(name, bm, "Vamp_ruby")

    # bezel: torus hugging the gem's base, half sunk into the pommel
    bm = bmesh.new()
    R, rt, n1, n2 = r + 0.0008, 0.0012, segs, 8
    grid = [[bm.verts.new((cx + (R + rt * math.cos(b)) * math.cos(a), cy + (R + rt * math.cos(b)) * math.sin(a),
                           cz + rt * math.sin(b)))
             for b in (j * 2 * math.pi / n2 for j in range(n2))] for a in (i * 2 * math.pi / n1 for i in range(n1))]
    for i in range(n1):
        for j in range(n2):
            bm.faces.new((grid[i][j], grid[(i + 1) % n1][j], grid[(i + 1) % n1][(j + 1) % n2], grid[i][(j + 1) % n2]))
    bez = _obj(name + "_bezel", bm, "Vamp_metal")
    return [gem, bez]


def horn(name, pts, r0, r1, sides=10, steps=28):
    """Tube along a cubic Bezier (4 points), radius r0 -> r1 (ease-out taper), tip closed to a point."""
    P = [Vector(p) for p in pts]

    def bez(t):
        u = 1 - t
        return u**3 * P[0] + 3 * u * u * t * P[1] + 3 * u * t * t * P[2] + t**3 * P[3]

    bm = bmesh.new()
    rings, prev_n = [], Vector((0, 0, 1))
    for i in range(steps + 1):
        t = i / steps
        c = bez(t)
        tan = (bez(min(t + 1e-3, 1)) - bez(max(t - 1e-3, 0))).normalized()
        n = (prev_n - tan * prev_n.dot(tan)).normalized(); prev_n = n   # parallel-transport frame
        b = tan.cross(n)
        r = r0 + (r1 - r0) * (1 - (1 - t) ** 1.6)
        if i == steps:
            rings.append([bm.verts.new(c)]); break
        rings.append([bm.verts.new(c + r * (math.cos(k * 2 * math.pi / sides) * n + math.sin(k * 2 * math.pi / sides) * b))
                      for k in range(sides)])
    for i in range(steps - 1):
        a, c = rings[i], rings[i + 1]
        for k in range(sides):
            bm.faces.new((a[k], a[(k + 1) % sides], c[(k + 1) % sides], c[k]))
    a, tip = rings[steps - 1], rings[steps][0]
    for k in range(sides):
        bm.faces.new((a[k], a[(k + 1) % sides], tip))
    bm.faces.new(rings[0][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, "Vamp_metal")


# bat-head outline (right half, x>=0), base on the guard collar, point toward the tip
LANGET_HALF = [(0.0, -0.1520), (0.0055, -0.1700), (0.0035, -0.1790), (0.0110, -0.1880),
               (0.0236, -0.1760), (0.0200, -0.1960), (0.0228, -0.2060), (0.0170, -0.2120),
               (0.0236, -0.2255)]


def langet(name, blade, side, thick=0.0011):
    # right side tip->base, then left side base->tip (the shared tip vertex only once)
    pts = LANGET_HALF + [(-x, y) for x, y in reversed(LANGET_HALF)][:-1]
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, side * 0.0060)) for x, y in pts]
    f = bm.faces.new(vs if side > 0 else vs[::-1])
    bmesh.ops.triangulate(bm, faces=[f])
    # subdivide so the plate can follow the blade's cross-section when shrinkwrapped
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
    # grid fill leaves mixed windings; solidify needs every face pointing away from the blade
    bmesh.ops.reverse_faces(bm, faces=[f for f in bm.faces if f.normal.z * side < 0])
    o = _obj(name, bm, "Vamp_metal")
    sw = o.modifiers.new("wrap", "SHRINKWRAP"); sw.target = blade; sw.wrap_method = "PROJECT"
    sw.use_project_z = True; sw.use_negative_direction = sw.use_positive_direction = True   # straight down onto the flat
    sw.offset = 0.00015
    so = o.modifiers.new("solid", "SOLIDIFY"); so.thickness = thick; so.offset = 1.0; so.use_even_offset = True
    with bpy.context.temp_override(object=o, active_object=o):
        for m in ("wrap", "solid"):
            bpy.ops.object.modifier_apply(modifier=m)
    return o


def build():
    blade = bpy.data.objects["Sword_LP"]
    parts = []
    for s in (1, -1):
        parts += cabochon(f"Vamp_ruby_pommel_{'f' if s > 0 else 'b'}", (0.0, -0.4495, s * 0.0170), 0.0072, 0.0058, s)
        parts.append(langet(f"Vamp_langet_{'f' if s > 0 else 'b'}", blade, s))
        parts += cabochon(f"Vamp_ruby_eye_{'f' if s > 0 else 'b'}", (0.0, -0.2080, s * 0.0068), 0.0034, 0.0024, s)
    for sx in (1, -1):
        parts.append(horn(f"Vamp_horn_{'r' if sx > 0 else 'l'}",
                          [(sx * 0.0990, -0.2392, 0.0), (sx * 0.1300, -0.2440, 0.0),
                           (sx * 0.1480, -0.2140, 0.0), (sx * 0.1300, -0.1780, 0.0)], 0.0092, 0.0005))
    # pommel crown: fangs radiating from the wheel rim, none on the grip side
    for k, deg in enumerate((-90, -50, -130, -10, -170)):
        a = math.radians(deg); ux, uy = math.cos(a), math.sin(a)
        L = 0.030 if k == 0 else 0.022
        base = (0.0365 * ux, -0.4495 + 0.0365 * uy, 0.0)
        tip = (0.0400 * ux + L * ux, -0.4495 + (0.0400 + L) * uy, 0.0)
        mid = ((base[0] + tip[0]) / 2 - 0.004 * uy, (base[1] + tip[1]) / 2 + 0.004 * ux, 0.0)   # slight hook
        parts.append(horn(f"Vamp_pommel_fang_{k}", [base, mid, mid, tip], 0.0090, 0.0005, steps=16))
    return parts
