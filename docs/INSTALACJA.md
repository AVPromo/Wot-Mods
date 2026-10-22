# Stay Sharp Medkit Reminder 1.6.0 — installation and testing

## Behavior

Displays an orange gradient frame around the medkit, brightening for two seconds and fading for two seconds. It runs only during battle when the player's vehicle has the active perk effect allowing medkit use, the medkit is ready and the HUD is visible. It does not activate the medkit, play sounds or change game statistics.

## Installation

1. Close World of Tanks.
2. Keep a backup of the confirmed working version 1.5.0 outside `mods`.
3. **Remove the old 1.5.0 file from the active `mods/<game_version>/` directory.** Two versions of the same mod must not run together.
4. Copy `com.staysharp.medkitreminder_1.6.0.wotmod` into the game directory, for example `C:\Games\World_of_Tanks_EU\mods\2.4.1.0\`. Use the current client-version directory if an update changed its name.
5. Start the game normally.

No separate `.py`, `.dds`, `.swf`, shaders, sound banks or DLLs are needed. The `.wotmod` contains `meta.xml`, a `.pyc` and all 21 DDS frames under WoT resource paths.

## In-game checks

- No frame should appear before the countdown or during configuration selection.
- After battle starts, a ready medkit on a vehicle with the relevant perk should pulse in a four-second cycle.
- Check arcade, sniper, top-down artillery and trajectory views.
- The frame should disappear after medkit use and during cooldown, then return when ready.
- Native crew-injury warnings and WoT highlighting should take priority.
- Leaving battle should remove the frames and stop their animation.

## Diagnostics

The local log is written to:

`%LOCALAPPDATA%\StaySharpMedkit\staysharp.log`

Useful entries:

- `v1.6.0 loaded; component events` — game-event subscriptions installed.
- `battle panel populated` — component discovered through registration events, without replacing methods.
- `HUD registration rejected: ...` — incompatible client/layout; graphics remain disabled.
- `equipment state=incompatible_hud_...` — unexpected mid-battle change; the frame is disabled.
- `GFX disabled by compatibility preflight: ...` — required renderer interface unavailable.
- `overlay mounted: hud_child` — overlay attached below the HUD component.
- `overlay mounted: gui_root` — legacy graphical fallback when the HUD component is unavailable.
- `PULSE alive` — animation frames are still being updated.

If the game exits unexpectedly, **remove 1.6.0**, return to the verified 1.5.0 version and provide the end of the log for diagnosis. Offline checks do not replace a real WoT client test.

## WoT updates

If the API is unchanged, moving the same `.wotmod` to the new `mods/<game_version>` directory is sufficient. Changed HUD structures or APIs should disable the mod without guessing frame placement, and may require a mod update. The `.pyc` uses CPython 2.7 bytecode matching the verified client; a different interpreter requires rebuilding.
