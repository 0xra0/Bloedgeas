"""Write an uncooked REDkit .xbm (CBitmapTexture) from a PNG, so wcc_lite cook + buildcache can take it.

  python3 -I w3_xbm.py in.png out.xbm TextureGroup

wcc_lite's own texture import needs a D3D12 feature-level-12 device (none under wine's vkd3d),
but cooking an uncooked xbm compresses on the CPU. Layout copied from REDkit's depot xbms
(items/weapons/additional/model/*.xbm): old CR2W container, version 153, with
  header   13 u32: ver, flags, names off/count, objects off/count, links off/count, deps off/count,
           data end, 0, 0
  names    1-based, each 0x80|len + ascii
  objects  29 bytes: class u16, parent u32, size u32, offset u32, 15 bytes as in the depot files
  CBitmapTexture  props width, height, sourceData, textureGroup, importFile, then u16 0, u32 0,
           mip count, per mip (w, h, pitch, u32 size, RGBA8 rows), u32 0
  CSourceTexture  props width, height, pitch, then u16 0, u32 size, RGBA8 rows
The compression is not stored: the texture group picks it when cooking (WorldDiffuse -> DXT1,
NormalmapGloss -> TCM_NormalsGloss). The editor thumbnail the depot files append is left out.
"""
import struct, sys
from PIL import Image

OBJ_REST = bytes.fromhex("000000000000800000000000000000")


def w2str(s):
    b = s.encode("ascii")
    n = len(b)
    return (bytes([0x80 | n]) if n < 64 else bytes([0xC0 | (n & 63), n >> 6])) + b


def write_xbm(png, out, group):
    im = Image.open(png).convert("RGBA")
    w, h = im.size
    names = ["CBitmapTexture", "width", "Uint32", "height", "sourceData", "handle:CSourceTexture",
             "CSourceTexture", "pitch", "textureGroup", "CName", group, "importFile", "String"]
    ix = {n: i + 1 for i, n in enumerate(names)}
    prop = lambda n, t, v: struct.pack("<HHI", ix[n], ix[t], 4 + len(v)) + v
    u32 = lambda v: struct.pack("<I", v)

    mips = [im]
    while mips[-1].size != (1, 1):
        mw, mh = mips[-1].size
        mips.append(mips[-1].resize((max(1, mw // 2), max(1, mh // 2)), Image.BOX))
    bmp = (prop("width", "Uint32", u32(w)) + prop("height", "Uint32", u32(h))
           + prop("sourceData", "handle:CSourceTexture", u32(2))
           + prop("textureGroup", "CName", struct.pack("<H", ix[group]))
           + prop("importFile", "String", w2str("Z:" + png.replace("/", "\\")))
           + struct.pack("<HI", 0, 0) + u32(len(mips)))
    bmp += b"".join(struct.pack("<IIII", m.size[0], m.size[1], m.size[0] * 4, m.size[0] * m.size[1] * 4) + m.tobytes()
                    for m in mips) + u32(0)
    src = (prop("width", "Uint32", u32(w)) + prop("height", "Uint32", u32(h)) + prop("pitch", "Uint32", u32(w * 4))
           + struct.pack("<HI", 0, w * h * 4) + im.tobytes())

    ntab = b"".join(bytes([0x80 | len(n)]) + n.encode() for n in names)
    obj_off = 56 + len(ntab)
    data_off = obj_off + 2 * 29
    objs = (struct.pack("<HIII", ix["CBitmapTexture"], 0, len(bmp), data_off) + OBJ_REST
            + struct.pack("<HIII", ix["CSourceTexture"], 1, len(src), data_off + len(bmp)) + OBJ_REST)
    end = data_off + len(bmp) + len(src)
    hdr = b"CR2W" + struct.pack("<13I", 153, 0, 56, len(names), obj_off, 2, obj_off, 0, obj_off, 1, end, 0, 0)
    open(out, "wb").write(hdr + ntab + objs + bmp + src)
    print("xbm", out, (w, h), group, len(mips), "mips", end, "bytes")


if __name__ == "__main__":
    write_xbm(*sys.argv[1:4])
