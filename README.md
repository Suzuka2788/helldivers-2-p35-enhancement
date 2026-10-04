# Suzuka‘s P35 enhancement v1.1.0

A Helldivers 2 P-35 Re-Educator mod with delayed gas / EMS darts, native ammo-mode switching and adjustable magazine settings.

## Features

- Switch gas / EMS heads through the native weapon menu: **gas = flechette icon; EMS = stun icon**. Both modes share the magazine.
- Both modes retain the speargun projectile body and flight behavior, **163 normal / 69 durable direct damage (AP3)** and **0.5-second delayed detonation**. EMS mode replaces the delayed gas explosion with an EMS explosion.
- P-35-specific direct damage changes; native S-11 Speargun direct damage remains unchanged. Speargun assets load with the P-35 without carrying the S-11.
- **Magazine** mode: capacity **2–6**, default **3**; the original **2 spare magazines** are retained. Apply and reload to use the new capacity.
- **Single load** mode: load **1 round** at a time; spare magazines **1–6**, default **6**. Weapons already held refill to the new limit when resupplied; the setting takes full effect the next time a weapon is spawned.
- GP-31 is no longer modified, avoiding overlap with **Contact Detonation Repair**.
- Compatible with **Suzuka's impact gas grenade v1.6.1, including preview1**. Shared audio comes from that mod.

## Requirements

1. [Bingus Shared Loader](https://github.com/CowboyBingus/BingusSharedLoader) v15+ / API 1.
2. [Suzuka's impact gas grenade](https://github.com/Suzuka2788/helldivers-2-impact-gas-grenade) **v1.6.1** (including preview1), enabled alongside this mod.
3. A Mod Menu providing **ModOptionsMenu API 1** to adjust magazine mode, capacity, spare magazines settings.

**This release requires the G-16 mod above.** It is not a standalone asset package.

## Install

Close the game. Download `Suzukas-P35-enhancement-v1.1.0.zip` from Releases and import it into your mod manager. Disable all previous P-35 enhancement packages, enable the requirements above, and deploy. Do not enable multiple versions together.

Menu: **Suzuka‘s P35 enhancement**. Existing saved menu choices are preserved. Select the desired settings and press APPLY; reload after changing magazine capacity.

Log: `%LOCALAPPDATA%\CowboyBingus\Helldivers2\Logs\TongzP35GasSpeargun.log`.

Uninstall with the game closed by disabling this mod and redeploying.

## Validation and limitations

**35 offline tests pass** across magazine settings, fixed projectiles, Lua runtime, native ammo menu, startup, performance and asset packaging. ZIP integrity, unchanged GUID, packed version `1.1.0` and absence of `grenade_pistol` content were checked.

This release is based on preview12. Performance logs from preview12 measured **19 µs average per frame and 0.97 ms maximum**; these are earlier in-game measurements, not a new v1.1.0 benchmark or an FPS claim. The author previously confirmed preview13 in-game testing of default 50% EMS radius, single-round loading and restoration on exit; that confirmation does not validate this preview12-based package. Separate in-game validation of this release has not been recorded.

Game updates, mods that change the same records/packages, or incompatible loader/menu versions may cause safe refusal to apply.

## Credits

Uses [Bingus Shared Loader](https://github.com/CowboyBingus/BingusSharedLoader). Game assets were extracted from the installed game with [FileDiver](https://github.com/xypwn/filediver). Original game assets belong to their respective owners.
