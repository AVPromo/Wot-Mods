/* Optional footer contract failures and late callbacks, not a Gameface emulator. */
const {chromium} = require('playwright');
const path = require('path');
const fs = require('fs');
const assert = require('assert');
const root = path.resolve(__dirname, '..');
const checks = [];
const errors = [];
function check(name, ok) { assert(ok, name); checks.push(name); }

async function fixture(browser, options = {}) {
  const page = await browser.newPage();
  page.on('pageerror', error => errors.push(error.message));
  await page.setContent('<html><body><div class="App_footer_verified"><div class="SessionStats_base_original">19</div><button id="native-button">Native</button></div></body></html>');
  await page.evaluate(options => {
    window.testActions = [];
    window.testEvents = {};
    window.testWarnings = [];
    window.testFrames = [];
    window.testModelCallbacks = [];
    window.testRegistrationAttempts = {};
    window.testFeature = {onAction:args=>testCommand(args)};
    window.testID = 41;
    window.nativeCalls = 0;
    window.requestAnimationFrame = callback => { testFrames.push(callback); return testFrames.length; };
    window.console.warn = message => testWarnings.push(message);
    window.isDomBuilt = true;
    document.getElementById('native-button').onclick = () => { nativeCalls++; };
    window.testCommand = args => testActions.push(args);
    window.engine = {
      whenReady: options.rejectedReady ? new Promise((resolve, reject) => { window.testRejectReady = reject; }) : Promise.resolve(),
      on(name, callback) {
        if (!testEvents[name]) testEvents[name] = [];
        testEvents[name].push(callback);
        if (options.partialOnFailure) throw new TypeError('registration changed');
      },
      off(name, callback) {
        if (options.cleanupFailure) throw new TypeError('event cleanup changed');
        testEvents[name] = (testEvents[name] || []).filter(fn => fn !== callback);
      }
    };
    window.viewEnv = {
      addDataChangedCallback(name, id) {
        testModelCallbacks.push(['add', id]);
        testRegistrationAttempts[id]=(testRegistrationAttempts[id] || 0)+1;
        if(options.rejectModel && testRegistrationAttempts[id]===1) throw new Error('Model registration rejected');
        if(options.emptyModel && testRegistrationAttempts[id]===1) return null;
        if(options.synchronousModel) emitChange();
        return id+100;
      },
      removeDataChangedCallback(callbackID, id) {
        testModelCallbacks.push(['remove', id]);
        if (options.cleanupFailure) throw new TypeError('model cleanup changed');
      }
    };
    window.subViews = {
      ids() { return [testID]; },
      get() { return {model: {grzSessionFooter: testFeature}}; }
    };
    if (options.missingGet) delete window.subViews.get;
    window.emitChange = () => (testEvents['viewEnv.onDataChanged'] || []).slice().forEach(fn => fn());
    window.flushFrames = () => {
      while (testFrames.length) testFrames.shift()(0);
    };
  }, options);
  await page.addScriptTag({path:path.join(root, 'ui/footer.js')});
  if (options.rejectedReady) await page.evaluate(() => testRejectReady(new Error('host unavailable')));
  await page.evaluate(() => Promise.resolve());
  return page;
}

