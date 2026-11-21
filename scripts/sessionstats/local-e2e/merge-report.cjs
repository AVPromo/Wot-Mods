'use strict';

const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const {createReadStream}=require('node:fs');
const {createInterface}=require('node:readline');
const {parseArgs}=require('node:util');
const {publicCase,writeReport}=require('./report.cjs');

const resultCounters=['completed','failed','interactions','interactionErrors','visualFailures','missingBaselines'];
const imagePath=/^(?:[a-z0-9_-]+\/)*[a-z0-9_-]+\.(?:png|jpe?g)$/i;
const caseKey=/^[a-z0-9_-]+(?:\/[a-z0-9_-]+)+$/i;

async function transfer(directory,out,relative) {
  assert(imagePath.test(relative),'Unexpected screenshot filename in shard');
  const source=await fs.realpath(path.join(directory,relative));
  assert(source.startsWith(directory+path.sep)&&(await fs.stat(source)).isFile(),'Screenshot is outside its shard');
  const target=path.join(out,relative);
  await fs.mkdir(path.dirname(target),{recursive:true});
  try {await fs.link(source,target);}
  catch(error) {
    if(!['EXDEV','EPERM','ENOTSUP'].includes(error.code)) throw error;
    const {constants}=require('node:fs');
    await fs.copyFile(source,target,constants.COPYFILE_EXCL);
  }
  return target;
}

async function merge({out,input,expected}) {
  const files=[];
  const seen=new Set();
  let metadata, invalidManifest=false;
  for(const sourcePath of input) {
    let directory, state;
    try {
      directory=await fs.realpath(sourcePath);
      state=JSON.parse(await fs.readFile(path.join(directory,'run.json'),'utf8'));
    } catch {
      invalidManifest=true;
      console.error('A shard manifest could not be read');
      continue;
    }
    // A damaged manifest never authorizes reading or copying that shard's
    // data. A manifest declaring private inputs rejects the whole upload.
    const required={engine:'chromium',fixture:'synthetic',assets:'test-art'};
    assert(!state||!Object.keys(required).some(key=>typeof state[key]==='string'&&state[key]&&state[key]!==required[key]),
      'Only synthetic Chromium shards are accepted in an uploadable report');
    const shard=state&&/^(\d+)\/(\d+)$/.exec(state.shard||'');
    const number=shard ? Number(shard[1]) : 0;
    if(!shard||number<1||number>expected||Number(shard[2])!==expected||seen.has(number)||
        !Object.keys(required).every(key=>state[key]===required[key])||
        typeof state.version!=='string'||state.version.length>64||
        !/^\d+\.\d+\.\d+(?:[-+][a-z0-9.-]+)?$/i.test(state.version)||
        !['build','smoke','full'].includes(state.suite)||!['all','final','failures'].includes(state.capture)||
        !['planned',...resultCounters].every(key=>Number.isSafeInteger(state[key])&&state[key]>=0)) {
      invalidManifest=true;
      console.error('A shard manifest has invalid or duplicate metadata');
      continue;
    }
    const identity=JSON.stringify([state.suite,state.version,state.engine,state.capture]);
    if(metadata===undefined) metadata=identity;
    if(metadata!==identity) {
      invalidManifest=true;
      console.error('A shard manifest has a different suite or version');
      continue;
    }
    seen.add(number);
    files.push({directory,state,number});
  }
  const first=files[0]?.state;
  const summary={version:first?.version||'unknown',engine:'chromium',renderer:first?.renderer||null,
    suite:first?.suite||'full',fixture:'synthetic',assets:'test-art',capture:first?.capture||null,
    expectedShards:expected,shards:files.length,omittedRows:0,
    finished:!invalidManifest&&files.length===expected&&files.every(({state})=>state.finished===true)};
  summary.planned=files.reduce((sum,file)=>sum+file.state.planned,0);
  for(const key of resultCounters) summary[key]=0;
  await fs.mkdir(path.dirname(out),{recursive:true});
  await fs.mkdir(out);
  const ledger=await fs.open(path.join(out,'results.ndjson'),'wx');
  const keys=new Set();
  try {
    for(const {directory,state,number} of files) {
      const observed=Object.fromEntries(resultCounters.map(key=>[key,0]));
      const lines=createInterface({input:createReadStream(path.join(directory,'results.ndjson'),{encoding:'utf8'}),crlfDelay:Infinity});
      try {
        for await(const line of lines) {
          if(!line.trim()) continue;
          let item, row;
          const copied=[];
          try {
            item=JSON.parse(line);
            row=publicCase(item);
            assert(row&&caseKey.test(row.key)&&!keys.has(row.key),'Invalid or duplicate case in shard');
            for(const frame of row.frames) {
              const image=row.key+'/'+frame.file;
              copied.push(await transfer(directory,out,image));
              if(frame.reference) copied.push(await transfer(directory,out,'baseline/'+image));
              if(frame.diff) copied.push(await transfer(directory,out,'differences/'+image));
            }
          } catch {
            summary.finished=false;
            summary.omittedRows++;
            // A rejected row owns only the files it successfully copied.
            // Release them so a later valid row can recover the same case.
            await Promise.all(copied.map(target=>fs.rm(target,{force:true})));
            continue;
          }
          await ledger.appendFile(JSON.stringify(item)+'\n');
          keys.add(row.key);
          const interaction=row.group==='interactions';
          observed[interaction?'interactions':'completed']++;
          if(row.issues.includes('fail')) observed[interaction?'interactionErrors':'failed']++;
          observed.visualFailures+=row.frames.filter(frame=>frame.changed).length;
          observed.missingBaselines+=row.frames.filter(frame=>frame.missing).length;
        }
      } catch {
        summary.finished=false;
        console.error(`Shard ${number} has an unreadable result ledger`);
      } finally {
        for(const key of resultCounters) summary[key]+=observed[key];
      }
      const validPlan=state.planned>0&&state.completed<=state.planned&&
        (state.finished!==true||state.completed===state.planned);
      if(!validPlan||resultCounters.some(key=>state[key]!==observed[key])) {
        summary.finished=false;
        console.error(`Shard ${number} has inconsistent test results or counts`);
      }
    }
  } catch(error) {
    summary.finished=false;
    throw error;
  } finally {
    await ledger.close();
    await fs.writeFile(path.join(out,'run.json'),JSON.stringify(summary,null,2)+'\n');
    await writeReport(out,summary);
  }
  if(!summary.finished||summary.failed||summary.interactionErrors||summary.visualFailures||summary.missingBaselines) {
    process.exitCode=1;
  }
}

const {values,positionals}=parseArgs({allowPositionals:true,
  options:{out:{type:'string'},'expected-shards':{type:'string'}}});
const expected=Number(values['expected-shards']||positionals.length);
assert(values.out&&Number.isInteger(expected)&&expected>=1,'Use --out DIRECTORY [--expected-shards N] [shard directories]');
merge({out:path.resolve(values.out),expected,input:positionals})
  .catch(error=>{console.error(error.message);process.exitCode=1;});
