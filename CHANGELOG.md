# v1.2.0

- Release based on preview22, retaining native gas / EMS switching, shared ammunition, 163/69 direct damage (AP3) and 0.5-second delayed detonation.
- Replace separate magazine modes with capacity 1–6 (default 1) and spare magazines 1–6 (default 5). Capacity 1 uses the S-11 reload threshold; held weapons refill to the new spare limit on resupply, and new spawns fully apply the setting.
- Add EMS field size 50% (default) / 100%, synchronizing explosion range, persistent blue smoke and airborne electric arc strips. At 50%, ranges are 0.5 / 5 / 6 m instead of 1 / 10 / 12 m.
- EMS field size also affects the EMS Mortar Sentry. Changes are local; another player's resolution uses their original values and their visuals are unaffected.
- Load packaged 50% effects and synchronize loaded effects in batches, reacquiring them after mission changes. Exit restores packaged 50% values.
- Use new menu IDs; old saved magazine/range choices are not carried over.
- Keep GP-31 unmodified and retain existing loader, G-16 and menu dependencies.
- 49 offline tests pass. The author confirmed preview22 in-game magazine/spare settings and EMS 50% / 100% range and blue-effect switching.
- Earlier preview12 performance logs measured 19 µs average per frame and 0.97 ms maximum; no new performance benchmark is claimed.

# v1.1.0

- Add native gas / EMS ammo switching with a shared magazine: flechette icon for gas, stun icon for EMS.
- Both modes retain the speargun projectile body, 163/69 direct damage (AP3) and 0.5-second delay; EMS replaces the delayed gas explosion.
- Add Magazine mode (2–6 rounds, default 3, original 2 spares) and Single load mode (1 round per reload, 1–6 spares, default 6). Held weapons refill to the new limit on resupply; new spawns fully apply the setting.
- Remove GP-31 modifications to avoid overlap with Contact Detonation Repair.
- Retain Bingus Shared Loader v15+ / API 1, Suzuka's impact gas grenade v1.6.1 (including preview1), and ModOptionsMenu API 1 requirements.
- Retain startup and polling performance improvements. Preview12 in-game logs measured 19 µs average per frame and 0.97 ms maximum.
- Release based on preview12, without the preview13 EMS radius option. 35 offline tests pass; separate in-game validation of this release has not been recorded.

# v1.0.0

- Release packaging and branding: Suzuka‘s P35 enhancement.
- Includes preview9's bounded startup scan and alias table cache.
- P-35 damage 163/69, AP3, native delayed gas behavior.
- Default 3 rounds; Mod Menu choices 2–6.
- G-16 v1.6.1 compatibility through shared audio dependency.
- 17 offline regression tests pass; final gameplay verification remains pending.
