# Reproducible build & automated releases

## Source of truth

- `source/mod_staysharp_medkit.py`: executable client logic, kept as-is from v1.6.0 (except build-time replacement of the literal `VERSION = '1.6.0'` for later Releases).
- `assets/medkit_pulse_master.dds.b85`: zlib-compressed base85 encoding of *the original* `medkit_pulse_20.dds`. No personal metadata or external dependencies.
- `source/build_wotmod.py`: builds exactly 21 DDS frames, a Python 2.7 `EXEC_STMT` entrypoint, and a ZIP_STORED `.wotmod`, with no network access. DDS headers and intensity progression are checked.
- `VERSION`: first Release's semantic version. To intentionally change major/minor, review changes to release numbering and runtime version in the same PR.

Run locally:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/privacy_audit.py
python3 source/build_wotmod.py
sha256sum dist/*.wotmod
```

To simulate the *next* release:

```sh
WOTMOD_VERSION=1.6.1 python3 source/build_wotmod.py
WOTMOD_VERSION=1.6.1 python3 -m unittest discover -s tests -v
```

For `1.6.0`, the complete resulting ZIP's SHA-256 must equal `9f3d98948ed398c3a4dc14b6785b68f10f1319381f896c6cd49b8709359c4927`. This detects any accidental change in original user-tested assets or logic.

## GitHub Actions workflow

- `.github/workflows/ci.yml`: on pull requests, readonly `contents: read`, runs tests, deterministic package checks and privacy audit. No release or elevated permission on PRs.
- `.github/workflows/release.yml`: on **every push to `main`** (and manual dispatch), `contents: write` only in its release job. Builds the `.wotmod`, verifies it, generates `SHA256SUMS.txt`, then invokes `gh release create` using the built-in scoped `GITHUB_TOKEN`.
- Pin `actions/checkout` to an immutable full SHA. The `gh` CLI and Python 3 are available on official Ubuntu runners.

The Release workflow has its own `github.run_number`, independent of CI runs. Baseline patch + (run_number - 1) determines the version; no tags need to be committed back to main, so the release process cannot create a recursive release trigger. GitHub guarantees a unique run number for each *new workflow run*; reruns keep the same number. A successful rerun skips if its tag already exists on the same commit.

Concurrent workflows can complete out of order; this is not a guarantee of chronological release numbering in the UI when multiple merges happen almost simultaneously. The workflow does not cancel pending runs.

## Important limitations

- GitHub Actions can be turned off or blocked by repository settings/billing. A PR can only verify the workflow configuration; the release workflow first executes **after merge** into `main`.
- A failing test, privacy scanner or build prevents a Release. Such a run consumes a version number; gaps are acceptable.
- `.wotmod` uses WoT's CPython 2.7 bytecode header and an ASCII source bootstrap. A WoT engine/interpreter change requires updating the builder and client code.
- The source code does not contain a Wargaming signing key or promise compatibility with future client versions.
- `github.run_number` is specific to the named workflow. Do not rename `release.yml` or reset baseline `VERSION` without reviewing version uniqueness.
