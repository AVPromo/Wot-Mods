'use strict';

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const { test } = require('node:test');

const scenario = {key:'625x730/en/history/vehicles/xp_received-sum-desc-newest'};
const interaction = {key:'interactions/625x730'};
const failure = 'Synthetic test failure';
const manifest = {
  engine:'chromium', fixture:'synthetic', assets:'test-art', version:'0.9.30', suite:'build',
  capture:'all', shard:'1/1', planned:1, completed:1, failed:0, interactions:1, interactionErrors:0,
  visualFailures:0, missingBaselines:0, finished:true
};

async function merge(t, {state={}, rows=[scenario,interaction], expected=1, missing=false,
  rawManifest, rawLedger, images={}, additional=[]}={}) {
  const directory = await fs.mkdtemp(path.join(await fs.realpath(os.tmpdir()),'sessionstats-merge-'));
  t.after(async()=>fs.rm(directory,{recursive:true,force:true}));
  const output = path.join(directory,'report');
  const args = [path.join(__dirname,'merge-report.cjs'),'--out',output,'--expected-shards',String(expected)];
  const inputs=missing ? [] : [{state,rows,rawManifest,rawLedger,images},...additional];
  for(const [index,input] of inputs.entries()) {
    const shard=path.join(directory,'shard-'+index);
    await fs.mkdir(shard);
    await fs.writeFile(path.join(shard,'run.json'),input.rawManifest??JSON.stringify({...manifest,...input.state}));
    const ledger=(input.rows??[scenario,interaction]).map(row=>JSON.stringify(row)+'\n').join('');
    await fs.writeFile(path.join(shard,'results.ndjson'),input.rawLedger??ledger);
    for(const [relative,contents] of Object.entries(input.images??{})) {
      const image=path.join(shard,relative);
      await fs.mkdir(path.dirname(image),{recursive:true});
      await fs.writeFile(image,contents);
    }
    args.push(shard);
  }
  const result = spawnSync(process.execPath,args,{encoding:'utf8'});
  assert.ifError(result.error);
  if(inputs.some(input=>input.state?.fixture&&input.state.fixture!=='synthetic')) {
    await assert.rejects(fs.access(output),{code:'ENOENT'});
    return {result};
  }
  const summary = JSON.parse(await fs.readFile(path.join(output,'run.json'),'utf8'));
  const html = await fs.readFile(path.join(output,'index.html'),'utf8');
  const catalogue = await fs.readFile(path.join(output,'catalog.js'),'utf8');
  assert.match(html, /<script src="catalog\.js"><\/script>/);
  assert.match(html, /Run incomplete/);
  assert.ok(!catalogue.includes(failure));
  const data=JSON.parse(catalogue.slice('window.sessionStatsMatrix = '.length).trimEnd().slice(0,-1));
  return {result,summary,data,output};
}

test('succeeds only after matching one scenario and one interaction to the manifest', async t => {
  const {result,summary} = await merge(t);
  assert.equal(result.status,0);
  assert.equal(summary.finished,true);
  assert.equal(summary.completed,1);
  assert.equal(summary.interactions,1);
});

test('a recorded failure fails the run while keeping its report', async t => {
  const {result,summary} = await merge(t,{state:{failed:1},rows:[{...scenario,error:failure},interaction]});
  assert.equal(result.status,1);
  assert.equal(summary.finished,true);
  assert.equal(summary.failed,1);
});

test('counts test failures even if the claimed totals say zero', async t => {
  const {result,summary} = await merge(t,{rows:[
    {...scenario,error:failure},
    {...interaction,error:failure},
  ]});
  assert.equal(result.status,1);
  assert.match(result.stderr,/inconsistent test results/);
  assert.equal(summary.finished,false);
  assert.equal(summary.failed,1);
  assert.equal(summary.interactionErrors,1);
});

test('marks missing ledger rows and invalid plans as incomplete', async t => {
  for(const [title,options,completed] of [
    ['missing case', {rows:[interaction]}, 0],
    ['missing interaction', {rows:[scenario]}, 1],
    ['empty plan', {state:{planned:0,completed:0,interactions:0},rows:[]}, 0],
    ['finished before all planned cases', {state:{planned:2}}, 1],
  ]) {
    await t.test(title,async check=>{
      const {result,summary} = await merge(check,options);
      assert.equal(result.status,1);
      assert.equal(summary.finished,false);
      assert.equal(summary.completed,completed);
    });
  }
});

test('publishes an incomplete report if shard artefacts are unavailable', async t => {
  for(const [title,options,shards] of [
    ['all expired', {missing:true}, 0],
    ['one missing', {expected:2,state:{shard:'1/2'}}, 1],
  ]) {
    await t.test(title,async check=>{
      const {result,summary,data} = await merge(check,options);
      assert.equal(result.status,1);
      assert.equal(summary.finished,false);
      assert.equal(summary.completed,shards);
      assert.equal(summary.shards,shards);
      assert.equal(data.summary.incomplete,true);
      assert.equal(data.summary.shards,shards);
      assert.equal(data.summary.expectedShards,options.expected??1);
    });
  }
});

