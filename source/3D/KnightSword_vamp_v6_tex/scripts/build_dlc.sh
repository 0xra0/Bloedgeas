#!/bin/sh
# Pack the dlcvampsword DLC (Bloedgeas item) and install it with its script.
#   build_dlc.sh <mod work dir> <dlc work dir> [install]      e.g. build_dlc.sh mod dlc_src install
# <dlc work dir> comes from mk_dlc.py (pack/ = bundle contents, content/ = w3strings + info.json) and holds
# scripts/bloedgeas.ws. wcc_lite runs from <mod work dir>/wcc_ov like build_mod.sh. Installs
#   GAME/dlc/dlcvampsword/content/                 blob0.bundle, metadata.store, *.w3strings, info.json, texture.cache (icon), soundspc.cache
#   GAME/mods/modVampSword/content/scripts/local/  bloedgeas.ws
set -eu
M=$(cd "$1" && pwd); D=$(cd "$2" && pwd)
GAME="/mnt/ssd/Games/The Witcher 3 Wild Hunt Remastered/game/game"
PFX=/mnt/ssd/Codex/2026-10-12/i-x20/witcher3-romance-mod/work/wcc_prefix
O=$D/build_$(date +%H%M%S)

if pgrep -x witcher3.exe >/dev/null; then echo "witcher3.exe is running; not building" >&2; exit 1; fi
win() { printf 'Z:%s' "$(printf %s "$1" | tr / '\\')"; }
mkdir -p "$O/content"
cd "$M/wcc_ov/bin/x64_RedKit"
export WINEPREFIX=$PFX WINEDEBUG=-all
wcc() { env -u DISPLAY -u WAYLAND_DISPLAY timeout 900 nice wine wcc_lite.exe "$@"; rc=$?; wineserver -k || true; return $rc; }
wcc pack "-dir=$(win "$D/pack")" "-outdir=$(win "$O/content")" > "$O/pack.log" 2>&1 || true
wcc metadatastore "-path=$(win "$O/content")" > "$O/meta.log" 2>&1 || true
cp "$D"/content/* "$O/content/"
[ -f "$D/../audio/build/soundspc.cache" ] && cp "$D/../audio/build/soundspc.cache" "$O/content/"   # from wwise_bank.py + soundcache.py
grep -h "Error\]\[WCC\]" "$O"/*.log || true
ls -la "$O/content"

if [ "${3:-}" = install ]; then
    mkdir -p "$GAME/dlc/dlcvampsword" "$GAME/mods/modVampSword/content/scripts/local"
    cp -r "$O/content" "$GAME/dlc/dlcvampsword/"
    cp "$D/scripts/bloedgeas.ws" "$GAME/mods/modVampSword/content/scripts/local/"
    # TEST: also in the mod's content, in case the game only mounts sound caches from mods/
    [ -f "$O/content/soundspc.cache" ] && cp "$O/content/soundspc.cache" "$GAME/mods/modVampSword/content/"
    # the mod's texture.cache is proven to mount (the sword's textures show), so the icon goes in there as well;
    # merge onto the pristine wcc cache, kept as texture.cache.noicon, so a rerun never doubles the names
    MC="$GAME/mods/modVampSword/content/texture.cache"
    [ -f "$MC.noicon" ] || cp "$MC" "$MC.noicon"
    python3 -I /mnt/ssd/Codex/2026-10-12/i-x20/witcher3-romance-mod/tools/merge_texcache.py "$O/mod_texture.cache" "$MC.noicon" "$O/content/texture.cache"
    cp "$O/mod_texture.cache" "$MC"
    echo "installed -> $GAME/dlc/dlcvampsword + modVampSword/content/scripts/local/bloedgeas.ws"
fi
