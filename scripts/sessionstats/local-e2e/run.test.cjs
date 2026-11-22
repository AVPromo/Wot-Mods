'use strict';

const assert = require('node:assert/strict');
const {test} = require('node:test');
const {runCase} = require('./run.cjs');

const task={width:365,height:730,language:'en',range:'since-sunday',group:'vehicles',scope:'timeline'};
const order={metric:'off',statistic:'avg',direction:'desc',chronology:'newest'};
const version='0.9.35';
const phase=(top,remaining,layout={})=>({top,remaining,visible:1,mounted:3,resultsReached:true,resultsTop:330,
  contentTop:120,contentBottom:650,...layout});
const clipped={visible:0,resultsReached:false,resultsTop:830};

function probe(phases,total=3) {
  let index=-1;
  const wheels=[], captures=[];
  const ctx={
    applyOrder:async()=>{},
    idle:async()=>{},
    read:()=>({scopes:{timeline:{pagination:{vehicles:{total}}}}}),
    snapshot:async name=>{captures.push(name);return name;},
    driver:{
      evaluate:async()=> {
        if(index++===-1) return;
        return {...phases[index-1],width:task.width,height:task.height,group:task.group,
          version:'v'+version,wheelAt:{x:100,y:200},errors:[],wheels:[...wheels]};
      },
      wheel:async(x,y,delta)=>{wheels.push({delta,trusted:true});}
    }
  };
  return {run:()=>runCase(ctx,task,order,version,'all'),wheels,captures};
}

test('a trusted wheel must move the actual viewport while it has space',async()=>{
  for(const [name,phases] of [
    ['never starts',[phase(0,500),phase(0,500)]],
    ['stalls on the second notch',[phase(0,500),phase(130,370),phase(130,370)]],
  ]) {
    await assert.rejects(probe(phases).run(),/did not move the primary scroll viewport/,name);
  }
});

test('short results and the bottom of the list permit a stationary wheel',async()=>{
  for(const phases of [
    Array.from({length:4},()=>phase(0,0)),
    [phase(0,135),phase(130,5),phase(135,0),phase(135,0)],
  ]) {
    const {run,wheels,captures}=probe(phases);
    await run();
    assert.equal(wheels.length,3);
    assert.equal(captures.length,4);
  }
});

test('results must mount, have visible layout and be visible when they intersect the viewport',async()=>{
  for(const [layout,error] of [
    [{mounted:0},/mounted no cards/],
    [{resultsTop:null,visible:0},/no result card has visible layout/],
    [{visible:0},/visible without any result cards/],
  ]) {
    await assert.rejects(probe([phase(0,500,layout)]).run(),error);
  }
});

test('three wheel movements may stop above cards that remain reachable',async()=>{
  const {run,wheels}=probe([phase(0,900,clipped),phase(130,770,clipped),
    phase(260,640,clipped),phase(390,510,clipped)]);
  await run();
  assert.equal(wheels.length,3);
});

test('cards clipped outside the reachable range fail the case',async()=>{
  for(const [remaining,layout] of [[30,clipped],[310,{...clipped,resultsTop:340}],[310,{...clipped,contentTop:650}]]) {
    await assert.rejects(probe([phase(0,remaining+390,clipped),phase(130,remaining+260,clipped),
      phase(260,remaining+130,clipped),phase(390,remaining,layout)]).run(),/No result card appeared/);
  }
});

test('an empty response can scroll or stay put and cannot show stale cards',async()=>{
  await probe(Array.from({length:4},()=>phase(0,0,{...clipped,mounted:0,resultsTop:null})),0).run();
  await assert.rejects(probe([phase(0,0)],0).run(),/retained result cards for an empty Python response/);
});
