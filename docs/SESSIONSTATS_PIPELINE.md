# Shared repository, independent releases

CI infrastructure and source import use separate PRs. Merge order:
**pipeline → update the import branch from `main` → full CI → Session Stats source**.
Before source import, infrastructure runs its own tests while Session Stats build
and release steps report that sources are pending. This does not validate the mod.
The exception applies only if the source directory exists neither in the checkout
nor its complete Git history. Deleting or renaming the entrypoint after import
fails both PR validation and release builds. Merging the sources into `main`
triggers the first automatic release. Creating the PRs neither publishes a Release
nor merges them automatically.

| Mod | Source | Base version | Tags | Workflow |
|---|---|---|---|---|
| Medkit Reminder | `source/`, `assets/` | `VERSION` | `v1.6.…` | `release.yml` |
| Session Stats | `mods/sessionstats/` | `mods/sessionstats/VERSION` | `sessionstats-v0.2.…` | `sessionstats-release.yml` |

Changes confined to one mod do not release the other. Shared publisher, versioning
or scanner changes release both because they can affect both. Every relevant
Session Stats push to `main` builds a new version and creates a Release. PRs run
tests and upload only Actions artifacts, without release-publication permission.

Patch number = base patch + that workflow's run number − 1. Empty, failed or
blocked runs can leave gaps. Do not change the base VERSION for ordinary fixes;
bump major/minor for a new release line. Rerunning a run preserves its version
and verifies the existing tag, commit SHA, complete asset set and SHA-256 digests.
Published assets are not overwritten. An incomplete draft can be resumed; an
unrelated tag blocks publication.

The installation ZIP contains the `.wotmod`, default configuration, editable
language catalog, one OpenWG copy and sources. Separate assets are both `.wotmod`
files, the configuration JSON, `BUILD.json` and `SHA256SUMS.txt`. The version is
stamped into filenames, `meta.xml`, compiled `VERSION` and the report. Client
versions in historical notes identify tested baselines, not compatibility with
arbitrary future WoT versions.

The game compiler is CPython 2.7.18 from official python.org, verified against
SHA-256 `da3080e3b488f648a3d7a4560ddee895284c3380b11d6de75edb986526b9a814`.
The archive also matches Python.org's historical MD5
`38c84292658ed4456157195f1c9bcbe1`; MD5 is provenance information only, while the
pipeline enforces SHA-256. Source: https://www.python.org/downloads/release/python-2718/.
Compilation and mod tests do not download code through Python 2.7.

Validation covers Python 3 and 2.7 tests, six Chromium suites, repeat builds with
SHA-256 comparison, source/archive privacy and recursive bytecode constant/path
inspection. QA data is synthetic. Mocked-client tests do not replace running the
game. Reproducibility compares all six published assets, including configuration,
report and checksum manifest. Privacy and integration checks inspect the final
second build. The scanner also rejects binary `.p12`/`.P12` files inside nested
archives.

Build jobs use `contents: read`. A separate publisher gets `contents: write`,
and only its publication step receives `GH_TOKEN`. No PAT, user secrets,
`pull_request_target`, private runners or PR-branch releases are used.
Checkout/upload/download actions are pinned to complete SHAs.
