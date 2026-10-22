# PR #3 review fixes

## English repository documentation

Repository guides, historical notes, changelogs, attribution descriptions and
package metadata are now English. Legacy guide/archive filenames remain stable
for existing packaging and links. The builder stamps the English `Version` line;
synthetic preview names and generic test messages are English too. Translated
catalogs, legacy Polish warning lookups and deliberate Unicode/localization test
fixtures retain their language-specific content.

Installation and language guides explicitly document the bundled seven-language
catalog, embedded English fallback, optional neighboring JSON files and partial
nested configuration overrides.

## Earlier review fixes

- Sources are stacked on dedicated PR #2, which supplies builds, both Python
  versions, Chromium tests and automatic Session Stats Releases. Workflow review
  remains in PR #2; PR #3 shows source changes. The pipeline must be accepted on
  `main` before the final source merge.
- Malformed-JSON tests require a numeric error location and omission of private
  values from logs without depending on the decoder's chosen error position.
- Each cache request owns a token. Late responses from expired requests cannot
  remove newer requests or bypass backoff.
- Only `reconcile=True` authorizes changing known results. `complete=True` marks
  completeness; without revision authority it may fill unknown fields only.
- Optional Gameface registration failure does not block the initial model read
  or sizing. A later model event retries registration without duplicate engine
  listeners; cleanup removes only an acquired registration.
- The builder stamps active guide filenames, including the source copy, with the
  release version. Historical changelogs and compatibility evidence stay historical.
- The ZIP's internal manifest uses paths relative to the extracted package root.
  At this review stage, `sha256sum -c SHA256SUMS.txt` verified all three installed
  files; the later language-catalog addition extends this to four.
- Old incomplete entries remain queued and stored, but do not keep the spinner
  active after restarting without a new battle. The panel explains the gap.
  Details: [RESTORED_RESULTS_ACTIVITY.md](RESTORED_RESULTS_ACTIVITY.md).

Validation: 364 Python 3 tests; the same Python 2.7 suite with 4 Python-3-only
builder tests skipped. The 114 panel checks cover rejected callback registration,
synchronous delivery during registration and retained callbacks after teardown.
A 0.2.8 build, actual extracted-ZIP checksum verification and an identical ZIP
rebuilt from its included sources were checked. Mocked-client tests do not replace
running WoT.

Offline recovery additionally observes the native cache before its consumer and
stream acknowledgment, uses a fair queue, separates cooldown/login delays and
fills unknown fields from late streams. Incomplete periods and missing battles
remain explicit. Recovery limits and pinned client code:
[OFFLINE_RESULT_RECOVERY.md](OFFLINE_RESULT_RECOVERY.md). Battle entry also saves
available map/vehicle names, tier and class, making missing results recognizable
after restart. Eight tests cover native descriptors, late metadata readiness,
persistence, write deduplication, confirmed-result protection and context privacy.

Raster comparison retains its 16-pixel limit; the 6/255 channel tolerance covers
10 pixels differing by 5/255 observed on Chromium 151. Styles and geometry still
match exactly. A negative control confirms rejection of actual color, radius and
opacity changes.

Review 5610518614:
- Deferred bonus refresh retains the account captured when scheduled. After an
  account switch, the timer releases its state and stops without reading or
  processing the new account's results. Manual Refresh remains independent and
  neither consumes nor cancels the old account's timer.
- Panel cleanup invalidates local binding/callback state before calling the bridge.
  Each of three engine.off calls and model-callback removal is guarded separately.
  One failure neither blocks the others nor escapes beforeunload. A retained scale
  callback stays inert after document destruction.
- Two Python tests cover switching accounts while a timer waits, no reads/revisions
  of the new account and independent manual refresh. Fifteen Chromium checks cover
  each removal failing separately, all failing together, repeated cleanup and late
  callbacks.

Account scopes and the optional durable installation scope:
- Default scopes and manual resets remain isolated per account and region.
  A confirmation from a previous account cannot reset the current account.
- sessions.instance_tab=true displays the installation tab. Its history and
  manual reset persist across game restarts using a separate transactional
  StatsService ledger; account ledgers and reset epochs are never modified.
- Installation identity uses the verified physical game root, independent of
  client-version directories. Unknown roots do not select a global fallback.
- Fifteen additional Python tests cover persistent history and reset boundaries,
  restart recovery, late discovery, separate installations, failed writes,
  corrupted generations and identity discovery. An additional browser check
  verifies that confirmation explains restart persistence.
- Details and migration rules: [ACCOUNT_SESSIONS.md](ACCOUNT_SESSIONS.md).

## English defaults and editable language catalogs

