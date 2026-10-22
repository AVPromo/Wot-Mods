# Building and publishing WotMods

## Source and local build

- `source/mod_staysharp_medkit.py` is the WoT client runtime (Python 2.7-compatible).
- `source/build_wotmod.py` creates the single, self-contained `.wotmod` archive using Python 3 standard-library tools.
- `assets/medkit_pulse_master.dds.b85` and `.sha256` are the checked animation master; 21 DDS frames are generated without external downloads.
- `VERSION` is the reviewed release base. The `Release WotMod` workflow uses its own `github.run_number` to select a unique patch number. A *rerun* keeps the same number; a new dispatch/merge gets a new number.

Run:

```sh
python3 scripts/privacy_audit.py
python3 -m unittest discover -s tests -v
python3 source/build_wotmod.py
(cd dist && sha256sum -- *.wotmod > SHA256SUMS.txt && sha256sum --check SHA256SUMS.txt)
```

Local tests do not prove rendering correctness inside the game; test each new build in a real WoT client before recommending it as confirmed stable.

## GitHub Actions: deliberately simple and GitHub-native

- **PR CI:** `.github/workflows/ci.yml` checks source, privacy and builds. It has `contents: read` and **cannot publish** a release.
- **Automatic Release:** `.github/workflows/release.yml` runs after each push to `main` (including a merged PR) or a manual dispatch. No third-party release platform, custom REST/HTTP client or Java.
- **Build job:** read-only checkout, unit tests, source/privacy scan, deterministic `.wotmod` + `SHA256SUMS.txt` validation. GitHub's first-party `actions/upload-artifact` preserves the verified output between jobs.
- **Publish job:** only after a green build, and only on `main`, grants `contents: write`, downloads **that same** build with `actions/download-artifact`, verifies SHA-256 again, creates the Git tag pointing to the exact merge commit (if absent), and checks it.
- **Release:** a single official `gh release create --verify-tag` uploads both files and publishes. The workflow then downloads the published assets and checks their bytes, filename set and SHA-256. Existing published assets are verified but never overwritten.
- First-party GitHub Actions are pinned to their exact full commit hashes. The only credential is the ephemeral, repository-scoped `GITHUB_TOKEN`; the build job never receives a write-capable token. The publish job's checkout uses this token only to push the Git tag.
- `concurrency` serializes releases without cancellation. No automation deletes, moves, modifies or retargets existing Releases.

GitHub's `gh release create` internally creates a draft, uploads assets and publishes the Release as separate requests. **No implementation can guarantee these three steps are atomic.** If a draft is interrupted, the workflow fails visibly; it does not delete the draft or falsely report success. There is intentionally **no custom recovery script or workflow**.

## One-time GitHub setting: Immutable Releases

Before the first successful public release, enable **Settings → Releases → Enable release immutability** in this repository. GitHub then protects new published release assets and their associated tags from modification, and generates release attestations. This setting applies to **future** published releases and cannot be enabled by this source-code PR alone.

Check published assets using `gh release verify <tag>` and `gh release verify-asset <tag> <filename>` after enabling immutability. The workflow also always verifies actual downloaded bytes independently of this setting.

## The interrupted `v1.6.1` release

The original first run left **an unpublished, empty draft** named `v1.6.1`. The tag still points to the exact original commit. This draft is **not** a public downloadable Release; it does not block a newer `v1.6.2` (automatic run #2).

To tidy it, inspect `v1.6.1` in GitHub's Releases UI. Only if it is **still a draft**, optionally delete **the draft only**, keeping its Git tag. Do not delete published releases or move tags. There is no need to re-create `v1.6.1`: the first successful automatic publication will use the new, unique release number. For a historical rebuild, check out the original tag and run the local build procedure, without publishing over an existing tag.

If a new run leaves a draft, leave it for manual investigation, and fix the underlying fault in a reviewed PR. A fresh run can publish a new version; **rerunning the same run** will fail safely until the draft is manually reconciled.

## Release numbering and scope

The first merged workflow on `main` had run number 1, producing `v1.6.1`, but publication failed. The next new Release workflow run will use `v1.6.2` if the baseline `VERSION` remains `1.6.1`. This is **workflow-run numbering**, not the number of commits and not a tag-triggered workflow. Tags created with `GITHUB_TOKEN` don't trigger another GitHub Actions workflow.

For now, this pipeline builds **Stay Sharp only**. The repo can contain other mods, but `/releases/latest` is a repository-wide pointer. A future multi-mod release workflow must be explicitly designed and reviewed before combining artifacts.

WoT upgrades may change the Python interpreter, HUD, or private methods used by the mod; this pipeline cannot guarantee runtime compatibility with untested game updates.
