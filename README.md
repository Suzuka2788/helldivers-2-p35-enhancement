# Suzuka‘s P35 enhancement

A Helldivers 2 P-35 Re-Educator mod that replaces its darts with delayed gas speargun heads, with reduced direct damage and adjustable magazine capacity.

## Features

- Direct damage: **163 normal / 69 durable**, medium armor penetration (AP3).
- Native gas speargun projectile behavior and **0.5-second delayed detonation**.
- **3-round magazine by default**, selectable **2–6 rounds** through Mod Menu. Apply and reload to use the new capacity. Existing saved menu choices are preserved.
- P-35-specific damage changes; native S-11 Speargun damage remains unchanged.
- Speargun assets load with the P-35, without carrying the S-11.
- Compatible with **Suzuka's impact gas grenade v1.6.1, including preview1**. Shared audio comes from that mod.

## Requirements

1. [Bingus Shared Loader](https://github.com/CowboyBingus/BingusSharedLoader) v15+ / API 1.
2. [Suzuka's impact gas grenade](https://github.com/Suzuka2788/helldivers-2-impact-gas-grenade) **v1.6.1** (including preview1), enabled alongside this mod.
3. A Mod Menu providing ModOptionsMenu API 1 to adjust capacity. Without the menu, capacity defaults to 3.

**This release requires the G-16 mod above.** It is not a standalone asset package.

## Install

Close the game. Download `Suzukas-P35-enhancement-v1.0.0.zip` from Releases and import it into your mod manager. Disable all previous P-35 enhancement preview packages, enable the requirements above, and deploy. Do not enable multiple versions together.

Menu: **Suzuka‘s P35 enhancement → Magazine capacity**. If an old saved choice is 6, select 3 and press APPLY. Reload afterward.

Log: `%LOCALAPPDATA%\CowboyBingus\Helldivers2\Logs\TongzP35GasSpeargun.log`.

Uninstall with the game closed by disabling this mod and redeploying.

## Validation and limitations

v1.0.0 packages the reviewed preview9 implementation with the release name. 17 offline tests cover damage isolation, safe restoration, default/menu magazine capacities, resource completeness and no shared resource identities with the two G-16 v1.6.1 packages. Full packed Lua and ZIP checks pass. Reduced scan work spreads startup loading over more frames; no measured FPS improvement is claimed.

The user confirmed preview2's gas speargun behavior in game. The final optimized release has not yet been independently validated in game. Game updates, mods that change P-35 records/packages, or incompatible loader/menu versions may cause safe refusal to apply. Memory writes are guarded by resource, record, context and readback checks. Partial-write failure recovery and shutdown error reporting have remaining review limitations; see the included review.

## Credits

Uses [Bingus Shared Loader](https://github.com/CowboyBingus/BingusSharedLoader). Game assets were extracted from the installed game with [FileDiver](https://github.com/xypwn/filediver). Original game assets belong to their respective owners.

---

中文：将 P-35 飞镖替换为延时毒气矛枪头，直击伤害 163/69、AP3，默认 3 发，菜单可选 2–6 发。仅修改 P-35，不改变原版毒矛伤害。**需同时启用 G-16 毒气冲击雷 v1.6.1（含 preview1）和 BSL**。关闭游戏后替换旧版、重新部署。最终优化发布版尚待独立实机验证。
