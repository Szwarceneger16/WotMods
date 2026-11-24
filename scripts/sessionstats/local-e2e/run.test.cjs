'use strict';

const assert = require('node:assert/strict');
const {test} = require('node:test');
const {runInNewContext} = require('node:vm');
const {applySortOrder,runCase} = require('./run.cjs');

const task={width:365,height:730,language:'en',range:'since-sunday',group:'vehicles',scope:'timeline'};
const order={metric:'off',statistic:'avg',direction:'desc',chronology:'newest'};
const version='0.9.35';
const phase=(top,remaining,layout={})=>({top,remaining,visible:1,mounted:3,resultsReached:true,resultsTop:330,
  contentTop:120,contentBottom:650,...layout});
const clipped={visible:0,resultsReached:false,resultsTop:830};

test('the runner preserves a preceding Max selection when the next sort hides Statistic',async()=>{
  for(const [group,metric] of [['vehicles','win_rate'],['maps','battles'],['battles','xp_received']]) {
    const current={...order,metric:'battle_wn8',statistic:'max',direction:'asc'};
    const selected=[];
    await applySortOrder(group,{...order,metric},{
      wide:false,read:()=>current,idle:async()=>{},
      click:async()=>assert.fail('The wide toggle is unavailable'),
      select:async(selector,value)=>{
        assert.notEqual(selector,'#ss-sort-statistic','The Statistic control is hidden');
        selected.push(selector);
        current[selector.slice('#ss-sort-'.length)]=value;
      },
    });
    assert.deepEqual(selected,['#ss-sort-metric','#ss-sort-direction']);
    assert.equal(current.statistic,'max');
  }
});

test('the runner still checks acceptance of an applicable Statistic selection',async()=>{
  const current={...order,metric:'battle_wn8',statistic:'max'};
  const selected=[];
  await assert.rejects(applySortOrder('vehicles',{...current,statistic:'min'},{
    wide:false,read:()=>current,idle:async()=>{},
    click:async()=>assert.fail('The wide toggle is unavailable'),
    select:async(selector,value)=>selected.push([selector,value]),
  }),/Python did not accept statistic/);
  assert.deepEqual(selected,[['#ss-sort-statistic','min']]);
});

function mounted({page,offset,ids},wide=false,top=0) {
  const cards=ids.map((id,index)=>({id,page:String(page),index:String(offset+index),lane:wide?index%2:0,
    top:top+(wide?Math.floor(index/2)*100+(index%2)*25:index*100),left:wide&&index%2?450:100}));
  // Each lane is a DOM column; the intended reading order interleaves them.
  return wide?[...cards.filter(card=>card.lane===0),...cards.filter(card=>card.lane===1)]:cards;
}

function probe(phases,total=3,results=null,startingScroll=0) {
  let index=-1;
  const first={page:0,offset:0,total,ids:['9007199254740993','002','10'].slice(0,total)};
  results=results||{current:first,pages:new Map([[0,first]])};
  const wheels=[], captures=[];
  const scroll={scrollTop:startingScroll};
  let queuedScroll=startingScroll;
  const topButton={onclick:()=>{scroll.scrollTop=queuedScroll=0;}};
  const ctx={
    applyOrder:async()=>{},
    idle:async()=>{
      if(queuedScroll!==null) scroll.scrollTop=queuedScroll;
      queuedScroll=null;
    },
    resultPages:()=>results,
    snapshot:async name=>{captures.push(name);return name;},
    driver:{
      evaluate:async callback=>{
        if(index++===-1) {
          return runInNewContext(`(${callback})()`,{window:{},document:{getElementById:id=>
            ({'ss-scroll':scroll,'ss-scroll-top':topButton})[id]}});
        }
        const layout=phases[index-1];
        return {rendered:mounted(results.current),wide:false,...layout,top:index===1?scroll.scrollTop:layout.top,
          width:task.width,height:task.height,group:task.group,
          version:'v'+version,wheelAt:{x:100,y:200},errors:[],wheels:[...wheels]};
      },
      wheel:async(x,y,delta)=>{wheels.push({delta,trusted:true});}
    }
  };
  return {run:()=>runCase(ctx,task,order,version,'all'),wheels,captures};
}

test('a queued layout cannot restore the previous scenario scroll offset',async()=>{
  const {run}=probe([phase(0,600),phase(192,408),phase(384,216),phase(576,24)],3,null,576);
  const report=await run();
  assert.deepEqual(report.phases.map(item=>item.top),[0,192,384,576]);
});

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

test('mounted IDs must match the Python order at each position and screenshot phase',async()=>{
  const current={page:0,offset:0,total:3,ids:['9007199254740993','02','10']};
  const results={current,pages:new Map([[0,current]])};
  const original=mounted(current), reversed=mounted({...current,ids:[...current.ids].reverse()});
  const phases=[phase(0,500,{rendered:original}),phase(130,370,{rendered:reversed})];
  await assert.rejects(probe(phases,3,results).run(),/Rendered result order differs from Python on page 1 at list position 1/);
  const rounded=original.map((card,index)=>index?card:{...card,id:String(Number(card.id))});
  await assert.rejects(probe([phase(0,0,{rendered:rounded})],3,results).run(),/Rendered result order differs/);
});

test('cached pages remain verifiable in the two-column layout',async()=>{
  const first={page:0,offset:0,total:6,ids:['a','b','c','d']};
  const current={page:1,offset:4,total:6,ids:['e','f']};
  const results={current,pages:new Map([[0,first],[1,current]])};
  const rendered=[...mounted(first,true),...mounted(current,true,230)];
  const layout={rendered,wide:true,mounted:6};
  const {run,captures}=probe(Array.from({length:4},()=>phase(0,0,layout)),6,results);
  const report=await run();
  assert.equal(captures.length,4);
  assert(report.phases.every(item=>!Object.hasOwn(item,'rendered')),'Card IDs are not included in the report');
  const [a,c,b,d,e,f]=rendered;
  for(const [items,error] of [
    [[a,{...c,index:'0'},b,d,e,f],/Duplicate result card/],
    [[a,b,d,e,f],/only part of Python page 1/],
    [[a,c,b,d],/did not mount Python page 2/],
    [[a,c,b,d,e,{...f,page:'2'}],/without a matching Python response/],
    [[e,f,a,c,b,d],/Mounted result pages are out of order/],
    [[a,{...c,lane:1},b,d,e,f],/wrong lane/],
    [[c,a,b,d,e,f],/one lane are out of order/],
    [[a,{...c,top:-1},b,d,e,f],/reverse vertical order/],
    [[a,c,{...b,left:20},d,e,f],/lanes are out of order across the panel/],
  ]) {
    await assert.rejects(probe([phase(0,0,{...layout,rendered:items,mounted:items.length})],6,results).run(),error);
  }
});
