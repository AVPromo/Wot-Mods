# Independent mod builds; one shared Releases page

**Builds are per mod, Releases are full immutable snapshots.**

Stay Sharp's `.github/workflows/release.yml` only runs on changes to
Stay Sharp's own source, texture, version, builder or release machinery.
Changes to `mods/sessionstats/**`, language files, repository README or
unrelated mods do **not** build Stay Sharp or increase its version.

## Copy last known-good build instead of recompiling

`scripts/release_snapshot.sh` invokes only the official GitHub CLI and
standard Unix utilities. It:

1. Finds the repository-wide **Latest** published **immutable** Release.
2. Downloads its assets and verifies the entire `SHA256SUMS.txt` manifest.
3. Omits the prior files **owned by the mod currently being rebuilt**.
4. Copies all other files byte-for-byte, without invoking any other mod's
   compiler, npm installation, Python runtime or test suite.
5. Recalculates one `SHA256SUMS.txt` covering **all** assets in the new snapshot.

The publishing job then creates a new release with `gh release create --latest`
and downloads every attachment to verify its exact bytes. No GitHub REST
publisher, custom HTTP, API key, PAT, Java, or deletion of older Releases.

If there are no previous stable Releases, the first one contains only the
changed mod. If the previous snapshot is mutable, incomplete, corrupt, or has
unlisted assets or colliding names, publication fails closed.

## Adding another mod to the same repository

- Give each mod its own subtree (for example `mods/sessionstats/**`), version,
  independent GitHub Actions CI/release workflow, and tag prefix.
- Each release workflow must have narrowly scoped `on.push.paths`, so only
  that mod's changes trigger its compiler.
- The new mod's publishing job should call the same snapshot helper with
  ALL of its own asset glob patterns, for example:

  ```bash
  bash scripts/release_snapshot.sh mods/sessionstats/dist \
    'grz.sessionstats_*.wotmod' \
    'wot-statystyki-sesji-v*.zip' \
    'net.openwg.gameface_*.wotmod' \
    'grz.sessionstats.json' \
    'BUILD.json'
  ```

- **Every** publisher must share the workflow concurrency group
  `wotmod-release-${{ github.repository }}`, with `cancel-in-progress: false`,
  to serialize snapshots. An isolated lock on only one mod is not sufficient.
- Give each additional mod a native tag protection ruleset matching its own
  tag prefix (for example `sessionstats-v*`). Do not weaken Stay Sharp's
  existing `v*` ruleset; keep immutable releases enabled.
- Asset filenames must be unique across mods. Each release replaces only
  its own files; it never uploads two `SHA256SUMS.txt` files.

**Important:** PR #2 still contains the older Session Stats publisher
importing a now-removed `scripts/publish_release.py` and calls the Stay Sharp
builder. PR #2 must be updated to this native independent/snapshot scheme
before merging; PR #3 is stacked on it. Do not merge PR #2 unmodified.

## Pull-request checks

GitHub's `pull_request.paths` filter skips Stay Sharp CI for unrelated mods.
Path-filter-skipped required checks can remain Pending and block a merge.
If adding branch protection, use an always-running required gate/check rather
than requiring mod-specific checks that may be skipped.

The repository-wide `/releases/latest` points to the latest snapshot, while
a mod's tags still identify which mod was actually rebuilt. Download the
desired mod by its unique asset filename.
