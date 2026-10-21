/* Browser QA of the actual shipped UI. Native Gameface still requires in-game QA. */
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');
const fixtures = JSON.parse(fs.readFileSync(path.join(root,'preview/demo_snapshot.json'),'utf8'));
const errors = [];
const checks = [];
const check = (name, pass) => { assert(pass, name); checks.push(name); };
const captions = {
  'ss-close':'×', 'ss-scope-launch':'Od uruchomienia', 'ss-scope-manual':'Od resetu',
  'ss-xp-base':'Bazowe PD', 'ss-xp-received':'Otrzymane PD',
  'ss-group-vehicles':'Czołgi', 'ss-group-maps':'Mapy', 'ss-group-battles':'Bitwy',
  'ss-refresh':'Odśwież', 'ss-reset':'Wyzeruj zakres',
  'ss-reset-cancel':'Anuluj', 'ss-reset-confirm':'Wyzeruj zakres'
};

// Always serve the current shipped sources, not a previously bundled preview.
async function serveUI(page) {
  await page.route('http://grz-session.test/**',async route=>{
    const name=new URL(route.request().url()).pathname.slice(1);
    if(!['SessionStats.html','session_stats.js','session_stats.css'].includes(name)) { await route.abort(); return; }
    const contentType=name.endsWith('.js')?'text/javascript':(name.endsWith('.css')?'text/css':'text/html');
    await route.fulfill({status:200,contentType,body:fs.readFileSync(path.join(root,'ui',name))});
  });
}

