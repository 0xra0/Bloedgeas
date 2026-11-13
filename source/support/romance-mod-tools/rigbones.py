"""Append bones to an uncooked W3 .w2rig (CSkeleton) without touching anything else.

  python3 rigbones.py in.w2rig out.w2rig [bones.json]
bones.json: [{"name": "penis_01", "parent": "pelvis", "pos": [x,y,z], "rot": [x,y,z,w]}, ...]
pos/rot are parent-local, in the file's own convention. With no json it rebuilds the file
unchanged, which must reproduce the input byte for byte.
"""
import json, struct, sys, zlib
from cr2w import CR2W

def fnv1a32(b):
    h = 0x811C9DC5
    for x in b:
        h = ((h ^ x) * 0x01000193) & 0xFFFFFFFF
    return h

def crc(b):
    return zlib.crc32(b) & 0xFFFFFFFF

def rebuild(c, chunk_bytes, extra_names):
    d = c.d
    so, ssz, _ = c.tables[0]
    strings = bytearray(d[so:so + ssz])
    no, nn, _ = c.tables[1]
    names_tab = bytearray(d[no:no + 8 * nn])
    for n in extra_names:
        off = len(strings)
        strings += n.encode("latin-1") + b"\0"
        names_tab += struct.pack("<II", off, fnv1a32(n.encode("latin-1") + b"\0"))
    # Tables 2..3 copied verbatim (imports, properties); exports rebuilt; buffers (5) copied
    # only when external (offset 0, data in .N.buffer files); 6+ must be empty.
    assert all(t[1] == 0 for t in c.tables[6:]), "embedded files not supported"
    bo, bc, _ = c.tables[5]
    buffers = bytes(d[bo:bo + 24 * bc]) if bc else b""
    assert all(struct.unpack_from("<IIIIII", buffers, 24 * i)[2] == 0 for i in range(bc)), "internal buffers"
    io_, ic, _ = c.tables[2]
    po, pc, _ = c.tables[3]
    imports = bytes(d[io_:io_ + 8 * ic]) if ic else b""
    props = bytes(d[po:po + 16 * pc]) if pc else b""
    pos = 160 + len(strings)
    names_off = pos; pos += len(names_tab)
    imp_off = pos if ic else 0; pos += len(imports)
    props_off = pos; pos += len(props)
    exp_off = pos; pos += 24 * len(c.exports)
    buf_off = pos if bc else 0; pos += len(buffers)
    data = b""
    exports = b""
    for e, cb in zip(c.exports, chunk_bytes):
        cls, oflags, parent, _, _, tmpl, ocrc = e
        # Unchanged chunks keep their stored crc (the CSkeleton one is stale in the source).
        same = cb == bytes(d[e[4]:e[4] + e[3]])
        exports += struct.pack("<HHIIIII", cls, oflags, parent, len(cb), pos + len(data), tmpl, ocrc if same else crc(cb))
        data += cb
    fsize = pos + len(data)
    tables = [(160, len(strings), crc(strings)), (names_off, len(names_tab) // 8, crc(names_tab)),
              (imp_off, ic, crc(imports) if ic else 0), (props_off, pc, crc(props)),
              (exp_off, len(c.exports), crc(exports)),
              (buf_off, bc, crc(buffers) if bc else 0)] + [(0, 0, 0)] * 4
    def header(crcv):
        h = b"CR2W" + struct.pack("<IIQIIIII", c.version, c.flags, c.ts, c.build, fsize, fsize, crcv, c.nchunks)
        return h + b"".join(struct.pack("<III", *t) for t in tables)
    hcrc = crc(header(0xDEADBEEF))
    return header(hcrc) + bytes(strings) + bytes(names_tab) + imports + props + exports + buffers + data

def main():
    src, dst = sys.argv[1], sys.argv[2]
    c = CR2W(open(src, "rb").read())
    chunks = [bytes(c.d[e[4]:e[4] + e[3]]) for e in c.exports]
    new = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else []
    extra = [b["name"] for b in new if b["name"] not in c.names]
    if new:
        chunks[0] = add_bones(c, chunks[0], new, extra)
    out = rebuild(c, chunks, extra)
    open(dst, "wb").write(out)
    print("wrote", dst, len(out), "identical" if out == bytes(c.d) else "changed")

def add_bones(c, ch, new, extra):
    names = c.names + extra
    idx = {n: i for i, n in enumerate(names)}
    e = c.exports[0]
    base = e[4]
    pr, endp = c.props(base + 1, base + e[3])
    P = {q[0]: q for q in pr}
    bones_p, par_p = P["bones"], P["parentIndices"]
    nb, = struct.unpack_from("<I", c.d, bones_p[2])
    # Bone element template: copy the last bone's serialized struct, swap its name fields.
    elems, p = [], bones_p[2] + 4
    for _ in range(nb):
        sub, q = c.props(p + 1, bones_p[2] + bones_p[3])  # each struct starts with a 0 byte
        elems.append((p, q, sub)); p = q
    def sval(s):
        return c.d[s[2] + 1:s[2] + s[3] - (0 if c.d[s[2]] & 0x80 else 1)].decode()
    bone_names = [sval(s) for _, _, sub in elems for s in sub if s[0] == "name"]
    tmpl_s, tmpl_e, tmpl_sub = elems[-1]
    def elem(name):
        out = b"\0"
        for s in tmpl_sub:
            ni, ti = struct.unpack_from("<HH", c.d, s[4])
            if s[0] == "name":
                # cooked files: 0x80|len, no terminator; uncooked: len+1, NUL-terminated
                v = (bytes([0x80 | len(name)]) + name.encode() if c.d[s[2]] & 0x80
                     else bytes([len(name) + 1]) + name.encode() + b"\0")
            elif s[0] == "nameAsCName":
                v = struct.pack("<H", idx[name])
            else:
                v = bytes(c.d[s[2]:s[2] + s[3]])
            out += struct.pack("<HHI", ni, ti, len(v) + 4) + v
        return out + b"\0\0"
    # sanity: the template rebuilt from its own name must equal the original bytes
    assert elem(bone_names[-1]) == bytes(c.d[tmpl_s:tmpl_e]), "bone element template mismatch"
    parents = list(struct.unpack_from("<%dh" % nb, c.d, par_p[2] + 4))
    bones_v = struct.pack("<I", nb + len(new)) + bytes(c.d[bones_p[2] + 4:bones_p[2] + bones_p[3]]) + b"".join(elem(b["name"]) for b in new)
    allnames = bone_names + [b["name"] for b in new]
    parents += [allnames.index(b["parent"]) for b in new]
    par_v = struct.pack("<I%dh" % len(parents), len(parents), *parents)
    # rig data tail: 48 bytes per bone (pos xyzw, rot xyzw, scale xyzw)
    tail = bytes(c.d[endp:base + e[3]])
    assert len(tail) == 48 * nb, (len(tail), nb)
    tail += b"".join(struct.pack("<12f", *b["pos"], 1.0, *b["rot"], 1, 1, 1, 1) for b in new)
    out = bytearray(c.d[base:base + 1])
    for q in pr:
        name, typ, vo, vs, ho = q
        v = bones_v if name == "bones" else par_v if name == "parentIndices" else bytes(c.d[vo:vo + vs])
        out += c.d[ho:ho + 4] + struct.pack("<I", len(v) + 4) + v
    return bytes(out) + b"\0\0" + tail

if __name__ == "__main__":
    main()
