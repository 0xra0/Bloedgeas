"""Pack .bnk/.wem files into a W3 next-gen soundspc.cache ("CS3W" version 2).

  python3 -I soundcache.py <out soundspc.cache> <file.bnk|file.wem>...

Layout, as in the vanilla content0/soundspc.cache (checked 2026-10-21):
  0x00  "CS3W", u32 version 2, 8 bytes (unknown, copied from vanilla)
  0x10  u64 info offset, u64 file count, u64 names offset
  0x28  u32 names size, u32 (unknown, vanilla 186)
  0x30  u64 buffer size (largest file rounded up to 4096), u64 checksum
  0x40  file data back to back, then the 0-terminated names, then the info table (u64 name off, data off, size)
The checksum is FNV-1a 64 over names + info table; it reproduces vanilla's exactly.
"""
import os, struct, sys

VANILLA_UNK = bytes.fromhex("0094a47ec9e6e305")
VANILLA_UNK3 = 186
DATA = 0x40


def fnv1a64(b):
    h = 0xcbf29ce484222325
    for c in b:
        h = ((h ^ c) * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h


def write(out, files):
    blobs = [open(f, "rb").read() for f in files]
    names = b"".join(os.path.basename(f).lower().encode() + b"\0" for f in files)
    info, name_off, data_off = b"", 0, DATA
    for f, b in zip(files, blobs):
        info += struct.pack("<QQQ", name_off, data_off, len(b))
        name_off += len(os.path.basename(f)) + 1
        data_off += len(b)
    buf = -(-max(map(len, blobs)) // 4096) * 4096
    with open(out, "wb") as o:
        o.write(b"CS3W" + struct.pack("<I", 2) + VANILLA_UNK)
        o.write(struct.pack("<QQQII", data_off + len(names), len(files), data_off, len(names), VANILLA_UNK3))
        o.write(struct.pack("<QQ", buf, fnv1a64(names + info)))
        for b in blobs:
            o.write(b)
        o.write(names + info)
    print("cache ->", out, len(files), "file(s)", os.path.getsize(out), "bytes")


if __name__ == "__main__":
    write(sys.argv[1], sys.argv[2:])
