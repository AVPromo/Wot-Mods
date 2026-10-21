# PR #1 review fixes (2026-10-21)

Review source: https://github.com/Szwarceneger16/WotMods/pull/1#pullrequestreview-5605202965

## P1 — interrupted Release (review `4341132571`)

Replaced the one-shot `gh release create <tag> <assets>` with `scripts/publish_release.py`: explicit tag, draft creation, resumable asset upload, digest/size/name validation, publication and post-publication checks. Failed uploads leave a resumable draft. Published releases are never overwritten, and incomplete published releases fail the job.

## P1 — existing wrong-commit tag (review `4341132577`)

Every publication resolves the tag to its final commit (including annotated tag objects) and compares it to the checked-out `GITHUB_SHA`. It fails before uploading on mismatch. A matching tag without a release can be used to safely create a release.

## P1 — future builds blocked by original v1.6.0 hash (review `4341132583`)

Historical package SHA-256 is only checked when `VERSION == 1.6.0`. The baseline was advanced to `1.6.1` to account for changed runtime logging. Future source changes build and test normally. A separate reviewed checksum accompanies the DDS master rather than hardcoding an old art hash into production code. CI derives the next patch from `scripts/release_version.py` instead of an unconditionally fixed `1.6.1`.

## P2 — Windows log rotation (review `4341132561`)

Rotation removes the old `.old` backup before calling Python 2.7-compatible `os.rename`. Rotation is checked on every write, so long battles cannot grow the active log without limit. A failed rename triggers a best-effort truncate of the active log rather than indefinite growth. This is intentionally a small runtime change; visuals, controls and effects are unchanged.

## Regression coverage

- `tests/test_release_publication.py` mocks GitHub for create/retry/corruption/rollback guard/tag mismatch/integrity, with no GitHub writes.
- `tests/test_log_rotation.py` reproduces Windows non-overwriting rename behavior and a locked backup scenario.
- Existing mod/HUD and packaging tests are retained; assets are not modified.

This tests the logic and packaging **offline**. Real GitHub Releases are not created until the PR has passed review and been merged. Live WoT rendering of the updated runtime remains to be confirmed.