- All mod interface text now uses an English default and a configurable local
  JSON catalog with complete English, Russian, French, Polish, German, Spanish
  and Ukrainian dictionaries (181 message keys per language, including previews).
- Root `language` in `grz.sessionstats.json` selects the language. The neighboring
  `grz.sessionstats.languages.json` can override individual messages or add
  languages. The installation ZIP includes the editable file and verifies its
  checksum; the `.wotmod` includes all bundled translations as an offline fallback.
- Translation validation rejects unsafe placeholders and malformed catalogs;
  valid partial overrides retain per-message fallbacks. Native notifications
  escape markup and panel/footer labels use text nodes. Catalog values and
  private paths are omitted from diagnostics.
- Canonical English and legacy Polish warning templates are translated at
  presentation time. Account histories, session/reset boundaries and game-supplied
  map/vehicle names remain intact. Language reloads require opening the panel or
  Refresh, with no per-tick file reads.
- Local validation: 375 Python tests on both runtime interpreters (four builder
  cases skipped on Python 2.7), 183 infrastructure/Medkit tests, 165 panel checks,
  29 footer activity checks, 22 wheel checks, 12 footer compatibility checks and
  31 appearance checks. Raster checks use grayscale text to avoid RGB subpixel
  repaint artifacts while retaining the original exact style/layout comparison
  and pixel thresholds. All six assets reproduce; recursive privacy and
  cross-mod integration checks pass. Native Gameface still needs in-game review.

## Catalog recursion and pending panel readiness

- Review 5612698603: external and source-catalog loading now handle decoder
  `RuntimeError`, which also covers Python 3 `RecursionError`. A deeply nested
  catalog below the byte limit falls back locally. Valid language, appearance,
  scroll speed and installation-tab settings are preserved; account/session
  records are unchanged. Source-only fallback can still use embedded English.
- Three regressions use real decoder recursion on Python 2.7 and Python 3:
  external-catalog fallback, source-catalog fallback, and runtime Refresh with
  customized appearance, an enabled installation tab and existing history.
- The older pending-DOM review thread is also fixed: cleanup removes the exact
  `self.onDomBuilt` callback even when model binding has not started. Late engine
  readiness and load events cannot create new subscriptions after destruction.
  Five browser checks cover pending subscription ownership/removal, retained
  callbacks, delayed engine readiness and normal deferred rendering.

## Portable decoder regressions (review comment 4348237318)

The original recursion fixture assumed that every decoder would reject an array
nested 16,384 levels deep. CPython 3.14.4 accepts it, causing three tests to fail
before reaching the fallback behavior. This was reproduced on that interpreter.

The three fallback regressions now inject `RuntimeError` and, where available,
`RecursionError` at `json.loads` for the selected catalog document only. They keep
real file reads and decoding/validation boundaries, verify that injection occurred,
and restore the decoder in `finally`. Other configuration and stored data continue
through the original decoder. External fallback retains the selected bundled
language; source fallback retains embedded English; Runtime Refresh preserves
custom appearance, scroll speed, installation-tab state and account history.

A separate real 16,384-level input checks bundled-message fallback whether a
decoder rejects nesting or accepts the invalid non-string translation. The
14-test localization suite passes on CPython 2.7.18, 3.12 and 3.14.4. A negative
control removing the production `RuntimeError` handlers makes all three targeted
fallback regressions fail. Production behavior and workflow files are unchanged.

## Review 5616729809: retry native panel and footer subscriptions

Panel binding is committed only after both engine subscriptions succeed.
A rejected subscription invalidates its attempt before independently removing
both listeners, clears the connection gate and permits a later load/readiness
retry. Attempt-owned wrappers keep partially retained callbacks inert even
when native unsubscription throws. Readiness rejection and synchronous bridge
errors are handled without an unhandled promise. Successful connections still
render the current model, size the window and retain optional model-callback
retry behavior.

Footer model registration is retried whenever its callback ID is missing,
including after a rejection or null return for the same/recreated subview.
The model/button remains usable while registration waits. A reentrancy guard
prevents synchronous delivery from recursively registering another callback.

Browser regressions cover subscription failures before/after registration,
failed rollback removal, recovery and inert old callbacks, readiness rejection
and recovery, initial/recreated footer subviews, activity/appearance updates,
cleanup and synchronous registration. Targeted negative controls run these
regressions against the previous shipped JavaScript and reproduce both bugs.
Real Gameface/client validation remains separate from these Chromium doubles.

The source branch was synchronized with accepted main after infrastructure
PR #2 and Stay Sharp namespace PR #6. No candidate workflow replaces the
accepted validation harness.
