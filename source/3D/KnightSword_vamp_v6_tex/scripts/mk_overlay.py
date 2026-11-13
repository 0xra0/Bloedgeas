"""Scratch wcc overlay: bin -> real overlay bin, r4data = symlink union of the real r4data plus extra trees."""
import os, sys
src, dst, extras = sys.argv[1], sys.argv[2], sys.argv[3:]
os.makedirs(dst, exist_ok=True)
if not os.path.lexists(f"{dst}/bin"):
    os.symlink(f"{src}/bin", f"{dst}/bin")

def union(a, d):
    """Link every entry of dir a into d; descend where d already has a real dir."""
    os.makedirs(d, exist_ok=True)
    for n in os.listdir(a):
        s, t = os.path.join(a, n), os.path.join(d, n)
        if not os.path.lexists(t):
            os.symlink(os.path.realpath(s), t)
        elif os.path.isdir(s) and os.path.islink(t):   # split a linked dir into a real one
            real = os.path.realpath(t); os.unlink(t); union(real, t); union(s, t)
        elif os.path.isdir(s) and os.path.isdir(t):
            union(s, t)

union(f"{src}/r4data", f"{dst}/r4data")
for e in extras:
    union(e, f"{dst}/r4data")
print("ok", dst)
