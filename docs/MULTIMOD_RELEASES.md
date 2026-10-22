# One WotMods repository: independently built mods, consistent shared Releases

## Scope

Stay Sharp's workflow only builds on changes to its own sources, assets, version,
packaging or workflow. A change in `mods/sessionstats/**` (including languages),
README, or another mod does **not** rebuild Stay Sharp. Each mod has its own
version series, build job, tests and workflow. GitHub has one Releases page and
one repository-wide `/releases/latest` pointer. Each *published* Release is a
complete immutable snapshot of all mod artifacts known at publication time.

## Publishing without cross-mod rebuilds

1. Build and test the changed mod **in its own read-only job**. Upload its
   freshly built files with GitHub's first-party `actions/upload-artifact`.
2. The publish job waits for the common mutex used by **every** mod publisher.
   Jobs that are only building do not hold this mutex.
3. **Inside that mutex**, fetch the repository-wide Latest published immutable
   Release, download all its files and validate the complete `SHA256SUMS.txt`.
4. Compare the *versioned primary package* of the updated mod with the one in
   the current Latest. If Latest already contains a **newer** version, skip
   the older job (exit status `75` is explicitly converted into a successful
   no-op). If versions are equal, verify the package bytes match; equal
   versions with different bytes fail closed.
5. Replace only the current mod's old files; copy every other mod's published
   package and configuration **byte-for-byte**, without invoking its builder.
   Recreate the global checksum manifest, publish a new GitHub Release and
   verify all uploaded bytes while **still holding the mutex**.

### Required mutex across ALL release workflows

```yaml
jobs:
  publish:
    needs: build
    if: github.ref == 'refs/heads/main'
    concurrency:
      group: wotmod-release-${{ github.repository }}
      queue: max
      cancel-in-progress: false
    # ... fetch current Latest, assemble snapshot, publish, verify ...
```

`queue: max` is officially supported in GitHub Actions since May 2026; it
allows up to 100 pending jobs rather than silently replacing an older pending
publication. **Do not** place this shared mutex on the *entire workflow*, or
builds of different mods will be serialized unnecessarily. The group must
cover the entire critical section: latest lookup → carry-forward → upload →
post-upload verification. Every new mod's publisher must use **exactly** the
same group and options. The GitHub queue is FIFO by when each job starts
*waiting*, not necessarily by merge order; the primary-artifact SemVer guard
prevents older builds of the **same** mod from rolling newer ones back.

GitHub queues up to 100 pending jobs, not an unlimited number. Failed jobs
remain visible as failures; successful publication of a different mod cannot
recover a failed build. Do not configure `cancel-in-progress: true`.

### Two fast merges, in either order

Suppose the initial Latest contains A0+B0, merge A builds A1, and merge B
builds B1. The two builds can complete in any order, **but publishing is
serialized**:

- **A publishes first:** A1+B0, then B snapshots that Latest and publishes A1+B1.
- **B publishes first:** A0+B1, then A snapshots that Latest and publishes A1+B1.

The resulting Latest contains both changes without recompiling the unchanged
mod. If an older build A1 reaches publication after a newer A2, it skips
instead of replacing A2 with A1; equal-version mismatches fail safely.

## Adding Session Stats and additional mods

The common helper interface is:

```bash
bash scripts/release_snapshot.sh DIST PRIMARY_FILE PRIMARY_GLOB [OTHER_OWNED_GLOBS...]
```

For Stay Sharp:

```bash
bash scripts/release_snapshot.sh dist \
  "com.staysharp.medkitreminder_${RELEASE_VERSION}.wotmod" \
  'com.staysharp.medkitreminder_*.wotmod'
```

For Session Stats (after PR #2 is updated to this model):

```bash
bash scripts/release_snapshot.sh mods/sessionstats/dist \
  "grz.sessionstats_${SESSIONSTATS_VERSION}.wotmod" \
  'grz.sessionstats_*.wotmod' \
  'wot-statystyki-sesji-v*.zip' \
  'net.openwg.gameface_*.wotmod' \
  'grz.sessionstats.json' \
  'BUILD.json'
```

Every mod needs its own `on.push.paths`, independent version tags and native
GitHub tag-protection Ruleset for its prefix. The root SHA256SUMS.txt is always
recreated for the complete snapshot, and release filenames must not collide.

**Merge dependency:** PR #2 for Session Stats currently uses the removed
`scripts/publish_release.py`, has a non-serialized publisher and invokes Stay
Sharp's builder. **Do not merge PR #2 as it stands.** First integrate PR #5,
then update PR #2 to this same job-level `queue: max` mutex and helper,
without triggering Stay Sharp's builder. PR #3 is stacked on PR #2. Only
then will A/B simultaneous-merge behavior be consistently protected.

## Testing and operating limits

`tests/test_release_snapshot.py` checks A→B and B→A snapshot assembly using
two separately prebuilt versions, stale and duplicate version guards, asset
hashes, immutable sources, corrupt/missing manifests and name collisions.
`tests/test_release_scoping.py` checks the shared **publish-job** mutex and
that the stale skip happens before tag/Release creation.

The read/modify/publish process is serialized among cooperating GitHub Actions
jobs, not against a repository administrator manually publishing a release
outside those workflows. Immutable Releases and protected tags limit tampering;
workflow runs should be monitored. A snapshot does not silently repair a
release that failed to build or publish. CI and local tests cannot guarantee
runtime compatibility in the World of Tanks client.

**Required PR check note:** Path-filter-skipped checks may be Pending if
configured as required. Use an always-running required gate rather than
requiring a check that is intentionally skipped for unrelated mods.
