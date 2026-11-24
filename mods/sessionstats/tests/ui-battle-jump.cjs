/* Native page-three navigation must follow the exact card through late layout. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
const shipped=()=>fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8').replace(/\r\n/g,'\n');
function actualFunction(source,name) {
  const start=source.indexOf('    function '+name+'('),end=source.indexOf('\n    }\n',start);
  assert(start>=0&&end>start,'Exercise actual shipped '+name);return source.slice(start,end+7);
}
function geometry(source=shipped()) {
  let clock=1000,offset=0,physical=0,position=1500,missing=false,busy=false,validContext=true,lag=false,pendingOffset=null,focused=0,paints=0,nextTimer=1,pinnedUpdates=0;
  let droppedWrites=0,maximum=4000;
  const timers=new Map(),owner={account_key:'synthetic-jump',scope:'launch',period_id:'synthetic-period'};
  const feed={navigationPage:2};
  const target={getAttribute:name=>name==='data-group-id'?'selected-page-three':null,
    get offsetTop(){return position;},
    getBoundingClientRect:()=>missing?{top:0,width:0,height:0}:({top:100+position-physical,bottom:250+position-physical,width:500,height:150}),
    querySelector:selector=>selector==='.ss-battle-selection-banner'?{
      getBoundingClientRect:()=>({top:90+position-physical,bottom:110+position-physical,height:20})
    }:null};
  const scroll={get scrollTop(){return offset;},set scrollTop(value){const next=Math.max(0,Math.min(maximum,value));
      if(droppedWrites>0){droppedWrites--;return;}
      if(lag){pendingOffset=next;if(lag==='getter')physical=next;if(lag==='rect')offset=next;}
      else {offset=next;physical=next;}},
    clientHeight:500,scrollHeight:4500,getBoundingClientRect:()=>({top:100,bottom:600,width:700,height:500})};
  target.offsetParent=scroll;
  const groups={offsetTop:300,offsetParent:scroll,getAttribute:()=>busy?'true':'false',
    getBoundingClientRect:()=>({top:400-physical,bottom:4600-physical,width:700,height:4200})};
  const state={destroyed:false,bound:true,pendingBattle:{id:'selected-page-three',request_id:'owned-focus',context:owner},
    group:'maps',nativeScale:1,battleJump:null,battleJumpTimer:null,targetSequence:0,targetTimer:null,
    groupCards:[],feed,renderedFeed:feed,cardPages:[{index:2,section:{getBoundingClientRect:()=>({top:600-offset,width:700,height:2000})}}],
    cardFlowQueued:false,scrollTarget:null,pageJump:{feed,page:2}};
  const context={state,nodes:{scroll,groups},Date:{now:()=>clock},Math,
    hasNumber:value=>typeof value==='number'&&Number.isFinite(value),sameContext:()=>validContext,
    currentScope:()=>({}),renderFilterActivity(){},
    clearBattleTarget(){state.highlightedBattle=null;},paintBattleTarget(){paints++;},
    cancelUITimer:id=>timers.delete(id),window:{setTimeout(callback,delay){const id=nextTimer++;timers.set(id,{callback,delay});return id;}},
    focusControl(){focused++;},pinnedFilterHeight:()=>60,scrollbarMetrics:()=>({maximum}),
    queueResize(){context.finishBattleJump();},updatePinnedFilters(){pinnedUpdates++;},syncScrollbar(){}};
  vm.createContext(context);
  const names=['cancelBattleNavigation','cancelPageJump','retireFeed','consumeBattleFocus','startBattleJump','retainBattleTargetAfterResize',
    'renderedBattleTarget','finishBattleJump','finishPageJump','onScrollIntent','battleOwnsViewport','keepSelectedBattleVisible'];
  for(const name of ['retryBattleJump','battleLayoutOffset','battleScrollPending'])if(source.includes('    function '+name+'('))names.push(name);
  vm.runInContext(names.map(name=>actualFunction(source,name)).join('\n'),context);
  context.consumeBattleFocus({battle_focus:{id:'selected-page-three',request_id:'owned-focus'},pagination:{battles:{page:2}}});
  return {context,state,scroll,target,timers,
    tick(delta=100){clock+=delta;const next=[...timers].find(([,timer])=>timer.delay>0&&timer.delay<=100);if(next){timers.delete(next[0]);next[1].callback();}},
    show(){state.groupCards=[target];},missing(value){missing=value;},busy(value){busy=value;},
    move(value){position=value;},limit(value){maximum=value;},setContext(value){validContext=value;},lag(value){lag=value;},
    dropNextWrite(){droppedWrites++;},
    flush(){lag=false;if(pendingOffset!==null){offset=pendingOffset;physical=pendingOffset;pendingOffset=null;}},
    focused:()=>focused,paints:()=>paints,pinnedUpdates:()=>pinnedUpdates};
}
function assertBattleJumpSource(source=shipped()) {
  const late=geometry(source);late.context.finishBattleJump();late.tick(3000);
  assert(late.state.battleJump,'A result arriving after the previous two-second limit still owns its destination');
  late.show();late.missing(true);late.tick(100);assert.strictEqual(late.focused(),0,'Placeholder card geometry cannot receive focus');
  late.missing(false);late.busy(true);late.tick(100);assert.strictEqual(late.scroll.scrollTop,0,'A rebuilding page does not align against staged geometry');
  late.busy(false);late.tick(100);
  assert.strictEqual(late.scroll.scrollTop,1424,'The exact card below the page-three divider is aligned with room for its overlay badge');
  assert.strictEqual(late.focused(),1);assert(late.state.battleJump,'First measurable paint is not yet stable');
  late.state.pageJump={feed:late.state.feed,page:2};late.context.finishPageJump();
  assert.strictEqual(late.scroll.scrollTop,1424,'Page-level navigation cannot override the more specific battle destination');
  assert.strictEqual(late.state.pageJump,null);
  late.lag(true);late.move(1900);late.tick(100);
  assert.strictEqual(late.scroll.scrollTop,1424,'The native scroll setter can lag while geometry changes');
  assert(late.state.battleJump,'An unapplied scroll setter is not considered settled');
  late.flush();assert.strictEqual(late.scroll.scrollTop,1824);
  for(let index=0;index<7&&late.state.battleJump;index++)late.tick(100);
  assert.strictEqual(late.state.battleJump,null,'Repeated stable geometry retires the owned correction');
  assert.strictEqual(late.focused(),1,'Native focus is applied once per mounted destination');
  assert.strictEqual(late.timers.size,1,'Only the separate paint pulse remains after alignment');

  late.state.resize={};late.scroll.scrollTop=1200;late.move(2100);
  late.context.finishBattleJump();
  assert.strictEqual(late.scroll.scrollTop,1200,'The held resize does not fight the current scroll');
  late.state.resize=null;late.busy(true);late.context.retainBattleTargetAfterResize();late.context.finishBattleJump();
  assert.strictEqual(late.scroll.scrollTop,1200,'Release waits for the final lane layout');
  late.busy(false);late.tick();
  assert.strictEqual(late.scroll.scrollTop,1750,'Release brings an offscreen selected card fully into view');
  late.move(1300);late.tick();
  assert.strictEqual(late.scroll.scrollTop,1224,'The same release follows a late lane change');
  for(let index=0;index<7&&late.state.battleJump;index++)late.tick();
  late.scroll.scrollTop=1175;late.context.retainBattleTargetAfterResize();late.context.finishBattleJump();
  assert.strictEqual(late.scroll.scrollTop,1175,'A visible selected card keeps its current scroll after resizing');
  assert.strictEqual(late.focused(),1,'Resize reveal leaves keyboard focus on the active control');
  late.context.onScrollIntent({type:'wheel',deltaY:1,target:late.scroll});late.scroll.scrollTop=500;late.tick();
  assert.strictEqual(late.scroll.scrollTop,500,'New user scrolling supersedes resize alignment');
  late.context.retainBattleTargetAfterResize();
  assert.strictEqual(late.context.battleOwnsViewport(),false,'A resize can reveal the card once without reclaiming ownership after a user scroll');
  assert.strictEqual(late.state.battleJump.revealOnly,true);

  const notices=geometry(source);notices.show();notices.context.finishBattleJump();
  for(let index=0;index<8&&notices.state.battleJump;index++)notices.tick();
  assert.strictEqual(notices.state.battleJump,null);
  notices.move(1475);
  notices.context.keepSelectedBattleVisible();
  assert(notices.state.battleJump,'Removing a notice triggers correction even when the selected card node was reused');
  notices.context.finishBattleJump();
  assert(notices.target.querySelector('.ss-battle-selection-banner').getBoundingClientRect().top>=160,
    'The marker returns below the pinned filters without a native scrollbar event');
  assert.strictEqual(notices.focused(),1,'The correction does not steal keyboard focus again');

  const duringJump=geometry(source);duringJump.show();duringJump.state.resize={};duringJump.context.finishBattleJump();
  assert.strictEqual(duringJump.scroll.scrollTop,0,'An initial jump also waits while the window is being resized');
  duringJump.state.resize=null;duringJump.context.retainBattleTargetAfterResize();duringJump.context.finishBattleJump();
  assert.strictEqual(duringJump.scroll.scrollTop,1424,'Releasing during initial selection resumes its original alignment');
  assert.strictEqual(duringJump.focused(),1,'The original selection still receives initial focus');

  for(const phase of ['getter','rect']) {
    const async=geometry(source);async.show();async.lag(phase);async.context.finishBattleJump();
    for(let index=0;index<3;index++)async.tick(100);
    assert.strictEqual(async.state.battleJump.requestedOffset,1424,'A '+phase+'-late setter retains the original destination');
    assert.strictEqual(async.pinnedUpdates(),0,'Mixed '+phase+' samples cannot clamp the pinned-filter range');
    const pinned=vm.runInContext('('+actualFunction(source,'updatePinnedFilters')+')',async.context);
    async.context.nodes['filter-panel']={getBoundingClientRect(){throw Error('Mixed '+phase+' samples reached normal-flow clamping');}};
    pinned();
    async.flush();async.tick(100);
    assert.strictEqual(async.scroll.scrollTop,1424,'Acknowledged '+phase+' geometry does not undo the original jump');
    assert(async.pinnedUpdates()>0,'The pinned bar refreshes after '+phase+' acknowledgement');
    for(let index=0;index<7&&async.state.battleJump;index++)async.tick(100);
    assert.strictEqual(async.state.battleJump,null,'Acknowledged '+phase+' geometry settles and retires');
  }

  const dropped=geometry(source);dropped.show();dropped.dropNextWrite();dropped.context.finishBattleJump();
  assert.strictEqual(dropped.scroll.scrollTop,0,'A discarded native setter changes neither the scroll getter nor the rendered geometry');
  for(let index=0;index<8&&dropped.scroll.scrollTop===0;index++)dropped.tick();
  assert.strictEqual(dropped.scroll.scrollTop,1424,'A discarded scroll write is reissued while the original battle still owns alignment');
  assert.strictEqual(dropped.focused(),1,'Reissuing the scroll preserves the single focus transfer');

  const shrinking=geometry(source);shrinking.show();shrinking.dropNextWrite();shrinking.context.finishBattleJump();
  assert(shrinking.state.battleJump.requestedOffset>150,'The selected card requested a position above the future range');
  shrinking.move(225);shrinking.limit(150);shrinking.tick();
  assert.strictEqual(shrinking.state.battleJump.requestedOffset,150,'The retained selected card setter uses the new maximum');
  assert.strictEqual(shrinking.scroll.scrollTop,150);
  for(let index=0;index<12&&shrinking.state.battleJump;index++)shrinking.tick();
  assert.strictEqual(shrinking.state.battleJump,null,'The selected card settles before timeout after the range shrinks');
  assert.strictEqual(shrinking.focused(),1);

  for(const kind of ['wheel','mousedown','keydown']) {
    const moved=geometry(source);moved.context.finishBattleJump();
    const retained=[...moved.timers.values()].find(timer=>timer.delay===100).callback;
    moved.context.onScrollIntent({type:kind,key:'ArrowDown',deltaY:1,button:0,target:moved.scroll});
    moved.state.scrollTarget=null;moved.scroll.scrollTop=350;moved.show();retained();
    assert.strictEqual(moved.state.battleJump,null,'Newer '+kind+' retires the pending target');
    assert.strictEqual(moved.scroll.scrollTop,350,'Late target geometry cannot undo newer '+kind);
    assert.strictEqual(moved.focused(),0);
  }
  for(const kind of ['deadline','attempts','context','dismissal']) {
    const expired=geometry(source);expired.context.finishBattleJump();
    if(kind==='deadline')expired.tick(10000);
    else if(kind==='attempts')for(let index=0;index<105&&expired.state.battleJump;index++)expired.tick(0);
    else if(kind==='context'){expired.setContext(false);expired.tick(100);}
    else {expired.state.highlightedBattle=null;expired.tick(100);}
    assert.strictEqual(expired.state.battleJump,null,kind+' retires automatic navigation');
    assert.strictEqual([...expired.timers.values()].filter(timer=>timer.delay===100).length,0,'No retired geometry timers survive '+kind);
    expired.show();expired.context.finishBattleJump();assert.strictEqual(expired.scroll.scrollTop,0);
  }
}
module.exports={assertBattleJumpSource};
if(require.main===module){assertBattleJumpSource();console.log('Actual-source delayed page-three target, stable layout, page priority and input cancellation passed.');}
