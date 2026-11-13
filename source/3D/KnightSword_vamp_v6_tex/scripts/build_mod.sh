#!/bin/sh
# Cook + texture cache + pack + metadatastore the vampire sword mod with REDkit's wcc_lite under wine.
#   build_mod.sh <work dir> [install]
# <work dir>/depot holds the uncooked files at their depot paths (meshes from wcc import, xbms from
# w3_xbm.py); <work dir>/wcc_ov is the scratch overlay (bin + r4data union incl. depot, see mk_overlay.py),
# so buildcache finds the xbms in the local depot. Produces <work dir>/build_<time>/modVampSword/content/;
# "install" copies it into the game's mods folder (over an older copy; nothing is deleted).
set -eu
B=$(cd "$1" && pwd)
GAME="/mnt/ssd/Games/The Witcher 3 Wild Hunt Remastered/game/game"
PFX=/mnt/ssd/Codex/2026-10-12/i-x20/witcher3-romance-mod/work/wcc_prefix
MOD=modVampSword
O=$B/build_$(date +%H%M%S)

if pgrep -x witcher3.exe >/dev/null; then echo "witcher3.exe is running; not building" >&2; exit 1; fi
win() { printf 'Z:%s' "$(printf %s "$1" | tr / '\\')"; }
mkdir -p "$O/cooked" "$O/pack_in" "$O/$MOD/content"

cd "$B/wcc_ov/bin/x64_RedKit"
export WINEPREFIX=$PFX WINEDEBUG=-all
# headless: wcc_lite always logs a Halt assert (depotDirectory.cpp) and would block on its dialog
wcc() { env -u DISPLAY -u WAYLAND_DISPLAY timeout 900 nice wine wcc_lite.exe "$@"; rc=$?; wineserver -k || true; return $rc; }
wcc cook -platform=pc "-mod=$(win "$B/depot")" "-outdir=$(win "$O/cooked")" > "$O/cook.log" 2>&1 || true
# buildcache must not get -basedir (REDkit's split depot refuses the remap); it reads the local depot
wcc buildcache textures -platform=pc "-db=$(win "$O/cooked/cook.db")" "-out=$(win "$O/$MOD/content/texture.cache")" > "$O/cache.log" 2>&1 || true
for d in "$O/cooked"/*/; do cp -r "$d" "$O/pack_in/"; done
wcc pack "-dir=$(win "$O/pack_in")" "-outdir=$(win "$O/$MOD/content")" > "$O/pack.log" 2>&1 || true
wcc metadatastore "-path=$(win "$O/$MOD/content")" > "$O/meta.log" 2>&1 || true

echo "cooked: $(find "$O/cooked" -type f ! -name cook.db | wc -l) files"
grep -h "Error\]\[WCC\]" "$O"/*.log || true
ls -la "$O/$MOD/content"

if [ "${2:-}" = install ]; then
    mkdir -p "$GAME/mods"
    cp -r "$O/$MOD" "$GAME/mods/"
    echo "installed -> $GAME/mods/$MOD"
fi