test('rejects a private fixture before creating any output', async t => {
  const {result} = await merge(t,{expected:2,state:{shard:'1/2'},
    additional:[{state:{shard:'2/2',fixture:'local-aggregate'}}]});
  assert.equal(result.status,1);
  assert.match(result.stderr,/Only synthetic Chromium/);
});

test('skips a damaged manifest and publishes healthy shard results', async t => {
  const {result,summary,data}=await merge(t,{expected:2,rawManifest:'{"fixture":',
    rows:[{key:'1220x900/en/history/maps/xp_received-sum-desc-newest'}],
    additional:[{state:{shard:'2/2'}}]});
  assert.equal(result.status,1);
  assert.match(result.stderr,/manifest could not be read/);
  assert.equal(summary.finished,false);
  assert.equal(summary.shards,1);
  assert.equal(summary.completed,1);
  assert.deepEqual(data.rows.map(row=>row.key),[scenario.key,interaction.key]);
  assert.equal(data.summary.incomplete,true);
});

test('skips malformed provenance without reading the affected shard', async t => {
  const untrusted={key:'1220x900/en/history/maps/xp_received-sum-desc-newest'};
  const {result,summary,data}=await merge(t,{expected:2,state:{shard:'1/2',fixture:null,assets:[]},
    rows:[untrusted],additional:[{state:{shard:'2/2'}}]});
  assert.equal(result.status,1);
  assert.match(result.stderr,/manifest has invalid/);
  assert.equal(summary.shards,1);
  assert.equal(summary.finished,false);
  assert.deepEqual(data.rows.map(row=>row.key),[scenario.key,interaction.key]);
});

test('checks run identity fields before accepting a shard as the report identity', async t => {
  for(const damaged of [{version:null},{suite:'unknown'},{capture:false}]) {
    const {result,summary,data}=await merge(t,{expected:2,state:{shard:'1/2',...damaged},
      rawLedger:'{"key":',additional:[{state:{shard:'2/2'}}]});
    assert.equal(result.status,1);
    assert.match(result.stderr,/manifest has invalid/);
    assert.equal(summary.version,manifest.version);
    assert.equal(summary.shards,1);
    assert.equal(summary.finished,false);
    assert.deepEqual(data.rows.map(row=>row.key),[scenario.key,interaction.key]);
  }
});

test('keeps valid ledger rows after a damaged row and continues the other shards', async t => {
  const other={key:'1220x900/en/history/maps/xp_received-sum-desc-newest'};
  const nextInteraction={key:'interactions/1220x900'};
  const {result,summary,data}=await merge(t,{expected:2,state:{shard:'1/2'},
    rawLedger:JSON.stringify(scenario)+'\n{"key":\n'+JSON.stringify(interaction)+'\n',
    additional:[{state:{shard:'2/2'},rows:[other,nextInteraction]}]});
  assert.equal(result.status,1);
  assert.equal(summary.finished,false);
  assert.equal(summary.shards,2);
  assert.equal(summary.completed,2);
  assert.equal(summary.interactions,2);
  assert.equal(data.summary.incomplete,true);
  assert.equal(data.summary.omitted,1);
  assert.deepEqual(data.rows.map(row=>row.key),[scenario.key,other.key,interaction.key,nextInteraction.key]);
});

test('a damaged row releases its copied screenshots so a later valid case can be recovered', async t => {
  const first=scenario.key+'/0.png';
  const missing=scenario.key+'/1.png';
  const {result,summary,data,output}=await merge(t,{expected:2,state:{shard:'1/2',interactions:0},
    rows:[{...scenario,shots:[{image:first},{image:missing}]}],
    images:{[first]:'screenshot from the damaged row'},
    additional:[{state:{shard:'2/2',interactions:0},
      rows:[{...scenario,shots:[{image:first}]}],
      images:{[first]:'screenshot from the recovered row'}}]});
  assert.equal(result.status,1);
  assert.equal(summary.finished,false);
  assert.equal(summary.completed,1);
  assert.equal(data.summary.omitted,1);
  assert.deepEqual(data.rows.map(row=>row.key),[scenario.key]);
  assert.equal(await fs.readFile(path.join(output,first),'utf8'),'screenshot from the recovered row');
  await assert.rejects(fs.access(path.join(output,missing)),{code:'ENOENT'});
});

test('rejects a duplicate without replacing a committed case or its screenshot', async t => {
  const image=scenario.key+'/0.png';
  const rows=[{...scenario,shots:[{image}]}];
  const {result,summary,data,output}=await merge(t,{expected:2,state:{shard:'1/2',interactions:0},
    rows,images:{[image]:'original screenshot'},
    additional:[{state:{shard:'2/2',interactions:0},rows,images:{[image]:'duplicate screenshot'}}]});
  assert.equal(result.status,1);
  assert.equal(summary.finished,false);
  assert.equal(summary.completed,1);
  assert.equal(data.summary.omitted,1);
  assert.deepEqual(data.rows.map(row=>row.key),[scenario.key]);
  assert.equal(await fs.readFile(path.join(output,image),'utf8'),'original screenshot');
});