async function controlLayout(page) {
  return page.evaluate(expected=>Object.keys(expected).map(id=>{
    const button=document.getElementById(id), label=button.querySelector('.ss-control-label');
    const box=button.getBoundingClientRect(), labelBox=label && label.getBoundingClientRect();
    const css=getComputedStyle(button), labelCSS=label && getComputedStyle(label);
    return {id,visible:box.width>0 && box.height>0,
      explicit:!!label && label.parentNode===button && label.textContent===expected[id],
      directText:Array.from(button.childNodes).some(node=>node.nodeType===3 && node.textContent.trim()),
      flex:css.display==='flex', block:labelCSS && labelCSS.display==='block',
      font:labelCSS && labelCSS.fontFamily.split(',')[0].replace(/["']/g,'').trim(),
      fits:!!labelBox && labelBox.width>0 && labelBox.height>0 &&
        labelBox.left>=box.left-1 && labelBox.right<=box.right+1 &&
        labelBox.top>=box.top-1 && labelBox.bottom<=box.bottom+1};
  }),captions);
}

async function battleCards(page) {
  return page.locator('#ss-groups .ss-group').evaluateAll(groups=>groups.map(group=>({
    id:group.getAttribute('data-group-id'),
    values:Array.from(group.querySelectorAll('.ss-battle-measure')).map(row=>({
      label:row.querySelector('.ss-battle-label').textContent,
      value:row.querySelector('.ss-battle-value').textContent
    })),
    aggregateRows:group.querySelectorAll('.ss-metric-head,.ss-metric-row').length,
    aggregateKPIs:group.querySelectorAll('.ss-group-kpi').length,
    outcome:group.querySelector('.ss-battle-outcome') && group.querySelector('.ss-battle-outcome').textContent,
    money:Array.from(group.querySelectorAll('.ss-money-row')).map(row=>({
      label:row.querySelector('.ss-money-label').textContent,
      values:Array.from(row.querySelectorAll('.ss-cell-value')).map(value=>value.textContent)
    }))
  })));
}

const formattedInteger=value=>String(Math.round(value)).replace(/\B(?=(\d{3})+(?!\d))/g,'\u00a0');

async function numericTextOverflow(page) {
  return page.locator('#grz-session-stats').evaluate(panel=>{
    const bad=[];
    const selector='.ss-metric-row .ss-metric-number,.ss-money-row .ss-cell-value,.ss-battle-value,.ss-group-kpi .ss-kpi-value';
    for(const value of panel.querySelectorAll(selector)) {
      const cell=value.classList.contains('ss-cell-value')?value.parentNode:value;
      const box=cell.getBoundingClientRect(), style=getComputedStyle(cell);
      if(box.width===0 || box.height===0) { continue; }
      const range=document.createRange(); range.selectNodeContents(value);
      const text=range.getBoundingClientRect();
      const left=box.left+parseFloat(style.paddingLeft)+parseFloat(style.borderLeftWidth);
      const right=box.right-parseFloat(style.paddingRight)-parseFloat(style.borderRightWidth);
      if(text.left<left-1 || text.right>right+1) {
        bad.push({className:cell.className,value:value.textContent,textWidth:text.width,available:right-left});
      }
    }
    return bad.slice(0,12);
  });
}

async function nativeHost(browser, options) {
  const native=await browser.newPage({viewport:options.initialViewport || {width:1440,height:900}});
  native.on('pageerror',e=>errors.push(String(e)));
  const snapshot=JSON.parse(JSON.stringify(fixtures.normal));
  snapshot.viewport=options.viewport || {width:1440,height:900};
  await native.addInitScript(({snapshot,options})=>{
    window.__grzCommands=[];
    window.__grzEvents={};
    window.__grzWindowEvents=[];
    window.__grzHelperCalls={rem:0,resize:0,callback:0};
    window.__grzEngineOn=[];
    window.__grzRemovedCallbacks=[];
    window.isDomBuilt=true;
    window.model={payload:JSON.stringify(snapshot),onAction:function(args){
      window.__grzCommands.push(args);
      if(args.action==='viewport' && options.changedScale) {
        const fresh=JSON.parse(window.model.payload);
        fresh.viewport.scale=options.changedScale;
        window.model.payload=JSON.stringify(fresh);
        window.__grzEvents['viewEnv.onDataChanged']();
      }
    }};
    window.engine={whenReady:Promise.resolve(),on:function(name,fn){window.__grzEngineOn.push(name);window.__grzEvents[name]=fn;},off:function(){}};
    window.viewEnv={addDataChangedCallback:function(){
      const count=++window.__grzHelperCalls.callback;
      if(options.callback==='throw' || (options.callback==='throw-once' && count===1)) throw new Error('Optional model registration unavailable');
      return 71;
    },removeDataChangedCallback:function(id){window.__grzRemovedCallbacks.push(id);}};
    if(options.drag==='supported' || options.drag==='throw') {
      window.viewEnv.handleViewEvent=function(event){
        if(options.drag==='throw') { throw new Error('Unavailable native move proxy'); }
        window.__grzWindowEvents.push(event);
      };
    }
    if(options.helpers!=='absent') {
      window.viewEnv.remToPx=function(n){
        window.__grzHelperCalls.rem++;
        if(options.helpers==='throw') { throw new Error('Unavailable native rem helper'); }
        return n;
      };
      window.viewEnv.resizeViewPx=function(w,h){
        window.__grzHelperCalls.resize++;
        if(options.helpers==='throw') { throw new Error('Unavailable native surface helper'); }
        window.__nativeSize=[w,h];
      };
    }
    if(options.noFocus) { Object.defineProperty(HTMLElement.prototype,'focus',{value:undefined,configurable:true}); }
  },{snapshot,options});
  await serveUI(native);
  await native.goto('http://grz-session.test/SessionStats.html');
  await native.waitForFunction(()=>window.__grzCommands.some(args=>args.action==='resize'));
  return native;
}

(async function () {
  const browser = await chromium.launch({executablePath:process.env.GRZ_CHROME,headless:true,args:['--no-sandbox']});
  try {
  const page = await browser.newPage({viewport:{width:744,height:730},colorScheme:'dark',timezoneId:'UTC'});
  page.on('pageerror',e=>errors.push(String(e)));
  await serveUI(page);
  await page.goto('http://grz-session.test/SessionStats.html');
  await page.waitForFunction(()=>window.GRZSessionStats);
  await page.evaluate(data=>{
    window.GRZ_DEMO_FIXTURES=data;
    const toolbar=document.createElement('div');
    toolbar.innerHTML='<button id="demo-reopen">Otwórz panel</button><button id="demo-restart">Przywróć przykład</button>';
    document.body.appendChild(toolbar);
  },fixtures);
  await page.addScriptTag({path:path.join(root,'preview/controller.js')});
  await page.locator('#ss-groups .ss-group').first().waitFor();

  // User's native screenshot: direct <button> text was invisible; span captions
  // inside the existing flex footer button survived. Model that failure explicitly.
  // This is a regression fixture for that observation, not a Gameface emulator.
  const textRegression=await page.evaluate(expected=>{
    function discardDirectText(button) {
      Array.from(button.childNodes).filter(node=>node.nodeType===3).forEach(node=>button.removeChild(node));
    }
    const oldButton=document.createElement('button');
    oldButton.textContent='Od uruchomienia';
    discardDirectText(oldButton);
    Object.keys(expected).forEach(id=>discardDirectText(document.getElementById(id)));
    return {legacyFails:oldButton.textContent==='',
      captionsSurvive:Object.keys(expected).every(id=>document.getElementById(id).textContent===expected[id])};
  },captions);
  check('Missing anonymous button text fixture rejects v0.2 markup',textRegression.legacyFails);
  check('Every caption survives the observed direct-text failure',textRegression.captionsSurvive);
  let controls=await controlLayout(page);
  check('All twelve controls have explicit caption nodes',controls.length===12 && controls.every(c=>c.explicit && !c.directText));
  check('Visible controls have flex boxes, block captions and nonzero fitted labels',controls.filter(c=>c.visible).every(c=>c.flex && c.block && c.fits));
  check('Panel and captions use normal Warhelios rather than PFDINMax',controls.every(c=>c.font==='Warhelios') && await page.evaluate(()=>getComputedStyle(document.body).fontFamily.split(',')[0].trim()==='Warhelios'));
  check('Native content avoids unsupported main, section and article tags',await page.locator('#grz-session-stats main,#grz-session-stats section,#grz-session-stats article').count()===0);
  check('Offline preview retains its independent viewport height',await page.evaluate(()=>!document.documentElement.classList.contains('ss-native-document') && document.body.getBoundingClientRect().height===730));
  // Simulate the client's ignored auto margin. Close must remain at the right edge.
  await page.addStyleTag({content:'#ss-close { margin-left:0 !important; }'});
  check('Close stays pinned to the titlebar right edge without auto margins',await page.locator('#ss-close').evaluate(button=>{
    const box=button.getBoundingClientRect(), bar=button.parentNode.getBoundingClientRect();
    return getComputedStyle(button).position==='absolute' && Math.abs(bar.right-box.right-9)<1 && Math.abs(box.top-bar.top-6)<1;
  }));
  const kpis=()=>page.locator('#ss-summary .ss-kpi-value').allTextContents();
  let values=await kpis();
  check('Launch has 16 completed battles',values[0]==='16');
  check('Default view is tanks/base XP',(await page.evaluate(()=>GRZSessionStats.getState())).group==='vehicles' && (await page.evaluate(()=>GRZSessionStats.getState())).xp==='base');
  check('Full integer WN8 is shown',values[2]==='2236');
  check('Summary and tank details are present without expanding',await page.locator('#ss-summary .ss-details').isVisible() && await page.locator('#ss-groups .ss-details').count()===3);
  const wrappedMetricLabels=await page.locator('.ss-metric-row .ss-metric-name .ss-cell-value').evaluateAll(labels=>labels.map(label=>{
      const range=document.createRange(); range.selectNodeContents(label);
      return {text:label.textContent,height:range.getBoundingClientRect().height,
        lineHeight:parseFloat(getComputedStyle(label).lineHeight),width:label.getBoundingClientRect().width,
        group:label.closest('.ss-group')?label.closest('.ss-group').getAttribute('data-group-id'):'summary'};
    }).filter(label=>label.height>label.lineHeight+1));
  check('Aggregate metric labels stay on one line in the standard-width panel'+(wrappedMetricLabels.length?' '+JSON.stringify(wrappedMetricLabels):''),wrappedMetricLabels.length===0);
  check('No more-details buttons or accordions',await page.locator('details,[aria-expanded]').count()===0);
  check('One vertical scroll area works',await page.locator('#ss-scroll').evaluate(el=>el.scrollHeight>el.clientHeight));
  await page.locator('#grz-session-stats').screenshot({path:path.join(root,'preview/qa-compact.png')});
  const before=await page.locator('#ss-summary .ss-metric-row').first().innerText();
  await page.locator('#ss-xp-received').click();
  const after=await page.locator('#ss-summary .ss-metric-row').first().innerText();
  check('Received XP differs from base XP',before!==after && after.includes('Otrzymane PD'));
  await page.locator('#ss-group-maps').click();
  check('Map grouping contains all five maps',await page.locator('#ss-groups .ss-group').count()===5);
  await page.locator('#ss-scroll').evaluate(el=>el.scrollTop=el.scrollHeight);
  check('Mouse/scroll position can reach last group',await page.locator('#ss-scroll').evaluate(el=>el.scrollTop>0));
  await page.locator('#ss-scope-manual').click();
  check('Manual session contains previous launch too',(await kpis())[0]==='25');
  check('Changing scope keeps selected grouping',(await page.evaluate(()=>GRZSessionStats.getState())).group==='maps');
  await page.locator('#ss-group-battles').click();
  check('Per-battle list available',await page.locator('#ss-groups .ss-group').count()===25);
  let battles=await battleCards(page);
  const expectedBattles=new Map(fixtures.normal.scopes.manual.battles.map(row=>[row.id,row]));
  check('Each battle shows one XP and one WN8 value without min/mean/max rows',
    battles.every(row=>row.values.length===2 && row.aggregateRows===0));
  check('Received XP and WN8 match each individual battle result',battles.every(row=>{
    const stats=expectedBattles.get(row.id).stats;
    return row.values[0].label==='Otrzymane PD' && row.values[0].value===formattedInteger(stats.xp_received.sum) &&
      row.values[1].label==='WN8' && row.values[1].value===String(Math.round(stats.wn8));
  }));
  check('Battle header shows the actual outcome without one-battle count or win-rate KPIs',battles.every(row=>{
    const outcomes={win:'Zwycięstwo',loss:'Porażka',draw:'Remis'};
    return row.aggregateKPIs===0 && row.outcome===outcomes[expectedBattles.get(row.id).outcome];
  }));
  check('Aggregate summary still has min/mean/max while the battle list is selected',
    (await page.locator('#ss-summary .ss-metric-head .ss-metric-number').allTextContents()).join('|')==='Min|Średnia|Max' &&
    await page.locator('#ss-summary .ss-metric-row').count()===2);
  await page.locator('#ss-xp-base').click();
  battles=await battleCards(page);
  check('XP switch changes every battle to its single base-XP result',battles.every(row=>
    row.values[0].label==='Bazowe PD' && row.values[0].value===formattedInteger(expectedBattles.get(row.id).stats.xp_base.sum)));
  const knownBattle=battles.find(row=>row.id==='2000015');
  check('Battle finances retain separate income, costs and net including bonds',
    knownBattle.money[0].label==='Kredyty' && knownBattle.money[0].values.join('|')==='78\u00a0935|-41\u00a0385|+37\u00a0550' &&
    knownBattle.money[1].label==='Obligacje' && knownBattle.money[1].values.join('|')==='0|-6|-6');
  await page.locator('#ss-reset').click();
  controls=await controlLayout(page);
  check('Reset and confirmation captions also have visible fitted boxes',controls.filter(c=>['ss-reset','ss-reset-cancel','ss-reset-confirm'].includes(c.id)).every(c=>c.visible && c.flex && c.block && c.fits));
  await page.locator('#ss-reset-cancel').click();
  check('Cancel does not reset manual session',(await kpis())[0]==='25');
  await page.locator('#ss-reset').click();
  await page.locator('#ss-reset-confirm').click();
  check('Confirmed manual reset produces empty stats',(await kpis())[0]==='0' && (await kpis())[2]==='—');
  await page.locator('#ss-scope-launch').click();
  check('Manual reset leaves launch session intact',(await kpis())[0]==='16');
  await page.locator('#ss-close').click();
  check('Preview close action is wired',!(await page.locator('#grz-session-stats').isVisible()));
  await page.locator('#demo-reopen').click();
  check('Preview can reopen',await page.locator('#grz-session-stats').isVisible());
  await page.locator('#demo-restart').click();

  const overflow=[],textOverflow=[];
  for(const width of [744,620,560,420,360,320]) {
    await page.setViewportSize({width,height:820});
    for(const view of ['vehicles','maps','battles']) {
      await page.locator('#ss-group-'+view).click();
      const result=await page.locator('#grz-session-stats').evaluate(el=>{
        const rect=el.getBoundingClientRect();
        const bad=Array.from(el.querySelectorAll('*')).filter(x=>{
          const r=x.getBoundingClientRect(); const s=getComputedStyle(x);
          return r.width>0 && s.display!=='none' && (r.right>rect.right+1 || r.left<rect.left-1);
        }).map(x=>x.className).slice(0,8);
        return {w:rect.width,scroll:el.scrollWidth,client:el.clientWidth,bad};
      });
      if(result.scroll>result.client+1 || result.bad.length) overflow.push({width,view,...result});
      const text=await numericTextOverflow(page);
      if(text.length) textOverflow.push({width,view,bad:text});
    }
  }
  check('No horizontal layout overflow from 320 to 744px'+(overflow.length?' '+JSON.stringify(overflow):''),overflow.length===0);
  check('Rendered result text fits inside its padded cells from 320 to 744px'+(textOverflow.length?' '+JSON.stringify(textOverflow):''),textOverflow.length===0);

  // Stress the display with full amounts and XP without abbreviating values.
  // These are formatting fixtures, not imported account or battle records.
  const largeNumberFixture=JSON.parse(JSON.stringify(fixtures.normal));
  const largeStats=[largeNumberFixture.scopes.launch.summary];
  for(const grouping of ['vehicles','maps','battles']) {
    largeNumberFixture.scopes.launch[grouping].forEach(row=>largeStats.push(row.stats));
  }
  largeStats.forEach((stats,index)=>{
    for(const field of ['xp_base','xp_received']) {
      for(const value of ['min','avg','max','sum']) stats[field][value]=123456;
    }
    stats.wn8=10420;
    for(const value of ['min','avg','max','sum']) stats.battle_wn8[value]=10420;
    stats.win_rate=100;
    stats.currencies.credits.income=index%2?0:24691356;
    stats.currencies.credits.costs=12345678;
    stats.currencies.credits.net=index%2?-12345678:12345678;
  });
  await page.evaluate(p=>GRZSessionStats.update(p),largeNumberFixture);
  const largeTextOverflow=[];
  for(const width of [744,620,560,420,360,320]) {
    await page.setViewportSize({width,height:820});
    for(const view of ['vehicles','maps','battles']) {
      await page.locator('#ss-group-'+view).click();
      const text=await numericTextOverflow(page);
      if(text.length) largeTextOverflow.push({width,view,bad:text});
    }
  }
  check('Full large credits, six-digit XP and five-digit WN8 fit the padded layout'+(largeTextOverflow.length?' '+JSON.stringify(largeTextOverflow):''),largeTextOverflow.length===0);
  await page.evaluate(p=>GRZSessionStats.update(p),fixtures.normal);
  await page.setViewportSize({width:744,height:730});
  await page.locator('#ss-group-vehicles').click();
  await page.locator('#ss-xp-base').click();
  await page.locator('#ss-scroll').evaluate(el=>el.scrollTop=0);
  await page.locator('#grz-session-stats').screenshot({path:path.join(root,'preview/qa-final.png')});
  await page.locator('#ss-group-battles').click();
  await page.locator('#ss-scroll').evaluate(el=>el.scrollTop=document.getElementById('ss-group-tabs').offsetTop-el.offsetTop);
  await page.locator('#grz-session-stats').screenshot({path:path.join(root,'preview/qa-battles.png')});
  await page.locator('#ss-group-vehicles').click();

  const malformed=await page.evaluate(()=>GRZSessionStats.update('{bad json'));
  check('Malformed payload returns readable error',malformed===false && (await page.locator('#ss-status').innerText()).includes('Nie udało'));
  await page.evaluate(p=>GRZSessionStats.update(p),fixtures.normal);
  await page.evaluate(p=>{const q=JSON.parse(JSON.stringify(p));q.scopes.launch.summary.wn8=10420;GRZSessionStats.update(q);},fixtures.normal);
  check('WN8 above 9999 is not truncated',(await kpis())[2]==='10420');
  await page.evaluate(p=>{const q=JSON.parse(JSON.stringify(p));q.scopes.launch.summary.wn8=805;GRZSessionStats.update(q);},fixtures.normal);
  check('WN8 below 1000 has no artificial padding',(await kpis())[2]==='805');
  await page.evaluate(p=>{const q=JSON.parse(JSON.stringify(p));q.scopes.launch.summary.currencies.bonds.net=null;q.scopes.launch.summary.currencies.bonds.net_count=0;GRZSessionStats.update(q);},fixtures.normal);
  check('Missing bond net is a dash, not zero',(await page.locator('#ss-summary .ss-money-row').nth(1).innerText()).includes('—'));
  await page.evaluate(p=>{const q=JSON.parse(JSON.stringify(p));q.scopes.launch.summary.currencies.credits.net=-5484;GRZSessionStats.update(q);},fixtures.normal);
  check('Negative balance and costs use the client-readable ASCII minus',
    (await page.locator('#ss-summary .ss-money-row').first().locator('.ss-money-value').nth(2).innerText())==='-5\u00a0484' &&
    (await page.locator('#ss-summary .ss-money-row').first().locator('.ss-money-value').nth(1).innerText()).startsWith('-'));
  await page.evaluate(p=>GRZSessionStats.update(p),fixtures.normal);

  // Missing data must not turn into a fabricated zero when a battle uses a
  // single series sum; zero is nevertheless a valid known battle result.
  await page.locator('#ss-group-battles').click();
  await page.evaluate(p=>{
    const q=JSON.parse(JSON.stringify(p)), source=q.scopes.launch.battles[0];
    const zero=JSON.parse(JSON.stringify(source)), missing=JSON.parse(JSON.stringify(source));
    zero.id='qa-battle-zero'; zero.started_at=1800000001;
    missing.id='qa-battle-missing'; missing.started_at=1800000000;
    for(const field of ['xp_base','xp_received','battle_wn8']) {
      zero.stats[field]={min:0,avg:0,max:0,sum:0,count:1};
      missing.stats[field]={min:null,avg:null,max:null,sum:0,count:0};
    }
    zero.stats.wn8=0; zero.stats.wn8_count=1;
    missing.stats.wn8=null; missing.stats.wn8_count=0;
    missing.stats.currencies.bonds.net=null; missing.stats.currencies.bonds.net_count=0;
    missing.outcome=null;
    q.scopes.launch.battles=[zero,missing];
    GRZSessionStats.update(q);
  },fixtures.normal);
  for(const xpMode of ['base','received']) {
    await page.locator('#ss-xp-'+xpMode).click();
    battles=await battleCards(page);
    check('Known zero XP/WN8 remain zero in a single battle ('+xpMode+')',
      battles.find(row=>row.id==='qa-battle-zero').values.every(value=>value.value==='0'));
    const missing=battles.find(row=>row.id==='qa-battle-missing');
    check('Unavailable XP/WN8 remain dashes in a single battle ('+xpMode+')',
      missing.values.every(value=>value.value==='—'));
    check('Unknown battle outcome and unavailable bond balance stay explicit ('+xpMode+')',
      missing.outcome==='Nieznany wynik' && missing.money[1].values[2]==='—');
  }
  await page.evaluate(p=>GRZSessionStats.update(p),fixtures.normal);
  for(const grouping of ['maps','vehicles']) {
    await page.locator('#ss-group-'+grouping).click();
    check('Min/mean/max battle statistics remain available for '+grouping,
      await page.locator('#ss-groups .ss-battle-measure').count()===0 &&
      (await page.locator('#ss-groups .ss-group').first().locator('.ss-metric-head .ss-metric-number').allTextContents()).join('|')==='Min|Średnia|Max' &&
      await page.locator('#ss-groups .ss-group').first().locator('.ss-metric-row').count()===2);
  }
  await page.locator('#ss-xp-base').click();

  // Synthetic local names test only the visual contract and layout. They are not
  // bundled game art or evidence of a successfully loaded native WoT texture.
  const visualFixture=JSON.parse(JSON.stringify(fixtures.normal));
  for(const [group,kind] of [['vehicles','vehicle'],['maps','map'],['battles','vehicle']]) {
    visualFixture.scopes.launch[group][0].visual={kind,src:'img://gui/maps/icons/'+kind+'/__qa_contract__.png',alt:visualFixture.scopes.launch[group][0].name};
  }
  await page.evaluate(p=>GRZSessionStats.update(p),visualFixture);
  for(const group of ['vehicles','maps','battles']) {
    await page.locator('#ss-group-'+group).click();
    check('Verified local visual contract is used in '+group,await page.locator('#ss-groups .ss-group-thumb').count()===1 && await page.locator('#ss-groups .ss-group-thumb').evaluate(thumb=>{
      const style=getComputedStyle(thumb), box=thumb.getBoundingClientRect();
      return style.backgroundImage.includes('img://gui/maps/icons/') && style.backgroundSize==='contain' &&
        box.width===54 && box.height===32 && thumb.getAttribute('aria-label').length>0;
    }));
  }
  await page.locator('#ss-group-vehicles').click();
  await page.setViewportSize({width:320,height:820});
  check('Thumbnail leaves tank identity and KPIs within the narrow panel',await page.locator('#ss-groups .ss-group').first().evaluate(group=>{
    const panel=document.getElementById('grz-session-stats').getBoundingClientRect();
    return Array.from(group.querySelectorAll('.ss-group-thumb,.ss-group-name,.ss-group-kpi')).every(node=>{
      const box=node.getBoundingClientRect();return box.width>0 && box.left>=panel.left && box.right<=panel.right;
    });
  }));
  await page.setViewportSize({width:744,height:730});
  const invalidVisuals=[
    'https://example.invalid/tank.png', 'data:image/png;base64,AA==', 'coui://gui/maps/icons/vehicle/test.png',
    'img://gui/maps/icons/map/wrong-family.png', 'img://gui/maps/icons/vehicle/../outside.png',
    'img://gui/maps/icons/vehicle/test.png?query', 'img://gui/maps/icons/vehicle/test.png#fragment',
    'img://gui/maps/icons/vehicle/sub\\image.png', 'img://gui/maps/icons/vehicle/test");color:red'
  ];
  let rejected=0;
  for(const src of invalidVisuals) {
    const q=JSON.parse(JSON.stringify(fixtures.normal));
    q.scopes.launch.vehicles[0].visual={kind:'vehicle',src};
    await page.evaluate(p=>GRZSessionStats.update(p),q);
    if(await page.locator('#ss-groups .ss-group-thumb').count()===0) { rejected++; }
  }
  check('Visuals reject remote, escaped, traversing and mismatched resource paths',rejected===invalidVisuals.length);
  await page.evaluate(p=>GRZSessionStats.update(p),fixtures.normal);
  check('Old records without a visual keep their names and stats without a fake thumbnail',await page.locator('#ss-groups .ss-group-thumb').count()===0 && (await kpis())[0]==='16');

  await page.locator('#ss-group-battles').click();
  await page.evaluate(p=>{
    const q=JSON.parse(JSON.stringify(p));const list=q.scopes.launch.battles;const long=[];
    for(let n=0;n<200;n++){const row=JSON.parse(JSON.stringify(list[n%list.length]));row.id='long-'+n;row.started_at=1800000000-n;long.push(row);}
    q.scopes.launch.battles=long;GRZSessionStats.update(q);
  },fixtures.normal);
  check('Long battle history starts with a bounded batch',await page.locator('#ss-groups .ss-group').count()===40);
  await page.locator('#ss-scroll').evaluate(el=>{el.scrollTop=el.scrollHeight;el.dispatchEvent(new Event('scroll'));});
  await page.waitForFunction(()=>document.querySelectorAll('#ss-groups .ss-group').length>40);
  check('Scrolling appends more battles without a button',await page.locator('#ss-groups .ss-group').count()>40);
  await page.evaluate(p=>GRZSessionStats.update(p),fixtures.normal);
  await page.locator('#ss-group-vehicles').click();

  // Host mocks check the actual bridge failure paths. They do not render with Coherent.
  const native=await nativeHost(browser,{viewport:{width:1440,height:900,scale:1.25},changedScale:1.5,drag:'supported',initialViewport:{width:1,height:1}});
  await native.locator('#ss-groups .ss-group').first().waitFor();
  check('Fake native host binds model payload',(await native.evaluate(()=>GRZSessionStats.getState())).nativeBound===true);
  check('Python GUI scale takes precedence over optional rem helper',await native.evaluate(()=>document.documentElement.style.fontSize==='1.25px' && __grzHelperCalls.rem===0));
  check('Initial one-pixel native surface does not clip the measured panel',await native.evaluate(()=>__nativeSize[0]===875 && __nativeSize[1]===775));
  check('Native document height follows the panel instead of the initial surface',await native.evaluate(()=>document.documentElement.classList.contains('ss-native-document') && document.body.getBoundingClientRect().height===775 && document.documentElement.getBoundingClientRect().height===775));
  await native.setViewportSize({width:1440,height:900});
  await native.locator('#ss-titlebar h1').dispatchEvent('mousedown',{button:0});
  await native.evaluate(()=>document.dispatchEvent(new MouseEvent('mousemove',{clientX:410,clientY:250,bubbles:true})));
  await native.evaluate(()=>document.dispatchEvent(new MouseEvent('mouseup',{button:0,bubbles:true})));
  check('Titlebar drag delegates the exact native move start and stop events',await native.evaluate(()=>{
    const events=__grzWindowEvents;
    return events.length===2 && events[0].on===true && events[1].on===false &&
      events.every(x=>x.__Type==='GFViewEventProxy' && x.type===16 && x.isMouseEvent===true) &&
      __grzCommands.filter(x=>x.action==='drag').map(x=>x.active).join(',')==='true,false';
  }));
  check('Native drag never translates the HTML inside its surface',await native.locator('#grz-session-stats').evaluate(panel=>panel.style.left==='' && panel.style.top==='' && panel.style.transform===''));
  await native.locator('#ss-titlebar').dispatchEvent('mousedown',{button:2});
  await native.locator('#ss-close').dispatchEvent('mousedown',{button:0});
  check('Right click and close button do not initiate native dragging',await native.evaluate(()=>__grzWindowEvents.length===2));
  await native.locator('#ss-scope-manual').click();
  await native.locator('#ss-reset').click();
  await native.locator('#ss-titlebar').dispatchEvent('mousedown',{button:0});
  check('Reset confirmation blocks titlebar dragging',await native.evaluate(()=>__grzWindowEvents.length===2 && !GRZSessionStats.getState().dragging));
  await native.locator('#ss-reset-cancel').click();
  await native.locator('#ss-scope-launch').click();
  await native.locator('#ss-titlebar').dispatchEvent('mousedown',{button:0});
  await native.evaluate(()=>window.dispatchEvent(new Event('blur')));
  check('Losing focus ends native drag',await native.evaluate(()=>__grzWindowEvents.length===4 && __grzWindowEvents[3].on===false && !GRZSessionStats.getState().dragging));
  await native.locator('#ss-refresh').click();
  check('Native commands are sent as one map',await native.evaluate(()=>__grzCommands.some(x=>x.action==='refresh' && typeof x==='object')));
  await native.evaluate(()=>__grzEvents['self.onScaleUpdated']());
  await native.waitForFunction(()=>document.documentElement.style.fontSize==='1.5px' && __nativeSize[1]===880);
  check('Scale change refreshes the viewport and stays within the parent',await native.evaluate(()=>__grzCommands.some(x=>x.action==='viewport') && __nativeSize[0]===1050 && __nativeSize[1]===880));
  check('Native diagnostics are bounded to three stages',await native.evaluate(()=>{
    const messages=__grzCommands.filter(x=>x.action==='diagnostic');
    return messages.length===3 && messages.map(x=>x.stage).join(',')==='dom_ready,model_bound,layout_ready' &&
      messages.every(x=>Object.keys(x).every(k=>['action','stage','width','height','scale'].includes(k)));
  }));
  await native.evaluate(()=>{model.payload=JSON.stringify({version:'0.2.0',scopes:{launch:{summary:{battles:0,wins:0,losses:0,draws:0},vehicles:[],maps:[],battles:[]},manual:{summary:{battles:0,wins:0,losses:0,draws:0},vehicles:[],maps:[],battles:[]}}});__grzEvents['viewEnv.onDataChanged']();});
  check('Native model push updates UI',await native.locator('#ss-summary .ss-kpi-value').first().innerText()==='0');
  for(const callback of ['throw-once','throw']) {
    const degraded=await nativeHost(browser,{callback});
    check('Failed callback registration still renders and sizes the initial model ('+callback+')',await degraded.evaluate(()=>
      GRZSessionStats.getState().nativeBound && document.querySelectorAll('#ss-groups .ss-group').length===3 &&
      __grzCommands.some(x=>x.action==='resize') && __grzHelperCalls.callback===1));
    await degraded.evaluate(()=>{
      const changed=JSON.parse(model.payload);changed.scopes.launch.summary.battles=0;
      model.payload=JSON.stringify(changed);__grzEvents['viewEnv.onDataChanged']();
      __grzEvents['viewEnv.onDataChanged']();
    });
    check('Model updates retry optional registration without duplicate engine listeners ('+callback+')',await degraded.evaluate(mode=>
      document.querySelector('#ss-summary .ss-kpi-value').textContent==='0' && __grzEngineOn.length===2 &&
      __grzHelperCalls.callback===(mode==='throw-once'?2:3),callback));
    await degraded.evaluate(()=>{
      window.__grzCallsBeforeDestroy=__grzHelperCalls.callback;
      GRZSessionStats.destroy();
      __grzEvents['viewEnv.onDataChanged']();
    });
    check('Cleanup removes only a successfully registered callback ('+callback+')',await degraded.evaluate(mode=>
      !GRZSessionStats.getState().nativeBound && __grzHelperCalls.callback===__grzCallsBeforeDestroy &&
      __grzRemovedCallbacks.join(',')===(mode==='throw-once'?'71':''),callback));
    await degraded.close();
  }
  for(const helpers of ['absent','throw']) {
    const degraded=await nativeHost(browser,{helpers,noFocus:true,drag:helpers});
    check('Python resize is still sent when native helpers are '+helpers,await degraded.evaluate(()=>__grzCommands.some(x=>x.action==='resize' && x.width==='700' && x.height==='620')));
    await degraded.locator('#ss-scope-manual').click();
    await degraded.locator('#ss-reset').click();
    await degraded.locator('#ss-reset-cancel').click();
    check('Scope and reset controls work without focus and with '+helpers+' helpers',(await degraded.locator('#ss-summary .ss-kpi-value').first().innerText())==='25');
    await degraded.locator('#ss-titlebar').dispatchEvent('mousedown',{button:0});
    check('Unavailable native move proxy does not fake a DOM drag ('+helpers+')',await degraded.evaluate(()=>!GRZSessionStats.getState().dragging && !__grzCommands.some(x=>x.action==='drag')));
    await degraded.close();
  }
  await native.locator('#ss-titlebar').dispatchEvent('mousedown',{button:0});
  await native.evaluate(()=>GRZSessionStats.destroy());
  const dragEventsAfterDestroy=await native.evaluate(()=>__grzWindowEvents.length);
  await native.locator('#ss-titlebar').dispatchEvent('mousedown',{button:0});
  check('Destroy ends the native drag and removes titlebar listeners',await native.evaluate(count=>__grzWindowEvents.length===count && __grzWindowEvents[count-1].on===false && !GRZSessionStats.getState().dragging,dragEventsAfterDestroy));
  check('No browser JavaScript errors',errors.length===0);
  const report={passed:checks.length,checks,errors,overflow,textOverflow,largeTextOverflow,live_gameface_tested:false,
    regression_fixture:'Models the observed loss of direct button text; actual Coherent rendering still needs an in-game check.'};
  fs.writeFileSync(path.join(root,'tests/ui-report.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));
  } finally {
    await browser.close();
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
