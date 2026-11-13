# Source assets and rebuilding

The ready-to-install runtime files in `installed/` are the release authority. Development sources preserve the original workstation pipeline; they are not a portable, one-command REDkit build.

## Package a release

From the repository root, with Python 3 installed:

```sh
python3 scripts/package_release.py --version 1.0.0
```

This creates `dist/Bloedgeas-v1.0.0-Witcher3-5.01c.zip` and `dist/SHA256SUMS`. The archive contains `mods/`, `dlc/`, the README, and an internal checksum list. The packager includes the three named runtime components, excludes `.noicon`, `.log`, and `.bak` files, checks required files, and verifies the archived bytes against the inputs. Archive entry timestamps are fixed for reproducibility.

Verify the downloaded ZIP on Linux with:

```sh
sha256sum --check SHA256SUMS
```

On Windows PowerShell, run `Get-FileHash .\Bloedgeas-v1.0.0-Witcher3-5.01c.zip -Algorithm SHA256` and compare it with the release's checksum file. After extracting, `sha256sum --check SHA256SUMS` from the extraction directory checks the individual runtime files and README.

The root-level `SHA256SUMS` in the original local workspace belongs to the older archive inventory and is intentionally ignored by Git. Use the checksum list delivered with the release.

## Edit gameplay

The runtime WitcherScript is:

```text
installed/mods/modVampSword/content/scripts/local/bloedgeas.ws
```

The corresponding authoring copy is:

```text
source/3D/KnightSword_vamp_v6_tex/dlc_src/scripts/bloedgeas.ws
```

Keep both copies synchronized when editing. The current repository starts with byte-identical copies. Changes to this plain script do not require cooking meshes; they do require compatible TW3SE support and successful game script compilation.

The small functions at the start control bleed chance (0.35), critical vitality threshold (0.30), flare cooldown (2.5 seconds), and regeneration (0.004 of maximum vitality per second). `Bloedgeas_RegenRate` currently ignores its `hpPercent` argument. The comments proposing stronger healing near death describe future work, not current behavior.

`Bloedgeas_ScaleInventory` calls `GLS_ScaleItem` on each inventory copy using valid, enabled sword settings. Keep the `Bloedgeas` eligibility exception in `installed/mods/modGearLevelScaling/content/scripts/local/ItemLevelScaling_main.ws`; the general scaler would otherwise be able to undo these upgrades when its menu options differ. The bundled base-script overrides contain the inventory, equipment, readiness, and level hooks.

## Item and localization source

The authored item XML is under:

```text
source/3D/KnightSword_vamp_v6_tex/dlc_src/pack/dlc/dlcvampsword/data/gameplay/items/def_item_bloedgeas.xml
```

`scripts/mk_dlc.py` inside that v6 directory generates this XML and localization files. Edit its `ITEM_XML` and `STRINGS` constants if regenerating. Editing the loose XML alone does not alter the already packed runtime `blob0.bundle`.

Localization uses ID space **7319** and string IDs based on `2110000000 + idSpace * 1000 + row`. This was selected against the author's installed mod set; other mods can still collide. English and Ukrainian are authored in the generator. The installed snapshot also has English-equivalent fallback files for other languages, but the historical generator's `LANGS` list contains only `en` and `ua`; preserve or regenerate the fallbacks deliberately when rebuilding.

The historical `info.json` contains `gameVersion: "29"`. That is preserved package metadata, not a statement that the release targets patch 29. The release target requested for this repository is **5.01c**.

## Mesh and texture pipeline

The current editable models are `KnightSword_vamp_v6.blend` and `KnightSword_vamp_v6_scabbard.blend`. The v6 texture directory includes source PBR images, rune/sigil artwork, LOD exports, renders, and the `w3/` FBX/texture handoff.

The historical pipeline uses Blender, Python (including NumPy and Pillow where imported), Witcher 3 Blender tools, REDkit's `wcc_lite.exe`, and Wine on Linux. Main stages are:

1. `vamp_geometry.py`, `vamp_shader_v6.py`, and `vamp_pipeline.py`: geometry, shading, and texture baking.
2. `scabbard.py`, `scabbard_shader.py`, and `back_fit.py`: scabbard construction, fit, and skinning.
3. `w3_export.py`: game-axis FBX exports, LOD/collision exports, and Witcher texture conversion.
4. `mk_overlay.py` and `wccx.sh`: workstation REDkit overlay/import helpers.
5. `build_mod.sh`: cooking, texture cache generation, bundles, and metadata.
6. `mk_dlc.py` and `build_dlc.sh`: item definition/localization generation, DLC packing, script installation, and icon-cache merging.

The model uses the vanilla Dwarven sword/scabbard template paths. Changing this reuse strategy requires creating and registering appropriate new entity/template resources; renaming only the inventory item does not isolate the replacement.

## Audio pipeline

`source/wwise/bloedgeas/` contains the standalone Wwise project and work units. The project was built with the Wwise 2023.1 toolchain. Source WAV files are also under the v6 directory's `audio/src/`, and the retained SoundCraft sessions are in `craft-out/`.

The historical `wwise_bank.py` uses WAAPI to generate an embedded-media `bloedgeas.bnk`. `soundcache.py` packages it into the game's sound cache format. Events used by WitcherScript are:

| Event | Purpose |
| --- | --- |
| `Play_bloedgeas_hit` | Randomized hit container with three variants |
| `Play_bloedgeas_bleed` | Randomized bleed sting with two variants |
| `Play_bloedgeas_heartbeat` | Start heartbeat loop |
| `Stop_bloedgeas_heartbeat` | Stop heartbeat loop |

The current runtime includes `soundspc.cache` in both the mod and DLC. Preserve this arrangement unless a focused in-game test establishes that one copy is unnecessary. Both icon caches are also retained.

## Workstation paths and missing external inputs

Before invoking any historical build helper, inspect its constants and shell variables. Several scripts contain absolute paths and optional `install` arguments that copy output directly into the author's game installation.

| Original reference | Adaptation needed |
| --- | --- |
| `/mnt/ssd/ComfyUI/output/3D/` | Point to this checkout's `source/3D/` assets |
| `/mnt/ssd/Codex/2026-10-12/i-x20/witcher3-romance-mod/` | Shared tool imports and Wine/REDkit scratch setup; selected helpers are under `source/support/romance-mod-tools/` |
| `/mnt/ssd/Games/The Witcher 3 REDkit/` | Point to your own REDkit installation |
| `/mnt/ssd/Games/The Witcher 3 Wild Hunt Remastered/game/game` | Point to your game only after reviewing installation steps |
| `/mnt/sata/wwise/prefix/` and `C:\wwproj\bloedgeas` | Configure your own Wwise installation/project paths |

The GitHub source excludes Wine prefixes, scratch overlays, uncooked retail depots, third-party reference mods, generated sound banks, old builds, and earlier sword iterations. Specific historical steps still need external inputs: `mk_dlc.py` references an Ard Bombs `.reddlc` sample; `cr2wbuild.py` imports an external `cr2w` parser; shader helpers reference earlier texture sources; sound synthesis helpers read original REDkit WAVs. Obtain the appropriate tools/assets and adapt the scripts before attempting a full rebuild. The shipped `.blend`, FBX, textures, Wwise source, and cooked runtime remain available independently of those historical steps.

## Verification record

`docs/scaling-verification.json` is the final preserved runtime result from 2026-11-13. It records player level 54, a sword level change from 42 to 54, base damage from 369 to 465, 12 tracked upgrades, no manual scaler command, and zero compiler errors. It is historical evidence from the author's running game, not a playtest performed during GitHub packaging.
