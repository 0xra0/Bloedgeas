"""Read/write Witcher 3 .w3strings (port of WolvenKit-7 W3StringFile.cs).

  write(path, lang, [(id, key, text), ...])     read(path) -> (lang_key, [(id, text)], {keyhash: id})
Layout: 'RTSW', u32 version, u16 key1, bit6 count + (id^magic, offset, len) per string (sorted by
hashed id), bit6 count + (keyhash, id^magic) per key (sorted by hash), bit6 buffer length, the
XOR-scrambled strings (each 0-terminated), u16 key2. Version 162 (classic) stores UTF-16 code units;
163 (next-gen, e.g. Ard Bombs) stores UTF-8 bytes, scrambled with the low byte of the same key
schedule, and counts offsets/lengths in bytes. Keys let XML name a string
(localisation_key_name); the hash is Java-style h*31+c over the key's chars.
"""
import struct

LANGS = {  # handle: (key, magic)
    "ar": (0, 0), "br": (0, 0), "esMX": (0, 0), "kr": (0, 0), "tr": (0, 0),
    "pl": (0x83496237, 0x73946816), "en": (0x43975139, 0x79321793), "de": (0x75886138, 0x42791159),
    "it": (0x45931894, 0x12375973), "fr": (0x23863176, 0x75921975), "cz": (0x24987354, 0x21793217),
    "es": (0x18796651, 0x42387566), "zh": (0x18632176, 0x16875467), "ru": (0x63481486, 0x42386347),
    "hu": (0x42378932, 0x67823218), "jp": (0x54834893, 0x59825646),
}


def bit6(c):
    if c == 0:
        return b"\x80"
    out, left, i = [], c, 0
    while left > 0:
        out.append(left & 63 if i == 0 else left & 255)
        left >>= 6 if i == 0 else 7
        i += 1
    for i in range(len(out) - 1):
        if len(out) - 1 - i >= 1 and i >= 1:
            out[i] |= 128
        else:
            out[i] |= 64 if out[i] < 64 else 128
    return bytes(out)


def read_bit6(d, o):
    res = shift = 0; i = 1
    while True:
        b = d[o]; o += 1
        mask, s = (127, 7) if b > 127 else ((63 if i == 1 else 255), 6) if b > 63 else (255, 6)
        res |= (b & mask) << shift; shift += s; i += 1
        if b < 64 or (i >= 3 and b < 128):
            return res, o


def keyhash(k):
    h = 0
    for c in k:
        h = (h * 31 + ord(c)) & 0xFFFFFFFF
    return h


def scramble(s, magic):
    sk = (magic >> 8) & 0xFFFF; n = len(s); out = bytearray()
    for ch in s:
        ck = ((n + 1) * sk) & 0xFFFF
        out += bytes([(ord(ch) & 255) ^ (ck & 255), (ord(ch) >> 8) ^ (ck >> 8)])
        sk = ((sk << 1) | (sk >> 15)) & 0xFFFF
    return bytes(out)


def scramble8(b, magic):
    sk = (magic >> 8) & 0xFFFF; n = len(b); out = bytearray()
    for x in b:
        out.append(x ^ (((n + 1) * sk) & 255))
        sk = ((sk << 1) | (sk >> 15)) & 0xFFFF
    return bytes(out)


def write(path, lang, rows, key_magic=None, version=163):
    key, magic = key_magic or LANGS[lang]
    u = 1 if version >= 163 else 2
    buf = bytearray(); ent = []
    for sid, _, text in rows:                       # buffer in the given order, table by hashed id
        enc = scramble8(text.encode("utf-8"), magic) if u == 1 else scramble(text, magic)
        ent.append((sid ^ magic, len(buf) // u, len(enc) // u))
        buf += enc + b"\0" * u
    b1 = sorted(ent)
    tab1 = b"".join(struct.pack("<III", *e) for e in b1)
    b2 = sorted(((keyhash(k), sid) for sid, k, _ in rows if k), key=lambda r: r[0])
    tab2 = b"".join(struct.pack("<II", h, sid ^ magic) for h, sid in b2)
    data = (b"RTSW" + struct.pack("<IH", version, key >> 16) + bit6(len(b1)) + tab1 + bit6(len(b2)) + tab2
            + bit6(len(buf) // u) + bytes(buf) + struct.pack("<H", key & 0xFFFF))
    open(path, "wb").write(data)


def read(path, magic=None):
    d = open(path, "rb").read()
    assert d[:4] == b"RTSW"
    u = 1 if struct.unpack_from("<I", d, 4)[0] >= 163 else 2
    key = struct.unpack_from("<H", d, 8)[0] << 16 | struct.unpack_from("<H", d, len(d) - 2)[0]
    if magic is None:
        magic = next((m for k, m in LANGS.values() if k == key), None)
    n, o = read_bit6(d, 10)
    b1 = [struct.unpack_from("<III", d, o + 12 * i) for i in range(n)]; o += 12 * n
    n2, o = read_bit6(d, o)
    b2 = [struct.unpack_from("<II", d, o + 8 * i) for i in range(n2)]; o += 8 * n2
    _, o = read_bit6(d, o)
    out = []
    for hid, off, ln in b1:
        raw = d[o + u * off:o + u * off + u * ln]
        if magic is None:
            out.append((hid, None)); continue
        if u == 1:
            out.append((hid ^ magic, scramble8(raw, magic).decode("utf-8", "replace"))); continue
        s = scramble("".join(chr(raw[2 * i] | raw[2 * i + 1] << 8) for i in range(ln)), magic)  # XOR is symmetric
        out.append((hid ^ magic, "".join(chr(s[2 * i] | s[2 * i + 1] << 8) for i in range(ln))))
    return key, out, {h: sid ^ (magic or 0) for h, sid in b2}