(async function () {
  const localChrome = path.resolve(root, '../.wot-design-tools/chrome-testing/chrome-headless-shell-linux64/chrome-headless-shell');
  const executablePath = process.env.GRZ_CHROME || (fs.existsSync(localChrome) ? localChrome : undefined);
  const browser = await chromium.launch({executablePath, headless:true, args:['--no-sandbox']});
  try {
    const normal = await fixture(browser);
    check('Working footer keeps its original icon insertion and command path',
      await normal.locator('#grz-session-stats-footer-button').count() === 1);
    await normal.locator('#grz-session-stats-footer-button').click();
    check('An unchanged host dispatches exactly one open command',
      JSON.stringify(await normal.evaluate(() => testActions)) === JSON.stringify([{action:'open'}]));
    await normal.evaluate(() => {
      testEvents['viewEnv.onDataChanged'].push(() => { nativeCalls++; });
      window.savedGet = subViews.get;
      subViews.get = () => { throw new TypeError('subview contract changed'); };
      for (let i = 0; i < 4; i++) emitChange();
    });
    check('A changed subview contract cannot interrupt later native footer listeners',
      await normal.evaluate(() => nativeCalls === 4));
    check('A broken optional subview removes only our button and logs once',
      await normal.locator('#grz-session-stats-footer-button').count() === 0 &&
      await normal.locator('.SessionStats_base_original').textContent() === '19' &&
      await normal.evaluate(() => testWarnings.length === 1));
    await normal.evaluate(() => { subViews.get = savedGet; emitChange(); });
    check('A temporary subview failure recovers on the next valid host update',
      await normal.locator('#grz-session-stats-footer-button').count() === 1);
    await normal.evaluate(() => { testCommand = () => { throw new TypeError('command changed'); }; });
    await normal.locator('#grz-session-stats-footer-button').click();
    await normal.locator('#native-button').click();
    check('A rejected mod command leaves native footer controls callable',
      await normal.evaluate(() => nativeCalls === 6 && testActions.length === 1));
    await normal.close();

    for(const mode of ['rejectModel','emptyModel']) {
      const retry=await fixture(browser,{[mode]:true});
      check('Initial failed footer callback keeps the usable icon ('+mode+')',
        await retry.locator('#grz-session-stats-footer-button').count()===1 &&
        await retry.evaluate(()=>testRegistrationAttempts[41]===1));
      await retry.evaluate(()=>emitChange());
      check('The same footer subview retries and then stops registering ('+mode+')',
        await retry.evaluate(()=>{emitChange();return testRegistrationAttempts[41]===2;}));
      await retry.evaluate(()=>{testID=42;emitChange();});
      check('A recreated footer subview retains its icon after rejected registration ('+mode+')',
        await retry.locator('#grz-session-stats-footer-button').count()===1 &&
        await retry.evaluate(()=>testRegistrationAttempts[42]===1 && testModelCallbacks.some(x=>x[0]==='remove' && x[1]===41)));
      await retry.evaluate(()=>{
        testFeature.activity=JSON.stringify({pending:3,processing:false});
        testFeature.appearance='.grz-session-footer-button { color: rgb(12, 34, 56); }';
        emitChange();emitChange();
      });
      check('Recovered footer callback receives activity and appearance changes ('+mode+')',
        await retry.evaluate(()=>testRegistrationAttempts[42]===2 &&
          document.getElementById('grz-session-stats-footer-button').getAttribute('aria-busy')==='true' &&
          getComputedStyle(document.getElementById('grz-session-stats-footer-button')).color==='rgb(12, 34, 56)'));
      await retry.evaluate(()=>GRZSessionFooter.destroy());
      check('Cleanup removes the successfully retried callback for the current subview ('+mode+')',
        await retry.evaluate(()=>testModelCallbacks.filter(x=>x[0]==='remove' && x[1]===42).length===1));
      await retry.close();
    }
    const synchronous=await fixture(browser,{synchronousModel:true});
    check('Synchronous footer model delivery cannot recursively duplicate registration',
      await synchronous.evaluate(()=>testRegistrationAttempts[41]===1));
    await synchronous.close();
    const late = await fixture(browser, {cleanupFailure:true});
    const lateState = await late.evaluate(() => {
      const staleClick = document.getElementById('grz-session-stats-footer-button').onclick;
      const queued = testFrames.length;
      GRZSessionFooter.destroy();
      emitChange();
      flushFrames();
      staleClick();
      GRZSessionFooter.refresh();
      GRZSessionFooter.destroy();
      return {queued, present:!!document.getElementById('grz-session-stats-footer-button'),
        actions:testActions.length, native:!!document.getElementById('native-button'),
        cleanupAttempted:testModelCallbacks.some(x => x[0] === 'remove')};
    });
    check('Failed native unsubscription still removes the mod button and attempts model cleanup',
      !lateState.present && lateState.native && lateState.cleanupAttempted);
    check('Queued frames, retained events and stale clicks stay inert after destroy',
      lateState.queued > 0 && !lateState.present && lateState.actions === 0);
    await late.close();

    const missing = await fixture(browser, {missingGet:true});
    await missing.evaluate(() => { emitChange(); flushFrames(); });
    check('A missing subview getter disables only the optional icon',
      await missing.locator('#grz-session-stats-footer-button').count() === 0 &&
      await missing.locator('#native-button').count() === 1);
    await missing.close();

    const partial = await fixture(browser, {partialOnFailure:true});
    await partial.evaluate(() => { emitChange(); flushFrames(); GRZSessionFooter.refresh(); });
    check('A host that throws after registering cannot leave a live partial injection',
      await partial.locator('#grz-session-stats-footer-button').count() === 0);
    await partial.close();

    const rejected = await fixture(browser, {rejectedReady:true});
    await rejected.evaluate(() => { flushFrames(); GRZSessionFooter.refresh(); });
    check('Rejected host readiness is handled without an unhandled promise',
      await rejected.locator('#grz-session-stats-footer-button').count() === 0 &&
      await rejected.locator('#native-button').count() === 1);
    await rejected.close();
    check('No mod error escapes to the browser native-event fixture' + (errors.length ? ': ' + JSON.stringify(errors) : ''), errors.length === 0);
    console.log(JSON.stringify({checked_at_utc:new Date().toISOString(), passed:checks.length, checks,
      errors, live_client_tested:false,
      fixture:'Chromium DOM with simulated OpenWG/subview API failures and deterministic pending animation frames.'}, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
