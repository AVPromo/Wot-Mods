# History persistence and panel performance

This follow-up to the independent PR #3 audit removes full-history rewriting
from battle updates and full-history projection from normal panel refreshes.
It does **not** make initial history loading asynchronous or certify live-game
frame times. All measurements below use synthetic records on a Linux host.

## Changes

- Battle updates persist the changed normalized record and changed period
  boundaries. They no longer deep-copy, encode, hash or reread all battles.
  Accepted state and indexes advance only after the commit marker is durable.
- Storage format 2 retains three small, atomic generation descriptors. A
  descriptor authenticates an immutable base and a committed journal prefix.
  Journal files are owned by one writer and have an independently flushed mirror.
  Transactions are chained by SHA-256, flushed before descriptor rename, and
  replayed iteratively. A failed append/rename leaves the prior prefix committed;
  a retry truncates only that writer's uncommitted tail. A restarted writer uses
  a new segment. Existing lock, stale-generation and post-commit protections apply.
- Base/segment creation uses exclusive file creation. Names are restricted to
  local UUID filenames. A corrupted primary can recover from its mirror;
  damaged newest prefixes can recover an earlier valid descriptor. Unknown
  formats remain read-only. A missing/corrupt base and mirror are not reinitialized.
- Legacy v1 histories load with their existing checksum and application validator.
  Base copies and new segment headers are prepared during service initialization,
  before live writes. Subsequent loads authenticate the immutable base bytes,
  avoiding repeated full-history JSON encoding. Old mod versions see storage
  version 2 and refuse writes instead of overwriting the new history.
- A snapshot read is capped at 64 MiB; larger files fail closed without falling
  back to an older, potentially incomplete history. Individual journal headers
  and transactions are bounded at 1 MiB and JSON nesting remains bounded.
- Active-period totals, group totals, extrema, warning counts and pending IDs are
  indexed. Corrections remove the old contribution and add the new one. WN8
  remains calculated from aggregate actual/expected totals. Floating-point
  cancellation and overflow can recover after a correction. Startup builds
  indexes in batches; battle updates modify only affected groups.
- Each scope supplies at most 40 rows per grouping (battles, vehicles, maps).
  Previous/Next controls request further pages. Totals and coverage always refer
  to the entire period. Commands carry account and period identity, so stale
  account/reset requests are ignored. Native thumbnail enrichment only copies
  displayed battle contexts. Display names are capped at 256 characters and
  notices at 200 plus an explicit additional-notices message; stored data remains
  intact. The installation scope uses the same paging and storage machinery.

No database extension, network service, new mod dependency, game thread,
worker-thread game API call, or new shared-client hook was introduced.

## Reproducible benchmark

Run `tools/benchmark_history.py` under Python 2.7 and Python 3. The revised fixture
first writes a real legacy ledger, then reopens it normally, so index construction
and migration are not bypassed by direct in-memory test seeding. It measures
initial load separately from a new beginning, a result correction, the first
snapshot plus compact strict JSON, and a subsequent journal-backed restart.

Baseline: `77331eb581f00bd3b3fe5947a43f4fd2c90b875e`, as measured in the independent
audit. Follow-up timings below are one observed run, not latency guarantees.

| Interpreter | Records | Beginning before | Beginning after | Correction after | Snapshot before | Snapshot after | Payload before → after |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CPython 2.7.18 | 1,000 | 1.107 s | 0.003913 s | 0.004628 s | 0.859 s | 0.009833 s | 2,505,356 → 113,128 bytes |
| CPython 2.7.18 | 10,000 | 7.154 s | 0.004354 s | 0.004231 s | 7.287 s | 0.016238 s | 24,933,550 → 113,410 bytes |
| CPython 3.12.14 | 1,000 | 0.094 s | 0.002956 s | 0.002880 s | 0.177 s | 0.004456 s | 2,505,356 → 113,128 bytes |
| CPython 3.12.14 | 10,000 | 0.930 s | 0.005399 s | 0.004424 s | 2.151 s | 0.014177 s | 24,933,550 → 113,410 bytes |

These measurements exclude localization, thumbnails, native transfer, DOM layout
and the optional installation write. Actual disk/antivirus latency remains a
factor because successful receipt still requires synchronous flushing.

## Remaining performance limits

**Initial loading is still synchronous and proportional to retained history.**
In the same 10,000-record run, Python 2.7 took 25.025 s for the legacy load and
preparation, and 3.687 s for a subsequent journal-backed restart. An earlier
legacy-load run was 4.658 s, illustrating substantial host variability; no
percentile claim is made. Python 3 took 1.362 s and 1.072 s respectively.
Account activation or initialization during reconnect can therefore still stall.
This is a remaining P1 startup-performance issue, separate from the corrected
per-battle write and panel projection paths. Solving it safely requires staged
or asynchronous loading with explicit handling of events arriving before the
ledger is ready, including durability and account-switch ownership tests.

Journal replay and index memory grow with history. Journals, mirrors and orphaned
pre-commit segments are deliberately not deleted or automatically compacted by
this change. Reset preserves historical membership. Very long histories with
many result revisions/restarts require an explicit maintenance/compaction design.
Period-list copying and group sorting still scale with period/group count, and
pending-result recovery scales with the number of incomplete results. This is
not a constant-time or bounded-memory guarantee for every possible input.

Back up the **entire account/installation data directory while the game is
closed**, including `journal/` and its `.bak` files. Copying only `state-*.json`
no longer creates a complete backup. Do not manually delete journal segments.

## Regression evidence

`test_history_performance.py` checks bounded encoded writes and copy work,
complete traversal of all pages, full-period totals, incremental/full-recompute
parity through corrections/resets/restarts, overflow recovery, independent
snapshot objects, failed commit/mirror flush and retry, mirrored corruption
recovery, torn-tail fallback, stale writers, malformed/future descriptors,
oversize protection, filename collisions, bounded display fields and stale
pagination commands. Existing chronology/account/installation/recovery suites
also run against journal storage. The generation-recovery fixture now restores
its journal dependencies alongside its head descriptors.

`ui-pagination.cjs`, included in the existing panel suite, exercises shipped
pagination controls, ownership parameters, row replacement, totals/counts,
first/last-page limits, old small payloads and retained handlers after teardown.
It uses explicit button-label elements required by the existing Gameface
compatibility contract. Browser doubles do not replace a real client test.

Local validation: all 523 tests pass on CPython 3.12.14; the same suite passes on
CPython 2.7.18 with nine expected Python-3-only packaging skips. All 211 repository
tests pass. Browser suites pass 220 panel, 22 wheel, 29 footer activity, 40 footer
compatibility and 31 appearance checks, plus the base footer suite. The package
build, all-six-asset reproducibility, integration isolation and recursive
source/archive/bytecode privacy audit pass. Hosted CI is reported separately in
PR #3. No live WoT/Windows/mod-pack validation was performed.
