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
4. `scripts/publish_release.py` checks the target tag's **resolved commit** (including annotated tags). An existing wrong-commit tag **fails without publication**.
5. If no tag exists, create it explicitly at the workflow's exact `GITHUB_SHA` and verify it before making a draft Release.
6. If a matching **draft** exists, re-upload/repair its two assets, check exact names/sizes/SHA-256, and only then publish it.
7. If a matching **published Release** already exists, re-verify its two immutable assets; success only if it is complete and correct. Missing or corrupt published assets fail with a clear error for manual investigation; never silently overwrite published binaries.
8. After publishing, verify tag, published state and both asset hashes again. GitHub supplies asset SHA-256 digests; if missing, the publisher downloads and hashes the asset.

The release script uses `gh` CLI and the built-in GitHub `GITHUB_TOKEN` (`GH_TOKEN`). No PAT or repository secret is required. There are no external actions other than pinned `actions/checkout`.

## Operational limitations

- A public repository does not guarantee an active Actions runner. Check workflow logs/billing/policy on any failure before merging. Local tests cannot prove the GitHub API publication path itself.
- Release publication is multi-step, not an atomic GitHub operation. A failed run may leave a correctly tagged draft, which a rerun repairs. A corrupt **published** release intentionally requires manual intervention instead of overwriting public binaries.
- `github.run_number` is workflow-specific. Changing the workflow name or lowering the base `VERSION` requires a review of version collisions. Tags are never moved by the pipeline.
- The WoT bytecode uses the game's historical CPython 2.7 interpreter and non-public HUD structures. A future game update may require changing the mod.
- Do not merge until the PR CI actually runs and passes, and perform one live in-game regression test of v1.6.1 after release.
