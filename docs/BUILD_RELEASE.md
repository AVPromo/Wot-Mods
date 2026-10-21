# Reproducible build & automated releases

## Source of truth

- `source/mod_staysharp_medkit.py`: versioned WoT CPython 2.7-compatible runtime, currently v1.6.1. The only behavioral change from 1.6.0 is bounded Windows-compatible log rotation. Graphic assets and HUD behavior remain unchanged.
- `assets/medkit_pulse_master.dds.b85`: zlib-compressed Base85 of the original DDS master, without personal metadata. `assets/medkit_pulse_master.sha256` authenticates the decoded bytes. **Update both files together** in a reviewed PR when updating the art.
- `source/build_wotmod.py`: generates 21 DDS frames, a CPython 2.7 bootstrap and one ZIP_STORED `.wotmod`. It uses only the Python standard library.
- `VERSION`: current reviewed baseline, initially `1.6.1`. Change it alongside the literal runtime version and heading if bumping the baseline. The release workflow derives future patch versions from its `run_number`.

Local build (no Wargaming files, private data or network required):

```sh
python3 -m unittest discover -s tests -v
python3 scripts/privacy_audit.py
python3 source/build_wotmod.py
sha256sum dist/*.wotmod
```

To exercise the next automatic patch release without editing `VERSION`:

```sh
WOTMOD_VERSION="$(python3 scripts/release_version.py --run-number 2)" \
  python3 -m unittest discover -s tests -v
WOTMOD_VERSION="$(python3 scripts/release_version.py --run-number 2)" \
  python3 source/build_wotmod.py
```

The **historical v1.6.0** package hash is
`9f3d98948ed398c3a4dc14b6785b68f10f1319381f896c6cd49b8709359c4927`.
It is checked **only when actually building v1.6.0**, not for later releases. The updated v1.6.1 runtime intentionally produces a different package hash.

## PR CI (`ci.yml`)

Runs on pull requests to `main` with only `contents: read` and pinned checkout, no publication token. Executes privacy and regression tests, verifies the reviewed build, then builds the next automatically generated patch version to catch interpolation issues. `VERSION` upgrades and reviewed source/graphics changes do not require changing a hard-coded v1.6.0 checksum.

## Automated Releases (`release.yml`)

Runs on every push to `main` and optional manual dispatch, serializing all release jobs with `concurrency` (no cancellation). The release job has `contents: write` only on `main`; PR workflows cannot publish.

1. Compute `v<base_patch + run_number - 1>`; a **rerun uses the same release version**, and failed attempts can leave gaps.
2. Run full unit tests, privacy scan and deterministic `.wotmod` builder.
3. Generate `SHA256SUMS.txt` and verify it before any GitHub write.
4. `scripts/publish_release.sh` uses only **GitHub CLI `gh release`**, read-only Git tag checks (`git ls-remote`) and `sha256sum`. No hand-written REST calls, HTTP client, Java, additional credentials or third-party release service.
5. If a release tag already exists, its resolved commit is checked against the exact `GITHUB_SHA`. Incorrect tags stop publication; tags are never moved.
6. `gh release create` takes both built files in one command. GitHub CLI internally creates a temporary draft, uploads its assets and publishes it. It is **not** fully atomic; an interrupted command may leave a draft.
7. The pipeline recognizes incomplete drafts via `gh release list --json tagName,isDraft` rather than incorrectly treating `gh release view` HTTP 404 as proof of absence. An ordinary release run refuses to overwrite an existing draft.
8. For already published releases, the pipeline downloads and compares the actual asset bytes with the local build. Both the mod and checksum manifest must match; existing published assets are never modified.
9. The publication is verified only after GitHub CLI reports it as published and both downloads match `sha256sum`.

The sole GitHub credential is the job-scoped built-in `GITHUB_TOKEN`, passed to GitHub CLI as `GH_TOKEN`. `actions/checkout` is pinned to a commit SHA and configured with `persist-credentials: false`.

## Operational limitations

- A public repository does not guarantee an active Actions runner. Check workflow logs/billing/policy on any failure before merging. Offline command-level mocks cannot guarantee success of the real GitHub CLI upload path until a release completes.
- Release publication is multi-step, not an atomic GitHub operation. A failed run may leave a correctly tagged draft. A manually dispatched Recovery workflow deletes **only that draft** (leaving its existing Git tag intact) and recreates it using one `gh release create` invocation. A corrupt **published** release intentionally requires manual intervention instead of overwriting public binaries.
- `github.run_number` is workflow-specific. Changing the workflow name or lowering the base `VERSION` requires a review of version collisions. Tags are never moved by the pipeline.
- The WoT bytecode uses the game's historical CPython 2.7 interpreter and non-public HUD structures. A future game update may require changing the mod.
- Do not merge until the PR CI actually runs and passes, and perform one live in-game regression test of v1.6.1 after release.

## Recovery of interrupted draft releases

The original `v1.6.1` publication workflow built correctly but left a draft without files. The manual Recovery workflow uses only native `git` and `gh release` commands:

1. Validate `vX.Y.Z`, and resolve the existing tag to the exact commit with `git ls-remote` (including annotated tags).
2. Check out that exact commit, rebuild the original `.wotmod`, run its own unit tests, privacy scan and SHA-256 manifest validation.
3. Detect the existing release with `gh release list` (drafts included). If it is a **draft**, delete that draft only using `gh release delete --yes` (never `--cleanup-tag`). Then recreate and publish the complete Release using `gh release create TAG .wotmod SHA256SUMS.txt --verify-tag`.
4. If GitHub CLI cannot delete the draft, fail with instructions to delete just the draft in the Releases UI while retaining the tag, then rerun Recovery.
5. Verify the published release using `gh release view`, `gh release download`, byte-for-byte comparison and SHA-256.
6. If already published, verify assets read-only. A wrong commit or a corrupt published release always fails without overwriting it.

To recover `v1.6.1`, after merging the reviewed fix: **Actions → Recover an interrupted WotMod Release → Run workflow**, choose branch `main`, tag `v1.6.1`. This does not increment the normal Release workflow's version numbering or make the older release the latest one.

The GitHub CLI may use GitHub's own APIs internally; the repository does not implement or contact any external release API or service.
