"""Write a GUI icon PNG as a single-entry W3 texture.cache, the way DLCs ship their inventory icons.

  python3 -I icon_texcache.py icon.png out/texture.cache "dlc\\<dlc>\\data\\gameplay\\gui_new\\icons\\...\\x.png" [name2 ...]

The GUI never reads a raw PNG from a bundle: icon_path "icons/x.png" resolves to the depot path
dlc\\<dlc>\\data\\gameplay\\gui_new\\icons\\x.png and is looked up in the texture caches, where the cooked
icon sits under that same .png name. Entry fields copied from dlcHoods' icons (checked 2026-10-21):
DXT5 (format byte 8, type 4), one mip, no mip offsets, NumMipOffsets field 0x10000. The entry hash is
WolvenKit-7's HashKey (h = h*31 + char over the path). Chunk, mip table and footer layout and the
checksum as in tint_texcache.py. Every name gets its own copy of the pixels (one page each), so the
same icon can sit under several depot paths. The timestamp is vanilla's; every cooked entry has one.
"""
import io, os, struct, sys, zlib
from PIL import Image

sys.path.insert(0, "/mnt/ssd/Codex/2026-10-12/i-x20/witcher3-romance-mod/tools")
from tint_texcache import checksum

CACHE_VER = 7
TIMESTAMP = 258794411886983168            # from content0's own weapon icons


def hash_key(s):
    h = 0
    for c in s:
        h = (h * 31 + ord(c)) & 0xFFFFFFFF
    return h


def dxt5(png):
    im = Image.open(png).convert("RGBA")
    assert im.width % 4 == 0 and im.height % 4 == 0, im.size
    buf = io.BytesIO()
    im.save(buf, "DDS", pixel_format="DXT5")
    dds = buf.getvalue()
    data = dds[128:]                                   # plain DDS header, no DX10 extension for DXT5
    assert len(data) == im.width * im.height, (len(data), im.size)
    return im.size, data


def main(png, out, *names):
    (w, h), raw = dxt5(png)
    z = zlib.compress(raw, 9)
    page = struct.pack("<IIB", len(z), len(raw), 0) + z
    csz = len(page)
    page += b"\0" * (-len(page) % 4096)
    body, strs, ents = b"", b"", b""
    for name in names:
        ents += struct.pack("<IiIIIIHHHHiiqBBBB", hash_key(name), len(strs), len(body) // 4096, csz, len(raw), 16,
                            w, h, 1, 1, 0, 0x10000, TIMESTAMP, 8, 4, 0, 0)
        strs += name.encode("ascii") + b"\0"
        body += page
    tables = strs + ents                               # no mip table: one mip
    foot = struct.pack("<QIIII4sI", checksum(tables), len(body) // 4096, len(names), len(strs), 0, b"HCXT", CACHE_VER)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    open(out, "wb").write(body + tables + foot)
    print("texture.cache ->", out, os.path.getsize(out), "bytes,", w, "x", h, *names)


if __name__ == "__main__":
    main(*sys.argv[1:])
