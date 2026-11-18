# Validation performance and maintenance

The PR workflow uses standard GitHub Actions concurrency, native parallel steps
and the pinned `actions/cache` restore/save actions. The module's test matrix,
browser image, Playwright version, timeouts and release checks are preserved.

## One set of validation commands

`scripts/sessionstats/validate.sh` is the shared command entry point. Without an
argument, or with `all`, it performs the complete release transaction in order.
The PR workflow exposes the same phases as named steps:

| Phase | Work |
| --- | --- |
| `python3` | Complete module unittest discovery on Python 3 |
| `python27` | Complete module unittest discovery on the verified game runtime |
| `preview` | Generate the current preview once |
| `browser` | Prepare the pinned browser environment once, smoke-test it and run all six browser suites |
| `build` | Build, snapshot all six assets, rebuild and compare every asset |
| `integration` | Check module identities and resource integration |
| `privacy` | Audit source, recursive archives and game bytecode |

The PR job generates the preview before starting both Python suites and browser
QA together on one runner. GitHub's native `parallel` group joins all three
steps. They must all succeed before the build and package checks begin.
Production uses the complete `all` entry point.

There is no custom process scheduler or persistent prepared-browser state.
The existing full browser runner owns preparation, isolated containers and
cleanup. Package verification and upload remain after every validation phase.

## Verified CPython cache

`.github/actions/python27` restores an exact Ubuntu 24.04 cache key containing
runner OS, architecture and the bootstrap recipe hash. The recipe includes the
CPython version, source archive SHA-256, configure flags and runtime probe.
There are no prefix restore keys for executable runtimes.

The bootstrap always runs, including on cache hits. It checks CPython 2.7.18,
bytecode magic and marshal, compression, hashing and ZIP round trips. The probe
ignores Python environment/user-site settings and disables bytecode writes.
A cache miss builds the checksum-verified official source. An invalid or
incomplete restored runtime fails before exporting `PYTHON27`.

PR validation has read-only cache access. Only a successful bootstrap from
accepted `main` in a push or manual release run can save the runtime. The release
build's read-only repository permissions and separate publishing job remain.
Until an accepted main build fills a new key, PRs take the ordinary cold path.
Neither a cold cache nor a cache hit skips module tests.

To invalidate a damaged cache, delete that exact entry in Actions > Caches.
Changes to the bootstrap recipe produce a new key automatically. When changing
the runner OS or compiler recipe, update the action's platform key and its
contracts together. The supported runtime path is still
`${RUNNER_TEMP}/sessionstats-cpython27/Python-2.7.18/python`.

## Superseded PR runs and releases

Each PR workflow groups concurrency by workflow, event and PR number. A newer
commit cancels its superseded PR validation. Manual runs use their own run ID,
and different workflows or PRs do not cancel one another.

The release transaction keeps its existing serialized queue and
`cancel-in-progress: false`. Native PR path filters still evaluate the complete
PR diff, including earlier shared changes; they are not last-commit shortcuts.
The existing release planner classifies `scripts/sessionstats/**` as build inputs,
so accepting changes to those scripts can allocate a Session Stats release under
the unchanged publication policy.

## Verification

Run the complete infrastructure suite with
`python3 -m unittest discover -s tests -v`. New contracts cover cold/warm/invalid
runtime reuse, verification and download failures, phase failure propagation,
temporary-manifest cleanup, concurrency isolation and cache writer boundaries.

Run both complete module test suites and browser QA against the candidate.
Validate the main-based CI PR and the current feature source separately because
their application versions and test counts may differ. For timing comparisons,
keep the application revision and compiler cache state fixed. Compare each
test phase, the time until the installer is available and the sum of job times.

## References

- [Native parallel steps](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idstepsparallel)
- [Workflow concurrency](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency)
- [Cache restore/save examples](https://github.com/actions/cache#using-a-combination-of-restore-and-save-actions)
- [Cache scopes and access modes](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)
- [Pinned Playwright containers](https://playwright.dev/docs/docker)
