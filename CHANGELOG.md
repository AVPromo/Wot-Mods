# Changelog

## 1.6.1 (first GitHub publication candidate, PR #1 fixes)

- Fix Windows log rotation when the `.old` backup already exists; also rotate logs during long sessions.
- Fail closed on existing mismatched release tags and wrong SHA-256 assets.
- Make GitHub Releases resumable after interrupted draft creation or partial upload.
- Stop forcing future builds to reproduce the original v1.6.0 checksum.
- Verify the master DDS against its own reviewed SHA-256 file so artwork can be updated in later PRs.
- Add offline regression tests for failed/draft/published release states and Windows log rotation.

## 1.6.0 (historical baseline, not published by this PR)

- Event-based registration/unregistration of the battle consumables panel, without monkeypatching WoT methods.
- Explicit state checks for player vehicle ID and medkit readiness in arcade/sniper/arty views.
- HUD compatibility validation and safe disabling on unknown layout.
- Identical 21 DDS frames with 2-second ramp-up + 2-second fade, no sound.
- Existing offline tests and release-packaging pipeline.

Later releases are generated for **each push to `main`** after a reviewed merge; GitHub Releases contains the corresponding commit-based change notes.

### GitHub Releases automation (pending PR #4)
- Replaced the bespoke GitHub HTTP/REST publisher with first-party `gh release` commands.
- Verify exact Git tags and real downloaded Release files using Git and SHA-256.
- Explicitly detect incomplete draft releases; recovery deletes only the draft and recreates it from the original tag.
