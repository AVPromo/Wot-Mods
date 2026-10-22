# Independent Session Stats builds and shared release snapshots

CI infrastructure is reviewed in PR #2 separately from source import PR #3.
Merge order: accepted infrastructure → update the source branch onto main →
full source validation → source merge. Before the first import, source steps
are skipped only if neither the checkout nor full Git history contains the
mod. A removed/misnamed entrypoint or shallow history fails validation.

| Mod | Sources | Baseline | Tags | Workflow |
|---|---|---|---|---|
| Stay Sharp | `source/`, `assets/` | `VERSION` | `staysharp-v…` | `release.yml` |
| Session Stats | `mods/sessionstats/` | `mods/sessionstats/VERSION` | `sessionstats-v0.2.…` | `sessionstats-release.yml` |

Session Stats builds never invoke Stay Sharp's builder. Read-only builds test
and reproduce all six Session Stats assets before uploading an Actions artifact.
The installer includes the mod, default configuration, one OpenWG dependency
and sources; editable language catalogs are included by the source builder.

Patch = baseline patch + workflow run number − 1. Failed/skipped runs may leave
gaps. Ordinary fixes do not require a baseline bump. Reruns retain their version.
Version stamping covers filenames, meta.xml, runtime bytecode and BUILD.json.
Historical client versions describe tested baselines, not future compatibility.

Publication follows the accepted [shared snapshot model](MULTIMOD_RELEASES.md).
Only the publish job has `contents: write` and holds the repository-wide
`wotmod-release-${{ github.repository }}` mutex with `queue: max` and
`cancel-in-progress: false`. Inside the lock it verifies the build, fetches
Latest, carries other mods byte-for-byte, publishes and compares every uploaded
file. Stale/equal identical primary versions return a successful no-op; equal
versions with different bytes fail. Drafts require manual inspection and are
never automatically resumed, overwritten or deleted. Tags must resolve to the
exact build commit before and after publication.

The owner must configure the `sessionstats-release-tags` Ruleset and
`sessionstats-release` Environment described in MULTIMOD_RELEASES.md before the
first publication. Missing/changed approval fails closed. No PAT, user secrets,
custom release API, pull_request_target or publication from PR branches is used.
Actions use full SHA pins matching accepted main.

The game compiler is CPython 2.7.18 from python.org, verified with SHA-256
`da3080e3b488f648a3d7a4560ddee895284c3380b11d6de75edb986526b9a814`.
Historical upstream MD5 `38c84292658ed4456157195f1c9bcbe1` records provenance;
the pipeline enforces SHA-256. Source: https://www.python.org/downloads/release/python-2718/.
Python 2.7 does not download build dependencies.

Full source validation runs Python 3 and 2.7 tests, six Chromium suites, two
builds compared across all six assets including configuration/report/checksums,
final-output integration and recursive source/archive/bytecode privacy scans.
Nested binary .p12/.P12 files are rejected. Integration inspects local built
packages without compiling another mod; the publisher also checks carried
packages for resource or package-ID collisions. Synthetic tests do not replace
validation inside the real World of Tanks client.
