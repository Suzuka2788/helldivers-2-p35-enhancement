# Suzuka‘s P35 enhancement v1.2.0

A Helldivers 2 P-35 Re-Educator mod with delayed gas / EMS darts, native ammo-mode switching and adjustable magazine settings.

## Features

- Switch gas / EMS heads through the native weapon menu: **gas = flechette icon; EMS = stun icon**. Both modes share the magazine.
- Both modes retain the speargun projectile body and flight behavior, **163 normal / 69 durable direct damage (AP3)** and **0.5-second delayed detonation**. EMS mode replaces the delayed gas explosion with an EMS explosion.
- P-35-specific direct damage changes; native S-11 Speargun direct damage remains unchanged. Speargun assets load with the P-35 without carrying the S-11.
- **Magazine capacity**: **1–6 rounds**, default **1**. Apply and reload to use the new capacity. At capacity 1, the reload threshold is 0, matching the S-11 Speargun; capacities 2–6 retain the vanilla threshold.
- **Spare magazines**: **1–6**, default **5**. Initial supply, maximum supply and resupply amount match the selected value. Held weapons refill to the new limit on resupply; the setting fully applies to the next weapon spawn. Default loadout: **1 round × 5 spare magazines**.
- **EMS field size**: **50%** (default) or **100%**. At 50%, explosion ranges change from the original 1 / 10 / 12 m to 0.5 / 5 / 6 m, and persistent blue smoke and airborne electric arc strips shrink by half. At 100%, ranges and visuals use their original size.
- EMS field size also affects the **EMS Mortar Sentry**, which shares the explosion and effects. Changes are local; multiplayer resolution by another player uses that player's original values, and other players' visuals are unaffected.
- The package contains 50% effects. During missions, the mod scans loaded effects in batches and synchronizes them to the selected size (`EMS_VISUAL=SYNCED`). It writes only matching packaged content, reacquires effects after mission changes, and restores the packaged 50% values on exit.
- New menu option IDs replace the old saved magazine/range choices. Select your settings again after upgrading.
- GP-31 is no longer modified, avoiding overlap with **Contact Detonation Repair**.
- Compatible with **Suzuka's impact gas grenade v1.6.1, including preview1**. Shared audio comes from that mod.

## Requirements

1. [Bingus Shared Loader](https://github.com/CowboyBingus/BingusSharedLoader) v15+ / API 1.
2. [Suzuka's impact gas grenade](https://github.com/Suzuka2788/helldivers-2-impact-gas-grenade) **v1.6.1** (including preview1), enabled alongside this mod.
3. A Mod Menu providing **ModOptionsMenu API 1** to adjust magazine capacity, spare magazines and EMS field size.

**This release requires the G-16 mod above.** It is not a standalone asset package.

## Install

Close the game. Download `Suzukas-P35-enhancement-v1.2.0.zip` from Releases and import it into your mod manager. Disable all previous P-35 enhancement packages, enable the requirements above, and deploy. Do not enable multiple versions together.

Menu: **Suzuka‘s P35 enhancement**. Old menu choices are not carried over; select your settings again. Select the desired settings and press APPLY; reload after changing magazine capacity.

Log: `%LOCALAPPDATA%\CowboyBingus\Helldivers2\Logs\TongzP35GasSpeargun.log`.

Uninstall with the game closed by disabling this mod and redeploying.

## Validation and limitations

**49 offline tests pass** across EMS radius and visuals, magazine settings, fixed projectiles, Lua runtime, native ammo menu, startup, performance and asset packaging. ZIP integrity, unchanged GUID, packed version `1.2.0` and absence of `grenade_pistol` content were checked.

This release packages the preview22 implementation. The author confirmed in-game testing of magazine capacity and spare magazines, and EMS 50% / 100% range and blue-effect switching. Performance logs from preview12 measured **19 µs average per frame and 0.97 ms maximum**; these are earlier measurements, not a new v1.2.0 benchmark or an FPS claim.

Game updates, mods that change the same records/packages, or incompatible loader/menu versions may cause safe refusal to apply.

## Credits

Uses [Bingus Shared Loader](https://github.com/CowboyBingus/BingusSharedLoader). Game assets were extracted from the installed game with [FileDiver](https://github.com/xypwn/filediver). Original game assets belong to their respective owners.
