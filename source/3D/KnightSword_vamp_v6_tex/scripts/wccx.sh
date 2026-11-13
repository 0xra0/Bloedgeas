#!/bin/sh
# wccx.sh <work dir> <logfile> <args...> — wcc_lite with a real D3D12 device, for native texture import:
#   wccx.sh ../mod /abs/imp.log import -depot=local -file=Z:\..\x.png -out=Z:\..\x.xbm -texturegroup=WorldDiffuse
# Private Xvfb display + RADV + wine-staging's vkd3d forced to feature level 12.0; <work dir>/pfx is a wine
# prefix with an NVIDIA vendor-id spoof (vendor.reg). Dialog windows are logged to <logfile>.win (+ .xwd shots).
# The "Not implemented / open heap" log errors are harmless.
B=$(cd "$1" && pwd); log=$2; shift 2
if pgrep -x witcher3.exe >/dev/null; then echo "witcher3.exe running" >&2; exit 1; fi
Xvfb :77 -screen 0 1280x1024x24 -nolisten tcp >/dev/null 2>&1 & XP=$!
sleep 2
cd "$B/wcc_ov/bin/x64_RedKit"
export VK_DRIVER_FILES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json
export VKD3D_CAPS_OVERRIDE=feature_level=12.0 WINEPREFIX=$B/pfx WINEDEBUG=-all DISPLAY=:77
env -u WAYLAND_DISPLAY timeout 900 nice wine wcc_lite.exe "$@" > "$log" 2>&1 & WP=$!
: > "$log.win"
while kill -0 $WP 2>/dev/null; do
  for w in $(xdotool search --onlyvisible --name . 2>/dev/null); do
    n=$(xdotool getwindowname $w 2>/dev/null)
    grep -qxF "$w $n" "$log.win" || { echo "$w $n" >> "$log.win"; xwd -display :77 -root -silent > "$log.$w.xwd" 2>/dev/null; }
  done
  sleep 3
done
wait $WP; rc=$?
wineserver -k 2>/dev/null || true
kill $XP 2>/dev/null
grep -E "\[(Info)\]\[WCC\]|Error\]\[(WCC|Assert)" "$log" | grep -v -- '-----\|soundFile\|depotDirectory' | tail -8
echo "windows:"; cat "$log.win"
exit $rc
