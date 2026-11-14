/* Source -> native result -> Back restores the owned view, page and anchor. */
const assert=require('assert'),path=require('path'),readline=require('readline'),{spawn}=require('child_process');
const frames=(page,count=8)=>page.evaluate(count=>new Promise(resolve=>{function next(){if(--count)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}),count);
function nativeDriver(){
  const root=path.resolve(__dirname,'..'),pending=new Map();let sequence=0,stderr='';
  const child=spawn(process.env.GRZ_PYTHON3||'python3',['-u','-c',`
import copy, json, sys, tempfile, traceback
from test_core import Clock, EXPECTED, result
from grz_session_stats.core import StatsService
from grz_session_stats.projection import DEFAULT_ORDER
with tempfile.TemporaryDirectory(prefix='grz-return-navigation-') as directory:
    clock = Clock(100)
    service = StatsService(directory, 'SYNTHETIC:return-navigation', 'return-launch', EXPECTED, clock, timeline_enabled=True)
    clock.value = 2000
    rows = {}
    for index in range(125):
        row = result('return-row-{0:03d}'.format(index), 110 + index, ended_at=500 + index,
                     xp_base=100 + index, xp_received=12345 if index == 0 else 500 + index,
                     vehicle_name='Synthetic vehicle', map_id='return-map-{0:03d}'.format(index),
                     map_name='Synthetic map {0:03d}'.format(index))
        row.update(_manual_id=service._state['current_manual_id'], _launch_id=service.launch_id,
                   _updated_at=1000, _result_seen=True, revision=1)
        rows[row['arena_id']] = row
    service._state['battles'] = rows
    service._rebuild_indexes()
    def snapshot():
        payload = service.snapshot()
        payload['scopes']['timeline'] = service.timeline_snapshot()
        return copy.deepcopy(payload)
    for line in sys.stdin:
        try:
            request = json.loads(line)
            command = request['command']
            action = command.get('action')
            scope = service.timeline_snapshot()
            period = scope['period_id']
            accepted = True
            if action == 'configure':
                assert service.set_order('timeline', 'battles', dict(DEFAULT_ORDER), period)
                assert service.set_page('timeline', 'battles', 0, period)
                assert service.set_order('timeline', 'maps', dict(DEFAULT_ORDER, metric='xp_base', statistic='max', direction='asc', chronology='oldest'), period)
                assert service.set_page('timeline', 'maps', 0, period)
            elif action == 'revise':
                row = copy.deepcopy(service._state['battles']['return-row-060'])
                row.update(damage=row.get('damage', 1000) + 1, reconcile=True)
                assert service.record_result(row)
            elif action in ('page', 'sort', 'battle_select'):
                accepted = command.get('account_key') == service.account_key
                if accepted and action == 'page':
                    accepted = service.set_page(command['scope'], command['group'], int(command['page']), command['period_id'], command.get('request_id'))
                elif accepted and action == 'sort':
                    options = dict((key, command[key]) for key in ('metric', 'statistic', 'direction', 'chronology'))
                    accepted = service.set_order(command['scope'], command['group'], options, command['period_id'])
                elif accepted:
                    accepted = service.select_battle(command['scope'], command['id'], command['period_id'], command['request_id'])
            elif action != 'snapshot':
                raise ValueError('Unexpected synthetic bridge command: ' + str(action))
            print(json.dumps({'sequence':request['sequence'], 'accepted':bool(accepted), 'payload':snapshot()}))
        except Exception:
            print(json.dumps({'sequence':request.get('sequence'), 'error':traceback.format_exc()}))
`],{cwd:root,env:{...process.env,PYTHONPATH:[path.join(root,'src'),__dirname].join(path.delimiter)},stdio:['pipe','pipe','pipe']});
  child.stderr.on('data',chunk=>{stderr=(stderr+chunk.toString()).slice(-8000);});
  const rejectAll=error=>{for(const [id,item]of pending){clearTimeout(item.timer);item.reject(error);pending.delete(id);}};
  child.on('error',rejectAll);child.on('exit',(code,signal)=>rejectAll(new Error('Synthetic native driver exited '+code+'/'+signal+' '+stderr)));
  const lines=readline.createInterface({input:child.stdout});
  lines.on('line',line=>{let reply;try{reply=JSON.parse(line);}catch(error){rejectAll(new Error('Invalid synthetic native reply: '+line.slice(0,200)));return;}
    const item=pending.get(reply.sequence);if(!item)return;pending.delete(reply.sequence);clearTimeout(item.timer);
    if(reply.error)item.reject(new Error(reply.error));else item.resolve(reply);});
  return {request(command){return new Promise((resolve,reject)=>{const id=++sequence,timer=setTimeout(()=>{pending.delete(id);reject(new Error('Synthetic native response timed out: '+JSON.stringify(command)+' '+stderr));},10000);
    pending.set(id,{resolve,reject,timer});child.stdin.write(JSON.stringify({sequence:id,command})+'\n');});},close(){lines.close();child.stdin.end();child.kill();rejectAll(new Error('Synthetic native driver closed'));}};
}
module.exports=async({browser,nativeHost,check})=>{
  const driver=nativeDriver(),page=await nativeHost(browser,{initialViewport:{width:1800,height:1400},viewport:{width:1800,height:1400,scale:1},realTimers:true});
  const sourceCard='return-map-045',mapSource='#ss-groups [data-group-id="'+sourceCard+'"] .ss-metric-battle-link[data-ss-source-metric="xp_received"][data-ss-extreme="max"]';
  const summarySource='#ss-summary .ss-metric-battle-link[data-ss-source-metric="xp_received"][data-ss-extreme="max"]';
  try{
    await page.exposeFunction('__returnNativeCommand',async command=>{const reply=await driver.request(command);if(!reply.accepted)throw new Error('Owned synthetic native command rejected: '+JSON.stringify(command));return reply.payload;});
    await page.evaluate(()=>{
      window.__returnBridgeErrors=[];window.__returnBridgePending=0;
      const previous=model.onAction;
      model.onAction=function(command){previous.call(this,command);if(!['battle_select','page','sort'].includes(command.action)||window.__returnBridgeFrozen)return;
        __returnBridgePending++;
        __returnNativeCommand(command).then(payload=>{
          if(window.__returnHoldPrefix&&command.action==='page'&&command.group==='maps'&&command.page==='0'){window.__returnHeldPrefix={command,payload};return;}
          const previousPayload=JSON.parse(model.payload);payload.viewport=previousPayload.viewport;payload.window_size=[900,1050];
          model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
        }).catch(error=>__returnBridgeErrors.push(String(error))).finally(()=>{__returnBridgePending--;});
      };
    });
    async function publish(payload){await page.evaluate(payload=>{payload.viewport=JSON.parse(model.payload).viewport;payload.window_size=[900,1050];model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);},payload);await frames(page);}
    async function configure(view){await page.evaluate(()=>{window.__returnBridgeFrozen=false;});const reply=await driver.request({action:'configure',view});await publish(reply.payload);await page.locator('#ss-scope-launch').click();await page.locator('#ss-scope-manual').click();await page.locator('#ss-group-'+view).click();await ready(view);await page.locator('#ss-page-next').click();await page.locator('#ss-groups .ss-continuous-page[data-page-index="1"]').waitFor({state:'visible',timeout:5000});await ready(view);await stopAutomaticNavigation();}
    async function stopAutomaticNavigation(){const box=await page.locator('#ss-scroll').boundingBox();await page.mouse.move(box.x+20,box.y+Math.min(100,box.height/2));await page.mouse.wheel(0,1);await frames(page,10);}
    async function opened(){await page.locator('#ss-groups .ss-battle-target .ss-battle-return').waitFor({state:'visible',timeout:5000});await frames(page);}
    async function ready(group){await page.waitForFunction(group=>document.getElementById('ss-group-'+group).getAttribute('aria-pressed')==='true'&&__returnBridgePending===0&&document.getElementById('ss-groups').getAttribute('aria-busy')!=='true',group,{timeout:5000});await frames(page,12);}
    async function geometry(identifier){return page.evaluate(identifier=>{const card=[...document.querySelectorAll('#ss-groups .ss-group')].find(node=>node.getAttribute('data-group-id')===identifier),scroll=document.getElementById('ss-scroll'),box=scroll.getBoundingClientRect();const edge=Math.max(box.top,document.getElementById('ss-filter-panel').getBoundingClientRect().bottom),visible=[...document.querySelectorAll('.ss-continuous-page')].find(section=>{const r=section.getBoundingClientRect();return r.bottom>edge&&r.top<box.bottom;});return {offset:card?card.getBoundingClientRect().top-box.top:null,scroll:scroll.scrollTop,visiblePage:visible?Number(visible.getAttribute('data-page-index')):null,pageLabel:document.getElementById('ss-page-label').textContent,group:document.querySelector('.ss-group-tab[aria-pressed="true"]').id,pages:[...document.querySelectorAll('.ss-continuous-page')].map(node=>Number(node.getAttribute('data-page-index'))),payload:(scope=>({period_id:scope.period_id,data_revision:scope.data_revision,from_point:scope.from_point,to_point:scope.to_point,ordering:scope.ordering,pagination:scope.pagination}))(JSON.parse(model.payload).scopes.timeline)};},identifier);}
    // A fresh snapshot may stage a new feed while the old rendered pages
    // remain visible. The summary is fresh and can still open a source result.
    await configure('maps');
    await page.evaluate(()=>{document.getElementById('ss-scroll').scrollTop=40;});await frames(page,12);
    const stagedBefore=await geometry(sourceCard);
    await page.evaluate(()=>{window.__returnHoldPrefix=true;window.__returnHeldPrefix=null;window.__returnStagedCard=document.querySelector('#ss-groups [data-group-id="return-map-060"]');});
    // Select the incoming native page without replacing the existing browser
    // window; any earlier prefetch is free to have changed the server scalar.
    const incomingPage=await driver.request({action:'page',account_key:'SYNTHETIC:return-navigation',scope:'timeline',group:'maps',period_id:'timeline',page:'1',request_id:'staging-incoming-page'});
    assert(incomingPage.accepted,'Synthetic incoming native page is accepted');
    const stagedRevision=await driver.request({action:'revise'}),stagedScope=stagedRevision.payload.scopes.timeline;
    const stagedRating=stagedScope.maps.find(row=>row.id==='return-map-060').stats.wn8;
    await publish(stagedRevision.payload);
    await page.waitForFunction(()=>!!__returnHeldPrefix&&document.getElementById('ss-groups').getAttribute('aria-busy')==='true',null,{timeout:5000});
    const stagedFixture={pages:stagedBefore.pages,incoming:stagedScope.pagination.maps.page,revisionChanged:stagedScope.data_revision!==stagedBefore.payload.data_revision,same:await page.evaluate(()=>!!__returnStagedCard&&document.querySelector('#ss-groups [data-group-id="return-map-060"]')===__returnStagedCard)};
    check('A fresh revision stages prefix loading while keeping the old two-page source window visible '+JSON.stringify(stagedFixture),stagedFixture.pages.join(',')==='0,1'&&stagedFixture.incoming===1&&stagedFixture.revisionChanged&&stagedFixture.same);
    await page.locator(summarySource).click();await opened();
    await page.evaluate(()=>{window.__returnHoldPrefix=false;});
    await page.locator('.ss-battle-return').click();await ready('maps');
    await page.waitForFunction(top=>Math.abs(document.getElementById('ss-scroll').scrollTop-top)<=3,stagedBefore.scroll,{timeout:5000});
    const stagedAfter=await geometry(sourceCard);
    check('Back from a staged source restores its complete rendered page window rather than only the incoming page',stagedAfter.pages.join(',')===stagedBefore.pages.join(',')&&stagedAfter.visiblePage===stagedBefore.visiblePage&&Math.abs(stagedAfter.scroll-stagedBefore.scroll)<=3);
    check('Back from a staged revision refetches current values instead of reviving the old rendered cache',
      stagedAfter.payload.data_revision===stagedScope.data_revision&&Number((await page.locator('#ss-groups [data-group-id="return-map-060"] .ss-group-wn8-kpi .ss-kpi-value').textContent()).replace(/\s/g,''))===Math.round(stagedRating));
    check('Back from a staged summary source restores that exact action focus',await page.locator(summarySource).evaluate(node=>document.activeElement===node));
    await configure('maps');
    for(const scenario of [{name:'pointer',keyboard:false},{name:'keyboard',keyboard:true},{name:'revised',keyboard:false,revise:true}]){
      const keyboard=scenario.keyboard;
      await stopAutomaticNavigation();
      await page.locator('#ss-groups [data-group-id="'+sourceCard+'"]').scrollIntoViewIfNeeded();await frames(page);
      await page.evaluate(identifier=>{const card=[...document.querySelectorAll('#ss-groups .ss-group')].find(node=>node.getAttribute('data-group-id')===identifier),scroll=document.getElementById('ss-scroll'),filter=document.getElementById('ss-filter-panel');scroll.scrollTop+=card.getBoundingClientRect().top-scroll.getBoundingClientRect().top-filter.getBoundingClientRect().height-50;},sourceCard);await frames(page,12);
      const before=await geometry(sourceCard);
      check('Source anchor is captured from the visible clicked control '+scenario.name,await page.locator(mapSource).evaluate(node=>{const box=node.getBoundingClientRect(),viewport=document.getElementById('ss-scroll').getBoundingClientRect();return box.top>=viewport.top&&box.bottom<=viewport.bottom;}));
      if(keyboard)await page.locator(mapSource).press('Enter');else await page.locator(mapSource).click();
      await opened();
      let revisedRating=null;
      if(scenario.revise){const revised=await driver.request({action:'revise'});
        check('Revision fixture changes the actual native result generation',revised.payload.scopes.timeline.data_revision!==before.payload.data_revision);
        revisedRating=revised.payload.scopes.timeline.maps.find(row=>row.id==='return-map-060').stats.wn8;
        await publish(revised.payload);await opened();}
      const badge=await page.locator('.ss-battle-target .ss-battle-selection-banner').evaluate(banner=>{const button=banner.querySelector('.ss-battle-return'),label=banner.querySelector('.ss-battle-selection-label'),a=button.getBoundingClientRect(),b=label.getBoundingClientRect();return {tag:button.tagName,caption:button.getAttribute('aria-label'),left:a.right<=b.left+1,width:a.width,height:a.height};});
      check('Selected result offers a keyboard-native Back box left of its label '+scenario.name,badge.tag==='BUTTON'&&badge.caption==='Back to source'&&badge.left&&badge.width>=18&&badge.height>=18);
      if(keyboard)await page.locator('.ss-battle-target .ss-battle-return').press('Enter');else await page.locator('.ss-battle-target .ss-battle-return').click();
      await ready('maps');
      try{await page.waitForFunction(({identifier,offset})=>{const card=[...document.querySelectorAll('#ss-groups .ss-group')].find(node=>node.getAttribute('data-group-id')===identifier),scroll=document.getElementById('ss-scroll');return card&&Math.abs(card.getBoundingClientRect().top-scroll.getBoundingClientRect().top-offset)<=3;},{identifier:sourceCard,offset:before.offset},{timeout:5000});}catch(error){throw Error('Source anchor did not return: '+JSON.stringify({scenario:scenario.name,before,after:await geometry(sourceCard),bridge:await page.evaluate(()=>({errors:__returnBridgeErrors,commands:__grzCommands.filter(command=>['page','sort','battle_select'].includes(command.action)).slice(-8),state:GRZSessionStats.getState()}))}));}
      const after=await geometry(sourceCard);
      check('Back restores the exact Timeline map order, native page and loaded page window '+scenario.name,after.payload.period_id===before.payload.period_id&&after.payload.from_point===before.payload.from_point&&after.payload.to_point===before.payload.to_point&&JSON.stringify(after.payload.ordering.maps)===JSON.stringify(before.payload.ordering.maps)&&after.payload.pagination.maps.page===before.payload.pagination.maps.page&&after.pages.join(',')===before.pages.join(','));
      check('Back restores the source card anchor instead of resetting the viewport '+scenario.name,before.scroll>100&&Math.abs(after.offset-before.offset)<=3);
      check('Back restores focus to the exact source action '+scenario.name,await page.locator(mapSource).evaluate(node=>document.activeElement===node));
      if(scenario.revise)check('A revised return reloads fresh result values instead of reviving stale source cache',Number((await page.locator('#ss-groups [data-group-id="return-map-060"] .ss-group-wn8-kpi .ss-kpi-value').textContent()).replace(/\s/g,''))===Math.round(revisedRating));
    }
    for(const reordered of [false,true]){
      await configure('battles');
      await page.evaluate(()=>{document.getElementById('ss-scroll').scrollTop=40;});await frames(page,12);
      const summaryBefore=await geometry('return-row-084');
      await page.locator(summarySource).click();await opened();
      check('Summary source while Battles is open reaches a different native page '+reordered,await page.locator('.ss-battle-target').getAttribute('data-group-id')==='return-row-000');
      if(reordered){
        const sorted=await driver.request({action:'sort',account_key:'SYNTHETIC:return-navigation',scope:'timeline',group:'battles',period_id:'timeline',metric:'xp_received',statistic:'max',direction:'desc',chronology:'newest'});
        assert(sorted.accepted,'Synthetic destination sort is accepted by the real service');await publish(sorted.payload);await opened();
      }
      const commandStart=await page.evaluate(()=>__grzCommands.length);
      await page.locator('.ss-battle-return').click();await ready('battles');
      await page.waitForFunction(top=>Math.abs(document.getElementById('ss-scroll').scrollTop-top)<=3,summaryBefore.scroll,{timeout:5000});
      const summaryAfter=await geometry('return-row-084');
      // The latest native page can be a prefetched successor. The actual
      // origin is the visible cached page beneath the summary, not that scalar.
      const summaryRestored=summaryAfter.payload.pagination.battles.page===summaryBefore.visiblePage&&summaryAfter.visiblePage===summaryBefore.visiblePage&&summaryAfter.pageLabel===summaryBefore.pageLabel&&summaryAfter.pages.join(',')===summaryBefore.pages.join(',')&&Math.abs(summaryAfter.scroll-summaryBefore.scroll)<=3&&JSON.stringify(summaryAfter.payload.ordering.battles)===JSON.stringify(summaryBefore.payload.ordering.battles);
      check('Back from an already-open Battles summary restores its visible page, cached window, order and scroll '+reordered+(summaryRestored?'':': '+JSON.stringify({before:summaryBefore,after:summaryAfter,state:await page.evaluate(()=>GRZSessionStats.getState())})),summaryRestored);
      check('Summary return restores the exact summary source focus '+reordered,await page.locator(summarySource).evaluate(node=>document.activeElement===node));
      if(reordered){const commands=await page.evaluate(start=>__grzCommands.slice(start).filter(command=>['sort','page'].includes(command.action)),commandStart);
        check('Back restores the native origin order before requesting its page',commands.length>=2&&commands[0].action==='sort'&&commands[0].metric==='off'&&commands[0].statistic==='avg'&&commands[0].chronology==='newest'&&commands[1].action==='page'&&commands[1].group==='battles'&&Number(commands[1].page)===summaryBefore.visiblePage);
      }
    }
    for(const changed of ['account','range']){
      await configure('battles');await page.locator(summarySource).click();await opened();
      const retired=await page.evaluate(changed=>{const callback=document.querySelector('.ss-battle-return').onclick,payload=JSON.parse(model.payload),owner={account:payload.account_key,period:payload.scopes.timeline.period_id};
        // The driver owns one account. External replacement views still record
        // commands, while their independent native responses are out of scope.
        window.__returnBridgeFrozen=true;
        if(changed==='account')payload.account_key='SYNTHETIC:return-replacement';else{payload.scopes.timeline.period_id='timeline:return-other-range';payload.scopes.timeline.from_point='return-other-range';}
        model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);const start=__grzCommands.length;callback();return {start,owner};},changed);await frames(page);
      check('A retired Back callback cannot restore an earlier '+changed,await page.evaluate(({start,owner})=>!__grzCommands.slice(start).some(command=>['page','sort','battle_select'].includes(command.action)&&command.account_key===owner.account&&command.period_id===owner.period),retired));
    }
    check('Real native return bridge accepts every owned command without errors',await page.evaluate(()=>__returnBridgeErrors.length===0));
  }finally{await page.close();driver.close();}
};
