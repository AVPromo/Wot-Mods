# Changelog

## 1.6.0 (initial GitHub publication candidate)

- Event-based registration/unregistration of the battle consumables panel, without monkeypatching WoT methods.
- Explicit state checks for player vehicle ID and medkit readiness in arcade/sniper/arty views.
- HUD compatibility validation and safe disabling on unknown layout.
- Identical 21 DDS frames with 2-second ramp-up + 2-second fade, no sound.
- Existing offline tests and release-packaging pipeline.

Later releases are generated for **each push to `main`** after a reviewed merge; GitHub Releases contains the corresponding commit-based change notes.
