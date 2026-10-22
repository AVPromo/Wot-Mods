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
4. `scripts/publish_release.sh` uses only first-party GitHub CLI (`gh`), standard Git and `sha256sum`, without custom HTTP/REST requests, Java, PATs or external publishing services.
5. Verify that an existing tag resolves to the exact `GITHUB_SHA`. If neither tag nor Release exists, configure Git authentication through `gh auth setup-git` with the scoped `GH_TOKEN`; create and push a lightweight Git tag to **exactly** that commit and verify the remote ref **before** creating any Release draft.
6. Create the Release using `gh release create --verify-tag` with both assets, preventing the CLI from silently creating a tag only after the upload. This operation stages a draft, uploads, then publishes; it is not atomic, but a failed upload now leaves a verifiable existing tag.
7. Inspect drafts with `gh release list --json tagName,isDraft,isPrerelease`. A draft is never deleted automatically: the CLI has no atomic delete-if-still-draft operation. Stop and require a maintainer to confirm and manually delete ONLY a still-unpublished draft, preserving the tag, then rerun Recovery.
8. When the Release is already published, download both immutable assets, check filenames, exact bytes and SHA-256; never overwrite or delete an existing published Release.
9. After creating a new Release, verify the remote tag SHA, published status, asset names, downloaded bytes and SHA-256. **Do not force `--latest=false`**: GitHub's automatic Latest selection handles the newest recovery appropriately.

The sole GitHub credential is the job-scoped built-in `GITHUB_TOKEN` (environment variable `GH_TOKEN`). The checkout uses a pinned `actions/checkout` commit with `persist-credentials: false`; `gh auth setup-git` is used only to authenticate the initial tag push and does not store a PAT.
## Operational limitations

- A public repository does not guarantee an active Actions runner. Check workflow logs/billing/policy on any failure before merging. Offline command-level mocks cannot guarantee success of the real GitHub CLI upload path until a release completes.
- Release publication is multi-step, not an atomic GitHub operation. A failed run may leave a correctly tagged draft. Recovery **never automatically deletes a Release**, because its draft state could change between inspection and deletion. A maintainer must verify/delete only the still-unpublished draft in GitHub's UI, retain the tag, and rerun the Recovery workflow. A corrupt **published** release intentionally requires manual intervention instead of overwriting public binaries.
- `github.run_number` is workflow-specific. Changing the workflow name or lowering the base `VERSION` requires a review of version collisions. Tags are never moved by the pipeline.
- The WoT bytecode uses the game's historical CPython 2.7 interpreter and non-public HUD structures. A future game update may require changing the mod.
- Do not merge until the PR CI actually runs and passes, and perform one live in-game regression test of v1.6.1 after release.

## Recovery of interrupted draft releases

The original `v1.6.1` workflow built the mod successfully but left an empty draft. The Recovery workflow rebuilds from the historical tag commit; all GitHub release operations use native `gh release` commands.

1. Verify the requested tag and resolve it to the correct commit with `git ls-remote`, including annotated tags.
2. Check out the exact historical source; run its regression tests, privacy audit, deterministic build and SHA-256 manifest checks.
3. If the Release is published, verify both assets by downloading them. **Never overwrite or delete them.**
4. If a draft exists, stop safely. In the GitHub Releases UI, confirm that it is **still a draft** and manually delete ONLY that draft, without deleting its Git tag. Then rerun Recovery.
5. With the preserved tag and no Release, run `gh release create --verify-tag` with both rebuilt assets, and verify the resulting published files and tag.
6. If a historical draft is missing its tag entirely, refuse automatic recovery: inspect the original Actions run and target commit manually. New publications avoid this case by pushing and verifying the tag **before** creating a draft.

For existing `v1.6.1`, verify that the draft is still unpublished, manually delete just that draft (keep tag `v1.6.1`), then run **Actions → Recover an interrupted WotMod Release**, branch `main`, tag `v1.6.1`. A recovered newest version can become Latest under GitHub's automatic selection; an older release will not be forcibly marked Latest.

**Reason for manual cleanup:** the `gh release delete` command has no atomic draft-only precondition. A pre-deletion visibility check cannot rule out a concurrent publication; therefore automated deletion would put an already-published Release at risk.

The GitHub CLI may use GitHub's internal APIs. The repository contains no hand-written HTTP client or integration with an external publishing service.
