Bloedgeas is a vampire-themed relic steel sword for **The Witcher 3: Wild Hunt — Remastered 5.01c**.

This initial GitHub release includes the custom v6 sword and scabbard, rune artwork, icon and localized description, a 35% human-target bleed chance, combat regeneration, custom randomized sounds, low-health glow/heartbeat, and automatic level scaling.

### Download and install

Download **Bloedgeas-v1.0.0-Witcher3-5.01c.zip**, extract it, and copy its **mods/** and **dlc/** folders to the game root (beside **bin/** and **content/**). Keep all three components: **modVampSword**, **dlcvampsword**, and the bundled **modGearLevelScaling** compatibility snapshot. A compatible **TW3SE** installation is required separately. Hearts of Stone supplies the life-drain effect asset. Review script conflicts if other mods override playerWitcher.ws or inventoryComponent.ws.

Enable the debug console and spawn the sword with:

```text
additem('Bloedgeas')
```

Equip it as your steel sword. [Full installation, usage, compatibility, and troubleshooting instructions](https://github.com/0xra0/Bloedgeas#installation).

### Scaling correction and current behavior

The preserved in-game verification records an existing sword scaling from **level 42 to 54**, with base damage rising from **369 to 465** (+96), 12 tracked upgrades, and zero compiler errors. The current script updates inventory copies every half second and retains the scaler's upgrade tracking.

Healing is a fixed **0.4% maximum vitality per second** while drawn in combat. Below 30% vitality, glow and heartbeat activate; the stronger low-health healing described in the lore text is not yet implemented. Bloedgeas shares the Dwarven sword 1 model/scabbard replacement paths, so that vanilla sword also changes appearance.

### Integrity and validation

**SHA256SUMS** attached here verifies the installation ZIP. The ZIP contains its own SHA256SUMS for the runtime files and README. Packaging checks validate required files, ZIP integrity, and byte-for-byte payload equality. The in-game result above is retained historical evidence, not a new playtest of every effect or mod combination.

The automatic GitHub source archives contain development assets; use the named installation ZIP to play. See the repository's [development notes](https://github.com/0xra0/Bloedgeas/blob/main/docs/DEVELOPMENT.md) and [changelog](https://github.com/0xra0/Bloedgeas/blob/main/docs/CHANGELOG.md) for more detail.
